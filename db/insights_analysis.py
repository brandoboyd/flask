import threading
from solariat_bottle.settings import LOGGER
from solariat.db import fields
from solariat.db.abstract import Document
from solariat.utils.timeslot import guess_timeslot_level, parse_datetime

from solariat_bottle.db.user import User

from solariat_bottle.tasks.analysis.base import *
from solariat_bottle.tasks.analysis.journeys_analysis import process_journeys_analysis
from solariat_bottle.tasks.analysis.predictors_analysis import process_predictive_analysis

from datetime import timedelta, datetime
from solariat.utils.timeslot import datetime_to_timestamp_ms, utc


class InsightsAnalysis(Document):

    KEY_WEIGHT = 'discriminative_weight'
    KEY_RANK = 'rank'
    KEY_SCORE = 'score'
    KEY_VALUES = 'values'
    KEY_CROSSTAB = 'crosstab_results'
    KEY_VALUE_TYPE = 'value_type'

    KEY_PIE = 'pie'
    KEY_BAR = 'bar'
    KEY_BOX = 'boxplot'
    KEY_SCATTER = 'scatter'

    CLASSIFICATION_TYPE = 'classification'
    REGRESSION_TYPE = 'regression'

    BOOLEAN_METRIC = 'Boolean'
    NUMERIC_METRIC = 'Numeric'
    LABEL_METRIC = 'Label'

    METRIC_CONVERTED = "converted"
    METRIC_ABANDONED = "abandoned"
    METRIC_STUCK = "stuck"

    IDX_UNKNOWN = -1
    IDX_SKIP = -2
    NUM_TIMERANGE_SLOTS = 7

    user = fields.ObjectIdField(db_field='usr')
    title = fields.StringField(db_field='te')
    created_at = fields.NumField(db_field='ca')
    account_id = fields.ObjectIdField(db_field='ac')
    filters = fields.DictField(db_field='ft', required=True)
    analysis_type = fields.StringField(choices=[CLASSIFICATION_TYPE, REGRESSION_TYPE], db_field='at')
    application = fields.StringField(db_field='an')  # e.g. application which's used for the analysis
    analyzed_metric = fields.StringField(db_field='me')
    metric_type = fields.StringField(choices=[BOOLEAN_METRIC, NUMERIC_METRIC, LABEL_METRIC], db_field='mt')
    metric_values = fields.ListField(fields.StringField(), db_field='mv')
    metric_values_range = fields.ListField(fields.NumField(), db_field='mvr')  # e.g. min/max Numeric values or unique labels
    progress = fields.NumField(db_field='pg', default=0)
    _results = fields.StringField(db_field='rt')
    _timerange_results = fields.StringField(db_field='trt')
    status_message = fields.StringField(db_field='msg')

    _cached_from_date = None
    _cached_to_date = None
    time_increment = None

    @property
    def status_progress(self):
        if self.progress == PROGRESS_STOPPED:
            return STATUS_STOPPED, 0
        elif self.progress == 0:
            return STATUS_QUEUE, self.progress
        elif self.progress == PROGRESS_DONE:
            return STATUS_DONE, self.progress
        elif self.progress == PROGRESS_ERROR:
            return STATUS_ERROR, 0
        else:
            return STATUS_IN_PROGRESS, self.progress

    def is_stopped(self):
        return self.progress == PROGRESS_STOPPED

    def compute_class_names(self):
        import json
        metric_names = []
        try:
            if self.analyzed_metric == "stage-paths":
                for metric in self.metric_values:
                    metric_info = json.loads(metric)
                    metric_names.append("%s at step %s" % (metric_info['stage'], metric_info['step']))
                return metric_names
            if self.analyzed_metric == "paths-comparison":
                for metric in self.metric_values:
                    metric_info = json.loads(metric)
                    metric_names.append(
                        "%s %s (%s)" % (metric_info['measure'], metric_info['path'], metric_info['metric_value']))
                return metric_names
            if self.metric_type == self.NUMERIC_METRIC and self.analysis_type == self.CLASSIFICATION_TYPE:
                metric_values = [
                    '%s(%s:%s)' % (self.analyzed_metric, self.metric_values_range[0], self.metric_values[0]),
                    "%s(%s:%s)" % (self.analyzed_metric, self.metric_values[0], self.metric_values[1]),
                    "%s(%s:%s)" % (self.analyzed_metric, self.metric_values[1], self.metric_values_range[1])]
                return metric_values
        except:
            import logging
            logging.exception(__name__)
        return self.metric_values

    def to_dict(self, fields2show=None):
        base_dict = super(InsightsAnalysis, self).to_dict()
        base_dict.pop('_results')
        base_dict.pop('_timerange_results')
        base_dict['results'] = self.results
        base_dict['timerange_results'] = self.timerange_results
        base_dict['status'] = self.status_progress
        base_dict['metric_values'] = self.compute_class_names()
        base_dict['metric_values_range'] = self.metric_values_range
        base_dict['level'] = self.get_timerange_level()
        return base_dict

    def get_timerange_level(self):
        try:
            return guess_timeslot_level(parse_datetime(self.filters['from']), parse_datetime(self.filters['to']))
        except:
            LOGGER.warn('Unknown period to determine the timerange level')

    def get_user(self):
        return User.objects.get(self.user)

    def initialize_timeslot_counts(self):
        time_results = {}
        self.time_increment = (self._cached_to_date - self._cached_from_date).days * 24 / float(self.NUM_TIMERANGE_SLOTS)
        for class_idx in range(-1, self.get_num_classes()):
            time_results[class_idx] = dict()
            for slot_idx in xrange(self.NUM_TIMERANGE_SLOTS):
                timeslot = datetime_to_timestamp_ms(self._cached_from_date + timedelta(hours=self.time_increment * slot_idx))
                time_results[class_idx][timeslot] = 0
        return time_results

    def get_num_classes(self):
        if self.metric_type == self.NUMERIC_METRIC:
            return len(self.metric_values) + 1
        else:
            return len(self.metric_values) + 2

    def get_timeslot_index(self, item):
        for idx in xrange(self.NUM_TIMERANGE_SLOTS):
            if hasattr(item, 'created_at') and utc(item.created_at) > self._cached_from_date + timedelta(hours=self.time_increment * idx):
                continue
            else:
                break
        return datetime_to_timestamp_ms(self._cached_from_date + timedelta(hours=self.time_increment * idx))

    def process(self):
        if self.application is None:
            self.application = self.get_user().account.selected_app
        if self.application == "Journey Analytics":
            # process_journeys_analysis.ignore(self)
            process_journeys_analysis(self)
        elif self.application == "Predictive Matching":
            # process_predictive_analysis.ignore(self)
            process_predictive_analysis(self)

    def save(self, **kw):
        if 'upsert' not in kw:
            kw['upsert'] = False
        # import json
        # analysis_file = open('analysis_' + str(self.id) + '.json', 'w')
        # json_data = {}
        # from bson import ObjectId
        # for key, val in self.data.iteritems():
        #     if not isinstance(val, ObjectId):
        #         json_data[key] = val
        # json.dump(json_data, analysis_file)
        # analysis_file.close()
        if self.id:
            self.objects.update(self.data, **kw)
        else:
            self.id = self.objects.insert(self.data, **kw)

    def start(self):
        datetime.strptime('2011-01-01', '%Y-%m-%d')  # dummy call (https://bugs.launchpad.net/openobject-server/+bug/947231/comments/8)
        self.process()

    def stop(self):
        self.progress = PROGRESS_STOPPED
        self.save()

    def restart(self):
        self.progress = 0
        self.save()
        self.start()

    def terminate(self):
        self.progress = PROGRESS_ERROR
        self.status_message = 'Process had been terminated.'
        self.save()

    @property
    def timerange_results(self):
        if self._timerange_results:
            return json.loads(self._timerange_results)
        return {}

    @property
    def results(self):
        # Just in case we need some post-processing done
        if self._results:
            return json.loads(self._results)
        return {}