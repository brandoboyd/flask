import json
import math
import re
import numpy as np

from copy import deepcopy
from collections import defaultdict, Counter

from solariat.exc.base import AppException
from solariat.utils.timeslot import now as utc_now
from solariat_bottle.settings import LOGGER
from solariat_bottle.jobs.manager import manager


BATCH_SIZE = 10000  # Process 100 items at a time
STATUS_DONE = 'done'
STATUS_QUEUE = 'queue'
STATUS_IN_PROGRESS = 'running'
STATUS_STOPPED = 'stopped'
STATUS_ERROR = 'error'

NPS_PROMOTER = 'promoter'
NPS_DETRACTOR = 'detractor'
NPS_PASSIVE = 'passive'

PROGRESS_STOPPED = -1
PROGRESS_DONE = 100
PROGRESS_ERROR = -2


class AnalysisTerminationException(AppException):
    pass


class AnalysisContinuationException(AppException):
    pass


class ClassificationAttrHandler(object):
    def __init__(self, attribute):
        self.attribute = attribute

    @staticmethod
    def increment_counts(crosstab_results, feature_value, class_idx):
        # Just increment the count for a specific feature value and given class
        if feature_value not in crosstab_results:
            crosstab_results[feature_value] = dict()

        feature_specific_results = crosstab_results[feature_value]
        if class_idx not in feature_specific_results:
            feature_specific_results[class_idx] = 1
        else:
            feature_specific_results[class_idx] += 1

    @staticmethod
    def ensure_all_values(attribute_value, all_values):
        if isinstance(attribute_value, list):
            for one_feature in attribute_value:
                if one_feature not in all_values:
                    all_values.append(one_feature)
        else:
            if attribute_value not in all_values:
                all_values.append(attribute_value)


class AnalysisProcess(object):
    # Common class for current PRR and JA analysis
    # Each Attribute Handler Class should have 'train_class' field which is the reference of Collection
    def __init__(self, special_attr_handler, params):
        self.analysis = special_attr_handler.analysis
        self.initial_pipeline = params['initial_pipeline']
        self.filters = params['filters']
        self.timeline_filter = params['timeline_filter']
        self.special_attr_handler = special_attr_handler
        self.start_time = params['start_time']

    def get_class_idx(self, item):
        stored_metric_values = self.analysis.metric_values  # Load so no extra validation / mongo calls done

        if self.analysis.analyzed_metric == "conversion":
            return self.special_attr_handler.get_conversion_class(item)

        if self.analysis.analyzed_metric == "stage-paths":
            return self.special_attr_handler.get_stage_path_class(item)

        if self.analysis.analyzed_metric == 'nps_categories':
            return self.special_attr_handler.get_nps_category(item)

        if self.analysis.analyzed_metric == 'paths-comparison':
            return self.special_attr_handler.get_path_class(item)

        if hasattr(item, 'reward'):
            metric_value = item.reward  # TODO: old field name, should be removed as well
        else:
            # Journey Analysis stuff, this needs to be refactored
            # metric_value = getattr(item, self.analysis.analyzed_metric)
            if self.analysis.analyzed_metric in item.journey_attributes:
                metric_value = item.journey_attributes[self.analysis.analyzed_metric]
            else:
                metric_value = item.journey_attributes[self.analysis.analyzed_metric.lower()]

        if metric_value is None:
            return -1
        if self.analysis.metric_type == self.analysis.BOOLEAN_METRIC or self.analysis.metric_type == self.analysis.LABEL_METRIC:
            if str(metric_value).lower() in stored_metric_values:
                return stored_metric_values.index(str(metric_value).lower())
            else:
                return self.analysis.IDX_UNKNOWN
        if self.analysis.metric_type == self.analysis.NUMERIC_METRIC:
            for idx, boundary in enumerate(stored_metric_values):
                if int(metric_value) <= int(boundary):
                    return idx
            return idx + 1
        return self.analysis.IDX_UNKNOWN

    def get_scatter_bar_plot(self, feature_dict):
        # If we have known Feature Value categories, then we can group_by them per each key
        scatter_results = dict(key='Bubble', values=[])
        bar_results = dict(key='Bar', values=[])
        for _feature_value_key, _feature_value_rewards in feature_dict.iteritems():
            reward_counts = sorted(list(_feature_value_rewards.iteritems()), key=lambda x: x[0])
            sum_counts = 0
            sum_values = 0
            for feat_val, feat_val_count in reward_counts:
                sum_counts += feat_val_count
                sum_values += feat_val_count * feat_val
            bar_results['values'].append({'label': str(_feature_value_key),
                                          'count': len(_feature_value_rewards),
                                          'avg_metric': float(sum_values) / sum_counts})
        return [scatter_results], [bar_results]

    # def get_pie_plot(self, feature_dict):
    #     pie_plot_results = []
    #     for _feature_value_key, _feature_value_rewards in feature_dict.iteritems():
    #         _item = {'label': _feature_value_key,
    #                  'value': _feature_value_rewards}
    #         pie_plot_results.append(_item)
    #     return pie_plot_results

    def get_box_plot(self, feature_dict):
        """Computation of metric values for boxplot chart"""
        box_plot_results = []
        descriptive_statistics = []

        for _feature_value_key, _feature_value_rewards in feature_dict.iteritems():
            # if len(set(_feature_value_rewards)) == 1:
                # ignore feature value with 1 reward, because it's useless to find mean, Q1, Q3 etc with 1 value
                # continue
            reward_counts = sorted(list(_feature_value_rewards.iteritems()), key=lambda x: x[0])
            total_counts = sum([r[1] for r in reward_counts])
            current_count = 0
            found_25_quartile = False
            found_median = False
            found_75_quartile = False
            max_count = 0
            most_common = None
            running_sum = 0
            for feat_val, feat_val_count in reward_counts:
                current_count += feat_val_count
                if current_count > 0.25 * total_counts and not found_25_quartile:
                    found_25_quartile = True
                    q1 = feat_val
                if current_count > 0.5 * total_counts and not found_median:
                    found_median = True
                    q2 = feat_val
                if current_count > 0.75 * total_counts and not found_75_quartile:
                    found_75_quartile = True
                    q3 = feat_val
                if feat_val_count > max_count:
                    max_count = feat_val_count
                    most_common = feat_val
                running_sum += feat_val * feat_val_count

            iqr = q3 - q1
            _lowest = q1 - 1.5 * iqr
            _highest = q3 + 1.5 * iqr

            if self.analysis.metric_type == self.analysis.NUMERIC_METRIC:
                _lowest = max(_lowest, self.analysis.metric_values_range[0])
                _highest = min(_highest, self.analysis.metric_values_range[1])

            _descriptive_analysis = dict(Q1=q1,
                                         Q2=q2,
                                         Q3=q3,
                                         mean=float(running_sum) / total_counts,
                                         mode=most_common,
                                         whisker_low=_lowest,
                                         whisker_high=_highest)
            _descriptive_analysis.update(outliers=[x[0] for x in reward_counts if x[0] > _highest or x[0] < _lowest])

            box_plot_results.append({'label': _feature_value_key, 'values': _descriptive_analysis})
            descriptive_statistics.append(_descriptive_analysis)

        return sorted(box_plot_results), descriptive_statistics

    def _fetch_in_batches(self, pipeline, batch_size=BATCH_SIZE):
        agg_cursor = self.special_attr_handler.train_class.objects.coll.aggregate(
            pipeline,
            allowDiskUse=True,
            cursor={'batchSize': batch_size})

        counter = 0
        ids = []
        for entry in agg_cursor:
            ids.append(entry['_id'])
            counter += 1
            if counter % batch_size == 0:
                for item in self.special_attr_handler.train_class.objects(id__in=ids):
                    yield item
                ids = []
        if ids:
            for item in self.special_attr_handler.train_class.objects(id__in=ids):
                yield item

    def classification(self):
        n_processed_items = 0
        temp_results = dict()

        timeslot_counts = self.analysis.initialize_timeslot_counts()
        count = 0

        for item in self._fetch_in_batches(self.initial_pipeline, batch_size=BATCH_SIZE):
            if count % BATCH_SIZE == 0:
                try:
                    self.analysis.reload()
                except self.special_attr_handler.train_class.DoesNotExist:
                    LOGGER.warning("Analysis with id=%s was removed while running." % self.analysis.id)

            count += 1
            if self.analysis.is_stopped():
                return

            try:
                class_idx = self.get_class_idx(item)
            except AnalysisTerminationException, ex:
                LOGGER.error(ex)
                self.analysis.status_message = str(ex)
                self.analysis.progress = PROGRESS_ERROR
                self.analysis.save()
                manager.produce_state_update({'error': str(ex)})
                return

            if class_idx == self.analysis.IDX_SKIP:
                continue

            timeslot_idx = self.analysis.get_timeslot_index(item)
            if timeslot_counts[class_idx][timeslot_idx] is not None:
                timeslot_counts[class_idx][timeslot_idx] += 1

            for feature in self.special_attr_handler.FEATURES:
                feature = self.special_attr_handler.train_class.translate_static_key_name(feature)
                if feature not in temp_results:
                    temp_results[feature] = {self.analysis.KEY_WEIGHT: 0,
                                             self.analysis.KEY_VALUES: [],
                                             self.analysis.KEY_CROSSTAB: {}}
                attribute_handler = ClassificationAttrHandler(feature)
                feature_value = self.special_attr_handler.get_value(item, feature)
                known_feature_values = temp_results[feature][self.analysis.KEY_VALUES]
                # Brand new value never processed, add to list of all existing values for this feature
                attribute_handler.ensure_all_values(feature_value, known_feature_values)

                # If we have a list field, process each individually, all of them might have made
                # this specific item instance fall into this class
                crosstab_results = temp_results[feature][self.analysis.KEY_CROSSTAB]
                if isinstance(feature_value, list):
                    for one_feature in feature_value:
                        attribute_handler.increment_counts(crosstab_results, one_feature, class_idx)
                else:
                    attribute_handler.increment_counts(crosstab_results, feature_value, class_idx)

            n_processed_items += 1
            self.analysis.progress = n_processed_items
            self.analysis.save()
            if n_processed_items % 100 == 0:
                manager.produce_state_update({'progress': n_processed_items})

        if n_processed_items == 0:
            self.analysis.status_message = "Could not find any results for specified filters. Canceled analysis."
            self.analysis.progress = PROGRESS_ERROR
            self.analysis.save()
            manager.produce_state_update({'error': self.analysis.status_message})
            return

        manager.produce_state_update({'progress': n_processed_items})

        for one_feature_values in temp_results.values():
            sum_per_attribute = 0
            min_weight = 1. / self.analysis.get_num_classes()
            # Normalize all results
            weights = []
            for feature_class_counts in one_feature_values[self.analysis.KEY_CROSSTAB].values():
                sum_per_value = 0
                max_per_value = 0

                for key, individual_count in feature_class_counts.iteritems():
                    normalized_value = float(individual_count) / n_processed_items
                    if normalized_value > max_per_value:
                        max_per_value = normalized_value
                    sum_per_value += normalized_value
                    feature_class_counts[key] = "%.3f" % (normalized_value * 100)

                if max_per_value:
                    weight = max_per_value / sum_per_value
                    weight = (weight - min_weight) / (1 - min_weight)
                    weights.append(weight)
                sum_per_attribute += sum_per_value
            if weights:
                one_feature_values['discriminative_weight'] = sum(weights) / len(weights)
                LOGGER.info("Individual weights are %s and final weight is %s" % (weights, sum(weights) / len(weights)))
            else:
                one_feature_values['discriminative_weight'] = 0

            # Append 0's as needed
            all_classes = range(self.analysis.get_num_classes()) + [-1]
            for feature_class_counts in one_feature_values[self.analysis.KEY_CROSSTAB].values():
                for class_key in all_classes:
                    if class_key not in feature_class_counts:
                        feature_class_counts[class_key] = '0'

        ordered_timeslot_counts = []
        for key, value in timeslot_counts.iteritems():
            timerange_entry = dict(class_key=key,
                                   timerange=[])
            ordered_timeslot_counts.append(timerange_entry)
            for timeslot in sorted(timeslot_counts[key].keys()):
                timerange_entry['timerange'].append([timeslot, timeslot_counts[key][timeslot]])

        if 'timerange' in self.analysis.filters:
            self.analysis.filters.pop('timerange')

        self.analysis._timerange_results = json.dumps(ordered_timeslot_counts)
        self._save_analysis(temp_results, n_processed_items)

    def _save_analysis(self, temp_results, n_processed_items):
        end_time = utc_now()
        processing_time = (end_time - self.start_time).total_seconds()
        self.analysis._results = json.dumps(temp_results)
        self.analysis.status_message = "Successfully finished the analysis of %s items in %s seconds." % (n_processed_items, processing_time)
        self.analysis.progress = PROGRESS_DONE
        self.analysis.save()
        manager.produce_state_update({'progress': 'done'})

    def regression(self):
        from copy import deepcopy
        min_metric, max_metric = self.analysis.metric_values_range
        min_metric = int(min_metric)
        max_metric = int(max_metric)

        max_helper_values = 100        # Maximum number of distinct metric value buckets to keep counts of
        helper_metric_counts = dict()

        one_metric_helper = dict()
        if max_metric - min_metric + 1 < max_helper_values:
            metric_step = 1
            for metric_val in range(min_metric, max_metric + 1):
                one_metric_helper[metric_val] = 0
        else:
            metric_step = (max_metric - min_metric) / max_helper_values
            for idx in xrange(max_helper_values):
                one_metric_helper[int(idx * metric_step)] = 0

        def get_reward_bucket(reward):
            n_steps = (reward - min_metric) / metric_step
            return min_metric + n_steps * metric_step

        batch_size = 10000
        have_more_data = True
        current_batch = 0
        _results = {}
        ranking_helper = dict()
        result_count = 0

        while have_more_data:
            pipeline = deepcopy(self.initial_pipeline)
            pipeline.append({'$skip': current_batch * batch_size})
            pipeline.append({'$limit': batch_size})
            pipeline = self.special_attr_handler.build_regression_pipe(pipeline)
            # if use_mongo:
            aggregation_results = self.special_attr_handler.train_class.objects.coll.aggregate(
                pipeline, allowDiskUse=True)['result']
            if not aggregation_results:
                have_more_data = False
                break
            else:
                aggregation_results = aggregation_results[0]
                current_batch += 1
                result_count += aggregation_results['count']

            for feat_key, feat_values in aggregation_results.iteritems():
                if feat_key not in helper_metric_counts:
                    helper_metric_counts[feat_key] = dict()
                feature_helper = helper_metric_counts[feat_key]
                if isinstance(feat_values, list) and feat_values:
                    for value in feat_values:
                        if not value or 'value' not in value:
                            continue
                        if type(value['value']) in (dict, list):
                            value['value'] = str(value['value'])
                        if value['value'] not in feature_helper:
                            feature_helper[value['value']] = deepcopy(one_metric_helper)    # TODO: bucket value['value'] for features with huge cardinalties
                        reward = get_reward_bucket(value['reward'])
                        if reward not in feature_helper[value['value']]:
                            feature_helper[value['value']][reward] = 1
                        else:
                            feature_helper[value['value']][reward] += 1

        try:
            timeline_results = self.special_attr_handler.get_timeline_results(self.initial_pipeline,
                                                                              self.timeline_filter)
        except AnalysisTerminationException, ex:
            LOGGER.error(ex)
            self.analysis.status_message = str(ex)
            self.analysis.progress = PROGRESS_ERROR
            self.analysis.save()
            manager.produce_state_update({'error': str(ex)})
            return

        for feat_key, feat_values in helper_metric_counts.iteritems():
            # filtered_val = [dict(t) for t in set([tuple(d.items()) for d in feat_value])]
            if not feat_values:
                continue
            box_plot_results, descr_statistics = self.get_box_plot(feat_values)
            scatter_plot_results, bar_plot_results = self.get_scatter_bar_plot(feat_values)
            # pie_plot_results = self.get_pie_plot(feat_values)

            if feat_key not in _results:
                # This was the first time this feature was present in the data
                feature = {feat_key: {
                    self.analysis.KEY_VALUES: [1, 2, 3], #TODO: Not actually used but UI won't render without them!!
                    self.analysis.KEY_SCORE: 0,  # TODO: Get the score from Feature Selection
                    self.analysis.KEY_RANK: 0  # TODO: Get the rank from Feature Selection
                }}

                if isinstance(feat_values.keys()[0], (int, float)):
                    # continuous values
                    feature[feat_key].update({
                        self.analysis.KEY_BOX: box_plot_results,
                        # self.analysis.KEY_PIE: pie_plot_results,
                        # self.analysis.KEY_SCATTER: [],    # TODO: Scatter plot as in won't work for large collections.
                        self.analysis.KEY_BAR: bar_plot_results,
                        self.analysis.KEY_VALUE_TYPE: self.analysis.NUMERIC_METRIC
                    })

                elif isinstance(feat_values.keys()[0], (basestring, bool)):
                    # categorical values
                    feature[feat_key].update({
                        self.analysis.KEY_BOX: box_plot_results,
                        # self.analysis.KEY_PIE: pie_plot_results,
                        self.analysis.KEY_BAR: bar_plot_results,
                        self.analysis.KEY_VALUE_TYPE: self.analysis.LABEL_METRIC
                    })
                ranking_helper[feat_key] = np.var([val['mean'] for val in descr_statistics]) / len(descr_statistics)
            else:
                feature = _results[feat_key]

                #TODO: Incrementally update box plot results here
                ranking_helper[feat_key] = ranking_helper[feat_key] * current_batch

            _results.update(feature)

        min_var, max_var = min(ranking_helper.values()), max(ranking_helper.values())
        for key, val in ranking_helper.iteritems():
            ranking_helper[key] = (val - min_var) / (max_var - min_var)

        rankins = sorted(ranking_helper.iteritems(), key=lambda x: -x[1])
        for idx, rank in enumerate(rankins):
            _results[rank[0]][self.analysis.KEY_SCORE] = rank[1] if not math.isnan(rank[1]) else 0
            _results[rank[0]][self.analysis.KEY_RANK] = idx

        self.analysis._timerange_results = json.dumps(timeline_results)   #TODO: This will not scale, mongo doesn't allow us to store documents this big. Need total rework json.dumps(timeline_results)
        self._save_analysis(_results, result_count)