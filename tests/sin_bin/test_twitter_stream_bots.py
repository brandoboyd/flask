import unittest
import json
from solariat.tests.base import LoggerInterceptor
import time
from solariat_bottle.daemons.twitter.parsers import parse_user_profile

sleep = lambda x: time.sleep(x)

from solariat_bottle.tests.base import BaseCase

from solariat_bottle.daemons.twitter.user_stream_bot import (
    UserStreamBot, UserStreamDbEvents)
from solariat_bottle.daemons.twitter.public_stream_bot import (
    PublicStreamBot, PublicStreamDbEvents)

from solariat_bottle.daemons.twitter.stream import test_utils
from solariat_bottle.db.channel.twitter import TwitterServiceChannel, EnterpriseTwitterChannel
from solariat_bottle.db.post.twitter import TwitterPost
from solariat_bottle.db.user_profiles.user_profile import UserProfile


def gen_twitter_user(screen_name):
    id_ = hash(screen_name) & 0xFFFFFFFF

    return {
        "lang": "en",
        "created_at": "Thu Aug 09 16:52:43 +0000 2012",
        "screen_name": screen_name,
        "profile_image_url_https": "https://abs.twimg.com/sticky/default_profile_images/default_profile_2_normal.png",
        "profile_image_url": "http://abs.twimg.com/sticky/default_profile_images/default_profile_2_normal.png",
        "time_zone": None,
        "utc_offset": None,
        "description": None,
        "location": None,
        "followers_count": id_ & 0xFF,
        "friends_count": id_ << 2 & 0xFF,
        "statuses_count": id_ << 4 & 0xFF,
        "id_str": str(id_),
        "id": id_,
        "name": screen_name.title()}


def get_user_profile(tw_json):
    from solariat_bottle.daemons.twitter.parsers import parse_user_profile
    try:
        return UserProfile.objects.get_by_platform('Twitter', tw_json['screen_name'])
    except UserProfile.DoesNotExist:
        return UserProfile.objects.upsert('Twitter', profile_data=parse_user_profile(tw_json))


VALID_DM_DATA = {"direct_message": {"id": 489374081880719360,
                                    "id_str": "489374081880719360",
                                    "text": "I am having some laptop problems, can you check?",
                                    "sender": {"id": 1411050992,
                                               "id_str": "1411050992",
                                               "name": "user1_solariat",
                                               "screen_name": "user1_solariat",
                                               "location": "San Francisco",
                                               "url": "http:\/\/www.web.com",
                                               "description": "Teacher",
                                               "protected": False,
                                               "followers_count": 8,
                                               "friends_count": 13,
                                               "listed_count": 0,
                                               "created_at": "Tue May 07 19:35:50 +0000 2013",
                                               "favourites_count": 1,
                                               "utc_offset": None,
                                               "time_zone": None,
                                               "geo_enabled": False,
                                               "verified": False,
                                               "statuses_count": 1943,
                                               "lang": "en",
                                               "contributors_enabled": False,
                                               "is_translator": False,
                                               "is_translation_enabled": False,
                                               "profile_background_color": "C0DEED",
                                               "profile_background_image_url": "http:\/\/abs.twimg.com\/images\/themes\/theme1\/bg.png",
                                               "profile_background_image_url_https": "https:\/\/abs.twimg.com\/images\/themes\/theme1\/bg.png",
                                               "profile_background_tile": False,
                                               "profile_image_url": "http:\/\/pbs.twimg.com\/profile_images\/468781442852339712\/69CJihsO_normal.jpeg",
                                               "profile_image_url_https": "https:\/\/pbs.twimg.com\/profile_images\/468781442852339712\/69CJihsO_normal.jpeg",
                                               "profile_link_color": "0084B4",
                                               "profile_sidebar_border_color": "C0DEED",
                                               "profile_sidebar_fill_color": "DDEEF6",
                                               "profile_text_color": "333333",
                                               "profile_use_background_image": True,
                                               "default_profile": True,
                                               "default_profile_image": False,
                                               "following": False,
                                               "follow_request_sent": False,
                                               "notifications": False},
                                    "sender_id": 1411050992,
                                    "sender_id_str": "1411050992",
                                    "sender_screen_name": "user1_solariat",
                                    "recipient": {"id": 1411000506,
                                                  "id_str": "1411000506",
                                                  "name": "solariat_brand",
                                                  "screen_name": "solariat_brand",
                                                  "location": None,
                                                  "url": None,
                                                  "description": None,
                                                  "protected": False,
                                                  "followers_count": 17,
                                                  "friends_count": 66,
                                                  "listed_count": 0,
                                                  "created_at": "Tue May 07 19:20:46 +0000 2013",
                                                  "favourites_count": 0,
                                                  "utc_offset": None,
                                                  "time_zone": None,
                                                  "geo_enabled": False,
                                                  "verified": False,
                                                  "statuses_count": 1057,
                                                  "lang": "en",
                                                  "contributors_enabled": False,
                                                  "is_translator": False,
                                                  "is_translation_enabled": False,
                                                  "profile_background_color": "C0DEED",
                                                  "profile_background_image_url": "http:\/\/abs.twimg.com\/images\/themes\/theme1\/bg.png",
                                                  "profile_background_image_url_https": "https:\/\/abs.twimg.com\/images\/themes\/theme1\/bg.png",
                                                  "profile_background_tile": False,
                                                  "profile_image_url": "http:\/\/abs.twimg.com\/sticky\/default_profile_images\/default_profile_6_normal.png",
                                                  "profile_image_url_https": "https:\/\/abs.twimg.com\/sticky\/default_profile_images\/default_profile_6_normal.png",
                                                  "profile_link_color": "0084B4",
                                                  "profile_sidebar_border_color": "C0DEED",
                                                  "profile_sidebar_fill_color": "DDEEF6",
                                                  "profile_text_color": "333333",
                                                  "profile_use_background_image": True,
                                                  "default_profile": True,
                                                  "default_profile_image": True,
                                                  "following": False,
                                                  "follow_request_sent": False,
                                                  "notifications":False},
                                    "recipient_id": 1411000506,
                                    "recipient_id_str": "1411000506",
                                    "recipient_screen_name": "solariat_brand",
                                    "created_at": "Wed Jul 16 11:40:47 +0000 2014",
                                    "entities": {"hashtags": [],
                                                 "symbols": [],
                                                 "urls": [],
                                                 "user_mentions": []}
                                    }
        }

MAX_TIMEOUT = 15


class BaseBotTest(BaseCase):
    def start_bot(self, tw_bot=None):
        tw_bot = tw_bot or self.tw_bot
        tw_bot.start()
        timeout = MAX_TIMEOUT
        sleep_time = 0.1

        while timeout > 0:
            if tw_bot.is_running():
                break
            else:
                sleep(sleep_time)
                timeout -= sleep_time
        else:
            self.fail("Bot never got started after waiting %s seconds." % MAX_TIMEOUT)

    def wait_bot(self, tw_bot=None, timeout=MAX_TIMEOUT):
        tw_bot = tw_bot or self.tw_bot
        sleep_time = 0.1
        while timeout > 0:
            if not (tw_bot.is_busy() or tw_bot.is_blocked()):
                break
            else:
                sleep(sleep_time)
                timeout -= sleep_time
        else:
            self.fail("Post processing did not finish after waiting %s seconds" % MAX_TIMEOUT)

    def stop_bot(self, tw_bot=None):
        tw_bot = tw_bot or self.tw_bot
        tw_bot.stop()

        timeout = MAX_TIMEOUT * 4
        sleep_time = 0.1
        while timeout > 0:
            if not tw_bot.isAlive():
                break
            else:
                sleep(sleep_time)
                timeout -= sleep_time
        else:
            self.fail("Bot never stopped after waiting %s seconds." % (4 * MAX_TIMEOUT))

    def sync_bot(self, tw_bot=None):
        tw_bot = tw_bot or self.tw_bot
        import signal
        tw_bot.signal(signal.SIGHUP)

    def send_event(self, event, *args, **kwargs):
        tw_bot = self.tw_bot
        server = tw_bot.server
        for greenlet in server.streams.values():
            test_connector = greenlet._stream.test_stream
            test_connector.send(event, *args, **kwargs)
            test_connector.next()

    def setup_outbound_channel(self, title='TestAccount', twitter_handle='test'):
        etc = EnterpriseTwitterChannel.objects.create_by_user(
            self.user, title=title,
            account=self.user.current_account)
        etc.twitter_handle = twitter_handle
        etc.on_active()
        etc.save()
        return etc

    def setup_channel(self, keywords=['test'], usernames=['test'], title='Test'):
        sc = TwitterServiceChannel.objects.create(account=self.user.current_account, title=title)
        for kwd in keywords:
            sc.add_keyword(kwd)
        for uname in usernames:
            sc.add_username(uname)
        self.sync_bot()
        return sc

    def assert_no_errors_in_logs(self, logs, allow_levels={'DEBUG', 'INFO'}):
        errors = [(log.levelname, log.message) for log in logs if log.levelname not in allow_levels]
        self.assertEqual(len(errors), 0, msg=errors)


class UserStreamBotTest(BaseBotTest):

    def setUp(self):
        super(UserStreamBotTest, self).setUp()
        #from solariat_bottle.daemons.twitter.twitter_bot_dm import UserStreamMulti as CurlUserStreamMulti
        MultiStreamCls = None  # CurlUserStreamMulti
        self.tw_bot = UserStreamBot(
            username=self.user.email,
            lockfile='tw_bot_test_lockfile',
            concurrency=2,
            heartbeat=1,
            stream_manager_cls=MultiStreamCls)

    def tearDown(self):
        self.stop_bot()

    def assert_tweet_data_stored(self, post):
        """Test the raw tweet data gets stored in Post.extra_fields['twitter']
        and UserProfile.platform_data
        """
        from solariat_bottle.daemons.twitter.parsers import TweetParser, TwitterUserParser

        expected_attrs = set(VALID_DM_DATA['direct_message']) & set(TweetParser.MIRROR_ATTRIBUTES)
        self.assertTrue(expected_attrs)

        for attr in expected_attrs:
            self.assertTrue(attr in post.native_data,
                            msg=u"%s not in %s" % (attr, post.native_data))

        up = post.get_user_profile()
        platform_data = up.platform_data

        expected_attrs = set(VALID_DM_DATA['direct_message']['sender']) & set(TwitterUserParser.MIRROR_ATTRIBUTES)
        self.assertTrue(expected_attrs)

        for attr in expected_attrs:
            self.assertTrue(attr in platform_data,
                            msg=u"%s not in %s" % (attr, platform_data))

    def post_received(self, *args, **kwargs):
        self.tw_bot.post_received(*args, **kwargs)
        self.wait_bot()

    def test_one_post_happy_flow(self):
        """ Just a basic test of the main flow. Start a datasift bot, pass it some datasift data that
        would get matched in our system, check that it's actually created and matched properly. """
        efc = EnterpriseTwitterChannel.objects.create_by_user(self.user, title='TW_OUTB',
                                                              account=self.user.current_account)
        efc.twitter_handle = 'solariat_brand'
        efc.save()
        efc.on_active()
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='TW_INB',
                                                               account=self.user.current_account)
        channel.add_username('solariat_brand')
        channel.add_username('@solariat_brand')
        channel.add_keyword('laptop problems')
        channel.on_active()

        outbound_check = EnterpriseTwitterChannel.objects(twitter_handle='solariat_brand',
                                                          status='Active',
                                                          account=self.user.current_account)[:]
        self.assertTrue(len(outbound_check) == 1)

        self.assertEqual(TwitterPost.objects.count(), 0)

        self.start_bot()
        self.post_received(json.dumps(VALID_DM_DATA))
        self.wait_bot()
        self.post_received(json.dumps(VALID_DM_DATA))
        self.wait_bot()
        self.assertEqual(TwitterPost.objects.count(), 1)
        created_post = TwitterPost.objects.find_one()
        self.assertTrue(created_post.message_type == 'direct')
        self.assertEqual(created_post.content, VALID_DM_DATA['direct_message']['text'] + ' @solariat_brand')
        self.assertTrue(str(channel.inbound_channel.id) in created_post.channel_assignments)
        self.assertEqual(created_post.channel_assignments[str(channel.inbound_channel.id)], 'highlighted')

        self.assert_tweet_data_stored(created_post)

        self.stop_bot()

    @unittest.skip("Processing follow/unfollow events is deprecated in favor of the direct twitter api calls")
    def test_follow_unfollow_events(self):
        """Tests UserProfile's followed_by_brands and follows_brands lists
        are being updated on follow/unfollow events from twitter user stream
        """
        from_user = gen_twitter_user('fake_user1')
        to_user = gen_twitter_user('fake_user2')
        etc = EnterpriseTwitterChannel.objects.create(
            status='Active',
            title='ETC',
            access_token_key='dummy_key',
            access_token_secret='dummy_secret',
            twitter_handle=from_user['screen_name'])

        # class StreamData(object):
        #     """Subset of twitter_bot_dm.UserStream class:
        #     `me` and `channel` attributes are used in
        #     follow/unfollow event handling task.
        #     """
        #     me = from_user['screen_name']
        #     channel = str(etc.id)

        def assert_relations(*rels):
            _eq = self.assertEqual
            _t = self.assertTrue
            _ids = lambda lst: [x.id for x in lst]

            for (up, followed_by, follows) in rels:
                up.reload()
                _eq(up.followed_by_brands, _ids(followed_by))
                _eq(up.follows_brands, _ids(follows))
                for u in followed_by:
                    u.reload()
                    _t(up.is_friend(u))

                for u in follows:
                    u.reload()
                    _t(up.is_follower(u))

        def send_event(event_json):
            server = self.tw_bot.server
            print (server, server.__dict__)
            greenlet = server.streams.get(etc.twitter_handle)
            test_connector = greenlet._stream.test_stream
            test_connector.send('on_data', event_json)
            test_connector.next()

        # 1. brand follows user
        event_json = {"event": "follow", "source": from_user, "target": to_user}

        self.start_bot()
        self.sync_bot()
        self.wait_bot()

        # stream_data = StreamData()
        # self.post_received(json.dumps(event_json), stream_data)
        send_event(event_json)

        source = get_user_profile(from_user)
        target = get_user_profile(to_user)

        assert_relations(
            # profile   followed_by  follows
            (source,    [],          []), # check the user profile of brand has no changes
            (target,    [source],    [])) # check the follower is added

        # 2. user follows brand
        event_json['source'] = to_user
        event_json['target'] = from_user
        # self.post_received(json.dumps(event_json), stream_data)
        send_event(event_json)

        assert_relations(
            # profile   followed_by  follows
            (source,    [],          []), # check the user profile of brand has no changes
            (target,    [source],    [source])) # check the friend is added

        # 3. user unfollows brand - this should result in error in logs
        event_json['event'] = 'unfollow'

        with LoggerInterceptor() as logs:
            # self.post_received(json.dumps(event_json), stream_data)
            send_event(event_json)

        import logging
        errors = filter(
            lambda x: x.levelname == logging.getLevelName(logging.ERROR), logs)
        self.assertEqual(errors[0].exc_info[1].message,
                         "Unexpected 'unfollow' event")
        # check nothing changed
        assert_relations(
            # profile   followed_by  follows
            (source,    [],          []),
            (target,    [source],    [source]))

        # 4. brand unfollows user
        event_json['source'] = from_user
        event_json['target'] = to_user
        # self.post_received(json.dumps(event_json), stream_data)
        send_event(event_json)
        assert_relations(
            # profile   followed_by  follows
            (source,    [],          []),
            (target,    [],          [source]))  # user lost follower

        self.stop_bot()

    def test_lifecycle(self):
        self.start_bot()
        server = self.tw_bot.server
        uname = lambda i: 'sreen_name_%s' % i

        def make_channel(num, title_prefix='Title_'):
            sc = TwitterServiceChannel.objects.create_by_user(
                self.user,
                title='%sService_%s' % (title_prefix, num),
                account=self.user.current_account)
            channel = EnterpriseTwitterChannel.objects.create_by_user(
                self.user,
                account=self.user.current_account,
                title="%s%s" % (title_prefix, num),
                twitter_handle=uname(num),
                access_token_key='dummy_key',
                access_token_secret='dummy_secret')
            channel.save()
            sc.add_username(uname(i))
            return channel

        def check_users(user_nums_list):
            count = 0
            for i in user_nums_list:
                self.assertIn(uname(i), server.username_channels)
                self.assertIn(uname(i), server.streams)
                count += 1
            for stream in server.streams.values():
                self.assertIn(stream, server.stream_threads)
            self.assertEqual(len(server.streams), count)
            self.assertEqual(len(server.username_channels), count)
            self.assertEqual(len(server.stream_threads) - len(server.stream_threads.dying), count)

        def send_event(event, user_nums_list, *args, **kwargs):
            for i in user_nums_list:
                greenlet = server.streams.get(uname(i))
                test_connector = greenlet._stream.test_stream
                test_connector.send(event, *args, **kwargs)
                test_connector.next()

        def patch_recipient(data, username, previous_posts_count=0):
            import copy
            result = copy.deepcopy(data)
            #result = data.copy()
            result['direct_message']['id'] += previous_posts_count
            result['direct_message']['id_str'] = str(result['direct_message']['id'])
            result['direct_message']['recipient']['screen_name'] = username
            result['direct_message']['recipient_screen_name'] = username
            result['direct_message']['created_at'] = "Wed Jul 16 11:40:%02d +0000 2014" % (result['direct_message']['id'] % 60)
            return result

        # add several active EnterpriseTwitterChannels
        num_users = 5
        all_users = xrange(num_users)

        for i in all_users:
            make_channel(i)
        self.sync_bot()

        check_users(all_users)

        # Add duplicate channels for the same twitter handles
        duplicates = [1, 2]
        for i in duplicates:
            make_channel(i, title_prefix="Title_Duplicate_")

        self.sync_bot()
        for i in duplicates:
            self.assertEqual(len(server.username_channels[uname(i)]), 2)

        for i in duplicates:
            channel = EnterpriseTwitterChannel.objects.get(title="Title_Duplicate_%s" % i)
            channel.update(status='Suspended')

        self.sync_bot()
        check_users(all_users)

        for i in duplicates:
            channel = EnterpriseTwitterChannel.objects.get(title="Title_%s" % i)
            channel.update(status='Suspended')
        self.sync_bot()

        check_users(set(all_users) - set(duplicates))

        # send connect and on_data events and check posts created
        all_users = set(all_users) - set(duplicates)
        send_event('on_connect', all_users)
        post_count = 0
        for i in all_users:
            post_count += 1
            send_event('on_data', [i], patch_recipient(VALID_DM_DATA, uname(i), post_count))
            send_event('on_data', [i], patch_recipient(VALID_DM_DATA, uname(i), post_count))
        self.wait_bot()
        self.assertEqual(TwitterPost.objects.count(), len(all_users))

        # check heartbeat events are saved
        server.heartbeat()
        self.assertIs(UserStreamDbEvents(), UserStreamDbEvents())  # should be singleton
        # print(list(DbEvents().events_coll.find()))
        for i in all_users:
            last_event = UserStreamDbEvents().last_online(uname(i))
            self.assertEqual(last_event[0], UserStreamDbEvents.EVENT_KEEP_ALIVE)

        self.stop_bot()


class PublicStreamBotTest(BaseBotTest):
    def setUp(self):
        super(PublicStreamBotTest, self).setUp()
        self.user.is_superuser = True
        self.user.save()
        self.tw_bot = PublicStreamBot(
            username=self.user.email,
            lockfile='tw_bot_public_test_lockfile',
            concurrency=2,
            heartbeat=1)

    def tearDown(self):
        self.wait_bot()
        self.stop_bot()
        super(PublicStreamBotTest, self).tearDown()

    def test_streaming(self):
        """Load tweets from sample file"""
        sample_count = 10

        ch = self.setup_channel(keywords=['Directioners4Music', '#Directioners4Music'])
        ch.skip_retweets = False
        ch.save()
        self.start_bot()
        try:
            with LoggerInterceptor() as logs:
                for data in test_utils.filestream():
                    self.send_event('on_data', data)

                self.assert_no_errors_in_logs(logs)

            self.wait_bot(timeout=1 * sample_count)
            self.assertEqual(TwitterPost.objects.count(), sample_count)
        finally:
            self.stop_bot()

    def test_stream_sync(self):
        ch = self.setup_channel(keywords=['test1', 'test2', 'test3'], usernames=[])
        self.start_bot()
        self.sync_bot()
        ch.del_keyword('test1')
        self.sync_bot()
        self.stop_bot()

    def test_lifecycle(self):
        ch = self.setup_channel(keywords=['test1', 'test2', 'test3'], usernames=[])
        self.start_bot()
        self.send_event('on_disconnect', 'notice')
        self.send_event('on_exception', exception=RuntimeError("TestError"))
        self.stop_bot()

    @unittest.skip("Skipwords disabled. TAP-660")
    def test_skipwords_and_skip_retweets(self):
        """Tests tweets with skipwords and retweets
        are skipped according to channel configuration"""
        import random
        up = UserProfile.objects.upsert('Twitter', profile_data={'screen_name': 'test'})
        ta = self.setup_outbound_channel('OC', twitter_handle=up.user_name)
        ch = self.setup_channel(keywords=['Directioners4Music', '#Directioners4Music'], usernames=[])
        skipwords = ['test123123', 'skip234345']
        languages = ['en', 'es', 'it', 'fr', 'und']
        for skipword in skipwords:
            ch.add_skipword(skipword)
        ch.set_allowed_langs(languages)
        ch.skip_retweets = True
        ch.save()
        self.sync_bot()

        def is_retweet(data):
            json_data = json.loads(data)
            return 'retweeted_status' in json_data

        def patch_content_with_skipword(data):
            json_data = json.loads(data)
            json_data['text'] = u"%s %s" % (json_data['text'], random.choice(skipwords))
            return json.dumps(json_data)

        sample_size = 10
        retweets_count = 0
        skipped_count = 0
        max_skipped = 5
        expected_tweets = []
        self.assertEqual(TwitterPost.objects.count(), 0)
        with LoggerInterceptor() as logs:
            for data in test_utils.filestream(languages=languages, sample_count=sample_size):
                if is_retweet(data):
                    retweets_count += 1
                else:
                    if skipped_count < max_skipped:
                        data = patch_content_with_skipword(data)
                        skipped_count += 1
                    else:
                        expected_tweets.append(json.loads(data)['text'])
                self.send_event('on_data', data)
            self.assert_no_errors_in_logs(logs, allow_levels={'DEBUG', 'INFO', 'WARNING'})

        expected_posts_count = sample_size - retweets_count - skipped_count
        self.wait_bot(timeout=1 * expected_posts_count)
        for post in TwitterPost.objects():
            self.assertIn(post.plaintext_content, expected_tweets)
            expected_tweets.remove(post.plaintext_content)
        self.assertFalse(expected_tweets, msg=expected_tweets)
        self.assertEqual(TwitterPost.objects.count(), expected_posts_count)

        from solariat_bottle.daemons.twitter.stream.db import StreamRef
        self.assertTrue(StreamRef.objects().count() > 0)
        self.assertEqual(StreamRef.objects(status=StreamRef.RUNNING).count(), 1)
        ref = StreamRef.objects(status=StreamRef.RUNNING).sort(id=-1)[0]
        self.assertEqual(len(ref.languages), len(languages))
        self.assertEqual(set(ref.languages), set(languages))

    def test_post_reply(self):
        solariat1001 = {u'follow_request_sent': None, u'profile_use_background_image': True, u'default_profile_image': True, u'id': 2953886599, u'verified': False, u'profile_image_url_https': u'https://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png', u'profile_sidebar_fill_color': u'DDEEF6', u'profile_text_color': u'333333', u'followers_count': 5, u'profile_sidebar_border_color': u'C0DEED', u'id_str': u'2953886599', u'profile_background_color': u'C0DEED', u'listed_count': 0, u'profile_background_image_url_https': u'https://abs.twimg.com/images/themes/theme1/bg.png', u'utc_offset': None, u'statuses_count': 191, u'description': None, u'friends_count': 5, u'location': u'', u'profile_link_color': u'0084B4', u'profile_image_url': u'http://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png', u'following': None, u'geo_enabled': False, u'profile_background_image_url': u'http://abs.twimg.com/images/themes/theme1/bg.png', u'name': u'Solariatw', u'lang': u'en', u'profile_background_tile': False, u'favourites_count': 6, u'screen_name': u'solariat1001', u'notifications': None, u'url': None, u'created_at': u'Wed Dec 31 17:10:35 +0000 2014', u'contributors_enabled': False, u'time_zone': None, u'protected': False, u'default_profile': True, u'is_translator': False}
        solariat1002 = {u'follow_request_sent': None, u'profile_use_background_image': True, u'default_profile_image': True, u'id': 2977841942, u'verified': False, u'profile_image_url_https': u'https://abs.twimg.com/sticky/default_profile_images/default_profile_5_normal.png', u'profile_sidebar_fill_color': u'DDEEF6', u'profile_text_color': u'333333', u'followers_count': 4, u'profile_sidebar_border_color': u'C0DEED', u'id_str': u'2977841942', u'profile_background_color': u'C0DEED', u'listed_count': 0, u'profile_background_image_url_https': u'https://abs.twimg.com/images/themes/theme1/bg.png', u'utc_offset': -14400, u'statuses_count': 56, u'description': None, u'friends_count': 5, u'location': u'', u'profile_link_color': u'0084B4', u'profile_image_url': u'http://abs.twimg.com/sticky/default_profile_images/default_profile_5_normal.png', u'following': None, u'geo_enabled': True, u'profile_background_image_url': u'http://abs.twimg.com/images/themes/theme1/bg.png', u'name': u'Solariatr', u'lang': u'en', u'profile_background_tile': False, u'favourites_count': 0, u'screen_name': u'solariat1002', u'notifications': None, u'url': None, u'created_at': u'Mon Jan 12 22:56:50 +0000 2015', u'contributors_enabled': False, u'time_zone': u'Eastern Time (US & Canada)', u'protected': False, u'default_profile': True, u'is_translator': False}
        UserProfile.objects.upsert('Twitter', profile_data=parse_user_profile(solariat1001))
        UserProfile.objects.upsert('Twitter', profile_data=parse_user_profile(solariat1002))

        self.user.is_superuser = True

        sc1 = self.setup_channel(keywords=[], usernames=['@solariat1001'], title='TS1')
        sc2 = self.setup_channel(keywords=['new smart TV'], usernames=['@solariat1002'], title='TS2')
        sc2.add_username('@solariat1001')  # for routing all replies to sc2.outbound
        ta1 = self.setup_outbound_channel('TA1', 'solariat1001')
        ta2 = self.setup_outbound_channel('TA2', 'solariat1002')

        self.user.set_outbound_channel(ta1)
        self.user.current_account.set_outbound_channel(ta1)

        stream = [
            {u'contributors': None, u'truncated': False, u'text': u'I need a new smart TV tomorrow', u'in_reply_to_status_id': None, u'id': 598561105468850178, u'favorite_count': 0, u'source': u'<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>', u'retweeted': False, u'coordinates': None, u'timestamp_ms': u'1431543062928', u'entities': {u'user_mentions': [], u'symbols': [], u'trends': [], u'hashtags': [], u'urls': []}, u'in_reply_to_screen_name': None, u'id_str': u'598561105468850178', u'retweet_count': 0, u'in_reply_to_user_id': None, u'favorited': False, u'user': {u'follow_request_sent': None, u'profile_use_background_image': True, u'default_profile_image': True, u'id': 2750033348, u'verified': False, u'profile_image_url_https': u'https://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png', u'profile_sidebar_fill_color': u'DDEEF6', u'profile_text_color': u'333333', u'followers_count': 4, u'profile_sidebar_border_color': u'C0DEED', u'id_str': u'2750033348', u'profile_background_color': u'C0DEED', u'listed_count': 0, u'profile_background_image_url_https': u'https://abs.twimg.com/images/themes/theme1/bg.png', u'utc_offset': None, u'statuses_count': 119, u'description': None, u'friends_count': 1, u'location': u'', u'profile_link_color': u'0084B4', u'profile_image_url': u'http://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png', u'following': None, u'geo_enabled': False, u'profile_background_image_url': u'http://abs.twimg.com/images/themes/theme1/bg.png', u'name': u'Solariat2014 Tester', u'lang': u'en', u'profile_background_tile': False, u'favourites_count': 0, u'screen_name': u'solariat2014', u'notifications': None, u'url': None, u'created_at': u'Wed Aug 20 19:05:26 +0000 2014', u'contributors_enabled': False, u'time_zone': None, u'protected': False, u'default_profile': True, u'is_translator': False}, u'geo': None, u'in_reply_to_user_id_str': None, u'possibly_sensitive': False, u'lang': u'en', u'created_at': u'Wed May 13 18:51:02 +0000 2015', u'filter_level': u'low', u'in_reply_to_status_id_str': None, u'place': None},
            {u'contributors': None, u'truncated': False, u'text': u'@solariat2014 Reply from TA2 ^dna', u'in_reply_to_status_id': 598561105468850178, u'id': 598561193196818432, u'favorite_count': 0, u'source': u'<a href="http://solariat.com" rel="nofollow">Solariat test</a>', u'retweeted': False, u'coordinates': None, u'timestamp_ms': u'1431543083844', u'entities': {u'user_mentions': [{u'id': 2750033348, u'indices': [0, 13], u'id_str': u'2750033348', u'screen_name': u'solariat2014', u'name': u'Solariat2014 Tester'}], u'symbols': [], u'trends': [], u'hashtags': [], u'urls': []}, u'in_reply_to_screen_name': u'solariat2014', u'id_str': u'598561193196818432', u'retweet_count': 0, u'in_reply_to_user_id': 2750033348, u'favorited': False, u'user': solariat1002, u'geo': None, u'in_reply_to_user_id_str': u'2750033348', u'possibly_sensitive': False, u'lang': u'en', u'created_at': u'Wed May 13 18:51:23 +0000 2015', u'filter_level': u'low', u'in_reply_to_status_id_str': u'598561105468850178', u'place': None},
            {u'contributors': None, u'truncated': False, u'text': u'My new smart TV is broken', u'in_reply_to_status_id': None, u'id': 598561297995800577, u'favorite_count': 0, u'source': u'<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>', u'retweeted': False, u'coordinates': None, u'timestamp_ms': u'1431543108830', u'entities': {u'user_mentions': [], u'symbols': [], u'trends': [], u'hashtags': [], u'urls': []}, u'in_reply_to_screen_name': None, u'id_str': u'598561297995800577', u'retweet_count': 0, u'in_reply_to_user_id': None, u'favorited': False, u'user': {u'follow_request_sent': None, u'profile_use_background_image': True, u'default_profile_image': True, u'id': 2750033348, u'verified': False, u'profile_image_url_https': u'https://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png', u'profile_sidebar_fill_color': u'DDEEF6', u'profile_text_color': u'333333', u'followers_count': 4, u'profile_sidebar_border_color': u'C0DEED', u'id_str': u'2750033348', u'profile_background_color': u'C0DEED', u'listed_count': 0, u'profile_background_image_url_https': u'https://abs.twimg.com/images/themes/theme1/bg.png', u'utc_offset': None, u'statuses_count': 120, u'description': None, u'friends_count': 1, u'location': u'', u'profile_link_color': u'0084B4', u'profile_image_url': u'http://abs.twimg.com/sticky/default_profile_images/default_profile_6_normal.png', u'following': None, u'geo_enabled': False, u'profile_background_image_url': u'http://abs.twimg.com/images/themes/theme1/bg.png', u'name': u'Solariat2014 Tester', u'lang': u'en', u'profile_background_tile': False, u'favourites_count': 0, u'screen_name': u'solariat2014', u'notifications': None, u'url': None, u'created_at': u'Wed Aug 20 19:05:26 +0000 2014', u'contributors_enabled': False, u'time_zone': None, u'protected': False, u'default_profile': True, u'is_translator': False}, u'geo': None, u'in_reply_to_user_id_str': None, u'possibly_sensitive': False, u'lang': u'en', u'created_at': u'Wed May 13 18:51:48 +0000 2015', u'filter_level': u'low', u'in_reply_to_status_id_str': None, u'place': None},
            {u'contributors': None, u'truncated': False, u'text': u'@solariat2014 Reply from TA1 ^dna', u'in_reply_to_status_id': 598561297995800577, u'id': 598561354618802176, u'favorite_count': 0, u'source': u'<a href="http://solariat.com" rel="nofollow">Solariat test</a>', u'retweeted': False, u'coordinates': None, u'timestamp_ms': u'1431543122330', u'entities': {u'user_mentions': [{u'id': 2750033348, u'indices': [0, 13], u'id_str': u'2750033348', u'screen_name': u'solariat2014', u'name': u'Solariat2014 Tester'}], u'symbols': [], u'trends': [], u'hashtags': [], u'urls': []}, u'in_reply_to_screen_name': u'solariat2014', u'id_str': u'598561354618802176', u'retweet_count': 0, u'in_reply_to_user_id': 2750033348, u'favorited': False, u'user': solariat1001, u'geo': None, u'in_reply_to_user_id_str': u'2750033348', u'possibly_sensitive': False, u'lang': u'en', u'created_at': u'Wed May 13 18:52:02 +0000 2015', u'filter_level': u'low', u'in_reply_to_status_id_str': u'598561297995800577', u'place': None},
            {u'contributors': None, u'truncated': False, u'text': u"RT @SportsMania005: Over the next few days we are adding a new feature which is making our Streams compatible with Smart TV's so we will be\u2026", u'in_reply_to_status_id': None, u'id': 598562190078156800, u'favorite_count': 0, u'source': u'<a href="http://twitter.com/download/android" rel="nofollow">Twitter for Android</a>', u'retweeted': False, u'coordinates': None, u'timestamp_ms': u'1431543321519', u'entities': {u'user_mentions': [{u'id': 2208881395, u'indices': [3, 18], u'id_str': u'2208881395', u'screen_name': u'SportsMania005', u'name': u'SportsMania'}], u'symbols': [], u'trends': [], u'hashtags': [], u'urls': []}, u'in_reply_to_screen_name': None, u'id_str': u'598562190078156800', u'retweet_count': 0, u'in_reply_to_user_id': None, u'favorited': False, u'retweeted_status': {u'contributors': None, u'truncated': False, u'text': u"Over the next few days we are adding a new feature which is making our Streams compatible with Smart TV's so we will be confirming which...", u'in_reply_to_status_id': None, u'id': 598530764574203904, u'favorite_count': 1, u'source': u'<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>', u'retweeted': False, u'coordinates': None, u'entities': {u'user_mentions': [], u'symbols': [], u'trends': [], u'hashtags': [], u'urls': []}, u'in_reply_to_screen_name': None, u'id_str': u'598530764574203904', u'retweet_count': 2, u'in_reply_to_user_id': None, u'favorited': False, u'user': {u'follow_request_sent': None, u'profile_use_background_image': False, u'default_profile_image': False, u'id': 2208881395, u'verified': False, u'profile_image_url_https': u'https://pbs.twimg.com/profile_images/568481878542270464/236eDfg5_normal.png', u'profile_sidebar_fill_color': u'000000', u'profile_text_color': u'000000', u'followers_count': 1361, u'profile_sidebar_border_color': u'000000', u'id_str': u'2208881395', u'profile_background_color': u'000000', u'listed_count': 12, u'profile_background_image_url_https': u'https://abs.twimg.com/images/themes/theme1/bg.png', u'utc_offset': 3600, u'statuses_count': 63, u'description': None, u'friends_count': 343, u'location': u'Romania', u'profile_link_color': u'DD2E44', u'profile_image_url': u'http://pbs.twimg.com/profile_images/568481878542270464/236eDfg5_normal.png', u'following': None, u'geo_enabled': False, u'profile_banner_url': u'https://pbs.twimg.com/profile_banners/2208881395/1424371546', u'profile_background_image_url': u'http://abs.twimg.com/images/themes/theme1/bg.png', u'name': u'SportsMania', u'lang': u'en', u'profile_background_tile': False, u'favourites_count': 102, u'screen_name': u'SportsMania005', u'notifications': None, u'url': u'http://SportsMania.eu', u'created_at': u'Fri Nov 22 12:18:31 +0000 2013', u'contributors_enabled': False, u'time_zone': u'Casablanca', u'protected': False, u'default_profile': False, u'is_translator': False}, u'geo': None, u'in_reply_to_user_id_str': None, u'possibly_sensitive': False, u'lang': u'en', u'created_at': u'Wed May 13 16:50:29 +0000 2015', u'filter_level': u'low', u'in_reply_to_status_id_str': None, u'place': None}, u'user': {u'follow_request_sent': None, u'profile_use_background_image': True, u'default_profile_image': False, u'id': 315963404, u'verified': False, u'profile_image_url_https': u'https://pbs.twimg.com/profile_images/551095536871546880/ub3RZJC0_normal.jpeg', u'profile_sidebar_fill_color': u'DDEEF6', u'profile_text_color': u'333333', u'followers_count': 156, u'profile_sidebar_border_color': u'C0DEED', u'id_str': u'315963404', u'profile_background_color': u'C0DEED', u'listed_count': 0, u'profile_background_image_url_https': u'https://abs.twimg.com/images/themes/theme1/bg.png', u'utc_offset': None, u'statuses_count': 1258, u'description': None, u'friends_count': 380, u'location': u'Workington', u'profile_link_color': u'0084B4', u'profile_image_url': u'http://pbs.twimg.com/profile_images/551095536871546880/ub3RZJC0_normal.jpeg', u'following': None, u'geo_enabled': False, u'profile_banner_url': u'https://pbs.twimg.com/profile_banners/315963404/1416002538', u'profile_background_image_url': u'http://abs.twimg.com/images/themes/theme1/bg.png', u'name': u'shaun mandale', u'lang': u'en', u'profile_background_tile': False, u'favourites_count': 995, u'screen_name': u'S_mandale', u'notifications': None, u'url': None, u'created_at': u'Sun Jun 12 18:40:55 +0000 2011', u'contributors_enabled': False, u'time_zone': None, u'protected': False, u'default_profile': True, u'is_translator': False}, u'geo': None, u'in_reply_to_user_id_str': None, u'possibly_sensitive': False, u'lang': u'en', u'created_at': u'Wed May 13 18:55:21 +0000 2015', u'filter_level': u'low', u'in_reply_to_status_id_str': None, u'place': None}
        ]
        self.start_bot()
        for post in stream:
            self.send_event('on_data', post)
            self.wait_bot()  # wait to preserve post order

        # test both posts in sc2.inbound are replied
        self.assertEqual(TwitterPost.objects(channels=sc2.inbound).count(), 2)
        self.assertEqual(TwitterPost.objects(channels=sc2.outbound).count(), 2)
        for post in TwitterPost.objects(channels=sc2.inbound):
            self.assertEqual(post.channel_assignments[str(sc2.inbound)], 'replied')
        for reply in TwitterPost.objects(channels=sc2.outbound):
            self.assertIn(sc2.inbound, reply.parent.channels)

        self.stop_bot()


class BotConcurrencyTest(BaseBotTest):

    def setUp(self):
        from gevent import monkey
        monkey.patch_all(Event=True)

        super(BotConcurrencyTest, self).setUp()
        self.user.is_superuser = True
        self.user.save()
        self.tw_bot = PublicStreamBot(
            username=self.user.email,
            lockfile='tw_bot_public_test_lockfile',
            concurrency=2,
            multiprocess_concurrency=2,
            heartbeat=1)

    def tearDown(self):
        self.wait_bot()
        self.stop_bot()
        super(BotConcurrencyTest, self).tearDown()

    def test_bot(self):
        up = UserProfile.objects.upsert('Twitter', profile_data=dict(user_name='test', user_id='123123'))
        ta = self.setup_outbound_channel('OC', twitter_handle=up.user_name)
        ch = self.setup_channel(keywords=['Directioners4Music', '#Directioners4Music'], usernames=[up.user_name])
        self.sync_bot()

        sample_size = 3

        for data in test_utils.filestream(sample_count=sample_size):
            self.send_event('on_data', data)
        self.wait_bot()
        sleep(1)

        self.assertEqual(TwitterPost.objects(channels=ch.inbound).count(), sample_size)

        # test bot status
        import signal
        self.tw_bot.signal(signal.SIGUSR2)
        status = PublicStreamDbEvents().status_coll.find_one()
        self.assertIsNotNone(status)