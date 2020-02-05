from copy import deepcopy
from collections import defaultdict
from solariat.utils.timeslot import datetime_to_timestamp_ms
from datetime import datetime, timedelta
from solariat_bottle.settings import LOGGER

from solariat_bottle.tasks.analysis.base import AnalysisTerminationException, \
    AnalysisProcess, PROGRESS_ERROR, NPS_DETRACTOR, NPS_PASSIVE, NPS_PROMOTER, utc_now
from solariat_bottle.db.journeys.customer_journey import CustomerJourney, STRATEGY_DEFAULT, STAGE_INDEX_SEPARATOR
from solariat_bottle.db.journeys.journey_type import JourneyType
from solariat_bottle.db.funnel import Funnel
from solariat_bottle.jobs.manager import job, manager, terminate_handler
from solariat_bottle.db.account import Account


class JourneysAnalysis(object):
    """Class to parse, manage data
     related to Journeys for InsightsAnalysis
    """
    _customer_cache = {}
    _agents_cache = {}
    _funnel = None

    def __init__(self, analysis, journey_type):
        from solariat_bottle.views.facets import JourneyPlotsView
        self.analysis = analysis
        self.journey_type = journey_type
        self.train_class = CustomerJourney
        self.journeys_view = JourneyPlotsView()
        self.FEATURES = journey_type.get_journey_type_attributes()

    def get_customer(self, journey):
        if journey not in self._customer_cache:
            account = Account.objects.get(journey.account_id)
            CustomerProfile = account.get_customer_profile_class()
            customer = CustomerProfile.objects.get(journey.customer_id)
            self._customer_cache[journey] = customer
        return self._customer_cache[journey]

    def get_agent(self, agent_id, journey):
        if agent_id not in self._agents_cache:
            account = Account.objects.get(journey.account_id)
            AgentProfile = account.get_agent_profile_class()
            self._agents_cache[agent_id] = AgentProfile.objects.get(agent_id)
        return self._agents_cache[agent_id]

    def get_agent_related_attribute(self, journey, attribute_name):
        result = []
        for agent_id in journey.agents:
            agent = self.get_agent(agent_id, journey)
            attribute_value = getattr(agent, attribute_name)
            if isinstance(attribute_value, dict):
                for value in attribute_value.keys():
                    if value not in result:
                        result.append(value)
            elif isinstance(attribute_value, list):
                for value in attribute_value.keys():
                    if value not in result:
                        result.append(value)
            elif attribute_value not in result:
                result.append(attribute_value)
        return result

    def get_value(self, journey, attribute):
        # we have to use this in separate Attribute handler class due to specific values like Customer Segment, stages
        base_value = self.base_get_value(journey, attribute)

        if attribute == 'nps':
            if base_value is None:
                return 'N/A'
            if base_value <= 6:
                return NPS_DETRACTOR
            if base_value <= 8:
                return NPS_PASSIVE
            return NPS_PROMOTER

        if attribute == 'stage_sequence_names':
            result = []
            if len(base_value) > 2:
                for idx in xrange(len(base_value) - 1):
                    result.append("->".join(base_value[idx:idx + 2]))
            else:
                result.append("->".join(base_value))
            return result
        return base_value

    def base_get_value(self, journey, attribute):
        # attribute_name = attribute
        # if attribute_name.startswith('customer'):
        #     customer = self.get_customer(journey)
        #     attribute_name = attribute_name.split(':')[1]
        #     return getattr(customer, attribute_name)
        # if attribute_name.startswith('agent'):
        #     attribute_name = attribute_name.split(':')[1]
        #     return self.get_agent_related_attribute(journey, attribute_name)
        # return getattr(journey, attribute_name)
        return journey.full_journey_attributes[journey.translate_static_key_name(attribute)]

    def get_funnel(self):
        if self.analysis.analyzed_metric != 'conversion':
            LOGGER.warning("Funnel should only be present in conversion metrics")
            return None
        if self._funnel:
            return self._funnel
        if 'funnel_id' not in self.analysis.filters:
            err_msg = "Funnel is required for conversion analysis. Only filters stored are %s" % self.analysis.filters
            LOGGER.error(err_msg)
            raise AnalysisTerminationException(err_msg)
        try:
            self._funnel = Funnel.objects.get(self.analysis.filters['funnel_id'])
        except Funnel.DoesNotExist:
            err_msg = "No funnel found with id=%s" % self.analysis.filters['funnel_id']
            LOGGER.error(err_msg)
            raise AnalysisTerminationException(err_msg)
        return self._funnel

    def get_conversion_class(self, journey):
        from solariat_bottle.db.journeys.journey_type import JourneyStageType
        from solariat_bottle.db.journeys.journey_stage import JourneyStage
        stored_metric_values = self.analysis.metric_values
        funnel = self.get_funnel()
        if 'stage_id' in self.analysis.filters and self.analysis.filters['stage_id']:
            stage_id = self.analysis.filters['stage_id']
        else:
            stage_id = funnel.steps[-2]

        string_steps = [str(step) for step in funnel.steps]
        if str(stage_id) not in string_steps:
            err_msg = "Could not find stage=%s in steps=%s. Invalid funnel." % (self.analysis.filters['stage_id'],
                                                                                string_steps)
            LOGGER.error(err_msg)
            raise AnalysisTerminationException(err_msg)
        else:
            stage_idx = string_steps.index(str(stage_id))

        if stage_idx == len(funnel.steps) - 1:
            raise AnalysisTerminationException("Cannot perform conversion analysis on last step from funnel.")

        current_stage = funnel.steps[stage_idx]
        next_stage = funnel.steps[stage_idx + 1]

        current_stage = JourneyStageType.objects.get(current_stage).display_name + STAGE_INDEX_SEPARATOR + str(stage_idx)
        next_stage = JourneyStageType.objects.get(next_stage).display_name + STAGE_INDEX_SEPARATOR + str(stage_idx + 1)

        journey_stage_seq = journey.stage_sequences[STRATEGY_DEFAULT]

        if current_stage not in journey_stage_seq:
            # Never even made it there, not relevant
            LOGGER.error("%s not found in %s" % (current_stage, journey_stage_seq))
            return self.analysis.IDX_SKIP

        if next_stage not in journey_stage_seq:
            # We never made it to next stage, it's either abandoned or stuck
            if journey_stage_seq.index(current_stage) == len(journey_stage_seq) - 1:
                # Analyzed stage is last one, use status
                if journey.status == JourneyStageType.TERMINATED:
                    if self.analysis.METRIC_ABANDONED not in stored_metric_values:
                        return self.analysis.IDX_UNKNOWN
                    return stored_metric_values.index(self.analysis.METRIC_ABANDONED)    # Abandoned
                else:
                    if self.analysis.METRIC_STUCK not in stored_metric_values:
                        return self.analysis.IDX_UNKNOWN
                    return stored_metric_values.index(self.analysis.METRIC_STUCK)    # Stuck
            else:
                if self.analysis.METRIC_ABANDONED not in stored_metric_values:
                    return self.analysis.IDX_UNKNOWN
                # It was abandoned from our point of view, since it went to different stage
                return stored_metric_values.index(self.analysis.METRIC_ABANDONED)    # Abandoned
        else:
            if journey_stage_seq.index(next_stage) == journey_stage_seq.index(current_stage) + 1:
                if self.analysis.METRIC_CONVERTED not in stored_metric_values:
                    return self.analysis.IDX_UNKNOWN
                return stored_metric_values.index(self.analysis.METRIC_CONVERTED)    # Converted
            else:
                if self.analysis.METRIC_ABANDONED not in stored_metric_values:
                    return self.analysis.IDX_UNKNOWN
                return stored_metric_values.index(self.analysis.METRIC_ABANDONED)    # Abandoned

    def get_path_class(self, journey):
        import json
        metric_values = [json.loads(metric_value) for metric_value in self.analysis.metric_values]
        metric = metric_values[0].get('path')  # same metric for both paths
        paths_metric_values = [p['metric_value'] for p in metric_values]
        mean_paths_metric = float(sum(paths_metric_values)) / len(paths_metric_values)
        diff_paths_metric = abs(paths_metric_values[0] - paths_metric_values[1])

        # if paths' metric values are unique, then classify Journey by attribute's value
        # consider the discriminant as the average, and if the difference is not 1
        # else compare by other path's metric average
        if len(set(paths_metric_values)) == 2 and diff_paths_metric > 1:
            j_attr_val = journey.full_journey_attributes.get(metric)
            if not j_attr_val:
                return self.analysis.IDX_UNKNOWN
            return 1 if j_attr_val >= mean_paths_metric else 0
        else:
            paths_other_metric_values = [p['metrics'] for p in metric_values]
            all_paths_metrics_values = [m for path_metric in paths_other_metric_values for m in path_metric if m.keys()[0] != metric]

            _results_per_metric = defaultdict(list)
            for metric in all_paths_metrics_values:
                _results_per_metric[metric.keys()[0]].append(float(metric.values()[0]))

            for k, values in _results_per_metric.iteritems():
                _mean = float(sum(values)) / len(values)
                if len(set(values)) != 1 and _mean > 1:
                    attr_val = journey.full_journey_attributes.get(k)
                    if not attr_val:
                        continue
                    return 1 if attr_val >= _mean else 0

        return self.analysis.IDX_SKIP

    def get_stage_path_class(self, journey):
        import json
        from solariat_bottle.db.journeys.journey_type import JourneyStageType

        metric_values = [json.loads(metric_value) for metric_value in self.analysis.metric_values]
        # Load up actual stages
        journey_sequences = []
        for entry in metric_values:
            try:
                entry['stage'] = JourneyStageType.objects.get(display_name=entry['stage']).display_name
                journey_sequence = journey.stage_sequence_names
                journey_sequences.append(journey_sequence)
            except JourneyStageType.DoesNotExist:
                # It's a strategy stage, need more specific aggregation for this
                from solariat_bottle.db.journeys.customer_journey import EVENT_STRATEGY, PLATFORM_STRATEGY

                query = {CustomerJourney.F.id: journey.id}
                for strategy in {EVENT_STRATEGY, PLATFORM_STRATEGY}:
                    # query[StrategyLabelInformation.F.strategy] = strategy
                    # pipeline = [
                    #     {'$match': query},
                    #     {'$group':
                    #             {
                    #                 '_id': {"journey_id": '$' + StrategyLabelInformation.F.customer_journey_id},
                    #                 'stage_sequence': {"$max": '$' + StrategyLabelInformation.F.stage_sequence_names},
                    #             }
                    #         }
                    # ]
                    # agg_results = StrategyLabelInformation.objects.coll.aggregate(pipeline)['result'][0]
                    journey_sequence = agg_results['stage_sequence']
                    journey_sequences.append(journey_sequence)
                break

        for class_idx, metric_value in enumerate(metric_values):
            step = metric_value['step']
            stage = metric_value['stage']
            for journey_sequence in journey_sequences:
                if len(journey_sequence) <= step:
                    LOGGER.info("Skipped sequence %s because shorter than step %s" % (journey_sequence, step))
                    continue

                stage_at_step = journey_sequence[step]
                if stage_at_step != stage:
                    LOGGER.info("Skipped sequence %s because found stage %s at step %s instead of %s" % (journey_sequence, stage_at_step, step, stage))
                    continue
                else:
                    return class_idx

        return self.analysis.IDX_SKIP        # Doesn't even matter

    def get_nps_category(self, journey):
        stored_metric_values = self.analysis.metric_values
        nps = journey.nps  # TODO: this wont work, because CustomerJourney doesnt have field "nps"
        if nps is None:
            return self.analysis.IDX_UNKNOWN

        if nps <= 6:
            if self.analysis.METRIC_DETRACTOR in stored_metric_values:
                return stored_metric_values.index(self.analysis.METRIC_DETRACTOR)
            else:
                return self.analysis.IDX_SKIP
        if nps <= 8:
            if self.analysis.METRIC_PASSIVE in stored_metric_values:
                return stored_metric_values.index(self.analysis.METRIC_PASSIVE)
            else:
                return self.analysis.IDX_SKIP
        if self.analysis.METRIC_PROMOTER in stored_metric_values:
            return stored_metric_values.index(self.analysis.METRIC_PROMOTER)
        return self.analysis.IDX_SKIP

    def parsed_journeys_filters(self):
        # TODO: attempt at quick fix, definitely MOVE this out, or do it on view level
        from solariat_bottle.views.facets import JourneyDetailsView, str_or_none, Param, Parameters
        # from solariat_bottle.views.facets import JourneyPlotsView
        # params_view = JourneyPlotsView()
        params_view = JourneyDetailsView()
        params_view.user = self.analysis.get_user()

        if 'timerange' in self.analysis.filters:
            self.analysis.filters.pop('timerange')

        # make them all optional
        existing_params = [(p[0], p[1], p[2], None) for p in params_view.get_parameters_list()]
        existing_params.append(('journey_type_id', str_or_none, Param.UNCHECKED, None))
        existing_params.append(('funnel_id', str_or_none, Param.UNCHECKED, None))
        existing_params.append(('stage_id', str_or_none, Param.UNCHECKED, None))

        valid_request_params = Parameters(*[Param(*p) for p in existing_params])
        valid_request_params.update(self.analysis.filters)
        valid_request_params = valid_request_params.as_dict()

        params = params_view.postprocess_params(valid_request_params.copy())
        postprocessed_filters = params_view.prepare_query(params, valid_request_params,
                                                          collection_name=CustomerJourney.__name__)

        if self.analysis._cached_from_date is None:
            self.analysis._cached_from_date = params['from']
        if self.analysis._cached_to_date is None:
            self.analysis._cached_to_date = params['to']

        return postprocessed_filters

    def _prepare_regression_timeline_query(self, initial_pipeline, params):
        F = self.train_class.F
        last_updated = '$' + F.last_updated

        timeline_level = params.get('level')
        if timeline_level == 'hour':
            time_group = {"year": {'$year': last_updated},
                          "day": {'$dayOfYear': last_updated},
                          "hour": {'$hour': last_updated}}
        elif timeline_level == 'day':
            time_group = {"year": {'$year': last_updated},
                          "day": {'$dayOfYear': last_updated}}
        elif timeline_level == 'month':
            time_group = {"year": {'$year': last_updated},
                          "month": {'$month': last_updated},
                          "day": {'$dayOfYear': last_updated}}
        else:
            raise Exception("Unknown level %s" % timeline_level)

        computed_metric = params.get('computed_metric', 'count')
        group_dict = {'$group': {
            "_id": time_group,
            "reward": {'$avg': '$%s.%s' % (F.full_journey_attributes, computed_metric)},
            "count": {'$sum': 1}
        }}

        initial_pipeline.append(group_dict)
        return initial_pipeline

    def get_timeline_results(self, pipeline, params):
        computed_pipeline = self._prepare_regression_timeline_query(pipeline, params)
        LOGGER.info("Executing timeline query: " + str(pipeline))

        result = self.train_class.objects.coll.aggregate(computed_pipeline)['result']

        helper_structure = defaultdict(list)
        for entry in result:
            date = datetime(year=entry['_id']['year'], month=1, day=1)
            date = date + timedelta(days=entry['_id']['day'] - 1)
            if 'hour' in entry['_id']:
                date = date + timedelta(hours=entry['_id']['hour'])
            timestamp = datetime_to_timestamp_ms(date)
            helper_structure[self.analysis.analyzed_metric].append([timestamp, entry['reward']])
            helper_structure['Count'].append([timestamp, entry['count']])
        result = []
        for key, value in helper_structure.iteritems():
            result.append(dict(label=key,
                               data=sorted(value, key=lambda x: x[0])))
        return result

    def build_regression_pipe(self, pipe):
        reward = '$' + self.train_class.F.journey_attributes + '.' + self.analysis.analyzed_metric
        context = '$' + self.train_class.F.journey_attributes
        group_regr = {
            '$group': {
                '_id': {},
                'count': {'$sum': 1}
            }
        }

        project_regr = {'$project': {'reward': reward,
                                     '_id': '$_id'}}
        [project_regr['$project'].update({CustomerJourney.journey_attributes.db_field + '_' + _feature:
                                          '$' + CustomerJourney.journey_attributes.db_field + '.' + _feature})
        for _feature in self.FEATURES]
        pipe.append(project_regr)

        [group_regr['$group'].update({'ctx_' + _feature: {'$push': {
            # "key": action_vector + '.' + _feature,
            "value": context + '_' + _feature,
            "reward": '$reward'
        }}}) for _feature in self.FEATURES]

        pipe.append(group_regr)
        return pipe

    def get_regression_results(self, pipeline):
        from itertools import imap
        item_class = self.train_class
        F = item_class.F
        j_attr = F.journey_attributes

        features = self.FEATURES
        analyzed_metric = self.analysis.analyzed_metric

        def map_fn(item):
            if j_attr not in item and analyzed_metric not in item[j_attr]:
                return None
            static_attrs = [f_key for f_key in self.FEATURES if f_key not in item[j_attr]]
            static_attr_vals = {}
            for s_attr_key in static_attrs:
                static_attr_vals[s_attr_key] = item.get(s_attr_key)

            emission = {
                'count': {'$sum': 1}
            }

            _data = {
                _feature:
                    {'$push': {
                        "value": item[j_attr].get(_feature, static_attr_vals.get(_feature)),
                        "reward": item[j_attr].get(analyzed_metric)  # TODO: better use average
                    }}
                for _feature in features}
            emission.update(_data)
            return emission

        def reduce_fn(a, b):
            if b is None:
                return a
            for key, op in b.viewitems():
                for op_name, operand in op.viewitems():
                    if op_name == '$sum':
                        a[key] += operand
                    elif op_name == '$push':
                        if 'value' in operand and operand['value'] is not None:
                            a[key].append(operand)
            return a

        LOGGER.info("Executing aggregation query: " + str(pipeline))

        agg_cursor = item_class.objects.coll.aggregate(pipeline,
                                                       allowDiskUse=True,
                                                       cursor={})

        initial = {'count': 0}
        initial.update({_feature: [] for _feature in features})
        result = reduce(reduce_fn, imap(map_fn, agg_cursor), initial)

        for key in result.keys():
            data_key = self.train_class.translate_static_key_name(key)
            translated_values = []
            if isinstance(result[key], list):
                for value in result[key]:
                    value['value'] = self.train_class.translate_static_key_value(key, value['value'])
                    translated_values.append(value)
                result.pop(key)
                result[data_key] = translated_values

        return result


# @io_pool.task(timeout=None)
@job('analysis')
def process_journeys_analysis(analysis_tpl):
    start_time = utc_now()
    journey_type_instance = JourneyType.objects.get(analysis_tpl.filters['journey_type'][0])  # We pass 1 journey_type id as array
    j_analysis = JourneysAnalysis(analysis_tpl, journey_type_instance)  # JourneyAnalysis (data parsing, filtering etc)

    try:
        journey_filters = j_analysis.parsed_journeys_filters()
        # We only use these for matching to classes in case of converstion analysis, pop them from filters
        if 'funnel_id' in journey_filters:
            journey_filters.pop('funnel_id')
        if 'stage_id' in journey_filters:
            journey_filters.pop('stage_id')

        match = journey_filters
        initial_pipeline = [{"$match": match}]
        pipe = initial_pipeline.append
        pipe({'$sort': {CustomerJourney.F.first_event_date: 1}})

        if 'from_dt' in journey_filters:
            journey_filters.pop('from_dt')
            journey_filters.pop('to_dt')

        timeline_filter = deepcopy(journey_filters)
        timeline_filter.update({
            'level': analysis_tpl.get_timerange_level(),
            'computed_metric': analysis_tpl.analyzed_metric,
            'plot_type': 'timeline'
        })

        params = dict(filters=journey_filters,
                      initial_pipeline=initial_pipeline,
                      start_time=start_time,
                      timeline_filter=timeline_filter)
        analysis_process = AnalysisProcess(j_analysis, params)

        if analysis_tpl.analysis_type == analysis_tpl.CLASSIFICATION_TYPE:
            analysis_process.classification()
        elif analysis_tpl.analysis_type == analysis_tpl.REGRESSION_TYPE:
            analysis_process.regression()

    except AnalysisTerminationException, ex:
        LOGGER.error(ex)
        j_analysis.analysis.status_message = str(ex)
        j_analysis.analysis.progress = PROGRESS_ERROR
        j_analysis.analysis.save()
        manager.produce_state_update({'error': str(ex)})
        return


@terminate_handler(process_journeys_analysis)
def terminate_journeys_analysis(analysis_tpl):
    analysis_tpl.terminate()
