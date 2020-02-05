# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import operator
import itertools

from solariat_nlp.sa_labels import ALL_INTENTIONS

from solariat_bottle.settings import LOGGER

from solariat_nlp.utils.topics import get_subtopics
from solariat_bottle.utils.stats      import fix_for_neg_value
from solariat.utils.timeslot   import (
    timeslot_to_datetime, decode_timeslot, Timeslot, gen_timeslots)
from solariat_bottle.utils.id_encoder import (
    get_channel_num, get_topic_hash, get_status_code,
    get_intention_id)

from solariat_bottle.db.speech_act         import SpeechActMap
from solariat_bottle.db.channel_trends     import ALL_AGENTS, make_lang_query
from solariat_bottle.db.channel_stats_base import ChannelTopicsBase
from solariat.db.abstract           import (
    Manager)
from solariat.db.fields             import (
    StringField, ListField, NumField, EmbeddedDocumentField)
from solariat.utils.lang.support import get_lang_id


ALL_INTENTIONS_ID = ALL_INTENTIONS.oid
DELIMITER         = '__'


def make_pipeline(match_query, filter_query, limit):
    '''
    Re-use the pipeline templae for computing topics
    '''
    pipeline = [
            {"$match": match_query},
            {"$unwind": "$es"},
            {"$match": filter_query},
            {"$group": {"_id": {"grp": "$tc", "is_leaf": "$es.if"}, "count": {"$sum": "$es.tt"}}},
            {"$project": {"topic": "$_id.grp",
                          "_id": 0,
                          "topic_count": {"$cond": ["$_id.is_leaf", "$count", 0]},
                          "term_count": {"$cond": ["$_id.is_leaf", 0, "$count"]}}},
            {"$group": {"_id": "$topic",
                        "term_count": {"$sum": "$term_count"},
                        "topic_count": {"$sum": "$topic_count"}}},
            {"$match": {"term_count": {"$gt": 0}}},
            {"$sort": {"term_count": -1, "topic_count": -1}},
            {"$limit": limit},
            {"$project": {"topic": "$_id", "topic_count": "$topic_count", "term_count": "$term_count", "_id": 0}}
        ]

    return pipeline


def values_sub(val1, val2):
    return val1 - val2


def percent_inc(val1, val2):
    return 100.0 * (val1 - val2) / (val2 or 1.0)


def get_delta_fn(cloud_type):
    fns = {
        'delta': values_sub,
        'percent': percent_inc
    }
    return fns.get(cloud_type, values_sub)


def calculate_deltas(lst, delta_fn=values_sub):
    if len(lst) < 2:
        return lst

    def _diff(res1, res2, delta_fn):
        get = operator.itemgetter
        groupby = itertools.groupby

        prev = {
            topic: list(grp)[0] for topic, grp in groupby(res1, get('topic'))}
        result = []
        for topic, grp in groupby(res2, get('topic')):
            val = list(grp)[0]
            deltas = {"topic": topic}
            for cnt in ("topic_count", "term_count"):
                deltas[cnt] = delta_fn(
                    val[cnt], prev.get(topic) and prev[topic][cnt] or 0)
            if deltas['term_count'] > 0:
                result.append(deltas)
        return result

    return [_diff(lst[idx], lst[idx + 1], delta_fn)
            for idx in range(len(lst) - 1)]


class ChannelHotTopicsManager(Manager):

    def batch_select(self, channel=None, parent_topic=None, intentions=None,
                     statuses=None, agents=None, languages=None, time_ranges=(), limit=200,
                     cloud_type='delta'):
        results = [
            self.by_time_span(channel, parent_topic, intentions, statuses,
                              agents, languages, from_ts=from_ts, to_ts=to_ts, limit=limit)
            for (from_ts, to_ts) in time_ranges]
        return calculate_deltas(results, delta_fn=get_delta_fn(cloud_type))

    def by_time_span(self, channel=None, parent_topic=None, intentions=None, statuses=None,
                     agents=None, languages=None, from_ts=None, to_ts=None, limit=100):
        # Use the aggregation framework to resolve the counts:
        # match on channel + slot + hashed_parents [+ status [+ intention_type ]]
        # group on topic, sum(leaf or node count?)
        # sort(count, -1)
        # limit(100)
        F = ChannelHotTopics.F

        from_ts = Timeslot(from_ts).timeslot
        to_ts   = Timeslot(to_ts or from_ts).timeslot

        time_range = list(gen_timeslots(from_ts, to_ts, closed_range=False))
        assert len(time_range) <= 7, "Max allowed range is 7 days, got %s %s" % (len(time_range), time_range)

        if len(time_range) == 1:
            time_query = {F("time_slot"): time_range[0]}
        else:
            time_query = {F("time_slot"): {"$in": time_range}}

        channel_num = get_channel_num(channel)
        if parent_topic is None:
            parents = []
        else:
            parents = get_topic_hash(parent_topic)

        intention_ids = set(intentions or [ALL_INTENTIONS_ID])
        intention_ids = map(get_intention_id, intention_ids)

        statuses = set(statuses or SpeechActMap.STATUS_NAME_MAP)
        statuses = map(get_status_code, statuses)
        languages = map(get_lang_id, languages or [])

        match_query_base = {
            F("channel_num")    : channel_num,
            F("status")         : {"$in" : statuses},
            F("hashed_parents") : parents,
        }
        match_query_base.update(time_query)

        agent_ids = [a.agent_id for a in (agents or [])] or [ALL_AGENTS]

        match_query_filters = {
            "es.at": {"$in": agent_ids},
            "es.in": {"$in": intention_ids}
        }
        match_query_filters.update(make_lang_query(languages))

        return self.execute_pipeline(match_query_base, match_query_filters, limit)

    def execute_pipeline(self, match_query_base, match_query_filters, limit):
        # Edge case handling
        if limit == 0:
            return []

        pipeline = make_pipeline(match_query_base, match_query_filters, limit)
        res = self.coll.aggregate(pipeline)

        if res['ok']:
            fix_for_neg_value(res['result'], ['topic_count', 'term_count'], pipeline)
            return res['result']
        else:
            LOGGER.warning(
                'ChannelHotTopics pipeline %s failed with result %s', pipeline, res
            )
            return []

class ChannelHotTopics(ChannelTopicsBase):
    ''' Each document tracks specific topic/term stats during a specific timeslot
        (only days and months are being track, not hours).

        The main purpose of this collection is to keep track of the most frequently
        occuring topics and terms (terms being unigrams, bigrams and trigrams of topics).
    '''
    manager = ChannelHotTopicsManager

    channel_num    = NumField(db_field='cl', required=True)
    topic          = StringField(db_field='tc', required=True)
    hashed_parents = ListField(NumField(), db_field='hp', required=True)  # hashed parent topics <[int]> (they always have one word fewer)
    status         = NumField(db_field='ss', required=True)
    embedded_stats = ListField(EmbeddedDocumentField('ExtendedEmbeddedStats'), db_field='es')

    indexes =      [ ('channel_num', 'time_slot', 'status', 'hashed_parents'), ('gc_counter') ]

    def __init__(self, data=None, **kwargs):
        if data is None:
            self.channel = kwargs.pop('channel', None)
            if self.channel:
                kwargs['channel_num'] = self.channel.counter
            else:
                assert 'channel_num' in kwargs, 'Channel object or channel number must be provided'
                from solariat_bottle.db.channel.base import Channel
                self.channel = Channel.objects.get(counter=kwargs['channel_num'])
        super(ChannelHotTopics, self).__init__(data, **kwargs)

    def compute_increments(self, is_leaf=True, intention_id=None, agent=None, lang_id=None, n=1):
        """ Compute requred increments to embeded stats for this stat instance. """
        update_dict = {'topic_count': n}
        self.update_embedded_stats(intention_id, is_leaf, agent, lang_id, update_dict)

    @classmethod
    def increment(cls, channel=None, time_slot=None, topic=None, status=None,
                  intention_id=None, is_leaf=True, agent=None, lang_id=None, n=1):
        """Deprecated
        """
        assert channel is not None and intention_id is not None \
                and topic is not None and time_slot is not None, vars()
 
        hashed_parents = map(get_topic_hash, get_subtopics(topic))
        #channel_num = get_channel_num(channel)
        stat = cls(channel=channel, time_slot=time_slot, topic=topic, status=status,
                   hashed_parents=hashed_parents)
        stat.compute_increments(is_leaf, intention_id, agent, lang_id, n)
        stat.upsert()
        return stat

    def __repr__(self):
        return '<%s: id=%s channel=%s, topic=%s, hashed_parents=%s, time_slot=%s>' % (
            self.__class__.__name__,
            self.id,
            self.channel_num,
            self.topic,
            self.hashed_parents,
            self.time_slot)

    @property
    def datetime(self):
        return timeslot_to_datetime(self.time_slot)

    @property
    def level(self):
        _, level = decode_timeslot(self.time_slot)
        return level

    def to_dict(self):
        return dict(id=self.id, channel_num=self.channel_num, topic=self.topic,
                    hashed_parents=self.hashed_parents, time_slot=self.time_slot, status=self.status)

