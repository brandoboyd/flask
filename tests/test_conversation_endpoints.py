# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import unittest
import json

from datetime import datetime as dt, timedelta
from ..db.conversation import Conversation
from ..db.conversation_trends import ConversationQualityTrends
from .test_conversation_trends import ConversationQualityTrendsCase


class FetchMixin(object):
    def _fetch(self, url, **kw):
        resp = self.client.post(url, data=json.dumps(kw), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'], data.get('error'))
        self.assertTrue('list' in data)
        return data['list']

class BaseConversationEndpointCase(ConversationQualityTrendsCase, FetchMixin):

    def setUp(self):
        ConversationQualityTrendsCase.setUp(self)   
        now = dt.now()
        self.one_day_before_str = dt.strftime(now-timedelta(days=1), "%Y-%m-%d %H:%M")
        self.one_day_after_str = dt.strftime(now+timedelta(days=1), "%Y-%m-%d %H:%M")


    @unittest.skip('skipping these tests, noone uses ConversationTrends now')
    def test_basically_works(self):
        """
        Lets get a json for one conversation,
        the most simple case.
        """
        now = dt.now()
        self._create_conversation(topic="laptop").close(closing_time=now, quality="win")
        kw = {
            'channel_id': str(self.sc.id),
            'from': self.one_day_before_str,
            'to': self.one_day_after_str,
            'level': 'day', 
            'limit': 10, 
            'offset': 0, 
            'sort_by': 'time',
            'categories': []
        }
        self.login()
        conversations = self._fetch("conversations/json", **kw)
        self.assertTrue(conversations)
        self.assertEqual(len(conversations), 1)

    @unittest.skip('skipping these tests, noone uses ConversationTrends now')
    def test_categories_param(self):
        """
        Pass categories param and get a json.
        """
        now = dt.now()
        self._create_conversation(topic="laptop").close(closing_time=now, quality="win")
        self._create_conversation(topic="ipad").close(closing_time=now, quality="loss")
        self._create_conversation(topic="iphone").close(closing_time=now, quality="unknown")

        self.assertEqual(Conversation.objects().count(), 3)
        self.assertEqual(ConversationQualityTrends.objects.count(), 6)
        
        kw = {
            'channel_id': str(self.sc.id),
            'from': self.one_day_before_str,
            'to': self.one_day_after_str,
            'level': 'day', 
            'limit': 10, 
            'offset': 0, 
            'sort_by': 'time',
            'categories': ['win']
        }
        self.login()
        conversations = self._fetch("conversations/json", **kw)

        self.assertTrue(conversations)
        self.assertEqual(len(conversations), 1)


