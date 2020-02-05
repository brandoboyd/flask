from operator import itemgetter
from datetime import timedelta

from solariat_bottle.db.channel_stats import aggregate_stats
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.speech_act    import SpeechActMap
from solariat_bottle.tests.sin_bin.test_trends_endpoints import BaseEndpointCase, SingleLangMixin

from solariat.utils.timeslot import Timeslot, now

from .test_smarttags import SmartTagsBaseCase, get_data


DATE_TIME = "%Y-%m-%d %H:%M:%S"
DATE = "%m/%d/%Y"


def format_date(dt, format=DATE_TIME):
    return dt.strftime(format)


class ConversationTest(SmartTagsBaseCase, BaseEndpointCase, SingleLangMixin):
    def _get_number_of_posts(self, tag):
        channel_stats_map = aggregate_stats(
            self.user,
            [tag.id],
            from_=None,
            to_=None,
            level='month',
            aggregate=('number_of_posts',))
        return channel_stats_map.get(str(tag.id))['number_of_posts']

    def _reply_to_post(self, post):
        self._create_tweet(
            'Try this one ' + self.agent1.signature,
            channel=self.o,
            user_profile=self.agent1.user_profile,
            in_reply_to=post)

    def _get_trends(self, **kw):
        return self._fetch('/trends/json', **kw)

    def _get_posts(self, **kw):
        kw['from'] = format_date(kw['from'], DATE_TIME)
        kw['to'] = format_date(kw['to'], DATE_TIME)
        kw['thresholds'] = {"intention": 0.0}
        return self._fetch('/posts/json', **kw)

    def setUp(self):
        super(ConversationTest, self).setUp()

        #settings.DEBUG_STAT_UPDATE = False

        self.start_date = now()
        self.i = self.sc.inbound_channel
        self.o = self.sc.outbound_channel
        self.sc.add_username('@test')

        # Create 2 Smart Tags, for different use keywords
        self.laptop_tag = self._create_smart_tag(self.i, 'Laptops Tag', status='Active', keywords=['laptop'])
        self.display_tag = self._create_smart_tag(self.i, 'Other Tag', status='Active', keywords=['display'])

        self.from_ts_hour = Timeslot(point=self.start_date, level='hour')

    def test_tag_not_set_for_posts(self):
        ''' Make sure that when we add a tag, it appears as an accepted tag. We found a bug
        where 'smart_tags' was a cached property, and was thus not being updated on assignmnet.'''
        post = self._create_tweet('I need a canary',
                                  channel=self.i,
                                  user_profile=self.customer)
        self.assertEqual(post.accepted_smart_tags, [])
        foo_tag = self._create_smart_tag(self.i, 'Foo', status='Active', keywords=['Foo'])
        post.handle_add_tag(self.user, [foo_tag])
        post.reload()
        self.assertNotEqual(post.accepted_smart_tags, [])

    def test_tagging_replied_posts(self):
        ''' Make sure that when we tag a replied post, the proper stats are set'''
        post = self._create_tweet('I need a laptop',
                                  channel=self.i,
                                  user_profile=self.customer)

        self._create_tweet('Try this laptop. ' + self.agent1.signature,
                           channel=self.o,
                           user_profile=self.agent1.user_profile,
                           in_reply_to=post)

        # Reply changes post state, so reload.
        post.handle_add_tag(self.user, [self.display_tag])
        self._assertData(self.display_tag, [self.agent1], [SpeechActMap.ACTUAL], post)
        self._assertData(self.laptop_tag, None, [SpeechActMap.ACTUAL], post)
        self._assertData(self.display_tag, None, [SpeechActMap.ACTUAL], post)


    def test_channel_update_stats(self):
        """ Unit test directly the update stats for a channel """
        post = self._create_tweet('Foo random post', channel=self.i, user_profile=self.customer)
        # First test adding tags directly from update stats
        self.display_tag.update_stats(post, [self.display_tag], 'starred', 'discarded', {})
        self.laptop_tag.update_stats(post, [self.laptop_tag], 'starred', 'discarded', {})
        post.reload()
        self.assertTrue(post.tag_assignments[str(self.laptop_tag.id)] == 'starred')
        self.assertTrue(post.tag_assignments[str(self.display_tag.id)] == 'starred')


    def test_actionability_for_tags(self):
        ''' Adjusting the actionability of the parent should not by default
        impact the assignment status of the tag. It should only afffect the
        post status for which the tag is searchable.
        '''
        post = self._create_tweet('I need a laptop. I also need a display.',
                                  channel=self.i,
                                  user_profile=self.customer)

        self.assertEqual(len(post.accepted_smart_tags), 2)
        post.handle_reject(self.user, [self.i])
        self.assertEqual(len(post.accepted_smart_tags), 2)

    def test_tag_rendering(self):
        ''' Show only the relevant tags '''
        from solariat_bottle.utils.views import post_to_dict

        post1 = self._create_tweet('I need a laptop.',
                                  channel=self.i,
                                  user_profile=self.customer)

        self.assertEqual(post1.accepted_smart_tags, [self.laptop_tag])
        tags = dict([(str(self.laptop_tag.id), self.laptop_tag)])
        self.assertEqual([t['title'] for t in post_to_dict(post1, self.user, channel=self.i, tags=tags)['smart_tags']],
                         [self.laptop_tag.title])


    def test_tags_channel_filter(self):
        ''' A post with 2 utterances, and 2 tags. Generate a reply and confirm tag stats
        are synced correctly'''
        post1 = self._create_tweet('I need a laptop. My display is broken.',
                                  channel=self.i,
                                  user_profile=self.customer)

        self.assertEqual(post1.accepted_smart_tags, [self.laptop_tag, self.display_tag])

        # Post a reply. This will cause a change in the status. That should cause an update
        self._create_tweet('Try this one ' + self.agent1.signature,
                           channel=self.o,
                           user_profile=self.agent1.user_profile,
                           in_reply_to=post1)

        # should be actionable in channel & "laptop tag" and in "display" tag
        topics_channel, trends_channel, posts_channel = get_data(self.i, self.from_ts_hour, agents=None, statuses=[SpeechActMap.ACTUAL])
        topics_tag1, trends_tag1, posts_tag1 = get_data(self.laptop_tag, self.from_ts_hour, agents=None, statuses=[SpeechActMap.ACTUAL])
        topics_tag2, trends_tag2, posts_tag2 = get_data(self.display_tag, self.from_ts_hour, agents=None, statuses=[SpeechActMap.ACTUAL])
        # 2 hot topics
        self.assertEqual(set(map(itemgetter('topic'), topics_channel)), {'laptop', 'display'})
        # __ALL__ topic count is 2
        self.assertEqual(trends_channel['list'][0]['count'], 2)
        self.assertEqual(posts_channel, [post1])

        # verify all synced
        self.assertEqual(sorted(topics_channel, key=lambda x: x['topic']),
                         sorted(topics_tag1, key=lambda x: x['topic']))
        self.assertEqual(sorted(topics_channel, key=lambda x: x['topic']),
                         sorted(topics_tag2, key=lambda x: x['topic']))
        self.assertEqual(trends_channel, trends_tag1)
        self.assertEqual(trends_channel, trends_tag2)
        self.assertEqual(posts_channel, posts_tag1)
        self.assertEqual(posts_channel, posts_tag2)

    def test_potential_stats(self):
        ''' Initial stats are good and complies with tag assignment '''
        post = self._create_tweet('I need a laptop',
                                  channel=self.i,
                                  user_profile=self.customer)

        # Just one tag
        self.assertEqual(post.accepted_smart_tags, [self.laptop_tag])
        self.assertEqual(sorted([str(tag.id) for tag in post.available_smart_tags]),
                         sorted([str(self.laptop_tag.id), str(self.display_tag.id)]))

        # We whould see the stats for POTENTIAL case, for both the channel, and the laptop_tag
        topics_channel, trends_channel, posts_channel = get_data(self.i, self.from_ts_hour, None, statuses=[SpeechActMap.POTENTIAL])
        topics_tag1, trends_tag1, posts_tag1 = get_data(self.laptop_tag, self.from_ts_hour, None, statuses=[SpeechActMap.POTENTIAL])
        self.assertEqual(topics_channel, topics_tag1)
        self.assertEqual(trends_channel, trends_tag1)
        self.assertEqual(posts_channel, posts_tag1)

    def test_actionable_stats(self):
        '''We reply to make a post actionable next time around.'''
        ''' Initial stats are good and complies with tag assignment '''

        post  = self._create_tweet('I need a laptop',
                                   channel=self.i,
                                   user_profile=self.customer)
        self._create_tweet('Try this one ' + self.agent1.signature,
                           channel=self.o,
                           user_profile=self.agent1.user_profile,
                           in_reply_to=post)
        post  = self._create_tweet('I need a laptop',
                                   channel=self.i,
                                   user_profile=self.customer)
        topics_channel, trends_channel, posts_channel = get_data(self.i, self.from_ts_hour, None, statuses=[SpeechActMap.ACTIONABLE])
        topics_tag1, trends_tag1, posts_tag1 = get_data(self.laptop_tag, self.from_ts_hour, None, statuses=[SpeechActMap.ACTIONABLE])
        self.assertEqual(topics_channel, topics_tag1)
        self.assertEqual(trends_channel, trends_tag1)
        self.assertEqual(posts_channel, posts_tag1)

    def test_adding_and_removing(self):
        '''
        Tests that when a tag is added to three posts
        number_of_posts for that tag is 3 and when
        all tags are removed count for that tag is 0.
        '''

        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        post1 = self._create_tweet('@test I need a laptop 1',
                                   channel=self.i,
                                   user_profile=customer1)

        customer2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer2'))
        post2 = self._create_tweet('@test I need a laptop 2',
                                   channel=self.i,
                                   user_profile=customer2)

        customer3 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer3'))
        post3 = self._create_tweet('@test I need a laptop 3',
                                   channel=self.i,
                                   user_profile=customer3)

        foo_tag = self._create_smart_tag(self.i, 'Foo', status='Active')

        post1.handle_add_tag(self.user, [foo_tag])
        # one post is 'starred', other two are 'highlighted'
        self.assertEqual(self._get_number_of_posts(foo_tag), 3)
        post2.reload()
        self.assertTrue(foo_tag.is_assigned(post2))
        post2.handle_add_tag(self.user, [foo_tag])
        self.assertEqual(self._get_number_of_posts(foo_tag), 3)
        post3.reload()
        post3.handle_add_tag(self.user, [foo_tag])
        self.assertEqual(self._get_number_of_posts(foo_tag), 3)

        post1.handle_remove_tag(self.user, [foo_tag])
        post2.handle_remove_tag(self.user, [foo_tag])
        post3.handle_remove_tag(self.user, [foo_tag])

        self.assertEqual(self._get_number_of_posts(foo_tag), 0)

    def test_adding_and_removing_trends_json(self):
        '''
        Check `trends/json` endpoint.
        Similar to `ConversationTest.test_adding_and_removing`
        only for data that's used in plots.
        Stats should be zero at the end.
        '''

        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        post1 = self._create_tweet('@test I need a laptop 1',
                                   channel=self.i,
                                   user_profile=customer1)

        customer2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer2'))
        post2 = self._create_tweet('@test I need a laptop 2',
                                   channel=self.i,
                                   user_profile=customer2)

        customer3 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer3'))
        post3 = self._create_tweet('@test I need a laptop 3',
                                   channel=self.i,
                                   user_profile=customer3)

        foo_tag = self._create_smart_tag(self.i, 'Foo', status='Active')

        post1.handle_add_tag(self.user, [foo_tag])
        # one post is 'starred', other two are 'highlighted'
        self.assertEqual(self._get_number_of_posts(foo_tag), 3)
        post2.reload()
        self.assertTrue(foo_tag.is_assigned(post2))
        post2.handle_add_tag(self.user, [foo_tag])
        self.assertEqual(self._get_number_of_posts(foo_tag), 3)
        post3.reload()
        post3.handle_add_tag(self.user, [foo_tag])
        self.assertEqual(self._get_number_of_posts(foo_tag), 3)

        trends = self._get_trends(**{
            'channel_id': str(foo_tag.id),
            'from': self.created_on_str,
            'to': self.created_on_str,
            'level': 'hour',
            'topics': [],
            'intentions': ['needs'],
        })
        self.assertEqual(trends[0]['count'], 3)

        post1.handle_remove_tag(self.user, [foo_tag])
        post2.handle_remove_tag(self.user, [foo_tag])
        post3.handle_remove_tag(self.user, [foo_tag])

        trends = self._get_trends(**{
            'channel_id': str(foo_tag.id),
            'from': self.created_on_str,
            'to': self.created_on_str,
            'level': 'hour',
            'topics': [],
            'intentions': ['needs'],
        })
        # zero counts are removed from the response, so trends should be empty
        self.assertEqual(len(trends), 0)

    def test_reject_accept(self):
        '''
        Check `trends/json` endpoint.
        Similar to `test_adding_and_removing_trends_json`
        only first apply the tag, reject a post, and accept it again.
        Check both tag stats and overall stats.

        1. Have one actionable post.
        2. Tag it with 'Foo'.
        3. Reject it.
        4. Make it actionable again.

        Check that trends for actionable have 1.
        Check that trends for rejected have 0.
        '''

        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        post1 = self._create_tweet(
            '@test I need a laptop 1',
            channel=self.i,
            user_profile=customer1)
        foo_tag = self._create_smart_tag(self.i, 'Foo', status='Active')
        post1.handle_add_tag(self.user, [foo_tag])
        post1.handle_reject(self.user, [self.i])
        post1.handle_accept(self.user, [self.i])

        data = {
            'from': self.created_on_str,
            'to': self.created_on_str,
            'level': 'hour',
            'topics': [],
            'intentions': ['needs'],
        }

        # inbound channel, rejected
        data['channel_id'] = str(self.i.id)
        data['statuses'] = ['rejected']
        trends = self._get_trends(**data)
        self.assertEqual(len(trends), 0)

        # inbound channel, actionable
        data['channel_id'] = str(self.i.id)
        data['statuses'] = ['actionable']
        trends = self._get_trends(**data)
        self.assertEqual(len(trends), 1)
        self.assertEqual(trends[0]['count'], 1)

        # tag channel, rejected
        data['channel_id'] = str(foo_tag.id)
        data['statuses'] = ['rejected']
        trends = self._get_trends(**data)
        self.assertEqual(len(trends), 0)

        # tag channel, actionable
        data['channel_id'] = str(foo_tag.id)
        data['statuses'] = ['actionable']
        trends = self._get_trends(**data)
        self.assertEqual(len(trends), 1)
        self.assertEqual(trends[0]['count'], 1)

    def test_several_tags_trends(self):
        '''
        Check `trends/json` endpoint when several tags are requested by `channel_id`.
        '''

        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        post1 = self._create_tweet('@test I need a laptop 1',
                                   channel=self.i,
                                   user_profile=customer1)

        customer2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer2'))
        post2 = self._create_tweet('@test I need a laptop 2',
                                   channel=self.i,
                                   user_profile=customer2)

        customer3 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer3'))
        post3 = self._create_tweet('@test I need a laptop 3',
                                   channel=self.i,
                                   user_profile=customer3)

        foo_tag = self._create_smart_tag(self.i, 'Foo', status='Active')
        bar_tag = self._create_smart_tag(self.i, 'Bar', status='Active')

        post1.handle_add_tag(self.user, [foo_tag])
        # remove tag from other two posts since they were highlighted
        post2.handle_remove_tag(self.user, [foo_tag])
        post3.handle_remove_tag(self.user, [foo_tag])

        post2.handle_add_tag(self.user, [bar_tag])
        # remove tag from other two posts since they were highlighted
        post1.handle_remove_tag(self.user, [bar_tag])
        post3.handle_remove_tag(self.user, [bar_tag])

        # one post with foo_tag
        trends = self._get_trends(**{
            'channel_id': str(foo_tag.id),
            'from': self.created_on_str,
            'to': self.created_on_str,
            'level': 'hour',
            'topics': [],
            'intentions': ['needs'],
        })
        self.assertEqual(trends[0]['count'], 1)

        # two posts with foo_tag and bar_tag
        trends = self._get_trends(**{
            'channel_id': [str(foo_tag.id), str(bar_tag.id)],
            'from': self.created_on_str,
            'to': self.created_on_str,
            'level': 'hour',
            'topics': [],
            'intentions': ['needs'],
        })
        self.assertEqual(trends[0]['count'], 2)

    def test_several_tags_posts(self):
        '''
        Check `posts/json` endpoint when several tags are requested by `channel_id`.
        '''

        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        post1 = self._create_tweet('@test I need a laptop 1',
                                   channel=self.i,
                                   user_profile=customer1)

        customer2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer2'))
        post2 = self._create_tweet('@test I need a laptop 2',
                                   channel=self.i,
                                   user_profile=customer2)

        customer3 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer3'))
        post3 = self._create_tweet('@test I need a laptop 3',
                                   channel=self.i,
                                   user_profile=customer3)

        foo_tag = self._create_smart_tag(self.i, 'Foo', status='Active')
        bar_tag = self._create_smart_tag(self.i, 'Bar', status='Active')

        post1.handle_add_tag(self.user, [foo_tag])
        # remove tag from other two posts since they were highlighted
        post2.handle_remove_tag(self.user, [foo_tag])
        post3.handle_remove_tag(self.user, [foo_tag])

        post2.handle_add_tag(self.user, [bar_tag])
        # remove tag from other two posts since they were highlighted
        post1.handle_remove_tag(self.user, [bar_tag])
        post3.handle_remove_tag(self.user, [bar_tag])

        # one post with foo_tag
        posts = self._get_posts(**{
            'channel_id': str(foo_tag.id),
            'from': now(),
            'to': now() + timedelta(minutes=1),
            'level': 'hour',
            'topics': [],
            'intentions': ['needs'],
        })
        self.assertEqual(len(posts), 1)

        # two posts with foo_tag and bar_tag
        posts = self._get_posts(**{
            'channel_id': [str(foo_tag.id), str(bar_tag.id)],
            'from': now(),
            'to': now() + timedelta(minutes=1),
            'level': 'hour',
            'topics': [],
            'intentions': ['needs'],
        })
        self.assertEqual(len(posts), 2)

    def test_remove_automatically_assigned(self):
        '''
        Test manually removing a tag from a post to which is was automatically added and removed.

        Scenario:

        1. Make a post about foo (1).
        2. Create another post about foo (2).
        3. Create another post about foo (3).
        4. Create a post about bar (4).
        5. Add bar tag to bar post.
        6. Remove bar tags from first three posts.

        Check that trends for bar tag have 1 post.
        '''

        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        post1 = self._create_tweet(
            '@test I need foo 1',
            channel=self.i,
            user_profile=customer1)
        post2 = self._create_tweet(
            '@test I need foo 2',
            channel=self.i,
            user_profile=customer1)
        post3 = self._create_tweet(
            '@test I need foo 3',
            channel=self.i,
            user_profile=customer1)
        post4 = self._create_tweet(
            '@test I need bar 1',
            channel=self.i,
            user_profile=customer1)
        bar_tag = self._create_smart_tag(self.i, 'Bar', status='Active')
        post4.handle_add_tag(self.user, [bar_tag])
        post3.handle_remove_tag(self.user, [bar_tag])
        post2.handle_remove_tag(self.user, [bar_tag])
        post1.handle_remove_tag(self.user, [bar_tag])

        data = {
            'from': self.created_on_str,
            'to': self.created_on_str,
            'level': 'hour',
            'topics': [],
            'intentions': ['needs'],
            'statuses': ['actionable'],
        }

        # bar tag channel, actionable
        data['channel_id'] = str(bar_tag.id)
        trends = self._get_trends(**data)
        self.assertEqual(len(trends), 1)
        self.assertEqual(trends[0]['count'], 1)

