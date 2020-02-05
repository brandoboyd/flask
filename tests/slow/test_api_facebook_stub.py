import json
import unittest

from solariat_bottle.app import get_api_url
from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.db.post.facebook import FacebookPost
from solariat_bottle.db.queue_message import QueueMessage
from solariat_bottle.db.conversation import Conversation

from solariat_bottle.tests.base import UICase


class TestFacebookStub(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.account.update(account_type='GSE')
        self.sc = FacebookServiceChannel.objects.create_by_user(self.user, title='Service Channel')
        self.inbound = self.sc.inbound_channel

    def test_post(self):
        self.assertEqual(QueueMessage.objects.count(), 0)
        self.assertEqual(FacebookPost.objects.count(), 0)
        self.assertEqual(Conversation.objects.count(), 0)

        params = dict(content="Test creating root post",
                      channel=str(self.inbound.id),
                      token=self.get_token())
        response = self.client.post(get_api_url('stubs/facebook/create_post'),
                                    data=json.dumps(params),
                                    content_type='application/json',
                                    base_url='https://localhost')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(FacebookPost.objects.count(), 1)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(QueueMessage.objects.count(), 1)

    @unittest.skip("Incorrect post data. Correct data workflow available in test_api_queue.py")
    def test_post_and_comment(self):
        token = self.get_token()
        self.assertEqual(QueueMessage.objects.count(), 0)
        self.assertEqual(FacebookPost.objects.count(), 0)
        self.assertEqual(Conversation.objects.count(), 0)

        params = dict(content="Test creating root post",
                      channel=str(self.inbound.id),
                      token=token)
        response = self.client.post(get_api_url('stubs/facebook/create_post'),
                                    data=json.dumps(params),
                                    content_type='application/json',
                                    base_url='https://localhost')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(FacebookPost.objects.count(), 1)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(QueueMessage.objects.count(), 1)
        created_post = FacebookPost.objects.find_one()

        params = dict(content="Test creating another root post",
                      channel=str(self.inbound.id),
                      parent=str(created_post.native_id),
                      token=token)
        response = self.client.post(get_api_url('stubs/facebook/create_comment'),
                                    data=json.dumps(params),
                                    content_type='application/json',
                                    base_url='https://localhost')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(FacebookPost.objects.count(), 2)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(QueueMessage.objects.count(), 2)
