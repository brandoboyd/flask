import pytz
from flask import request, jsonify
from flask.views import MethodView

from solariat_bottle.app import app
from solariat_bottle.db.account import Account
from solariat_bottle.utils.decorators import admin_required
from solariat_bottle.db.work_time import TimeMark


class AccountScheduleView(MethodView):
    """Get/Set offline hours and time zone.
    Used in account's response time reports settings UI.
    """
    url_rule = '/account/<account_id>/schedule/json'
    methods = ['GET', 'POST']

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        view = super(AccountScheduleView, cls).as_view(name, *class_args, **class_kwargs)
        return admin_required(view)

    def dispatch_request(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        account_id = kwargs.pop('account_id', None)

        try:
            self.account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            result = dict(ok=False, error="Account not found")
            return jsonify(result)

        try:
            result = super(AccountScheduleView, self).dispatch_request(*args, **kwargs)
        except Exception as exc:
            result = dict(ok=False, error=unicode(exc))
        return jsonify(result)

    def get(self):
        return dict(ok=True,
                    time_marks=map(TimeMark.to_json, self.account.off_time_schedule),
                    time_zone=self.account.time_zone)

    def post(self):
        from solariat_bottle.utils.views import Parameters, Param

        is_timezone = lambda tz_str: tz_str in pytz.all_timezones_set

        params = Parameters(
            Param('time_zone', basestring, is_timezone, Param.REQUIRED),
            Param('time_marks', list, Param.UNCHECKED, Param.REQUIRED)
        )
        params.update(request.json)
        params.check()

        #params = params.as_dict()
        params = dict((p.name, p.value) for p in params)
        self.account.time_zone = params['time_zone']
        try:
            self.account.off_time_schedule = map(
                TimeMark.from_json, params['time_marks'])
        except KeyError:
            app.logger.exception(
                "Cannot parse time marks: %s", params['time_marks'])
            raise TypeError("Bad time mark")

        self.account.save()
        return self.get()


app.add_url_rule(AccountScheduleView.url_rule,
                 view_func=AccountScheduleView.as_view('account_schedule'))


@app.route('/country_timezones/json')
def list_country_timezones():
    """Returns countries and timezones listed by countries.
        {ok: true,
         country_names: {
            "BD": "Bangladesh",
            ...
            },
         country_timezones: {
            "BD": ["Asia/Dhaka"],
            ...
        }}
    """
    return jsonify(
        ok=True,
        country_names=dict(pytz.country_names),
        country_timezones=dict(pytz.country_timezones))


@app.route('/timezones/json')
def list_timezones():
    """Returns timezones with offsets
    {
        ok: true,
        common_timezones: {'timezone name': ['UTC offset', 'DST offset'], ...}
    }
    """
    from datetime import datetime
    utc_now = datetime.utcnow()

    tzs = pytz.common_timezones

    def get_offset(tz):
        d = pytz.timezone(tz).fromutc(utc_now)
        return d.utcoffset().total_seconds(), d.dst().total_seconds()

    return jsonify(
        ok=True,
        common_timezones=dict(zip(tzs, map(get_offset, tzs))))