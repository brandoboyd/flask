import pytz
from collections import defaultdict
from operator import itemgetter
from datetime import datetime, date, time, timedelta

from solariat.db import fields
from solariat.db.abstract import SonDocument
from solariat.utils import timeslot

combine = datetime.combine


def inverse(d):
    return dict(zip(d.values(), d.keys()))


def dates_diff(d1, d2):
    return abs((timeslot.utc(d2) - timeslot.utc(d1)).total_seconds())


DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


class TimeMark(SonDocument):

    PERIODIC_DATE_FORMAT = '%m-%d'
    STATIC_DATE_FORMAT = '%Y-%m-%d'
    TIME_FORMAT = '%H:%M:%S'

    DAY_OF_WEEK = 0
    PERIODIC_DATE = 1
    STATIC_DATE = 2

    TYPE_NAME_MAP = {
        DAY_OF_WEEK: 'dayofweek',
        PERIODIC_DATE: 'periodicdate',
        STATIC_DATE: 'staticdate'}

    TYPE_CLASS_MAP = property(lambda self: {
        self.DAY_OF_WEEK: DayOfWeek,
        self.PERIODIC_DATE: PeriodicDate,
        self.STATIC_DATE: StaticDate})

    mark_type = fields.NumField(choices=(DAY_OF_WEEK, PERIODIC_DATE, STATIC_DATE), db_field='t')
    value = fields.StringField()
    _from_time = fields.DateTimeField(db_field='a', default=None, null=True)
    _to_time = fields.DateTimeField(db_field='b', default=None, null=True)

    @property
    def from_time(self):
        return self._from_time and self._from_time.time() or time()

    @property
    def from_time_fmt(self):
        return self._from_time and self.from_time.strftime(self.TIME_FORMAT)

    @property
    def to_time(self):
        return self._to_time and self._to_time.time() or time(23, 59, 59, 999999)

    @property
    def to_time_fmt(self):
        return self._to_time and self.to_time.strftime(self.TIME_FORMAT)

    @property
    def mark_type_str(self):
        return self.TYPE_NAME_MAP[self.mark_type]

    def __init__(self, data=None, **kw):
        if self.__class__ != TimeMark and not ('mark_type' in kw or data and 't' in data):
            m = inverse(self.TYPE_CLASS_MAP)
            kw.update(mark_type=m[self.__class__])

        super(TimeMark, self).__init__(data=data, **kw)

        class_ = self.TYPE_CLASS_MAP[self.data['t']]
        if class_ != self.__class__:
            self.__class__ = class_
            class_.validate(self)

    def __hash__(self):
        return (self.mark_type, self.value,
                self.from_time_fmt, self.to_time_fmt)

    def __str__(self):
        return u"<%s %s %s %s>" % (self.__class__.__name__, self.value,
                                   self.from_time_fmt, self.to_time_fmt)

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __lt__(self, other):
        raise TypeError("%s is not comparable type" % self.__class__.__name__)

    def to_json(self, fields_to_show=None):
        result = {
            "type": self.mark_type_str,
            "from": self.from_time_fmt,
            "to": self.to_time_fmt,
            "value": self.value
        }
        return result

    @classmethod
    def from_json(cls, data):
        m = inverse(cls.TYPE_NAME_MAP)
        type_ = m[data['type']]
        from_time = None
        to_time = None

        if data['from']:
            from_time = datetime.strptime(data['from'], cls.TIME_FORMAT)

        if data['to']:
            to_time = datetime.strptime(data['to'], cls.TIME_FORMAT)

        return cls(
            mark_type=type_,
            value=data['value'],
            _from_time=from_time,
            _to_time=to_time
        )

    def time_points(self):
        return self.from_time, self.to_time

    def validate(self):
        assert self.from_time < self.to_time, "from_time must be less than to_time"


class DayOfWeek(TimeMark):
    @property
    def day_of_week(self):
        return DOW.index(self.value.title())

    def time_points(self, dt=None):
        assert dt, "date must be provided"
        assert isinstance(dt, date), \
            "expected instance of datetime.date, got %s" % type(dt)

        from_time, to_time = super(DayOfWeek, self).time_points()
        return combine(dt, from_time), combine(dt, to_time)

    def validate(self):
        super(DayOfWeek, self).validate()
        assert self.value.title() in set(DOW), "improper day of week value"


class PeriodicDate(TimeMark):
    @property
    def current_year(self):
        return datetime.utcnow().year

    def date(self, year=None):
        assert year is None or isinstance(year, int), type(year)
        dt = datetime.strptime(self.value, self.PERIODIC_DATE_FORMAT)
        return date(year or self.current_year, dt.month, dt.day)

    def time_points(self, year=None):
        from_time, to_time = super(PeriodicDate, self).time_points()
        dt = self.date(year)

        return combine(dt, from_time), combine(dt, to_time)

    def validate(self):
        super(PeriodicDate, self).validate()
        self.date()


class StaticDate(TimeMark):
    def date(self):
        return datetime.strptime(self.value, self.STATIC_DATE_FORMAT).date()

    def time_points(self):
        from_time, to_time = super(StaticDate, self).time_points()
        dt = self.date()

        return combine(dt, from_time), combine(dt, to_time)

    def validate(self):
        super(StaticDate, self).validate()
        self.date()


TimeMarkField = fields.EmbeddedDocumentField(TimeMark)


class WorkTimeMixin(object):
    time_zone = fields.StringField(db_field='tzn', default='UTC')
    off_time_schedule = fields.ListField(TimeMarkField, db_field='otse')

    @property
    def tz(self):
        tz = pytz.UTC
        if self.time_zone:
            try:
                tz = pytz.timezone(self.time_zone)
            except pytz.UnknownTimeZoneError:
                pass
        return tz

    def filter_time_marks(self, mark_type, group=False):
        result = [tm for tm in self.off_time_schedule if tm.mark_type == mark_type]
        if not group:
            return result

        grouped = defaultdict(list)
        for tm in result:
            grouped[tm.value].append(tm)
        return grouped

    @staticmethod
    def as_tz(d, tz):
        if d.tzinfo:
            d = d.astimezone(tz)
        else:
            d = tz.fromutc(d)
        return tz.normalize(d)

    def generate_time_line(self, d1, d2):
        start = self.as_tz(d1, self.tz)
        end = self.as_tz(d2, self.tz)
        localize = lambda tp: self.tz.localize(tp)

        def to_bounds(dt):
            if dt < start:
                return start
            if dt > end:
                return end
            return dt

        dows_group = self.filter_time_marks(TimeMark.DAY_OF_WEEK, group=True)
        dows_group = {DOW.index(day_of_week): tms for day_of_week, tms in dows_group.items()}

        periodic_dates = [tm for tm in self.filter_time_marks(TimeMark.PERIODIC_DATE)
                          if tm.date(year=start.year) >= start.date()
                          and tm.date(year=end.year) <= end.date()]

        static_dates = [tm for tm in self.filter_time_marks(TimeMark.STATIC_DATE)
                        if start.date() <= tm.date() <= end.date()]

        def _gen(from_, to_):
            while from_ < to_:
                dow = from_.weekday()
                if dow in dows_group:
                    for tm in dows_group[dow]:
                        yield tm.time_points(from_.date())

                for tm in periodic_dates:
                    yield tm.time_points(year=from_.year)

                for tm in static_dates:
                    yield tm.time_points()

                from_ = from_ + timedelta(days=1)

        for (tp1, tp2) in _gen(start, end):
            yield to_bounds(localize(tp1)), 1
            yield to_bounds(localize(tp2)), -1

    def generate_intervals(self, d1, d2):
        edge_sum = 0
        start = None

        for (tp, edge_mark) in sorted(
                self.generate_time_line(d1, d2), key=itemgetter(0)):
            if edge_sum == 0:
                start = tp
            edge_sum += edge_mark
            if edge_sum == 0:
                interval = dates_diff(start, tp)
                yield interval

    def schedule_aware_dates_diff(self, d1, d2):
        return dates_diff(d1, d2) - sum(self.generate_intervals(d1, d2))