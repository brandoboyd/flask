from datetime import datetime
from flask import jsonify, render_template, request
from urllib import unquote

from solariat.utils import timeslot
from solariat_bottle.views.base import BaseMultiActionView
from solariat_bottle.schema_data_loaders.csv import CsvDataLoader
from solariat_bottle.schema_data_loaders.base import WrongFileExtension
from solariat_bottle.settings import LOGGER
from solariat_bottle.app import app


KEY_NAME = 'name'


class DatasetView(BaseMultiActionView):

    url_rules = [
        ('/dataset/create', ['POST'], 'create'),
        ('/dataset/get/<path:name>', ['GET'], 'get'),
        ('/dataset/update/<path:name>', ['POST'], 'update'),
        ('/dataset/delete/<path:name>', ['POST'], 'delete'),
        ('/dataset/list', ['GET'], 'list'),

        ('/dataset/update_schema/<path:name>', ['POST'], 'update_schema'),
        ('/dataset/sync/apply/<path:name>', ['POST'], 'sync_dataset'),
        ('/dataset/sync/accept/<path:name>', ['POST'], 'accept_sync'),
        ('/dataset/sync/cancel/<path:name>', ['POST'], 'cancel_sync'),
        ('/dataset/view/<path:name>/<field_name>', ['GET'], 'view_dataset'),
    ]

    def get_parameters(self):
        params = super(DatasetView, self).get_parameters()
        if KEY_NAME in params:
            params[KEY_NAME] = unquote(params[KEY_NAME])
        return params

    def create(self, *args, **kwargs):
        ''' Create endpoint creates Dataset entity (:status=NEW)
        then makes schema analysis (:status=ANALYZED), then starts async
        task to load raw data into db (:status=LOADING). After ANALYZED
        user can invoke /dataset/update_schema/<name> to alter schema conf
        and then invoke /dataset/sync/<name> to sync the uploaded data.
        '''

        name = kwargs['name']
        csv_file = kwargs['csv_file']
        if not csv_file.filename.endswith('.csv'):
            raise WrongFileExtension('Wrong file extension, only .csv is supported.')

        sep = kwargs['sep']
        data_loader = CsvDataLoader(csv_file.stream, sep=sep)
        acc = self.user.account
        dataset = acc.datasets.add_dataset(self.user, name, data_loader)
        return dataset.to_dict()

    def update_schema(self, *args, **kwargs):
        '''Schema update allowed only before first /dataset/sync/<name>'''

        name = kwargs['name']
        acc = self.user.account
        dataset = acc.datasets.get_dataset(self.user, name)
        dataset.update_schema(kwargs['schema'])
        return dataset.to_dict()

    def sync_dataset(self, *args, **kwargs):
        '''Re-loads previously uploaded data into Dataset with latest schema.'''

        acc = self.user.account
        name = kwargs['name']
        dataset = acc.datasets.sync_dataset(self.user, name)
        return dataset.to_dict()

    def accept_sync(self, *args, **kwargs):
        '''Accept last sync, move :sync_status from SYNCED to IN_SYNC'''

        acc = self.user.account
        dataset = acc.datasets.get_dataset(self.user, kwargs['name'])
        dataset.accept_sync()
        return dataset.to_dict()

    def cancel_sync(self, *args, **kwargs):
        '''Cancel last sync, move :sync_status from SYNCED to OUT_OF_SYNC'''

        acc = self.user.account
        dataset = acc.datasets.get_dataset(self.user, kwargs['name'])
        dataset.cancel_sync()
        return dataset.to_dict()

    def update(self, *args, **kwargs):
        '''Append new data into existing Dataset. Schema is locked at
        the moment, so only same data structure is allowed to upload.
        Statuses start changing from LOADING then LOADED. :sync_status
        left IN_SYNC.
        '''

        csv_file = kwargs['csv_file']
        sep = kwargs['sep']
        if not csv_file.filename.endswith('.csv'):
            raise WrongFileExtension('Wrong file extension, only .csv is supported.')

        acc = self.user.account
        dataset = acc.datasets.get_dataset(self.user, kwargs['name'])
        if not dataset:
            return

        data_loader = CsvDataLoader(csv_file.stream, sep=sep)
        acc.datasets.update_dataset(self.user, dataset, data_loader)
        return dataset.to_dict()

    def get(self, *args, **kwargs):
        user = self.user
        acc = user.account
        name = kwargs['name']
        dataset = acc.datasets.get_dataset(user, name)
        if not dataset:
            return
        return dataset.to_dict(include_data_distribution=True, include_cardinalities=True)

    def list(self, *args, **kwargs):
        user = self.user
        acc = user.account
        from_dt = to_dt = None
        if 'from' in kwargs:
            from_dt = timeslot.parse_datetime(kwargs['from'])
            to_dt = timeslot.parse_datetime(kwargs['to'])
        datasets = acc.datasets.get_all_datasets(user, from_dt, to_dt)
        return [s.to_dict() for s in datasets]

    def delete(self, *args, **kwargs):
        acc = self.user.account
        if acc.datasets.delete_dataset(self.user, kwargs['name']):
            return {}

    def view_dataset(self, name, field_name, skip=0, limit=20):
        acc = self.user.account
        skip = int(skip)
        limit = min(int(limit), 100)

        dataset = acc.datasets.get_dataset(self.user, name)
        if not dataset:
            return

        data_coll = dataset.data_coll
        total_items = data_coll.count()
        result = data_coll.find({}, {field_name: 1, '_id': 0}).sort('_id', 1).skip(skip).limit(limit)
        values = [d[field_name] for d in result]

        if values and isinstance(values[0], datetime):
            for i in xrange(len(values)):
                values[i] = values[i].ctime()

        return {
                'list': values,
                'skip': skip,
                'limit': limit,
                'total_items': total_items,
        }


DatasetView.register(app)
