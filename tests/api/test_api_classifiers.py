import json

from solariat_bottle.settings import get_var
from solariat_bottle.db.account import Account
from solariat_bottle.db.roles import ADMIN
from solariat_bottle.db.classifiers import TYPE_KEYWORD_AUGMENTED, TYPE_CONTENT_BASIC
from solariat_bottle.tests.base import RestCase


class APIClassifiersCase(RestCase):

    def _create_classifier(self, token, name, type, **metadata):
        happy_flow_data = {
            'name': name,
            'token': token,
            'type': type
        }
        happy_flow_data.update(metadata)
        resp = self.client.post('/api/v2.0/classifiers',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        return post_data['item']

    def _list_classifiser(self, token):
        post_data = dict(token=token)
        resp = self.client.get('/api/v2.0/classifiers',
                               data=json.dumps(post_data),
                               content_type='application/json',
                               base_url='https://localhost')
        data = json.loads(resp.data)
        return data['list']

    def test_classifier_resource_management(self):
        new_acc1 = Account.objects.create(name='TestAccount1')
        new_acc2 = Account.objects.create(name='TestAccount2')
        user_1_mail = 'admin1@test_channels.com'
        user_password = 'password'
        user_2_mail = 'admin2@test_channels.com'
        admin_user_1 = self._create_db_user(email=user_1_mail,
                                            password=user_password,
                                            roles=[ADMIN])
        admin_user_2 = self._create_db_user(email=user_2_mail,
                                            password=user_password,
                                            roles=[ADMIN])
        new_acc1.add_perm(admin_user_1)
        new_acc2.add_perm(admin_user_2)

        token = self.get_token(user_1_mail, user_password)
        classifier_one = self._create_classifier(token, "ClassifierOne", TYPE_CONTENT_BASIC)
        classifier_two = self._create_classifier(token, "ClassifierTwo", TYPE_KEYWORD_AUGMENTED,
                                                 keywords=["Test", "Testing"],
                                                 watchwords=["Tester"],
                                                 skip_keywords=["Skip"])

        token = self.get_token(user_2_mail, user_password)
        classifier_three = self._create_classifier(token, "ClassifierThree", TYPE_CONTENT_BASIC)

        # Check listing the classifiers for user2
        classifier_list = self._list_classifiser(token)
        self.assertEqual(len(classifier_list), 1)
        self.assertDictEqual(classifier_list[0], classifier_three)

        # Check listing the classifiser for user1
        token = self.get_token(user_1_mail, user_password)
        classifier_list = self._list_classifiser(token)
        self.assertEqual(len(classifier_list), 2)
        self.assertEqual(set([c['id'] for c in classifier_list]),
                         set([c['id'] for c in [classifier_one, classifier_two]]))

        # Now check fetching a classifier based on id
        resp = self.client.get(classifier_one['uri'].replace(get_var('HOST_DOMAIN'), ''),
                               data=json.dumps({'token': token}),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertDictEqual(data['item'], classifier_one)

        # Now check fetching based on name
        resp = self.client.get('/api/v2.0/classifiers',
                               data=json.dumps({'token': token,
                                                'name': 'ClassifierTwo'}),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data['list']), 1)
        self.assertDictEqual(data['list'][0], classifier_two)

        # Now delete one of the classifiers
        resp = self.client.delete('/api/v2.0/classifiers', #classifier_one['uri'].replace(get_var('HOST_DOMAIN'), ''),
                                  data=json.dumps({'token': token,
                                                   'id': classifier_one['id']}),
                                  content_type='application/json',
                                  base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertDictEqual(data, {"ok": True, "removed_count": 1})

        # Now check fetching the classifier we just removed
        resp = self.client.get(classifier_one['uri'].replace(get_var('HOST_DOMAIN'), ''),
                               data=json.dumps({'token': token}),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 404)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['code'], 34)
        self.assertEqual(data['error'], "The requested resource does not exist in collection 'AuthTextClassifier'")

    def test_classifier_actions_complex(self):
        """
        A complex test that goes through all the actions for two different classifiers.
        """
        token = self.get_token()
        classifier_one = self._create_classifier(token, "ClassifierOne", TYPE_CONTENT_BASIC)
        classifier_two = self._create_classifier(token, "ClassifierTwo", TYPE_KEYWORD_AUGMENTED,
                                                 keywords=['test', 'post'],
                                                 watchwords=['test'],
                                                 skip_keywords=['laptop'])
        classifier1_id = classifier_one['id']
        classifier2_id = classifier_two['id']
        post_data = {'token': token,
                     'samples': [{'text': 'This is a test post.'}, {'text': 'This is a test laptop'}],
                     'classifiers': [classifier1_id, classifier2_id]}

        # Test the predict endpoint with a fresh classifier
        resp = self.client.post('/api/v2.0/classifiers/predict',
                                data=json.dumps(post_data),
                                content_type='application/json',
                                base_url='https://localhost')
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['list']), 4)
        entries = data['list']
        for entry in entries[:-1]:
            # Classifier is brand new, all samples should be 0.5 except last one which is rejected by skip keywords
            self.assertEqual(entry['score'], 0.5)
            self.assertTrue('id' in entry and 'name' in entry)
        self.assertEqual(entries[-1]['score'], 0)

        # Now do a train. First missing the required samples parameter.
        resp = self.client.post('/api/v2.0/classifiers/train',
                                data=json.dumps({'token': token}),
                                content_type='application/json',
                                base_url='https://localhost')
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['code'], 113)
        self.assertEqual(data['error'], "Missing required parameter 'samples'")

        # Now let's add some samples
        samples = [{'text': "This is a test post for testing",
                    'values': [(classifier1_id, 1), (classifier2_id, 1)],},
                   {'text': "This is another test post",
                    'values': [(classifier1_id, 1), (classifier2_id, 1)],},
                   {'text': "This is a laptop",
                    'values': [(classifier1_id, 0), (classifier2_id, 0)],},
                   {'text': "This is another laptop",
                    'values': [(classifier1_id, 0), (classifier2_id, 0)],},]

        resp = self.client.post('/api/v2.0/classifiers/train',
                                data=json.dumps({'token': token,
                                                 'samples': samples}),
                                content_type='application/json',
                                base_url='https://localhost')
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['list']), 2)  # We only have two classifier instances
        self.assertEqual(data['skipped_samples'], 0)
        self.assertEqual(data['errors'], [])
        for entry in data['list']:
            self.assertTrue('latency' in entry and 'id' in entry)


        # Now let's try another prediction on the initial data. Expect scores to change
        post_data = {'token': token,
                     'samples': [{'text': 'This is a test post.'}, {'text': 'This is a test laptop'}],
                     'classifiers': [classifier1_id, classifier2_id]}
        resp = self.client.post('/api/v2.0/classifiers/predict',
                                data=json.dumps(post_data),
                                content_type='application/json',
                                base_url='https://localhost')
        data = json.loads(resp.data)
        after_train_data = data
        self.assertEqual(len(data['list']), 4)
        score_classifier1_post = 0
        score_classifier2_post = 0
        for entry in data['list']:
            # We just gave some positive examples regarding posts, should increase this score
            if entry['text'] == "This is a test post." and entry['id'] == classifier1_id:
                self.assertTrue(entry['score'] > 0.5, "%s > 0.5" % entry['score'])
                score_classifier1_post = entry['score']
            # We just gave some negative examples regarding laptop, should decrease this score
            if entry['text'] == "This is a test laptop" and entry['id'] == classifier1_id:
                self.assertTrue(entry['score'] < 0.5, "%s < 0.5" % entry['score'])
            # Same as first classifier, score should increase for a test post because of positive sample
            if entry['text'] == "This is a test post." and entry['id'] == classifier2_id:
                self.assertTrue(entry['score'] > 0.5, "%s > 0.5" % entry['score'])
                score_classifier2_post = entry['score']
            # For the laptop post we expect still 0, since that should be rejected by rules
            if entry['text'] == "This is a test laptop" and entry['id'] == classifier2_id:
                self.assertTrue(entry['score'] < 0.5, "%s < 0.5" % entry['score'])
        # The score for the second classifier should have increased more with the same samples
        # due to specific keywords / watchwords that were relevant for the sample
        self.assertTrue(score_classifier2_post > score_classifier1_post)

        # Retrain both the classifiers
        resp = self.client.post('/api/v2.0/classifiers/retrain',
                                data=json.dumps({'token': token,
                                                 'classifiers': [classifier1_id, classifier2_id]}),
                                content_type='application/json',
                                base_url='https://localhost')
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['list']), 2)  # We only have two classifier instances
        self.assertEqual(data['skipped_samples'], 0)
        self.assertEqual(data['errors'], [])

        # Now do predict again, check that classifiers still learned stuff
        post_data = {'token': token,
                     'samples': [{'text': 'This is a test post.'}, {'text': 'This is a test laptop'}],
                     'classifiers': [classifier1_id, classifier2_id]}
        resp = self.client.post('/api/v2.0/classifiers/predict',
                                data=json.dumps(post_data),
                                content_type='application/json',
                                base_url='https://localhost')
        data = json.loads(resp.data)
        # After retrain we should get the same result since we chose to retrain incremental
        for entry in data['list']:
            # We just gave some positive examples regarding posts, should increase this score
            if entry['text'] == "This is a test post." and entry['id'] == classifier1_id:
                self.assertTrue(entry['score'] > 0.5, "%s > 0.5" % entry['score'])
            # We just gave some negative examples regarding laptop, should decrease this score
            if entry['text'] == "This is a test laptop" and entry['id'] == classifier1_id:
                self.assertTrue(entry['score'] < 0.5, "%s < 0.5" % entry['score'])
            # Same as first classifier, score should increase for a test post because of positive sample
            if entry['text'] == "This is a test post." and entry['id'] == classifier2_id:
                self.assertTrue(entry['score'] > 0.5, "%s > 0.5" % entry['score'])
            # For the laptop post we expect still 0, since that should be rejected by rules
            if entry['text'] == "This is a test laptop" and entry['id'] == classifier2_id:
                self.assertTrue(entry['score'] < 0.5, "%s < 0.5" % entry['score'])

        # Reset both classifiers now
        resp = self.client.post('/api/v2.0/classifiers/reset/%s' % classifier1_id,
                                data=json.dumps({'token': token}),
                                content_type='application/json',
                                base_url='https://localhost')
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        resp = self.client.post('/api/v2.0/classifiers/reset/%s' % classifier2_id,
                                data=json.dumps({'token': token}),
                                content_type='application/json',
                                base_url='https://localhost')
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        post_data = {'token': token,
                     'samples': [{'text': 'This is a test post.'}, {'text': 'This is a test laptop'}],
                     'classifiers': [classifier1_id, classifier2_id]}
        resp = self.client.post('/api/v2.0/classifiers/predict',
                                data=json.dumps(post_data),
                                content_type='application/json',
                                base_url='https://localhost')
        data = json.loads(resp.data)
        # After reset the check comes back to a clear classifier
        entries = data['list']
        for entry in entries[:-1]:
            # Classifier is brand new, all samples should be 0.5 except last one which is rejected by skip keywords
            self.assertEqual(entry['score'], 0.5)
            self.assertTrue('id' in entry and 'name' in entry)
        self.assertEqual(entries[-1]['score'], 0)
