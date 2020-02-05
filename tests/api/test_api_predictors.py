import json
from solariat_bottle.db.predictors.base_predictor import BasePredictor, TYPE_AGENTS, HYBRID, ERROR_NO_ACTIVE_MODELS
from solariat_bottle.db.predictors.models.linucb import ModelState
from solariat_bottle.db.predictors.operators import UNIQ_OPERATORS, DB_OPERATORS, OPERATOR_REGISTRY
import unittest
from solariat_bottle.db.dynamic_classes import InfomartEvent
from solariat_bottle.tests.base import UICase
from solariat_bottle.db.account import Account
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.roles import ADMIN
from solariat_bottle.db.predictors.factory import create_agent_matching_predictor
from solariat_bottle.db.predictors.entities_registry import EntitiesRegistry
from solariat_bottle.tests.api.test_api_agents import TestApiAgentsBase
from solariat_bottle.api.predictors import (ERR_MSG_MISSING_FIELD, ERR_MSG_NO_PREDICTOR, ERR_MSG_NO_ACCESS)

from solariat_bottle.db.schema_based import KEY_IS_ID, KEY_NAME, KEY_TYPE, KEY_EXPRESSION, TYPE_INTEGER, \
    TYPE_STRING, TYPE_BOOLEAN, TYPE_LIST, TYPE_DICT
from solariat_bottle.db.dynamic_event import KEY_IS_NATIVE_ID
from solariat_bottle.schema_data_loaders.base import SchemaProvidedDataLoader



def retrain(predictor):
    predictor.refresh_cardinalities()
    for model in predictor.models:
        total = predictor.training_data_class.objects(predictor_id=predictor.id).count()
        progress = 0
        predictor.save_progress(model, progress, total)

        context_list = []
        action_list = []
        reward_list = []
        for data in predictor.training_data_class.objects(predictor_id=predictor.id):
            context_list.append(data.context)
            action_list.append(data.action)
            reward_list.append(data.reward)

        import itertools
        bulk = predictor.training_data_class.objects.coll.initialize_ordered_bulk_op()

        for context, action, reward in itertools.izip(context_list, action_list, reward_list):
            training_data = predictor.training_data_class(predictor_id=predictor.id,
                                                          context=context,
                                                          action=action,
                                                          reward=reward,
                                                          n_batch=predictor.get_n_batch_value())
            bulk.insert(training_data.data)
        bulk.execute()
        predictor.refresh_cardinalities()
        predictor.train_models(model=model)
        # model.version += 1
        predictor.save_model(model)


class APIPredictorsCase(UICase, TestApiAgentsBase):

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

    def test_predictor_score(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self.setup_requirements(user_mail, user_password)
        token = self.get_token(user_mail, user_password)
        predictor = create_agent_matching_predictor(
            admin_user.account.id,
            state=ModelState(status=ModelState.STATUS_ACTIVE,
                             state=ModelState.CYCLE_NEW), is_test=True
        )

        feedback_data = dict(action=dict(action_id='UUID_2',
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
        self.client.post('/api/v2.0/predictors/%s/feedback' % predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')
        retrain(predictor)

        score_data = dict(actions=[dict(action_id='UUID_1',
                                        skill='testing',
                                        age=27,
                                        fluency='good',
                                        seniority='veteran'),
                                   dict(action_id='UUID_2',
                                        skill='testing',
                                        age=77,
                                        fluency='good',
                                        seniority='new')],
                          context=dict(age=35,
                                       gender='M',
                                       location='San Francisco',
                                       n_subs=15,
                                       intention='Closing an account',
                                       seniority='ancient'),
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        #import pdb; pdb.set_trace()
        self.assertEquals(resp_data['model'], u'Full feature set')
        self.assertEquals(resp_data['predictor'], u'Test Agent Matching Predictor')
        self.assertEquals(len(resp_data['list']), 2)
        self.assertTrue('predictor_id' in resp_data.keys())
        self.assertTrue('model_id' in  resp_data.keys())

        max_ucb = 0
        for entry in resp_data['list']:
            self.assertTrue("score" in entry)
            self.assertTrue("id" in entry)
            self.assertTrue("estimated_reward" in entry)

            # if entry['id'] == 'UUID_2':
            self.assertEqual(entry["score"], 0)                 # Only data was a zero
            self.assertEqual(entry["estimated_reward"], 0)      # Only data was a zero
            # else:
            #     self.assertEqual(entry["score"], 0.25)              # Only data was a zero
            #     self.assertEqual(entry["estimated_reward"], 0.25)   # Only data was a zero
            if max_ucb < entry["score"]:
                max_ucb = entry["score"]

        feedback_data = dict(action=dict(action_id='UUID_1',
                                         skill='testing',
                                         age=27,
                                         fluency='good',
                                         seniority='veteran'),
                             context=dict(AGE=35,
                                          GENDER='M',
                                          LOCATION='San Francisco',
                                          N_SUBS=15,
                                          INTENTION='Closing an account',
                                          SENIORITY='ancient'),
                             token=token,
                             reward=100)
        self.client.post('/api/v2.0/predictors/%s/feedback' % predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')

        retrain(predictor)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertEquals(len(resp_data['list']), 2)

        new_max_ucb = 0
        uuid1_score = 0
        uuid2_score = 0
        uuid1_ex_reward = 0
        uuid2_ex_reward = 0
        for entry in resp_data['list']:
            self.assertTrue("score" in entry)
            self.assertTrue(entry["score"] > 0) # Some upper confidence at first
            self.assertTrue("id" in entry)
            self.assertTrue("estimated_reward" in entry)
            self.assertTrue(entry["estimated_reward"] > 0) # Had positive example, both should be positive
            if new_max_ucb < entry["score"]:
                new_max_ucb = entry["score"]
            if entry['id'] == "UUID_1":
                uuid1_score = entry["score"]
                uuid1_ex_reward = entry["estimated_reward"]
            if entry['id'] == "UUID_2":
                uuid2_score = entry["score"]
                uuid2_ex_reward = entry["estimated_reward"]

        # Overall max ucb should be higher since we just got positive reward
        self.assertTrue(new_max_ucb > max_ucb)
        # UCB for non-rated agent should be higher but estimated reward lower
        self.assertTrue(uuid1_ex_reward > uuid2_ex_reward, '%s > %s' % (uuid1_ex_reward, uuid2_ex_reward))
        self.assertTrue(uuid1_score > uuid2_score, '%s > %s' % (uuid1_score, uuid2_score))

        score_data = dict(actions=[dict(action_id='UUID_1',
                                        Skill='testing',
                                        Age=27,
                                        Fluency='good',
                                        Seniority='veteran'),
                                   dict(action_id='UUID_2',
                                        Skill='testing',
                                        Age=77,
                                        Fluency='good',
                                        Seniority='new')],
                          context=dict(aGe=35,
                                       genDer='M',
                                       locatIon='San Francisco',
                                       n_sUbs=15,
                                       iNtention='Closing an account',
                                       senioRity='ancient'),
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data2 = json.loads(resp.data)
        self.assertEqual(resp_data['list'][0]['score'], resp_data2['list'][0]['score'])
        self.assertEqual(resp_data['list'][1]['score'], resp_data2['list'][1]['score'])
        # Now test same score with a score expression
        from solariat_bottle.api.predictors import KEY_P_SCORE, PredictorsAPIView
        predictor.score_expression = "2000 + " + KEY_P_SCORE
        predictor.save()
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        score_result_data = json.loads(resp.data)
        self.assertTrue(score_result_data['ok'])
        for entry in score_result_data['list']:
            self.assertTrue(entry['score'] >= 2000)
        self.assertFalse('warning' in score_result_data)
        # Now try an invalid expression, check default scores + warning is returned
        PredictorsAPIView._parsers_cache = dict()
        predictor.score_expression = "2000 + unknown_key"
        predictor.save()
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        score_result_data = json.loads(resp.data)
        self.assertTrue(score_result_data['ok'])
        for entry in score_result_data['list']:
            self.assertTrue(entry['score'] <= 2000)
        self.assertTrue('warning' in score_result_data)


    def test_score_non_active(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self.setup_requirements(user_mail, user_password)
        token = self.get_token(user_mail, user_password)
        predictor = create_agent_matching_predictor(
            admin_user.account.id,
            state=ModelState(status=ModelState.STATUS_INACTIVE,
                             state=ModelState.CYCLE_NEW), is_test=True
        )
        for mdl in predictor.models:
            mdl.state.status = mdl.state.STATUS_INACTIVE
            mdl.save()

        feedback_data = dict(action=dict(action_id='UUID_2',
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
        self.client.post('/api/v2.0/predictors/%s/feedback' % predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')
        retrain(predictor)

        score_data = dict(actions=[dict(action_id='UUID_1',
                                        skill='testing',
                                        age=27,
                                        fluency='good',
                                        seniority='veteran'),
                                   dict(action_id='UUID_2',
                                        skill='testing',
                                        age=77,
                                        fluency='good',
                                        seniority='new')],
                          context=dict(age=35,
                                       gender='M',
                                       location='San Francisco',
                                       n_subs=15,
                                       intention='Closing an account',
                                       seniority='ancient'),
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])
        self.assertEqual(resp_data['error'], ERROR_NO_ACTIVE_MODELS)

    def test_predictor_expressions_metadata(self):
        self.login()

        # expression_type = feedback_model
        params = {'expression_type': 'feedback_model',
                  'suggestion_type': 'collections'}
        response = self.client.post('/predictors/expressions/metadata',
                                    data=json.dumps(params),
                                    content_type='application/json')
        resp_data = json.loads(response.data)
        self.assertTrue(resp_data['ok'])
        self.assertTrue(resp_data['metadata'])

        # expression_type = reward
        params = {'expression_type': 'reward',
                  'collections': resp_data['metadata'],
                  'suggestion_type': 'fields'}
        response = self.client.post('/predictors/expressions/metadata',
                                    data=json.dumps(params),
                                    content_type='application/json')
        resp_data = json.loads(response.data)
        self.assertTrue(resp_data['ok'])
        self.assertTrue(resp_data['metadata'])
        for item in resp_data['metadata']:
            self.assertTrue(item['fields'])
            self.assertTrue(item['collection'])

        # expression_type = action_id
        params = {'expression_type': 'action_id',
                  'suggestion_type': 'operators'}
        response = self.client.post('/predictors/expressions/metadata',
                                    data=json.dumps(params),
                                    content_type='application/json')
        resp_data = json.loads(response.data)
        self.assertTrue(resp_data['ok'])
        self.assertEqual(resp_data['metadata'], UNIQ_OPERATORS.keys())

        # expression_type = feedback_model, suggestion_type = operators
        params = {'expression_type': 'feedback_model',
                  'suggestion_type': 'operators'}
        response = self.client.post('/predictors/expressions/metadata',
                                    data=json.dumps(params),
                                    content_type='application/json')
        resp_data = json.loads(response.data)
        self.assertTrue(resp_data['ok'])
        self.assertEqual(resp_data['metadata'], DB_OPERATORS.keys())

    def test_composite_predictor(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self.setup_requirements(user_mail, user_password)
        token = self.get_token(user_mail, user_password)
        first_predictor = create_agent_matching_predictor(
            admin_user.account.id,
            state=ModelState(status=ModelState.STATUS_ACTIVE,
                             state=ModelState.CYCLE_NEW), is_test=True
        )
        first_predictor.name = "pred1"
        first_predictor.save()
        second_predictor = create_agent_matching_predictor(
            admin_user.account.id,
            state=ModelState(status=ModelState.STATUS_ACTIVE,
                             state=ModelState.CYCLE_NEW), is_test=True
        )
        second_predictor.name = "pred2"
        second_predictor.save()
        third_predictor = create_agent_matching_predictor(
            admin_user.account.id,
            state=ModelState(status=ModelState.STATUS_ACTIVE,
                             state=ModelState.CYCLE_NEW), is_test=True
        )
        third_predictor.name = "pred3"
        third_predictor.save()

        feedback_data = dict(action=dict(action_id='UUID_2',
                                         skill='testing2',
                                         age=28,
                                         fluency='good2',
                                         seniority='veteran2'),
                             context=dict(age=36,
                                          gender='M',
                                          location='San Francisco2',
                                          n_subs=16,
                                          intent='Closing an account2',
                                          seniority='ancient2'),
                             token=token,
                             reward=0)

        self.client.post('/api/v2.0/predictors/%s/feedback' % first_predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')
        retrain(first_predictor)
        self.client.post('/api/v2.0/predictors/%s/feedback' % second_predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')
        retrain(second_predictor)
        self.client.post('/api/v2.0/predictors/%s/feedback' % third_predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')
        retrain(third_predictor)

        composite_predictor_data = {'predictors_list': [str(first_predictor.id),
                                                        str(second_predictor.id),
                                                        str(third_predictor.id)],
                                    'predictor_type': BasePredictor.TYPE_COMPOSITE,
                                    'raw_expression': "%s + %s * %s" % (first_predictor.name,
                                                                        second_predictor.name,
                                                                        third_predictor.name),
                                    'account_id': str(admin_user.account.id),
                                    'name': 'The Composite Predictor'}
        self.login(user_mail, user_password)
        resp_data = self.client.post('/predictors/json',
                                     data=json.dumps(composite_predictor_data),
                                     content_type='application/json',
                                     base_url='https://localhost')
        resp_data = json.loads(resp_data.data)

        predictor_id = resp_data['obj']['id']

        # edit predictor
        composite_predictor_data['name'] = 'The Composite Predictor 2'
        resp_data = self.client.post('/predictors/%s' % predictor_id,
                                     data=json.dumps(composite_predictor_data),
                                     content_type='application/json',
                                     base_url='https://localhost')

        score_data = dict(actions=[dict(action_id='UUID_1',
                                        skill='testing',
                                        age=27,
                                        fluency='good',
                                        seniority='veteran'),
                                   dict(action_id='UUID_2',
                                        skill='testing',
                                        age=77,
                                        fluency='good',
                                        seniority='new')],
                          context=dict(age=35,
                                       gender='M',
                                       location='San Francisco',
                                       n_subs=15,
                                       intent='Closing an account',
                                       seniority='ancient'),
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor_id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertEquals(len(resp_data['list']), 2)

        max_ucb = 0
        for entry in resp_data['list']:
            self.assertTrue("score" in entry)
            self.assertTrue("id" in entry)
            self.assertTrue("estimated_reward" in entry)
            # if entry['id'] != 'UUID_2':
                # self.assertTrue(entry["score"] > 0)             # Some upper confidence at first
                # self.assertTrue(entry["estimated_reward"], 0)   # No data at first
            # else:
            self.assertEqual(entry["score"], 0)             # Some upper confidence at first
            self.assertEqual(entry["estimated_reward"], 0)  # No data at first
            if max_ucb < entry["score"]:
                max_ucb = entry["score"]

        feedback_data = dict(action=dict(action_id='UUID_1',
                                         skill='testing',
                                         age=27,
                                         fluency='good',
                                         seniority='veteran'),
                             context=dict(age=35,
                                          gender='M',
                                          location='San Francisco',
                                          n_subs=15,
                                          intent='Closing an account',
                                          seniority='ancient'),
                             token=token,
                             reward=100)
        self.client.post('/api/v2.0/predictors/%s/feedback' % first_predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')

        retrain(first_predictor)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor_id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertEquals(len(resp_data['list']), 2)

        new_max_ucb = 0
        uuid1_score = 0
        uuid2_score = 0
        uuid1_ex_reward = 0
        uuid2_ex_reward = 0
        for entry in resp_data['list']:
            self.assertTrue("score" in entry)
            self.assertTrue(entry["score"] > 0) # Some upper confidence at first
            self.assertTrue("id" in entry)
            self.assertTrue("estimated_reward" in entry)
            self.assertTrue(entry["estimated_reward"] > 0) # Had positive example, both should be positive
            if new_max_ucb < entry["score"]:
                new_max_ucb = entry["score"]
            if entry['id'] == "UUID_1":
                uuid1_score = entry["score"]
                uuid1_ex_reward = entry["estimated_reward"]
            if entry['id'] == "UUID_2":
                uuid2_score = entry["score"]
                uuid2_ex_reward = entry["estimated_reward"]

        # Overall max ucb should be higher since we just got positive reward
        self.assertTrue(new_max_ucb > max_ucb)
        # UCB for non-rated agent should be higher but estimated reward lower
        self.assertTrue(uuid1_ex_reward > uuid2_ex_reward, '%s > %s' % (uuid1_ex_reward, uuid2_ex_reward))
        self.assertTrue(uuid1_score > uuid2_score, '%s > %s' % (uuid1_score, uuid2_score))

    def test_filter_based_score(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self.setup_requirements(user_mail, user_password)
        token = self.get_token(user_mail, user_password)

        batch_data = [{u'name': u'Tester Testerson',
                       u'gender': u'M',
                       u'date_of_birth': u'06/06/1985',
                       u'date_of_hire': u'01/01/1988',
                       u'native_id': u'UUID_1',
                       u'location': u'San Francisco',
                       u'attached_data': dict(skill='testing',
                                              age=27,
                                              fluency='good',
                                              seniority='veteran',
                                              location='San Francisco')},
                      {u'name': u'Badboy Agent',
                       u'gender': u'M',
                       u'date_of_birth': u'07/11/1951',
                       u'date_of_hire': u'04/04/2004',
                       u'native_id': u'UUID_2',
                       u'location': u'San Francisco',
                       u'attached_data': dict(action_id='UUID_2',
                                              skill='testing',
                                              age=77,
                                              fluency='good',
                                              seniority='new',
                                              location='San Francisco')},
                      {u'name': u'Sadboy Agent',
                       u'gender': u'M',
                       u'date_of_birth': u'07/11/1982',
                       u'date_of_hire': u'04/04/2005',
                       u'native_id': u'UUID_3',
                       u'location': u'San Jose',
                       u'skills': {u'products': 3, u'hardware': 10}}]
        self.batch_create(token, batch_data)
        predictor = create_agent_matching_predictor(admin_user.account.id, is_test=True)
        predictor.action_type = TYPE_AGENTS
        predictor.save()

        feedback_data = dict(action=dict(action_id='UUID_2',
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
        self.client.post('/api/v2.0/predictors/%s/feedback' % predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')
        retrain(predictor)

        score_data = dict(action_filters='location=San Francisco',
                          context=dict(AGE=35,
                                       gender='M',
                                       location='San Francisco',
                                       n_subs=15,
                                       intention='Closing an account',
                                       seniority='ancient'),
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertEquals(len(resp_data['list']), 2)

        max_ucb = 0
        for entry in resp_data['list']:
            self.assertTrue("score" in entry)
            self.assertTrue("id" in entry)
            self.assertTrue("estimated_reward" in entry)
            self.assertEqual(entry["score"], 0)             # One case with a reward of 0
            self.assertEqual(entry["estimated_reward"], 0)  # One case with a reward of 0

            if max_ucb < entry["score"]:
                max_ucb = entry["score"]
        feedback_data = dict(action=dict(action_id=resp_data['list'][0]['id']),
                             context=dict(AGE=35,
                                          GENDER='M',
                                          LOCATION='San Francisco',
                                          N_SUBS=15,
                                          INTENTION='Closing an account',
                                          SENIORITY='ancient'),
                             token=token,
                             reward=100)
        self.client.post('/api/v2.0/predictors/%s/feedback' % predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')

        retrain(predictor)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertEquals(len(resp_data['list']), 2)

        new_max_ucb = 0
        for entry in resp_data['list']:
            self.assertTrue("score" in entry)
            self.assertTrue(entry["score"] > 0)             # Some upper confidence at first
            self.assertTrue("id" in entry)
            self.assertTrue("estimated_reward" in entry)
            self.assertTrue(entry["estimated_reward"] > 0)  # Had positive example, both should be positive
            if new_max_ucb < entry["score"]:
                new_max_ucb = entry["score"]

        # Overall max ucb should be higher since we just got positive reward
        self.assertTrue(new_max_ucb > max_ucb)

    def test_get_dataset_fields(self):
        self.login()
        expected_dataset_fields = [{'name': k, 'type': v.__class__.__name__} for k, v in InfomartEvent.fields.items()]

        params = {'dataset_name': 'TestDataSet'}
        response = self.client.post('/predictors/expressions/dataset_fields',
                                    data=json.dumps(params),
                                    content_type='application/json')
        resp_data = json.loads(response.data)
        self.assertTrue(resp_data['ok'])
        self.assertTrue(resp_data['dataset_fields'])
        self.assertTrue(resp_data['dataset_name'])

        self.assertEqual(resp_data['dataset_fields'], expected_dataset_fields)


    @unittest.skip('Skip for now, because it always fails at jenkins job')
    def test_predictor_multi_intentions(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self.setup_requirements(user_mail, user_password)
        token = self.get_token(user_mail, user_password)

        predictor = create_agent_matching_predictor(
            admin_user.account.id,
            state=ModelState(status=ModelState.STATUS_ACTIVE,
                             state=ModelState.CYCLE_NEW), is_test=True)
        predictor.models[0]._clf = 0
        predictor.models[0].model_type = HYBRID
        predictor.models[0].save()

        feedback_data = dict(action=dict(action_id='UUID_2',
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
        self.client.post('/api/v2.0/predictors/%s/feedback' % predictor.id,
                         data=json.dumps(feedback_data),
                         content_type='application/json',
                         base_url='https://localhost')
        retrain(predictor)

        # Each agent skill should create new intention label and new feature index in the classifier
        # test what happens if we have more than expected
        n_agents = 20
        n_scores = 15
        base_product = "PRODUCT_%s"
        base_uuid = 'UUID_%s'
        base_intention = "INTENTION_%s"

        agents = []
        for idx in xrange(n_agents):
            agents.append(dict(skills={base_product % idx : 7},
                               action_id=base_uuid % idx,
                               age=27,
                               seniority='veteran',
                               location="San Francisco"))

        # Each agent had a separate skill, intents would be created for all of them
        for idx in xrange(n_scores):
            score_data = dict(actions=[agents[idx], agents[idx + 1]],
                              context=dict(age=35,
                                           gender='M',
                                           location='San Francisco',
                                           n_subs=15,
                                           intention=base_intention % idx,
                                           seniority='ancient'),
                              token=token)
            resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                    data=json.dumps(score_data),
                                    content_type='application/json',
                                    base_url='https://localhost')
            resp_data = json.loads(resp.data)
            self.assertEquals(len(resp_data['list']), 2)

            for entry in resp_data['list']:
                self.assertTrue("score" in entry)
                self.assertTrue("id" in entry)
                self.assertTrue("estimated_reward" in entry)
                if entry['id'] != 'UUID_2':
                    self.assertTrue(entry["score"] > 0)             # Hybrid. Only global model got a 0.
                    self.assertTrue(entry["estimated_reward"] > 0)
                else:
                    self.assertEquals(entry["score"], 0)
                    self.assertEquals(entry["estimated_reward"], 0)

        for idx in xrange(n_scores):
            feedback_data = dict(action=agents[idx],
                                 context=dict(AGE=35,
                                              GENDER='M',
                                              LOCATION='San Francisco',
                                              N_SUBS=15,
                                              intention=base_intention % idx,
                                              seniority='ancient'),
                                 token=token,
                                 reward=100 if idx % 2 == 0 else 7)
            self.client.post('/api/v2.0/predictors/%s/feedback' % predictor.id,
                             data=json.dumps(feedback_data),
                             content_type='application/json',
                             base_url='https://localhost')
        retrain(predictor)
        # Check agents that actually got scored and see improvements
        for idx in xrange(n_scores - 1):
            score_data = dict(actions=[agents[idx], agents[idx + 1]],
                              context=dict(AGE=35,
                                           gender='M',
                                           location='San Francisco',
                                           n_subs=15,
                                           intention=base_intention % idx,
                                           seniority='ancient'),
                              token=token)
            resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor.id,
                                    data=json.dumps(score_data),
                                    content_type='application/json',
                                    base_url='https://localhost')
            resp_data = json.loads(resp.data)
            for entry in resp_data['list']:
                agent_number = int(entry['id'].split('_')[1])
                if agent_number % 2 == 0:
                    # We gave positive feedback
                    self.assertTrue(entry['estimated_reward'] > 40, entry)
                else:
                    # We gave negative feedback
                    self.assertTrue(entry['estimated_reward'] < 40, entry)

    def test_predictors_invalid_requests(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self.setup_requirements(user_mail, user_password)
        predictor = create_agent_matching_predictor(admin_user.account.id, is_test=True)
        token = self.get_token(user_mail, user_password)
        # Test with score / feedback invalid predictor id
        score_data = dict(actions=[dict(action_id='UUID_1',
                                        skill='testing',
                                        age=27,
                                        fluency='good',
                                        seniority='veteran'),
                                   dict(action_id='UUID_2',
                                        skill='testing',
                                        age=77,
                                        fluency='good',
                                        seniority='new')],
                          context=dict(AGE=35,
                                       gender='M',
                                       location='San Francisco',
                                       n_subs=15,
                                       intention='Closing an account',
                                       seniority='ancient'),
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % (str(predictor.id) + 'invalid'),
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])
        self.assertEqual(ERR_MSG_NO_PREDICTOR % (str(predictor.id) + 'invalid'), resp_data['error'])

        feedback_data = dict(action=dict(action_id='UUID_1',
                                         skill='testing',
                                         age=27,
                                         fluency='good',
                                         seniority='veteran'),
                             context=dict(AGE=35,
                                          gender='M',
                                          location='San Francisco',
                                          n_subs=15,
                                          intention='Closing an account',
                                          seniority='ancient'),
                             token=token,
                             reward=100)
        self.client.post('/api/v2.0/predictors/%s/feedback' % (str(predictor.id) + 'invalid'),
                             data=json.dumps(feedback_data),
                             content_type='application/json',
                             base_url='https://localhost')

        # Missing required field
        score_data.pop('context')
        resp = self.client.post('/api/v2.0/predictors/%s/score' % (str(predictor.id)),
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])
        self.assertEquals(ERR_MSG_MISSING_FIELD % 'context', resp_data['error'])

        # Missing action id
        score_data = dict(actions=[dict(skill='testing',
                                        age=27,
                                        fluency='good',
                                        seniority='veteran'),
                                   dict(skill='testing',
                                        age=77,
                                        fluency='good',
                                        seniority='new')],
                          context=dict(AGE=35,
                                       gender='M',
                                       location='San Francisco',
                                       n_subs=15,
                                       intention='Closing an account',
                                       seniority='ancient'),
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % (str(predictor.id)),
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])

        # Invalid context
        score_data = dict(actions=[dict(skill='testing',
                                        age=27,
                                        fluency='good',
                                        seniority='veteran'),
                                   dict(skill='testing',
                                        age=77,
                                        fluency='good',
                                        seniority='new')],
                          context=[1, 2, 3, 4],
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % (str(predictor.id)),
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])

        # No access to predictor
        new_account = Account.objects.create(name='test2')
        other_predictor = create_agent_matching_predictor(new_account.id, is_test=True)

        score_data = dict(actions=[dict(action_id='UUID_1',
                                        skill='testing',
                                        age=27,
                                        fluency='good',
                                        seniority='veteran'),
                                   dict(action_id='UUID_2',
                                        skill='testing',
                                        age=77,
                                        fluency='good',
                                        seniority='new')],
                          context=dict(AGE=35,
                                       gender='M',
                                       location='San Francisco',
                                       n_subs=15,
                                       intention='Closing an account',
                                       seniority='ancient'),
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % (str(other_predictor.id)),
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])
        self.assertEquals(ERR_MSG_NO_PREDICTOR % other_predictor.id, resp_data['error'])

    def test_testpredictor(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self.setup_requirements(user_mail, user_password,
                                             extra_schema=[{KEY_NAME: 'employeeId',
                                                            KEY_TYPE: TYPE_DICT}])
        token = self.get_token(user_mail, user_password)
        # create/reset testpredictor

        agent_profile_schema = admin_user.account.agent_profile._get()
        AgentProfile = agent_profile_schema.get_data_class()
        action_id = "17"
        ap = AgentProfile()
        ap.id = action_id
        ap.native_id = action_id

        # RELOAD IS NOT WORKING. SUPSECT IT HAS SOMETING TO DO WITH THE WAY
        # ID IS BEING HANDLED. Curiously it is stored as _id, and retrieved as id
        # when the details are printed out.
        ap.save()
        ap.reload()

        context = {u'status': u'VIP', u'last_call_intent': {}, u'first_name': u'John', u'last_name': u'B',
                   u'assigned_segments': {}, u'age': u'53', u'prr-ixn-start-utc': u'53583', u'cust_intent_ced': u'1',
                   u'intention': u'CLOSING_AN_ACCOUNT', u'products': {}, u'location': u'USA', u'groups': {},
                   u'seniority': u'NEW', u'sex': u'M', u'id': u'574db52707d0a354e79f327d', u'cust_req_survey': u'0'}
        score = 0.7
        request_data = dict(
            token=token,
            name="TestPredictor",
            lookup_map=(
              ((str(ap.id), context), score),
            )
        )
        resp = self.client.post('/api/v2.0/predictors/testid/testpredictor',
                                data=json.dumps(request_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data["ok"])
        predictor_id = resp_data["data"]["predictor_id"]
        
        score_data = dict(actions=[dict(action_id=action_id)],
                          context=context,
                          token=token)
        resp = self.client.post('/api/v2.0/predictors/%s/score' % predictor_id,
                                data=json.dumps(score_data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data2 = json.loads(resp.data) 
        reponse_item = resp_data2["list"][0]
        self.assertEquals(1, len(resp_data2["list"]))
        self.assertEquals(score, reponse_item["score"])
        self.assertEquals(action_id, reponse_item["id"])
        self.assertTrue(resp_data2['ok'])

    def test_reset(self):
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self.setup_requirements(user_mail, user_password)

        token = self.get_token(user_mail, user_password)
        predictor = create_agent_matching_predictor(admin_user.account.id, is_test=True)

        resp = self.client.post('/api/v2.0/predictors/%s/reset' % str(predictor.id),
                                content_type='application/json',
                                data=json.dumps({'token': token}),
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertTrue("ok", resp_data['status'])

    def test_expression_validate(self):
        self.login()
        predictor = create_agent_matching_predictor(str(self.user.account.id), is_test=True)
        entities_registry = EntitiesRegistry()

        def _validate(user_expression):
            expression_data = entities_registry.generate_expression_context(predictor, user_expression)
            params = {'expression_type': 'feedback_model',
                      'expression': expression_data['expression']}
            return self.client.post('/predictors/expressions/validate',
                                    data=json.dumps(params),
                                    content_type='application/json')

        # No longer valid
        # resp = _validate("collect(InfomartEvent)")  # simple mongo db expression
        # resp_data = json.loads(resp.data)
        # self.assertTrue(resp_data['ok'])

        # resp = _validate("collect(InfomartEvent) + isin(1, [1, 2])")  # multiple expression
        resp = _validate("isin(1, [1, 2])")
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        resp = _validate("1 + 3")
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        resp = _validate("1 + []")  # invalid expression
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])

        resp = _validate("collect(InfomartEvent")  # invalid syntax, missing )
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])

        resp = _validate("abcdef(InfomartEvent)")  # invalid operator
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])
