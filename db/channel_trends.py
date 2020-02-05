# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from collections import defaultdict
from itertools   import product
from datetime    import datetime
from pprint      import pformat

import pymongo

from solariat_bottle.settings import LOGGER

# utils.stats imports are later due to circular imports issues
from solariat.db          import fields
from solariat.db.abstract import Manager

from solariat_bottle.db.speech_act         import SpeechActMap
from solariat_bottle.db.channel_stats_base import (
    ALL_AGENTS, to_python, CountDict, EmbeddedStats, ChannelTrendsBase)

from solariat.utils.timeslot   import (
    decode_timeslot, timeslot_to_timestamp_ms, gen_timeslots, Timeslot)
from solariat_bottle.utils.id_encoder import (
    pack_short_stats_id, unpack_short_stats_id, ALL_TOPICS, get_status_code)
from solariat_bottle.utils.post       import get_service_channel
from solariat_bottle.utils.stats      import seq_types
from solariat_nlp.utils.topics import is_iterable
from solariat.utils.lang.support import Lang, get_lang_code


# Project document into average response time in *seconds*
PROJECT_DIVIDE_SECONDS = {
    "count": {
        "$divide": ['$sum_rt', '$sum_rv'],
    }
}

# Project document into average response time in *hours*
SECONDS_PER_HOUR     = 3600
PROJECT_DIVIDE_HOURS = {
    "count": {
        "$add": [
            {"$divide": [
                {"$subtract":
                    ['$sum_rt',
                        {"$mod": [
                            '$sum_rt',
                            {"$multiply": [SECONDS_PER_HOUR, "$sum_rv"]}
                        ]}
                    ]
                },
                {"$multiply": [SECONDS_PER_HOUR, "$sum_rv"]}
            ]},
            {"$cond":
                [
                    {"$eq":
                        [
                            {"$mod":
                                [
                                    '$sum_rt',
                                    {"$multiply":
                                        [SECONDS_PER_HOUR, "$sum_rv"]}
                                ]
                            },
                            0.0
                        ]
                    }, 0, 1]}
        ]
    }
}


def translate_label(value, feature_type):
    """ Based on the type of feature we are plotting by,
    get user display names from our encoded values.
    :param value: The actual value returned by query. E.G. 0,1,2 for status
    :param feature_type: Types by which we do plots (e.g. status, topic, intention, agent)"""
    from solariat_nlp.sa_labels import SATYPE_ID_TO_NAME_MAP
    from ..db.speech_act import SpeechActMap

    if feature_type == 'intention':
        return SATYPE_ID_TO_NAME_MAP[str(value)]

    elif feature_type == 'status':
        return SpeechActMap.STATUS_NAME_MAP[value]

    elif feature_type == 'topic':
        if len(value) == 2:  # (term, is_leaf)
            topic = value[0]
        else:
            topic = value
        if topic == ALL_TOPICS:
            return 'all'
        return topic

    elif feature_type == 'agent':
        #value = pair (agent id, correspondent user instance)
        try:
            return value[1].display_agent
        except:
            return 'all'

    elif feature_type == 'lang':
        return value[1]

    elif feature_type == None:
        return 'count'
    return value


def transform(data, from_ts=None, to_ts=None, group_by='topic',
              plot_by='time', plot_type='topics', features=None):
    """ Transforms aggregation data to plot data """
    def group_by_timeslot_label(data):
        by_timeslot_label = defaultdict(dict)
        for item in data:
            time_slot = item['_id'].get('ts', 0)
            label = item['_id'].get('grp', 'count')
            by_timeslot_label[time_slot][label] = item

        return by_timeslot_label

    def _get_count(stats_data, stat_type='count'):
        return stats_data.get(stat_type, 0)

    def get_feature_key(feature):
        if group_by in ('topic', 'agent', 'lang'):
            try:
                return feature[0]
            except (TypeError, IndexError):
                return feature
        elif group_by in ('intention', 'status'):
            return int(feature)
        return 'count'

    def to_client_tz_offset(js_timestamp, tz_offset):
        if tz_offset:
            js_timestamp -= 1000.0 * tz_offset * 60
        return js_timestamp

    def get_time_data(groups, y_axis):
        total_counts = defaultdict(int)
        total_items = defaultdict(int)
        data = defaultdict(list)

        for slot in gen_timeslots(from_ts, to_ts):
            timestamp = timeslot_to_timestamp_ms(slot)
            features_data = groups.get(slot, {})

            for feature in y_axis:
                feature_key = get_feature_key(feature)

                if features_data.get(feature_key):
                    count = _get_count(features_data[feature_key])

                    total_counts[feature_key] += count
                    total_items[feature_key] += 1
                    data[feature_key].append([timestamp, count])
                else:
                    data[feature_key].append([timestamp, 0])

        if plot_type == 'response-time':
            # return average as result
            result_counts = defaultdict(float)
            for key, value in total_counts.iteritems():
                if total_items.get(key):
                    result_counts[key] = round(value / total_items[key], 2)
                else:
                    result_counts[key] = 0
        else:
            result_counts = total_counts
        return data, result_counts

    results = {}
    level = Timeslot(from_ts).level
    assert level == Timeslot(to_ts).level

    if plot_by == 'time':
        groups = group_by_timeslot_label(data)
        y_axis = features or ['count']
        data, counts = get_time_data(groups, y_axis)

        for f in y_axis:
            feature = get_feature_key(f)
            if not counts.get(feature):
                continue
            data_series = {
                "label": translate_label(f, group_by),
                "data": data.get(feature, []),
                "level": level,
                "count": counts.get(feature, 0)
            }
            if group_by == 'topic':
                data_series['topic_type'] = f[1] and 'leaf' or 'node'
            results[feature] = data_series
    elif plot_by == 'distribution':
        groups = group_by_timeslot_label(data)[0]
        y_axis = features or groups.keys()

        idx = 0
        for f in y_axis:
            feature = get_feature_key(f)
            idx += 1
            if feature not in groups:
                continue
            count = _get_count(groups[feature])
            data_series = {
                "label": translate_label(f, group_by),
                "data": [[idx * 2, count]]
            }
            if group_by == 'topic':
                data_series['topic_type'] = f[1] and 'leaf' or 'node'

            results[feature] = data_series

    return {
        "ok": True,
        "level": level,
        "list": results.values()
    }


def make_lang_query(languages, field='es.le'):
    q = {}
    if languages:
        if Lang.EN in languages:
            # special case for EN to avoid db upgrade
            q.update({"$or": [
                {field: {"$exists": False}},
                {field: {"$in": languages}}
            ]})
        else:
            q[field] = {"$in": languages}
    else:
        q.update({"$or": [
            {field: {"$exists": False}},
            {field: Lang.ALL}
        ]})
    return q


def make_lang_features(languages):
    return [(lang_id, get_lang_code(lang_id)) for lang_id in (languages or [])]


class ReportsEmbeddedStats(EmbeddedStats):
    # Additional metrics for Reports
    response_volume = fields.NumField(db_field='rv', default=0)
    response_time   = fields.NumField(db_field='rt', default=0)
    post_count = fields.NumField(db_field='pt', default=0)

    countable_keys = ['response_volume', 'response_time', 'post_count']


class ChannelTrendsManager(Manager):
    # The possible fields we might group by, and corresponding mongo ids
    group_by_ids = {"agent": "$es.at", "lang": "$es.le", "time": "$ts"}

    def sum_group_by_query(self, group_by_field, plot_by='time', plot_type=None):
        """ Based on a field we want to group by, the plot type and the attribute
        we are plotting by, return a group mongo aggregation query. """
        if group_by_field is None:
            query = {"_id": {}}
        else:
            _id = self.group_by_ids[group_by_field]
            query = {
                "_id": {"grp": _id},
            }
        if plot_type == 'response-time':
            query.update({
                "sum_rt": {"$sum": "$es.rt"},  # sum of response time
                "sum_rv": {"$sum": "$es.rv"}   # sum of response volume
            })
        elif plot_type == 'response-volume':
            query.update({"count": {"$sum": "$es.rv"}})
        elif plot_type == 'inbound-volume' or plot_type == 'missed-posts':
            query.update({"count": {"$sum": "$es.pt"}})

        if plot_by == 'time':  # add time slot to group by
            query["_id"]["ts"] = "$ts"

        return query

    def construct_filter_query(self, statuses, agents, languages):
        query = {}
        if agents:
            query["es.at"] = {"$in": tuple({u.agent_id for u in agents})}
        else:
            query["es.at"] = ALL_AGENTS
        if statuses:
            query["ss"] = {"$in": statuses}
        query.update(make_lang_query(languages, field='es.le'))
        return query

    def preprocess_agents(self, agents, group_by, channel):
        """ If we are plotting by agent, we need the actual list of agents instead of empty list
        since we are using that for the y_axis `channel` can be either a string or a sequense """
        if not agents and group_by == 'agent':
            if isinstance(channel, seq_types):
                sc = get_service_channel(list(channel)[0])
            else:
                sc = get_service_channel(channel)
            agents = sc and sc.agents or []
            # filter out common users, keep only agents
            agents = [a for a in agents if a.agent_id != 0]
        return agents

    def assemble_pipeline(self, initial_pipeline, match_query, plot_type, plot_by, group_by):
        """ Given an initial pipeline and match query, depending on the plot_type and
        what we are plotting / groupping by, assemble the final pipeline query. """
        if plot_type:  # Case for ui. Otherwise only $match results will be returned
            # filter by intentions, statuses, agents
            initial_pipeline.extend([
                {"$unwind": '$es'},
                {"$match": match_query},
                {"$group": self.sum_group_by_query(group_by, plot_by, plot_type)}
            ])

            if plot_type == 'response-time':
                if plot_by == 'time':
                    project_divide = PROJECT_DIVIDE_SECONDS
                else:
                    project_divide = PROJECT_DIVIDE_HOURS

                initial_pipeline.append({"$project": project_divide})

                if plot_by == 'distribution' and group_by == 'time':
                    # Group by average response time in hours
                    initial_pipeline.append({"$group": {
                        "_id": {"grp": "$count"},
                        "count": {"$sum": 1}}
                    })
        return initial_pipeline

    def execute_pipeline(self, pipeline):
        """ Execute aggregation pipeline, handle any division by zero and return result """
        start_query_time = datetime.now()
        try:
            res = self.coll.aggregate(pipeline)
        except pymongo.errors.OperationFailure, ex:
            # do not log a warning if this is divide by zero error
            if not 'divide by zero' in str(ex):
                LOGGER.warning("Mongo operation failed with error: %s. Returning empty list.", ex)
            res = {u'ok': 1.0, u'result': []}

        LOGGER.debug(
            "ChannelTrendsManager.by_time_span Pipeline=\n%s\nAggregated in %s sec.",
            pformat(pipeline), datetime.now()-start_query_time
        )
        return res

    def postprocess_results(self, result, pipeline, no_transform, plot_type,
                            from_ts, to_ts, group_by, plot_by, features):
        """
        Do any postprocessing on the result returned from mongo in order to
        get the 'plottable' data.
        """
        if not result['ok']:
            error_msg = "Aggregate error=%s" % result
            #LOGGER.error("%s pipeline=%s", error_msg, pformat(pipeline))
            return {'ok':False, 'error':error_msg}
        else:
            from ..utils.stats import remove_zero_counts, fix_for_neg_value
            result['result'] = remove_zero_counts(result['result'])
            fix_for_neg_value(result['result'], ['count'], pipeline)

            if no_transform:
                return result['result']

            if plot_type is None:
                return map(self.doc_class, result['result'])

            return transform(result['result'], from_ts=from_ts, to_ts=to_ts, group_by=group_by,
                             plot_by=plot_by, plot_type=plot_type, features=features)

    def get_id_intervals(self, channel, status, from_ts, to_ts):
        "Get (`from_id`, `to_id`) parameters for a channel `channel`"
        return (ChannelTrends.make_id(channel, status, from_ts),
                ChannelTrends.make_id(channel, status, to_ts))

    def by_time_span(self, channel=None, from_ts=None, to_ts=None, agents=None,
                     statuses=None, languages=None,
                     group_by='agent', plot_by='time', plot_type=None, no_transform=False):
        """
        :param channel: can be a string or a sequence
        :param from_ts: starting timeslot
        :param to_ts: end timeslot
        :param group_by: the type of grouping we are doing for aggregation

        :returns: stats by time span
        """
        agents = self.preprocess_agents(agents, group_by, channel)

        if statuses:
            statuses = is_iterable(statuses) and statuses or [statuses]
            statuses = map(get_status_code, statuses)
        else:
            statuses = SpeechActMap.STATUS_NAME_MAP.keys()

        from_ts = Timeslot(from_ts).timeslot
        to_ts = Timeslot(to_ts or from_ts).timeslot

        or_query = []
        for status in statuses:
            # channel can be a string or a sequence
            if isinstance(channel, seq_types):
                for c in channel:
                    from_id, to_id = self.get_id_intervals(c, status, from_ts, to_ts)
                    or_query.append({"_id": {"$gte": from_id, "$lte": to_id}})
            else:
                from_id, to_id = self.get_id_intervals(channel, status, from_ts, to_ts)
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
            match_query = self.construct_filter_query(statuses, agents, languages)
        pipeline = self.assemble_pipeline(initial_pipeline, match_query, plot_type, plot_by, group_by)
        res = self.execute_pipeline(pipeline)

        if group_by is None:
            features = None
        else:
            features = {'agent': [(u.agent_id, u) for u in (agents or [])],
                        'lang': make_lang_features(languages),
                        'time': None}[group_by]
        return self.postprocess_results(res, pipeline, no_transform, plot_type, from_ts,
                                        to_ts, group_by, plot_by, features)


class ChannelTrends(ChannelTrendsBase):
    """
    Each document tracks stats of a specific channel-term pair during
    a specific timeslot (hours, days and months).
    In contrast with ChannelTopicTrends that have extra metrics.
    """
    manager = ChannelTrendsManager

    status = fields.NumField(db_field='ss')
    embedded_stats = fields.ListField(fields.EmbeddedDocumentField('ReportsEmbeddedStats'), db_field='es')

    def __init__(self, data=None, **kwargs):
        super(ChannelTrends, self).__init__(data, **kwargs)

    def channel_ts_from_id(self, data_id):
        """ From a document id compute a channel ts """
        channel_num, _, time_slot = unpack_short_stats_id(to_python(data_id))
        return self.make_channel_ts(channel=channel_num, time_slot=time_slot)

    def compute_increments(self, agent=None, lang_id=None, inc_dict={}, n=1):
        """ Compute requred increments to embeded stats for this stat instance. """
        update_dict = {k: n * v for k,v in inc_dict.iteritems()}  # multiply inc values by n (inc/dec factor)
        self.update_embedded_stats(agent, lang_id, update_dict)

    @classmethod
    def increment(cls, channel=None, time_slot=None,
                  agent=None, lang_id=None, inc_dict={}, n=1):
        assert channel is not None and time_slot is not None, vars()

        stats = cls(channel=channel, time_slot=time_slot)
        stats.compute_increments(agent, lang_id, inc_dict, n)

        stats.upsert()
        return stats

    def __repr__(self):
        channel_num, time_slot = self.unpacked
        dt_value, dt_level = decode_timeslot(time_slot)

        return '<%s id=%s channel=%s timeslot=%s %s>' % (
            self.__class__.__name__,
            self.id,
            channel_num,
            dt_value.strftime('%Y%m%d.%H'),
            dt_level
        )

    @property
    def _query(self):
        if not self.id:
            self.id = self.__class__.make_id(self.channel, self.status, self.time_slot)

        data = self.data.copy()
        data.pop(self.name2db_field('embedded_stats'), None)
        return data

    def compute_new_embeded_stats(self):
        new_embedded_stats = []
        for (agent, lang_id), inc_dict in self.embedded_dict.items():
            # For each in memory cached items, create actual embedded
            # stats instances, and increment stat values.
            es = self.EmbeddedStatsCls(agent=agent, language=lang_id)
            for stat, value in inc_dict.items():
                es.inc(stat, value)
            new_embedded_stats.append(es)
        return new_embedded_stats

    def update_embedded_stats(self, agent, lang_id, inc_dict):
        """
        Generate a dictionary of the form: { (agent) : inc_dict }
        This can then be used to incrementally upgrade the inc_dict for this pair in
        memory and do the save to the database in once call.
        """
        if not hasattr(self, 'embedded_dict'):
            self.embedded_dict = defaultdict(lambda: CountDict({}))

        agents = {ALL_AGENTS}
        if agent:
            agents.add(agent)

        languages = {Lang.ALL}
        if lang_id is not None:
            languages.add(lang_id)

        for key in product(agents, languages):
            self.embedded_dict[key].update(inc_dict)

    @classmethod
    def make_id(cls, channel, status, time_slot):
        channel_num = channel.counter

        assert isinstance(
            channel_num, (int, long)), \
           'channel.counter must be an integer: %r' % channel_num # noqa
        to_binary = fields.BytesField().to_mongo
        return to_binary(pack_short_stats_id(channel_num, status, time_slot))


    @property
    def unpacked(self):
        return unpack_short_stats_id(self.id)


    def unpack(self):
        self.channel_num, self.time_slot = self.unpacked

