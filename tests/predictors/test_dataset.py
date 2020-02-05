from solariat_bottle.tests.base import BaseCase
from solariat_bottle.tests.predictors.test_dataset_view import CSV_FILEPATH
from solariat_bottle.settings import LOGGER
from solariat_bottle.db.dataset import Dataset
from solariat_bottle.db.schema_based import (SchemaBased,
                                             NameDuplicatedError,
                                             ImproperStateError,
                                             OutOfSyncError,
                                             SchemaValidationError,
                                             finish_data_load,
                                             KEY_NAME, KEY_TYPE,
                                             KEY_EXPRESSION,
                                             TYPE_STRING, TYPE_INTEGER, TYPE_TIMESTAMP)
from solariat_bottle.schema_data_loaders.csv import CsvDataLoader

from mock import patch
import unittest
import os
import csv
import tempfile

from solariat_bottle.tests.data import __file__ as data_path
DATA_PATH = os.path.dirname(data_path)
CSV_SHORT_FILENAME = 'test_dataset_short.csv'
CSV_SHORT_FILEPATH = os.path.join(DATA_PATH, CSV_SHORT_FILENAME)


TEST_MAX_LINES = 5
TEST_DATASET_1 = 'TestDataset1'
TEST_DATASET_2 = 'TestDataset2'
TEST_DATASET_3 = 'TestDataset3'


class DatasetTest(BaseCase):

    def create_and_load_dataset(self, name, set_schema_after_load=True):
        acc = self.user.account
        with open(CSV_SHORT_FILEPATH) as csv_file:
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            dataset = acc.datasets.add_dataset(self.user, name, data_loader)
            return dataset

    def create_dataset(self, name):
        return Dataset.create(self.user.account.id, name)

    def load_dataset(self, dataset):
        with open(CSV_SHORT_FILEPATH) as csv_file:
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            finish_data_load.async(self.user, dataset, data_loader)

    def get_dataset(self, name):
        return self.user.account.datasets.get_dataset(self.user, name)

    def test_name_for_account_is_unique(self):
        from bson.objectid import ObjectId

        name = 'TestUniqueName'
        dataset = Dataset.create_by_user(self.user, self.user.account.id, name)
        with self.assertRaises(NameDuplicatedError):
            Dataset.create(self.user.account.id, name)

        some_other_acc_id = ObjectId()
        Dataset.create(some_other_acc_id, name)

        # if we delete dataset, we can use this name again
        dataset.delete_by_user(self.user)
        name = 'TestUniqueName'
        dataset = Dataset.create(self.user.account.id, name)

    def __get_dataset(self):
        name = 'Create Dataset Test'
        acc = self.user.account

        # test create
        dataset = Dataset.create_by_user(self.user, acc.id, name)
        dataset = Dataset.objects.find_one_by_user(self.user, id=dataset.id)
        self.assertTrue(dataset)
        self.assertEqual(dataset.parent_id, acc.id)
        self.assertEqual(dataset.name, name)
        self.assertEqual(dataset.sync_status, Dataset.OUT_OF_SYNC)

        with open(CSV_SHORT_FILEPATH) as csv_file:
            filelen = len([1 for _ in csv_file])
            csv_file.seek(0)
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            discovered_schema = data_loader.read_schema()
            dataset.update(schema=discovered_schema)
            finish_data_load.async(self.user, dataset, data_loader)

        self.assertEqual(dataset.sync_status, Dataset.OUT_OF_SYNC)
        self.assertEqual(dataset.load_progress, 100)
        self.assertEqual(dataset.data_coll.count(), filelen - 1)  # minus head
        self.assertEqual(dataset.data_coll.count(), dataset.rows)

        data_item = dataset.data_coll.find_one()
        self.assertTrue({c[KEY_NAME] for c in dataset.schema} <= set(data_item.keys()))

        # TODO: test full data integrity!!!
        return dataset

    # @unittest.skip('dev')
    def test_create_and_load_dataset(self):
        dataset = self.__get_dataset()
        dataset.drop_data()

    # @unittest.skip('dev')
    @patch('solariat_bottle.schema_data_loaders.csv.'
           'CsvDataLoader.MAX_ANALYSIS_LINES', TEST_MAX_LINES)
    def test_schema_parse_max_lines(self):
        import pandas

        acc = self.user.account
        with open(CSV_SHORT_FILEPATH) as csv_file:
            with patch('pandas.read_csv',
                       wraps=pandas.read_csv) as parse_meth:
                name = 'test_schema_analysis'
                # dataset = Dataset.create(acc.id, self.user, 'test_schema_analysis')
                data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
                data_loader.read_schema()

                input_file = parse_meth.call_args[0][0]
                input_file.seek(0)
                filelen = len([1 for _ in input_file])
                self.assertEqual(TEST_MAX_LINES + 1, filelen)
                acc.datasets.delete_dataset(self.user, name)

    # TODO: test json loader
    # def test_json_loader(self):
    #     pass

    # @unittest.skip('dev')
    def test_update_schema(self):
        name = 'TestUpdateSchema'
        dataset = self.create_and_load_dataset(name)

        with self.assertRaises(ImproperStateError):
            dataset.accept_sync()
        with self.assertRaises(ImproperStateError):
            dataset.cancel_sync()

        TEST_SCHEMA = [{KEY_NAME: 'column', KEY_TYPE: TYPE_STRING}]
        with self.assertRaises(SchemaValidationError):
            dataset.update_schema(TEST_SCHEMA)
        self.assertNotEqual(dataset.schema, TEST_SCHEMA)

        # dataset schema could not be different from schema by columns
        new_schema = [{KEY_NAME: col[KEY_NAME], KEY_TYPE: TYPE_INTEGER} for col in dataset.schema]
        dataset.update_schema(new_schema)
        self.assertEqual(dataset.schema, new_schema)
        dataset.drop_data()

        # also, we can apply with current suggested schema right away
        name = 'TestApplyWithoutSchemaUpdate'
        dataset = self.create_and_load_dataset(name)
        dataset.apply_sync()
        self.assertEqual(dataset.sync_status, Dataset.SYNCED)
        dataset.drop_data()

    def test_apply_sync_and_accept_sync(self):
        name = 'TestApplySchema'
        dataset = Dataset.create(self.user.account.id, name)
        self.assertEqual(dataset.sync_status, Dataset.OUT_OF_SYNC)
        self.assertEqual(dataset.rows, 0)
        self.assertEqual(dataset.sync_progress, 0)
        self.assertFalse(dataset.schema)

        with open(CSV_FILEPATH) as csv_file:
            raw_items = len([1 for _ in csv_file]) - 1  # minus head
            csv_file.seek(0)
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            dataset.schema = data_loader.read_schema()
            dataset.save()

        # cannot do csv_file.seek() because pandas close the file
        with open(CSV_FILEPATH) as csv_file:
            data_loader.csv_file = csv_file
            finish_data_load.async(self.user, dataset, data_loader)

        self.assertEqual(dataset.rows, raw_items)

        # let's include the case when not all data could be synced
        FAIL_COL_NAME = 'STAT_INI_1'
        # dataset.update_schema(dataset.discovered_schema)
        self.assertTrue(dataset.schema)
        col = [col for col in dataset.schema if col[KEY_NAME] == FAIL_COL_NAME][0]
        self.assertEqual(col[KEY_TYPE], TYPE_INTEGER)

        raw_data = dataset.data_coll.find_one()
        dataset.data_coll.update({'_id': raw_data['_id']}, {'$set': {FAIL_COL_NAME: 'fail'}})

        # start of sync
        self.assertEqual(dataset.sync_status, Dataset.OUT_OF_SYNC)
        dataset.apply_sync()
        self.assertEqual(dataset.sync_status, Dataset.SYNCED)
        self.assertEqual(dataset.sync_progress, 100)
        self.assertEqual(dataset.rows, raw_items)
        self.assertEqual(dataset.data_coll.count(), raw_items)
        d = dataset
        self.assertTrue(d.sync_collection and d.sync_collection != d.mongo_collection)
        items_synced = dataset.items_synced
        self.assertEqual(dataset.data_sync_coll.count(), items_synced)
        self.assertNotEqual(raw_items, items_synced)  # because we fail 1 item manually
        self.assertTrue(FAIL_COL_NAME in dataset.sync_errors)
        self.assertEqual(len(dataset.sync_errors[FAIL_COL_NAME]), 1)

        # we cannot apply once more time since no changes to schema were made
        with self.assertRaises(ImproperStateError):
            dataset.apply_sync()

        dataset.accept_sync()
        self.assertEqual(dataset.sync_status, Dataset.IN_SYNC)
        self.assertEqual(dataset.rows, items_synced)
        self.assertEqual(dataset.data_coll.count(), items_synced)
        dataset.drop_data()

    # @unittest.skip('dev')
    def test_cancel_edit_apply_flow(self):
        from solariat_bottle.utils.predictor_events import translate_column
        from solariat.db.mongo import get_connection
        from datetime import datetime

        name = 'TestCancelUpdateCancelLoop'
        ITX_COL_NAME = translate_column('INTERACTION_ID')

        dataset = self.create_and_load_dataset(name)
        new_schema = [dict(col) for col in dataset.schema]
        itx_col = [col for col in new_schema if col[KEY_NAME] == ITX_COL_NAME][0]
        self.assertTrue(itx_col[KEY_TYPE] == TYPE_TIMESTAMP)
        raw_data = dataset.data_coll.find_one()
        self.assertTrue(isinstance(raw_data[ITX_COL_NAME], datetime))

        itx_col[KEY_TYPE] = TYPE_STRING
        dataset.update_schema(new_schema)
        dataset.reload()
        assert dataset.schema == new_schema

        dataset.apply_sync()
        itx_col = [col for col in dataset.schema if col[KEY_NAME] == ITX_COL_NAME][0]
        self.assertTrue(itx_col[KEY_TYPE] == TYPE_STRING,
                        'type:%s, but must be:%s' % (itx_col[KEY_TYPE], TYPE_STRING))
        raw_sync_data = dataset.data_sync_coll.find_one()
        self.assertTrue(isinstance(raw_sync_data[ITX_COL_NAME], basestring))

        self.assertEqual(dataset.sync_status, Dataset.SYNCED)
        dataset.cancel_sync()
        self.assertEqual(dataset.sync_status, Dataset.OUT_OF_SYNC)

        # check sync collection does not exists anymore
        colls = get_connection().collection_names(include_system_collections=False)
        self.assertTrue(dataset.sync_collection not in colls)

        TEST_SCHEMA = [dict(col) for col in dataset.schema]
        itx_col = [col for col in TEST_SCHEMA if col[KEY_NAME] == ITX_COL_NAME][0]
        itx_col[KEY_TYPE] = TYPE_INTEGER
        dataset.update_schema(TEST_SCHEMA)
        self.assertEqual(dataset.schema, TEST_SCHEMA)

        dataset.apply_sync()
        itx_col = [col for col in dataset.schema if col[KEY_NAME] == ITX_COL_NAME][0]
        self.assertTrue(itx_col[KEY_TYPE] == TYPE_INTEGER)
        raw_sync_data = dataset.data_sync_coll.find_one()
        self.assertTrue(isinstance(raw_sync_data[ITX_COL_NAME], (int, long, float)))

        dataset.accept_sync()
        self.assertTrue(dataset.sync_status, Dataset.IN_SYNC)
        colls = get_connection().collection_names(include_system_collections=False)
        self.assertTrue(dataset.sync_collection not in colls)
        raw_data = dataset.data_coll.find_one()
        self.assertTrue(isinstance(raw_data[ITX_COL_NAME], (int, long, float)))
        dataset.drop_data()

    # @unittest.skip('dev')
    def test_get_data(self):
        name = 'TestGetData'
        dataset = self.create_and_load_dataset(name)

        with self.assertRaises(OutOfSyncError):
            dataset.get_data()

        dataset.apply_sync()
        dataset.accept_sync()
        data = dataset.get_data()
        self.assertTrue(isinstance(data[0], dataset.get_data_class()))
        dataset.drop_data()

    # @unittest.skip('dev')
    def test_drop_data(self):
        from solariat.db.mongo import get_connection
        
        name = 'TestDropData'
        dataset = self.create_and_load_dataset(name)
        dataset.apply_sync()
        origin_coll = dataset.mongo_collection
        sync_coll = dataset.sync_collection

        self.user.account.datasets.delete_dataset(self.user, name)

        dataset.reload()
        self.assertTrue(dataset.is_archived)
        colls = get_connection().collection_names(include_system_collections=False)
        self.assertTrue(origin_coll not in colls)
        self.assertTrue(sync_coll not in colls)

    def test_1k_fields(self):
        from cStringIO import StringIO
        from bson.objectid import ObjectId
        import random

        COLUMNS = 1000
        LAST_COL_IDX = COLUMNS - 1

        csv = StringIO()
        for col in xrange(COLUMNS):
            csv.write(('COLUMN%s' % col))
            csv.write('\t') if col != LAST_COL_IDX else csv.write('\n')

        _from = 10 * 1000 * 1000 * 1000
        _to = _from * 2
        for row in (1, 2):
            for col in xrange(COLUMNS):
                last = col == LAST_COL_IDX
                if col < COLUMNS / 2:
                    csv.write('%s' % random.randint(_from, _to))
                else:
                    csv.write(unicode(ObjectId()))
                if not last:
                    csv.write('\t')
                else:
                    csv.write('\n')

        csv.seek(0)
        name = 'Test1000Columns'
        data_loader = CsvDataLoader(csv, sep=CsvDataLoader.TAB)
        dataset = self.user.account.datasets.add_dataset(self.user, name, data_loader)
        data_cls = dataset.get_data_class()
        self.assertEqual(data_cls.objects.count(), 2)

    @unittest.skip('OperationFailure: 24: Too many open files')
    def test_10k_datasets(self):
        from solariat.db.mongo import get_connection
        from bson.objectid import ObjectId
        db = get_connection()

        TOTAL = 10000
        for _ in xrange(TOTAL):
            db['tdataset%s' % ObjectId()].insert({'empty': 1})

        coll_deleted = 0
        for coll_name in db.collection_names(False):
            if coll_name.startsfrom('tdataset'):
                db[coll_name].drop()
                coll_deleted += 1

        self.assertEqual(coll_deleted, TOTAL)

    def test_expression_fields(self):
        name = "ExpressionsTest"
        dataset = self.create_and_load_dataset(name)
        COL_NAME = 'EXP_COLUMN'
        EXP_FIELD = {
            KEY_NAME: COL_NAME,
            KEY_TYPE: TYPE_INTEGER,
            KEY_EXPRESSION: 'INTERACTION_ID % 2',
        }
        schema = dataset.schema + [EXP_FIELD]
        for col in schema:
            if col[KEY_NAME] == 'INTERACTION_ID':
                col[KEY_TYPE] = TYPE_INTEGER
                break

        dataset.update_schema(schema)
        dataset.apply_sync()
        dataset.accept_sync()

        cnt = 0
        for data in dataset.get_data():
            if data.INTERACTION_ID is None:
                continue
            self.assertEqual(data.INTERACTION_ID % 2, data.EXP_COLUMN)
            cnt += 1

        with open(CSV_SHORT_FILEPATH) as csv_file:
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            self.user.account.datasets.update_dataset(self.user, dataset, data_loader)

        cnt2 = 0
        for data in dataset.get_data():
            if data.INTERACTION_ID is None:
                continue
            self.assertEqual(data.INTERACTION_ID % 2, data.EXP_COLUMN)
            cnt2 += 1

        self.assertGreater(cnt2, cnt)

    def test_compute_cardinalities(self):
        csv_file = tempfile.TemporaryFile('w+')
        writer = csv.writer(csv_file, delimiter=CsvDataLoader.TAB)
        writer.writerow(['FName', 'LName',    'SN'])
        writer.writerow(['ram',   'shakya',   None])
        writer.writerow(['shyam', 'shrestha', 0])
        writer.writerow(['hari',  'shrestha', 1])
        writer.writerow(['shyam', 'shakya',   2])
        writer.writerow(['hari',  'shakya',   3])
        writer.writerow(['hari',  'shakya',   4])

        csv_file.flush()
        csv_file.seek(0)

        name = "cardinality_test"
        data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
        self.user.account.datasets.add_dataset(self.user, name, data_loader)

        dataset = self.user.account.datasets.get_dataset(self.user, name)
        dataset.reload()

        actual = dataset.cardinalities
        self.assertEqual(sorted(actual.keys()), ['FName', 'LName', 'SN'])

        self.assertEqual(actual['FName']['count'], 3)
        self.assertEqual(sorted(actual['FName']['values']), ['hari', 'ram', 'shyam'])

        self.assertEqual(actual['LName']['count'], 2)
        self.assertEqual(sorted(actual['LName']['values']), ['shakya', 'shrestha'])

        # None and NaN are dropped
        self.assertEqual(actual['SN']['count'], 5)
        self.assertEqual(sorted(actual['SN']['values']), [0, 1, 2, 3, 4])

    def test_expression_context(self):
        dataset = self.__get_dataset()

        context = dataset.get_expression_context()

        self.assertTrue(context['context'])
        self.assertTrue(context['functions'])
        self.assertTrue('expression_context' in dataset.to_dict().keys())
