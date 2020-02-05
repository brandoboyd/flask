# coding=utf-8
import json
import time
from solariat_bottle.daemons.feedapi import RequestsClient

from solariat_bottle.tests.base import BaseCase

from solariat_bottle.daemons.datasift.datasift_bot import DatasiftBot
from solariat_bottle.daemons.helpers import FeedApiPostCreator
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.post.base import Post
from solariat_bottle.db.user_profiles.social_profile import SocialProfile as UserProfile
from solariat.utils.timeslot import now, datetime_to_timestamp_ms
from solariat.utils.iterfu import flatten
from solariat_bottle.db.post.twitter import datetime_to_string

# This is an example of valid data as received from datasift
SAMPLE_VALID_DATA = {"hash": "799d14355017b948fadd78fa259b5007",
                     "data": {"interaction": {"schema": {"version": 3},
                                              "source": "Twitter Web Client",
                                              "author": {"username": "user1_solariat",
                                                         "name": "user1_solariat",
                                                         "id": 1411050992,
                                                         "avatar": "http://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg",
                                                         "link": "https://twitter.com/user1_solariat",
                                                         "language": "en"},
                                              "type": "twitter",
                                              "created_at": "Tue, 08 Jul 2014 12:24:58 +0000",
                                              "received_at": 1404822299.0200000,
                                              "content": "@solariat_brand can you help with my laptop problems?",
                                              "id": "1e4069adff40a900e074bdc6611b07fa",
                                              "link": "https://twitter.com/user1_solariat/status/486486097535721472",
                                              "mentions": ["solariat_brand"],
                                              "mention_ids": [1411000506]},
                              "klout": {"score": 17},
                              "language": {"tag": "en",
                                           "tag_extended": "en",
                                           "confidence": 97},
                              "salience": {"content": {"sentiment": 0}},
                              "twitter": {"created_at": "Tue, 08 Jul 2014 12:24:58 +0000",
                                          "filter_level": "medium",
                                          "id": "486486097535721472",
                                          "in_reply_to_screen_name": "solariat_brand",
                                          "in_reply_to_user_id": "1411000506",
                                          "lang": "en",
                                          "mention_ids": [1411000506],
                                          "mentions": ["solariat_brand"],
                                          "source": "<a href=\"http://twitter.com\" rel=\"nofollow\">Twitter Web Client</a>",
                                          "text": "@solariat_brand can you help with my laptop problems?",
                                          "user": {"name": "user1_solariat",
                                                   "url": "http://www.web.com",
                                                   "description": "Teacher",
                                                   "location": "San Francisco",
                                                   "statuses_count": 1905,
                                                   "followers_count": 8,
                                                   "friends_count": 13,
                                                   "screen_name": "user1_solariat",
                                                   "profile_image_url": "http://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg",
                                                   "profile_image_url_https": "https://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg",
                                                   "lang": "en",
                                                   "listed_count": 0,
                                                   "id": 1411050992,
                                                   "id_str": "1411050992",
                                                   "geo_enabled": False,
                                                   "verified": False,
                                                   "favourites_count": 1,
                                                   "created_at": "Tue, 07 May 2013 19:35:50 +0000"}
                              }
                     }
}


def patch_created_at(data, created_at=None):
    import copy

    if not created_at:
        created_at = now()

    res = copy.deepcopy(data)
    delta = datetime_to_timestamp_ms(created_at)
    res["data"]["twitter"]["created_at"] = datetime_to_string(created_at) # "Tue, 08 Jul 2014 12:24:58 +0000"
    res["data"]["twitter"]["id"] = str(long(res["data"]["twitter"]["id"]) + delta)
    return res


MAX_TIMEOUT = 1000
json_lib = json

from solariat_bottle.app import app

class TestClient(RequestsClient):
    def __init__(self, username, password):
        self.client = app.test_client()
        class Options(dict):
            __getattr__ = dict.__getitem__
        self.options = Options(username=username, password=password, url='')
        self.user_agent = 'TestAgent'
        self.sleep_timeout = 1

    def post(self, url, data=None, json=None, **kwargs):
        from solariat_bottle.daemons.exc import ApplicationError, FeedAPIError, \
            InfrastructureError, UnauthorizedRequestError

        if json is not None:
            data = json_lib.dumps(json)

        app.logger.debug("POST {} {} {} {}".format(url, data, json, kwargs))
        resp = self.client.post(
            url,
            data=data,
            content_type="application/json",
            base_url='https://localhost')

        if resp.status_code == 401:
            raise UnauthorizedRequestError(resp.data)

        if resp.status_code != 200:
            raise InfrastructureError(u"HTTP status: {} Response: {}".format(
                resp.status_code, resp.data))

        data = json_lib.loads(resp.data)
        if not data.get('ok'):
            raise ApplicationError(data.get('error', 'Unknown Error'))
        return data


class DatasiftBotTest(BaseCase):
    def setUp(self):
        super(DatasiftBotTest, self).setUp()
        self.setup_channel()

    def start_bot(self, ds_bot):
        ds_bot.start()

        for idx in xrange(MAX_TIMEOUT):
            time.sleep(1)
            if ds_bot.is_running():
                break
        else:
            self.fail("Bot never got started after waiting %s seconds." % MAX_TIMEOUT)

    def wait_bot(self, ds_bot):
        for idx in xrange(MAX_TIMEOUT):
            time.sleep(1)
            if not (ds_bot.is_busy() or ds_bot.is_blocked()):
                break
        else:
            self.fail("Post processing did not finish after waiting %s seconds" % MAX_TIMEOUT)

    def stop_bot(self, ds_bot):
        ds_bot.stop()

        for idx in xrange(MAX_TIMEOUT * 4):
            time.sleep(1)
            if not ds_bot.isAlive():
                break
        else:
            self.fail("Bot never stopped after waiting %s seconds." % (4 * MAX_TIMEOUT))

    def run_it(self, ds_bot):
        try:
            self._do_test(ds_bot)
        finally:
            self.stop_bot(ds_bot)

    def setup_channel(self):
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='TW_INB')
        channel.add_username('solariat_brand')
        channel.add_username('@solariat_brand')
        channel.add_keyword('laptop problems')
        channel.on_active()
        self.channel = channel
        return self.channel

    def _do_test(self, ds_bot, posts_before=0):
        self.assertEqual(Post.objects.count(), posts_before)

        if not ds_bot.is_running():
            self.start_bot(ds_bot)

        post_data = patch_created_at(SAMPLE_VALID_DATA, now())
        ds_bot.post_received(json.dumps(post_data))
        self.wait_bot(ds_bot)

        self.assertEqual(Post.objects.count(), posts_before + 1)
        created_post = Post.objects().sort(_created=-1).limit(1)[0]
        u_p = UserProfile.objects.get(user_name='user1_solariat')
        # Check fields that are required on user profile
        self.assertDictEqual(u_p.platform_data, {u'lang': u'en',
                                                 u'statuses_count': 1905,
                                                 u'screen_name': u'user1_solariat',
                                                 u'friends_count': 13,
                                                 u'name': u'user1_solariat',
                                                 u'created_at': u'Tue, 07 May 2013 19:35:50 +0000',
                                                 u'profile_image_url': u'http://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg',
                                                 u'id': 1411050992,
                                                 u'followers_count': 8,
                                                 u'id_str': u'1411050992',
                                                 u'location': u'San Francisco',
                                                 u'profile_image_url_https': u'https://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg',
                                                 u'description': u'Teacher'})
        self.assertEqual(created_post.content, post_data['data']['twitter']['text'])
        self.assertTrue(str(self.channel.inbound_channel.id) in created_post.channel_assignments)
        self.assertEqual(created_post.channel_assignments[str(self.channel.inbound_channel.id)], 'highlighted')
        # Check that we actually hold everything in wrapped data
        print(created_post.wrapped_data)
        print(post_data['data'])
        self.assertDictEqual(created_post.wrapped_data, post_data['data'])

    def test_one_post_happy_flow(self):
        """ Just a basic test of the main flow. Start a datasift bot, pass it some datasift data that
        would get matched in our system, check that it's actually created and matched properly. """
        self.run_it(DatasiftBot(
            username=self.user.email,
            ds_login='dummy_login',
            ds_api_key='dummy_api_key',
            lockfile='ds_bot_test_lockfile',
            concurrency=2))

    def test_feed_api_post_creator(self):
        from solariat_bottle.daemons.feedapi import FeedApiThread

        password = 'password'
        self.user.is_superuser = True
        self.user.set_password(password)
        FeedApiThread.client = TestClient(self.user.email, password)
        bot = DatasiftBot(username=self.user.email,
                          ds_login='dummy_login',
                          ds_api_key='dummy_api_key',
                          lockfile='ds_bot_test_lockfile',
                          concurrency=2,
                          password=password,
                          url='', # for test client base url remains empty
                          post_creator=FeedApiPostCreator)
        self.run_it(bot)

    def test_auth_token_expiration(self):
        from solariat_bottle.daemons.feedapi import FeedApiThread

        password = 'password'
        self.user.is_superuser = True
        self.user.set_password(password)
        FeedApiThread.client = TestClient(self.user.email, password)
        bot = DatasiftBot(username=self.user.email,
                          ds_login='dummy_login',
                          ds_api_key='dummy_api_key',
                          lockfile='ds_bot_test_lockfile',
                          concurrency=2,
                          password=password,
                          url='', # for test client base url remains empty
                          post_creator=FeedApiPostCreator)
        try:
            self.start_bot(bot)
            self._do_test(bot)
            # now expire auth tokens
            from solariat_bottle.db.api_auth import AuthToken
            AuthToken.objects.remove()
            self._do_test(bot, posts_before=1)
            AuthToken.objects.remove()
            self._do_test(bot, posts_before=2)
            self._do_test(bot, posts_before=3)
        finally:
            self.stop_bot(bot)


class TestDatasiftSync(BaseCase):
    def create_channel(self, data):
        title, keywords, skipwords, usernames = data
        ch = TwitterServiceChannel.objects.create(title=title)
        for kwd in keywords:
            ch.add_keyword(kwd)
        for skwd in skipwords:
            ch.add_skipword(skwd)
        for u in usernames:
            ch.add_username(u)
        return ch

    def setup_channels(self, data):
        return map(self.create_channel, data)

    def test_csdl_generator(self):
        from solariat_bottle.scripts.datasift_sync2 import get_csdl_data, generate_csdl

        db_data = [
            ('Channel A', [u'en__laptop', u'es__portátil'], [], ['@user_a']),
            ('Channel B', [u'en__laptop', u'es__laptop', u'es__portátil', 'laptop bag'], [u'bag'], ['@user_b1', '@user_b2']),
            ('Channel C', [u'keyword_c'], [], ['user_c1', '@user_c2']),
            ('Channel D', ['laptop bag'], ['bag', 'something else'], ['user_a']),
            ('Channel E', ['keyword_e'], ['bag', 'something else', 'skip_e'], [])
        ]
        channels = self.setup_channels(db_data)
        subchannels = lambda *idx: list(flatten((c.inbound_channel, c.outbound_channel) for c in [channels[i] for i in idx]))

        def csdl_data_channel(*idx):
            data = get_csdl_data(subchannels(*idx))
            unames, _, ks = data
            if len(idx) == 1:
                return unames, ks[0][0], ks[0][1]
            else:
                return unames, tuple(", ".join(k) + " | " + ", ".join(s) for (k, s) in ks)

        def csdl_string_channel(*idx):
            data = get_csdl_data(subchannels(*idx))
            csdl_string = generate_csdl(*data)
            # bypass language query
            return csdl_string.split(' AND ', 1)[1]

        from solariat_bottle.db.tracking import PostFilterEntry
        assert PostFilterEntry.objects.count() > 1
        print list(PostFilterEntry.objects.coll.find())

        self.assertEqual(
            csdl_data_channel(0),
            (('user_a',), ('@user_a', 'laptop', u'portátil'.encode('utf-8')), ())
        )
        self.assertEqual(
            csdl_data_channel(1),
            (('user_b1', 'user_b2'),
             ('@user_b1', '@user_b2', 'laptop', 'laptop bag', u'portátil'.encode('utf-8')),
             (u'bag',))
        )
        self.assertEqual(
            csdl_data_channel(2),
            (('user_c1', 'user_c2'), ('@user_c1', '@user_c2', 'keyword_c'), ())
        )

        self.assertEqual(
            csdl_data_channel(0, 1),
            (('user_a', 'user_b1', 'user_b2'),
             ('@user_a, laptop, portátil | ',
              '@user_b1, @user_b2, laptop bag | bag'))
        )

        all_channels = \
            (('user_a', 'user_b1', 'user_b2', 'user_c1', 'user_c2'),
             ('@user_a, @user_c1, @user_c2, keyword_c, laptop, portátil | ',
              '@user_b1, @user_b2, laptop bag | bag'))
        self.assertEqual(
            csdl_data_channel(0, 1, 2),
            all_channels
        )
        # channel D should not change anything
        self.assertEqual(
            csdl_data_channel(0, 1, 2, 3),
            all_channels
        )
        self.assertEqual(
            csdl_data_channel(3),
            (('user_a',),
             ('@user_a', 'laptop bag'),
             ('bag', 'something else'))
        )

        # tests skips are not omitted for channel with no common keywords
        self.assertEqual(
            csdl_data_channel(4),
            (tuple([]),
             ('keyword_e',),
             ('bag', 'skip_e', 'something else'))
        )

        self.assertEqual(
            csdl_data_channel(0, 1, 2, 3, 4),
            tuple([
                all_channels[0], # same usernames
                all_channels[1] + ('keyword_e | bag, skip_e, something else',)])
        )

        self.assertEqual(
            csdl_string_channel(0, 1, 2, 3, 4),
            # usernames
            '( twitter.user.screen_name in "user_a,user_b1,user_b2,user_c1,user_c2" '
            'OR twitter.retweet.user.screen_name in "user_a,user_b1,user_b2,user_c1,user_c2" '
            'OR ( '
            # common keywords and mentions
            '( twitter.text contains_any "keyword_c,laptop,port\xc3\xa1til" '
            'OR twitter.mentions in "user_a,user_c1,user_c2" '
            'OR twitter.retweet.text contains_any "keyword_c,laptop,port\xc3\xa1til" '
            'OR twitter.retweet.mentions in "user_a,user_c1,user_c2" ) '
            ') OR ( '
            # Channel B specific query
            '( twitter.text contains_any "laptop bag" '
            'OR twitter.mentions in "user_b1,user_b2" '
            'OR twitter.retweet.text contains_any "laptop bag" '
            'OR twitter.retweet.mentions in "user_b1,user_b2" ) '
            'AND NOT ( twitter.text contains_any "bag" OR twitter.retweet.text contains_any "bag" ) '
            ') OR ( '
            # Channel E specific query
            '( twitter.text contains_any "keyword_e" '
            'OR twitter.retweet.text contains_any "keyword_e" ) '
            'AND NOT ( twitter.text contains_any "bag,skip_e,something else" OR twitter.retweet.text contains_any "bag,skip_e,something else" ) ) )'
        )
