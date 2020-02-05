import unittest
import json
from solariat_bottle.tests.base import MainCase, UICase, SA_TYPES
from solariat_bottle.db.tracking import (
    PostFilter,
    PostFilterEntry, PostFilterStream, PostFilterEntryPassive,
    POSTFILTER_CAPACITY)
from solariat_bottle.db.user_profiles.social_profile import SocialProfile
from solariat_bottle.tasks import get_tracked_channels
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.channel.twitter import UserTrackingChannel, KeywordTrackingChannel, TwitterServiceChannel, EnterpriseTwitterChannel
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.utils.tracking import get_channel_post_filters_map, \
    combine_and_split, flatten_channel_post_filters_map


class TrackingCase(MainCase):

    def setUp(self):
        MainCase.setUp(self)
        self.stream =  PostFilterStream.get()

    def test_track_passive(self):

        self.stream.track_passive(["123456"], [self.channel])
        self.assertTrue(PostFilterEntryPassive.objects.count() == 1)

        tracked_channels = get_tracked_channels('Twitter',
            dict(content="I need a new laptop", user_profile=dict(user_name='user_name', user_id='123456')))

        self.assertTrue(self.channel in tracked_channels)

        self.stream.untrack_channel_passive(self.channel)
        self.assertTrue(PostFilterEntryPassive.objects.count() == 0)

    def test_base_tracking_cases(self):
        # Track the first one
        self.stream.track(
            "KEYWORD",
            ["foo"],
            [self.channel])

        self.assertTrue(PostFilter.objects.count() == 1)
        self.assertTrue(PostFilterEntry.objects.count() == 1)
        self.assertFalse(PostFilterEntry.objects()[0].channels == [])

        #print [(pf.entry, pf.filter_type_id, len(pf.channels)) for pf in PostFilterEntry.objects()]

        self.assertEqual(PostFilter.objects()[0].spare_capacity, POSTFILTER_CAPACITY - 1)
        self.assertEqual(PostFilter.objects()[0].entry_count, 1)
        
        # Track another - multiples, no new filter
        self.stream.track(
            "KEYWORD",
            ["bar", "baz"],
            [self.channel])

        self.assertTrue(PostFilter.objects.count() == 1)
        self.assertTrue(PostFilterEntry.objects.count() == 3)
        self.assertEqual(PostFilter.objects()[0].spare_capacity, POSTFILTER_CAPACITY - 3)
        self.assertEqual(PostFilter.objects()[0].entry_count, 3)

        # Untrack some
        self.stream.untrack(
            "KEYWORD",
            ["foo", "Bar"],
            [self.channel])

        self.assertEqual(PostFilterEntry.objects.count(), 1)
        self.assertEqual(PostFilter.objects()[0].spare_capacity, POSTFILTER_CAPACITY - 1)
        self.assertEqual(PostFilter.objects()[0].entry_count, 1)

        # Untrack last - all gone
        self.stream.untrack(
            "KEYWORD",
            ["baz"],
            [self.channel])

        self.assertTrue(PostFilter.objects.count() == 0)
        self.assertTrue(PostFilterEntry.objects.count() == 0)

    @unittest.skip("Skipwords disabled. TAP-660")
    def test_skipword(self):

        ktc1 = KeywordTrackingChannel.objects.create_by_user(
                      self.user, title='KeywordTrackingChannel', status='Active')
        ktc1.add_keyword('iphone')
        ktc1.add_skipword('iPad')  # Note: the keyword in PostFilterEntry will be lowercase 'ipad'

        ktc2 = KeywordTrackingChannel.objects.create_by_user(
                      self.user, title='KeywordTrackingChannel2', status='Active')
        ktc2.add_keyword('iphone')

        tracked_channels = get_tracked_channels('Twitter',
                dict(user_name='user', user_id='1'),
                dict(content='I have iphone but not ipad'))

        self.assertEqual(len(tracked_channels), 1)
        self.assertTrue(ktc1 not in tracked_channels)
        self.assertTrue(ktc2 in tracked_channels)

        # test keywords case-insensitivity
        tracked_channels = get_tracked_channels('Twitter',
                dict(user_name='user', user_id='1'),
                dict(content='I have the iPhone but not iPAD'))

        self.assertEqual(len(tracked_channels), 1)
        self.assertTrue(ktc1 not in tracked_channels)
        self.assertTrue(ktc2 in tracked_channels)

    def test_trackingchannels(self):

        utc = UserTrackingChannel.objects.create_by_user(
                      self.user, title='UserTrackingChannel', status='Active')
        utc.add_username('user1')
        utc.add_username('user1')
        utc.add_username('user2')

        ktc = KeywordTrackingChannel.objects.create_by_user(
                      self.user, title='KeywordTrackingChannel', status='Active')
        ktc.add_keyword('key1')
        ktc.add_keyword('key2')
        ktc.add_keyword('key2')

        self.assertEqual(len(utc.usernames), 2)
        self.assertTrue(
            'user1' in utc.usernames and 'user2' in utc.usernames)
        self.assertEqual(len(ktc.keywords), 2)
        self.assertTrue('key1' in ktc.keywords and 'key2' in ktc.keywords)
        self.assertEqual(
            PostFilterEntry.objects.find(filter_type_id=0).count(), 2)
        self.assertEqual(
            PostFilterEntry.objects.find(filter_type_id=1).count(), 2)

        utc.del_username('user1')
        ktc.del_keyword('key2')
        ktc.del_keyword('key1')

        self.assertEqual(len(utc.usernames), 1)
        self.assertTrue('user2' in utc.usernames)
        self.assertEqual(len(ktc.keywords), 0)
        self.assertEqual(
            PostFilterEntry.objects.find(filter_type_id=0).count(), 0)
        self.assertEqual(
            PostFilterEntry.objects.find(filter_type_id=1).count(), 1)

    def test_complex_key(self):

        self.stream.track(
            'KEYWORD',
            ["can't stop a girl"],
            [self.channel])

        tracked_channels = get_tracked_channels('Twitter',
                dict(content="I Can't stop a girl from shopping!!"))

        self.assertTrue(self.channel in tracked_channels)

    def test_user_name_case(self):

        self.stream.track('USER_NAME', ['winPhoneSupport'], [self.channel])

        tracked_channels = get_tracked_channels('Twitter',
                dict(content="Xbox Music cloud is cool",
                     user_profile=dict(user_name='WinPhoneSupport', user_id='193456251')))

        self.assertTrue(self.channel in tracked_channels)

    def test_catch_hashtag_by_keyword(self):

        self.stream.track('KEYWORD', ['foobarcmg'], [self.channel])

        tracked_channels = get_tracked_channels('Twitter',
            dict(content="This is a #foobarcmg! I hope you like it."))

        self.assertTrue(self.channel in tracked_channels)

    def test_catch_hashtag_by_hashtag(self):

        self.stream.track('KEYWORD', ['#foobarcmg'], [self.channel])

        tracked_channels = get_tracked_channels('Twitter',
                dict(content="This is a #foobarcmg! I hope you like it."))

        self.assertTrue(self.channel in tracked_channels)

    def test_incorrect_hashtag(self):

        self.stream.track('KEYWORD', ['#foobarcmg'], [self.channel])

        tracked_channels = get_tracked_channels('Twitter',
                dict(content="This is a #foobarcmg# I hope you like it."))

        self.assertFalse(self.channel in tracked_channels)

    def test_catch_mentions(self):

        self.stream.track('KEYWORD', ['@john81'], [self.channel])

        tracked_channels = get_tracked_channels('Twitter',
                dict(content="Hi @John81 I have problems on my Win 8 Laptop"))

        self.assertTrue(self.channel in tracked_channels)

    def test_postfilter_channel_removed(self):
        def _test(delete_channel):
            default_capacity = 5
            PostFilter.spare_capacity.default = default_capacity
            ch = Channel.objects.create(title='To be Deleted')
            self.stream.track('KEYWORD', ['@john81'], [ch])

            tracked_channels = get_tracked_channels(
                'Twitter',
                dict(content="Hi @John81 I have problems on my Win 8 Laptop"))

            self.assertEqual([ch], tracked_channels)
            self.assertEqual(PostFilterEntry.objects(channels=ch.id).count(), 1)

            delete_channel(ch)
            tracked_channels = get_tracked_channels(
                'Twitter',
                dict(content="Hi @John81 I have problems on my Win 8 Laptop"))

            self.assertEqual([], tracked_channels)
            self.assertEqual(PostFilterEntry.objects(channels=ch.id).count(), 0)
            self.assertEqual(PostFilterEntry.objects().count(), 0)

            post_filters = PostFilter.objects.find()
            self.assertEqual(len(post_filters), 1)
            self.assertEqual(post_filters[0].entry_count, 0)
            self.assertEqual(post_filters[0].spare_capacity, default_capacity)

        _test(lambda ch: ch.delete())
        _test(lambda ch: ch.archive())

    def test_retweets_received(self):
        def _test():
            return get_tracked_channels(
                'Twitter',
                dict(content='RT: @aaa I like test_kwd',
                     user_profile=dict(user_name='test', user_id='1'),
                     twitter=dict(retweeted_status={"content": "I like test_kwd"})))

        uname = 'test'
        sc = TwitterServiceChannel.objects.create_by_user(self.user, title='INB_TW')
        etc = EnterpriseTwitterChannel.objects.create_by_user(self.user, title='ETC', twitter_handle=uname)
        sc.add_keyword('test_kwd')
        sc.skip_retweets = False
        sc.save()
        channels = _test()
        self.assertEqual(set(channels), {sc.inbound_channel, etc})
        sc.delete()
        channels = _test()
        self.assertEqual(set(channels), {etc})


class TrackingUITest(UICase):
    '''Excercise range of end-points and make sure integration is working.'''

    def _create_channel(self, _type, title):
        res = self._post('/configure/channels/json', dict(type=_type,
                                                          title=title,
                                                          platform='Twitter'))
        channel = Channel.objects.get(res['id'])
        self.assertTrue(_type in channel.__class__.__name__.lower(),
                        msg="Wrong channel type %s" % channel)
        # All such channels should be active initially
        self.assertEqual(channel.status, channel.initial_status)
        return channel

    def _create_tracked_post(self, content, user_name):
        user_profile = UserProfile.objects.upsert(
            'Twitter', dict(screen_name=user_name, user_id=user_name))

        lang = 'en'
        tracked_channels = get_tracked_channels(
            "Twitter",
            dict(content=content, lang=lang, user_profile=dict(user_name=user_name,
                                                               user_id=user_name)))

        post = self._create_db_post(
            user_profile=user_profile,
            channels=[str(c.id) for c in tracked_channels],
            content=content,
            lang=lang)
        return post

    def _create_user_tracking_channel(self, title, usernames):
        c = self._create_channel('usertracking', title)
        c.status = 'Active'
        c.save()
        for username in usernames:
            self._post('/tracking/usernames/json',
                       dict(channel_id=str(c.id), username=username))
        return c

    def _create_keyword_tracking_channel(self, title, keywords):
        c = self._create_channel('keywordtracking', title)
        c.status = 'Active'
        c.save()
        for kw in keywords:
            self._post('/tracking/keywords/json',
                       dict(channel_id=str(c.id), keyword=kw))
        return c

    def _create_enterprise_twitter_channel(self, title, handle):
        c = self._create_channel('enterprisetwitter', title)
        self._post('/configure/channel_update/json',
                   dict(channel_id=str(c.id), twitter_handle=handle))
        c.reload()
        return c

    def _delete_channel(self, channel):
        data = {'channels': [ str(channel.id) ]}
        resp = self.client.post(
            '/commands/delete_channel',
            data=json.dumps(data), content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])

        channel.reload()
        self.assertEqual(channel.status, 'Archived')
        return channel

    def _check_property(self, channel, tag_items, k, v):
        for tag_item in tag_items:
            if tag_item['id'] == str(channel.id):
                return tag_item[k] == v
        return False

    def setUp(self):
        UICase.setUp(self)
        self.login()

        # Create User Tracking Channels
        self.ut1 = self._create_user_tracking_channel('user_tracker_1', ['u1', 'u2'])
        self.ut2 = self._create_user_tracking_channel('user_tracker_2', ['u2', 'u3'])
        self.kw1 = self._create_keyword_tracking_channel('kw_tracker_1', ['k1', 'k2'])
        self.kw2 = self._create_keyword_tracking_channel('kw_tracker_2', ['k2', 'k3'])
        self.etc = self._create_enterprise_twitter_channel('etc_1', 'twr1')


    def test_post_track_error_cases(self):
        res = self._get('/post/track/json', {'post_id': 'abc123'}, False)
        self.assertEqual(res['error'], "Post abc123 does not exist")

    def test_fetch_all_available_tags(self):
        res = self._get('/post/track/json', {}, True)
        titles = [ item['text'] for item in res['items'] ]
        self.assertEqual(titles, [ 'user_tracker_1', 'user_tracker_2'])

    def test_post_creation(self):
        post = self._create_tracked_post("I need a foo. k1, k2, k3",
                                         'u1')
        self.assertEqual(set(post.channels).difference(
                set([self.ut1.id, self.kw1.id, self.kw2.id])), set())

        self.assertEqual(post.user_profile['user_name'], 'u1')

        # Now fetch the proper tags details
        res = self._get('/post/track/json', {'post_id': post.id}, True)

        # All Items should be green
        self.assertEqual([item['color'] for item in res['items']],
                         ['green', 'green', 'green'])

        # Only user tag should be modifiable...
        self.assertTrue( self._check_property(self.ut1, res['items'], 'change', True) )
        self.assertTrue( self._check_property(self.kw1, res['items'], 'change', False) )
        self.assertTrue( self._check_property(self.kw2, res['items'], 'change', False) )

        # Now we remove the tag on this user and observe it going red and un-modifiable
        self._delete('/tracking/usernames/json',
                       dict(channel_id=str(self.ut1.id), username='u1'))
        res = self._get('/post/track/json', {'post_id': post.id}, True)
        self.assertTrue( self._check_property(self.ut1, res['items'], 'change', False), res['items'] )
        self.assertTrue( self._check_property(self.ut1, res['items'], 'color', 'red'), res['items']  )

        # Now add a tag for another channel and verify the color and mutability
        self._post('/tracking/usernames/json',
                       dict(channel_id=str(self.ut2.id), username='u1'))
        res = self._get('/post/track/json', {'post_id': post.id}, True)
        self.assertTrue( self._check_property(self.ut2, res['items'], 'change', True), res['items'] )
        self.assertTrue( self._check_property(self.ut2, res['items'], 'color', 'yellow'), res['items']  )


    def test_tracking_incomplete_handle(self):
        """ Test a regression where in case we only added a twitter handle as
        @twitter_handle and not at twitter_handle ended up in a state where the
        database and what we show in UI and what is in database is different. This
        also caused problems with datasift and didn't pick up the tweets from that handle."""
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='INB_TW',
                                                               account=self.user.account)
        self._post('/tracking/usernames/json', dict(channel_id=str(channel.id), username='@usr1'))
        usernames = self._get('/tracking/usernames/json', dict(channel_id=str(channel.id)))['item']
        channel.reload()
        db_usernames = channel.outbound_channel.data['usernames']
        self.assertListEqual(usernames, db_usernames)

    def test_post_tagging_after_creation(self):
        post = self._create_tracked_post("I need a foo. k1, k2, k3", 'u1')

        # Add Tag and verify configuration update
        self._post('/tracking/usernames/json',
                       dict(channel_id=str(self.ut2.id), username='u1'))
        self.ut2.reload()
        self.assertTrue('u1' in self.ut2.usernames, self.ut2.usernames)

        # Add a keyword tracking channel and verify tag update so it is present,
        # Yellow, and not mutable (keyword)
        self.kw3 = self._create_keyword_tracking_channel('kw_tracker_3', ['foo'])

        self.assertEqual(KeywordTrackingChannel.objects(keywords__in=['k1', 'k2']).count(), 2)
        res = self._get('/post/track/json', {'post_id': post.id}, True)
        self.assertTrue( self._check_property(self.kw3, res['items'], 'change', False), res['items'] )
        self.assertTrue( self._check_property(self.kw3, res['items'], 'color', 'yellow'), res['items']  )

        # Now deactivate it and verify that it is still present
        kwtc = Channel.objects.get(title='kw_tracker_3')
        kwtc.on_suspend()
        self.kw3.on_suspend()
        res = self._get('/post/track/json', {'post_id': post.id}, True)
        self.assertTrue( self._check_property(self.kw3, res['items'], 'color', 'yellow'), res['items']  )
        self.assertTrue( self._check_property(kwtc, res['items'], 'color', 'yellow'), res['items']  )

    def test_etc_twitter_handle_tracking(self):
        "twr1 is the twitter handle created for the Enterprise Twitter account"
        post = self._create_tracked_post("I need a foo. k1, k2, k3",
            self.etc.twitter_handle)  #'twr1'

        # This makes sure that we are tracking it.
        self.assertTrue(set(post.channels) == set([self.etc.id, self.kw1.id, self.kw2.id]))
        self.assertEqual(post.user_profile['user_name'], self.etc.twitter_handle)

        # Now fetch the proper tags details
        res = self._get('/post/track/json', {'post_id': post.id}, True)

        # All Items should be green
        self.assertEqual([item['color'] for item in res['items']],
            ['green', 'green', 'green'])

        #Delete ("archive") channel
        self._delete_channel(self.etc)
        res = self._get('/post/track/json', {'post_id': post.id}, True)
        self.assertEqual([item['color'] for item in res['items']],
            ['green', 'green'])

        #un-archive channel
        self.etc.status = 'Suspended'
        self.etc.is_archived = False
        self.etc.save()  #pre_save=False => do not check twitter_handle

        res = self._get('/post/track/json', {'post_id': post.id}, True)
        self.assertEqual([item['color'] for item in res['items']],
            ['red', 'green', 'green'])

        #update channel with empty twitter handle
        self._post('/configure/channel_update/json',
            dict(channel_id=str(self.etc.id), twitter_handle=""))
        self.etc.reload()

        res = self._get('/post/track/json', {'post_id': post.id}, True)
        self.assertEqual([item['color'] for item in res['items']],
            ['red', 'green', 'green'])

    def test_interim_channel_tracked(self):
        """Test channel keywords/handles are tracked
        when channel is in Interim state.

        In production just activated twitter service channel has Interim state,
        in which it's also possible to update channel keywords/handles"""
        KEYWORD = 0
        USER_NAME = 1

        channel = TwitterServiceChannel.objects.create(title='Test',
                                                       status='Interim')
        channel.add_username('@test_USER')
        channel.save()
        q = PostFilterEntry.objects(channels__in=[channel.inbound, channel.outbound])
        self.assertEqual(q.count(), 3)

        self.assertEqual(set(((item.filter_type_id, item.entry) for item in q)),
            set(((KEYWORD, '@test_user'),
                 (USER_NAME, '@test_user'),
                 (USER_NAME, 'test_user'))))


class TrackingUtilsTest(MainCase):
    def test_tracking_items(self):
        n_kwd = 10
        n_users = 10
        expected_users = []
        expected_phrases = []

        channel = TwitterServiceChannel.objects.create(title='Test')
        for n in xrange(n_users):
            channel.add_username('@test_USER%s' % n)
            UserProfile.objects.upsert('Twitter', profile_data={"user_name": 'test_user%s' % n, "user_id": str(123 + n)})
            expected_users.append(str(123 + n))
            expected_phrases.append('@test_user%s' % n)

        for n in xrange(n_kwd):
            channel.add_keyword('test%s' % n)
            expected_phrases.append('test%s' % n)
            channel.save()

        def assert_tracking(channel, expected_phrases, expected_users,
                            max_track=5, max_follow=5, expected_parts=4):
            channel_key_map = get_channel_post_filters_map([channel.inbound_channel, channel.outbound_channel])
            username_list, user_id_list = flatten_channel_post_filters_map(channel_key_map)
            parts = combine_and_split(channel_key_map, max_track=max_track, max_follow=max_follow)
            self.assertEqual(len(parts), expected_parts)
            all_phrases = []
            all_users = []
            for (track, follow, accounts, channels) in parts:
                all_phrases.extend(track)
                all_users.extend(follow)

            self.assertEqual(len(expected_phrases), len(all_phrases))
            self.assertEqual(len(expected_users), len(all_users))
            self.assertEqual(set(expected_phrases), set(all_phrases))
            self.assertEqual(set(expected_users), set(all_users))
            self.assertEqual(set(profile.user_id for profile in SocialProfile.objects(user_name__in=username_list)),
                             set(expected_users), (user_id_list, username_list))

        # 10 keywords and 10 user names result in 20 keywords and 10 usernames,
        # so there should be 4 parts: 2 full and 2 with keywords only
        assert_tracking(channel, expected_phrases, expected_users)
        channel.add_keyword('#new_keyword')
        channel.add_keyword('#test0')  # old keyword with hashtag should be omitted
        channel.add_keyword('@new_user')  # mention should be added
        channel.add_keyword('test_user0')  # mention @test_user0 should be replaced with test_user0
        channel.add_keyword('a' * 61)  # should be skipped - too long
        channel.add_username('test_user1')  # adding this username should not change anything
        expected_phrases.extend(['#new_keyword', '@new_user', 'test_user0'])
        expected_phrases.remove('@test_user0')

        # added new keywords - will split onto 5 parts
        assert_tracking(channel, expected_phrases, expected_users, expected_parts=5)


class TestDirectMessagesTracking(MainCase):
    def test_directed_to_handle(self):
        """DMs and tweets directed to a handle should all be received
        in spite of the language detected"""
        non_configured_lang = 'id'
        channel_langs = ['fr', 'en', 'pt', 'ro', 'it', 'es']
        assert non_configured_lang not in channel_langs

        public_tweet = {u'contributors': None, u'truncated': False,
                                 u'text': u'@jessy_makaroff I need a new laptop now',
                                 u'is_quote_status': False, u'in_reply_to_status_id': None,
                                 u'id': 740742270610247680, u'favorite_count': 0,
                                 u'source': u'<a href="http://twitter.com" rel="nofollow">Twitter Web Client</a>',
                                 u'retweeted': False, u'coordinates': None,
                                 u'timestamp_ms': u'1465441694296', u'entities': {
                u'user_mentions': [
                    {u'id': 4842980294, u'indices': [0, 15], u'id_str': u'4842980294',
                     u'screen_name': u'jessy_makaroff', u'name': u'Jessy Petroff'}], u'symbols': [],
                u'hashtags': [], u'urls': []}, u'in_reply_to_screen_name': u'jessy_makaroff',
                                 u'id_str': u'740742270610247680', u'retweet_count': 0,
                                 u'in_reply_to_user_id': 4842980294, u'favorited': False,
                                 u'user': {u'follow_request_sent': None,
                                           u'profile_use_background_image': True,
                                           u'default_profile_image': True, u'id': 4843024956,
                                           u'verified': False,
                                           u'profile_image_url_https': u'https://abs.twimg.com/sticky/default_profile_images/default_profile_0_normal.png',
                                           u'profile_sidebar_fill_color': u'DDEEF6',
                                           u'profile_text_color': u'333333', u'followers_count': 11,
                                           u'profile_sidebar_border_color': u'C0DEED',
                                           u'id_str': u'4843024956',
                                           u'profile_background_color': u'F5F8FA',
                                           u'listed_count': 0,
                                           u'profile_background_image_url_https': u'',
                                           u'utc_offset': None, u'statuses_count': 122,
                                           u'description': None, u'friends_count': 12,
                                           u'location': None, u'profile_link_color': u'2B7BB9',
                                           u'profile_image_url': u'http://abs.twimg.com/sticky/default_profile_images/default_profile_0_normal.png',
                                           u'following': None, u'geo_enabled': False,
                                           u'profile_background_image_url': u'',
                                           u'name': u'Tara Petroff', u'lang': u'en',
                                           u'profile_background_tile': False,
                                           u'favourites_count': 7, u'screen_name': u'PetroffTara',
                                           u'notifications': None, u'url': None,
                                           u'created_at': u'Mon Feb 01 05:16:16 +0000 2016',
                                           u'contributors_enabled': False, u'time_zone': None,
                                           u'protected': False, u'default_profile': True,
                                           u'is_translator': False}, u'geo': None,
                                 u'in_reply_to_user_id_str': u'4842980294', u'lang': non_configured_lang,
                                 u'created_at': u'Thu Jun 09 03:08:14 +0000 2016',
                                 u'filter_level': u'low', u'in_reply_to_status_id_str': None,
                                 u'place': None}

        direct_message = {u'sender_screen_name': u'PetroffTara', u'recipient_id_str': u'4842980294',
                         u'sender':
                             {u'follow_request_sent': False, u'profile_use_background_image': True,
                              u'contributors_enabled': False, u'id': 4843024956, u'verified': False,
                              u'profile_image_url_https': u'https://abs.twimg.com/sticky/default_profile_images/default_profile_0_normal.png',
                              u'profile_sidebar_fill_color': u'DDEEF6',
                              u'profile_text_color': u'333333', u'followers_count': 11,
                              u'profile_sidebar_border_color': u'C0DEED', u'location': None,
                              u'default_profile_image': True, u'id_str': u'4843024956',
                              u'is_translation_enabled': False, u'utc_offset': None,
                              u'statuses_count': 125, u'description': None, u'friends_count': 12,
                              u'profile_link_color': u'2B7BB9',
                              u'profile_image_url': u'http://abs.twimg.com/sticky/default_profile_images/default_profile_0_normal.png',
                              u'notifications': False, u'geo_enabled': False,
                              u'profile_background_color': u'F5F8FA',
                              u'profile_background_image_url': None, u'name': u'Tara Petroff',
                              u'lang': u'en', u'following': False,
                              u'profile_background_tile': False, u'favourites_count': 8,
                              u'screen_name': u'PetroffTara', u'url': None,
                              u'created_at': u'Mon Feb 01 05:16:16 +0000 2016',
                              u'profile_background_image_url_https': None, u'time_zone': None,
                              u'protected': False, u'default_profile': True,
                              u'is_translator': False, u'listed_count': 0}
            , u'sender_id_str': u'4843024956', u'text': u'AAAA',
                         u'created_at': u'Wed Jun 15 13:04:51 +0000 2016', u'sender_id': 4843024956,
                         u'entities':
                             {u'symbols': [], u'user_mentions': [], u'hashtags': [], u'urls': []}
            , u'recipient_id': 4842980294, u'id_str': u'743066741715046403',
                         u'recipient_screen_name': u'jessy_makaroff', u'recipient':
                             {u'follow_request_sent': False, u'profile_use_background_image': True,
                              u'contributors_enabled': False, u'id': 4842980294, u'verified': False,
                              u'profile_image_url_https': u'https://pbs.twimg.com/profile_images/694016704918081536/dj7tqhRm_normal.png',
                              u'profile_sidebar_fill_color': u'DDEEF6',
                              u'profile_text_color': u'333333', u'followers_count': 13,
                              u'profile_sidebar_border_color': u'C0DEED', u'location': None,
                              u'default_profile_image': False, u'id_str': u'4842980294',
                              u'is_translation_enabled': False, u'utc_offset': None,
                              u'statuses_count': 7868, u'description': None, u'friends_count': 20,
                              u'profile_link_color': u'2B7BB9',
                              u'profile_image_url': u'http://pbs.twimg.com/profile_images/694016704918081536/dj7tqhRm_normal.png',
                              u'notifications': False, u'geo_enabled': False,
                              u'profile_background_color': u'F5F8FA',
                              u'profile_background_image_url': None, u'name': u'Jessy Petroff',
                              u'lang': u'en', u'following': False,
                              u'profile_background_tile': False, u'favourites_count': 2,
                              u'screen_name': u'jessy_makaroff', u'url': None,
                              u'created_at': u'Mon Feb 01 04:35:17 +0000 2016',
                              u'profile_background_image_url_https': None, u'time_zone': None,
                              u'protected': False, u'default_profile': True,
                              u'is_translator': False, u'listed_count': 4}
            , u'id': 743066741715046403}

        from solariat_bottle.daemons.helpers import twitter_dm_to_post_dict, \
            twitter_status_to_post_dict

        public_tweet_data = twitter_status_to_post_dict(public_tweet)
        direct_message_data = twitter_dm_to_post_dict(direct_message)
        # Overriding language to guarantee it's not a language from the channel configuration.
        # This makes get_language() bypass the internal language detection routine.
        direct_message_data['lang'] = non_configured_lang
        public_tweet_data['lang'] = non_configured_lang

        sc = TwitterServiceChannel.objects.create_by_user(
            self.user,
            account=self.account,
            title='TSC',
            status='Active')
        sc.set_allowed_langs(channel_langs)
        sc.add_keyword('@jessy_makaroff')
        sc.add_username('@jessy_makaroff')
        etc = EnterpriseTwitterChannel.objects.create_by_user(
            self.user,
            account=self.account,
            title='TA',
            status='Active',
            twitter_handle='jessy_makaroff')

        for data in [public_tweet_data, direct_message_data]:
            channels = get_tracked_channels('Twitter', data)
            self.assertEqual(channels, [sc.inbound_channel])
