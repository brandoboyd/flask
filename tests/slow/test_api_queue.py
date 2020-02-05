import json
import logging
import time
import unittest
from datetime import datetime, timedelta

import itertools
from mock import patch, PropertyMock
from solariat_bottle.utils.tracking import lookup_tracked_channels

from solariat.tests.base import LoggerInterceptor

from solariat_bottle.app import get_api_url
from solariat_bottle.api.queue import DEFAULT_LIMIT, DEFAULT_RESERVE_TIME, MAX_LIMIT, MAX_RESERVE_TIME, \
    PostGroup
from solariat_bottle.db.channel.twitter import TwitterServiceChannel, TwitterTestDispatchChannel, \
    EnterpriseTwitterChannel
from solariat_bottle.db.channel.facebook import FacebookServiceChannel, EnterpriseFacebookChannel
from solariat_bottle.db.post.base import Post
from solariat_bottle.db.post.facebook import FacebookPost, FacebookPostManager
from solariat_bottle.db.queue_message import QueueMessage, BrokenQueueMessage
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.conversation import Conversation

from solariat_bottle.tests.base import MainCase, UICase, fake_twitter_url, RestCase


def stop_mock_patch(patch_obj):
    try:
        patch_obj.stop()
    except RuntimeError:
        pass


class ApiQueueTestMixin(object):
    @staticmethod
    def cleanup_db():
        Conversation.objects.coll.remove()
        Post.objects.coll.remove()
        QueueMessage.objects.coll.remove()

    def send_post(self, content):
        data = dict(content=0,
                    serialized_to_json=True,
                    post_object_data=content,
                    channel=0,
                    token=self.api_token)

        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(data),
                                content_type='application/json',
                                base_url='https://localhost')
        return json.loads(resp.data)

    def send_queue_request(self, mode, channel=None, **kwargs):
        channel = channel or self.channel
        data = dict(reserve_time=1,
                    lookup_size=10,
                    mode=mode,
                    channel=str(channel.id),
                    token=self.api_token)
        data.update(kwargs)
        response = self.client.post('/api/v2.0/queue/fetch',
                                    data=json.dumps(data),
                                    content_type='application/json',
                                    base_url='https://localhost')
        return json.loads(response.data)

    def fetch_and_confirm(self, mode, channel=None, **kwargs):
        channel = channel or self.channel
        fetch_response_data = self.send_queue_request(mode, channel, **kwargs)
        callback_params = {'token': self.api_token,
                           'batch_token': fetch_response_data['metadata']['batch_token']}
        response = self.client.post(get_api_url('queue/confirm'),
                                    data=json.dumps(callback_params),
                                    content_type='application/json',
                                    base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        return {'confirmed': data['cleared_count']}


class TestQueueMessage(MainCase):

    def get_post(self):
        return self._create_tweet(content=self.content)
        
    def setUp(self):
        MainCase.setUp(self)
        self.content = '@screen_name I need a laptop'

    def test_push_to_queue(self):
        post1, post2, post3 = self.get_post(), self.get_post(), self.get_post()
        QueueMessage.objects.push(post1, str(self.channel.id))
        QueueMessage.objects.push(post2, str(self.channel.id))
        QueueMessage.objects.push(post3, str(self.channel.id))
        data = ''.join((unicode(qm.post_data) for qm in QueueMessage.objects()))
        self.assertTrue(post1.plaintext_content not in data,
                        msg="non-secure content: %s" % data)

        result = QueueMessage.objects.find(channel_id=str(self.channel.id))
        self.assertEqual(len(result), 3)
        #content is encrypted, but 'laptop' should be in punks
        #self.assertTrue(self.content in result[0].post_data[Post.content.db_field], msg=result[0].post_data)
        self.assertTrue('laptop' in result[0].post_data[Post.punks.db_field])

    def test_select_and_reserve(self):
        posts = [self.get_post() for _ in range(0, 4)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        reserved_deadline = datetime.utcnow() + timedelta(seconds=10)
        reserved_posts, _ = QueueMessage.objects.select_and_reserve(str(self.channel.id), 3, 5)
        self.assertEqual(len(reserved_posts), 3)
        self.assertLess(reserved_posts[0].reserved_until, reserved_deadline)
        self.assertLess(reserved_posts[2].reserved_until, reserved_deadline)

        reserved_posts, _ = QueueMessage.objects.select_and_reserve(str(self.channel.id), 3, 5)
        self.assertEqual(len(reserved_posts), 1)

        time.sleep(10)
        reserved_posts, _ = QueueMessage.objects.select_and_reserve(str(self.channel.id), 4)
        self.assertEqual(len(reserved_posts), 4)

    def test_remove_reserved(self):
        posts = [self.get_post() for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        reserve_time = 3  # Messages will be reserved for one second
        reserved, _ = QueueMessage.objects.select_and_reserve(str(self.channel.id),  3, reserve_time)
        QueueMessage.objects.remove_reserved(reserved[0].batch_token)
        time.sleep(5)
        reserved, duplicates = QueueMessage.objects.select_and_reserve(str(self.channel.id),  5, reserve_time)
        self.assertEqual(duplicates, 0)
        self.assertEqual(len(reserved), 2)

    def test_get_unsafe(self):
        posts = [self.get_post() for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        reserved, _ = QueueMessage.objects.get_unsafe(str(self.channel.id),  5)
        self.assertEqual(len(reserved), 5)
        reserved, _ = QueueMessage.objects.select_and_reserve(str(self.channel.id),  5)
        self.assertEqual(len(reserved), 0)


class TestQueueEndpoint(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()
        self.content = '@screen_name I need a laptop'
        self.get_post = lambda: self._create_db_post(content=self.content)
        self.channel = TwitterServiceChannel.objects.create_by_user(self.user,
                                                                    account=self.account,
                                                                    title='QUEUE TEST')

    def check_access_not_allowed(self, params, url):
        response = self.client.get(get_api_url(url),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(data['code'], 12)

    def test_invalid_id(self):
        params = {'channel': "invalid_id",
                  'limit': 4,
                  'reserve_time': 30,
                  'token': self.auth_token}

        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'No channel found with id=invalid_id')

    def test_pull_message_from_queue(self):
        posts = [self.get_post() for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        params = {'channel': str(self.channel.id), 'limit': 4, 'reserve_time': 30}
        self.check_access_not_allowed(params, 'queue/fetch')

        token = self.auth_token
        params['token'] = token
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 4)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])

        callback_params = {'token': token,
                           'batch_token': data['metadata']['batch_token']}
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
             
    def test_pull_horizon_settings(self):
        horizon = 200   # Assume 100s before posts don't matter
        self.channel.history_time_period = horizon
        self.channel.save()

        posts = [self.get_post() for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        # Enforce that 3 of the queue messages are older
        older_than_horizon = datetime.utcnow() - timedelta(seconds=horizon + 1)
        for q_m in QueueMessage.objects()[:][:3]:
            q_m.created_at = older_than_horizon
            q_m.save()

        params = {'channel': str(self.channel.id), 'limit': 4, 'reserve_time': 30, 'token': self.auth_token}

        token = self.auth_token
        params['token'] = token
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 2)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])
        self.assertEqual(QueueMessage.objects.count(), 2)

        callback_params = {'token': token,
                           'batch_token': data['metadata']['batch_token']}
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        self.assertEqual(QueueMessage.objects.count(), 0)

    def test_pull_facebook_messages(self):
        channel = FacebookServiceChannel.objects.create_by_user(self.user, title="Facebook Service Channel")
        wrapped = dict(type="status", source_id="fakeid", source_type="page", page_id="12345")
        fb = dict(_wrapped_data=wrapped, facebook_post_id="12345_54321")
        posts = []
        for _ in range(0, 5):
            fb['facebook_post_id'] = '12345_5432%s' % _
            posts.append(self._create_db_post(content=self.content,
                                      facebook=fb,
                                      channel=channel))
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        params = {'channel': str(self.channel.id),
                  'limit': 4,
                  'reserve_time': 30,
                  'token': self.auth_token}

        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 4)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])

    def test_pull_twitter_messages(self):
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title="Twitter Service Channel")
        posts = [self._create_db_post(content=self.content,
                                      channel=channel) for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        params = {'channel': str(self.channel.id),
                  'limit': 4,
                  'reserve_time': 30,
                  'token': self.auth_token}

        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 4)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])

    def test_pull_twitter_public_stream_messages(self):
        from solariat_bottle.daemons.twitter.stream import test_utils
        from solariat_bottle.daemons.helpers import twitter_status_to_post_dict

        channel = TwitterServiceChannel.objects.create_by_user(self.user, title="Twitter Service Channel")
        n = 5

        def gen_posts(channels):
            for post in test_utils.filestream(sample_count=n):
                post_data = twitter_status_to_post_dict(json.loads(post))
                post_data['channels'] = channels
                yield post_data

        def create_post(post_data):
            return self._create_db_post(**post_data)

        posts = map(create_post, gen_posts([str(channel.inbound)]))

        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        params = {'channel': str(self.channel.id),
                  'limit': 4,
                  'reserve_time': 30,
                  'token': self.auth_token}

        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 4)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])

    def test_with_invalid_data(self):
        posts = [self.get_post() for _ in range(0, 5)]
        for idx, post in enumerate(posts):
            if idx == 3:
                # Break on purpose
                post.content = ''
                post.speech_acts = []
                post.save()
            QueueMessage.objects.push(post, str(self.channel.id))

        self.assertEqual(QueueMessage.objects.count(), 5)
        params = {'channel': str(self.channel.id), 'limit': 5, 'reserve_time': 30}
        token = self.auth_token
        params['token'] = token
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 5)  # 5 now, that is no longer invalid data
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])
        self.assertEqual(QueueMessage.objects.count(), 5)

    def test_id_based_confirmation(self):
        posts = [self.get_post() for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        params = {'channel': str(self.channel.id), 'limit': 4, 'reserve_time': 30}
        self.check_access_not_allowed(params, 'queue/fetch')

        token = self.auth_token
        params['token'] = token
        response = self.client.post(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 4)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])
        post_ids = [data['id'] for data in data['data']]

        callback_params = {'token': token,
                           'ids': post_ids}
        response = self.client.post(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(data['cleared_count'], 4)

    def test_broken_post_confirmation(self):
        posts = [self.get_post() for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        params = {'channel': str(self.channel.id), 'limit': 5, 'reserve_time': 30}
        self.check_access_not_allowed(params, 'queue/fetch')

        token = self.auth_token
        params['token'] = token
        response = self.client.post(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 5)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])
        post_ids = [data['id'] for data in data['data']]

        callback_params = {'token': token,
                           'ids': post_ids}
        response = self.client.post(get_api_url('queue/confirm_error'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(data['cleared_count'], 5)

        self.assertEqual(len(QueueMessage.objects.find()[:]), 0)
        self.assertEqual(len(BrokenQueueMessage.objects.find()[:]), 5)

    def test_partial_confirmation(self):
        nr_of_posts = 5
        posts = [self.get_post() for _ in range(0, nr_of_posts)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        params = {'channel': str(self.channel.id),
                  'limit': nr_of_posts,
                  'reserve_time': 3,
                  'token': self.auth_token}
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), nr_of_posts)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])
        post_ids = [data['id'] for data in data['data']]
        to_confirm = post_ids[:2]
        to_fail = post_ids[2:]

        callback_params = {'token': self.auth_token,
                           'ids': to_confirm}
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(data['cleared_count'], len(to_confirm))

        time.sleep(4)    # Wait one extra second to make sure posts are cleared
        params = {'channel': str(self.channel.id),
                  'limit': nr_of_posts,
                  'reserve_time': 3,
                  'token': self.auth_token}
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), len(to_fail))
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])
        post_ids = [data['id'] for data in data['data']]
        self.assertEqual(set(post_ids), set(to_fail))

    def test_count(self):
        posts = [self.get_post() for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))
        params = {'channel': str(self.channel.id)}
        self.check_access_not_allowed(params, 'queue/count')

        token = self.auth_token
        params['token'] = token
        response = self.client.get(get_api_url('queue/count'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        self.assertEqual(data['count'], 5)

    def test_get_messages_unsafe(self):
        token = self.get_token()
        posts = [self.get_post() for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        params = {'channel': str(self.channel.id),
                  'limit': 4,
                  'unsafe': True,
                  'token': token}
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['data']), 4)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNone(data['metadata']['reserved_until'])

    def test_confirm_invalid(self):
        token = self.get_token()
        callback_params = {'token': token,
                           'batch_token': 'invalid_token'}
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertTrue(data['cleared_count'] == 0)

    def test_invalid_methods(self):
        token = self.get_token()
        happy_flow_data = {
            'token': token
        }
        resp = self.client.put(get_api_url('queue/confirm'),
                               data=json.dumps(happy_flow_data),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 405)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 135)
        resp = self.client.delete(get_api_url('queue/confirm'),
                                  data=json.dumps(happy_flow_data),
                                  content_type='application/json',
                                  base_url='https://localhost')
        self.assertEqual(resp.status_code, 405)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 135)

    def test_constants(self):
        # Just to enfoerce they are in sync with API
        self.assertEqual(MAX_LIMIT, 10000)
        self.assertEqual(DEFAULT_LIMIT, 1000)
        self.assertEqual(MAX_RESERVE_TIME, 1000)
        self.assertEqual(DEFAULT_RESERVE_TIME, 100)

    def test_removed_channel(self):
        new_channel = TwitterServiceChannel.objects.create_by_user(self.user,
                                                                   title='New channel')
        posts = [self._create_db_post(content="Post content " + str(i),
                                      channels=[new_channel.id, self.channel.id]) for i in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))

        new_channel.archive()
        try:
            TwitterServiceChannel.objects.get(new_channel.id)
            self.fail("Channel was not archived")
        except TwitterServiceChannel.DoesNotExist:
            pass

        params = {'channel': str(self.channel.id),
                  'limit': 4,
                  'reserve_time': 30,
                  'token': self.auth_token}

        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 4)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])

    def test_confirm_after_reservation_expired(self):
        posts = [self.get_post() for _ in range(0, 5)]
        for post in posts:
            QueueMessage.objects.push(post, str(self.channel.id))
        params = {'channel': str(self.channel.id),
                  'limit': 4,
                  'reserve_time': 1}
        self.check_access_not_allowed(params, 'queue/fetch')

        token = self.auth_token
        params['token'] = token
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 4)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        old_token = data['metadata']['batch_token']
        self.assertIsNotNone(data['metadata']['reserved_until'])

        time.sleep(2)
        # Check that we get 5 posts again, since the reservation time expired
        params['limit'] = 2
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        #self.assertEqual(data['warnings'], [])
        self.assertEqual(len(data['data']), 2)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])

        callback_params = {'token': token,
                           'batch_token': old_token}
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        # Even if some tokens still have that token set, we should not remove them
        # as that batch should have expired by now
        self.assertEqual(data['cleared_count'], 0)


class TestQueueEndpointConversationCases(UICase):

    def make_setup(self):
        self.sc = TwitterServiceChannel.objects.create_by_user(self.user, title='Service Channel')
        self.inbound = self.sc.inbound_channel
        self.outbound = self.sc.outbound_channel
        self.sc.save()
        self.outbound.usernames = ['test']
        self.outbound.save()
        self.channel = self.inbound
        self.contact = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        self.support = UserProfile.objects.upsert('Twitter', dict(screen_name='@test'))

        # Set up a channel for dispatching....
        self.dispatch_channel = TwitterTestDispatchChannel.objects.create_by_user(self.user, title='OUTBOUND',
                                                                                  review_outbound=False,
                                                                                  twitter_handle='test')
        self.dispatch_channel.on_active()
        self.dispatch_channel.add_perm(self.user)
        self.account.update(account_type='GSE')
        self.account.set_outbound_channel(self.dispatch_channel)

    def setUp(self):
        UICase.setUp(self)
        self.login()
        self.content = '@screen_name I need a laptop'
        self.get_post = lambda: self._create_db_post(content=self.content)
        self.make_setup()

    def set_up_conversations(self):
        screen_name = 'customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))

        url = fake_twitter_url(screen_name)
        posts = []
        post = self._create_db_post(channel=self.inbound,
                                    content="I need a foo. Does anyone have a foo?",
                                    demand_matchables=False,
                                    url=url,
                                    user_profile=user_profile)
        posts.append(post)
        self.assertEqual(len(Conversation.objects()), 1)

        url = fake_twitter_url("@test")
        reply = self._create_tweet(user_profile=user_profile,
                                   channels=[self.outbound],
                                   content="Content",
                                   url=url,
                                   in_reply_to=post)
        self.assertEqual(len(Conversation.objects()), 1)
        posts.append(reply)

        post = self._create_tweet(channels=[self.inbound],
                                  content="I still need a foo. Does anyone have a foo?",
                                  url=url,
                                  user_profile=user_profile,
                                  in_reply_to=reply)
        posts.append(post)
        url = fake_twitter_url("@test")
        reply = self._create_tweet(user_profile=self.support,
                                   channels=[self.outbound],
                                   content="Content for reply",
                                   url=url,
                                   in_reply_to=post)
        posts.append(reply)

        screen_name = 'customer2'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name)
        post2 = self._create_db_post(
                                    channel=self.inbound,
                                    content="I need a foo. Does anyone have a foo?",
                                    demand_matchables=False,
                                    url=url,
                                    user_profile=user_profile)
        posts.append(post2)

        screen_name = 'customer3'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name)
        post3 = self._create_db_post(channel=self.inbound,
                                     content="I need a foo. Does anyone have a foo?",
                                     demand_matchables=False,
                                     url=url,
                                     user_profile=user_profile)
        posts.append(post3)
        self.assertEqual(len(Conversation.objects()), 3)
        self.assertEqual(len(QueueMessage.objects()), 6)

    def test_pull_conversation_mode(self):
        self.set_up_conversations()
        params = {'channel': str(self.channel.id),
                  'limit': 10,
                  'reserve_time': 30,
                  'mode': 'conversation'}

        token = self.auth_token
        params['token'] = token
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        # Only 3 posts, since we fetch in conversation mode
        self.assertEqual(len(data['data']), 3)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])

        post_ids = []
        for entry in data['data']:
            post_ids.extend(entry['post_ids'])
        callback_params = {'token': token,
                           'ids': post_ids}
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        self.assertEqual(len(Conversation.objects()), 3)
        self.assertEqual(len(QueueMessage.objects()), 0)

    def test_pull_conversation_mode_with_processing_errors(self):
        class TestExc(Exception):
            pass

        def error(*args, **kwargs):
            post = args[0]
            post_info = u"%s %s %s" % (post.id, post.plaintext_content, Conversation.objects(posts=post.id)[:])
            raise TestExc(post_info)

        self.sc.update(posts_tracking_enabled=True)
        self.set_up_conversations()
        qm_count = QueueMessage.objects.count()

        with patch('solariat_bottle.api.queue.wrap_post', side_effect=error), LoggerInterceptor() as logs:
            params = {'channel': str(self.channel.id),
                      'limit': 10,
                      'reserve_time': 30,
                      'mode': 'conversation'}
            token = self.auth_token
            params['token'] = token
            response = self.client.get(get_api_url('queue/fetch'),
                                       data=json.dumps(params),
                                       content_type='application/json',
                                       base_url='https://localhost')
            data = json.loads(response.data)
            post_ids = []
            for entry in data['data']:
                post_ids.extend(entry['post_ids'])
            error_logs = [log.message for log in logs if log.levelname == 'ERROR' and TestExc.__name__ in log.message]
            missing_posts_count = ''.join(error_logs).count(TestExc.__name__)

            callback_params = {'token': token,
                               'ids': post_ids}
            response = self.client.get(get_api_url('queue/confirm'),
                                       data=json.dumps(callback_params),
                                       content_type='application/json',
                                       base_url='https://localhost')
            self.assertEqual(qm_count, missing_posts_count)
            self.assertEqual(QueueMessage.objects.count(), missing_posts_count)

    @patch('solariat_bottle.db.conversation.Conversation.mark_corrupted')
    def test_pull_root_mode(self, mark_corrupted):
        self.set_up_conversations()
        params = {'channel': str(self.channel.id),
                  'limit': 10,
                  'reserve_time': 30,
                  'mode': 'root_included'}

        token = self.auth_token
        params['token'] = token
        response = self.client.get(get_api_url('queue/fetch'),
                                   data=json.dumps(params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        #self.assertEqual(data['warnings'], [])
        # Only 3 posts, since we fetch in conversation mode
        self.assertEqual(len(data['data']), 6)
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])

        post_ids = []
        for entry in data['data']:
            post_ids.append(entry['id'])
        callback_params = {'token': token,
                           'ids': post_ids}
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(data.get('deprecation_warning'),
                         "GET requests on /queue endpoints should be replaced with POST requests.")
        self.assertEqual(len(Conversation.objects()), 3)
        self.assertEqual(len(QueueMessage.objects()), 0)


class TestQueueEndpointConversationCorruptedCases(RestCase, ApiQueueTestMixin):
    _recover_parents_for_2nd_level_comments = patch(
        'solariat_bottle.api.queue.recover_parents_for_2nd_level_comments')
    _mark_corrupted = patch(
        'solariat_bottle.db.conversation.Conversation.mark_corrupted', new_callable=PropertyMock)

    NATIVE_IDS_MAP = {
        'root_post': '1526839287537851_1680168048871640',
        'comment1': '1680168048871640_1680175248870920',
        'comment2': '1680168048871640_1680434568844988',
        'second_level_comment': '1680168048871640_1680434598844985',
        'root_pm': 'm_mid.1438869346558:4ff7df25f504265294',
        'pm_comment': 'm_mid.1438869460799:44d770139bab47b636'
    }

    def send_root_post(self):

        content ='{"content":"This is conversation root","user_profile":{"id":"1526839287537851",' \
               '"user_name":"Software architect party"},"facebook":{"_wrapped_data":{"to":[],"share_count":0,' \
               '"source_type":"Page","created_by_admin":1,"from":{"category":"Community","name":"Software architect party",' \
               '"id":"1526839287537851"},"type":"status","updated_time":"2015-08-05T13:36:04 +0000","can_comment":1,' \
               '"id":"1526839287537851_1680168048871640","attachment_count":0,"created_at":"2015-08-05T13:36:04 +0000",' \
               '"is_published":false,"comment_count":0,"source_id":"1526839287537851","privacy":"EVERYONE","can_remove":1,' \
               '"properties":[],"can_change_visibility":1,"is_liked":0,"message":"This is conversation root","can_like":1,' \
               '"is_popular":false,"can_be_hidden":1,"actions":[{"name":"Comment"},{"name":"Like"}]},"facebook_post_id":' \
               '"1526839287537851_1680168048871640","created_at":"2015-08-05T13:36:04 +0000","page_id":"1526839287537851"},' \
               '"channel": "%s"}' % str(self.channel.id)

        return self.send_post(content)

    def send_comment1(self):

        content = '{"content":"Comment1 to post","user_profile":{"id":"1526839287537851","user_name":"Software architect party"},' \
                  '"facebook":{"root_post":"1526839287537851_1680168048871640","_wrapped_data":{"user_likes":0,"visibility":"Normal",' \
                  '"source_id":"1526839287537851_1680168048871640","source_type":"Page","can_remove":1,"from":{"category":"Community",' \
                  '"name":"Software architect party","id":"1526839287537851"},"can_hide":0,"type":"Comment","can_comment":1,"can_like":1,' \
                  '"id":"1680168048871640_1680175248870920","message":"Comment1 to post","like_count":0,"created_at":"2015-08-05T14:13:37 ' \
                  '+0000","parent_id":"1680168048871640"},"facebook_post_id":"1680168048871640_1680175248870920","in_reply_to_status_id":' \
                  '"1526839287537851_1680168048871640","created_at":"2015-08-05T14:13:37 +0000","page_id":"1526839287537851_1680168048871640",' \
                  '"second_level_reply":false},"channel":"%s","url":"www.facebook.com/permalink.php?id\u003d1526839287537851_1680168048871640\
                  u0026story_fbid\u003d1680175248870920\u0026comment_id\u003d1680168048871640"}' % str(self.channel.id)

        return self.send_post(content)

    def send_comment2(self):

        content = '{"content":"Comment 2 to post","user_profile":{"id":"1526839287537851",' \
                  '"user_name":"Software architect party"},"facebook":{"root_post":"1526839287537851_1680168048871640",' \
                  '"_wrapped_data":{"user_likes":0,"visibility":"Normal","source_id":"1526839287537851_1680168048871640",' \
                  '"source_type":"Page","can_remove":1,"from":{"category":"Community","name":"Software architect party",' \
                  '"id":"1526839287537851"},"can_hide":0,"type":"Comment","can_comment":1,"can_like":1,' \
                  '"id":"1680168048871640_1680434568844988","message":"Comment 2 to post",' \
                  '"like_count":0,"created_at":"2015-08-06T11:27:00 +0000","parent_id":"1680168048871640"},' \
                  '"facebook_post_id":"1680168048871640_1680434568844988","in_reply_to_status_id":"1526839287537851_1680168048871640",' \
                  '"created_at":"2015-08-06T11:27:00 +0000","page_id":"1526839287537851_1680168048871640",' \
                  '"second_level_reply":false},"channel":"%s",' \
                  '"url":"www.facebook.com/permalink.php?id\u003d1526839287537851_1680168048871640\u0026story_fbid\u003d1680434568844988' \
                  '\u0026comment_id\u003d1680168048871640"}' % str(self.channel.id)

        return self.send_post(content)

    def send_2ndlvl_comment(self):

        content = '{"content":"2nd level comment to post","user_profile":{"id":"1526839287537851","user_name":"Software ' \
                  'architect party"},"facebook":{"root_post":"1526839287537851_1680168048871640","_wrapped_data":{"user_likes":0,' \
                  '"source_id":"1526839287537851_1680168048871640","source_type":"Page","can_remove":1,"from":{"category":"Community",' \
                  '"name":"Software architect party","id":"1526839287537851"},"can_hide":0,"type":"Comment","can_comment":0,' \
                  '"can_like":0,"id":"1680168048871640_1680434598844985","message":"2nd level comment to post","like_count":0,' \
                  '"created_at":"2015-08-06T11:27:14 +0000","parent_id":"1680168048871640_1680434568844988"},"facebook_post_id":' \
                  '"1680168048871640_1680434598844985","in_reply_to_status_id":"1680168048871640_1680434568844988",' \
                  '"created_at":"2015-08-06T11:27:14 +0000","page_id":"1526839287537851_1680168048871640","second_level_reply":true},' \
                  '"channel":"%s","url":"www.facebook.com/permalink.php?id\u003d1526839287537851_16801680488716' \
                  '40\u0026story_fbid\u003d1680434598844985\u0026comment_id\u003d1680168048871640"}' % str(self.channel.id)

        return self.send_post(content)

    def send_root_pm(self):

        content = '{"content":"Hello. Do you work with java/python?","user_profile":{"id":"1462280684051936","first_name":' \
                  '"John","user_name":"John Dowe","link":"https://www.facebook.com/app_scoped_user_id/1462280684051936/","last_name":' \
                  '"John","updated_time":"2015-01-15T16:06:29 +0000","profile_image_url":"https://fbcdn-profile-a.akamaihd.net/hprofile-' \
                  'ak-xap1/v/t1.0-1/p50x50/10931006_1534184826861521_2691804554593843603_n.jpg?oh\u003db0fc3f4e36daf219fa1d45eca23ae898\
                  u0026oe\u003d56563F73\u0026__gda__\u003d1447337138_638cf65b6d5c2bf940106ec4f7085501"},"facebook":{"_wrapped_data":' \
                  '{"message":"Hello. Do you work with java/python?","id":"m_mid.1438869346558:4ff7df25f504265294","source_id":' \
                  '"t_mid.1409075856790:36237e8ba4af259786","source_type":"PM","created_at":"2015-08-06T13:55:46 +0000","from":' \
                  '"John Dowe","type":"pm"},"conversation_id":"t_mid.1409075856790:36237e8ba4af259786","facebook_post_id":' \
                  '"m_mid.1438869346558:4ff7df25f504265294","created_at":"2015-08-06T13:55:46 +0000","page_id":"1526839287537851"},' \
                  '"channel":"' + str(self.channel.id) +'","url":"https://facebook.com//dfdfadslfds/manager/messages/?mercurythreadid\u003duser' \
                  '%3A100008100554735\u0026threadid\u003dmid.1409075856790%3A36237e8ba4af259786\u0026folder\u003dinbox"}'

        return self.send_post(content)

    def send_pm_comment(self):

        content = '{"content":"Hello. Yes, we work with this platforms before and will be happy to help you.","user_profile"' \
                  ':{"id":"1526839287537851","user_name":"Software architect party"},"facebook":{"root_post":"m_mid.1438869346558:' \
                  '4ff7df25f504265294","_wrapped_data":{"message":"Hello. Yes, we work with this platforms before and will' \
                  ' be happy to help you.","id":"m_mid.1438869460799:44d770139bab47b636","source_id":"t_mid.1409075856790:' \
                  '36237e8ba4af259786","source_type":"PM","created_at":"2015-08-06T13:57:41 +0000","from":"Software ' \
                  ' party","type":"pm"},"conversation_id":"t_mid.1409075856790:36237e8ba4af259786","facebook_post_id":' \
                  '"m_mid.1438869460799:44d770139bab47b636","in_reply_to_status_id":"m_mid.1438869346558:4ff7df25f504265294",' \
                  '"created_at":"2015-08-06T13:57:41 +0000","page_id":"1526839287537851"},"channel":"' + str(self.channel.id) +'",' \
                  '"url":"https://facebook.com//dfdfadslfds/manager/messages/?mercurythreadid\u003duser%3A100008100554735' \
                  '\u0026threadid\u003dmid.1409075856790%3A36237e8ba4af259786\u0026folder\u003dinbox"}'

        return self.send_post(content)

    def setUp(self):

        RestCase.setUp(self)
        self.account.update(account_type='GSE')
        self.efc = EnterpriseFacebookChannel.objects.create_by_user(self.user, title="EFC", status="Active")
        self.efc.facebook_access_token = "test"
        self.efc.save()
        self.channel = FacebookServiceChannel.objects.create_by_user(self.user, title='FSC', facebook_page_ids=["1526839287537851"])
        self.user.set_outbound_channel(self.efc)
        self.channel.history_time_period = 0
        self.channel.save()
        self.api_token = self.get_token()
        self.mark_corrupted = self._mark_corrupted.start()
        self.recover_parents_for_2nd_level_comments = self._recover_parents_for_2nd_level_comments.start()

    def tearDown(self):
        super(TestQueueEndpointConversationCorruptedCases, self).tearDown()

        stop_mock_patch(self._mark_corrupted)
        stop_mock_patch(self._recover_parents_for_2nd_level_comments)

    def delete_root_post(self):
        post = FacebookPostManager.find_by_fb_id(self.NATIVE_IDS_MAP['root_post'])
        post.delete()

    def delete_root_pm_post(self):
        post = FacebookPostManager.find_by_fb_id(self.NATIVE_IDS_MAP['root_pm'])
        post.delete()

    def test_check_corrupted_conv(self):
        with self._mark_corrupted as mark_corrupted:
            self.assertTrue(Conversation.objects.count() == 0)
            self.send_root_post()
            self.send_comment1()
            self.send_comment2()
            self.send_2ndlvl_comment()

            self.assertTrue(Conversation.objects.count() == 1)
            conv = Conversation.objects.find()[:][0]
            self.assertTrue(conv.has_initial_root_post())

            self.delete_root_post()
            conv.reload()
            self.assertFalse(conv.has_initial_root_post())
            conv.mark_corrupted()
            # self.assertTrue(conv.is_corrupted)
            mark_corrupted.assert_called_once_with()

    def test_check_corrupted_pm_conv(self):
        with self._mark_corrupted as mark_corrupted:
            self.assertTrue(Conversation.objects.count() == 0)
            self.send_root_pm()
            self.send_pm_comment()
            self.assertTrue(Conversation.objects.count() == 1)

            self.assertTrue(Conversation.objects.count() == 1)
            conv = Conversation.objects.find()[:][0]
            self.assertTrue(conv.has_initial_root_post())

            self.delete_root_pm_post()
            conv.reload()
            self.assertFalse(conv.has_initial_root_post())
            conv.mark_corrupted()
            # self.assertTrue(conv.is_corrupted)
            mark_corrupted.assert_called_once_with()

    def test_incorrect_post_conv_build(self):

        self.send_comment1()
        self.send_comment2()
        self.send_2ndlvl_comment()
        conv = Conversation.objects.find()[:][0]
        self.assertFalse(conv.has_initial_root_post())

    def test_incorrect_pm_conv_build(self):

        self.send_pm_comment()
        self.assertTrue(Conversation.objects.count() == 1)
        conv = Conversation.objects.find()[:][0]
        self.assertFalse(conv.has_initial_root_post())
        self.assertTrue(conv.is_corrupted)

    def test_check_corrupted_conv_message_queue(self):
        with self._mark_corrupted as mark_corrupted:
            self.send_root_post()
            self.send_comment1()
            self.send_comment2()
            self.send_2ndlvl_comment()

            self.send_root_pm()
            self.send_pm_comment()

            queue_data = self.send_queue_request('conversation')['data']
            self.assertIsNotNone(queue_data)
            self.assertEqual(len(queue_data), 2)

            time.sleep(3)
            self.delete_root_pm_post()

            queue_data = self.send_queue_request('conversation')['data']
            self.assertIsNotNone(queue_data)
            self.assertEqual(len(queue_data), 2)
            # self.assertTrue(len(Conversation.objects.find(is_corrupted=True)[:]) == 1)
            mark_corrupted.assert_called_once_with()

    def test_check_corrupted_root_mode_message_queue(self):
        with self._mark_corrupted as mark_corrupted:
            self.send_root_post()
            self.send_comment1()
            self.send_comment2()
            self.send_2ndlvl_comment()

            self.send_root_pm()
            self.send_pm_comment()

            queue_data = self.send_queue_request('root_included')['data']
            self.assertIsNotNone(queue_data)
            self.assertEqual(len(queue_data), 6)

            time.sleep(3)
            self.delete_root_post()

            queue_data = self.send_queue_request('root_included')['data']
            self.assertIsNotNone(queue_data)
            self.assertEqual(len(queue_data), 2)
            # self.assertTrue(len(Conversation.objects.find(is_corrupted=True)[:]) == 1)
            mark_corrupted.assert_called_once_with()

    def test_threads_corrupted_on_queue_fetch(self):
        self.mark_corrupted.start()
        self.channel.update(posts_tracking_enabled=True)

        def fetch_and_confirm(*args):
            def _inner():
                res = self.fetch_and_confirm(mode='root_included')
                if args and args[0] is True:
                    self.mark_corrupted.assert_called_once_with()
                if len(args) > 1 and args[1] is True:
                    self.assertEqual(self.recover_parents_for_2nd_level_comments.call_count, 1)
                self.mark_corrupted.reset_mock()
                self.recover_parents_for_2nd_level_comments.reset_mock()
                return res

            if not args:
                return _inner()
            else:
                return _inner

        modes = ['root_included', 'conversation']
        cases = [
            # fetch modes list - posts list - expected post ids on queue fetch - should call mark_corrupted - should call comments recovery
            (modes, [self.send_comment2], [], True, False),
            (modes, [self.send_comment2, self.send_2ndlvl_comment], [], True, False),
            (modes, [self.send_2ndlvl_comment], [], True, False),
            (modes, [self.send_pm_comment], [], True, False),
            # missing first level comment cases
            (modes, [self.send_root_post, self.send_2ndlvl_comment], ['root_post'], False, True),
            (modes, [self.send_root_post, self.send_2ndlvl_comment, fetch_and_confirm], [], False, True),
            (modes, [self.send_root_post, fetch_and_confirm(False, False), self.send_2ndlvl_comment], [], False, True),
            (modes, [self.send_root_post, self.send_2ndlvl_comment, fetch_and_confirm(False, True), self.send_comment2],
                ['root_post', 'comment2', 'second_level_comment'], False, False),
        ]

        errors = []
        for modes, actions, return_posts, should_mark_as_corrupted, should_call_comments_recovery in cases:
            for mode in modes:
                self.cleanup_db()
                self.mark_corrupted.reset_mock()
                self.recover_parents_for_2nd_level_comments.reset_mock()
                confirmed = 0
                post_actions = 0
                for action in actions:
                    res = action()
                    post_actions += 1
                    if isinstance(res, dict) and 'confirmed' in res:
                        post_actions -= 1
                        confirmed += res.get('confirmed', 0)
                self.assertEqual(Conversation.objects.count(), 1)
                self.assertEqual(len(Conversation.objects.get().posts), post_actions)

                queue_data = self.send_queue_request(mode)['data']
                try:
                    if return_posts:
                        returned_post_ids = []
                        for batch in queue_data:
                            returned_post_ids.extend([p['id'] for p in batch['post_data']])

                        expected_post_ids = [p.id for p in map(FacebookPost.get_by_native_id,
                                                               map(self.NATIVE_IDS_MAP.get, return_posts))]
                        self.assertTrue(queue_data, msg="queue/fetch should have returned data")
                        self.assertEqual(
                            set(returned_post_ids), set(expected_post_ids),
                            msg="Expected: %s\nReturned: %s" % (expected_post_ids, returned_post_ids))
                    else:
                        self.assertFalse(queue_data)
                    if should_mark_as_corrupted:
                        self.mark_corrupted.assert_called_once_with()
                    if should_call_comments_recovery:
                        self.assertEqual(self.recover_parents_for_2nd_level_comments.call_count, 1)
                except AssertionError, e:
                    print(e)
                    print(mode, [getattr(a, '__name__', a) for a in actions], return_posts, should_mark_as_corrupted)
                    errors.append(e)
        if errors:
            print("found %d errors: %s" % (len(errors), errors))
            raise errors[0]

    def test_root_included_second_level_comments(self):
        initial_count = QueueMessage.objects.count()
        self.send_root_post()
        fetch_response = self.send_queue_request('root_included')
        queue_data = fetch_response['data']
        self.assertIsNotNone(queue_data)
        self.assertEqual(len(queue_data), 1)
        self.assertEqual(len(queue_data[0]['post_data']), 1)
        callback_params = {'token': self.api_token,
                           'batch_token': fetch_response['metadata']['batch_token']}
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(initial_count, QueueMessage.objects.count())

        self.send_comment2()

        time.sleep(2)    # So post makes it to queue
        fetch_response = self.send_queue_request('root_included')
        queue_data = fetch_response['data']
        self.assertIsNotNone(queue_data)
        self.assertEqual(len(queue_data), 1)
        self.assertEqual(len(queue_data[0]['post_data']), 2)
        callback_params['batch_token'] = fetch_response['metadata']['batch_token']
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(initial_count, QueueMessage.objects.count())

        self.send_2ndlvl_comment()
        time.sleep(2)    # So post makes it to queue
        queue_data = self.send_queue_request('root_included')['data']
        self.assertIsNotNone(queue_data)
        self.assertEqual(len(queue_data), 1)
        self.assertEqual(len(queue_data[0]['post_data']), 3)

    def test_restore_post_conv(self):

        self.send_comment1()
        self.send_comment2()
        self.send_2ndlvl_comment()
        conv = Conversation.objects.find()[:][0]
        self.assertFalse(conv.has_initial_root_post())
        conv.is_corrupted = True
        conv.save(is_safe=True)

        self.send_root_post()
        conv.reload()
        self.assertTrue(conv.has_initial_root_post())
        self.assertFalse(conv.is_corrupted)

    def test_restore_pm_conv(self):

        self.send_pm_comment()
        self.assertTrue(Conversation.objects.count() == 1)
        conv = Conversation.objects.find()[:][0]
        self.assertFalse(conv.has_initial_root_post())
        self.assertTrue(conv.is_corrupted)

        self.send_root_pm()
        conv.reload()
        self.assertTrue(conv.has_initial_root_post())
        self.assertFalse(conv.is_corrupted)

    def test_recover_parents_for_2nd_level_comments(self):
        stop_mock_patch(self._recover_parents_for_2nd_level_comments)

        from solariat_bottle.api.queue import recover_parents_for_2nd_level_comments

        with patch('requests.request') as http:
            resp = self.send_2ndlvl_comment()
            comments = [FacebookPost.objects.get(resp['item']['id'])]
            task = recover_parents_for_2nd_level_comments(comments)
            if hasattr(task, 'result'):
                res = task.result()
            self.assertEqual(http.call_count, 1)
            self.assertEqual(http.call_args[1]['json']['data'][0]['comment_id'], comments[0].wrapped_data['parent_id'])

    def test_recover_parents_for_2nd_level_comments_throttling(self):
        stop_mock_patch(self._recover_parents_for_2nd_level_comments)

        from solariat_bottle.api.queue import recover_parents_for_2nd_level_comments
        expected_log_head = "comment's parent is being recovered  cached_entry: "

        def test(throttle=0, N=3):
            from solariat_bottle.app import app
            app.logger.info("\n\n=== CASE %s %s", throttle, N)

            from solariat_bottle.utils.cache import MongoDBCache
            MongoDBCache().coll.remove()

            with patch('requests.request') as http, LoggerInterceptor() as logs:
                resp = self.send_2ndlvl_comment()
                comments = [FacebookPost.objects.get(resp['item']['id'])]
                for i in range(N):
                    task = recover_parents_for_2nd_level_comments(comments)
                    if hasattr(task, 'result'):
                        res = task.result()
                if throttle > 0 and N > 0:
                    self.assertEqual(http.call_count, 1)
                    self.assertEqual(len([1 for log in logs if log.message.startswith(expected_log_head)]), N - 1,
                                     msg="expected %s logs start with %s" % (N - 1, expected_log_head))
                else:
                    self.assertEqual(http.call_count, N)

        from solariat_bottle import settings
        for throttle, N in [(-10, 3), (0, 3), (10, 3), (1, 0)]:
            try:
                old_val = settings.FB_COMMENT_PARENT_RECOVERY_THROTTLE
                settings.FB_COMMENT_PARENT_RECOVERY_THROTTLE = throttle
                test(throttle, N)
            finally:
                settings.FB_COMMENT_PARENT_RECOVERY_THROTTLE = old_val


def log_conversation(conversation):
    logging.info("CONVERSATION %s", conversation)
    for post in conversation.post_objects:
        logging.info("\t\t%s %s %s", post.id, post.created_at, post.plaintext_content)
    if conversation.amplifiers:
        logging.info('==== amplifiers')
        for post in Post.objects(id__in=conversation.amplifiers):
            logging.info("\t\t%s %s %s", post.id, post.created_at, post.plaintext_content)
    logging.info('\n\n')


class TwitterChannelApiQueue(RestCase, ApiQueueTestMixin):
    COMBINED_CONVERSATION = 'tests/data/twitter/conversation_combined.yaml'
    POST_NAMES = """
    customer_dm_1
    brand_dm_1
    brand_dm_2
    customer_dm_2
    customer_dm_3
    customer_public_tweet_1
    customer_public_tweet_2
    brand_reply_to_public_tweet_2
    brand_public_tweet
    customer_retweet
    """

    @staticmethod
    def load_yaml(filename=COMBINED_CONVERSATION):
        import yaml
        import solariat_bottle
        from os.path import join, dirname

        with open(join(dirname(solariat_bottle.__file__), filename)) as input_file:
            return yaml.load(input_file)

    @staticmethod
    def load_posts_map(filename=COMBINED_CONVERSATION):
        posts_map = {}
        for chunk in TwitterChannelApiQueue.load_yaml(filename):
            data = chunk['data']
            data['channels'] = [str(ch.id) for ch in
                                lookup_tracked_channels('Twitter', data.copy())]
            data.pop('direct_message', None)
            data.pop('sender_handle', None)
            data.pop('recipient_handle', None)

            posts_map[chunk['name']] = chunk
        return posts_map

    def setUp(self):
        super(TwitterChannelApiQueue, self).setUp()
        self.api_token = self.get_token()

        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='Twitter-Service',
                                                               posts_tracking_enabled=True)
        etc = EnterpriseTwitterChannel.objects.create_by_user(self.user,
                                                              twitter_handle='brand_handle',
                                                              title='Twitter-Account')
        channel.set_dispatch_channel(etc)
        self.user.set_outbound_channel(etc)
        channel.add_username('@brand_handle')
        self.channel = channel
        self.posts_map = self.load_posts_map(self.COMBINED_CONVERSATION)

    def create_posts(self, *args):
        posts_resp = []
        if len(args) == 1 and isinstance(args[0], basestring):
            names = filter(None, map(str.strip, args[0].split()))
        else:
            names = args
        for name in names:
            post = self.posts_map[name]
            print post['description']
            tweet_data = post['data']
            posts_resp.append(self.send_post(content=json.dumps(tweet_data)))
        posts = sorted(Post.objects(id__in=[x['item']['id'] for x in posts_resp]),
                       key=lambda x: x.created_at)
        return posts

    def _generate_response_sample(self):
        def send_messages(self, scenario):
            for action in scenario:
                if action in self.posts_map:
                    post = self.posts_map[action]
                    print post['description']
                    tweet_data = post['data']
                    self.send_post(content=json.dumps(tweet_data))

        def test_combined_conversation(self):
            all_messages = filter(None, map(lambda x: x.strip(), self.POST_NAMES.split('\n')))[-2:]
            self.send_messages(all_messages)

            modes = ['conversation']  # , 'root_included']
            import inspect
            from solariat_bottle.settings import LOGGER
            for mode in modes:
                LOGGER.info('\n\nCASE %s', mode)
                response = self.send_queue_request(mode, self.channel)
                case_name = inspect.stack()[0][3]
                json.dump(response, open('twitter_case_%s__mode_%s.json' % (case_name, mode), 'w'))

                for conversation in Conversation.objects():
                    log_conversation(conversation)


class TwitterPostGroupingCase(TwitterChannelApiQueue):
    def test_maybe_group(self):
        from solariat_bottle.api.queue import maybe_group, PostGroup, PUBLIC_TWEET, DIRECT_MESSAGE, RETWEET

        class PostMock(dict):
            defaults = dict(
                created_at=datetime.utcnow(),
                is_pm=False,
                is_retweet=False,
                is_reply=False
            )

            def __getattr__(self, name):
                try:
                    return dict.__getitem__(self, name)
                except KeyError:
                    return self.defaults.get(name)

            @property
            def id(self):
                return self.created_at

        ConversationMock = PostMock

        start = datetime.utcnow()
        def t(delta):
            return start + timedelta(seconds=delta)

        def create_post_mock(created_at=datetime.now(), tweet_type=PUBLIC_TWEET):
            post_data = dict(created_at=created_at)
            if tweet_type == DIRECT_MESSAGE:
                post_data.update(is_pm=True)
            if tweet_type == RETWEET:
                post_data.update(is_retweet=True)
            return PostMock(**post_data)
        p = create_post_mock
        timeout = 30
        cases = [
            #     prev_post              post                    group_by_type  expect_new_group
            [(t(0), PUBLIC_TWEET), (t(0.5 * timeout), PUBLIC_TWEET), True, False],
            [(t(0), PUBLIC_TWEET), (t(1.5 * timeout), PUBLIC_TWEET), False, True],
            [(t(0), PUBLIC_TWEET), (t(0.5 * timeout), DIRECT_MESSAGE), False, False],
            [(t(0), PUBLIC_TWEET), (t(0.5 * timeout), DIRECT_MESSAGE), True, True],
        ]

        conv = ConversationMock(created_at=start)
        for prev_post, post, group_by_type, expect_new_group in cases:
            group = maybe_group(p(*post), p(*prev_post), conv, timeout, group_by_type)
            if expect_new_group:
                expected = PostGroup(conv, p(*post))
            else:
                expected = None
            self.assertEqual(group, expected, "%s != %s" % (group, expected))

    def test_get_previous_conversation_posts(self):
        from solariat_bottle.api.queue import get_previous_conversation_posts
        posts = self.create_posts("""
            customer_dm_1
            brand_dm_1
            brand_dm_2
            customer_dm_2
            customer_dm_3""")
        self.assertEqual(Conversation.objects.count(), 1)
        conversation = Conversation.objects.get()
        self.assertEqual(set(conversation.post_objects), set(posts))
        cases = [
            (posts[0], [], 10),
            (posts[1], [posts[0]], 10),
            (posts[2], [posts[1], posts[0]], 10),
            (posts[-1], posts[::-1][1:], 10),
            (posts[-1], [posts[-2]], 1),
        ]
        for current_post, expected, lookup_limit in cases:
            logging.info('CASE %s %s %s', current_post, expected, lookup_limit)
            self.assertEqual(get_previous_conversation_posts(current_post, conversation, lookup_limit), expected)

    def test_find_last_group_in_conversation(self):
        from solariat_bottle.api.queue import find_last_group_in_conversation
        posts = self.create_posts("""
            customer_dm_1
            brand_dm_1
            brand_dm_2
            customer_dm_2
            customer_dm_3""")
        conversation = Conversation.objects.get()
        group_0 = PostGroup(conversation, posts[0])
        group_1 = PostGroup(conversation, posts[1])
        cases = [
            (posts[0], group_0),
            (posts[1], group_1),
            (posts[2], group_1),  # first post from brand
            (posts[3], group_0),
            (posts[4], group_0),
        ]
        for current_post, expected_group in cases:
            logging.info('CASE %s %s', current_post, expected_group)
            group = find_last_group_in_conversation(current_post, conversation, grouping_timeout=120)
            self.assertEqual(group, expected_group)

    def test_assign_groups(self):
        from solariat_bottle.api.queue import assign_groups
        posts = self.create_posts("""
            customer_dm_1
            brand_dm_1
            brand_dm_2
            customer_dm_2
            customer_dm_3""")
        conversation = Conversation.objects.get()
        group_0 = PostGroup(conversation, posts[0])
        group_1 = PostGroup(conversation, posts[1])
        expected_groups = [
            (posts[0], group_0),
            (posts[1], group_1),
            (posts[2], group_1),  # first post from brand
            (posts[3], group_0),
            (posts[4], group_0),
        ]
        i = 0
        for (post, group), (expected_post, expected_group) in itertools.izip(
                assign_groups(posts, conversation),
                expected_groups):
            i += 1
            self.assertEqual(post, expected_post)
            self.assertEqual(group, expected_group)
        self.assertEqual(i, len(posts))

        # timeout = 0 - each post should have its own group
        i = 0
        for post, group in assign_groups(posts, conversation, grouping_timeout=0):
            i += 1
            self.assertEqual(group, PostGroup(conversation, post))
        self.assertEqual(i, len(posts))

    def test_post_api_queue(self):
        posts = self.create_posts("""customer_dm_1""")
        conversation = Conversation.objects.get()
        # Note: grouping_timeout request parameter overrides channel configuration
        cases = [
            # channel grouping config (is_enabled, timeout)  -  api/queue request params  - expect group_id?
            [(False, 10), {}, False],
            [(False, 10), {'grouping_timeout': 0}, False],
            [(False, 10), {'grouping_timeout': 10}, True],

            # [(True, 0), {}, False],
            # [(True, 0), {'grouping_timeout': 0}, False],
            # [(True, 0), {'grouping_timeout': 10}, True],
            #
            # [(True, 10), {}, True],
            # [(True, 10), {'grouping_timeout': 0}, False],
            # [(True, 10), {'grouping_timeout': 20}, True],
        ]
        nothing = object()
        for (grouping_enabled, grouping_timeout), queue_request_kwargs, expect_group_id in cases:
            logging.info('CASE %s %s %s', (grouping_enabled, grouping_timeout), queue_request_kwargs, expect_group_id)
            self.channel.grouping_enabled = grouping_enabled
            self.channel.grouping_timeout = grouping_timeout
            self.channel.save()
            res = self.send_queue_request(mode='single', **queue_request_kwargs)
            self.assertEqual(len(res['data']), 1)

            post_data = res['data'][0]
            if expect_group_id:
                expected_group_id = "%s:%s" % (conversation.id, posts[0].id)
                self.assertEqual(post_data['group_id'], expected_group_id)
                self.assertEqual(post_data['grouping_info']['id'], expected_group_id)
                self.assertEqual(post_data['grouping_info']['timeout'], queue_request_kwargs.get('grouping_timeout') or grouping_timeout)
            else:
                self.assertEqual(post_data.get('group_id', nothing), nothing)
                self.assertEqual(post_data.get('grouping_info', nothing), nothing)
            QueueMessage.objects.reset_reservation(QueueMessage.objects()[:])

        # finalize
        res = self.fetch_and_confirm(mode='single')
        self.assertEqual(QueueMessage.objects.count(), 0)

    def test_assign_groups__complex(self):
        """TODO: post different types of tweets, group by timeout and tweet type"""
        from solariat_bottle.api.queue import assign_groups
        posts = self.create_posts("""
            customer_dm_1
            brand_dm_1
            brand_dm_2
            customer_dm_2
            customer_dm_3
            customer_public_tweet_1
            customer_public_tweet_2
            brand_reply_to_public_tweet_2""")

        conversation = Conversation.objects.get()
        group_0 = PostGroup(conversation, posts[0])
        group_1 = PostGroup(conversation, posts[1])
        expected_groups = [
            (posts[0], group_0),
            (posts[1], group_1),
            (posts[2], group_1),  # first post from brand
            (posts[3], group_0),
            (posts[4], group_0),
        ]
        # self.assertFalse(True)