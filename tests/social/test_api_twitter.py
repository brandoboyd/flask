import json
import mock
import tweepy
from mock import patch

from solariat_bottle.app import get_api_url, app
from solariat_bottle.db.account import Account
from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel, TwitterServiceChannel
from solariat_bottle.db.roles import ADMIN, AGENT, ANALYST
from solariat_bottle.db.user_profiles.social_profile import SocialProfile
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.tests.base import RestCase


LOGGED_ACTIONS = []


class MockResponse(object):
    def __init__(self, id_str, screen_name):
        self.id_str = id_str
        self.screen_name = screen_name


class FakeTwitterAPI(object):

    def __init__(self, auth_handler=None, host='api.twitter.com', search_host='search.twitter.com',
                 cache=None, secure=True, api_root='/1.1', search_root='', retry_count=0, retry_delay=0,
                 retry_errors=None, parser=None):
        self.auth = auth_handler
        self.host = host
        self.search_host = search_host
        self.api_root = api_root
        self.search_root = search_root
        self.cache = cache
        self.secure = secure
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_errors = retry_errors
        self.parser = parser
        self.wait_on_rate_limit = False
        self.wait_on_rate_limit_notify = False

    def __getattr__(self, item):
        raise NotImplementedError("Twitter Mock API does not expose %s" % item)

    def me(self):
        return
    def update_status(self, *args, **kwargs):
        # Just blindly return status
        LOGGED_ACTIONS.append(('update_status', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def media_upload(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('media_upload', args, kwargs))
        arg = args[0] if args else kwargs.items()[0] if kwargs else None
        return {
            "media_id": hash(arg) & 0xFFFF,
            "media_id_string": str(hash(arg) & 0xFFFF),
        }

    def update_with_media(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('update_with_media', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def send_direct_message(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('send_direct_message', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def retweet(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('retweet', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def create_friendship(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('create_friendship', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def destroy_friendship(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('destroy_friendship', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def show_friendship(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('show_friendship', args, kwargs))
        str_val = str(args[0]) if args else str(kwargs.items()[0]) if kwargs else None

        result = MockResponse(str_val, str_val)
        return result, result

    def destroy_status(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('destroy_status', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def destroy_direct_message(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('destroy_direct_message', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def create_favorite(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('create_favorite', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None

    def destroy_favorite(self, *args, **kwargs):
        LOGGED_ACTIONS.append(('destroy_favorite', args, kwargs))
        return args[0] if args else kwargs.items()[0] if kwargs else None


class TwitterCommandsTest(RestCase):
    patched_tweepy_api = mock.patch("tweepy.API", side_effect=FakeTwitterAPI)
    patched_tweepy_ext_api = mock.patch("solariat_bottle.utils.tweet.TwitterApiExt", side_effect=FakeTwitterAPI)

    def setUp(self):
        super(TwitterCommandsTest, self).setUp()
        self.email = "admin_benchmark@solariat.com"
        self.password = 'password'
        self.account = Account.objects.create(name="Search-Account")
        self.user = self._create_db_user(email=self.email, password=self.password, account=self.account,
                                         roles=[ADMIN, AGENT, ANALYST])
        del LOGGED_ACTIONS[:]
        self.patched_tweepy_api.start()
        self.patched_tweepy_ext_api.start()
        self.efc = EnterpriseTwitterChannel.objects.create_by_user(
            self.user, title="TOC",
            twitter_handle='test_handle',
            twitter_handle_data={'hash': hash("testtest") & (1 << 8),
                                 'profile': {'id_str': 'test_handle', 'screen_name': 'test_handle'}},
            status='Active')
        self.efc.access_token_key = 'test'
        self.efc.access_token_secret = 'test'
        self.efc.save()
        self.channel = TwitterServiceChannel.objects.create_by_user(self.user, title="TSC", status='Active')
        self.user.set_outbound_channel(self.efc)

    def tearDown(self):
        super(TwitterCommandsTest, self).tearDown()
        self.patched_tweepy_api.stop()
        self.patched_tweepy_ext_api.stop()

    def test_update_status(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         status="This is some test api status")
        data = json.dumps(post_data)
        resp = self.client.post(
            get_api_url('commands/twitter/update_status', version='v2.0'),
            data=data,
            content_type='application/json',
            base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(LOGGED_ACTIONS) == 1)
        self.assertEqual(LOGGED_ACTIONS[0], ('update_status', (),
                                             {'status': u'This is some test api status',
                                              'in_reply_to_status_id': None}))

    def test_update_with_media(self):
        from StringIO import StringIO as FileBuffer

        token = self.get_token()
        status = 'This is some test api status with media'
        image = 'image content'
        file_obj = (FileBuffer(image), 'image.jpg')
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         status=status,
                         media=file_obj)
        resp = self.client.post(
            get_api_url('commands/twitter/update_with_media', version='v2.0'),
            buffered=True,
            content_type='multipart/form-data',
            data=post_data,
            base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(LOGGED_ACTIONS), 2)
        method_name, args, kwargs = LOGGED_ACTIONS[0]
        self.assertEqual(method_name, 'media_upload')
        self.assertEqual(args, (file_obj[1],))  # first argument to update_with_media is filename
        stream = kwargs['file']
        self.assertIsNotNone(stream)
        #self.assertEqual(stream.read(), image)
        self.assertNotIn('media', kwargs)

        method_name, args, kwargs = LOGGED_ACTIONS[1]
        self.assertEqual(method_name, 'update_status')
        self.assertEqual(status, kwargs['status'])
        self.assertIsNone(kwargs['in_reply_to_status_id'])

    def test_direct_message(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         status="This is some test api status",
                         screen_name='test_user')
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/twitter/direct_message', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(LOGGED_ACTIONS) == 1)
        self.assertEqual(LOGGED_ACTIONS[0], ('send_direct_message', (),
                                             {'screen_name': 'test_user',
                                              'text': 'This is some test api status'}))

    def test_retweet_message(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         status_id="test_status_id",
                         screen_name='test_user')
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/twitter/retweet_status', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(LOGGED_ACTIONS) == 1)
        self.assertEqual(LOGGED_ACTIONS[0], ('retweet', (), {'id': 'test_status_id'}))

    def test_follow_unfollow_user(self):
        # Create a user profile we can work with
        user_name = 'test_user'
        u_p = UserProfile.objects.upsert('Twitter',
                                         dict(user_name=user_name,
                                              user_id='12345678'))
        # First do a follow operation
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         user_profile=user_name)
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/twitter/follow_user', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(LOGGED_ACTIONS) == 0)   # In test mode we don't actually follow
        # The list of followers should be updated
        u_p.reload()
        self.assertEquals(u_p.followed_by_brands, [SocialProfile.make_id('Twitter', self.efc.twitter_handle_id)])
        # Now do an unfollow
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         user_profile=user_name)
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/twitter/unfollow_user', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(LOGGED_ACTIONS) == 0)   # In test mode we don't actually follow
        # List should be empty again
        u_p.reload()
        self.assertTrue(u_p.followed_by_brands == [])

    def test_auth_media(self):
        import requests
        from solariat_bottle.tests.social.test_twitter_rate_limits import fake_download_media_success_response

        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         media_url="https://ton.twitter.com/1.1/ton/data/dm/5/5/q.png",
                         data_uri=True)
        data = json.dumps(post_data)

        with patch.object(requests, 'get') as mock:
            mock.return_value = fake_download_media_success_response()
            resp = self.client.get(get_api_url('commands/twitter/auth_media', version='v2.0'),
                                   data=data,
                                   content_type='application/json',
                                   base_url='https://localhost')
            self.assertEqual(mock.call_count, 1, "Must have been called once")
            self.assertEqual(mock.call_args[0][0], post_data['media_url'])
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertIn('item', resp)
        self.assertIn('media_data', resp['item'])
        self.assertIn('twitter_response_headers', resp['item'])

    @patch("requests.adapters.HTTPAdapter.proxy_manager_for")
    @patch("requests.adapters.PoolManager.connection_from_url")
    def test_auth_media_through_proxy(self, patched_connection_from_url, patched_proxy_manager_for):
        """Tests that requests.adapters.HTTPAdapter.get_connection chooses
        the correct connection to proxy for both http and https urls.
        """
        proxied_media_urls = [
            "http://pbs.twimg.com/media/made_up.jpg",
            "https://ton.twitter.com/1.1/ton/data/dm/5/5/made_up.png"
        ]

        ORIGINAL_PROXIES = app.config.get('PROXIES', {})
        PROXIES = {'https': 'badproxytest'}
        app.config['PROXIES'] = PROXIES
        from solariat.utils.http_proxy import enable_proxy, disable_proxy
        disable_proxy()
        enable_proxy(settings=app.config)

        def raise_exception(error_message):
            class ExpectedTestException(Exception):
                pass

            def _effect(*args, **kwargs):
                raise ExpectedTestException(error_message)
            return _effect

        patched_connection_from_url.side_effect = raise_exception('no')
        patched_proxy_manager_for.side_effect = raise_exception('proxy')

        for media_url in proxied_media_urls:
            token = self.get_token()
            post_data = dict(token=token,
                             channel=str(self.channel.id),
                             media_url=media_url,
                             data_uri=True)
            data = json.dumps(post_data)
            with self.assertRaises(Exception) as ctx:
                resp = self.client.get(get_api_url('commands/twitter/auth_media', version='v2.0'),
                                       data=data,
                                       content_type='application/json',
                                       base_url='https://localhost')
                self.assertEqual(str(ctx.exception), "proxy")

            patched_connection_from_url.assert_not_called()
            self.assertEqual(patched_proxy_manager_for.call_count, 1)
            self.assertEqual(patched_proxy_manager_for.call_args[0][0], 'http://' + PROXIES['https'])

            patched_proxy_manager_for.reset_mock()
        app.config['PROXIES'] = ORIGINAL_PROXIES

    def test_destroy_status(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         object_id="test_status_id",
                         message_type="Status")
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/twitter/destroy_message', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(LOGGED_ACTIONS) == 1)
        self.assertEqual(LOGGED_ACTIONS[0], ('destroy_status', (), {'id': u'test_status_id'}))

        post_data['message_type'] = "DirectMessage"
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/twitter/destroy_message', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(LOGGED_ACTIONS) == 2)
        self.assertEqual(LOGGED_ACTIONS[1], ('destroy_direct_message', (), {'id': u'test_status_id'}))

    def test_create_favorite(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         object_id="test_status_id")
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/twitter/create_favorite', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(LOGGED_ACTIONS) == 1)
        self.assertEqual(LOGGED_ACTIONS[0], ('create_favorite', (), {'id': u'test_status_id'}))

    def test_destroy_favorite(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         object_id="test_status_id")
        data = json.dumps(post_data)
        resp = self.client.get(get_api_url('commands/twitter/destroy_favorite', version='v2.0'),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(LOGGED_ACTIONS) == 1)
        self.assertEqual(LOGGED_ACTIONS[0], ('destroy_favorite', (), {'id': u'test_status_id'}))

