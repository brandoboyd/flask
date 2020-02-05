# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import json
from datetime import timedelta

from solariat.utils.timeslot import format_date
from solariat_bottle.tests.base import UICase


class HotTopicsEndPointCase(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()
        self.post = self._create_db_post('I do not like laptop bag',
                                         demand_matchables=True)

    def make_request(self, params):
        resp = self.client.post(
            '/hot-topics/json',
            data         = json.dumps(params),
            content_type = 'application/json'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'], data)
        self.assertTrue(isinstance(data['list'], list))

        return data['list']

    def test_nodes(self):
        def check_endpoint(params):
            results = self.make_request(params)
            self.assertEqual(len(results), 1)
            topic_set = set(x['topic'] for x in results)
            self.assertEqual(topic_set, set(['bag']))

        params = {
            'channel_id' : self.channel_id,
            'from'       : format_date(self.post.created),
            'level'      : 'month',
            #'intentions' : []  # no explicit value implies ALL_INTENTION
        }
        check_endpoint(params)
        params['parent_topic'] = None
        check_endpoint(params)
        params['agents'] = []
        check_endpoint(params)

        params['level'] = 'day'
        params['from']  = format_date(self.post.created - timedelta(days=3))
        params['to']    = format_date(self.post.created + timedelta(days=3))
        check_endpoint(params)

    def test_leaves(self):
        params = {
            'channel_id'   : self.channel_id,
            'from'         : format_date(self.post.created),
            'level'        : 'day',
            'parent_topic' : 'bag',
            'intentions'   : []  # empty-list implies ALL_INTENTION
        }
        results = self.make_request(params)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['topic'], 'laptop bag')

    def test_matching_intentions(self):
        params = {
            'channel_id'   : self.channel_id,
            'from'         : format_date(self.post.created),
            'level'        : 'day',
            'parent_topic' : 'bag',
            'intentions'   : ['problem', 'asks']
        }
        results = self.make_request(params)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['topic'], 'laptop bag')

    def test_nonmatching_intentions(self):
        params = {
            'channel_id'   : self.channel_id,
            'from'         : format_date(self.post.created),
            'level'        : 'day',
            'parent_topic' : 'bag',
            'intentions'   : ['apology', 'gratitude'],
            'plot_type'    : 'sentiment',
        }
        results = self.make_request(params)

        self.assertFalse(results)

    def test_matching_sentiments(self):
        params = {
            'channel_id'   : self.channel_id,
            'from'         : format_date(self.post.created),
            'level'        : 'day',
            'parent_topic' : 'bag',
            'sentiments'   : ['negative']
        }
        results = self.make_request(params)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['topic'], 'laptop bag')

    def test_nonmatching_sentiments(self):
        params = {
            'channel_id'   : self.channel_id,
            'from'         : format_date(self.post.created),
            'level'        : 'day',
            'parent_topic' : 'bag',
            'sentiments'   : ['positive', 'neutral'],
            'plot_type'    : 'sentiment',
        }
        results = self.make_request(params)

        self.assertFalse(results)

    def test_matching_language(self):
        params = {
            'channel_id'   : self.channel_id,
            'from'         : format_date(self.post.created),
            'level'        : 'day',
            'parent_topic' : 'bag',
            'languages'    : ['English']
        }
        results = self.make_request(params)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['topic'], 'laptop bag')

        params['languages'] = ['Spanish']
        results = self.make_request(params)

        self.assertFalse(results)

    def test_topic_cloud(self):
        self._create_db_post(
            'I do not like laptop bag',
            demand_matchables=True)
        self._create_db_post(
            'I do not like laptop bag',
            demand_matchables=True,
            _created=self.post.created_at - timedelta(days=1, minutes=1))
        params = {
            'channel_id'   : self.channel_id,
            'from'         : format_date(self.post.created_at),
            'level'        : 'day',
            'parent_topic' : None,
            'cloud_type'   : 'delta'
        }
        results = self.make_request(params)

        self.assertEqual(results, [
            {"topic": "bag", "topic_count": 0, "term_count": 1}])

        params['parent_topic'] = 'bag'
        results = self.make_request(params)
        self.assertEqual(results, [
            {"topic": "laptop bag", "topic_count": 1, "term_count": 1}])

        params['cloud_type'] = 'percent'
        results = self.make_request(params)
        self.assertEqual(results, [
            {"topic": "laptop bag", "topic_count": 100.0, "term_count": 100.0}])
