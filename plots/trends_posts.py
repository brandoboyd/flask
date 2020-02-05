from collections import defaultdict

from solariat_bottle.db.channel_stats_base import ALL_AGENTS
from solariat_bottle.db.channel_trends import (ChannelTrends, make_lang_query, make_lang_features,
                                               PROJECT_DIVIDE_SECONDS, PROJECT_DIVIDE_HOURS)
from solariat_bottle.db.speech_act import SpeechActMap
from solariat_bottle.utils.id_encoder import get_status_code
from solariat_bottle.utils.post import get_service_channel
from solariat_bottle.utils.stats import seq_types, remove_zero_counts, fix_for_neg_value
from solariat_nlp.utils.topics import is_iterable
from solariat.utils.timeslot import (timeslot_to_timestamp_ms,
                                            gen_timeslots, Timeslot)
from solariat.utils.lang.support import get_lang_id

# In normal 'time' grouping, we use timeslots to compute counts on graph, in distribution
# based views we do not, so this is just a timeslot we use to count when doing
# distribution based plotting
DISTRIBUTION_TS = -1


class BasePlotter(object):
    # The possible fields we might group by, and corresponding mongo fields
    group_by_ids = {"agent": "$es.at", "lang": "$es.le", "time": "$ts"}
    model = ChannelTrends
    
    def __init__(self, channel=None, from_ts=None, to_ts=None, agents=None, statuses=None, languages=None,
                 group_by='agent', plot_by='time', plot_type=None, no_transform=False, **kwargs):
        self.channel = channel
        self.from_ts = Timeslot(from_ts).timeslot
        self.to_ts = Timeslot(to_ts or from_ts).timeslot
        self.agents = self.ensure_agents(agents, group_by, channel)
        self.statuses = self.ensure_statuses(statuses)
        self.languages = map(get_lang_id, languages or [])
        if group_by not in ('time', 'agent', 'lang'):   # Just in case we get parameter from UI, ignore it
            group_by = None
        self.group_by = group_by
        self.plot_by = plot_by
        self.plot_type = plot_type
        self.no_transform = no_transform
    
    def ensure_statuses(self, statuses):
        """ Make sure we have statuses by which we can filter. """
        if statuses:
            statuses = is_iterable(statuses) and statuses or [statuses]
            statuses = map(get_status_code, statuses)
        else:
            statuses = SpeechActMap.STATUS_NAME_MAP.keys()
        return statuses
    
    def get_id_intervals(self, channel, status, from_ts, to_ts):
        "Get (`from_id`, `to_id`) parameters for a channel `channel`"
        return (self.model.make_id(channel, status, from_ts),
                self.model.make_id(channel, status, to_ts))
    
    def ensure_agents(self, agents, group_by, channel):
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

    def sum_group_by_query(self):
        """ Based on a field we want to group by and the attribute
        we are plotting by, return a group mongo aggregation query. """
        if self.group_by is None:
            query = {"_id": {}}
        else:
            _id = self.group_by_ids[self.group_by]
            query = {"_id": {"grp": _id}}
        if self.plot_by == 'time':  # add time slot to group by
            query["_id"]["ts"] = "$ts"
        return query
            
    def assemble_pipeline(self, initial_pipeline, match_query):
        """ Given an initial pipeline and match query, depending on the plot_type and
        what we are plotting / groupping by, assemble the final pipeline query. """
        # filter by intentions, statuses, agents
        initial_pipeline.extend([
            {"$unwind": '$es'},                         # expand embedded_stats
            {"$match": match_query},
            {"$group": self.sum_group_by_query()}
        ])
        return initial_pipeline
        
    def compute_features(self):
        """ Get the features we are plotting by (e.g. time or agent) """
        if self.group_by is None:
            features = None
        else:
            features = {'agent': [(u.agent_id, u) for u in (self.agents or [])],
                        'lang': make_lang_features(self.languages or []),
                        'status': self.statuses,
                        'time': None}
        return features
    
    def construct_filter_query(self):
        """ Basic filter query based on agents and statuses. """
        query = {}
        if self.agents:
            query["es.at"] = {"$in": tuple({u.agent_id for u in self.agents})}
        else:
            query["es.at"] = ALL_AGENTS
        if self.statuses:
            query["ss"] = {"$in": self.statuses}
        query.update(make_lang_query(self.languages))
        return query
    
    def postprocess_results(self, result, pipeline, features):
        """ Do any postprocessing on the result returned from mongo in order to
        get the 'plottable' data. """
        if not result['ok']:
            error_msg = "Aggregate error=%s" % result
            return {'ok': False, 'error': error_msg}
        else:
            result['result'] = remove_zero_counts(result['result'])
            fix_for_neg_value(result['result'], ['count'], pipeline)
            transformed_data = self.transform_data(result['result'], features)
            return transformed_data
        
    def group_by_timeslot_label(self, data):
        """ Transform mongo returned data into groupings by timeslot / label.
        In case no timeslot is found, default to timeslot=DISTRIBUTION_TS, as for distributions.
        """
        by_timeslot_label = defaultdict(dict)
        for item in data:
            time_slot = item['_id'].get('ts', DISTRIBUTION_TS)
            label = item['_id'].get('grp', 'count')
            by_timeslot_label[time_slot][label] = item

        return by_timeslot_label
    
    def get_feature_key(self, feature):
        """ Based on the grouping type, get the feature key  """
        if self.group_by == 'agent':
            # For agents features are (user.agent_id, user) so we can get display name
            # of the actual user
            try:
                return feature[0]
            except (TypeError, IndexError):
                return feature
        return 'count'

    def get_time_data(self, groups, y_axis):
        """ Return data formated in a FLOT specific format; eg. [[time, count], [time, count]]
        so that we can use it for time plots """
        total_counts = defaultdict(int)
        total_items = defaultdict(int)
        data = defaultdict(list)

        for slot in gen_timeslots(self.from_ts, self.to_ts):
            timestamp = timeslot_to_timestamp_ms(slot)
            features_data = groups.get(slot, {})
            for feature in y_axis:
                feature_key = self.get_feature_key(feature)
                if features_data.get(feature_key):
                    count = features_data[feature_key].get('count', 0)
                    total_counts[feature_key] += count
                    total_items[feature_key] += 1
                    data[feature_key].append([timestamp, count])
                else:
                    data[feature_key].append([timestamp, 0])

        return data, total_counts, total_items
    
    def translate_label(self, value, feature_type):
        """ Based on the type of feature we are plotting by,
        get user display names from our encoded values.
        :param value: The actual value returned by query. E.G. 0,1,2 for status
        :param feature_type: Types by which we do plots (e.g. status, topic, intention, agent)"""
        if feature_type == 'status':
            return SpeechActMap.STATUS_NAME_MAP[value]
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
    
    def transform_time_based_plot(self, data, features, level):
        """ Transform data specific for time based plots. """
        results = {}
        groups = self.group_by_timeslot_label(data)
        # In case of time plot, we either have a specific feature list or we
        # just default to the post count.
        y_axis = features or ['count']
        data, counts, _ = self.get_time_data(groups, y_axis)

        for f in y_axis:
            feature = self.get_feature_key(f)
            if not counts.get(feature):
                continue
            data_series = {
                "label": self.translate_label(f, self.group_by),
                "data": data.get(feature, []),
                "level": level,
                "count": counts.get(feature, 0)
            }
            if self.group_by == 'topic':
                data_series['topic_type'] = f[1] and 'leaf' or 'node'
            results[feature] = data_series
        return results
    
    def transform_distribution_plot(self, data, features, level):
        """ Transform data on a format specific for distribution based plots. """
        results = {}
        groups = self.group_by_timeslot_label(data)[DISTRIBUTION_TS]
        # In case of distribution topics, we either use a specific list of features
        # or default to the timeslot/lebel dictionary keys (selected labels)
        y_axis = features or groups.keys()

        idx = 0
        for f in y_axis:
            feature = self.get_feature_key(f)
            idx += 1
            if feature not in groups:
                continue
            count = groups[feature].get('count', 0)
            data_series = {
                "label": self.translate_label(f, self.group_by),
                "data": [[idx * 2, count]]
            }
            if self.group_by == 'topic':
                data_series['topic_type'] = f[1] and 'leaf' or 'node'

            results[feature] = data_series
        return results
    
    def transform_data(self, data, features):
        """ Transform data we got from mongodb on data we can plot in the UI based
        on the features list. """
        level = Timeslot(self.from_ts).level
        assert level == Timeslot(self.to_ts).level
        if self.plot_by == 'time':
            results = self.transform_time_based_plot(data, features, level)
        elif self.plot_by == 'distribution':
            results = self.transform_distribution_plot(data, features, level)
        return {"ok": True, "level": level, "list": results.values()}
    
    def compute_initial_pipeline(self):
        or_query = []
        for status in self.statuses:
            # channel can be a string or a sequence
            if isinstance(self.channel, seq_types):
                for c in self.channel:
                    from_id, to_id = self.get_id_intervals(c, status, self.from_ts, self.to_ts)
                    or_query.append({"_id": {"$gte": from_id, "$lte": to_id}})
            else:
                from_id, to_id = self.get_id_intervals(
                    self.channel, status, self.from_ts, self.to_ts)
                or_query.append({"_id": {"$gte": from_id, "$lte": to_id}})

        if len(or_query) == 1:
            match_query = or_query[0]
        else:
            match_query = {"$or": or_query}
        
        initial_pipeline = [{"$match": match_query}]
        return initial_pipeline
    
    def compute_plotting_data(self):
        """ Construct data for actual plotting. """
        initial_pipeline = self.compute_initial_pipeline()
        match_query = self.construct_filter_query()
        pipeline = self.assemble_pipeline(initial_pipeline, match_query)
        res = self.model.objects.execute_pipeline(pipeline)

        if self.group_by:
            features = self.compute_features()[self.group_by]
        else:
            features = []
        return self.postprocess_results(res, pipeline, features)
    

class ResponseTimePlotter(BasePlotter):

    def assemble_pipeline(self, initial_pipeline, match_query):
        """ Given an initial pipeline and match query, depending on the plot_type and
        what we are plotting / groupping by, assemble the final pipeline query. """
        initial_pipeline = super(ResponseTimePlotter, self).assemble_pipeline(
            initial_pipeline, match_query)
        if self.plot_by == 'time':
            project_divide = PROJECT_DIVIDE_SECONDS
        else:
            project_divide = PROJECT_DIVIDE_HOURS

        project_divide['rv'] = '$sum_rv'
        initial_pipeline.append({"$project": project_divide})

        if self.plot_by == 'distribution' and self.group_by == 'time':
            # Group by average response time in hours
            initial_pipeline.append({"$group": {
                "_id": {"grp": "$count"},
                "count": {"$sum": 1}}
            })
        return initial_pipeline
    
    def sum_group_by_query(self):
        """ Overwrite base class with response time specifics """
        query = super(ResponseTimePlotter, self).sum_group_by_query()
        query.update({
            "sum_rt": {"$sum": "$es.rt"},  # sum of response time
            "sum_rv": {"$sum": "$es.rv"}   # sum of response volume
        })
        return query


    def get_time_data(self, groups, y_axis):
        """ Return data formated in a FLOT specific format; eg. [[time, count], [time, count]]
        so that we can use it for time plots """
        real_counts = defaultdict(int)
        # We need to actually count the response volume across this data, not timeslots
        # for an accurate average over response time
        for feature in y_axis:
            feature_key = self.get_feature_key(feature)
            for _, value in groups.iteritems():
                if feature_key in value:
                    real_counts[feature_key] += value[feature_key].get('rv', 0)

        total_counts = defaultdict(int)
        total_items = defaultdict(int)
        data = defaultdict(list)

        for slot in gen_timeslots(self.from_ts, self.to_ts):
            timestamp = timeslot_to_timestamp_ms(slot)
            features_data = groups.get(slot, {})
            for feature in y_axis:
                feature_key = self.get_feature_key(feature)
                if features_data.get(feature_key):
                    count = features_data[feature_key].get('count', 0)
                    total_counts[feature_key] += count * features_data[feature_key].get('rv', 1)
                    total_items[feature_key] += 1
                    data[feature_key].append([timestamp, count])
                else:
                    data[feature_key].append([timestamp, 0])

        result_counts = defaultdict(float)
        for key, value in total_counts.iteritems():
            if total_items.get(key):
                if real_counts[key]:
                    result_counts[key] = round(value / real_counts[key], 2)
                else:
                    result_counts[key] = 0
            else:
                result_counts[key] = 0
        return data, result_counts, total_items
    
    
class ResponseVolumePlotter(BasePlotter):
    
    def sum_group_by_query(self):
        """ Overwrite base class with response volume specifics """
        query = super(ResponseVolumePlotter, self).sum_group_by_query()
        query.update({"count": {"$sum": "$es.rv"}})
        return query
    
    
class CallVolumePlotter(BasePlotter):
    
    def sum_group_by_query(self):
        """ Overwrite base class with response volume specifics """
        query = super(CallVolumePlotter, self).sum_group_by_query()
        query.update({"count": {"$sum": "$es.pt"}})
        return query

