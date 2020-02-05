""" Test construction for post/matchable response
"""
import copy
import json

from bson import ObjectId
from pprint import pprint
from nose.tools import eq_
from deepdiff import DeepDiff
from dateutil.relativedelta import relativedelta

from solariat.utils.timeslot import now
from solariat.utils.packing import pack_object, unpack_object
from solariat_nlp.bandit.models import DEFAULT_CONFIGURATION, AGENT_MATCHING_CONFIGURATION
from solariat_bottle.db.account import Account, AccountMetadata
from solariat_bottle.db.predictors.models.linucb import LinUCBPredictorModel, ModelState
from solariat_bottle.tests.base import MainCase, UICase, UICaseSimple, setup_agent_schema
from solariat_bottle.db.next_best_action.actions import Action
from solariat_bottle.db.predictors.base_predictor import (BasePredictor, TYPE_BOOLEAN,
    CompositePredictor, TYPE_GENERATED, TYPE_AGENTS, LocalModel)
from solariat_bottle.db.predictors.factory import create_agent_matching_predictor, create_chat_engagement_predictor, create_supervisor_alert_predictor
from solariat_bottle.db.predictors.base_score import BaseScore
from solariat_bottle.db.predictors.classifiers import GLOBAL_KEY
from solariat_bottle.db.predictors.base_predictor import LocalModel
from solariat_bottle.jobs.config import jobs_config
from solariat_bottle.views.account import PredictorConfigurationConversion

inf = float('inf')

CONFIGURATION_DATA = {
'SimpleAgentMatchingPredictor': {
     'type': 'Agent Routing',
     'reward_name': 'NPS',
     'action_model': [
        {
            'name': 'age',
            'type': 'NumericRange',
            'values': [('underage', 18), ('young', 30), ('midage', 50), ('old', None)]
        },
        {
            'name': 'gender',
            'type': 'Label',
            'values': ['m', 'f']
        }],
    'context_model': [
        {
            'name': 'intention',
            'type': 'Label',
            'values': [],
            'limit': 20
        },
        {
            'name': 'location',
            'type': 'Lookup',
            'values': [('US-WEST', ['San Francisco', 'San Diego', ' Seattle']), ('US-EAST', ['New York', 'Miami'])],
            'limit': 50
        }]
    }
}


class AccountTest(UICase):

    def setUp(self):
        MainCase.setUp(self)
        self.account = Account(name="Solariat Test")
        self.account.save()
        self.user.account = self.account
        self.user.save()
        self.account.add_perm(self.user)

        self.customer_data = dict(
                first_name = 'Sujan',
                last_name = 'Shakya',
                age = 30,
                account_id = self.account.id,
                location = 'Nepal',
                sex = 'M',
                account_balance = 1000,
                last_call_intent = ['buy a house'],
                num_calls = 10,
                seniority = 'mediocre',
        )
        self.action = Action.objects.create(
            account_id=self.account.id,
            name="Got a question? Chat Now!",
            tags=[],
            channels=[]
        )
        self.login()


    def test_in_memory_cache(self):
        ''' We do cache LocalModel in threading local object
            variable is called _in_memory_model_cache
            lets see that cache works as we expect '''

        predictor = create_agent_matching_predictor(
            self.user.account.id,
            state=ModelState(state=ModelState.CYCLE_NEW,
                             status=ModelState.STATUS_ACTIVE), is_test=True)
        # we have 1 default global model
        self.assertEqual(len(predictor.models), 1)
        mdl1 = predictor.models[0]
        mdl1.model_type = 'DISJOINT'
        predictor.save_model(mdl1)
        # we didn't do anything with model, so it wasn't saved
        self.assertEqual(LocalModel.objects.count(), 0)
        # lets train model and make sure LocalModel was created
        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='mediocre')
        agent_data = {'action_id': str(self.action.id),
                      'id': self.action.id,
                      'age': 26,
                      'skill': 'Awesome',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}
        predictor.train_on_feedback_batch([customer_data], [agent_data], [.9])
        self.assertEqual(LocalModel.objects.count(), 2)
        # now lets make sure that if we 
        # read this model again from mongo
        # _in_memory_model_cache will be used
        LocalModel.objects.coll.remove({})
        self.assertEqual(LocalModel.objects.count(), 0)
        mdl2 = LinUCBPredictorModel.objects.get(mdl1.id)
        self.assertEqual(len(mdl2.clf._model_cache), 2)
        self.assertEqual(mdl2.clf._model_cache[GLOBAL_KEY].id, mdl1.clf._model_cache[GLOBAL_KEY].id)
        old_local_model_id = mdl2.clf._model_cache[GLOBAL_KEY].id
        # lets reset model and check that _in_memory_model_cache was updated
        mdl1.clf.reset_model()
        self.assertNotEqual(old_local_model_id, mdl1.clf._model_cache[GLOBAL_KEY])
        # lets manually erase cache and check that reatrain call will update cache
        from solariat_bottle.db.predictors.classifiers import _in_memory_model_cache
        _in_memory_model_cache.map = {}
        predictor.train_on_feedback_batch([customer_data], [agent_data], [.9])
        self.assertTrue(GLOBAL_KEY in _in_memory_model_cache.map[mdl1.id])
        self.assertTrue(str(self.action.id) in _in_memory_model_cache.map[mdl1.id])

        # lets just check that scoring works
        predictor.select_model(mdl1)
        scores = predictor.score([dict(action_id=self.action.id)], customer_data)
        score = scores[0]
        obj_id, score1, score2 = score
        self.assertTrue(isinstance(obj_id, ObjectId))
        self.assertTrue(isinstance(score1, float))
        self.assertTrue(isinstance(score2, float))


    def test_predictors_overlap(self):
        ''' two different predictors should use two different models
            and two different model's packed_clf fields
        '''
        predictor1 = create_chat_engagement_predictor(self.user.account.id)
        predictor2 = create_supervisor_alert_predictor(self.user.account.id)
        self.assertEqual(len(predictor1.models), 1)
        self.assertEqual(len(predictor2.models), 1)
        model1 = predictor1.models[0]
        model2 = predictor2.models[0]
        self.assertNotEqual(id(predictor1), id(predictor2))
        self.assertNotEqual(id(model1), id(model2))
        self.assertTrue(GLOBAL_KEY in model1.clf._model_cache)
        self.assertTrue(GLOBAL_KEY in model2.clf._model_cache)
        model1.save()
        model2.save()
        self.assertTrue(GLOBAL_KEY in model1.clf_map)
        self.assertTrue(GLOBAL_KEY in model2.clf_map)
        self.assertTrue(isinstance(model1.clf_map[GLOBAL_KEY], ObjectId))
        self.assertTrue(isinstance(model2.clf_map[GLOBAL_KEY], ObjectId))

        # initially clf should be equal
        # self.assertEqual(
        #     pack_object(model1.clf.model_cache[GLOBAL_KEY]),
        #     pack_object(model2.clf.model_cache[GLOBAL_KEY])
        # )

        # now we posting feedbacks and this should change packed_clf fields
        # predictor1.feedback(self.customer_data, dict(action_id=self.action.id), reward=.9)
        # predictor2.feedback(self.customer_data, dict(action_id=self.action.id), reward=.9)

        # here we actually execute on received feedback
        predictor1.train_on_feedback_batch(
            [self.customer_data], [dict(action_id=str(self.action.id))], [.9])
        predictor2.train_on_feedback_batch(
            [self.customer_data], [dict(action_id=str(self.action.id))], [.9])

        model1.reload()
        model2.reload()
        self.assertNotEqual(model1.clf_map, model2.clf_map)
        # self.assertNotEqual(id(model1.packed_clf), id(model2.packed_clf))

    def test_model_sub_vectors(self):
        ''' Checking that change of models weights
            result in score change
        '''
        from solariat_bottle.db.auth import default_access_groups
        predictor = create_agent_matching_predictor(
            self.user.account.id,
            state=ModelState(state=ModelState.CYCLE_NEW,
                             status=ModelState.STATUS_ACTIVE), is_test=True)
        predictor.acl = default_access_groups(self.user)
        predictor.save()

        create_data = dict(context_features=['age', 'intent'],
                           action_features=['skill', 'fluency'],
                           display_name='test1')
        resp = self.client.post('/predictors/%s/models' % predictor['id'],
                                data=json.dumps(create_data),
                                content_type='application/json')

        self.assertEqual(resp.status_code, 201)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        created_model1_id = resp_data['data']['id']

        create_data = dict(context_features=['age', 'gender'],
                           action_features=['skill', 'fluency'],
                           display_name='test2')
        resp = self.client.post('/predictors/%s/models' % predictor['id'],
                                data=json.dumps(create_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        created_model2_id = resp_data['data']['id']

        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='mediocre')
        agent_data = {'action_id': str(self.action.id),
                      'id': self.action.id,
                      'age': 26,
                      'skill': 'Awesome',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}
        predictor._cached_models = None
        predictor.reload()
        #'id', 'age', 'skill', 'seniority', 'fluency'
        # 'age', 'gender', 'location', 'n_subs', 'intent', 'seniority'
        for p_model in predictor.models:
            p_model.state.status = 'ACTIVE'
            p_model.save()

        predictor.train_on_feedback_batch([customer_data], [agent_data], [.1],
                                          model=predictor.as_model_instance(predictor.models[0]))
        predictor.train_on_feedback_batch([customer_data], [agent_data], [.5],
                                          model=predictor.as_model_instance(predictor.models[1]))
        predictor.train_on_feedback_batch([customer_data], [agent_data], [.9],
                                          model=predictor.as_model_instance(predictor.models[2]))

        self.assertEqual(len(predictor.models), 3)
        # print 11111, predictor.score([dict(action_id=self.str(action.id))], self.customer_data)
        predictor.models[0].weight = 1.0
        predictor.models[1].weight = 0.0
        predictor.models[2].weight = 0.0
        model1_name = predictor.select_model().display_name
        model1_score = predictor.score([dict(action_id=self.action.id)], self.customer_data)[0][2]

        self.assertEqual(predictor.models[0].weight, 1.0)
        predictor.models[0].weight = 0.0
        predictor.models[1].weight = 1.0
        predictor.models[2].weight = 0.0
        model2_name = predictor.select_model().display_name
        model2_score = predictor.score([dict(action_id=self.action.id)], self.customer_data)[0][2]

        predictor.models[0].weight = 0.0
        predictor.models[1].weight = 0.0
        predictor.models[2].weight = 1.0
        model3_name = predictor.select_model().display_name
        model3_score = predictor.score([dict(action_id=self.action.id)], self.customer_data)[0][2]

        # checking that names were changing
        self.assertNotEqual(model1_name, model2_name)
        self.assertNotEqual(model2_name, model3_name)

        # checking that scores were changing
        self.assertNotEqual(model1_score, model2_score)
        self.assertNotEqual(model2_score, model3_score)

    def test_score_counter(self):
        ''' Checking that score() call
            triggers BaseScore.counter for updating a stats
        '''
        predictor = create_agent_matching_predictor(
            self.user.account.id,
            state=ModelState(state=ModelState.CYCLE_NEW,
                             status=ModelState.STATUS_ACTIVE), is_test=True
        )

        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='mediocre')
        agent_data = {'action_id': str(self.action.id),
                      'id': self.action.id,
                      'age': 26,
                      'skill': 'Awesome',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}
        #'id', 'age', 'skill', 'seniority', 'fluency'
        # 'age', 'gender', 'location', 'n_subs', 'intent', 'seniority'
        predictor.train_on_feedback_batch([customer_data], [agent_data], [.9])

        # lets call score and check counter and number of records in Base Score
        t0 = now()
        predictor.score([dict(action_id=self.action.id)], self.customer_data)
        self.assertEqual(BaseScore.objects.count(), 1)
        base_score = BaseScore.objects.get(matching_engine=predictor.id)
        self.assertEqual(base_score.counter, 1)     # One is because of metric track score
        self.assertEqual(BaseScore.objects.count(), 1)
        # checking latency
        self.assertGreater(base_score.latency, 0)
        max_latency = (now() - t0).total_seconds()
        self.assertLess(base_score.latency, max_latency)
        self.assertEqual(base_score.cumulative_latency, base_score.latency)
        latency = base_score.latency

        # Doing the same for second time
        predictor.score([dict(action_id=self.action.id)], self.customer_data)
        self.assertEqual(BaseScore.objects.count(), 1)
        base_score.reload()
        self.assertEqual(base_score.counter, 2)
        # checking latency
        max_cumulative_latency = (now() - t0).total_seconds()
        self.assertTrue(latency < base_score.cumulative_latency < max_cumulative_latency)
        self.assertLess(base_score.latency, max_cumulative_latency / 2.0)


class PredictorsSettingsPage(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.jobs_origin_transport = jobs_config.transport
        self.setup_jobs_transport('serial')
        self.login()

        account_metadata = AccountMetadata(
            account=self.account,
            predictors_configuration=DEFAULT_CONFIGURATION)
        account_metadata.save()

    def tearDown(self):
        self.setup_jobs_transport(self.jobs_origin_transport)
        return UICase.tearDown(self)

    def test_crud_composite_predictor(self):
        self.assertEqual(BasePredictor.objects.count(), 0)
        self.assertEqual(CompositePredictor.objects.count(), 0)
        """
        {"label": "res_role", "type": "label", "field_expr": "RESOURCE_ROLE"}
        """
        create_data = dict(action_features_schema=[{'label': "id",
                                                    'type': 'label',
                                                    'field_expr': "id"},
                                                   {'label': "age",
                                                    'type': 'label',
                                                    'field_expr': "age"},
                                                   {'label': "skill",
                                                    'type': 'label',
                                                    'field_expr': "skill"},
                                                   {'label': "seniority",
                                                    'type': 'label',
                                                    'field_expr': "seniority"},
                                                   {'label': "fluency",
                                                    'type': 'label',
                                                    'field_expr': "fluency"}],
                           context_features_schema=[{'label': "age",
                                                     'type': 'label',
                                                     'field_expr': "age"},
                                                    {'label': "gender",
                                                     'type': 'label',
                                                     'field_expr': "gender"},
                                                    {'label': "location",
                                                     'type': 'label',
                                                     'field_expr': "location"},
                                                    {'label': "n_subs",
                                                     'type': 'label',
                                                     'field_expr': "n_subs"},
                                                    {'label': "intent",
                                                     'type': 'label',
                                                     'field_expr': "intent"},
                                                    {'label': "seniority",
                                                     'type': 'label',
                                                     'field_expr': "seniority"}],
                           description="Predictor for matching agent against customer.",
                           name="Test new agent matching#1",
                           reward="CSAT")

        self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        create_data['name'] = "Test new agent matching#2"
        self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        create_data['name'] = "Test new agent matching#3"
        self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(BasePredictor.objects.count(), 3)
        self.assertEqual(CompositePredictor.objects.count(), 0)
        p_names = [p.name for p in BasePredictor.objects()]

        composite_predictor_data = {'predictors_list': [p_names[0].replace(' ', ''),
                                                        p_names[1].replace(' ', ''),
                                                        p_names[2].replace(' ', '')],
                                    'raw_expression': "%s + %s * %s" % (p_names[0].replace(' ', ''),
                                                                        p_names[1].replace(' ', ''),
                                                                        p_names[2].replace(' ', '')),
                                    'predictor_type': BasePredictor.TYPE_COMPOSITE,
                                    'name': 'The Composite Predictor'}
        resp_data = self.client.post('/predictors/json',
                                     data=json.dumps(composite_predictor_data),
                                     content_type='application/json',
                                     base_url='https://localhost')
        resp_data = json.loads(resp_data.data)
        predictor_id = resp_data['obj']['id']
        self.assertEqual(BasePredictor.objects.count(), 4)
        self.assertEqual(CompositePredictor.objects.count(), 1)
        item = resp_data['obj']
        self.assertTrue(item['is_composite'])
        self.assertEqual(len(item['models_data']), 0)
        self.assertEqual(item['account_id'], str(self.account.id))
        self.assertEqual(item['metric'], None)
        self.assertEqual(item['models_count'], 3)
        self.assertEqual(item['name'], composite_predictor_data["name"])

        update_data = {'predictors_list': [p_names[0].replace(' ', ''),
                                           p_names[1].replace(' ', '')]}
        resp_data = self.client.post('/predictors/%s' % predictor_id,
                                     data=json.dumps(update_data),
                                     content_type='application/json',
                                     base_url='https://localhost')
        resp_data = json.loads(resp_data.data)
        predictor_id = resp_data['predictor']['id']
        self.assertEqual(BasePredictor.objects.count(), 4)
        self.assertEqual(CompositePredictor.objects.count(), 1)
        item = resp_data['predictor']
        self.assertTrue(item['is_composite'])
        self.assertEqual(len(item['models_data']), 0)
        self.assertEqual(item['account_id'], str(self.account.id))
        self.assertEqual(item['metric'], None)
        self.assertEqual(item['models_count'], 2)
        self.assertEqual(item['name'], composite_predictor_data["name"])

    def load_dataset(self):
        from solariat_bottle.tests.predictors.test_dataset import Dataset, CSV_FILEPATH, CsvDataLoader, finish_data_load
        name = 'TestApplySchema'

        with open(CSV_FILEPATH) as csv_file:
            raw_items = len([1 for _ in csv_file]) - 1  # minus head

        with open(CSV_FILEPATH) as csv_file:
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            dataset = self.user.account.datasets.add_dataset(self.user, name, data_loader)

        self.assertEqual(dataset.sync_status, Dataset.OUT_OF_SYNC)
        self.assertEqual(dataset.rows, raw_items)

        dataset.apply_sync()

        self.assertEqual(dataset.sync_status, Dataset.SYNCED)
        self.assertEqual(dataset.sync_progress, 100)
        self.assertEqual(dataset.rows, raw_items)
        self.assertEqual(dataset.data_coll.count(), raw_items)
        d = dataset
        self.assertTrue(d.sync_collection and d.sync_collection != d.mongo_collection)
        items_synced = dataset.items_synced
        self.assertEqual(dataset.data_sync_coll.count(), items_synced)

        dataset.accept_sync()
        return dataset

    # TODO: Move them in a helper mixin for both test dataset and test predictor
    def get_post_data(self, csv_file):
        from solariat_bottle.tests.predictors.test_dataset_view import CSV_FILENAME, CREATE_UPDATE_DATASET_NAME
        file_obj = (csv_file, CSV_FILENAME)
        return dict(name=CREATE_UPDATE_DATASET_NAME,
                    csv_file=file_obj)

    def test_predictor_trends(self):
        self.assertEqual(BasePredictor.objects.count(), 0)
        dataset = self.load_dataset()
        create_data = {"name": "New Predictor",
                       "dataset": str(dataset.id),
                       "metric": "CUSTOMER_ACW_DURATION",
                       "action_id_expression": "EMPLOYEE_ID",
                       "action_features_schema": [{"label": "res_role", "type": "label", "field_expr": "RESOURCE_ROLE"},
                                                  {"label": "vq", "type": "label", "field_expr": "VIRTUAL_QUEUE"},
                                                  {"label": "sid", "type": "label", "field_expr": "SKILLID"},
                                                  {"label": "w_id", "type": "expression", "field_expr": "int(EMPLOYEE_ID) / 20.0"}],
                       "context_features_schema": [
                           {"label": "itype", "type": "label", "field_expr": "INTERACTION_TYPE"},
                           {"label": "c_hold", "type": "label", "field_expr": "CUSTOMER_HOLD_DURATION"}],
                       "sync_status": "IN_SYNC",
                       "from_dt": 1461135600,
                       "to_dt": 1468652400,
                       "model_type": "GLOBAL"}
        resp = self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(BasePredictor.objects.count(), 1)
        resp_data = json.loads(resp.data)
        self.assertTrue(len(resp_data['obj']['metric_values_range']) == 2)  # [min, max]
        self.assertTrue(resp_data['ok'])

        predictor_id = resp_data['obj']['id']
        model_id = resp_data['obj']['models_data'][0]['model_id']
        predictor = BasePredictor.objects.get(predictor_id)

        dset_count = dataset.get_data_class().objects.count()
        self.assertEqual(predictor.training_data_class.objects.count(), 0)
        self.client.post('/predictors/%s/models/%s/upsertFeedback' % (predictor_id, model_id),
                         content_type='application/json')
        self.assertEqual(predictor.training_data_class.objects.count(), dset_count)

        self.client.post('/predictors/%s/models/%s/purgeFeedback' % (predictor_id, model_id),
                         content_type='application/json')
        self.assertEqual(predictor.training_data_class.objects.count(), 0)

        self.client.post('/predictors/%s/models/%s/upsertFeedback' % (predictor_id, model_id),
                         content_type='application/json')
        self.assertEqual(predictor.training_data_class.objects.count(), dset_count)


        from datetime import datetime, date, timedelta
        today = datetime.now()

        to_date = date(today.year, today.month, 1) + timedelta(hours=24 * 31)
        from_date = date(today.year, today.month, 1) - timedelta(hours=24 * 31)
        date_format = '%m/%d/%Y'
        facets_data = {"predictor_id": str(predictor.id), "models": [], "plot_type": "time",
                       "plot_by": "ab testing", "from": from_date.strftime(date_format),
                       "to": to_date.strftime(date_format), "level": "day",
                       "request_url": "/predictors/facets/json", "action_vector": {"res_role": []},
                       "context_vector": {"itype": []}}
        facets_request = self.client.post('predictors/facets/json',
                                          data=json.dumps(facets_data),
                                          content_type='application/json')
        resp_data = json.loads(facets_request.data)
        self.assertTrue(resp_data['ok'])

        self.assertEqual(len(resp_data['list']), 1) # A'B testing enabled
        for entry in resp_data['list']:
            self.assertTrue('data' in entry)
            self.assertEqual(len(entry['data'][0]), 2)
        facets_data['plot_by'] = "all"
        facets_request = self.client.post('predictors/facets/json',
                                          data=json.dumps(facets_data),
                                          content_type='application/json')
        resp_data = json.loads(facets_request.data)
        self.assertTrue(resp_data['ok'])
        self.assertEqual(len(resp_data['list']), 1) # A'B testing disabled
        for entry in resp_data['list']:
            self.assertTrue('data' in entry)
            self.assertEqual(len(entry['data'][0]), 2)

        # Now for distribution view
        facets_data['plot_type'] = 'distribution'
        facets_request = self.client.post('predictors/facets/json',
                                          data=json.dumps(facets_data),
                                          content_type='application/json')
        resp_data = json.loads(facets_request.data)
        self.assertTrue(resp_data['ok'])

        self.assertEqual(len(resp_data['list']), 1)     # No A/B testing
        self.assertTrue('label' in resp_data['list'][0] and 'value' in resp_data['list'][0])

        facets_data['plot_by'] = 'ab testing'
        facets_request = self.client.post('predictors/facets/json',
                                          data=json.dumps(facets_data),
                                          content_type='application/json')
        resp_data = json.loads(facets_request.data)
        self.assertTrue(resp_data['ok'])

        self.assertEqual(len(resp_data['list']), 1)     # With A/B testing

        facets_data['plot_by'] = 'res_role'
        facets_request = self.client.post('predictors/facets/json',
                                          data=json.dumps(facets_data),
                                          content_type='application/json')
        resp_data = json.loads(facets_request.data)
        self.assertTrue(resp_data['ok'])
        self.assertTrue(len(resp_data['list']) > 2)

    def test_predictor_create_then_train(self):
        self.assertEqual(BasePredictor.objects.count(), 0)
        dataset = self.load_dataset()
        create_data = {"name": "New Predictor",
                       "dataset": str(dataset.id),
                       "metric": "CUSTOMER_ACW_DURATION",
                       "action_id_expression": "EMPLOYEE_ID",
                       "action_features_schema": [{"label": "res_role", "type": "label", "field_expr": "RESOURCE_ROLE"},
                                                  {"label": "vq", "type": "label", "field_expr": "VIRTUAL_QUEUE"},
                                                  {"label": "sid", "type": "label", "field_expr": "SKILLID"},
                                                  {"label": "w_id", "type": "expression", "field_expr": "int(EMPLOYEE_ID) / 20.0"}],
                       "context_features_schema": [
                           {"label": "itype", "type": "label", "field_expr": "INTERACTION_TYPE"},
                           {"label": "c_hold", "type": "label", "field_expr": "CUSTOMER_HOLD_DURATION"}],
                       "sync_status": "IN_SYNC",
                       "from_dt": 1461135600,
                       "to_dt": 1468652400,
                       "model_type": "GLOBAL"}
        resp = self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(BasePredictor.objects.count(), 1)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        predictor_id = resp_data['obj']['id']
        model_id = resp_data['obj']['models_data'][0]['model_id']
        predictor = BasePredictor.objects.get(predictor_id)

        dset_count = dataset.get_data_class().objects.count()
        self.assertEqual(predictor.training_data_class.objects.count(), 0)
        self.client.post('/predictors/%s/models/%s/upsertFeedback' % (predictor_id, model_id),
                         content_type='application/json')
        self.assertEqual(predictor.training_data_class.objects.count(), dset_count)

        one_item = predictor.training_data_class.objects.find_one()
        expected_schema = [item for item in one_item.context.keys()]
        expected_schema.extend([item for item in one_item.action.keys()])
        expected_schema.append(predictor.metric)

        fetch_data = dict(limit=dset_count + 1, offset=0)
        resp = self.client.get('/predictors/%s/data/json' % predictor.id,
                               data=json.dumps(fetch_data),
                               content_type='application/json')
        resp_data = json.loads(resp.data)
        items = resp_data['list']
        schema = resp_data['schema']
        # First feedback record
        self.assertEqual(len(items), dset_count)
        item = items[0]
        self.assertSetEqual(set(item.keys()), set(expected_schema))

        # Should be a duplicate predictor name and ail
        resp = self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])
        self.assertEqual(BasePredictor.objects.count(), 1)

        create_data['name'] = create_data['name'] + '_edited'
        resp = self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        self.assertEqual(BasePredictor.objects.count(), 2)

    def test_crud_predictor(self):
        # Initial user is only admin, should have access only to that list
        self.assertEqual(BasePredictor.objects.count(), 0)
        context = [{"type": "expression",
                    "field_expr": "bucket(age, ['YOUNG', 'OLD'], [50, 100])",
                    "label": "customer_age"},
                   {"type": "label",
                    "field_expr": "gender",
                    "label": "customer_gender"}]
        action = [{"type": "expression",
                   "field_expr": "bucket(age, ['YOUNG', 'OLD'], [45, 65])",
                   "label": "agent_age"}, ]
        create_data = dict(description="Predictor for matching agent against customer.",
                           name="Test new agent matching",
                           context_features_schema=context,
                           action_features_schema=action,
                           score_expression="p_score + 1",
                           metric="CSAT")
        resp = self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(BasePredictor.objects.count(), 1)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        item = resp_data['obj']
        self.assertEqual(len(item['models_data']), 1)
        self.assertEqual(item['account_id'], str(self.account.id))
        self.assertEqual(item['score_expression'], create_data['score_expression'])
        self.assertEqual(item['metric'], 'CSAT')
        self.assertEqual(item['models_count'], 1)
        self.assertEqual(item['name'], "Test new agent matching")
        self.assertListEqual(item['context_features_schema'], context)
        self.assertListEqual(item['action_features_schema'], action)

        resp = self.client.get('/predictors/' + str(item['id']))
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        item = resp_data['predictor']
        self.assertEqual(len(item['models_data']), 1)
        self.assertEqual(item['account_id'], str(self.account.id))
        self.assertEqual(item['metric'], 'CSAT')
        self.assertEqual(item['models_count'], 1)
        self.assertEqual(item['name'], "Test new agent matching")

        resp = self.client.get('/predictors/%s/models?with_deactivated=true' % item['id'])
        resp_data = json.loads(resp.data)
        self.assertEqual(len(resp_data['data']), 1)
        for entry in resp_data['data']:
            for key in ["status", "task_data", "display_name", "description", "parent", "predictor",
                        "counter", "weight", "version"]:
                self.assertTrue(key in entry, "Did not find key " + key)
            self.assertIsNone(entry['version'])
            self.assertEqual(entry['state'], ModelState.CYCLE_NEW)
            self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
            self.assertEqual(entry['weight'], 1.0)

        create_data["action_features_schema"].append({"type": "label",
                                                      "field_expr": "SEGMENT",
                                                      "label": "customer_segment"})
        create_data["context_features_schema"][0]["field_expr"] = "bucket(age, ['YOUNG', 'MIDAGE', 'OLD'], [35, 52, 100])"
        create_data['id'] = item['id']
        resp = self.client.post('/predictors/%s' % item['id'],
                                data=json.dumps(create_data),
                                content_type='application/json')
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        item = resp_data['predictor']
        self.assertListEqual(item['context_features_schema'], create_data["context_features_schema"])
        self.assertListEqual(item['action_features_schema'], create_data["action_features_schema"])

    def test_model_lifecycle(self):
        self.assertEqual(BasePredictor.objects.count(), 0)

        create_data = dict(action_features_schema=[{'label': "id",
                                                    'type': 'label',
                                                    'field_expr': "id"},
                                                   {'label': "age",
                                                    'type': 'label',
                                                    'field_expr': "age"},
                                                   {'label': "skill",
                                                    'type': 'label',
                                                    'field_expr': "skill"},
                                                   {'label': "seniority",
                                                    'type': 'label',
                                                    'field_expr': "seniority"},
                                                   {'label': "fluency",
                                                    'type': 'label',
                                                    'field_expr': "fluency"}],
                           context_features_schema=[{'label': "age",
                                                     'type': 'label',
                                                     'field_expr': "age"},
                                                    {'label': "gender",
                                                     'type': 'label',
                                                     'field_expr': "gender"},
                                                    {'label': "location",
                                                     'type': 'label',
                                                     'field_expr': "location"},
                                                    {'label': "n_subs",
                                                     'type': 'label',
                                                     'field_expr': "n_subs"},
                                                    {'label': "intent",
                                                     'type': 'label',
                                                     'field_expr': "intent"},
                                                    {'label': "seniority",
                                                     'type': 'label',
                                                     'field_expr': "seniority"}],
                           description="Predictor for matching agent against customer.",
                           name="Test new agent matching",
                           metric="CSAT")
        resp = self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(BasePredictor.objects.count(), 1)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        item = resp_data['obj']
        self.assertEqual(len(item['models_data']), 1)
        self.assertEqual(item['account_id'], str(self.account.id))
        self.assertEqual(item['metric'], 'CSAT')

        # Initial state, all inactive
        resp = self.client.get('/predictors/%s/models?with_deactivated=true' % item['id'])
        resp_data = json.loads(resp.data)
        self.assertEqual(len(resp_data['data']), 1)
        for entry in resp_data['data']:
            self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
            self.assertEqual(entry['state'], ModelState.CYCLE_NEW)
        last_model_id = entry['id']

        # Now train models and wait, at end should be trained and inactive
        train_data = dict(action='train')
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(train_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400) # bad request, missing model ID
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])

        train_data['id'] = last_model_id

        # No training data found
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(train_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 500)

        action = Action.objects.create(account_id=self.account.id,
                                       name="Got a question? Chat Now!",
                                       tags=[],
                                       channels=[])
        predictor = BasePredictor.objects.find_one()

        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='mediocre')
        agent_data = {'action_id': str(action.id),
                      'id': str(action.id),
                      'age': 26,
                      'skill': 'Awesome',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}
        #'id', 'age', 'skill', 'seniority', 'fluency'
        # 'age', 'gender', 'location', 'n_subs', 'intent', 'seniority'
        predictor.feedback(customer_data,
                           agent_data,
                           reward=.9)
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(train_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        # import time
        # time.sleep(1)    # No feedback, retrain done instantly

        # That one trained model should be trained but still inactive since we didn't de-activate it
        resp = self.client.get('/predictors/%s/models?with_deactivated=true' % item['id'])
        resp_data = json.loads(resp.data)
        self.assertEqual(len(resp_data['data']), 1)     # Retrain would have created new model
        for entry in resp_data['data']:
            self.assertTrue(entry['quality'])
            quality = entry['quality'][0]
            self.assertTrue(quality['measure'].lower() in entry)
            if entry['id'] != last_model_id:
                self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_NEW)
            else:
                self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_TRAINED)

        # Retrain inactive model, should not create new model instance, model state should remain the same
        retrain_data = dict(action='retrain',
                            id=last_model_id)
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(retrain_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        resp = self.client.get('/predictors/%s/models?with_deactivated=true' % item['id'])
        resp_data = json.loads(resp.data)
        self.assertEqual(len(resp_data['data']), 1)
        for entry in resp_data['data']:
            if entry['id'] != last_model_id:
                self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_NEW)
            else:
                self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_TRAINED)

        # Now make model active
        activate_data = dict(action='activate',
                             id=last_model_id)
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(activate_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        # That one trained model should now be locked and active since we didn't de-activate it
        resp = self.client.get('/predictors/%s/models?with_deactivated=true' % item['id'])
        resp_data = json.loads(resp.data)
        self.assertEqual(len(resp_data['data']), 1)     # Retrain would have created new model
        old_model_ids = []
        for entry in resp_data['data']:
            if entry['id'] != last_model_id:
                self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_NEW)
            else:
                self.assertEqual(entry['status'], ModelState.STATUS_ACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_LOCKED)
            old_model_ids.append(entry['id'])

        # Retrain model, should create new model instance and switch old one to inactive
        retrain_data = dict(action='retrain',
                            id=last_model_id)
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(retrain_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        # time.sleep(1)
        # Now we should have 4 models, the one retrained switched to inactive, new one has version 1 and is trained
        resp = self.client.get('/predictors/%s/models?with_deactivated=true' % item['id'])
        resp_data = json.loads(resp.data)
        self.assertEqual(len(resp_data['data']), 2)     # Retrain would have created new model
        for entry in resp_data['data']:
            if entry['id'] not in old_model_ids:
                new_model_id = entry['id']
                self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_TRAINED)
                self.assertEqual(entry['version'], 1)

            else:
                if entry['id'] != last_model_id:
                    self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
                    self.assertEqual(entry['state'], ModelState.CYCLE_NEW)
                else:
                    self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
                    self.assertEqual(entry['state'], ModelState.CYCLE_LOCKED)

        # Now activate the latest trained model, should keep same version and lock
        activate_data = dict(action='activate',
                             id=new_model_id)
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(activate_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        resp = self.client.get('/predictors/%s/models?with_deactivated=true' % item['id'])
        resp_data = json.loads(resp.data)
        self.assertEqual(len(resp_data['data']), 2)
        for entry in resp_data['data']:
            if entry['id'] == new_model_id:
                self.assertEqual(entry['status'], ModelState.STATUS_ACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_LOCKED)
                self.assertEqual(entry['version'], 1)

        # Create one extra active model so we can play with deactivation cycle
        create_data = dict(context_features=['age', 'gender', 'intent'],
                           action_features=['skill', 'fluency'])
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(create_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        created_model_id = resp_data['data']['id']

        train_data['id'] = created_model_id
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(train_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        activate_data = dict(action='activate',
                             id=created_model_id)
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(activate_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        # De-activate it and activate it again, should be same version
        deactivate_data = dict(action='deactivate',
                               id=new_model_id)
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(deactivate_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        resp = self.client.get('/predictors/%s/models?with_deactivated=true' % item['id'])
        resp_data = json.loads(resp.data)
        self.assertEqual(len(resp_data['data']), 3)
        for entry in resp_data['data']:
            if entry['id'] == new_model_id:
                self.assertEqual(entry['status'], ModelState.STATUS_INACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_LOCKED)
                self.assertEqual(entry['version'], 1)

        activate_data = dict(action='activate',
                             id=new_model_id)
        resp = self.client.post('/predictors/%s/models' % item['id'],
                                data=json.dumps(activate_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        resp = self.client.get('/predictors/%s/models?with_deactivated=true' % item['id'])
        resp_data = json.loads(resp.data)
        self.assertEqual(len(resp_data['data']), 3)
        for entry in resp_data['data']:
            if entry['id'] == new_model_id:
                self.assertEqual(entry['status'], ModelState.STATUS_ACTIVE)
                self.assertEqual(entry['state'], ModelState.CYCLE_LOCKED)
                self.assertEqual(entry['version'], 1)

    def test_predictor_data(self):
        self.assertEqual(BasePredictor.objects.count(), 0)
        create_data = dict(action_features_schema=[{'label': "id",
                                                    'type': 'label',
                                                    'field_expr': "id"},
                                                   {'label': "age",
                                                    'type': 'label',
                                                    'field_expr': "age"},
                                                   {'label': "skill",
                                                    'type': 'label',
                                                    'field_expr': "skill"},
                                                   {'label': "seniority",
                                                    'type': 'label',
                                                    'field_expr': "seniority"},
                                                   {'label': "fluency",
                                                    'type': 'label',
                                                    'field_expr': "fluency"}],
                           context_features_schema=[{'label': "age",
                                                     'type': 'label',
                                                     'field_expr': "age"},
                                                    {'label': "gender",
                                                     'type': 'label',
                                                     'field_expr': "gender"},
                                                    {'label': "location",
                                                     'type': 'label',
                                                     'field_expr': "location"},
                                                    {'label': "n_subs",
                                                     'type': 'label',
                                                     'field_expr': "n_subs"},
                                                    {'label': "intent",
                                                     'type': 'label',
                                                     'field_expr': "intent"},
                                                    {'label': "seniority",
                                                     'type': 'label',
                                                     'field_expr': "seniority"}],
                           description="Predictor for matching agent against customer.",
                           name="Test new agent matching",
                           metric="CSAT")
        resp = self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(BasePredictor.objects.count(), 1)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])

        action = Action.objects.create(account_id=self.account.id,
                                       name="Got a question? Chat Now!",
                                       tags=[],
                                       channels=[])

        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='good')
        agent_data = {'id': str(action.id),
                      'age': 26,
                      'skill': 'Awesome2',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}

        predictor = BasePredictor.objects.find_one()
        predictor.feedback(customer_data, agent_data, reward=.9)

        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='mediocre')
        agent_data = {'id': str(action.id),
                      'age': 26,
                      'skill': 'Awesome',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}
        predictor.feedback(customer_data, agent_data, reward=.8)

        fetch_data = dict(limit=1, offset=0)
        resp = self.client.get('/predictors/%s/data/json' % predictor.id,
                               data=json.dumps(fetch_data),
                               content_type='application/json')
        resp_data = json.loads(resp.data)
        items = resp_data['list']
        schema = resp_data['schema']
        # First feedback record
        self.assertEqual(len(items), 1)
        item = items[0]
        item_keys = set(item.keys())
        item_keys.remove('action_id')      # Action id not directly part of schema
        self.assertSetEqual(item_keys, set(schema))

        fetch_data = dict(limit=1, offset=1)
        resp = self.client.get('/predictors/%s/data/json' % predictor.id,
                               data=json.dumps(fetch_data),
                               content_type='application/json')
        resp_data = json.loads(resp.data)
        items = resp_data['list']
        schema = resp_data['schema']
        # Second feedback record
        self.assertEqual(len(items), 1)
        item = items[0]
        item_keys = set(item.keys())
        item_keys.remove('action_id')      # Action id not directly part of schema
        self.assertSetEqual(item_keys, set(schema))

    def test_classifier_scoring(self):
        from solariat.db.abstract import KEY_NAME, KEY_TYPE, TYPE_STRING, TYPE_INTEGER
        extra_schema = [{KEY_NAME: 'seniority', KEY_TYPE: TYPE_STRING},
                        {KEY_NAME: 'age', KEY_TYPE: TYPE_INTEGER},
                        {KEY_NAME: 'skill', KEY_TYPE: TYPE_STRING},
                        {KEY_NAME: 'is_transfer', KEY_TYPE: 'boolean'},
                        {KEY_NAME: 'fluency', KEY_TYPE: TYPE_STRING}]
        setup_agent_schema(self.user, extra_schema=extra_schema)
        self.assertEqual(BasePredictor.objects.count(), 0)
        create_data = dict(action_features_schema=[{'label': "id",
                                                    'type': 'label',
                                                    'field_expr': "id"},
                                                   {'label': "age",
                                                    'type': 'label',
                                                    'field_expr': "age"},
                                                   {'label': "skill",
                                                    'type': 'label',
                                                    'field_expr': "skill"},
                                                   {'label': "seniority",
                                                    'type': 'label',
                                                    'field_expr': "seniority"},
                                                   {'label': "fluency",
                                                    'type': 'label',
                                                    'field_expr': "fluency"}],
                           context_features_schema=[{'label': "age",
                                                     'type': 'label',
                                                     'field_expr': "age"},
                                                    {'label': "gender",
                                                     'type': 'label',
                                                     'field_expr': "gender"},
                                                    {'label': "location",
                                                     'type': 'label',
                                                     'field_expr': "location"},
                                                    {'label': "n_subs",
                                                     'type': 'label',
                                                     'field_expr': "n_subs"},
                                                    {'label': "intent",
                                                     'type': 'label',
                                                     'field_expr': "intent"},
                                                    {'label': "seniority",
                                                     'type': 'label',
                                                     'field_expr': "seniority"}],
                           description="Predictor for matching agent against customer.",
                           action_id_expression="id",
                           reward_type='Boolean',
                           name="Test new agent matching",
                           metric="is_transfer")
        resp = self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(BasePredictor.objects.count(), 1)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        AgentProfile = self.user.account.get_agent_profile_class()

        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='good')
        id1 = '3001'
        agent_data = {'age': 26,
                      'id': id1,
                      'skill': 'Awesome2',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}
        AgentProfile.objects.create(**agent_data)

        predictor = BasePredictor.objects.find_one()
        predictor.action_type = TYPE_AGENTS
        predictor.save()
        predictor.feedback(customer_data, agent_data, reward=True)
        predictor.feedback(customer_data, agent_data, reward=False)
        predictor.feedback(customer_data, agent_data, reward=False)

        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='mediocre')
        id2 = '3002'
        agent_data = {'age': 26,
                      'id': id2,
                      'skill': 'Awesome',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}
        AgentProfile.objects.create(**agent_data)

        predictor.feedback(customer_data, agent_data, reward=False)
        predictor.feedback(customer_data, agent_data, reward=True)

        from copy import deepcopy
        full_data = deepcopy(customer_data)
        full_data.update(agent_data)
        full_data[predictor.metric] = False
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

            predictor.train_on_feedback_batch(context_list,
                                              action_list,
                                              reward_list,
                                              model=model,
                                              insert_feedback=False)
            # model.version += 1
            model.state.status = model.state.STATUS_ACTIVE
            model.save()
            predictor.save_model(model)

        resp = self.client.get('/predictors/%s/search' % predictor.id,
                               data=json.dumps(dict(context_row=full_data)),
                               content_type='application/json')
        resp_data = json.loads(resp.data)
        items = resp_data['considered_agents']
        action_schema = resp_data['action_schema']
        # First feedback record
        self.assertEqual(len(items), 2)
        self.assertEqual(len(action_schema), len(predictor.action_features_schema))

        # Test scoring with global model on unknown agent and similar on local model. Expect same results.
        current_global_model = predictor.models[0]
        new_local_model = current_global_model.clone()
        new_local_model.model_type = 'DISJOINT'
        new_local_model.save()
        predictor.add_model(new_local_model)
        predictor.save()
        predictor.train_on_feedback_batch(context_list,
                                          action_list,
                                          reward_list,
                                          model=new_local_model,
                                          insert_feedback=False)
        # model.version += 1
        predictor.save_model(new_local_model)
        global_score1 = predictor.score([dict(action_id=id1)],
                                        customer_data,
                                        model=current_global_model)[0][2]
        local_score1 = predictor.score([dict(action_id=id1)],
                                       customer_data,
                                       model=new_local_model)[0][2]
        # Since we have data on action id, we should have some scores. Since we have more than one action,
        # global model should be different than local model
        self.assertTrue(global_score1 != local_score1)
        self.assertTrue(global_score1 != 0.5 != local_score1)

        global_score = predictor.score([dict(action_id='new_action_id')], customer_data,
                                       model=current_global_model)[0][2]
        local_score = predictor.score([dict(action_id='new_action_id')], customer_data,
                                      model=new_local_model)[0][2]
        # Since we don't have data for this action id, both calls should use the global model
        # and because context is similar to the one we have training data on, should be different than default 0.5
        self.assertEqual(global_score, local_score)
        self.assertTrue(local_score != 0.5)

        # lets make sure that yes individual disjoint model
        # is stored as a seperate record in LocalModel collection
        # and PredictorModel has right mappings to these records in place
        self.assertTrue(isinstance(new_local_model.clf_map[GLOBAL_KEY], ObjectId))
        self.assertTrue(isinstance(new_local_model.clf_map[str(id1)], ObjectId))
        self.assertTrue(isinstance(new_local_model.clf_map[str(id2)], ObjectId))
        self.assertTrue(isinstance(new_local_model.clf.get_local_model(GLOBAL_KEY), LocalModel))
        self.assertTrue(isinstance(new_local_model.clf.get_local_model(str(id1)), LocalModel))
        self.assertTrue(isinstance(new_local_model.clf.get_local_model(str(id2)), LocalModel))
        self.assertEqual(LocalModel.objects.count(predictor_model=new_local_model), 3)

        # lets check that after deletin of PredictorModel
        # LocalModels are deleted too
        new_local_model.delete()
        self.assertEqual(LocalModel.objects.count(predictor_model=new_local_model), 0)

    def test_regressor_scoring(self):
        from solariat.db.abstract import KEY_NAME, KEY_TYPE, TYPE_STRING, TYPE_INTEGER
        extra_schema = [{KEY_NAME: 'seniority', KEY_TYPE: TYPE_STRING},
                        {KEY_NAME: 'age', KEY_TYPE: TYPE_INTEGER},
                        {KEY_NAME: 'skill', KEY_TYPE: TYPE_STRING},
                        {KEY_NAME: 'fluency', KEY_TYPE: TYPE_STRING}]
        setup_agent_schema(self.user, extra_schema=extra_schema)
        self.assertEqual(BasePredictor.objects.count(), 0)
        create_data = dict(action_features_schema=[{'label': "id",
                                                    'type': 'label',
                                                    'field_expr': "id"},
                                                   {'label': "age",
                                                    'type': 'label',
                                                    'field_expr': "age"},
                                                   {'label': "skill",
                                                    'type': 'label',
                                                    'field_expr': "skill"},
                                                   {'label': "seniority",
                                                    'type': 'label',
                                                    'field_expr': "seniority"},
                                                   {'label': "fluency",
                                                    'type': 'label',
                                                    'field_expr': "fluency"}],
                           context_features_schema=[{'label': "age",
                                                     'type': 'label',
                                                     'field_expr': "age"},
                                                    {'label': "gender",
                                                     'type': 'label',
                                                     'field_expr': "gender"},
                                                    {'label': "location",
                                                     'type': 'label',
                                                     'field_expr': "location"},
                                                    {'label': "n_subs",
                                                     'type': 'label',
                                                     'field_expr': "n_subs"},
                                                    {'label': "intent",
                                                     'type': 'label',
                                                     'field_expr': "intent"},
                                                    {'label': "seniority",
                                                     'type': 'label',
                                                     'field_expr': "seniority"}],
                           description="Predictor for matching agent against customer.",
                           action_id_expression="id",
                           name="Test new agent matching",
                           metric="CSAT")
        resp = self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(BasePredictor.objects.count(), 1)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        AgentProfile = self.user.account.get_agent_profile_class()

        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='good')
        id1 = '3001'
        agent_data = {'age': 26,
                      'id': id1,
                      'skill': 'Awesome2',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}
        AgentProfile.objects.create(**agent_data)

        predictor = BasePredictor.objects.find_one()
        predictor.action_type = TYPE_AGENTS
        predictor.save()
        predictor.feedback(customer_data, agent_data, reward=.9)

        customer_data = dict(age=30,
                             location='Nepal',
                             gender='M',
                             intent=['buy a house'],
                             n_subs=10,
                             seniority='mediocre')
        id2 = '3002'
        agent_data = {'age': 26,
                      'id': id2,
                      'skill': 'Awesome',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}
        AgentProfile.objects.create(**agent_data)

        predictor.feedback(customer_data, agent_data, reward=.8)

        from copy import deepcopy
        full_data = deepcopy(customer_data)
        full_data.update(agent_data)
        full_data[predictor.metric] = .8
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

            predictor.train_on_feedback_batch(context_list,
                                              action_list,
                                              reward_list,
                                              model=model)
            # model.version += 1
            model.state.status = model.state.STATUS_ACTIVE
            model.save()
            predictor.save_model(model)

        resp = self.client.get('/predictors/%s/search' % predictor.id,
                               data=json.dumps(dict(context_row=full_data)),
                               content_type='application/json')
        resp_data = json.loads(resp.data)
        items = resp_data['considered_agents']
        action_schema = resp_data['action_schema']
        # First feedback record
        self.assertEqual(len(items), 2)
        self.assertEqual(len(action_schema), len(predictor.action_features_schema))

        # Test scoring with global model on unknown agent and similar on local model. Expect same results.
        current_global_model = predictor.models[0]
        new_local_model = current_global_model.clone()
        new_local_model.model_type = 'DISJOINT'
        new_local_model.save()
        predictor.add_model(new_local_model)
        predictor.save()
        predictor.train_on_feedback_batch(context_list,
                                          action_list,
                                          reward_list,
                                          model=new_local_model)
        # model.version += 1
        predictor.save_model(new_local_model)
        global_score1 = predictor.score([dict(action_id=id1)], customer_data,
                                              model=current_global_model)[0][2]
        local_score1 = predictor.score([dict(action_id=id1)], customer_data,
                                             model=new_local_model)[0][2]
        # Since we have data on action id, we should have some scores. Since we have more than one action,
        # global model should be different than local model
        self.assertTrue(global_score1 != local_score1)
        self.assertTrue(global_score1 != 0.5 != local_score1)


        global_score = predictor.score([dict(action_id='new_action_id')], customer_data,
                                       model=current_global_model)[0][2]
        local_score = predictor.score([dict(action_id='new_action_id')], customer_data,
                                      model=new_local_model)[0][2]
        # Since we don't have data for this action id, both calls should use the global model
        # and because context is similar to the one we have training data on, should be different than default 0.5
        self.assertEqual(global_score, local_score)
        self.assertTrue(local_score != 0.5)

        # lets make sure that yes individual disjoint model
        # is stored as a seperate record in LocalModel collection
        # and PredictorModel has right mappings to these records in place
        self.assertTrue(isinstance(new_local_model.clf_map[GLOBAL_KEY], ObjectId))
        self.assertTrue(isinstance(new_local_model.clf_map[str(id1)], ObjectId))
        self.assertTrue(isinstance(new_local_model.clf_map[str(id2)], ObjectId))
        self.assertTrue(isinstance(new_local_model.clf.get_local_model(GLOBAL_KEY), LocalModel))
        self.assertTrue(isinstance(new_local_model.clf.get_local_model(str(id1)), LocalModel))
        self.assertTrue(isinstance(new_local_model.clf.get_local_model(str(id2)), LocalModel))
        self.assertEqual(LocalModel.objects.count(predictor_model=new_local_model), 3)

        # lets check that after deletin of PredictorModel
        # LocalModels are deleted too
        new_local_model.delete()
        self.assertEqual(LocalModel.objects.count(predictor_model=new_local_model), 0)


    def test_expression_context(self):
        self.assertEqual(BasePredictor.objects.count(), 0)
        self.assertEqual(CompositePredictor.objects.count(), 0)
        dataset = self.load_dataset()
        create_data = {"name": "TestNewAgentMatching1",
                       "dataset": str(dataset.id),
                       "metric": "CUSTOMER_ACW_DURATION",
                       "action_id_expression": "EMPLOYEE_ID",
                       "action_features_schema": [{"label": "res_role", "type": "label", "field_expr": "RESOURCE_ROLE"},
                                                  {"label": "vq", "type": "label", "field_expr": "VIRTUAL_QUEUE"},
                                                  {"label": "sid", "type": "label", "field_expr": "SKILLID"},
                                                  {"label": "w_id", "type": "expression", "field_expr": "int(EMPLOYEE_ID) / 20.0"}],
                       "context_features_schema": [
                           {"label": "itype", "type": "label", "field_expr": "INTERACTION_TYPE"},
                           {"label": "c_hold", "type": "label", "field_expr": "CUSTOMER_HOLD_DURATION"}],
                       "sync_status": "IN_SYNC",
                       "from_dt": 1461135600,
                       "to_dt": 1468652400,
                       "model_type": "GLOBAL"}

        self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        create_data['name'] = "TestNewAgentMatching2"
        self.client.post('/predictors/json', data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(BasePredictor.objects.count(), 2)
        self.assertEqual(CompositePredictor.objects.count(), 0)
        p_ids = [str(p.id) for p in BasePredictor.objects()]
        p_names = [str(p.name) for p in BasePredictor.objects()]

        composite_predictor_data = {'predictors_list': p_ids,
                                    'raw_expression': "%s + %s" % (p_names[0].replace(' ', ''),
                                                                        p_names[1].replace(' ', '')),
                                    'predictor_type': BasePredictor.TYPE_COMPOSITE,
                                    'name': 'The Composite Predictor'}
        resp_data = self.client.post('/predictors/json',
                                     data=json.dumps(composite_predictor_data),
                                     content_type='application/json',
                                     base_url='https://localhost')
        resp_data = json.loads(resp_data.data)
        predictor_id = resp_data['obj']['id']
        self.assertEqual(BasePredictor.objects.count(), 3)
        self.assertEqual(CompositePredictor.objects.count(), 1)
        for predictor in BasePredictor.objects():

            predictor.dataset = dataset.id
            predictor.save()

            expression_context = predictor.to_dict()['expression_context']
            self.assertTrue('functions' in expression_context)
            self.assertTrue(expression_context['functions'])
            self.assertTrue('context' in expression_context)
            self.assertTrue(expression_context['context'])

        composite_predictor = CompositePredictor.objects()[0]
        expression_context = composite_predictor.to_dict()['expression_context']

        self.assertTrue('functions' in expression_context)
        self.assertTrue('context' in expression_context)

        for predictor in BasePredictor.objects():
            if predictor.id == composite_predictor.id:
                continue
            predictor.dataset = dataset.id
            predictor.save()
            self.assertTrue(predictor.name in composite_predictor.to_dict()['predictor_names'])

    def test_feature_importance(self):
        from datetime import datetime, timedelta
        from solariat_bottle.db.predictors.factory import CONFIG
        from solariat_bottle.db.predictors.factory import get_or_create
        KEY_TRANSFER_RATE = 'Test Transfer Rate Predictor'
        AGENT_VECTOR = []
        CUSTOMER_VECTOR = [
                    {
                        'label': 'CALLTYPE',
                        'type': 'label',
                        'field_expr': 'CALLTYPE',
                    },
                    {
                        'label': 'PROD',
                        'type': 'label',
                        'field_expr': 'PROD',
                    },
                    {
                        'label': 'CPRODUCTTYPE',
                        'type': 'label',
                        'field_expr': 'CPRODUCTTYPE',
                    },
                    {
                        'label': 'SIVRREASONCODE1',
                        'type': 'label',
                        'field_expr': 'SIVRREASONCODE1',
                    },
                ]
        TRANSFER_RATE_CONFIGURATION = {
            'rewards': [{'display_name': 'TECHNICAL_RESULT_BOOL',
                         'type': 'Boolean',
                         'var_name': 'TECHNICAL_RESULT_BOOL'}],
            'action_model': AGENT_VECTOR,
            'context_model': CUSTOMER_VECTOR
        }
        CONFIG[KEY_TRANSFER_RATE] = TRANSFER_RATE_CONFIGURATION

        import os
        import solariat_bottle.tests as tests
        from solariat_bottle.db.schema_based import KEY_CREATED_AT
        from solariat_bottle.schema_data_loaders.csv import CsvDataLoader
        test_frame_file = os.path.join(os.path.dirname(tests.__file__), 'data', 'test_frame.csv')
        predictor = get_or_create(KEY_TRANSFER_RATE, self.user.account.id,
                                  state=ModelState(status=ModelState.STATUS_ACTIVE,
                                                   state=ModelState.CYCLE_LOCKED))
        predictor.reward_type = 'Boolean'
        predictor.action_id_expression = 'employeeId'
        predictor.save()

        with open(test_frame_file) as csv_file:
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            dataset = self.user.account.datasets.add_dataset(self.user,
                                                             'Test Transfer Rate Dataset',
                                                             data_loader)

            for entry in dataset.schema:
                if entry['name'] == 'CREATED_AT':
                    entry[KEY_CREATED_AT] = True
            dataset.save()
            dataset.apply_sync()
            dataset.accept_sync()
        predictor.dataset = dataset.id
        predictor.action_type = 'agents'
        predictor.save()
        dataset.reload()
        dset_distribution = dataset.data_distribution()
        if not dset_distribution:
            dataset.refresh_distribution_counts()
            dset_distribution = dataset.data_distribution()
        from_date, to_date = dset_distribution[0][0], dset_distribution[-1][0]
        from_date = datetime.fromtimestamp(from_date)
        to_date = datetime.fromtimestamp(to_date) + timedelta(hours=23, minutes=59, seconds=59)
        print 'Dataset distribution: %s, %s' % (from_date, to_date)
        predictor.from_dt = from_date
        predictor.to_dt = to_date
        print 'Time range for predictor: %s, %s' % (predictor.from_dt, predictor.to_dt)
        predictor.save()
        model_from_dt = datetime.now() - timedelta(hours=24 * 7)
        model_to_dt = datetime.now()
        model = predictor.make_model(context_features=predictor.context_features_schema,
                                     action_features=predictor.action_features_schema,
                                     display_name='Model_%s-%s' % (model_from_dt, model_to_dt),
                                     model_type='HYBRID',
                                     state=ModelState(status=ModelState.STATUS_INACTIVE,
                                                      state=ModelState.CYCLE_NEW))
        model.model_type = 'HYBRID'
        model.from_dt = model_from_dt
        model.to_dt = model_to_dt
        model.save()
        predictor.add_model(model)
        predictor.save()

        print 'Upserting feedback...'
        predictor.upsert_feedback()
        # predictor_model_retrain_task.async(self.predictor, model=model)
        print 'Retraining model...'
        predictor.retrain(model=model, create_new_model_version=False)
        model.save()
        predictor.save()
        self.assertEqual(LocalModel.objects.count(), 3)
        # NOTE: This may change if we change parameter types or model type of the actual predictor being used
        # If this is the case and we verified the solution, we should update this test case below
        ag1_features = model.clf.get_local_model('T6108889').clf.feature_importances_
        non_zeros_ag1 = [1 if feat > 0.1 else 0 for feat in ag1_features]
        ag2_features = model.clf.get_local_model('T6108889').clf.feature_importances_
        non_zeros_ag2 = [1 if feat > 0.1 else 0 for feat in ag2_features]
        glb_features = model.clf.get_local_model('__GLOBAL__').clf.feature_importances_
        non_zeros_global = [1 if feat > 0.1 else 0 for feat in glb_features]
        self.assertEqual(non_zeros_ag1, [0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0])
        self.assertEqual(non_zeros_ag2, [0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0])
        self.assertEqual(non_zeros_global, [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0])


class PredictorConfigurationPage(UICaseSimple):
    def setUp(self):
        UICaseSimple.setUp(self)
        self.login()
        self.configuration = copy.deepcopy(self.account.account_metadata.predictors_configuration)
        self.endpoint = '/account/predictor-configuration/%s' % self.account.id

    def _assert_current_configuration(self, expected_configuration):
        actual_configuration = self._get(self.endpoint, {})['data']
        expected_configuration = PredictorConfigurationConversion.python_to_json(expected_configuration)
        assert actual_configuration == expected_configuration, pprint(DeepDiff(actual_configuration, expected_configuration))

    def test_get_configuration(self):
        self._assert_current_configuration(self.configuration)

    def test_add_new_predictor_configuration(self):
        new_predictor_configuration = {
                'Brand New Predictor Type': {
                    'action_model': [{
                        'name': 'age',
                        'values': [['UNDERAGED', 18]],
                    }],
                    'context_model': [{
                        'name': 'gender',
                        'values': ['M', 'F'],
                    }],
                    'rewards': [{
                        'display_name': 'CSAT',
                        'type': 'numeric',
                        'max': 'inf',
                        'min': '-inf',
                    }],
                },
        }
        self.configuration.update(new_predictor_configuration)
        self._post(self.endpoint, self.configuration)
        self._assert_current_configuration(self.configuration)

    def test_add_new_predictor_data(self):
        """by default there are action_model, context_model, and rewards.
        """
        self.configuration['Agent Matching']['new_model'] = [
                {
                    'name': 'new_model_id',
                    'desc': 'testing',
                }
        ]
        self._post(self.endpoint, self.configuration)
        self._assert_current_configuration(self.configuration)

    def test_add_new_action_model(self):
        self.configuration['Agent Matching']['action_model'].append({
            'name': 'race',
            'values': ['asian', 'african', 'american', 'europion']
        })
        self._post(self.endpoint, self.configuration)
        self._assert_current_configuration(self.configuration)

    def test_rename_predictor_type(self):
        self.configuration['Agent Matching Renamed'] = self.configuration.pop('Agent Matching')
        self._post(self.endpoint, self.configuration)
        self._assert_current_configuration(self.configuration)

    def test_change_reward_max_min(self):
        self.configuration['Agent Matching']['rewards'][0]['max'] = 'inf'
        self.configuration['Agent Matching']['rewards'][0]['min'] = '-inf'
        self._post(self.endpoint, self.configuration)

        metadata = self.account.account_metadata
        metadata.reload()
        eq_(metadata.predictors_configuration['Agent Matching']['rewards'][0]['max'], inf)
        eq_(metadata.predictors_configuration['Agent Matching']['rewards'][0]['min'], -inf)


class PredictorConfigurationConversionTest:

    def test_json_to_python(self):
        conf_from_ui = {'max': 'inf', 'min': '-inf'}
        converted = PredictorConfigurationConversion.json_to_python(conf_from_ui)
        expected = {'max': inf, 'min': -inf}
        eq_(converted, expected)

    def test_python_to_json(self):
        conf_from_python = {'max': inf, 'min': -inf}
        converted = PredictorConfigurationConversion.python_to_json(conf_from_python)
        expected = {'max': 'inf', 'min': '-inf'}
        eq_(converted, expected)


