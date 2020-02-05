from bson import ObjectId
from collections import defaultdict
from datetime import datetime

from solariat_bottle.db.predictors.base_predictor import TYPE_BOOLEAN, TYPE_NUMERIC, TYPE_CLASSIFIER, \
    BasePredictor
from . import *

PLOT_BY_TIME = 'time'
PLOT_BY_DISTRIBUTION = 'distribution'

KEY_ALL = 'all'
KEY_REWARD = 'reward'
KEY_AB_TESTING = 'ab testing'
KEY_MODELS = 'models'

PREFIX_AB_NON_PREDICTED = 'NON PREDICTED'
PREFIX_AB_PREDICTED = 'PREDICTED'


class PredictorsView(FacetQueryView):
    url_rule = '/predictors/facets/json'

    predictor = None
    plot_by = None
    model_data = dict()

    def get_parameters_list(self):
        return [
            ('predictor_id',    basestring,   Param.UNCHECKED,  Param.REQUIRED),
            ('models',          list_or_none, Param.UNCHECKED,  None),
            ('from',            basestring,   is_date,          Param.REQUIRED),
            ('to',              basestring,   is_date,          Param.REQUIRED),
            ('level',           basestring,   is_hdm_level,     Param.REQUIRED),
            ('plot_type',       basestring,   Param.UNCHECKED,  Param.REQUIRED),
            ('plot_by',         basestring,   Param.UNCHECKED,  Param.REQUIRED),
            ('context_vector',  dict,         Param.UNCHECKED,  {}),
            ('action_vector',   dict,         Param.UNCHECKED,  {}),
            ('request_url',     str_or_none,  Param.UNCHECKED,  None),
            ('ab_testing',      str_or_none,  Param.UNCHECKED,  None)
        ]

    def postprocess_params(self, params):
        r = params
        if 'from' in r and 'to' in r:
            from_date = r.pop('from')
            to_date = r.pop('to') or from_date
            r['from_dt'], r['to_dt'] = parse_date_interval(from_date, to_date)
        return params

    def prepare_query(self, params):
        q = {'predictor_id': ObjectId(params['predictor_id'])}

        if self.predictor is None:
            self.predictor = BasePredictor.objects.get(params['predictor_id'])

        klass = self.predictor.training_data_class

        # TODO: this needs to be added
        q[klass.created_at.db_field] = {'$gte': params['from_dt'], '$lte': params['to_dt']}

        if params['models']:
            if self.is_ab_testing(params):
                q[klass.model_id.db_field] = {'$in': [ObjectId(m_id) for m_id in params['models']] + [None]}
            else:
                q[klass.model_id.db_field] = {'$in': [ObjectId(m_id) for m_id in params['models']]}
        # else:
        #     if not self.is_ab_testing(params):
        #         q[klass.model_id.db_field] = {'$ne': None}

        context_facets = params['context_vector']
        action_facets = params['action_vector']

        if context_facets:
            for facet_name, facet_values in context_facets.iteritems():
                if facet_values:
                    q[klass.context.db_field + '.' + facet_name] = {'$in': facet_values}

        if action_facets:
            for facet_name, facet_values in action_facets.iteritems():
                if facet_values:
                    q[klass.action.db_field + '.' + facet_name] = {'$in': facet_values}

        return q

    def compute_pipeline(self, initial_pipeline, params):
        if params['plot_type'] == PLOT_BY_TIME:
            return self.prepare_timeline_query(initial_pipeline, params)
        elif params['plot_type'] == PLOT_BY_DISTRIBUTION:
            return self.prepare_distribution_query(initial_pipeline, params)

    def set_plotby_param(self, params):
        klass = self.predictor.training_data_class
        if params['plot_by'] == KEY_ALL:
            params['plot_by'] = KEY_REWARD

        if params['plot_by'] != KEY_REWARD:
            if params['plot_by'] in params['context_vector']:
                self.plot_by = '$' + klass.context.db_field + '.' + params['plot_by']
            elif params['plot_by'] in params['action_vector']:
                self.plot_by = '$' + klass.action.db_field + '.' + params['plot_by']
            elif params['plot_by'] in (KEY_MODELS, KEY_AB_TESTING):
                self.plot_by = '$' + klass.model_id.db_field
            else:
                raise Exception("Invalid plot by option " + str(params['plot_by']))

    def prepare_distribution_query(self, initial_pipeline, params):
        klass = self.predictor.training_data_class
        reward = '$' + klass.reward.db_field
        self.set_plotby_param(params)

        id_group = {}
        if self.plot_by:
            id_group[params['plot_by']] = self.plot_by

        if self.predictor.reward_type == TYPE_NUMERIC:
            group_dict = {
                    '$group': {
                        "_id": id_group,
                        'reward': {'$avg': reward},
                        'count': {'$sum': 1},
                    }
            }
        elif self.predictor.reward_type == TYPE_CLASSIFIER or self.predictor.reward_type == TYPE_BOOLEAN:
            id_group['reward'] = reward
            group_dict = {
                '$group': {
                        "_id": id_group,
                        'count': {'$sum': 1},
                    }
            }
        initial_pipeline.append(group_dict)
        return initial_pipeline

    def prepare_timeline_query(self, initial_pipeline, params):
        if self.predictor is None:
            self.predictor = BasePredictor.objects.get(params['predictor_id'])

        klass = self.predictor.training_data_class
        created = '$' + klass.created_at.db_field
        reward = '$' + klass.reward.db_field
        self.set_plotby_param(params)

        timeline_level = params['level']
        if timeline_level == 'hour':
            time_group = {"year": {'$year': created},
                          "day": {'$dayOfYear': created},
                          "hour": {'$hour': created}}
        elif timeline_level == 'day':
            time_group = {"year": {'$year': created},
                          "day": {'$dayOfYear': created}}
        elif timeline_level == 'month':
            time_group = {"year": {'$year': created},
                          "month": {'$month': created},
                          "day": {'$dayOfYear': created}}
        else:
            raise Exception("Unknown level %s" % timeline_level)

        if self.plot_by:
            time_group[params['plot_by']] = self.plot_by

        if self.predictor.reward_type == TYPE_NUMERIC:
            group_dict = {
                    '$group': {
                        "_id": time_group,
                        'reward': {'$avg': reward},
                        'count': {'$sum': 1},
                    }
            }
        elif self.predictor.reward_type == TYPE_CLASSIFIER or self.predictor.reward_type == TYPE_BOOLEAN:
            time_group['reward'] = reward
            group_dict = {
                '$group': {
                        "_id": time_group,
                        'count': {'$sum': 1},
                    }
            }

        initial_pipeline.append(group_dict)
        return initial_pipeline

    def is_ab_testing(self, params):
        # return 'ab_testing' in params and params['ab_testing'] in ('true', 'True')
        return params['plot_by'] == KEY_AB_TESTING

    def get_timestamp(self, entry):
        date = datetime(year=entry['_id']['year'], month=1, day=1)
        date = date + timedelta(days=entry['_id']['day'] - 1)
        if 'hour' in entry['_id']:
            date = date + timedelta(hours=entry['_id']['hour'])
        return datetime_to_timestamp_ms(date)

    def compute_distribution_result(self, params, result):
        processed_result = []
        all_plotby_options = set()

        if self.predictor.reward_type == TYPE_NUMERIC:
            for entry in result:
                label = self.predictor.metric

                if self.plot_by:
                    if params['plot_by'] in entry['_id']:
                        plot_by_value = str(entry['_id'][params['plot_by']])
                        if params['plot_by'] in (KEY_MODELS, KEY_AB_TESTING):
                            if plot_by_value != 'None':
                                plot_by_value = self.model_data.get(plot_by_value, 'ALL')
                                if plot_by_value != 'ALL':
                                    plot_by_value = plot_by_value['display_name']
                            else:
                                plot_by_value = PREFIX_AB_NON_PREDICTED

                            label = plot_by_value + ":" + label
                        else:
                            label = params['plot_by'] + ':' + plot_by_value
                    else:
                        label = params['plot_by'] + ':null'

                processed_result.append(dict(label=label,
                                             value=entry['reward']))

        elif self.predictor.reward_type == TYPE_BOOLEAN:
            helper_structure = defaultdict(int)
            for entry in result:
                metric_value = str(entry['_id']['reward'])
                if self.plot_by:
                    if params['plot_by'] in entry['_id']:
                        plot_by_value = str(entry['_id'][params['plot_by']])
                        if params['plot_by'] in (KEY_MODELS, KEY_AB_TESTING):
                            if plot_by_value != 'None':
                                plot_by_value = self.model_data.get(plot_by_value, 'ALL')
                                if plot_by_value != 'ALL':
                                    plot_by_value = plot_by_value['display_name']
                            else:
                                plot_by_value = PREFIX_AB_NON_PREDICTED
                        else:
                            plot_by_value = str(entry['_id'][params['plot_by']])

                        label = plot_by_value + ":" + str(metric_value)
                        all_plotby_options.add(plot_by_value)
                    else:
                        plot_by_value = 'None'
                        label = plot_by_value + ":" + str(metric_value)
                        all_plotby_options.add(plot_by_value)
                else:
                    label = ':' + str(metric_value)
                helper_structure[label] = entry['count']

            if not self.plot_by:
                all_plotby_options = ['']

            for plot_by in all_plotby_options:
                metric_true = ':True'
                metric_false = ':False'
                label = self.predictor.metric + "%"
                if plot_by:
                    metric_true = plot_by + str(metric_true)
                    metric_false = plot_by + str(metric_false)
                    label = plot_by + ':' + label

                def compute_distro(label, true_count, false_count):
                    if false_count == 0 and true_count == 0:
                        processed_result.append(dict(label=label,
                                                     value=0.0))
                    elif false_count == 0 and true_count:
                        processed_result.append(dict(label=label,
                                                     value=1.0))
                    else:
                        processed_result.append(dict(label=label,
                                                     value=float(true_count) / float(false_count)))

                true_count = helper_structure[metric_true]
                false_count = helper_structure[metric_false]
                compute_distro(label, true_count, false_count)

        return processed_result

    def compute_time_trends_result(self, params, result):
        computed_metric = 'reward'
        all_plotby_options = set()

        if self.predictor.reward_type == TYPE_NUMERIC:
            helper_structure = defaultdict(list)
            for entry in result:
                timestamp = self.get_timestamp(entry)
                label = self.predictor.metric

                if self.plot_by:
                    if params['plot_by'] in entry['_id']:
                        plot_by_value = str(entry['_id'][params['plot_by']])
                        if params['plot_by'] in (KEY_MODELS, KEY_AB_TESTING):
                            if plot_by_value != 'None':
                                plot_by_value = self.model_data.get(plot_by_value, 'ALL')
                                if plot_by_value != 'ALL':
                                    plot_by_value = plot_by_value['display_name']
                            else:
                                plot_by_value = PREFIX_AB_NON_PREDICTED

                            label = plot_by_value + ":" + label
                        else:
                            label = params['plot_by'] + ':' + plot_by_value
                    else:
                        label = params['plot_by'] + ':null'
                val = entry[computed_metric]
                if params['plot_by'] == KEY_AB_TESTING:
                    val *= 100 # getting percentage for a/b testing chart
                helper_structure[label].append([timestamp, val])

        elif self.predictor.reward_type == TYPE_BOOLEAN:
            helper_structure = defaultdict(list)
            for entry in result:
                timestamp = self.get_timestamp(entry)
                metric_value = str(entry['_id']['reward'])
                if self.plot_by:
                    if params['plot_by'] in entry['_id']:
                        plot_by_value = str(entry['_id'][params['plot_by']])
                        if params['plot_by'] in (KEY_MODELS, KEY_AB_TESTING):
                            if plot_by_value != 'None':
                                plot_by_value = self.model_data.get(plot_by_value, 'ALL')
                                if plot_by_value != 'ALL':
                                    plot_by_value = plot_by_value['display_name']
                            else:
                                plot_by_value = PREFIX_AB_NON_PREDICTED

                        else:
                            plot_by_value = str(entry['_id'][params['plot_by']])

                        label = plot_by_value + ":" + str(metric_value)
                        all_plotby_options.add(plot_by_value)
                    else:
                        plot_by_value = 'None'
                        label = plot_by_value + ":" + str(metric_value)
                        all_plotby_options.add(plot_by_value)
                else:
                    label = ':' + str(metric_value)
                helper_structure[label].append([timestamp, entry['count']])

            def compute_percentages(true_label, false_label, helper_structure):
                true_series = helper_structure[true_label]
                false_series = helper_structure[false_label]
                true_timestamps = set([v[0] for v in true_series])
                false_timestamps = set([v[0] for v in false_series])
                full_timestamps = true_timestamps.union(false_timestamps)

                # Make sure we have entries on both lists so we can compute final percentage
                true_diffs = full_timestamps.difference(true_timestamps)
                for stamp in true_diffs:
                    true_series.append([stamp, 0])
                false_diffs = full_timestamps.difference(false_timestamps)
                for stamp in false_diffs:
                    false_series.append([stamp, 0])
                true_series = sorted(true_series, key=lambda x: x[0])
                false_series = sorted(false_series, key=lambda x: x[0])

                final_result = []
                for idx in xrange(len(true_series)):
                    timestamp = true_series[idx][0]
                    assert timestamp == false_series[idx][0]
                    false_cnt = false_series[idx][1]
                    true_cnt = true_series[idx][1]

                    if false_cnt == 0 and true_cnt == 0:
                        final_result.append([timestamp, 0.0])
                    elif false_cnt == 0 and true_cnt:
                        final_result.append([timestamp, 1.0])
                    else:
                        final_result.append([timestamp, (float(true_cnt) * 100) / float(true_cnt + false_cnt)])
                return final_result

            # Only two categories, compute the actual percentage
            result = []
            if not self.plot_by:
                all_plotby_options = ['']

            for plot_by in all_plotby_options:
                metric_true = ':True'
                metric_false = ':False'
                label = self.predictor.metric + "%"
                if plot_by:
                    metric_true = plot_by + str(metric_true)
                    metric_false = plot_by + str(metric_false)
                    label = plot_by + ':' + label
                result.extend([dict(label=label,
                                    data=compute_percentages(metric_true, metric_false, helper_structure))])
            return result

        result = []
        for key, value in helper_structure.iteritems():
            result.append(dict(label=key, data=sorted(value, key=lambda x: x[0])))
        return result

    def prepare_plot_result(self, params, result):
        if params['plot_type'] == PLOT_BY_TIME:
            result = self.compute_time_trends_result(params, result)
        elif params['plot_type'] == PLOT_BY_DISTRIBUTION:
            result = self.compute_distribution_result(params, result)
        return result

    def compute_model_data(self, params):
        query = self.prepare_query(params)

        initial_pipeline = [{"$match": query}]
        pipeline = self.compute_pipeline(initial_pipeline, params)
        from solariat_bottle.app import logger
        logger.info("Executing query: " + str(pipeline))

        result = self.predictor.training_data_class.objects.coll.aggregate(pipeline)['result']
        result = self.prepare_plot_result(params, result)

        if params['plot_type'] == PLOT_BY_TIME:
            for each in result:
                data = each['data']
                each['average'] = sum(l[1] for l in data) / float(len(data)) if data else 0
        return result

    def render(self, params, request_params):
        self.predictor = BasePredictor.objects.get(request_params['predictor_id'])
        self.model_data = {str(model.id): model.to_json() for model in self.predictor.models}

        result = self.compute_model_data(params)

        if params['plot_type'] == PLOT_BY_TIME:
            self.fill_multi_series_with_zeroes(result, params['from_dt'], params['to_dt'])

        return dict(ok=True, list=result)
