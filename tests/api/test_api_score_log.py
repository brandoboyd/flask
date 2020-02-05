import json
from solariat.db.mongo import get_connection

import solariat_bottle.app
from solariat_bottle.api.score_log import DEFAULT_COLLECTION, KEY_PREDICTOR
from solariat_bottle.db.predictors.models.linucb import ModelState
from solariat_bottle.db.dynamic_classes import InfomartEvent
from solariat_bottle.tests.base import UICase
from solariat_bottle.db.predictors.factory import create_agent_matching_predictor, create_chat_engagement_predictor
from solariat_bottle.tests.api.test_api_agents import TestApiAgentsBase

from solariat_bottle.db.schema_based import KEY_IS_ID, KEY_NAME, KEY_TYPE, KEY_EXPRESSION, TYPE_INTEGER, \
    TYPE_STRING, TYPE_BOOLEAN, TYPE_LIST, TYPE_DICT
from solariat_bottle.db.dynamic_event import KEY_IS_NATIVE_ID
from solariat_bottle.schema_data_loaders.base import SchemaProvidedDataLoader


class APIScoreLogCase(UICase, TestApiAgentsBase):

    def setup_agent_schema(self, user, extra_schema=[]):
        schema = list()
        schema.extend(extra_schema)
        schema.append({KEY_NAME: 'name', KEY_TYPE: TYPE_STRING})
        schema.append({KEY_NAME: 'skills', KEY_TYPE: TYPE_DICT})
        schema.append({KEY_NAME: 'attached_data', KEY_TYPE: TYPE_DICT})
        schema.append({KEY_NAME: 'date_of_birth', KEY_TYPE: TYPE_STRING})
        schema.append({KEY_NAME: 'date_of_hire', KEY_TYPE: TYPE_STRING})
        schema.append({KEY_NAME: 'gender', KEY_TYPE: TYPE_STRING})
        schema.append({KEY_NAME: 'location', KEY_TYPE: TYPE_STRING})
        schema.append({KEY_NAME: 'native_id', KEY_TYPE: TYPE_STRING, KEY_IS_NATIVE_ID: True})
        #schema.append({KEY_NAME: 'id', KEY_TYPE: TYPE_STRING})
        schema.append({KEY_NAME: 'on_call', KEY_TYPE: TYPE_BOOLEAN})
        schema_entity = user.account.agent_profile.create(user, SchemaProvidedDataLoader(schema))
        schema_entity.update_schema(schema)
        schema_entity.schema = schema_entity.discovered_schema
        schema_entity.save()
        schema_entity.apply_sync()
        schema_entity.accept_sync()

    def test_score_log(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self.setup_requirements(user_mail, user_password)
        token = self.get_token(user_mail, user_password)
        predictor1 = create_agent_matching_predictor(
            admin_user.account.id,
            state=ModelState(status=ModelState.STATUS_ACTIVE,
                             state=ModelState.CYCLE_NEW), is_test=True
        )
        predictor2 = create_chat_engagement_predictor(
            admin_user.account.id,
            state=ModelState(status=ModelState.STATUS_ACTIVE,
                             state=ModelState.CYCLE_NEW)
        )

        db = get_connection()
        db_pred1 = db[predictor1.log_collection_name()]
        db_pred2 = db[predictor2.log_collection_name()]
        db_default = db[DEFAULT_COLLECTION]
        self.assertEqual(db_pred1.count(), 0)
        self.assertEqual(db_pred2.count(), 0)
        self.assertEqual(db_default.count(), 0)

        score_data = dict(action=dict(action_id='UUID_2',
                                      skill='testing2',
                                      age=28,
                                      fluency='good2',
                                      seniority='veteran2'),
                          context=dict(AGE=36,
                                       GENDER='M',
                                       LOCATION='San Francisco2',
                                       N_SUBS=16,
                                       INTENTION='Closing an account2',
                                       SENIORITY='ancient2'),
                          token=token,
                          reward=0)
        resp = self.client.post('/api/v2.0/score_log',
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        self.assertTrue('warning' in resp_data)     # Warning returned since predictor name was not passed in
        # Request without predictor id, stored in default collection
        self.assertEqual(db_pred1.count(), 0)
        self.assertEqual(db_pred2.count(), 0)
        self.assertEqual(db_default.count(), 1)

        score_data[KEY_PREDICTOR] = predictor1.name
        resp = self.client.post('/api/v2.0/score_log',
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        self.assertFalse('warning' in resp_data)    # No more warning now that predictor was passed in
        # Request now for first predictor
        self.assertEqual(db_pred1.count(), 1)
        self.assertEqual(db_pred2.count(), 0)
        self.assertEqual(db_default.count(), 1)

        score_data['action']['action_id'] = 'UUID_3'
        resp = self.client.post('/api/v2.0/score_log',
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        self.assertFalse('warning' in resp_data)  # No more warning now that predictor was passed in
        # Request now for first predictor
        self.assertEqual(db_pred1.count(), 2)
        self.assertEqual(db_pred2.count(), 0)
        self.assertEqual(db_default.count(), 1)

        # With bad predictor name should just return false response
        score_data[KEY_PREDICTOR] = 'invalid predictor'
        resp = self.client.post('/api/v2.0/score_log',
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])

        # Now try and query back based on action_id
        fetch_data = dict()
        fetch_data[KEY_PREDICTOR] = predictor1.name
        fetch_data['action.action_id'] = 'UUID_3'
        fetch_data['token'] = token
        resp = self.client.get('/api/v2.0/score_log',
                               data=json.dumps(fetch_data),
                               content_type='application/json',
                               base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        self.assertEqual(len(resp_data['list']), 1)

        # Same query, without predictor name should not find anything
        fetch_data.pop(KEY_PREDICTOR)
        resp = self.client.get('/api/v2.0/score_log',
                               data=json.dumps(fetch_data),
                               content_type='application/json',
                               base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        self.assertTrue('warning' in resp_data)
        self.assertEqual(len(resp_data['list']), 0)
