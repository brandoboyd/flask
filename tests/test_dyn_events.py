from solariat_bottle.tests.base import UICaseSimple, RestCase
from solariat.tests.base import LoggerInterceptor

from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.channel.base import Channel

from solariat_bottle.db.dynamic_event import (EventType,
                                              ChannelTypeIsLocked,
                                              KEY_ACTOR_ID,
                                              KEY_IS_NATIVE_ID)
from solariat_bottle.views.dynamic_event import (KEY_PLATFORM, KEY_FILE, KEY_CHANNEL_ID,
                                                 STATIC_CHANNEL_EVENT_TYPE_DATA,
                                                 STATIC_EVENT_TYPE_MAPPING)
from solariat_bottle.db.dynamic_channel import ChannelType
from solariat_bottle.db.schema_based import (KEY_NAME, KEY_TYPE,
                                             KEY_IS_ID, KEY_CREATED_AT,
                                             TYPE_STRING, TYPE_INTEGER,
                                             TYPE_BOOLEAN, TYPE_TIMESTAMP,
                                             SchemaValidationError,
                                             ImproperStateError)
from solariat_bottle.schema_data_loaders.csv import CsvDataLoader
from solariat_bottle.schema_data_loaders.list import ListDataLoader
from solariat_bottle.settings import LOGGER
from solariat.utils.timeslot import utc, now, datetime_to_timestamp, timedelta
from predictors.test_dataset_view import CSV_FILEPATH, CSV_FILENAME, CSV_SEPARATOR

from mock import patch
import unittest
# import os
import csv
import json
import tempfile
import random
from bson.objectid import ObjectId


EVENT_TYPE_FLOW_NAME = 'TestEventTypeFlow'


class DynamicEventsViewTest(UICaseSimple):

    def setUp(self):
        super(DynamicEventsViewTest, self).setUp()
        self.login(self.user.email, self.password)

    def test_channel_type_workflow(self):
        # 1. create ChannelType
        name = 'TestCreate'
        self._post('/channel_type/create', {'name': name}, expected_code=201)

        channel_type = ChannelType.objects.find_one_by_user(self.user, name=name)
        self.assertEqual(channel_type.name, name)
        self.assertEqual(channel_type.sync_status, ChannelType.IN_SYNC)
        self.assertEqual(channel_type.is_locked, False)
        self.assertIsNotNone(channel_type.created_at)
        self.assertIsNotNone(channel_type.updated_at)

        # 2. create instance of ChannelType
        ChClass = channel_type.get_channel_class()
        channel = ChClass.objects.create_by_user(self.user,
                                                 title='Channel #1',
                                                 channel_type_id=channel_type.id)
        ch_id = channel.id

        # 3. edit schema of ChannelType
        schema = [{KEY_NAME: 'param', KEY_TYPE: TYPE_STRING}]
        self._post('/channel_type/update/%s' % name, {'schema': schema}, expected_code=201)

        resp = self._get('/channel_type/get/%s' % name, {})
        self.assertEqual(resp['data']['sync_status'], ChannelType.OUT_OF_SYNC, resp)

        # 4. apply_sync, check we have changed channel instance behavior
        self._post('/channel_type/apply_sync/%s' % name, {}, expected_code=201)
        channel_type.reload()
        channel_type._channel_class = None
        ChClass = channel_type.get_channel_class()
        channel = ChClass.objects.find_one_by_user(self.user, id=ch_id)
        FAIL_STRING = 'fail_string'
        channel.param = FAIL_STRING
        channel.save()
        self.assertTrue(ChClass.objects.coll.find({'_id': ch_id, 'param': FAIL_STRING}).count())
        self.assertEqual(channel_type.sync_status, ChannelType.IN_SYNC)

        # 5. update by fail schema, check we got error with failed field
        schema = [{KEY_NAME: 'param', KEY_TYPE: TYPE_INTEGER}]
        self._post('/channel_type/update/%s' % name, {'schema': schema}, expected_code=201)
        channel_type.reload()
        self.assertEqual(channel_type.schema, schema)

        resp = self._post('/channel_type/apply_sync/%s' % name,
                          {},
                          expected_code=400,
                          expected_result=False)
        channel_type.reload()
        self.assertEqual(channel_type.sync_status, ChannelType.OUT_OF_SYNC)

        self.assertIsNotNone(resp['data']['sync_errors'])
        val, err = resp['data']['sync_errors']['param'][0]
        self.assertTrue(val, FAIL_STRING)

        # 6. return schema to valid state and check result of applying
        schema = [{KEY_NAME: 'param', KEY_TYPE: TYPE_STRING}]
        self._post('/channel_type/update/%s' % name, {'schema': schema}, expected_code=201)
        self._post('/channel_type/apply_sync/%s' % name, {}, expected_code=201)
        resp = self._get('/channel_type/get/%s' % name, {})
        self.assertEqual(resp['data']['sync_status'], ChannelType.IN_SYNC)

    def test_dynamic_channel_inheritance(self):
        from solariat.db.abstract import MetaDocument
        from solariat_bottle.db.channel.base import Channel

        schema = [ {KEY_NAME: 'param', KEY_TYPE: TYPE_INTEGER} ]
        channel_type = ChannelType.objects.create_by_user(self.user,
                                                          name='TestChannelType',
                                                          account=self.user.account,
                                                          schema=schema)
        ChClass = channel_type.get_channel_class()
        channel = ChClass.objects.create_by_user(self.user,
                                                 title='TestInheritance #1',
                                                 channel_type_id=channel_type.id)
        # check inheritance works
        ch = Channel.objects.get(channel.id)
        self.assertIsInstance(ch, ChClass)
        ch.param = 1
        ch.save()

        # check class removed from registry after schema update
        schema2 = [dict(schema[0])]
        schema2[0][KEY_TYPE] = TYPE_STRING
        channel_type.update(schema=schema2, sync_status=ChannelType.OUT_OF_SYNC)
        self.assertNotIn(channel_type.data_class_name, MetaDocument.Registry)

        channel_type.apply_sync(self.user)
        ch = Channel.objects.get(channel.id)
        self.assertNotIsInstance(ch, ChClass)  # class has changed
        self.assertIsInstance(ch.param, basestring)

    def test_dynamic_events_inheritance(self):
        from solariat.db.abstract import MetaDocument
        from solariat_bottle.db.channel.base import Channel
        from solariat_bottle.db.events.event import Event

        acc = self.user.account

        schema = [{KEY_NAME: 'param', KEY_TYPE: TYPE_INTEGER}]
        channel_type = ChannelType.objects.create_by_user(self.user,
                                                          name='TestChannelType',
                                                          account=self.user.account,
                                                          schema=schema)
        ChClass = channel_type.get_channel_class()
        channel = ChClass.objects.create_by_user(self.user,
                                                 title='TestEventsInheritance',
                                                 channel_type_id=channel_type.id)

        event_type_1 = acc.event_types.create(self.user, channel_type, 'TestEventType_1')
        event_type_2 = acc.event_types.create(self.user, channel_type, 'TestEventType_2')
        EVENT_TYPE_1 = [
            {KEY_NAME: 'param', KEY_TYPE: TYPE_INTEGER},
            {KEY_NAME: 'option', KEY_TYPE: TYPE_STRING},
        ]
        DATA_1 = [
            {'param': 1, 'option': 'data=1', 'actor_id': 1},
            {'param': 2, 'option': 'another data', 'actor_id': 1},
        ]
        EVENT_TYPE_2 = [
            {KEY_NAME: 'is_test', KEY_TYPE: TYPE_BOOLEAN},
            {KEY_NAME: 'desc', KEY_TYPE: TYPE_STRING},
        ]
        DATA_2 = [
            {'is_test': True, 'desc': 'test', 'actor_id': 1},
            {'is_test': True, 'desc': 'test22', 'actor_id': 1},
        ]
        event_type_1.update_schema(EVENT_TYPE_1)
        event_type_2.update_schema(EVENT_TYPE_2)
        event_type_1.update(sync_status=EventType.IN_SYNC)
        event_type_2.update(sync_status=EventType.IN_SYNC)

        acc.event_types.import_data(self.user, channel, event_type_1, ListDataLoader(DATA_1))
        acc.event_types.import_data(self.user, channel, event_type_2, ListDataLoader(DATA_2))

        self.assertEqual(Event.objects.count(), 4)
        events = Event.objects.find()[:]
        for event in events:
            self.assertTrue('param' in event.data and 'option' in event.data or
                            'is_test' in event.data and 'desc' in event.data)

        EventType1 = event_type_1.get_data_class()
        EventType2 = event_type_2.get_data_class()

        for event in events:
            self.assertTrue(isinstance(event, EventType1) or isinstance(event, EventType2))

        # test set & save event field
        event = [evt for evt in events if isinstance(evt, EventType1)][0]
        event.param = 4
        event.save()
        event = Event.objects.get(event.id)
        self.assertEqual(event.param, 4)

        # test change schema and check inheritance changed
        new_schema = EVENT_TYPE_1 + [ {KEY_NAME: 'setting', KEY_TYPE: TYPE_INTEGER} ]
        new_schema[0][KEY_TYPE] = TYPE_STRING  # let's check sync is working
        # import pdb; pdb.set_trace()
        event_type_1.update_schema(new_schema)
        self.assertNotIn(event_type_1.data_class_name, MetaDocument.Registry)
        event_type_1.apply_sync()
        event_type_1.accept_sync()
        event_updated = Event.objects.get(event.id)
        self.assertNotIsInstance(event_updated, EventType1)
        self.assertEqual(event_updated.param, str(event.param))

        # test we create class instance only once, then use MetaDocument.Registry
        acc.event_types.reset_data_classes()  # clean dynamic data classes from Registry

        invoked = []
        def count_invokes(meth):
            def _meth(*args, **kwargs):
                invoked.append(1)
                return meth(*args, **kwargs)
            return _meth

        origin_meth = Event.set_dynamic_class
        Event.set_dynamic_class = count_invokes(Event.set_dynamic_class)
        try:
            for ev in Event.objects.find():
                pass

            self.assertEqual(len(invoked), 2)  # only 2 classes must be constructed for 4 items
        except:
            pass
        finally:
            Event.set_dynamic_class = origin_meth

    def test_native_id(self):
        acc = self.user.account

        schema = [ {KEY_NAME: 'param', KEY_TYPE: TYPE_INTEGER} ]
        channel_type = ChannelType.objects.create_by_user(self.user,
                                                          name='TestNativeIdChType',
                                                          account=self.user.account,
                                                          schema=schema)
        ChClass = channel_type.get_channel_class()
        channel = ChClass.objects.create_by_user(self.user,
                                                 title='TestNativeIdChannel',
                                                 channel_type_id=channel_type.id)

        event_type = acc.event_types.create(self.user, channel_type, 'TestNativeId')
        SCHEMA = [
            {KEY_NAME: 'name', KEY_TYPE: TYPE_STRING},
            {KEY_NAME: 'level', KEY_TYPE: TYPE_INTEGER},
            {KEY_NAME: 'origin_id', KEY_TYPE: TYPE_STRING, KEY_IS_NATIVE_ID: True},
        ]
        # TODO: actor_id is hardcoded
        DATA = [
            {'name': 'James Bond', 'level': 7, 'origin_id': '007', 'actor_id': 1},
            {'name': 'Archer', 'level': 8, 'origin_id': 'duchess', 'actor_id': 1},
            {'name': 'James Bond', 'level': 7, 'origin_id': '007', 'actor_id': 1},  # duplicate
        ]
        event_type.update_schema(SCHEMA)
        event_type.update(sync_status=EventType.IN_SYNC)

        start = utc(now())
        acc.event_types.import_data(self.user, channel, event_type, ListDataLoader(DATA))
        manager = event_type.get_data_class().objects
        self.assertEqual(manager.count(), 2)

        DATA_2 = [
            {'name': 'Archer', 'level': 8, 'origin_id': 'duchess', 'actor_id': 1},  # duplicate
            {'name': 'David Webb', 'level': 10, 'origin_id': 'jason_bourne', 'actor_id': 1},
        ]
        acc.event_types.import_data(self.user, channel, event_type, ListDataLoader(DATA_2))
        self.assertEqual(manager.count(), 3)

        # CustomerProfile = acc.get_customer_profile_class()
        # customer = CustomerProfile.objects.get(id=1)
        # end = utc(now())
        # customer_event_count = Event.objects.range_query_count(start, end, customer)
        # self.assertEqual(customer_event_count, 3)

    def get_csv_input_file(self, size=10):
        now_ts = datetime_to_timestamp(utc(now()))
        csv_file = tempfile.TemporaryFile('w+')
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(self.TEST_ITEM_COLUMNS)
        for _ in xrange(size):
            writer.writerow(self._gen_item_values(now_ts))
        csv_file.flush()
        csv_file.seek(0)
        return csv_file

    TEST_ITEM_COLUMNS = ('Name', 'Age', 'Date', 'Score', 'IntCol', 'BoolCol', 'actor_id')
    NAMES = ('Brooks', 'Angel', 'Betsy', 'David', 'Coolio', 'Matt', 'Max', 'Alex')
    ACTOR_IDS = {name: str(ObjectId()) for name in NAMES}
    AGES = xrange(25, 45)
    HOW_LONG_DAYS = xrange(2, 15)
    SCORES = xrange(5, 100)
    INTS = xrange(1000, 1000 * 1000)
    BOOLS = (False, True)
    DAY = 3600 * 24

    EVENT_TYPE_DATA_FIELD = 'event_type'

    def _gen_item_values(self, now_ts):
        name = random.choice(self.NAMES)
        return (name,
                random.choice(self.AGES),
                now_ts - random.choice(self.HOW_LONG_DAYS) * self.DAY,
                float(random.choice(self.SCORES)) / 10,
                random.choice(self.INTS),
                random.choice(self.BOOLS),
                self.ACTOR_IDS[name])

    def get_json_input_file(self, size=10, event_types=None):
        # schema:
        json_file = tempfile.TemporaryFile('w+')
        now_ts = datetime_to_timestamp(utc(now()))
        res = []
        for _ in xrange(size):
            data_item = dict(zip(self.TEST_ITEM_COLUMNS, self._gen_item_values(now_ts)))
            data_item.update({self.EVENT_TYPE_DATA_FIELD: random.choice(event_types)})
            res.append(data_item)
        json.dump(res, json_file)
        # json_file.write(json.dump(res))
        json_file.flush()
        json_file.seek(0)
        return json_file

    # def create_event_view(self, name):
    #     acc = self.user.account
    #     with open(CSV_FILEPATH) as csv_file:
    #         data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
    #         dataset = acc.datasets.add_dataset(self.user, name, data_loader)
    #         dataset.update_schema(dataset.discovered_schema)
    #         return dataset

    def get_post_data(self, csv_file):
        file_obj = (csv_file, CSV_FILENAME)
        return dict(name=EVENT_TYPE_FLOW_NAME,
                    csv_file=file_obj,
                    sep=CsvDataLoader.TAB)

    def test_events_view_workflow(self):
        from solariat_bottle.utils.predictor_events import translate_column

        acc = self.user.account

        # 1. create
        channel_type_resp = self._post('/channel_type/create',
                                       {KEY_NAME: 'TestChannelType'},
                                       expected_code=201)
        channel_type_name = channel_type_resp['data']['name']

        resp = self._post('/event_type/create',
                          {KEY_NAME: EVENT_TYPE_FLOW_NAME,
                          KEY_PLATFORM: channel_type_name},
                          expected_code=201)

        data = resp['data']
        self.assertEqual(data['sync_status'], EventType.OUT_OF_SYNC)
        self.assertFalse(data['schema'])
        self.assertFalse(data['discovered_schema'])
        self.assertFalse(data['is_locked'])

        # 2. discover schema
        with open(CSV_FILEPATH) as csv_file:
            # TODO: discover schema on json
            post_data = dict(file=(csv_file, CSV_FILENAME),
                             sep=CsvDataLoader.TAB,
                             name=EVENT_TYPE_FLOW_NAME)
            resp = self.client.post(
                '/event_type/discover_schema',
                buffered=True,
                content_type='multipart/form-data',
                data=post_data,
                base_url='https://localhost')

            self.assertEqual(resp.status_code, 201)
            data = json.loads(resp.data)['data']


        self.assertEqual(data['sync_status'], EventType.OUT_OF_SYNC)
        self.assertFalse(data['schema'])
        self.assertTrue(data['discovered_schema'])

        # 3. load data: we can load data without a schema, in this case derived schema applied
        channel_type = ChannelType.objects.find_one_by_user(self.user, name=channel_type_name)
        ChClass = channel_type.get_channel_class()
        channel = ChClass.objects.create_by_user(self.user,
                                                 title='ImportingChannel #1',
                                                 channel_type_id=channel_type.id)

        # import customer profile first
        with open(CSV_FILEPATH) as csv_file:
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            profile = self.user.account.customer_profile.create(self.user, data_loader)

        self.assertTrue(profile.discovered_schema)
        self.assertFalse(profile.schema)
        schema = [dict(col) for col in profile.discovered_schema]
        actor_id_col = [col for col in schema if col[KEY_NAME] == KEY_ACTOR_ID][0]
        actor_id_col[KEY_IS_ID] = True
        profile.update_schema(schema)
        profile.apply_sync()
        profile.accept_sync()

        with open(CSV_FILEPATH) as csv_file:
            # TODO: discover schema on json
            resp = self.client.post(
                '/event_type/import_data',
                buffered=True,
                content_type='multipart/form-data',
                data={
                    KEY_FILE: (csv_file, CSV_FILENAME),
                    'sep': CsvDataLoader.TAB,
                    KEY_CHANNEL_ID: channel.id,
                    KEY_NAME: EVENT_TYPE_FLOW_NAME,
                },
                base_url='https://localhost')

            self.assertEqual(resp.status_code, 201)
            data = json.loads(resp.data)['data']

        self.assertEqual(data['sync_status'], EventType.OUT_OF_SYNC)
        self.assertFalse(data['schema'])
        self.assertEqual(data['rows'], 50)  # TODO: replace with SIZE

        # 4. edit schema based on discovered
        resp = self._post('/event_type/update_schema/%s' % EVENT_TYPE_FLOW_NAME,
                          {'schema': data['discovered_schema']},
                          expected_code=201)
        data = resp['data']
        self.assertEqual(data['sync_status'], EventType.OUT_OF_SYNC)
        self.assertTrue(data['schema'])

        # 5. sync
        resp = self._post('/event_type/sync/apply/%s' % EVENT_TYPE_FLOW_NAME, {},
                          expected_code=201)
        data = resp['data']
        self.assertEqual(data['sync_status'], EventType.SYNCED)

        resp = self._post('/event_type/sync/accept/%s' % EVENT_TYPE_FLOW_NAME, {},
                          expected_code=201)
        data = resp['data']
        self.assertEqual(data['sync_status'], EventType.IN_SYNC)

        # 6. get, list
        resp = self._get('/event_type/get/%s' % EVENT_TYPE_FLOW_NAME, {})
        data = resp['data']
        self.assertEqual(data[KEY_NAME], EVENT_TYPE_FLOW_NAME)
        self.assertTrue(data['id'])

        resp = self._get('/event_type/list', {})
        items = resp['data']
        self.assertIsInstance(items, list)
        self.assertTrue(len(items) >= 1)
        item = [i for i in items if i[KEY_NAME] == EVENT_TYPE_FLOW_NAME]
        self.assertTrue(item)

        resp = self._get('/event_type/list', {KEY_PLATFORM: channel_type.name})
        items = resp['data']
        self.assertIsInstance(items, list)
        self.assertTrue(len(items) >= 1)

        #     dataset = acc.datasets.get_dataset(self.user, CREATE_UPDATE_DATASET_NAME)
        #     schema = dataset.discovered_schema
        #     DataClass = dataset.get_data_class()
        #     self.assertEqual(DataClass.objects.count(), 50)
        #
        # # test update schema
        # # based on test data, just lets change one column type
        # itx_col_name = translate_column('INTERACTION_ID')
        # itx_col = [s for s in schema if s['name'] == itx_col_name][0]
        # assert itx_col['type'] in ('integer', 'timestamp'), (itx_col['type'], itx_col_name)
        # itx_col['type'] = 'string'
        # data = self._post('/dataset/update_schema/%s' % CREATE_UPDATE_DATASET_NAME,
        #                   {'schema': schema},
        #                   expected_code=201)
        # dataset = acc.datasets.get_dataset(self.user, CREATE_UPDATE_DATASET_NAME)
        # self.assertTrue(bool([1 for col in dataset.schema if col['name'] == itx_col_name \
        #                                              and col['type'] == 'string']))
        #
        # # test invalid schema
        # broken_schema = schema[1:]
        # data = self._post('/dataset/update_schema/%s' % CREATE_UPDATE_DATASET_NAME,
        #                   {'schema': broken_schema},
        #                   expected_result=False,
        #                   expected_code=500)
        #
        # # cannot accept sync until it's happens
        # data = self._post('/dataset/sync/accept/%s' % CREATE_UPDATE_DATASET_NAME,
        #                   {},
        #                   expected_result=False,
        #                   expected_code=500)
        #
        # # let's include the case when not all data could be synced
        # FAIL_COL_NAME = 'STAT_INI_1'
        # dataset.reload()
        # col = [col for col in dataset.schema if col[KEY_NAME] == FAIL_COL_NAME][0]
        # self.assertEqual(col[KEY_TYPE], TYPE_INTEGER)
        # raw_data = dataset.data_coll.find_one()
        # dataset.data_coll.update({'_id': raw_data['_id']}, {'$set': {FAIL_COL_NAME: 'fail'}})
        #
        # # test applying schema on dataset (synchronous mode for testing)
        # data = self._post('/dataset/sync/apply/%s' % CREATE_UPDATE_DATASET_NAME,
        #                   {},
        #                   expected_code=201)
        #
        # self.assertEqual(data['data']['sync_status'], Dataset.SYNCED)
        # self.assertTrue(data['data']['is_locked'])
        # # we manually fail 1 raw sync
        # self.assertEqual(data['data']['items_synced'], 49)
        #
        # # until we accpet/discard last sync,
        # # our original collection keeps origin data
        # dataset = acc.datasets.get_dataset(self.user, CREATE_UPDATE_DATASET_NAME)
        # DataClass = dataset.get_data_class()
        # self.assertEqual(DataClass.objects.count(), 50)
        #
        # data = self._post('/dataset/sync/apply/%s' % CREATE_UPDATE_DATASET_NAME,
        #                   {},
        #                   expected_result=False,
        #                   expected_code=500)
        #
        # data = self._post('/dataset/sync/accept/%s' % CREATE_UPDATE_DATASET_NAME,
        #                   {},
        #                   expected_code=201)
        # dataset = acc.datasets.get_dataset(self.user, CREATE_UPDATE_DATASET_NAME)
        # DataClass = dataset.get_data_class()
        # self.assertEqual(DataClass.objects.count(), 49)


    def test_event_workflow(self):
        # TODO: check we cannot import data when channel OUT_OF_SYNC

        from solariat_bottle.db.events.event import Event
        from solariat_bottle.schema_data_loaders.csv import CsvDataLoader
        from solariat_bottle.schema_data_loaders.json import JsonDataLoader

        # View code
        channel_type = ChannelType.objects.create_by_user(self.user,
                                                          name='TestType',
                                                          account=self.user.account)
        acc = self.user.account
        web_event_type = acc.event_types.create(self.user, channel_type, name='Web')
        mail_event_type = acc.event_types.create(self.user, channel_type, name='Mail')
        chat_event_type = acc.event_types.create(self.user, channel_type, name='Chat')

        channel_type.is_locked = True
        channel_type.save()
        with self.assertRaises(ChannelTypeIsLocked):
            acc.event_types.create(self.user, channel_type, name='ChannelTypeIsLockedError')

        # discover from csv: event_type as input
        rows_csv = 10
        csv_file = self.get_csv_input_file(size=rows_csv)
        csv_data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.COMMA)
        schema1 = csv_data_loader.read_schema()
        web_event_type.update(discovered_schema=schema1)

        self.assertEqual({col[KEY_NAME] for col in schema1}, set(self.TEST_ITEM_COLUMNS))

        # discover from json: no event_type as input needed
        EVENT_TYPE_MAP = {
            ev.name: ev for ev in (web_event_type, mail_event_type, chat_event_type)
        }
        rows_json = 20
        json_file = self.get_json_input_file(size=rows_json, event_types=('Mail', 'Chat'))

        def event_type_getter(data_item):
            return data_item.get(self.EVENT_TYPE_DATA_FIELD)

        json_data_loader = JsonDataLoader(json_file, event_type_getter)
        schemas_map = json_data_loader.read_schema()

        discover_only_type = None
        for event_type_name, schema in schemas_map.iteritems():
            event_type = EVENT_TYPE_MAP.get(event_type_name)
            if not event_type:
                # TODO: log
                continue
            if discover_only_type and discover_only_type != event_type:
                continue
            event_type.update(discovered_schema=schema)
            self.assertEqual({col[KEY_NAME] for col in schema},
                             set(self.TEST_ITEM_COLUMNS) | {self.EVENT_TYPE_DATA_FIELD})

        # import data
        # case 1: event type has just discovered schema (or no schema at all)
        # sync_status: IN_SYNC; insert data to data_coll as it is (raw)
        #
        # case 2: event type has schema created
        # sync_status: OUT_OF_SYNC; do not insert any data
        #
        # case 3: event type has applied schema
        # sync_status: IN_SYNC; insert data with schema

        ChClass = channel_type.get_channel_class()
        channel = ChClass.objects.create_by_user(self.user,
                                                 title='SomeImportChannel',
                                                 channel_type_id=channel_type.id)

        with self.assertRaises(ImproperStateError):
            web_event_type.import_data(self.user, csv_data_loader)

        web_event_type.channel_id = channel.id
        web_event_type.import_data(self.user, csv_data_loader)
        self.assertEqual(web_event_type.data_coll.count(), rows_csv)
        # TODO: test it also like: channel.import_data(event_type=web_event_type)

        # check we have data imported, check accordance to schema

        channel.import_data(self.user, json_data_loader)
        for ev_type in EVENT_TYPE_MAP.values():
            ev_type.reload()

        # import pdb; pdb.set_trace()
        total_imported = rows_csv + rows_json
        self.assertNotEqual(web_event_type.data_coll.count(), total_imported)
        self.assertEqual(web_event_type.all_data_coll.count(), total_imported)
        self.assertEqual(Event.objects.coll.count(), total_imported)

        mail_events_count = mail_event_type.data_coll.count()
        chat_events_count = chat_event_type.data_coll.count()
        self.assertTrue(0 < mail_events_count <= rows_json)
        self.assertEqual(mail_event_type.rows, mail_events_count)

        schema = [dict(col) for col in mail_event_type.discovered_schema]
        bool_col = [col for col in schema if col[KEY_NAME] == 'BoolCol'][0]
        self.assertTrue(bool_col[KEY_TYPE], TYPE_BOOLEAN)
        raw_event = mail_event_type.data_coll.find_one()
        val = raw_event[bool_col[KEY_NAME]]
        self.assertIsInstance(val, bool)

        bool_col[KEY_TYPE] = TYPE_STRING
        mail_event_type.update_schema(schema)
        self.assertEqual(mail_event_type.sync_status, EventType.OUT_OF_SYNC)
        with self.assertRaises(ImproperStateError):
            mail_event_type.import_data(self.user, json_data_loader)

        mail_event_type.apply_sync()
        self.assertEqual(mail_event_type.sync_status, EventType.SYNCED)
        self.assertEqual(mail_event_type.items_synced, mail_events_count)  # should be no errors

        self.assertEqual(Event.objects.coll.count(), total_imported)
        self.assertEqual(mail_event_type.data_sync_coll.count(), mail_events_count)
        self.assertEqual(chat_event_type.data_sync_coll.count(), 0)

        raw_event = mail_event_type.data_sync_coll.find_one()
        val = raw_event[bool_col[KEY_NAME]]
        self.assertIsInstance(val, basestring)

        mail_event_type.accept_sync()
        self.assertEqual(Event.objects.coll.count(), total_imported)
        self.assertEqual(mail_event_type.data_sync_coll.count(), 0)

        raw_event = mail_event_type.data_coll.find_one()
        val = raw_event[bool_col[KEY_NAME]]
        self.assertIsInstance(val, basestring)

    def test_global_sync(self):
        pass

    def test_event_types(self):
        from solariat_bottle.db.events.event_type import BaseEventType, StaticEventType
        # from solariat_bottle.db.dynamic_event import EventType

        acc = self.user.account

        static_et = StaticEventType.objects.create(
            account_id=acc.id,
            platform='web',
            name='Static Event',
            attributes=['stage_metadata'])

        channel_type = ChannelType.objects.create_by_user(self.user,
                                                          name='chat',
                                                          account=acc,
                                                          schema=[])

        dynamic_et = acc.event_types.create(self.user, channel_type, 'Dynamic Event')

        all_et = BaseEventType.objects(id__in=[static_et.id, dynamic_et.id])

        self.assertEqual(len(all_et), 2)
        self.assertIsInstance(all_et[0], StaticEventType)
        self.assertIsInstance(all_et[1], EventType)


        # TODO: add event of event_type, rename event_type, get event from db
        # TODO: same for channel type

        self.assertIsInstance(all_et[0], BaseEventType)
        self.assertIsInstance(all_et[1], BaseEventType)


class TestStaticEventsCase(UICaseSimple):
    """TODO: better naming
     We use /event_types/import and /event_types/list endpoints
     for both built-in and dynamic channels, this is confusing as they are in
     views/dynamic_events.py
    """
    def setUp(self):
        super(TestStaticEventsCase, self).setUp()
        self.login(self.email, self.password)

    def event_stream(self, n=10, data_format='json', event_type='twitter'):
        from solariat_bottle.db.post.chat import ChatProfile

        templates = {
            'twitter': json.dumps({'content': 'i am a tweet',
                                   'user_profile': {'user_name': 'test'},
                                   'twitter': {'id': '%(id)s',
                                               'created_at': '%(now)s'}}),
            'facebook': json.dumps({'content': 'i am a tweet',
                                    'user_profile': {'user_name': 'test'},
                                    'facebook': {'facebook_post_id': '%(id)s',
                                                 '_wrapped_data': {'type': 'status',
                                                                   'source_type': 'status',
                                                                   'source_id': 'somepageid'},
                                                 'created_at': '%(now)s'}}),
            'web': json.dumps({'content': '',
                               '_platform': 'Web',
                               'url': 'g-tel.com',
                               'element_html': 'click'}),
            'faq': json.dumps({'content': '',
                               'query': 'How do I dispute an item in my bill?'}),
            'branch': json.dumps({'content': '',
                                  '_platform': 'Branch',
                                  'is_inbound': True}),
            'chat': json.dumps({'content': 'Hello. Can anyone tell me which iPhone is best for me?',
                                'chat_data': {'created_at': '%(now)s'}}),
            'voice': json.dumps({'content': 'What is my account balance?',
                                 'chat_data': {'created_at': '%(now)s'}}),
            'email': json.dumps({'content': 'Hi by email, what is my account balance?',
                                'email_data': {
                                    'cc': [],
                                    'sender': 'user@email.com',
                                    'recipients': ['rec1@address.com'],
                                    'subject': 'Test',
                                    'created_at': '%(now)s',
                                }}),
            # TODO: NPSOutcome couldn't be created in general way
            # 'voc': json.dumps({'content': 'Good',
            #                    'score': 8,
            #                    'response_type': 'Passive',
            #                    'case_number': 'a1-1',
            #                    'user_profile': None,
            #                    '_created': '%(now)s'
            #                    }),
        }
        from six import StringIO
        from solariat_bottle.scripts.data_load.demo_helpers import CsvPrinter

        class JsonPrinter(object):
            def __init__(self, stream):
                self.stream = stream

            def write_data(self, data):
                self.stream.write(json.dumps(data))
                self.stream.write('\n')

        stream = StringIO()
        printer = {'json': JsonPrinter, 'csv': CsvPrinter}[data_format](stream)

        for idx in range(n):
            ctx = {'id': idx + 1e6, 'now': now() - timedelta(seconds=random.choice(xrange(100)))}
            printer.write_data(json.loads(templates[event_type] % ctx))

        stream.seek(0)
        return stream

    def test_event_types_list(self):
        channel = Channel.objects.create_by_user(self.user, account=self.account, title='TestCh')
        resp = self._get('/event_type/list', {KEY_PLATFORM: channel.platform})
        self.assertEqual(resp['data'], [STATIC_CHANNEL_EVENT_TYPE_DATA])

    def test_import_data(self):
        from solariat_bottle.db.channel.web_click import WebClickChannel
        from solariat_bottle.db.channel.faq import FAQChannel
        from solariat_bottle.db.channel.branch import BranchChannel
        from solariat_bottle.db.channel.chat import ChatServiceChannel
        from solariat_bottle.db.channel.voice import VoiceServiceChannel
        from solariat_bottle.db.channel.email import EmailServiceChannel
        from solariat_bottle.db.channel.voc import VOCServiceChannel

        tw_channel = TwitterServiceChannel.objects.create_by_user(
            self.user, account=self.account, title='TestTwCh')
        fb_channel = FacebookServiceChannel.objects.create_by_user(
            self.user, account=self.account, title='TestFbCh')
        web_channel = WebClickChannel.objects.create_by_user(
            self.user, account=self.account, title='TestWebCh')
        faq_channel = FAQChannel.objects.create_by_user(
            self.user, account=self.account, title='TestFAQCh')
        branch_channel = BranchChannel.objects.create_by_user(
            self.user, account=self.account, title='TestBranchCh')
        chat_channel = ChatServiceChannel.objects.create_by_user(
            self.user, account=self.account, title='TestChatCh')
        voice_channel = VoiceServiceChannel.objects.create_by_user(
            self.user, account=self.account, title='TestVoiceCh')
        email_channel = EmailServiceChannel.objects.create_by_user(
            self.user, account=self.account, title='TestEmailCh')
        voc_channel = VOCServiceChannel.objects.create_by_user(
            self.user, account=self.account, title='TestVOCCh')

        def clean_channel_data(channel):
            EventCls = STATIC_EVENT_TYPE_MAPPING.get(channel.__class__)
            EventCls.objects.coll.remove()

        test_cases = [
            (2, 'json', 'twitter', tw_channel),
            (2, 'json', 'facebook', fb_channel),
            # TODO: csv format cannot represent dict structure deeper than 1 level
            # (1, 'csv', 'twitter', tw_channel),
            # (1, 'csv', 'facebook', fb_channel),
            (2, 'json', 'web', web_channel),
            (2, 'json', 'faq', faq_channel),
            (2, 'json', 'branch', branch_channel),
            (2, 'json', 'chat', chat_channel),
            (2, 'json', 'voice', voice_channel),
            (2, 'json', 'email', email_channel),
            # TODO: voc/nps not working and deprecated
            # (2, 'json', 'voc', voc_channel),
        ]
        errors = []
        for n_samples, data_format, event_type, channel in test_cases:
            LOGGER.info("\n\n=== LOADING %s %s %s %s\n", n_samples, data_format, event_type, channel)
            clean_channel_data(channel)
            resp = self.client.post(
                '/event_type/import_data',
                buffered=True,
                content_type='multipart/form-data',
                data={
                    KEY_FILE: (self.event_stream(n=n_samples, data_format=data_format, event_type=event_type), 'filename.%s' % data_format),
                    'sep': CsvDataLoader.COMMA,
                    KEY_CHANNEL_ID: channel.id,
                    KEY_NAME: 'builtin',
                },
                base_url='https://localhost')

            EventCls = STATIC_EVENT_TYPE_MAPPING.get(channel.__class__)
            try:
                self.assertEqual(resp.status_code, 201)
                data = json.loads(resp.data)['data']
                channels_to_search = [channel.id]
                if channel.is_service:
                    channels_to_search.extend([channel.inbound, channel.outbound])
                post_count = EventCls.objects(channels__in=channels_to_search).count()
                assert post_count == n_samples,\
                    "%s %s %s post count %s != %s" % (data_format, event_type, channel, post_count, n_samples)
            except AssertionError as exc:
                errors.append(exc)

        self.assertFalse(errors, msg='\n'.join([str(err) for err in errors]))


class DynamicEventsAPITest(UICaseSimple):

    def test_api(self):
        from solariat_bottle.db.events.event import Event

        acc = self.user.account
        CustomerProfile = acc.get_customer_profile_class()
        channel_type = ChannelType.objects.create_by_user(self.user,
                                                          name='APIChannelType',
                                                          account=self.user.account)
        ChClass = channel_type.get_channel_class()
        channel = ChClass.objects.create_by_user(self.user,
                                                 title='API Channel',
                                                 channel_type_id=channel_type.id)

        click_et = acc.event_types.create(self.user, channel_type, 'Click')
        CLICK_TYPE_SCHEMA = [
            {KEY_NAME: 'url', KEY_TYPE: TYPE_STRING},
            {KEY_NAME: 'date', KEY_TYPE: TYPE_TIMESTAMP, KEY_CREATED_AT: True},
            {KEY_NAME: 'session_id', KEY_TYPE: TYPE_STRING, KEY_IS_NATIVE_ID: True},
        ]

        call_et = acc.event_types.create(self.user, channel_type, 'Call')
        CALL_TYPE_SCHEMA = [
            {KEY_NAME: 'phone', KEY_TYPE: TYPE_STRING},
            # TODO: change later, check type is changed
            {KEY_NAME: 'duration', KEY_TYPE: TYPE_STRING},
            {KEY_NAME: 'date', KEY_TYPE: TYPE_TIMESTAMP, KEY_CREATED_AT: True},
            {KEY_NAME: 'agent_id', KEY_TYPE: TYPE_STRING},
        ]

        def gen_data(et, **kw):
            # dt = now() - timedelta(minutes=random.randint(1, 10))
            data = {
                'channel': str(channel.id),
                'actor_id': 1,
                'content': '',
                'token': self.get_token(),

                'event_type': et.name,
                # 'date': datetime_to_timestamp(dt),
            }
            data.update(kw)
            # return dt, data
            return data

        # click_dt, click_data = gen_data(click_et, **{
        click_data = gen_data(click_et, **{
            'url': 'http://site.com/page1/link1',
            'session_id': str(ObjectId()),
        })

        # call_dt, call_data = gen_data(call_et, **{
        call_data = gen_data(call_et, **{
            'phone': '123',
            'duration': str(random.randint(20, 300)),
            'agent_id': str(ObjectId()),
        })

        # post click (no schema)
        with LoggerInterceptor() as logs:
            resp = self.client.post('/api/v2.0/posts',
                data=json.dumps(click_data),
                content_type='application/json',
                base_url='https://localhost')

            errors = [1 for log in logs if 'is not in the field set' in log.message]
            self.assertTrue(errors)
            self.assertEqual(resp.status_code, 500)

        # create schema
        click_et.update(schema=CLICK_TYPE_SCHEMA)
        call_et.update(schema=CALL_TYPE_SCHEMA)

        start = now()

        resp = self.client.post('/api/v2.0/posts',
            data=json.dumps(click_data),
            content_type='application/json',
            base_url='https://localhost')

        click_resp = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(click_resp['ok'])

        resp = self.client.post(
            '/api/v2.0/posts',
            data=json.dumps(call_data),
            content_type='application/json',
            base_url='https://localhost')

        call_resp = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(click_resp['ok'])

        self.assertEqual(Event.objects.count(), 2)
        call_event = Event.objects.get(call_resp['item']['id'])
        self.assertIsInstance(call_event.duration, basestring)
        customer = CustomerProfile.objects.get(1)
        events_by_customer = Event.objects.range_query_count(start, now(), customer)
        self.assertEqual(events_by_customer, 2)

        # check basic dynamic functionality: change type of filed,
        # sync, check it is changed in db
        for col in CALL_TYPE_SCHEMA:
            if col[KEY_NAME] == 'duration':
                col[KEY_TYPE] = TYPE_INTEGER
        call_et.update_schema(CALL_TYPE_SCHEMA)
        call_et.apply_sync()
        call_et.accept_sync()
        # check data in db has changed
        call_event.reload()
        self.assertIsInstance(call_event.duration, (int, long, float))

        # add event by another customer
        click2_data = gen_data(click_et, **{
            'url': 'http://site.com/page1/link2',
            'session_id': str(ObjectId()),
        })
        resp = self.client.post(
            '/api/v2.0/posts',
            data=json.dumps(click2_data),
            content_type='application/json',
            base_url='https://localhost')

        # check how counters are changed
        self.assertEqual(Event.objects.count(), 3)
        self.assertEqual(events_by_customer, 2)
        self.assertEqual(click_et.get_data_class().objects.count(), 2)
