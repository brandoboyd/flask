import json
from collections import namedtuple
import unittest
from solariat_bottle.tests.social.twitter_helpers import FakeTwitterAPI
from solariat.tests.base import LoggerInterceptor

from solariat_bottle.app import get_api_url
from solariat_bottle.db.account import Account, AccountType
from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel, TwitterServiceChannel
from solariat_bottle.db.roles import ADMIN, AGENT, ANALYST
from solariat_bottle.db.user_profiles.social_profile import SocialProfile as UserProfile
from solariat_bottle.tests.base import RestCase
from solariat_bottle.tasks import twitter


class _TwitterAPI(FakeTwitterAPI):
    screen_name = 'solariatc'
    users = {
        '387209151': 'solariatc',
        '1411050992': 'user1_solariat',
        '1411081099': 'user2_solariat'
    }
    calls_count = 0

    def __init__(self):
        super(_TwitterAPI, self).__init__()
        user = self.get_user(screen_name=self.screen_name)
        FakeAuth = namedtuple('Auth', ['access_token', 'access_token_secret'])
        self.auth = FakeAuth('token', 'secret')
        self._setup(self.screen_name, user.followers_count, user.friends_count)

    def show_friendship(self, target_id=None, target_screen_name=None):
        _TwitterAPI.calls_count += 1
        screen_name = str(target_screen_name or target_id)
        if screen_name in self.users:
            screen_name = self.users[screen_name]
        brand = self.get_user(screen_name=self.screen_name)
        brand.following = False  # screen_name in self.friends()[0]
        brand.followed_by = False  # screen_name in self.followers()[0]
        user = self.get_user(screen_name=screen_name)
        user.following = brand.followed_by
        user.followed_by = brand.following
        return brand, user

    def get_user(self, screen_name):
        if screen_name in self.users:
            profile_data = super(_TwitterAPI, self).get_user(self.users[screen_name])
            profile_data['id'] = profile_data['id_str'] = screen_name
            return profile_data
        return super(_TwitterAPI, self).get_user(screen_name)

    def followers(self, *args, **kwargs):
        _TwitterAPI.calls_count += 1
        return super(_TwitterAPI, self).followers(*args, **kwargs)

    def friends(self, *args, **kwargs):
        _TwitterAPI.calls_count += 1
        return super(_TwitterAPI, self).friends(*args, **kwargs)

    def followers_ids(self, *args, **kwargs):
        items, cursor = self.followers(*args, **kwargs)
        return [x['id'] for x in items], cursor

    def friends_ids(self, *args, **kwargs):
        items, cursor = self.friends(*args, **kwargs)
        return [x['id'] for x in items], cursor


class TwitterCommandsTest(RestCase):

    def _count_message(self, message, logs):
        count = 0
        for log_entry in logs:
            if message in log_entry.msg:
                count += 1
        return count

    def setUp(self):
        self.stored_twitter_api = twitter.get_twitter_api
        twitter.get_twitter_api = lambda *args, **kwargs: _TwitterAPI()

        super(TwitterCommandsTest, self).setUp()

        from solariat_bottle.scripts.set_account_types import main
        main('local')

        self.email = "admin_benchmark@solariat.com"
        self.password = 'password'
        self.account = Account.objects.create(name="Search-Account")
        self.user = self._create_db_user(email=self.email, password=self.password, account=self.account,
                                         roles=[ADMIN, AGENT, ANALYST])
        self.etc = EnterpriseTwitterChannel.objects.create_by_user(
            self.user, title="TOC",
            twitter_handle='solariatc',
            twitter_handle_data={'hash': hash("testtest") & (1 << 8),
                                 'profile': {'id_str': '387209151',
                                             'screen_name': 'solariatc'}},
            status='Active')
        account_type = AccountType.objects.get(name=self.etc.account.account_type)
        self.etc.access_token_key = 'test' # account_type.twitter_access_token_key
        self.etc.access_token_secret = 'test' # account_type.twitter_access_token_secret
        self.etc.save()
        self.channel = TwitterServiceChannel.objects.create_by_user(self.user, title="TSC", status='Active')
        self.user.set_outbound_channel(self.etc)

    def tearDown(self):
        twitter.get_twitter_api = self.stored_twitter_api

    def rpc(self, path, **kw):
        resp = self.client.get(
            get_api_url(path, version='v2.0'),
            data=json.dumps(kw),
            content_type='application/json',
            base_url='https://localhost')
        self.assertEqual(resp.status_code, 200, msg="HTTP code %s: %s" % (resp.status_code, resp.data))
        return json.loads(resp.data)['item']

    def test_get_channel_user(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id))
        try:
            UserProfile.objects.get(user_name='solariatc')
            self.fail("Should be no user profile at this point.")
        except UserProfile.DoesNotExist:
            pass
        with LoggerInterceptor() as logs:
            u_p = self.rpc('commands/twitter/channel_user', **post_data)
            self.assertEqual(self._count_message('Did not find channel user for channel_id=', logs), 1)
            self.assertEqual(u_p["screen_name"], "solariatc")
            try:
                UserProfile.objects.get(user_name='solariatc')
            except UserProfile.DoesNotExist:
                self.fail("User profile should have been cached by the channel_user call.")

            new_u_p = self.rpc('commands/twitter/channel_user', **post_data)
            self.assertEqual(self._count_message('Did not find channel user for channel_id=', logs), 1)

            self.assertDictEqual(new_u_p, u_p)

    def test_get_user_info(self):
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         user_id='1411081099')  # This is id for user2_solariat
        try:
            UserProfile.objects.get(user_name='user2_solariat')
            UserProfile.objects.get(id='1411081099:0')
            self.fail("Should be no user profile at this point.")
        except UserProfile.DoesNotExist:
            pass

        with LoggerInterceptor() as logs:
            u_p = self.rpc('commands/twitter/user_info', **post_data)
            self.assertEqual(self._count_message(' in db. Fetching from twitter', logs), 1)
            self.assertEqual(u_p["screen_name"], "user2_solariat")
            try:
                UserProfile.objects.get(user_name='user2_solariat')
                UserProfile.objects.get(id='1411081099:0')
            except UserProfile.DoesNotExist:
                self.fail("User profile should have been cached by the channel_user call.")

            new_u_p = self.rpc('commands/twitter/user_info', **post_data)
            self.assertDictEqual(new_u_p, u_p)
            self.assertTrue(self._count_message(' in db. Fetching from twitter', logs) >= 1)

            post_data = dict(token=token,
                             channel=str(self.channel.id),
                             user_id='1411050992')  # This is id for user1_solariat
            self.rpc('commands/twitter/user_info', **post_data)
            try:
                UserProfile.objects.get(user_name='user1_solariat')
                UserProfile.objects.get(id='1411050992:0')
            except UserProfile.DoesNotExist:
                self.fail("User profile should have been cached by the channel_user call.")
            self.assertTrue(self._count_message(' in db. Fetching from twitter', logs) >= 2)

    def test_get_friend_info(self):
        _TwitterAPI.calls_count = 0
        token = self.get_token()
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         user_profile='1411081099')  # This is id for user2_solariat
        try:
            UserProfile.objects.get(user_name='user2_solariat')
            self.fail("Should be no user profile at this point.")
        except UserProfile.DoesNotExist:
            pass

        u_p = self.rpc('commands/twitter/is_friend', **post_data)
        self.assertEqual(_TwitterAPI.calls_count, 1)

        self.assertFalse(u_p)
        try:
            UserProfile.objects.get(user_name='user2_solariat')
        except UserProfile.DoesNotExist:
            self.fail("User profile should have been cached by the channel_user call.")

        new_u_p = self.rpc('commands/twitter/is_friend', **post_data)
        self.assertEqual(new_u_p, u_p)
        self.assertEqual(_TwitterAPI.calls_count, 1, 'Cached value must be used')

        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         user_profile='1411050992')  # This is id for user1_solariat
        self.rpc('commands/twitter/is_friend', **post_data)
        try:
            UserProfile.objects.get(user_name='user1_solariat')
        except UserProfile.DoesNotExist:
            self.fail("User profile should have been cached by the channel_user call.")
        self.assertEqual(_TwitterAPI.calls_count, 2)

    def test_get_friends_followers_cached(self):
        from solariat_bottle.tasks.twitter import get_twitter_api
        _TwitterAPI.calls_count = 0
        token = self.get_token()

        api = get_twitter_api(self.etc)
        solariatc_twitter = api.get_user(screen_name='solariatc')

        # fetch friends
        post_data = dict(token=token,
                         channel=str(self.channel.id),
                         user_id=solariatc_twitter.id)

        # this call should cache friends
        friends_from_twitter = self.rpc('commands/twitter/get_friends_list', **post_data)
        self.assertEqual(_TwitterAPI.calls_count, 1)

        # consequent call should use cached friends list
        friends_from_user_cache = self.rpc('commands/twitter/get_friends_list', **post_data)
        self.assertEqual(set(x['screen_name'] for x in friends_from_twitter),
                         set(x['screen_name'] for x in friends_from_user_cache))
        self.assertEqual(_TwitterAPI.calls_count, 1, 'Cached value must be used')


        friends_ids = set(u['id'] for u in friends_from_user_cache)
        # and cached friend ids list
        friend_ids_from_user_profile = self.rpc('commands/twitter/get_friends', **post_data)
        self.assertEqual(set(friend_ids_from_user_profile), friends_ids)
        self.assertEqual(_TwitterAPI.calls_count, 2)

        # test followers
        post_data.update(user_id='1411050992')  # user1_solariat
        self.rpc('commands/twitter/get_followers', **post_data)
        self.assertEqual(_TwitterAPI.calls_count, 3)

        # consequent call should use cached friends list
        self.rpc('commands/twitter/get_followers', **post_data)
        self.assertEqual(_TwitterAPI.calls_count, 3, 'Cached value must be used')
