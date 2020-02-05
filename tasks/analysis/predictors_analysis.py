from copy import deepcopy
from solariat.utils.timeslot import datetime_to_timestamp_ms
from datetime import datetime, timedelta
from collections import defaultdict
from solariat_bottle.settings import LOGGER

from .base import AnalysisTerminationException, \
    AnalysisProcess, PROGRESS_ERROR, utc_now
from solariat_bottle.jobs.manager import job, manager, terminate_handler


class PredictorsAnalysis(object):
    # TODO: Move to the def regression() in base.py
    def __init__(self, analysis):
        from solariat_bottle.views.facets import PredictorsView
        from solariat_bottle.db.predictors.base_predictor import BasePredictor
        self.analysis = analysis
        self.predictors_view = PredictorsView()
        self.predictors_view.predictor = BasePredictor.objects.get(self.analysis.filters['predictor_id'])  # init BasePredictor
        self.train_class = self.predictors_view.predictor.training_data_class  # abstract AnalysisProcess knows about class
        self.FEATURES = self.get_features()

    def get_features(self):
        action_features_schema = ['action:' + a['label'] for a in self.predictors_view.predictor.action_features_schema]
        context_features_schema = ['context:' + a['label'] for a in self.predictors_view.predictor.context_features_schema]
        return action_features_schema + context_features_schema

    @staticmethod
    def get_value(item, attribute):
        attribute_name = attribute
        value = "N/A"
        if attribute_name.startswith('context'):
            attribute_name = attribute_name.split(':')[1]
            value = item.context.get(attribute_name, value)
        if attribute_name.startswith('action'):
            attribute_name = attribute_name.split(':')[1]
            value = item.action.get(attribute_name, value)
        return value

    def get_timeline_results(self, pipeline, params):
        computed_pipeline = self.predictors_view.compute_pipeline(pipeline, params)
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
        F = self.train_class.F
        reward = '$' + F.reward
        context = '$' + F.context
        # context_vector = '$' + F.context_vector
        # action_vector = '$' + F.action_vector
        action = '$' + F.action

        context_f = []
        action_f = []
        for feature in self.FEATURES:
            if 'context' in feature:
                context_f.append(feature.replace('context:', ''))
            elif 'action' in feature:
                action_f.append(feature.replace('action:', ''))

        project_regr = {'$project': {'reward': '$reward', '_id': '$_id'}}
        [project_regr['$project'].update({'ctx_' + _feature: '$ctx.' + _feature}) for _feature in context_f]
        [project_regr['$project'].update({'act_' + _feature: '$act.' + _feature}) for _feature in action_f]

        pipe.append(project_regr)

        # No grouping -- only aggregating features data
        group_regr = {
            '$group': {
                '_id': {},
                'count': {'$sum': 1}
            }
        }

        [group_regr['$group'].update({'ctx_' + _feature: {'$push': {
            # "key": action_vector + '.' + _feature,
            "value": context + '_' + _feature,
            "reward": reward
        }}}) for _feature in context_f]

        [group_regr['$group'].update({'act_' + _feature: {'$push': {
            # "key":  context_vector + '.' + _feature,
            "value": action + '_' + _feature,
            "reward": reward
        }}}) for _feature in action_f]

        pipe.append(group_regr)
        LOGGER.info("Executing aggregation query: " + str(pipe))
        return pipe

    def get_regression_results(self, pipeline):
        """This is implementation of the $group step from `build_regression_pipe`
        in python.
        Returns result similar to
        >> pipeline = deepcopy(self.initial_pipeline)
        >> self.special_attr_handler_class.build_regression_pipe(pipeline)
        >> return self.item_class.objects.coll.aggregate(pipeline)['result']
        """
        from itertools import imap
        item_class = self.train_class
        F = item_class.F
        context_f = []
        action_f = []
        for feature in self.FEATURES:
            if 'context' in feature:
                context_f.append(feature.replace('context:', ''))
            elif 'action' in feature:
                action_f.append(feature.replace('action:', ''))

        def map_fn(item):
            for field in (F.context, F.action, F.reward):
                if field not in item:
                    return None

            emission = {
                'count': {'$sum': 1}
            }
            context_data = {
                'context:' + _feature:
                    {'$push': {
                        # "key": item[F.context].get(_feature),
                        "value": item[F.context].get(_feature),
                        "reward": item[F.reward]
                    }}
                for _feature in context_f}

            action_data = {
                'action:' + _feature:
                    {'$push': {
                        # "key": item[F.context].get(_feature),
                        "value": item[F.action].get(_feature),
                        "reward": item[F.reward]
                    }}
                for _feature in action_f}

            emission.update(context_data)
            emission.update(action_data)
            return emission

        def reduce_fn(a, b):
            if b is None:
                return a
            for key, op in b.viewitems():
                for op_name, operand in op.viewitems():
                    if op_name == '$sum':
                        a[key] += operand
                    elif op_name == '$push':
                        # if 'key' in operand and operand['key'] is not None:
                        if 'value' in operand and operand['value'] is not None:
                            a[key].append(operand)
            return a

        LOGGER.info("Executing aggregation query: " + str(pipeline))

        agg_cursor = item_class.objects.coll.aggregate(pipeline,
                                                       allowDiskUse=True,
                                                       cursor={})

        initial = {'count': 0}
        initial_context_data = {'context:' + _feature: [] for _feature in context_f}
        initial_action_data = {'action:' + _feature: [] for _feature in action_f}
        initial.update(initial_context_data)
        initial.update(initial_action_data)

        return reduce(reduce_fn, imap(map_fn, agg_cursor), initial)

    def parsed_predictor_filters(self):
        from solariat_bottle.views.facets import Param, Parameters

        if 'timerange' in self.analysis.filters:
            self.analysis.filters.pop('timerange')

        if self.analysis.analysis_type not in [self.analysis.CLASSIFICATION_TYPE, self.analysis.REGRESSION_TYPE]:
            err_msg = "Unknown analysis type - %s" % self.analysis.analysis_type
            raise AnalysisTerminationException(err_msg)

        existing_params = [(p[0], p[1], p[2], None) for p in self.predictors_view.get_parameters_list()]

        valid_request_params = Parameters(*[Param(*p) for p in existing_params])
        valid_request_params.update(self.analysis.filters)
        valid_request_params = valid_request_params.as_dict()

        params = self.predictors_view.postprocess_params(valid_request_params)

        if self.analysis._cached_from_date is None:
            self.analysis._cached_from_date = params['from_dt']
        if self.analysis._cached_to_date is None:
            self.analysis._cached_to_date = params['to_dt']

        return params


# @io_pool.task(timeout=None)
@job('analysis')
def process_predictive_analysis(analysis_tpl):
    start_time = utc_now()
    p_analysis_handler = PredictorsAnalysis(analysis_tpl)

    try:
        filters = p_analysis_handler.parsed_predictor_filters()  # add from_dt, to_dt fields
        query = p_analysis_handler.predictors_view.prepare_query(filters)
        initial_pipeline = [{'$match': query}]

        if 'from_dt' in filters:
            filters.pop('from_dt')
            filters.pop('to_dt')

        timeline_filter = deepcopy(filters)
        timeline_filter.update({
            'level': analysis_tpl.get_timerange_level(),
            'plot_by': 'reward',
            'plot_type': 'time'
        })
        params = dict(filters=filters,
                      initial_pipeline=initial_pipeline,
                      start_time=start_time,
                      timeline_filter=timeline_filter)
        analysis_process = AnalysisProcess(p_analysis_handler, params)

        if analysis_tpl.analysis_type == analysis_tpl.REGRESSION_TYPE:
            analysis_process.regression()   #use_mongo=False)
        elif analysis_tpl.analysis_type == analysis_tpl.CLASSIFICATION_TYPE:
            analysis_process.classification()

    except AnalysisTerminationException, ex:
        LOGGER.error(ex)
        p_analysis_handler.analysis.status_message = str(ex)
        p_analysis_handler.analysis.progress = PROGRESS_ERROR
        p_analysis_handler.analysis.save()
        manager.produce_state_update({'error': str(ex)})
        return


@terminate_handler(process_predictive_analysis)
def terminate_predictive_analysis(analysis_tpl):
    analysis_tpl.terminate()