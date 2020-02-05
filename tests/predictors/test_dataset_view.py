import csv
import json
import os
import tempfile

import tweepy

from solariat_bottle.app import get_api_url
from solariat_bottle.db.account import Account
from solariat_bottle.db.dataset import Dataset
from solariat_bottle.db.schema_based import KEY_NAME, KEY_TYPE, TYPE_STRING, TYPE_INTEGER, TYPE_TIMESTAMP
from solariat_bottle.schema_data_loaders.csv import CsvDataLoader
from solariat_bottle.tests.base import UICaseSimple
from solariat_bottle.tests.data import __file__ as data_path
from solariat_bottle.settings import LOGGER


DATA_PATH = os.path.dirname(data_path)
CSV_FILENAME = 'test_dataset.csv'
CSV_FILEPATH = os.path.join(DATA_PATH, CSV_FILENAME)
CSV_SEPARATOR = '\t'
CREATE_UPDATE_DATASET_NAME = 'CreateUpdateDataset'
DATASET_NAME = 'Dataset1'


class DatasetViewTest(UICaseSimple):

    def setUp(self):
        super(DatasetViewTest, self).setUp()
        self.login(self.user.email, self.password)

    def create_dataset(self, name):
        acc = self.user.account
        with open(CSV_FILEPATH) as csv_file:
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            dataset = acc.datasets.add_dataset(self.user, name, data_loader)
            return dataset

    def delete_dataset(self, name):
        self.user.account.datasets.delete_dataset(self.user, CREATE_UPDATE_DATASET_NAME)

    def get_post_data(self, csv_file):
        file_obj = (csv_file, CSV_FILENAME)
        return dict(name=CREATE_UPDATE_DATASET_NAME,
                    csv_file=file_obj,
                    sep=CsvDataLoader.TAB)

    def test_dataset_workflow(self):
        from solariat_bottle.utils.predictor_events import translate_column

        acc = self.user.account

        # create
        with open(CSV_FILEPATH) as csv_file:
            post_data = self.get_post_data(csv_file)
            # test create
            resp = self.client.post(
                '/dataset/create',
                buffered=True,
                content_type='multipart/form-data',
                data=post_data,
                base_url='https://localhost')

            self.assertEqual(resp.status_code, 201)
            data = json.loads(resp.data)
            self.assertTrue(data['ok'])
            self.assertEqual(data['data']['sync_status'], Dataset.OUT_OF_SYNC)
            self.assertTrue(data['data']['schema'])
            self.assertFalse(data['data']['is_locked'])
            dataset = acc.datasets.get_dataset(self.user, CREATE_UPDATE_DATASET_NAME)
            schema = dataset.schema
            DataClass = dataset.get_data_class()
            self.assertEqual(DataClass.objects.count(), 50)

        # test update schema
        # based on test data, just lets change one column type
        itx_col_name = translate_column('INTERACTION_ID')
        itx_col = [s for s in schema if s['name'] == itx_col_name][0]
        assert itx_col['type'] in ('integer', 'timestamp'), (itx_col['type'], itx_col_name)
        itx_col['type'] = 'string'
        data = self._post('/dataset/update_schema/%s' % CREATE_UPDATE_DATASET_NAME,
                          {'schema': schema},
                          expected_code=201)
        dataset = acc.datasets.get_dataset(self.user, CREATE_UPDATE_DATASET_NAME)
        self.assertTrue(bool([1 for col in dataset.schema if col['name'] == itx_col_name \
                                                     and col['type'] == 'string']))

        # test invalid schema
        broken_schema = schema[1:]
        data = self._post('/dataset/update_schema/%s' % CREATE_UPDATE_DATASET_NAME,
                          {'schema': broken_schema},
                          expected_result=False,
                          expected_code=500)

        # cannot accept sync until it's happens
        data = self._post('/dataset/sync/accept/%s' % CREATE_UPDATE_DATASET_NAME,
                          {},
                          expected_result=False,
                          expected_code=500)

        # let's include the case when not all data could be synced
        FAIL_COL_NAME = 'STAT_INI_1'
        dataset.reload()
        col = [col for col in dataset.schema if col[KEY_NAME] == FAIL_COL_NAME][0]
        self.assertEqual(col[KEY_TYPE], TYPE_INTEGER)
        raw_data = dataset.data_coll.find_one()
        dataset.data_coll.update({'_id': raw_data['_id']}, {'$set': {FAIL_COL_NAME: 'fail'}})

        # test applying schema on dataset (synchronous mode for testing)
        data = self._post('/dataset/sync/apply/%s' % CREATE_UPDATE_DATASET_NAME,
                          {},
                          expected_code=201)

        self.assertEqual(data['data']['sync_status'], Dataset.SYNCED)
        self.assertTrue(data['data']['is_locked'])
        # we manually fail 1 raw sync
        self.assertEqual(data['data']['items_synced'], 49)

        # until we accpet/discard last sync,
        # our original collection keeps origin data
        dataset = acc.datasets.get_dataset(self.user, CREATE_UPDATE_DATASET_NAME)
        DataClass = dataset.get_data_class()
        self.assertEqual(DataClass.objects.count(), 50)

        data = self._post('/dataset/sync/apply/%s' % CREATE_UPDATE_DATASET_NAME,
                          {},
                          expected_result=False,
                          expected_code=500)

        data = self._post('/dataset/sync/accept/%s' % CREATE_UPDATE_DATASET_NAME,
                          {},
                          expected_code=201)
        dataset = acc.datasets.get_dataset(self.user, CREATE_UPDATE_DATASET_NAME)
        DataClass = dataset.get_data_class()
        self.assertEqual(DataClass.objects.count(), 49)

        # test update, append 50 items again
        with open(CSV_FILEPATH) as csv_file:
            post_data = self.get_post_data(csv_file)
            resp = self.client.post(
                '/dataset/update/%s' % CREATE_UPDATE_DATASET_NAME,
                buffered=True,
                content_type='multipart/form-data',
                data=post_data,
                base_url='https://localhost')

            data = json.loads(resp.data)
            self.assertEqual(resp.status_code, 201)
            self.assertTrue(data['ok'])
            self.assertEqual(data['data']['rows'], 99)
            dataset = acc.datasets.get_dataset(self.user, CREATE_UPDATE_DATASET_NAME)
            DataClass = dataset.get_data_class()
            self.assertEqual(DataClass.objects.count(), 99)

        data = self._post('/dataset/update_schema/%s' % CREATE_UPDATE_DATASET_NAME,
                          {'schema': schema},
                          expected_result=False,
                          expected_code=500)

        # # prepare wrong schema for data update
        from StringIO import StringIO
        stream = StringIO()
        with open(CSV_FILEPATH) as csv_file:
            for row in csv_file:
                cols = row.split(CSV_SEPARATOR)
                if len(cols) > 1:
                    row = CSV_SEPARATOR.join(cols[1:])
                stream.write(row)
        stream.seek(0)
        post_data = self.get_post_data(stream)
        resp = self.client.post(
            '/dataset/update/%s' % CREATE_UPDATE_DATASET_NAME,
            buffered=True,
            content_type='multipart/form-data',
            data=post_data,
            base_url='https://localhost')

        self.assertEqual(resp.status_code, 500)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])
        dataset.drop_data()

    def test_get_dataset(self):
        dataset = self.create_dataset(DATASET_NAME)
        data = self._get('/dataset/get/%s' % DATASET_NAME, {})
        item = data['data']
        self.assertEqual(item['name'], DATASET_NAME)
        self.assertIsNotNone(item['schema'])
        self.assertIsNotNone(item['mongo_collection'])
        dataset.drop_data()

    def test_list_dataset(self):
        dataset = self.create_dataset(DATASET_NAME)
        data = self._get('/dataset/list', {})
        items = data['data']
        self.assertTrue(len(items) >= 1)
        item = [i for i in items if i['name'] == DATASET_NAME]
        self.assertTrue(item)
        dataset.drop_data()

    def test_delete_dataset(self):
        name = 'TestDelete'
        dataset = self.create_dataset(name)
        self._post('/dataset/delete/%s' % dataset.name, {}, expected_code=201)
        dataset.reload()
        self.assertTrue(dataset.is_archived)

    def test_comma_separator(self):
        name = 'TestCommaSeparator'

        def create_post_data():
            csv_file = tempfile.TemporaryFile('w+')
            writer = csv.writer(csv_file, delimiter=',')
            writer.writerow(['FName', 'LName',    'SN'])
            writer.writerow(['ram',   'shakya',   None])
            writer.writerow(['shyam', 'shrestha', 0])
            writer.writerow(['hari',  'shrestha', 1])
            writer.writerow(['shyam', 'shakya',   2])
            csv_file.flush()
            csv_file.seek(0)

            return dict(name=name,
                        csv_file=(csv_file, 'filename.csv'),
                        sep=CsvDataLoader.COMMA)

        post_data = create_post_data()

        resp = self.client.post(
            '/dataset/create',
            buffered=True,
            content_type='multipart/form-data',
            data=post_data,
            base_url='https://localhost')

        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        dataset = self.user.account.datasets.get_dataset(self.user, name)
        self.assertEqual(len(dataset.schema), 3)
        self.assertEqual(dataset.rows, 4)

        dataset.apply_sync()
        dataset.accept_sync()

        post_data = create_post_data()
        resp = self.client.post(
            '/dataset/update/%s' % name,
            buffered=True,
            content_type='multipart/form-data',
            data=post_data,
            base_url='https://localhost')

        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        dataset.reload()
        self.assertTrue(dataset.rows, 8)

    def test_facet_list(self):
        name = 'TestFacet'
        dataset = self.create_dataset(name)
        data = self._get('/facet-filters/dataset/%s' % dataset.name, {})
        self.assertEqual(len(data['filters']), 50)

        # convert list to dict for membership testing
        data_dict = {each['name']: each for each in data['filters']}

        string_facets = {k: v for k, v in data_dict.iteritems() if v['type'] == 'string'}
        integer_facets = {k: v for k, v in data_dict.iteritems() if v['type'] == 'integer'}
        timestamp_facets = {k: v for k, v in data_dict.iteritems() if v['type'] == 'timestamp'}

        self.assertEqual(len(string_facets), 30)
        self.assertEqual(len(integer_facets), 18)
        self.assertEqual(len(timestamp_facets), 2)

        self.assertTrue(all('values' in each for each in string_facets.itervalues()))
