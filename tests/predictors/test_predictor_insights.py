#!/usr/bin/env python2.7

import json
import unittest
from datetime import datetime, timedelta
from solariat_bottle.configurable_apps import CONFIGURABLE_APPS, APP_PREDICTORS

from solariat.utils.timeslot import now, datetime_to_timestamp
from solariat_bottle.tests.base import UICase
from solariat_bottle.db.next_best_action.actions import Action
from solariat_bottle.db.channel.base import SmartTagChannel
from solariat_bottle.db.insights_analysis import InsightsAnalysis

from solariat_bottle.tests.predictors.test_dataset import Dataset, CSV_SHORT_FILEPATH, CsvDataLoader
from solariat_bottle.db.schema_based import KEY_IS_ID, KEY_NAME

from solariat_bottle.jobs.manager import jobs_config

class InsightsTestCase(UICase):
    def setUp(self):
        UICase.setUp(self)
        self.login()
        self.user.account.update(available_apps=CONFIGURABLE_APPS, selected_app=APP_PREDICTORS)
        self.smart_tag = SmartTagChannel.objects.create_by_user(
            self.user,
            title="test_smart_tag",
            parent_channel=self.channel.id,
            account=self.channel.account)
        self.jobs_origin_transport = jobs_config.transport
        self.setup_jobs_transport('serial')
        self._setUp()

    def _setUp(self):
        self._load_dataset()
        self._load_prr_analysis_data()
        self._load_customer_profile()

    def tearDown(self):
        self.setup_jobs_transport(self.jobs_origin_transport)
        return UICase.tearDown(self)

    def add_daterange(self, filters, timeformat):
        current = datetime.now()
        three_montsh_ago = current - timedelta(days=90)
        current = current + timedelta(days=20)
        filters['from'] = three_montsh_ago.strftime(timeformat)
        filters['to'] = current.strftime(timeformat)
        filters['timerange'] = [datetime_to_timestamp(three_montsh_ago),
                                datetime_to_timestamp(current)]

    def _load_dataset(self):
        name = 'TestApplySchema_' + str(datetime.now())
        with open(CSV_SHORT_FILEPATH) as csv_file:
            raw_items = len([1 for _ in csv_file]) - 1  # minus head

        with open(CSV_SHORT_FILEPATH) as csv_file:
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
        self.dataset = dataset

    def _load_prr_analysis_data(self):
        from solariat_bottle.db.predictors.base_predictor import BasePredictor
        predictor_data = {"name": "New Predictor" + str(datetime.now()),
                          "dataset": str(self.dataset.id),
                          "metric": "MEDIATION_DURATION",
                          "action_id_expression": "EMPLOYEE_ID",
                          "action_features_schema": [
                                  {"label": "res_role", "type": "label", "field_expr": "RESOURCE_ROLE"}
                          ],
                          "context_features_schema": [
                              {"label": "c_hold", "type": "label", "field_expr": "CUSTOMER_HOLD_DURATION"}
                          ],
                          "sync_status": "IN_SYNC",
                          "from_dt": 1461135600,
                          "to_dt": 1468652400,
                          "model_type": "GLOBAL"}

        resp = self.client.post('/predictors/json', data=json.dumps(predictor_data), content_type='application/json')
        resp_data = json.loads(resp.data)
        self.predictor = BasePredictor.objects.get(resp_data['obj']['id'])
        self._post('/predictors/command/generate_data/%s' % self.predictor.id,
                   dict(from_dt=predictor_data['from_dt'], to_dt=predictor_data['to_dt']),
                   expected_code=200)

        self.prr_req_data = {'filters': {'action_vector': {},
                                         'context_vector': {},
                                         'predictor_id': str(self.predictor.id)
                                         },
                             'analyzed_metric': self.predictor.metric,
                             'metric_type': self.predictor.reward_type,  # TODO: rename to metric_type
                             'application': 'Predictive Matching',
                             'title': 'TEST_PREDICTIVE_ANALYSIS'
                             }
        self.add_daterange(self.prr_req_data['filters'], timeformat='%m/%d/%Y')

    def _load_customer_profile(self):
        from solariat_bottle.utils.predictor_events import translate_column
        manager = getattr(self.user.account, 'customer_profile')
        with open(CSV_SHORT_FILEPATH) as csv_file:
            data_loader = CsvDataLoader(csv_file, sep=CsvDataLoader.TAB)
            profile = manager.create(self.user, data_loader)

        id_col_name = translate_column('INTERACTION_ID')
        for col in profile.discovered_schema:
            if col[KEY_NAME] == id_col_name:
                col[KEY_IS_ID] = True

        self._post('/customer_profile/update_schema',
                   {'schema': profile.discovered_schema},
                   expected_code=201)

        data = self._get('/customer_profile/get', {})
        self.assertEqual(data['data']['schema'], profile.discovered_schema)

        profile.reload()
        profile.apply_sync()
        profile.accept_sync()
        data = profile.get_data()[0]
        self.customer_profile = data

    def test_predictive_analytics(self):
        self.client.get('/account_app/switch/Predictive Matching')
        action = Action.objects.create(account_id=self.account.id, name="Got a question? Chat Now!", tags=[], channels=[])
        agent_data = {'action_id': action.id,
                      'id': action.id,
                      'age': 26,
                      'skill': 'Awesome',
                      'seniority': 'Old',
                      'fluency': 'SoSo'}

        self.predictor.train_on_feedback_batch([self.customer_profile.to_dict()],
                                               [agent_data],
                                               [.9],
                                               model=self.predictor.models[0])

        regr_analysis_data = self.prr_req_data.copy()
        regr_analysis_data.update({"metric_values": self.predictor.metric_values_range,
                                   "metric_values_range": self.predictor.metric_values_range,
                                   "analysis_type": "regression"})
        classification_analysis_data = self.prr_req_data.copy()
        classification_analysis_data.update({"metric_values": ['10', '100'],
                                             "analysis_type": "classification",
                                             "metric_values_range": [1, 101]})

        res_regr = self.client.post('/analyzers',
                                    data=json.dumps(regr_analysis_data),
                                    content_type='application/json')
        res_regr = json.loads(res_regr.data)
        self.assertTrue('timerange_results' in res_regr['item'])
        self.assertTrue('results' in res_regr['item'])

        res_class = self.client.post('/analyzers',
                                     data=json.dumps(classification_analysis_data),
                                     content_type='application/json')
        res_class = json.loads(res_class.data)
        self.assertTrue('timerange_results' in res_class['item'])
        self.assertTrue('results' in res_class['item'])

        res = self.client.get('/analyzers')
        data = json.loads(res.data)
        self.assertEqual(len(data), 2)  # 2 Insight Analysis should be created
        self.assertTrue(all([d['timerange_results'] for d in data['list'] if d['progress'] != -2]))

        for d in data['list']:
            self.client.delete('/analyzers/' + d['id'])

    def test_insights_crud(self):
        # No insights to begin with
        self.client.get('/account_app/switch/Predictive Matching')
        resp = self.client.get('/analyzers')
        data = json.loads(resp.data)
        self.assertTrue('list' in data and len(data['list']) == 0)

        classification_analysis_data = self.prr_req_data.copy()
        classification_analysis_data.update({"metric_values": ['10', '100'],
                                             "analysis_type": "classification",
                                             "metric_values_range": [1, 101]})

        resp = self.client.post('/analyzers',
                                data=json.dumps(classification_analysis_data),
                                content_type='application/json')
        data = json.loads(resp.data)
        self.assertTrue('item' in data and data['item'])
        insight_id = data['item']['id']

        # List them all again
        resp = self.client.get('/analyzers')
        data = json.loads(resp.data)
        self.assertTrue('list' in data and len(data['list']) == 1)

        # Get specific instance
        resp = self.client.get('/analyzers/' + insight_id)
        data = json.loads(resp.data)
        self.assertTrue('item' in data and len(data['item']))
        self.assertTrue('account_id' in data['item'])
        self.assertTrue('filters' in data['item'])
        self.assertTrue('analyzed_metric' in data['item'])
        self.assertTrue('metric_type' in data['item'])
        self.assertTrue('metric_values' in data['item'])
        self.assertTrue('metric_values_range' in data['item'])
        self.assertTrue('status' in data['item'])
        self.assertTrue('results' in data['item'])

        results = data['item']['results']
        # for key, entry in results.iteritems():
            # self.assertTrue('attribute' in entry and type(entry['attribute']) in (str, unicode),
            #                 "actually got " + str(type(entry['attribute'])))
            # self.assertTrue('discriminative_weight' in entry and isinstance(entry['discriminative_weight'], int))
            # self.assertTrue('values' in entry and isinstance(entry['values'], list))
            # self.assertTrue('crosstab_results' in entry and isinstance(entry['crosstab_results'], dict))

    def test_insights_commands(self):
        # Create one now
        self.client.get('/account_app/switch/Predictive Matching')

        classification_analysis_data = self.prr_req_data.copy()
        classification_analysis_data.update({"metric_values": ['10', '100'],
                                             "analysis_type": "classification",
                                             "metric_values_range": [1, 101]})

        resp = self.client.post('/analyzers',
                                data=json.dumps(classification_analysis_data),
                                content_type='application/json')
        data = json.loads(resp.data)
        self.assertTrue('item' in data and data['item'])
        insight_id = data['item']['id']

        resp = self.client.get('/analyzers/' + insight_id)
        data = json.loads(resp.data)
        self.assertTrue('item' in data and len(data['item']))
        self.assertTrue('status' in data['item'])
        self.assertLessEqual(data['item']['status'], ["queue", 0])

        resp = self.client.post('/analyzers/' + insight_id + '/stop')
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        resp = self.client.get('/analyzers/' + insight_id)
        data = json.loads(resp.data)
        self.assertTrue('item' in data and len(data['item']))
        self.assertTrue('status' in data['item'])
        self.assertLessEqual(data['item']['status'], ["stopped", 0])

        resp = self.client.post('/analyzers/' + insight_id + '/restart')
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        resp = self.client.get('/analyzers/' + insight_id)
        data = json.loads(resp.data)
        self.assertTrue('item' in data and len(data['item']))
        self.assertTrue('status' in data['item'])
        self.assertLessEqual(data['item']['status'], ["queue", 0])

        resp = self.client.delete('/analyzers/' + insight_id)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertEqual(InsightsAnalysis.objects.count(), 0)
