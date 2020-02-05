from solariat_bottle.db.schema_based import (SchemaBased, SchemaValidationError,
                                             finish_data_load, sync_data,
                                             get_query_by_dates,
                                             KEY_EXPRESSION, KEY_NAME)
from solariat.db import fields
from solariat_bottle.settings import LOGGER, AppException
from solariat_bottle.utils.schema import get_dataset_functions

import json
import time
import datetime
import threading


# fields with cardinality lesser than this number will store unique values in db
KEY_CREATED_AT = 'created_time'

class DatasetDataClassIsNotRegistered(Exception):
    pass

class DatasetUsedByPredictor(AppException):
    pass


class Dataset(SchemaBased):

    def_type = fields.StringField()
    _data_distribution = fields.StringField(default='{}')

    @property
    def is_locked(self):
        '''For Events schema editing is locked only when SYNCING,
        since Dataset allows to edit schema only once, IN_SYNC
        is also counted.'''

        if self.schema and self.sync_status in (self.SYNCING, self.IMPORTING, self.SYNCED, self.IN_SYNC):
            return True
        return False

    def refresh_distribution_counts(self):
        distributions = dict()
        if not self.created_at_field or not self.sync_status == self.IN_SYNC:
            return None
        match_query = {self.created_at_field: {'$ne': None}}
        group_by_query = {'$group': {"_id": {"year": {"$year": "$" + self.created_at_field},
                                             "month": {"$month": "$" + self.created_at_field},
                                             "day": {"$dayOfMonth": "$" + self.created_at_field}},
                          'count': {"$sum": 1}}}
        pipeline = [{"$match": match_query},
                    group_by_query]
        result = self.data_coll.aggregate(pipeline)
        for entry in result['result']:
            # {u'count': 1, u'_id': {u'year': 2016, u'day': 2, u'month': 7}}
            date = time.mktime(datetime.datetime(year=entry['_id']['year'],
                                                 month=entry['_id']['month'],
                                                 day=entry['_id']['day']).timetuple())
            distributions[date] = entry['count']
        self._data_distribution = json.dumps(distributions)
        self.save()

    def data_distribution(self, from_date=None, to_date=None):
        if not self.created_at_field or not self.sync_status == self.IN_SYNC:
            return None
        distributions = json.loads(self._data_distribution)
        if not distributions:
            self.refresh_distribution_counts()
        processed_result = []
        for key, val in distributions.iteritems():
            processed_result.append([float(key), val])
        return sorted(processed_result, key=lambda x: x[0])

    def _validate_schema(self, schema_json):
        schema = self.schema or self.discovered_schema
        current_fields = {col[KEY_NAME] for col in schema if KEY_EXPRESSION not in col}
        input_fields = {col[KEY_NAME] for col in schema_json}
        if len(current_fields & input_fields) != len(current_fields):
            LOGGER.error('Input schema columns: %s \n\nis different from '
                         'current: %s' % (input_fields, current_fields))
            raise SchemaValidationError('Input schema columns is different from current.')

    def to_dict(self, include_data_distribution=False,
                include_expression_context=True, **kw):
        res = super(Dataset, self).to_dict(**kw)
        if include_data_distribution:
            res['data_distribution'] = self.data_distribution()
        if include_expression_context:
            res['expression_context'] = self.get_expression_context()
        return res

    def get_expression_context(self):
        dataset_class = self.get_data_class()
        return {
            "context": [x.name for x in dataset_class.schema_fields],
            "functions": get_dataset_functions(),
        }

    def import_data(self, user, data_loader, skip_cardinalities=False):
        super(Dataset, self).import_data(user, data_loader, skip_cardinalities)
        self.refresh_distribution_counts()


class DatasetManagerWrapper(object):

    def __init__(self, parent):
        self.parent = parent

    def add_dataset(self, user, name, data_loader):
        '''
        Create the Dataset and grant user permissions.
        '''

        try :
            schema = data_loader.read_schema()
        except AppException :
            raise

        dataset = Dataset.create_by_user(user, self.parent.id, name)
        start = time.time()
        LOGGER.info('Analysis of input data took: %s', time.time() - start)
        dataset.update(schema=schema)
        finish_data_load.async(user, dataset, data_loader)
        return dataset

    def sync_dataset(self, user, name):
        dataset = self.get_dataset(user, name)
        sync_data.async(dataset)
        return dataset

    def update_dataset(self, user, dataset, data_loader):
        schema = data_loader.read_schema()
        dataset._validate_schema(schema)
        finish_data_load.async(user, dataset, data_loader)
        return dataset

    def delete_dataset(self, user, name):
        dataset = self.get_dataset(user, name)
        if not dataset:
            return

        from solariat_bottle.db.predictors.base_predictor import BasePredictor
        predictor = BasePredictor.objects.find_one(dataset=dataset.id)
        if predictor:
            raise DatasetUsedByPredictor('Dataset is used by Predictor "%s"' % predictor.name)

        dataset.drop_data()
        dataset.delete_by_user(user)
        return True

    def get_dataset(self, user, name):
        return Dataset.objects.find_one_by_user(user, parent_id=self.parent.id, name=name)

    def get_all_datasets(self, user, from_dt=None, to_dt=None):
        date_query = get_query_by_dates(from_dt, to_dt)
        return Dataset.objects.find_by_user(user, parent_id=self.parent.id, **date_query)


class DatasetsManager(object):
    def __get__(self, instance, cls):
        if instance is None:
            return None
        if not hasattr(instance, '_dataset_manager'):
            setattr(instance, '_dataset_manager', DatasetManagerWrapper(instance))
        return instance._dataset_manager

