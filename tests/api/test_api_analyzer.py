import json

from solariat_bottle.tests.api.test_api_classifiers import APIClassifiersCase
from solariat_bottle.app import get_api_url
from solariat_bottle.db.classifiers import TYPE_CONTENT_BASIC


class APIAnalyzerCase(APIClassifiersCase):

    def test_basic(self):
        """ testing that endpoint basically works and
        returns correct number of utterances
        """
        sample1 = "iPod headphones are so crap. Can anyone recommend me some good headphones?"
        token = self.get_token()
        data = {
            'samples': [sample1],
            'token': token
        }
        self._create_classifier(token, "ClassifierOne", TYPE_CONTENT_BASIC)

        resp = self.client.post(get_api_url('analyzer/submit'),
                                data=json.dumps(data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp_data['list'][0]['utterances']), 2)
        self.assertTrue('latency' in resp_data)
