from itertools import product

from solariat.db                    import fields
from solariat_bottle.db.speech_act         import SpeechActMap
from solariat_bottle.db.channel_trends     import ChannelTrendsManager, make_lang_features
from solariat_bottle.db.channel_stats_base import (
    ChannelTopicsBase, ChannelTrendsBase, ALL_INTENTIONS_INT)

from solariat_bottle.utils.stats      import seq_types
from solariat.utils.timeslot   import decode_timeslot, Timeslot
from solariat_nlp.utils.topics import is_iterable
from solariat_bottle.utils.id_encoder import (
    get_status_code, get_intention_id, ALL_TOPICS)

from solariat.utils.lang.support import get_lang_id


class ChannelTopicTrendsManager(ChannelTrendsManager):
    # The possible fields we might group by, and corresponding mongo ids
    group_by_ids = {"intention": "$es.in", "topic": "$tc", "status": "$ss",
                    "agent": "$es.at", "lang": "$es.le", "time": "$ts"}

    def filter_topics(self, topic_pairs):
        """ Constructs a mongo query which checks for ANY($or) of the given topic/leaf pairs.
        :param topic_pairs: list of pairs (<topic:str>, <is_leaf:bool>)
        :returns: a mongo query dictionary """
        assert topic_pairs, "Terms list should not be empty. Use ALL_TOPICS if no topic constrains." # noqa
        queries = []
        for topic, is_leaf in topic_pairs:
            queries.append({"tc": topic, "es.if": is_leaf})

        if len(queries) > 1:
            return {"$or": queries}
        else:
            return queries[0]

    def sum_group_by_query(self, group_by_field, plot_by='time', plot_type='topics'):
        """ Based on a field we want to group by, the plot type and the attribute
        we are plotting by, return a group mongo aggregation query. """
        query = super(ChannelTopicTrendsManager, self).sum_group_by_query(group_by_field, plot_by, plot_type)
        # TODO: dudarev: remove missed-calls from here
        if plot_type in ('topics', 'missed-posts'):
            query.update({"count": {"$sum": "$es.tt"}})
        return query

    def construct_filter_query(self, intention_ids, statuses, agents, languages):
        assert intention_ids or statuses or agents or languages, "Filter parameters must be defined"
        query = super(ChannelTopicTrendsManager, self).construct_filter_query(statuses, agents, languages)
        if intention_ids:
            query["es.in"] = {"$in": intention_ids}

        return query

    def get_id_intervals(self, channel, from_ts, to_ts, topic, status):
        "Get (`from_id`, `to_id`) parameters for a channel `channel`"
        return (ChannelTopicTrends.make_id(channel, from_ts, topic, status),
                ChannelTopicTrends.make_id(channel, to_ts,   topic, status))

    def by_time_span(self, channel=None, from_ts=None, to_ts=None, topic_pairs=None,
                     intentions=None, statuses=None, agents=None,
                     languages=None, group_by='topic',
                     plot_by='time', plot_type=None, no_transform=False):
        """
        :param channel: can be a string or a sequence
        :param from_ts: starting timeslot
        :param to_ts: end timeslot
        :param group_by: the type of grouping we are doing for aggregation
        :param topic_pairs: list of pairs (<topic:str>, <is_leaf:bool>)
        :param statuses: list of <status:int|str>
        :param agents: list of <User>, where each user should have .agent_id != 0
        :param languages: list of language codes or ids
        :param group_by: <str:"topic"|"intention"|"status"|"agent">

        :returns: stats by time span
        """
        agents = self.preprocess_agents(agents, group_by, channel)

        if statuses:
            statuses = is_iterable(statuses) and statuses or [statuses]
            statuses = map(get_status_code, statuses)
        else:
            statuses = SpeechActMap.STATUS_NAME_MAP.keys()

        intention_ids = map(get_intention_id, intentions or []) or [ALL_INTENTIONS_INT]
        topic_pairs = topic_pairs or [[ALL_TOPICS, False]]
        languages = map(get_lang_id, languages or [])

        from_ts = Timeslot(from_ts).timeslot
        to_ts = Timeslot(to_ts or from_ts).timeslot

        or_query = []
        for (topic, _), status in product(topic_pairs, statuses):
            # channel can be a string or a sequence
            if isinstance(channel, seq_types):
                for c in channel:
                    from_id, to_id = self.get_id_intervals(c, from_ts, to_ts, topic, status)
                    or_query.append({"_id": {"$gte": from_id, "$lte": to_id}})
            else:
                from_id, to_id = self.get_id_intervals(channel, from_ts, to_ts, topic, status)
                or_query.append({"_id": {"$gte": from_id, "$lte": to_id}})

        if len(or_query) == 1:
            indexed_match_query = or_query[0]
        else:
            indexed_match_query = {"$or": or_query}

        initial_pipeline = [
            {"$match": indexed_match_query}
        ]

        match_query = {}
        if plot_type:
            match_query = {"$and": [
                self.filter_topics(topic_pairs),
                self.construct_filter_query(intention_ids, statuses, agents, languages)]}
        pipeline = self.assemble_pipeline(initial_pipeline, match_query, plot_type, plot_by, group_by)
        res = self.execute_pipeline(pipeline)

        if not res['ok']:
            error_msg = "Aggregate error=%s" % res
            #LOGGER.error("%s pipeline=%s", error_msg, pformat(pipeline))
            return {'ok': False, 'error': error_msg}

        features = {'agent': [(u.agent_id, u) for u in (agents or [])],
                    'intention': intention_ids,
                    'topic': topic_pairs,
                    'status': statuses,
                    'lang': make_lang_features(languages),
                    'time': None}[group_by]
        return self.postprocess_results(res, pipeline, no_transform, plot_type, from_ts,
                                        to_ts, group_by, plot_by, features)


class ChannelTopicTrends(ChannelTopicsBase, ChannelTrendsBase):
    """
    Each document tracks stats of a specific channel-term pair during
    a specific timeslot (hours, days and months).
    In addition to what's in ChannelTrends has status, topic, intention.
    """
    manager = ChannelTopicTrendsManager

    topic          = fields.StringField(db_field='tc')
    status         = fields.NumField(db_field='ss')
    embedded_stats = fields.ListField(fields.EmbeddedDocumentField('ExtendedEmbeddedStats'), db_field='es')

    indexes = [('time_slot', ), ('channel_ts', ), ('channel_ts', 'topic')]

    def compute_increments(self, is_leaf=True, intention_ids=None, agent=None, lang_id=None, inc_dict={}, n=1):
        """ Compute requred increments to embeded stats for this stat instance. """
        update_dict = {k: n * v for k,v in inc_dict.iteritems()}
        self.update_embedded_stats(intention_ids, is_leaf, agent, lang_id, update_dict)

    @classmethod
    def increment(cls, channel=None, time_slot=None, topic=None, status=None,
                  is_leaf=True, intention_ids=None, agent=None, lang_id=None,
                  inc_dict={}, n=1):
        """Deprecated
        """
        assert channel is not None and topic is not None and intention_ids is not None \
               and status is not None and time_slot is not None, vars()

        stats = cls(channel=channel, time_slot=time_slot, topic=topic, status=status)
        stats.compute_increments(is_leaf, intention_ids, agent, lang_id, inc_dict, n)

        stats.upsert()
        return stats

    def __repr__(self):
        channel_num, topic_hash, status, time_slot = self.unpacked
        dt_value, dt_level = decode_timeslot(time_slot)

        return '<%s id=%s channel=%s timeslot=%s %s status=%s>' % (
            self.__class__.__name__,
            self.id,
            channel_num,
            dt_value.strftime('%Y%m%d.%H'),
            dt_level,
            status
        )
