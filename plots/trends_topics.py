from itertools import product

from solariat_bottle.db.channel_stats_base import ALL_INTENTIONS_INT
from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
from solariat_bottle.db.speech_act import SpeechActMap
from solariat_bottle.plots.trends_posts import BasePlotter
from solariat_bottle.plots.utils import aggregate_results_by_label
from solariat_bottle.utils.id_encoder import ALL_TOPICS, get_intention_id
from solariat_bottle.utils.stats import seq_types
from solariat_nlp.sentiment import get_sentiment_by_intention
from solariat_nlp.sa_labels import SATYPE_ID_TO_NAME_MAP


class BaseTopicPlotter(BasePlotter):
    
    group_by_ids = {"intention": "$es.in", "topic": "$tc", "status": "$ss",
                    "agent": "$es.at", "lang": "$es.le", "time": "$ts"}
    model = ChannelTopicTrends
    
    def __init__(self, channel=None, from_ts=None, to_ts=None, topic_pairs=None,
                 intentions=None, statuses=None, agents=None, languages=None, group_by=None,
                 plot_by='time', plot_type=None, no_transform=False):
        super(BaseTopicPlotter, self).__init__(channel=channel, from_ts=from_ts, to_ts=to_ts,
                                               agents=agents, statuses=statuses,
                                               languages=languages, group_by=group_by,
                                               plot_by=plot_by, plot_type=plot_type,
                                               no_transform=no_transform)
        self.group_by = group_by or 'topic'
        self.intention_ids = map(get_intention_id, intentions or []) or [ALL_INTENTIONS_INT]
        self.topic_pairs = topic_pairs or [[ALL_TOPICS, False]]
        
    def sum_group_by_query(self):
        """ Based on a field we want to group by, the plot type and the attribute
        we are plotting by, return a group mongo aggregation query. """
        query = super(BaseTopicPlotter, self).sum_group_by_query()
        query.update({"count": {"$sum": "$es.tt"}})
        return query
   
    def compute_features(self):
        """ Get the features we are plotting by (e.g. time or agent) """
        features = super(BaseTopicPlotter, self).compute_features()
        if features is not None:
            features.update({
                'intention': self.intention_ids,
                'topic': self.topic_pairs
            })
        return features
   
    def get_feature_key(self, feature):
        """ Based on the grouping type, get the feature key  """
        if self.group_by in ('topic', 'agent', 'lang'):
            try:
                return feature[0]
            except (TypeError, IndexError):
                return feature
        elif self.group_by == 'intention':
            return int(feature)
        elif self.group_by == 'status':
            return int(feature)
        return 'count'
        
    def get_id_intervals(self, channel, from_ts, to_ts, topic, status):
        "Get (`from_id`, `to_id`) parameters for a channel `channel`"
        return (self.model.make_id(channel, from_ts, topic, status),
                self.model.make_id(channel, to_ts, topic, status))
        
    def compute_initial_pipeline(self):
        or_query = []
        for (topic, _), status in product(self.topic_pairs, self.statuses):
            # channel can be a string or a sequence
            if isinstance(self.channel, seq_types):
                for c in self.channel:
                    from_id, to_id = self.get_id_intervals(
                        c, self.from_ts, self.to_ts, topic, status)
                    or_query.append({"_id": {"$gte": from_id, "$lte": to_id}})
            else:
                from_id, to_id = self.get_id_intervals(
                    self.channel, self.from_ts, self.to_ts, topic, status)
                or_query.append({"_id": {"$gte": from_id, "$lte": to_id}})

        if len(or_query) == 1:
            match_query = or_query[0]
        else:
            match_query = {"$or": or_query}

        initial_pipeline = [{"$match": match_query}]
        return initial_pipeline
    
    def translate_label(self, value, feature_type):
        """ Based on the type of feature we are plotting by,
        get user display names from our encoded values.
        :param value: The actual value returned by query. E.G. 0,1,2 for status
        :param feature_type: Types by which we do plots (e.g. status, topic, intention, agent)"""
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
            # value = pair (agent id, correspondent user instance)
            try:
                return value[1].display_agent
            except:
                return 'all'
        elif feature_type == 'lang':
            return value[1]
        elif feature_type is None:
            return 'count'
        return value    

    def filter_topics(self):
        """ Constructs a mongo query which checks for ANY($or) of the given topic/leaf pairs.
        :param topic_pairs: list of pairs (<topic:str>, <is_leaf:bool>)
        :returns: a mongo query dictionary """
        assert self.topic_pairs, "Terms list should not be empty. Use ALL_TOPICS if no topic constrains."  # noqa
        queries = []
        for topic, is_leaf in self.topic_pairs:
            queries.append({"tc": topic, "es.if": is_leaf})

        if len(queries) > 1:
            return {"$or": queries}
        else:
            return queries[0]
        
    def construct_filter_query(self):
        assert self.intention_ids or self.statuses or self.agents or self.languages, "Filter parameters must be defined"  # noqa
        query = super(BaseTopicPlotter, self).construct_filter_query()
        if self.intention_ids:
            query["es.in"] = {"$in": self.intention_ids}

        return {"$and": [
            query,
            self.filter_topics()
        ]}
    
 
class SentimentPlotter(BaseTopicPlotter):
    
    def __init__(self, channel=None, from_ts=None, to_ts=None, topic_pairs=None,
                 intentions=None, statuses=None, agents=None, languages=None, group_by=None,
                 plot_by='time', plot_type=None, no_transform=False):
        if group_by == 'sentiment':
            self.post_aggregate = True
            group_by = 'intention'
        else:
            self.post_aggregate = False  # TODO: Do we really need this?
        super(SentimentPlotter, self).__init__(channel=channel, from_ts=from_ts, to_ts=to_ts,
                                               agents=agents, statuses=statuses,
                                               languages=languages, group_by=group_by,
                                               plot_by=plot_by, plot_type=plot_type,
                                               no_transform=no_transform)
        self.group_by = group_by or 'topic'
        self.intention_ids = map(get_intention_id, intentions or []) or [ALL_INTENTIONS_INT]
        self.topic_pairs = topic_pairs or [[ALL_TOPICS, False]]
    
    def compute_plotting_data(self):
        """ Construct data for actual plotting. """
        result = super(SentimentPlotter, self).compute_plotting_data()
        if self.post_aggregate and 'list' in result:
            # replace intention labels with sentiments
            for it in result['list']:
                it['label'] = get_sentiment_by_intention(it['label'])
            # re-group results by new labels
            result['list'] = aggregate_results_by_label(result['list'], self.plot_by)
        return result


# class MissedCallsPlotter(BaseTopicPlotter):

    # def sum_group_by_query(self):
    #     """ Overwrite base class with response volume specifics """
    #     query = super(MissedCallsPlotter, self).sum_group_by_query()
    #     query.update({"count": {"$sum": "$es.pt"}})
    #     return query