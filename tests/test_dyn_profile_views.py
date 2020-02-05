import json
import os
import unittest

from solariat_bottle.tests.base import UICaseSimple
from solariat_bottle.tests.data import __file__ as data_path
from solariat_bottle.settings import LOGGER
from solariat_bottle.db.schema_based import KEY_IS_ID, KEY_NAME, KEY_TYPE, KEY_EXPRESSION, TYPE_INTEGER
from solariat_bottle.db.dynamic_profiles import DynamicProfile
from solariat_bottle.schema_data_loaders.csv import CsvDataLoader


DATA_PATH = os.path.dirname(data_path)
CSV_FILENAME = 'test_dataset.csv'
CSV_FILEPATH = os.path.join(DATA_PATH, CSV_FILENAME)
CSV_SEPARATOR = '\t'


class DynamicProfileViewsMixin(object):

    acc_attr_name = None

    def setUp(self):
        super(DynamicProfileViewsMixin, self).setUp()
        self.login(self.user.email, self.password)

    def get_post_data(self, csv_file):
        file_obj = (csv_file, CSV_FILENAME)
        return dict(csv_file=file_obj, sep=CsvDataLoader.TAB)

    def test_workflow(self):
        from solariat_bottle.utils.predictor_events import translate_column
        acc = self.user.account

        # test create
        with open(CSV_FILEPATH) as csv_file:
            post_data = self.get_post_data(csv_file)
            # test create
            resp = self.client.post(
                '%s/create' % self.ENDPOINT,
                buffered=True,
                content_type='multipart/form-data',
                data=post_data,
                base_url='https://localhost')

            self.assertEqual(resp.status_code, 201)
            data = json.loads(resp.data)
            self.assertTrue(data['ok'])
            self.assertFalse(data['data']['is_locked'])
            self.assertEqual(data['data']['sync_status'], DynamicProfile.OUT_OF_SYNC)

            self.assertFalse(data['data']['schema'])
            self.assertTrue(data['data']['discovered_schema'])

        # test get
        data2 = self._get('%s/get' % self.ENDPOINT, {})
        self.assertDictContainsSubset(data['data'], data2['data'])

        manager = getattr(acc, self.acc_attr_name)
        profile = manager.get(self.user)
        origin_schema = [dict(i) for i in profile.discovered_schema]
        DataClass = profile.get_data_class()
        self.assertEqual(DataClass.objects.count(), 50)

        # test update schema: copy values from discovered_schema, add expression col
        copy_cols = ('INTERACTION_ID', 'START_TS', 'END_TS', 'RESOURCE_NAME', 'EMPLOYEE_ID')
        schema = [col for col in profile.discovered_schema if col[KEY_NAME] in copy_cols]
        for col in schema:
            if col[KEY_NAME] == 'INTERACTION_ID':
                col[KEY_TYPE] = TYPE_INTEGER
                break
        EXP_COL_NAME = 'EXP_COL'
        schema.append({
            KEY_NAME: EXP_COL_NAME,
            KEY_TYPE: TYPE_INTEGER,
            KEY_EXPRESSION: 'INTERACTION_ID % 2',
        })

        #  Profile schema or imported data must contain exact one "ID_FIELD"
        data = self._post('%s/update_schema' % self.ENDPOINT,
                          {'schema': schema},
                          expected_result=False,
                          expected_code=500)

        id_field = [col for col in schema if col[KEY_NAME] == 'EMPLOYEE_ID'][0]
        id_field[KEY_IS_ID] = True
        data = self._post('%s/update_schema' % self.ENDPOINT,
                          {'schema': schema},
                          expected_code=201)
        profile = manager.get(self.user)
        self.assertEqual(schema, profile.schema)

        # test we can modify schema columns (not allowed for datasets)
        new_schema = [col for col in schema if col[KEY_NAME] != 'END_TS']
        assert schema != new_schema
        data = self._post('%s/update_schema' % self.ENDPOINT,
                          {'schema': new_schema},
                          expected_code=201)

        # cannot accept sync until it's happens
        data = self._post('%s/sync/accept' % self.ENDPOINT,
                          {},
                          expected_result=False,
                          expected_code=500)

        # let's include the case when not all data could be synced
        FAIL_COL_NAME = 'INTERACTION_ID'
        profile.reload()
        col = [col for col in profile.schema if col[KEY_NAME] == FAIL_COL_NAME][0]
        self.assertEqual(col[KEY_TYPE], TYPE_INTEGER)
        raw_data = profile.data_coll.find_one()
        profile.data_coll.update({'_id': raw_data['_id']}, {'$set': {FAIL_COL_NAME: 'fail'}})

        # test applying schema (synchronous mode for testing)
        data = self._post('%s/sync/apply' % self.ENDPOINT,
                          {},
                          expected_code=201)

        self.assertEqual(data['data']['sync_status'], DynamicProfile.SYNCED)
        self.assertTrue(data['data']['is_locked'])
        # we manually fail 1 raw sync
        self.assertEqual(data['data']['items_synced'], 46) # 3 ids: None + 1 failed

        # until we accpet/discard last sync,
        # our original collection keeps origin data
        profile = manager.get(self.user)
        DataClass = profile.get_data_class()
        self.assertEqual(DataClass.objects.count(), 50)

        data = self._post('%s/sync/apply' % self.ENDPOINT,
                          {},
                          expected_result=False,
                          expected_code=500)

        data = self._post('%s/sync/accept' % self.ENDPOINT,
                          {},
                          expected_code=201)

        self.assertEqual(data['data']['sync_status'], DynamicProfile.IN_SYNC)
        profile = manager.get(self.user)
        DataClass = profile.get_data_class()
        self.assertEqual(DataClass.objects.count(), 46)
        for data in profile.get_data():
            if data.INTERACTION_ID is None:
                continue
            self.assertEqual(data.INTERACTION_ID % 2, data.EXP_COL)

        # test update
        with open(CSV_FILEPATH) as csv_file:
            post_data = self.get_post_data(csv_file)
            resp = self.client.post(
                '%s/update' % self.ENDPOINT,
                buffered=True,
                content_type='multipart/form-data',
                data=post_data,
                base_url='https://localhost')

            data = json.loads(resp.data)
            self.assertEqual(resp.status_code, 201)
            self.assertTrue(data['ok'])
            # since file is the same, almost all records will fail with duplicated ID errors
            # except 1 item, which we fail manually for sync test, so res: 47 + 1
            self.assertEqual(data['data']['rows'], 46 + 1)
            profile = manager.get(self.user)
            DataClass = profile.get_data_class()
            self.assertEqual(DataClass.objects.count(), 46 + 1)

        # prepare schema without some columns, it fails for dataset and ok for profiles
        # TODO: share in utils with datasets
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
            '%s/update' % self.ENDPOINT,
            buffered=True,
            content_type='multipart/form-data',
            data=post_data,
            base_url='https://localhost')

        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        # drop data collections
        profile.drop_data()

        # test delete
        self._post('%s/delete' % self.ENDPOINT, {}, expected_code=201)
        profile.reload()
        self.assertTrue(profile.is_archived)

    def test_change_id_column(self):
        from solariat_bottle.utils.predictor_events import translate_column

        manager = getattr(self.user.account, self.acc_attr_name)
        with open(CSV_FILEPATH) as csv_file:
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            profile = manager.create(self.user, data_loader)

        copy_cols = ('INTERACTION_ID', 'START_TS', 'END_TS')
        schema = [col for col in profile.discovered_schema if col[KEY_NAME] in copy_cols]
        id_col_name = 'INTERACTION_ID'
        for col in schema:
            if col[KEY_NAME] == id_col_name:
                col[KEY_IS_ID] = True
                break

        data = self._post('%s/update_schema' % self.ENDPOINT,
                          {'schema': schema},
                          expected_code=201)
        data = self._get('%s/get' % self.ENDPOINT, {})
        id_col = [col for col in data['data']['schema'] if KEY_IS_ID in col][0]
        self.assertEqual(id_col[KEY_NAME], id_col_name)

        self.assertEqual(data['data']['schema'], schema)
        data = self._post('%s/sync/apply' % self.ENDPOINT,
                          {},
                          expected_code=201)

        profile.reload()
        raw_data = profile.data_sync_coll.find_one()
        self.assertEqual(raw_data['_id'], raw_data[id_col_name])

        data = self._post('%s/sync/accept' % self.ENDPOINT,
                          {},
                          expected_code=201)

        profile.reload()
        data = profile.get_data()[0]
        self.assertEqual(data.id, getattr(data, id_col_name))


class CustomerProfileViewTest(DynamicProfileViewsMixin, UICaseSimple):
    ENDPOINT = '/customer_profile'
    acc_attr_name = 'customer_profile'


class AgentProfileViewTest(DynamicProfileViewsMixin, UICaseSimple):
    ENDPOINT = '/agent_profile'
    acc_attr_name = 'agent_profile'
