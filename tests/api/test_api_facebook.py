import json
from mock import patch
import random

from solariat_bottle.app import get_api_url
from solariat_bottle.db.account import Account
from solariat_bottle.db.channel.facebook import EnterpriseFacebookChannel, FacebookServiceChannel
from solariat_bottle.db.post.facebook import FacebookPost
from solariat_bottle.db.roles import ADMIN, AGENT, ANALYST
from solariat_bottle.tests.base import RestCase
from solariat_bottle.utils import facebook_driver

FB_OBJECTS = []
FB_REQUESTS = []


class FakeGraphAPI():

    def __init__(self, token, version=None, channel=None):
        self.token = token

    def __getattr__(self, item):
        raise NotImplementedError("Facebook Mock API does not expose %s" % item)

    def put_object(self, *args, **kwargs):
        # Just blindly return status
        FB_OBJECTS.append((args, kwargs))
        return dict(id=args[0]) if args else dict(id=kwargs.items()[0]) if kwargs else None

    def get_object(self, *args, **kwargs):
        FB_OBJECTS.append((args, kwargs))
        return self.request(*args, **kwargs)

    def request(self, *args, **kwargs):
        FB_REQUESTS.append((args, kwargs))
        return dict(id=args[0]) if args else kwargs.items()[0] if kwargs else None

    def put_comment(self, *args, **kwargs):
        FB_OBJECTS.append(('put_comment', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def put_wall_post(self, *args, **kwargs):
        FB_OBJECTS.append(('put_wall_post', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def delete_object(self, *args, **kwargs):
        FB_OBJECTS.append(('delete_object', args, kwargs))
        return dict(id=args[0]) if args else dict(id=kwargs.items()[0]) if kwargs else None


def fake_api_getter(*args):
    return FakeGraphAPI(token = "token")


class FacebookCommandsTest(RestCase):
    """ This test suite is strictly for the API interaction and making sure a valid API request
    actually makes it's way down until the actual Facebook GraphAPI request. Specific integrations
    with facebook are tested in separate files like test_facebook* """
    def setUp(self):
        super(FacebookCommandsTest, self).setUp()
        self.email = "admin_benchmark@solariat.com"
        self.password = 'password'
        self.account = Account.objects.create(name="Search-Account")
        self.user = self._create_db_user(email=self.email, password=self.password, account=self.account,
                                         roles=[ADMIN, AGENT, ANALYST])
        self._create_static_events(self.user)
        del FB_OBJECTS[:]
        del FB_REQUESTS[:]
        self.real_api = facebook_driver.GraphAPI
        facebook_driver.GraphAPI = FakeGraphAPI
        self.efc = EnterpriseFacebookChannel.objects.create_by_user(self.user, title="EFC", status="Active")
        self.efc.facebook_access_token = "test"
        self.efc.save()
        self.channel = FacebookServiceChannel.objects.create_by_user(self.user, title='FSC')
        self.channel.facebook_access_token = "test"
        self.user.set_outbound_channel(self.efc)

        eventId = random.randint(2000000, 5000000000)
        self.fb_nativeid = 'facebook_post_id'

        post = FacebookPost(channels=[self.channel.id], content="Test", actor_id='fake_actor_id',
                            _native_id=self.fb_nativeid,
                            extra_fields={})
        post.id = eventId
        post.save()

    def tearDown(self):
        super(FacebookCommandsTest, self).tearDown()
        facebook_driver.GraphAPI = self.real_api

    @patch("solariat_bottle.tasks.facebook.get_page_based_api", fake_api_getter)
    def test_like_unlike(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         object_id=self.fb_nativeid,
                         )
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/facebook/like', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(FB_OBJECTS) == 1)
        self.assertTrue(len(FB_REQUESTS) == 0)
        self.assertEqual(FB_OBJECTS[0], ((u'facebook_post_id', 'likes'), {}))

        post_data['delete'] = True
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/facebook/like', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(FB_OBJECTS) == 2)
        self.assertTrue(len(FB_REQUESTS) == 0)
        self.assertEqual(FB_OBJECTS[1], ((u'facebook_post_id', 'likes'), {'method': 'delete'}))

        self.efc.facebook_access_token = None
        self.efc.save()
        resp = self.client.get(get_api_url('commands/facebook/like', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 400)
        resp_data = json.loads(resp.data)
        self.assertFalse(resp_data['ok'])
        self.assertEqual(resp_data['code'], 364)
        self.assertTrue(len(FB_OBJECTS) == 2)
        self.assertTrue(len(FB_REQUESTS) == 0)

    def test_share_post(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         post_url="this_is_post_url")
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/facebook/share', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(FB_REQUESTS) == 1)
        self.assertEqual(FB_REQUESTS[0], (('/me/feed',), {'post_args': {'link': u'this_is_post_url'}}))

    @patch("solariat_bottle.tasks.facebook.get_page_based_api", fake_api_getter)
    def test_comment_post(self):

        token = self.get_token()

        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         object_id=self.fb_nativeid,
                         message="test_message")

        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/facebook/comment', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(FB_REQUESTS) == 1)
        self.assertEqual(FB_REQUESTS[0], (('facebook_post_id/comments',), {'post_args': {'message': 'test_message'}}))


    def test_wall_post(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         target_id=self.fb_nativeid,
                         message="test_message")
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/facebook/wall_post', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(FB_OBJECTS) == 1)
        self.assertTrue(len(FB_REQUESTS) == 0)
        self.assertEqual(FB_OBJECTS[0], ('put_wall_post', ('test_message',), {'attachment': {},
                                                                              'profile_id': self.fb_nativeid}))

    def test_delete_object(self):
        wrapped = dict(type="status", source_id="fakeid", source_type="page", page_id="12345")
        fb = dict(_wrapped_data=wrapped, facebook_post_id="12345_54321")
        post = self._create_db_post(content='Test fb post',
                                    channel=self.channel, facebook=fb)
        post.extra_fields = dict(facebook=dict(_wrapped_data=dict(source_type='Page',
                                                                  source_id='sourceid')))
        post._native_id = 'test_profile_id'
        post.save()
        self.channel.facebook_pages = [dict(id='sourceid',
                                            access_token='dummy_token')]
        self.channel.save()

        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         target_id='test_profile_id')
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/facebook/delete_object', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(FB_OBJECTS) == 1)
        self.assertTrue(len(FB_REQUESTS) == 0)
        self.assertEqual(FB_OBJECTS[0], ('delete_object', (u'test_profile_id',), {}))

    def test_get_channel_user(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id))
        data = json.dumps(post_data)

        def _fetch_channel_user():
            resp = self.client.get(get_api_url('commands/facebook/get_channel_user', version='v2.0'),
                                   data=data,
                                   content_type='application/json',
                                   base_url='https://localhost')
            self.assertEqual(resp.status_code, 200)
            # FB_REQUESTS should not change on repeated calls
            self.assertFalse(FB_OBJECTS)
            self.assertTrue(len(FB_REQUESTS) == 1)
            self.assertEqual(FB_REQUESTS[0], (('/me',), {}))

        _fetch_channel_user()
        # another calls to test caching
        _fetch_channel_user()
        _fetch_channel_user()

        # test FacebookUserMixin
        self.channel.facebook_access_token = 'test'
        fb_user_before = self.channel.facebook_me(force=True)
        self.assertTrue(len(FB_REQUESTS) == 2)
        fb_user_after = self.channel.facebook_me()
        self.assertTrue(len(FB_REQUESTS) == 2)
        self.assertEqual(fb_user_before, fb_user_after)

    def test_get_channel_description(self):
        service_channel_1 = self.channel
        service_channel_2 = FacebookServiceChannel.objects.create_by_user(self.user, title='FSC2')
        service_channel_1.dispatch_channel = self.efc
        service_channel_1.save()
        service_channel_1.channel_description = {"pages": [111], "id": str(service_channel_1.id)}
        service_channel_2.dispatch_channel = self.efc
        service_channel_2.save()
        service_channel_2.channel_description = {"pages": [222], "id": str(service_channel_2.id)}
        service_channel_3 = FacebookServiceChannel.objects.create_by_user(
            self.user, title='FSC3',
            facebook_access_token='test',
            facebook_page_ids=["333"],
            tracked_fb_event_ids=["444"])

        def _fetch_channel_description(channel, expected_objects=()):
            del FB_REQUESTS[:]
            del FB_OBJECTS[:]
            token = self.get_token()
            post_data = dict(token=token,
                             channel=str(channel.id))
            data = json.dumps(post_data)
            resp = self.client.get(
                get_api_url('commands/facebook/get_channel_description', version='v2.0'),
                data=data,
                content_type='application/json',
                base_url='https://localhost')
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(tuple([obj[0][0] for obj in FB_OBJECTS]), expected_objects)
            resp = json.loads(resp.data)
            self.assertTrue(resp['ok'])
            return resp['item']

        description1 = _fetch_channel_description(service_channel_1)
        description2 = _fetch_channel_description(service_channel_2)
        self.assertEqual(description1['id'], str(service_channel_1.id))
        self.assertEqual(description2['id'], str(service_channel_2.id))

        description3 = _fetch_channel_description(
            service_channel_3,
            expected_objects=('me', 'me/picture', '333', '333/picture', '444', '444/picture'))
        expected_description = {
            u'events': [{u'id': u'444', u'pic_url': None}],
            u'pages': [{u'id': u'333', u'pic_url': None}],
            u'user': {u'id': u'me', u'pic_url': None}}
        self.assertEqual(description3, expected_description)

        # subsequent call should return cached value
        description3 = _fetch_channel_description(service_channel_3)
        self.assertEqual(description3, expected_description)
