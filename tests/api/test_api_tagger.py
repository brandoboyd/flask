import json

from solariat_bottle.tests.base import RestCase
from solariat_bottle.app import get_api_url


class APITaggerCase(RestCase):

    def test_basic(self):
        """
        testing tagger endpoint using two simple samples
        """
        sample1 = 'I need good headphones.'
        sample2 = 'Ipod headphones are so crappy.'
        sample1_tags = [[u'i', u'PRP'], [u'need', u'VBP'], [u'good', u'JJ'], [u'headphones', u'NNS'], [u'.', u'.']]
        sample2_tags = [[u'ipod', u'NN'], [u'headphones', u'NNS'], [u'are',u'VBP'], [u'so', u'RB'], [u'crappy', u'JJ'],
                        [u'.', u'.']]
        token = self.get_token()
        data  = {
            'samples': [sample1, sample2],
            'token': token
        }
        resp = self.client.post(get_api_url('tagger/submit'),
                                data=json.dumps(data),
                                content_type='application/json',
                                base_url='https://localhost')
        resp_data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp_data["list"][0], sample1_tags)
        self.assertEqual(resp_data["list"][1], sample2_tags)
        self.assertTrue('latency' in resp_data)

