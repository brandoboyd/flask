# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from ..db.channel_stats import ChannelStatsManager
from solariat.db import fields
from solariat.utils.timeslot import (
    now,
    decode_timeslot,
    datetime_to_timeslot,
    TIMESLOT_LEVEL_NAMES
)
from .channel.base import ChannelAuthDocument


def yield_channel_stats(channel, agent, date):
    if date is None:
        date = now()
    for level in TIMESLOT_LEVEL_NAMES:
        time_slot = datetime_to_timeslot(date, level)
        yield ServiceChannelStats(channel=str(channel.id),
                                  time_slot=time_slot,
                                  agent=agent)


class ServiceChannelStatsManager(ChannelStatsManager):
    def outbound_post_received(self, channel, post, agents, stats):
        inc_stats = dict(("inc__%s" % k, v) for k, v in stats.iteritems())
        for agent in agents:
            for stat in yield_channel_stats(channel, agent, post.created_at):
                stat.update(**inc_stats)

    def by_time_span(self, user, channel, start_time=None,
                     end_time=None, level='hour',  **kw):
        agents = kw.pop('agents', [])
        if agents:
            kw['agent__in'] = agents

        return super(ServiceChannelStatsManager, self).by_time_span(user, channel, start_time, end_time, level, **kw)

    def by_time_point(self, user, channel, time_point=None,
                     level='hour', **kw):
        agents = kw.pop('agents', [])
        if agents:
            kw['agent__in'] = agents

        return super(ServiceChannelStatsManager, self).by_time_point(user, channel, time_point, level, **kw)


class ServiceChannelStats(ChannelAuthDocument):
    "Store stats for month, day and hour"
    manager = ServiceChannelStatsManager

    channel = fields.ObjectIdField(required=True,
                                   unique_with='time_slot',
                                   db_field='cl')

    # The time slot is a numeric encoding of elapsed time
    # see utils.timeslot for details
    time_slot = fields.NumField(required=True, db_field="ts")

    agent = fields.NumField(db_field='a',
                            default=0,  # 0 - all agents
                            required=True)

    volume = fields.NumField(default=0, db_field='v')   #number of outbound posts
    latency = fields.NumField(default=0, db_field='l')  #reply delay

    indexes = [('channel', 'time_slot', 'agent')]

    @property
    def average_latency(self):
        """Returns average reply delay in seconds."""

        if self.volume > 0:
            return float(self.latency) / float(self.volume)
        return 0.0

    @property
    def level(self):
        return decode_timeslot(self.time_slot)[1]

    def to_dict(self, fields2show=None):
        result = ChannelAuthDocument.to_dict(self, fields2show)
        result['level'] = self.level
        return result

    def __str__(self):
        return "%s" % self.time_slot

    @property
    def _query(self):
        query = self.__class__.get_query(
            channel=str(self.channel),
            time_slot=self.time_slot,
            agent=self.agent)
        return query

    def update(self, **kwargs):
        document = {}
        for arg in kwargs:
            (operation, field) = arg.split('__', 1)
            operation = '$'+operation
            if operation not in document:
                document[operation] = {}

            db_field = self.fields[field].db_field
            document[operation][db_field] = kwargs[arg]

        self.objects.coll.update(self._query, document, multi=False, upsert=True)

    def reload(self):
        source = ServiceChannelStats.objects.find_one(
            time_slot=self.time_slot,
            channel=self.channel,
            agent=self.agent)

        self.data = source.data
