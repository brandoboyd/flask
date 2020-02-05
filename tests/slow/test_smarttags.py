from datetime import datetime, timedelta
import unittest

import mock
from itsdangerous import URLSafeSerializer

from solariat.mail import Mail

from solariat_bottle import settings
from solariat_bottle.configurable_apps import APP_GSA
from solariat_bottle.settings import UNSUBSCRIBE_KEY, UNSUBSCRIBE_SALT
from solariat_bottle.app import app
from solariat_bottle.db.roles import AGENT
from solariat_bottle.db.account import Account, AccountEvent
from solariat_bottle.db.post.base import Post
from solariat_bottle.db.speech_act import SpeechActMap
from solariat_bottle.db.conversation import Conversation
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.channel.base import Channel, SmartTagChannel
from solariat_bottle.db.contact_label import ExplcitTwitterContactLabel
from solariat_bottle.db.message_queue import TaskMessage
from solariat_bottle.db.channel.twitter import TwitterServiceChannel, TwitterTestDispatchChannel
from solariat_bottle.db.channel_hot_topics import ChannelHotTopics
from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
from solariat_bottle.utils.id_encoder import ALL_TOPICS
from solariat.utils.timeslot import Timeslot, now
from solariat_bottle.tests.base import MainCase, UICase, fake_twitter_url


FAKE_NOW = [2015, 1, 1, 0, 0, 0]

class FakeDatetime(datetime):
    @classmethod
    def now(cls):
        return cls(*FAKE_NOW)


def get_posts(channel, term, from_ts, statuses=None, agents=None):
    res, are_more_posts_available = Post.objects.by_time_point(
        channel, term,
        from_ts  = from_ts,
        status   = statuses,
        agents   = agents,
        min_conf = 0.0
    )
    return list(res)

def get_hot_topics(channel, statuses=None, agents=None):
    from_ts = Timeslot(level='month')
    res = ChannelHotTopics.objects.by_time_span(
        channel,
        parent_topic = None,
        intentions   = None,
        statuses     = statuses,
        agents       = agents,
        from_ts      = from_ts)
    return res

def get_term_stats(channel, term, from_ts, statuses=None, agents=None, plot_type='topics'):

    stats = ChannelTopicTrends.objects.by_time_span(
        channel,
        topic_pairs = [[term, False]],
        from_ts     = from_ts,
        agents = agents,
        statuses = statuses,
        plot_type=plot_type
    )
    return stats

def get_channel_stats(user, channel):
    from solariat_bottle.db.channel_stats import aggregate_stats

    return aggregate_stats(user, channel.id,
                           from_=None, to_=None, level='month',
                           aggregate=('number_of_posts', 'number_of_assigned_posts'))[str(channel.id)]

def get_data(channel, from_ts, agents, statuses, plot_type='topics'):
    hot_topics = get_hot_topics(channel, agents=agents, statuses=statuses)
    trends = get_term_stats(channel, ALL_TOPICS, from_ts=from_ts, agents=agents, statuses=statuses, plot_type=plot_type)
    posts = get_posts(channel, ALL_TOPICS, from_ts=from_ts, agents=agents, statuses=statuses)
    return hot_topics, trends, posts


class SmartTagsTestHelper(object):
    def _create_smart_tag(self, channel, name, **kw):
        stc = SmartTagChannel.objects.create_by_user(
            self.user,
            title=name,
            parent_channel=channel.id,
            account=channel.account,
            **kw)
        return stc

    def _create_agent(self, email, signature, screen_name=None, roles=None):
        roles = roles or [AGENT]
        user = self._create_db_user(email=email, password='1', account=self.account, roles=roles)
        user.account = self.account
        user.signature = signature
        if screen_name:
            user.user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        user.save()
        self.sc.add_agent(user)
        return user

    def _create_contact_label(self,name,**kw):
        label = ExplcitTwitterContactLabel.objects.create_by_user(
            self.user,
            **kw
        )
        return label

    def _setup_channel(self):
        self.account = Account.objects.get_or_create(name="TestAcct")
        self.user.account = self.account
        self.user.accounts.append(self.account.id)
        self.user.save()
        self.sc = TwitterServiceChannel.objects.get_or_create(title="TwitterServiceChannel",
                                                              account=self.account)
        self.sc.add_perm(self.user)

        # Agents and customer
        self.customer = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        self.agent1 = self._create_agent('agent@test.test', 'A1', '@agent1')
        self.agents = [self.agent1]
        self.url = fake_twitter_url('customer')
        outbound_channel = TwitterTestDispatchChannel.objects.get_or_create(title="OutboundChannel",
                                                                            account=self.account)
        outbound_channel.add_perm(self.user)
        outbound_channel._auth_flag = True
        outbound_channel.twitter_handle = 'solariat'
        outbound_channel.save()
        outbound_channel.on_active()

class SmartTagsBaseCase(MainCase, SmartTagsTestHelper):
    def setUp(self):
        self.orig_filter_cls = settings.get_var('CHANNEL_FILTER_CLS')
        settings.CHANNEL_FILTER_CLS = 'DbChannelFilter'
        super(SmartTagsBaseCase, self).setUp()
        self._setup_channel()

        #ChannelTopicTrends.objects.remove()
        #ChannelHotTopics.objects.remove()

    def tearDown(self):
        settings.CHANNEL_FILTER_CLS = self.orig_filter_cls
        super(SmartTagsBaseCase, self).tearDown()

    def _assertData(self, channel, agents, status, post):
        """Verify topics/trends/posts data for the post"""
        start_date = now() - timedelta(seconds=2)
        from_ts_hour = Timeslot(point=start_date, level='hour')

        topics, terms, posts = get_data(channel, from_ts_hour, agents=agents, statuses=status)
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]['topic'], post.punks[0])
        self.assertEqual(terms['list'][0]['count'], 1)
        self.assertEqual(posts, [post])

        return topics, terms, posts

    def _assertNoData(self, channel, agents, status):
        start_date = now() - timedelta(hours=12)
        from_ts_hour = Timeslot(point=start_date, level='hour')

        topics, terms, posts = get_data(channel, from_ts_hour, agents=agents, statuses=status)
        self.assertFalse(topics)
        self.assertFalse(terms['list'])
        self.assertFalse(posts)

class SmartTagAssignment(SmartTagsBaseCase, UICase):

    def setUp(self):
        super(SmartTagAssignment, self).setUp()
        self.account.update(selected_app=APP_GSA)
        self.i = self.sc.inbound_channel
        self.o = self.sc.outbound_channel

        self.o.usernames = ['solariat']
        self.o.save()

        # Create 2 Smart Tags, for different use keywords
        self.laptop_tag = self._create_smart_tag(self.i, 'Laptops Tag', status='Active', keywords=['laptop'])
        self.laptop_tag_outbound = self._create_smart_tag(self.o, 'Laptops Tag', status='Active', keywords=['laptop'])
        self.other_tag = self._create_smart_tag(self.i, 'Other Tag', status='Active', keywords=['support', 'help'])
        self.other_tag_outbound = self._create_smart_tag(self.o, 'Other Tag', status='Active', keywords=['support', 'help'])

        url = fake_twitter_url(self.customer.user_name)


    def test_assignment_clocking(self):
        '''
        If a tag has been manually assigned, or manually rejected, we should not
        revert it automatically
        '''

        p1 = self._create_tweet('@solariat I need shoes',
                                  channel=self.i,
                                  user_profile=self.customer)
        p2 = self._create_tweet('@solariat I need shoes',
                                  channel=self.i,
                                  user_profile=self.customer)
        p3 = self._create_tweet('@solariat I need shoes',
                                  channel=self.i,
                                  user_profile=self.customer)
        p4 = self._create_tweet('@solariat I need shoes',
                                  channel=self.i,
                                  user_profile=self.customer)

        # Lets create a Tag, and verify propagation
        cookie_tag = self._create_smart_tag(self.i, 'Cookies Tag', status='Active')
        p1.handle_add_tag(self.user, [cookie_tag])
        self.assertFalse(cookie_tag.is_mutable(p1))
        p4.reload()
        self.assertTrue(cookie_tag.is_assigned(p4))
        self.assertTrue(cookie_tag.is_mutable(p4))

        # Now remove it from the system assigned one, and make sure the original
        # assignment remains
        p4.handle_remove_tag(self.user, cookie_tag)
        self.assertTrue(cookie_tag.is_assigned(p1))

        # Now remove original, and verify propagation
        p1.handle_remove_tag(self.user, [cookie_tag])
        p1.reload()
        p3.reload()
        self.assertFalse(cookie_tag.is_assigned(p3))

    @unittest.skip("Response is deprecated now")
    def test_tag_response_assignment(self):
        '''
        Make sure tags are properly updated for the response as the post is added.
        '''
        post = self._create_tweet('@solariat I need a laptop',
                                  channel=self.i,
                                  user_profile=self.customer)
        # Verify initial response has the expected tags
        response = Response.objects.upsert_from_post(post)
        self.assertEqual(response.tags, [self.laptop_tag.id])

        post = self._create_tweet('@solariat Please - I need help!',
                                  channel=self.i,
                                  user_profile=self.customer)

        # Verify the union of tags
        response = Response.objects.upsert_from_post(post)
        self.assertEqual(set(response.tags), set([self.other_tag.id, self.laptop_tag.id]))
        conv = Conversation.objects()[:][0]
        conv.is_closed = True
        conv.save(is_safe=True)
        post.handle_remove_tag(self.user, [self.other_tag])

        response.reload()
        self.assertEqual(set(response.tags), set([self.laptop_tag.id], ))

    @unittest.skip("Deprecating this case since Responses are deprecated now")
    def test_filtered_response_action_propagation(self):
        self.login()
        first_laptop_post = self._create_tweet('@solariat I need a laptop',
                                               channel=self.i,
                                               user_profile=self.customer)
        customer2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer2'))
        self.url = fake_twitter_url('customer2')
        second_laptop_post = self._create_tweet('@solariat I need another laptop',
                                               channel=self.i,
                                               user_profile=customer2)
        customer3 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer3'))
        self.url = fake_twitter_url('customer3')
        third_laptop_post = self._create_tweet('@solariat I need a third laptop',
                                               channel=self.i,
                                               user_profile=customer3)
        customer4 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer4'))
        self.url = fake_twitter_url('customer4')
        fourth_laptop_post = self._create_tweet('@solariat I need a fourth laptop',
                                                channel=self.i,
                                                user_profile=customer4)
        # At this point we should have accepted / rejected counts of 0 both
        # for the smart tag and inbound channel. Also posts should be in a
        # 'highlighted' state since they were just assigned by the system
        self.assertEqual(self.i.channel_filter.accept_count, 0)
        self.assertEqual(self.i.channel_filter.reject_count, 0)
        self.assertEqual(self.laptop_tag.channel_filter.accept_count, 0)
        self.assertEqual(self.laptop_tag.channel_filter.reject_count, 0)
        self.assertEqual(first_laptop_post.channel_assignments,
                         {str(self.i.id) : 'highlighted'})
        self.assertEqual(first_laptop_post.tag_assignments,
                         {str(self.laptop_tag.id) : 'highlighted', str(self.other_tag.id) : 'discarded'})
        # Now post a response, with a filtered tag and check propagation
        resp = Response.objects.get(_latest_post_id=first_laptop_post.id)
        self.client.post('/commands/post_response',
                         data='{"response":"%s","matchable":"%s","latest_post":"%s","tag":"%s"}' % (
                         str(resp.id), str(resp.matchable.id),
                         str(resp.post.id), str(self.laptop_tag.id)))
        first_laptop_post.reload()
        self.laptop_tag.reload()
        self.i.reload()
        # At this point, the accepted count should be 1 for both, reject count still 0
        # Also, `highlighted` states should be passed into the `starred` state
        self.i.channel_filter.reset_counters()
        self.laptop_tag.channel_filter.reset_counters()
        self.assertEqual(self.i.channel_filter.accept_count, 1)
        self.assertEqual(self.i.channel_filter.reject_count, 0)
        self.assertEqual(self.laptop_tag.channel_filter.accept_count, 1)
        self.assertEqual(self.laptop_tag.channel_filter.reject_count, 0)
        self.assertEqual(first_laptop_post.channel_assignments,
                         {str(self.i.id): 'replied'})
        self.assertEqual(first_laptop_post.tag_assignments,
                         {str(self.laptop_tag.id): 'starred', str(self.other_tag.id): 'discarded'})

        # Now do another post response, only this time don't do it while filtering by
        # tag. At this point, the channel should learn but this should not influence smart tag
        self.assertEqual(second_laptop_post.channel_assignments,
                         {str(self.i.id) : 'highlighted'})
        self.assertEqual(second_laptop_post.tag_assignments,
                         {str(self.laptop_tag.id) : 'highlighted', str(self.other_tag.id) : 'discarded'})
        # Now post a response, with a filtered tag and check propagation
        resp = Response.objects.get(_latest_post_id=second_laptop_post.id)
        self.client.post('/commands/post_response',
                         data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (str(resp.id),
                                                                                         str(resp.matchable.id),
                                                                                         str(resp.post.id)))
        second_laptop_post.reload()
        self.laptop_tag.reload()
        self.i.reload()
        # At this point, the accepted count should be 2 for channel, 1 for tag, reject count still 0
        # Also, `highlighted` states should be passed into the `starred` state for channel
        # but should still be `highlighted` for smart tag
        self.i.channel_filter.reset_counters()
        self.laptop_tag.channel_filter.reset_counters()
        self.assertEqual(self.i.channel_filter.accept_count, 2)
        self.assertEqual(self.i.channel_filter.reject_count, 0)
        self.assertEqual(self.laptop_tag.channel_filter.accept_count, 1)
        self.assertEqual(self.laptop_tag.channel_filter.reject_count, 0)
        self.assertEqual(second_laptop_post.channel_assignments,
                         {str(self.i.id) : 'replied'})
        self.assertEqual(second_laptop_post.tag_assignments,
                         {str(self.laptop_tag.id) : 'highlighted', str(self.other_tag.id) : 'discarded'})

        # Now do a post reject while filtering by a smart
        # tag. At this point, the channel should learn but this and tag aswell
        self.assertEqual(third_laptop_post.channel_assignments,
                         {str(self.i.id) : 'highlighted'})
        self.assertEqual(third_laptop_post.tag_assignments,
                         {str(self.laptop_tag.id) : 'highlighted', str(self.other_tag.id) : 'discarded'})
        # Now post a response, with a filtered tag and check propagation
        third_laptop_post.reload()
        self.laptop_tag.reload()
        self.i.reload()
        # At this point, the accepted count should be 2 for channel, 1 for tag,
        # reject count should go up for both
        # Also, `highlighted` states should be passed into the `rejected`
        self.i.channel_filter.reset_counters()
        self.laptop_tag.channel_filter.reset_counters()
        self.assertEqual(self.i.channel_filter.accept_count, 2)
        self.assertEqual(self.i.channel_filter.reject_count, 1)
        self.assertEqual(self.laptop_tag.channel_filter.accept_count, 1)
        self.assertEqual(self.laptop_tag.channel_filter.reject_count, 1)
        self.assertEqual(third_laptop_post.channel_assignments,
                         {str(self.i.id) : 'rejected'})
        self.assertEqual(third_laptop_post.tag_assignments,
                         {str(self.laptop_tag.id) : 'rejected', str(self.other_tag.id) : 'discarded'})

        # Now do a post reject without filtering by a smart
        # tag. At this point, the channel should learn but not the tag
        self.assertEqual(fourth_laptop_post.channel_assignments,
                         {str(self.i.id) : 'highlighted'})
        self.assertEqual(fourth_laptop_post.tag_assignments,
                         {str(self.laptop_tag.id) : 'highlighted', str(self.other_tag.id) : 'discarded'})
        # Now post a response, with a filtered tag and check propagation
        fourth_laptop_post.reload()
        self.laptop_tag.reload()
        self.i.reload()
        # At this point, the accepted count should be 2 for channel, 1 for tag,
        # reject count should go up for both
        # Also, `highlighted` states should be passed into the `rejected`
        self.i.channel_filter.reset_counters()
        self.laptop_tag.channel_filter.reset_counters()
        self.assertEqual(self.i.channel_filter.accept_count, 2)
        self.assertEqual(self.i.channel_filter.reject_count, 2)
        self.assertEqual(self.laptop_tag.channel_filter.accept_count, 1)
        self.assertEqual(self.laptop_tag.channel_filter.reject_count, 1)
        self.assertEqual(fourth_laptop_post.channel_assignments,
                         {str(self.i.id) : 'rejected'})
        self.assertEqual(fourth_laptop_post.tag_assignments,
                         {str(self.laptop_tag.id) : 'highlighted', str(self.other_tag.id) : 'discarded'})


    @unittest.skip("Response is deprecated")
    def test_tag_response_filtering(self):
        '''
        Make sure tags are properly updated for the response as the post is added.
        '''
        laptop_post = self._create_tweet('@solariat I need a laptop',
                                  channel=self.i,
                                  user_profile=self.customer)
        # Verify initial response has the expected tags
        response = Response.objects.upsert_from_post(laptop_post)
        self.assertEqual(response.tags, [self.laptop_tag.id])

        response.reload()
        self.assertEqual([self.laptop_tag.id], response.tags)
        # Now create a second tag, this one should have both tags assigned

        support_post = self._create_tweet('@solariat I need some support',
                                  channel=self.i,
                                  user_profile=self.customer)
        response.reload()
        self.assertEqual(set([self.laptop_tag.id, self.other_tag.id]), set(response.tags))

        # Now if we create a new post with junk, this should not change tag assignments
        self._create_tweet('@solariat This is junk',
                                  channel=self.i,
                                  user_profile=self.customer)

        response.reload()
        self.assertTrue(len(response.tags) == 2)
        self.assertEqual(set([self.laptop_tag.id, self.other_tag.id]), set(response.tags))

        # Create a new post which should be assigned both the tags, this should get
        # new response tags created.
        support_laptop = self._create_tweet('@solariat I need some support with my laptop',
                                  channel=self.i,
                                  user_profile=self.customer)

        response.reload()
        self.assertTrue(len(response.tags) == 2)
        self.assertEqual(set([self.laptop_tag.id, self.other_tag.id]), set(response.tags))
        self.assertEqual(set([self.laptop_tag.id, self.other_tag.id]), set(t.id for t in support_laptop.accepted_smart_tags))

        # If we remove the laptop tag, that should be propagated back to the
        # previous post with the tag
        support_laptop.handle_remove_tag(self.user, [self.laptop_tag])
        response.reload()
        self.assertEqual(len(response.tags), 1)
        laptop_post.handle_add_tag(self.user, [self.laptop_tag])
        response.reload()
        self.assertEqual(len(response.tags), 2)

        # Now if we remove the tag also from the laptop post, no other response
        # tag should exist for that tag
        laptop_post.handle_remove_tag(self.user, [self.laptop_tag])
        response.reload()
        self.assertEqual(len(response.tags), 1)
        self.assertEqual(response.tags, [self.other_tag.id])

        # Also check that we return the correct post from engage page
        junk_latest = self._create_tweet('@solariat This is more junk',
                                  channel=self.i,
                                  user_profile=self.customer)
        self.assertFalse(set(t.id for t in junk_latest.accepted_smart_tags))

        import json
        base_filter = {'channel_id': None,
                       'intentions': ['asks','consideration','needs','likes','problem']
                       }
        self.login()

        base_filter['channel_id'] = str(self.other_tag.id)
        resp = self.client.post('/responses/json',
                                data=json.dumps(base_filter),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertTrue('list' in data)
        self.assertTrue(len(data['list']) == 1)
        self.assertTrue(data['list'][0]['post']['id_str'] == str(support_laptop.id))

        base_filter['channel_id'] = str(self.laptop_tag.id)
        resp = self.client.post('/responses/json',
                                data=json.dumps(base_filter),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertTrue('list' in data)
        self.assertTrue(len(data['list']) == 0)

        base_filter['channel_id'] = str(self.i.id)
        resp = self.client.post('/responses/json',
                                data=json.dumps(base_filter),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertTrue('list' in data)
        self.assertTrue(len(data['list']) == 1)
        self.assertTrue(data['list'][0]['post']['id_str'] == str(junk_latest.id))


    @unittest.skip("Response is deprecated")
    def test_tag_response_removal(self):
        ''' Create a bunch of posts with alternate tags '''

        post = self._create_tweet('@solariat I need a laptop',
                                  channel=self.i,
                                  user_profile=self.customer)
        post = self._create_tweet('@solariat I need a laptop bag',
                                  channel=self.i,
                                  user_profile=self.customer)
        post = self._create_tweet('@solariat I love my laptop case',
                                  channel=self.i,
                                  user_profile=self.customer)

        post = self._create_tweet('@solariat I love my laptop case',
                                  channel=self.i,
                                  user_profile=self.customer)


        response = Response.objects.upsert_from_post(post)

        self.assertEqual(len(response.posts), 4)
        self.assertEqual(len(response.tags), 1)

        # Remove tag for Likes
        response.posts[2].handle_remove_tag(self.user, [self.laptop_tag])
        # Add tag for Needs: Reinforcing It
        response.posts[0].handle_add_tag(self.user, [self.laptop_tag])
        response.reload()
        self.assertFalse(self.laptop_tag.is_assigned(response.posts[2]))
        self.assertFalse(self.laptop_tag.is_assigned(response.posts[3]))
        self.assertEqual(len(response.tags), 1)

        # Add a post, bumping up tagc count, but themn remove it.
        post = self._create_tweet('@solariat Support please',
                                  channel=self.i,
                                  user_profile=self.customer)

        # Not enough to reload, because of cached conversation property
        response = Response.objects.upsert_from_post(post)
        self.assertTrue(post.id in [r.id for r in response.posts])
        self.assertEqual(len(response.tags), 2)
        response.posts[4].handle_remove_tag(self.user, [self.other_tag])
        response.update_and_check_fit(self.other_tag)
        response.reload()
        self.assertEqual(len(response.tags), 1)


    @unittest.skip("Response is deprecated")
    def test_tag_response_assignment_by_system(self):
        '''
        Initially posts will not be tagged. But assignment will trigger
        learning and propagation, which will also cause assignment to anopther
        '''

        p1 = self._create_tweet('@solariat I love cookies',
                                  channel=self.i,
                                  user_profile=self.customer)
        r1 = Response.objects.upsert_from_post(p1)
        r1.status = "rejected"
        r1.save()
        self.assertEqual(r1.tags, [])

        p2 = self._create_tweet('@solariat I love cookies',
                                  channel=self.i,
                                  user_profile=self.customer)
        r2 = Response.objects.upsert_from_post(p2)

        # Create and assign a tag
        cookie_tag = self._create_smart_tag(self.i, 'Cookies Tag', status='Active')
        p2.handle_add_tag(self.user, [cookie_tag])
        r2.reload()
        self.assertEqual(r2.tags, [cookie_tag.id])
        # Check Impact
        p1.reload()
        self.assertTrue(cookie_tag.is_assigned(p1))
        r1.reload()
        self.assertEqual(r1.tags, [cookie_tag.id])

    def test_tag_replied_post(self):
        '''
        Contact sends a post. It will be tagged
        The agent replies. The outbound post should be tagged
        '''
        post = self._create_tweet('I need a laptop',
                                  channel=self.i,
                                  user_profile=self.customer)

        self.assertFalse(self.i.is_assigned(post))
        self.assertEqual(post.get_post_status(self.i), 'rejected')
        self.assertTrue(self.laptop_tag.is_assigned(post))
        self.assertEqual(post.get_post_status(self.laptop_tag), 'rejected')

        # Agent1 responds
        reply = self._create_tweet('Try this laptop. ' + self.agent1.signature,
                                   channel=self.o,
                                   user_profile=self.agent1.user_profile,
                                   in_reply_to=post)

        reply = Post.objects.get(reply.id)
        self.assertTrue(self.o.is_assigned(reply))
        self.assertTrue(self.laptop_tag_outbound.is_assigned(reply))

        # Verify status update
        channel_res = self._assertData(self.o, agents=self.agents, status=[SpeechActMap.ACTIONABLE], post=reply)
        tag_laptop_res = self._assertData(self.laptop_tag_outbound, agents=self.agents, status=[SpeechActMap.ACTIONABLE], post=reply)
        self.assertEqual(channel_res, tag_laptop_res)

        # Now make sure agent stats are set right for addition and removal
        for p, status, tag, channel, initial_tag in zip([post, reply],
                                                        [[SpeechActMap.ACTUAL], [SpeechActMap.ACTIONABLE]],
                                                        [self.other_tag, self.other_tag_outbound],
                                                        [self.i, self.o],
                                                        [self.laptop_tag, self.laptop_tag_outbound]):
            p.handle_add_tag(self.user, [tag])

            for ags in [None, self.agents]:
                channel_res = self._assertData(channel, agents=ags, status=status, post=p)
                tag_laptop_res = self._assertData(initial_tag, agents=ags, status=status, post=p)
                self.assertEqual(channel_res, tag_laptop_res)

            p.handle_remove_tag(self.user, [tag])

            status = [SpeechActMap.POTENTIAL, SpeechActMap.ACTIONABLE, SpeechActMap.REJECTED, SpeechActMap.ACTUAL]
            for ags in [None, self.agents]:
                channel_res2 = self._assertData(channel, agents=ags, status=status, post=p)
                tag_laptop_res2 = self._assertData(initial_tag, agents=ags, status=status, post=p)
                self.assertEqual(channel_res2, tag_laptop_res2)
                self.assertEqual(channel_res2, channel_res)     # equal to previous result

                # data for other tag should be empty
                self._assertNoData(tag, agents=ags, status=status)

    def test_tag_alert_posts_count(self):
        """
        Make sure that alert_posts_count is incremented.
        """
        POSTS_LIMIT = 100
        self.laptop_tag.reload()
        self.laptop_tag.alert_posts_limit = POSTS_LIMIT
        self.laptop_tag.save()
        count_before = self.laptop_tag.alert_posts_count
        self._create_tweet(
            '@solariat I need a laptop',
            channel=self.i,
            user_profile=self.customer)
        self.laptop_tag.reload()
        count_after = self.laptop_tag.alert_posts_count
        self.assertEqual(count_after - count_before, 1)

        # post which is not tagged does not increase alert_posts_count
        self._create_tweet(
            '@solariat I need something else',
            channel=self.i,
            user_profile=self.customer)
        self.laptop_tag.reload()
        count_after = self.laptop_tag.alert_posts_count
        self.assertEqual(count_after - count_before, 1)

    def test_tag_alert_email_is_sent(self):
        """
        Tests that tag alert email is sent, count is reset.
        """
        mail = Mail(app)
        with app.test_request_context(), mail.record_messages() as outbox:
            self.laptop_tag.reload()
            POSTS_LIMIT = 100
            self.laptop_tag.alert_posts_count = POSTS_LIMIT - 1
            self.laptop_tag.alert_posts_limit = POSTS_LIMIT
            self.laptop_tag.alert_is_active = True
            self.laptop_tag.alert_emails = [self.user.email]
            self.laptop_tag.save()
            self._create_tweet(
                '@solariat I need a laptop',
                channel=self.i,
                user_profile=self.customer)
            self.laptop_tag.reload()
            count_after = self.laptop_tag.alert_posts_count
            self.assertEqual(count_after, 0)
            self.assertEqual(len(outbox), 1)

            # this part is not very strict since in principle
            # it's possible that next tweet will be in next day
            # than alert should be sent

            # again make posts count be close to POSTS_LIMIT
            # new post should not trigger email
            # since email was just sent
            self.laptop_tag.alert_posts_count = POSTS_LIMIT - 1
            self.laptop_tag.save()
            self._create_tweet(
                '@solariat I need one more laptop',
                channel=self.i,
                user_profile=self.customer)
            self.laptop_tag.reload()
            count_after = self.laptop_tag.alert_posts_count
            self.assertEqual(count_after, POSTS_LIMIT)
            self.assertEqual(len(outbox), 1)

    @mock.patch('solariat_bottle.utils.mailer.datetime', FakeDatetime)
    @mock.patch('solariat_bottle.db.channel.base.datetime', FakeDatetime)
    def test_tag_alert_email_is_sent_only_once_per_day(self):
        """
        Tests that alert email is not sent today if it was sent today.
        """
        mail = Mail(app)
        with app.test_request_context(), mail.record_messages() as outbox:
            self.laptop_tag.reload()
            POSTS_LIMIT = 100
            self.laptop_tag.alert_posts_count = POSTS_LIMIT - 1
            self.laptop_tag.alert_posts_limit = POSTS_LIMIT
            self.laptop_tag.alert_is_active = True
            self.laptop_tag.alert_emails = [self.user.email]
            self.laptop_tag.save()
            self._create_tweet(
                '@solariat I need a laptop',
                channel=self.i,
                user_profile=self.customer)
            self.laptop_tag.reload()
            count_after = self.laptop_tag.alert_posts_count
            self.assertEqual(count_after, 0)
            self.assertEqual(len(outbox), 1)

            # 10 hours later and limit is increased - new email is not sent
            self.laptop_tag.alert_posts_limit = POSTS_LIMIT + 1
            self.laptop_tag.save()
            new_fake_now = FAKE_NOW
            new_fake_now[3] = FAKE_NOW[3] + 10
            FakeDatetime.now = classmethod(lambda cls: datetime(*new_fake_now))
            self._create_tweet(
                '@solariat I need another laptop',
                channel=self.i,
                user_profile=self.customer)
            self.laptop_tag.reload()
            self.assertEqual(len(outbox), 1)

            # one day later - new email is sent
            self.laptop_tag.alert_posts_count = POSTS_LIMIT
            # we set limit to 1 since count in new day starts from 0
            self.laptop_tag.alert_posts_limit = 1
            self.laptop_tag.save()
            new_fake_now = FAKE_NOW
            new_fake_now[2] = FAKE_NOW[2] + 1
            FakeDatetime.now = classmethod(lambda cls: datetime(*new_fake_now))
            self._create_tweet(
                '@solariat I need yet another laptop',
                channel=self.i,
                user_profile=self.customer)
            self.laptop_tag.reload()
            self.assertEqual(len(outbox), 2)

    @mock.patch('solariat_bottle.utils.mailer.datetime', FakeDatetime)
    @mock.patch('solariat_bottle.db.channel.base.datetime', FakeDatetime)
    def test_tag_alert_posts_count_is_reset_every_day(self):
        """Tests that alert posts count is reset every day.
        """
        self.laptop_tag.reload()
        posts_limit = 100
        initial_count = 10
        self.laptop_tag.alert_posts_count = initial_count
        self.laptop_tag.alert_posts_limit = posts_limit
        self.laptop_tag.alert_is_active = True
        self.laptop_tag.alert_emails = [self.user.email]
        self.laptop_tag.save()
        self._create_tweet(
            '@solariat I need a laptop',
            channel=self.i,
            user_profile=self.customer)
        self.laptop_tag.reload()
        self.assertEqual(self.laptop_tag.alert_posts_count, initial_count + 1)

        # 10 hours later - posts count increments
        new_fake_now = FAKE_NOW
        new_fake_now[3] = FAKE_NOW[3] + 10
        FakeDatetime.now = classmethod(lambda cls: datetime(*new_fake_now))
        self._create_tweet(
            '@solariat I need another laptop',
            channel=self.i,
            user_profile=self.customer)
        self.laptop_tag.reload()
        self.assertEqual(self.laptop_tag.alert_posts_count, initial_count + 2)

        # one day later - count starts from 0
        new_fake_now = FAKE_NOW
        new_fake_now[2] = FAKE_NOW[2] + 1
        FakeDatetime.now = classmethod(lambda cls: datetime(*new_fake_now))
        self._create_tweet(
            '@solariat I need yet another laptop',
            channel=self.i,
            user_profile=self.customer)
        self.laptop_tag.reload()
        self.assertEqual(self.laptop_tag.alert_posts_count, 1)

    def test_tag_alert_email_content(self):
        """
        Tests that correct information is in email:
        - subject is correct
        - link to Analytics Details view for this tag filter for this month
        - link to edit tag
        - link to unsubscribe
        """
        mail = Mail(app)
        with app.test_request_context(), mail.record_messages() as outbox:
            self.laptop_tag.reload()
            POSTS_LIMIT = 100
            self.laptop_tag.alert_posts_count = POSTS_LIMIT - 1
            self.laptop_tag.alert_posts_limit = POSTS_LIMIT
            self.laptop_tag.alert_is_active = True
            self.laptop_tag.alert_emails = [self.user.email]
            self.laptop_tag.save()
            self._create_tweet(
                '@solariat I need a laptop',
                channel=self.i,
                user_profile=self.customer)
            self.laptop_tag.reload()
            count_after = self.laptop_tag.alert_posts_count
            self.assertEqual(count_after, 0)
            self.assertEqual(len(outbox), 1)
            msg = outbox[0]
            tag_edit_url = '{}/configure#/tags/edit/{}'.format(
                settings.get_var('HOST_DOMAIN'), str(self.laptop_tag.id))
            tag_view_url = 'inbound#?tag={}&channel={}'.format(
                str(self.laptop_tag.id), str(self.i.id)
            )
            self.assertIn(tag_edit_url, msg.html)
            self.assertIn(tag_view_url, msg.html)
            s = URLSafeSerializer(UNSUBSCRIBE_KEY, UNSUBSCRIBE_SALT)
            email_tag_id = s.dumps((self.user.email, str(self.laptop_tag.id)))
            tag_unsubscribe_url = '{}/unsubscribe/tag/{}'.format(
                settings.get_var('HOST_DOMAIN'), email_tag_id)
            self.assertIn(tag_unsubscribe_url, msg.html)


class SmartTagFeatures(SmartTagsBaseCase):

    def setUp(self):
        super(SmartTagFeatures, self).setUp()
        settings.CHANNEL_FILTER_CLS = 'OnlineChannelFilter'
        self.i = self.sc.inbound_channel

    def test_model_and_post_vector(self):
        tag = self._create_smart_tag(self.i, 'Laptops Tag', status='Active', watchwords=['foo'])
        cf = tag.channel_filter
        extract_features = cf.extract_features

        def create_tweet(content):
            return self._create_tweet(content, channel=self.i, user_profile=self.customer)

        p1 = create_tweet('foo is in this text')
        self.assertTrue('foo' in extract_features(p1))

        p2 = create_tweet('"foo is in this text"')
        self.assertTrue('"foo' in extract_features(p2))
        self.assertTrue(tag.is_assigned(p2))
        p2.handle_remove_tag(self.user, [tag])

        p3 = create_tweet('"foo is not in this text"')
        self.assertFalse(tag.is_assigned(p3))

        tag.reload()
        p3 = create_tweet('foo is not in this text"')
        p3.handle_add_tag(self.user, [tag])

        p4 = create_tweet('foo is not in this text')
        self.assertTrue(tag.is_assigned(p4))


class SmartTagChannelCase(SmartTagsBaseCase):

    def test_model(self):
        # test Channel.smart_tags
        tags = [
            self._create_smart_tag(self.channel, 'tag1', status='Active'),
            self._create_smart_tag(self.channel, 'tag2', status='Active')]

        self.assertEqual(self.channel.smart_tags, tags)

        tags.append(self._create_smart_tag(self.channel, 'tag3', status='Active'))
        self.channel.add_tag(tags[-1])
        self.assertEqual(self.channel.smart_tags, tags)

        tag2 = tags.pop(1)
        self.channel.remove_tag(tag2)
        self.assertEqual(self.channel.smart_tags, tags)

        self.channel.save()
        channel = Channel.objects.get(self.channel.id)
        self.assertEqual(set(channel.smart_tags), set(tags))

        # test Post.smart_tags
        post = self._create_db_post('Test content', channel=self.channel)
        self.assertEqual(set(post.smart_tags), set(tags))

    def test_smart_tag_removed(self):
        tags = [
            self._create_smart_tag(self.channel, 'tag1', status='Active'),
            self._create_smart_tag(self.channel, 'tag2', status='Active')]
        self.assertEqual(
            sorted(self.channel.smart_tags, key=lambda x: str(x.id)), 
            sorted(tags, key=lambda x: str(x.id))
        )
        tags[0].archive()

        self.channel.__dict__.pop('_cached_smart_tags', None)
        self.assertEqual(self.channel.smart_tags, [tags[1]])

        from solariat_bottle.commands.configure import DeleteChannel
        DeleteChannel(channels=[self.channel]).update_state(self.user)

        for tag in tags:
            tag.reload()
            self.assertEqual(tag.status, 'Archived')

    def test_channel_account_change(self):
        acct1 = Account.objects.create(name="Acct1")
        acct2 = Account.objects.create(name="Acct2")
        self.channel.account = acct1
        self.channel.save()

        tags = [
            self._create_smart_tag(self.channel, 'tag1'),
            self._create_smart_tag(self.channel, 'tag2')]

        for tag in tags:
            self.assertEqual(tag.account, acct1)
        self.channel.account = acct2
        self.channel.save()
        self.channel.__dict__.pop('_cached_smart_tags', None)
        for tag in self.channel.smart_tags:
            self.assertEqual(tag.account, acct2)

    def test_post_assigning(self):
        # test assign by klout score
        tag1 = self._create_smart_tag(self.channel, 'tag1', influence_score=20, status='Active')
        tag2 = self._create_smart_tag(self.channel, 'tag2', influence_score=70, status='Active')

        user_profile1 = UserProfile.objects.upsert('Twitter', dict(screen_name='screen_name1', klout_score=30))
        user_profile2 = UserProfile.objects.upsert('Twitter', dict(screen_name='screen_name2', klout_score=90))

        contact_label1 = self._create_contact_label('screen_name1',users=['screen_name1'],status='Active')
        contact_label2 = self._create_contact_label('screen_name2',users=['screen_name2'],status='Active')

        post1 = self._create_db_post('Post from user 1', channel=self.channel, user_profile=user_profile1)
        post2 = self._create_db_post('Post from user 2', channel=self.channel, user_profile=user_profile2)
        self.assertEqual(post1.accepted_smart_tags, [tag1])
        self.assertEqual(post2.accepted_smart_tags, [tag1, tag2])

        # test assign by single contact label
        tag3 = self._create_smart_tag(self.channel, 'tag3', contact_label=[contact_label1.id], status='Active')
        post3 = self._create_db_post('Post from user 1', channel=self.channel, user_profile=user_profile1)
        self.assertEqual(post3.accepted_smart_tags, [tag1, tag3])

        # test assigning by keywords
        tag4 = self._create_smart_tag(self.channel, 'tag4', keywords=['tag4', '#post'], status='Active')
        post4 = self._create_db_post('Post from user 1 tag4', channel=self.channel, user_profile=user_profile2)
        self.assertEqual(post4.accepted_smart_tags, [tag1, tag2, tag4])

        # test assign by multiple contact sa_labels
        tag5 = self._create_smart_tag(self.channel, 'tag5', contact_label=[contact_label1.id,contact_label2.id], status='Active')
        post5 = self._create_db_post('Post from user 1', channel=self.channel, user_profile=user_profile1)
        self.assertEqual(post5.accepted_smart_tags, [tag1, tag3, tag5])

    def test_post_assigning_klout_none(self):
        """
        Testing that if users klout score is None post from it is not assigned to
        smart tag with minimum klout score specified.

        https://github.com/solariat/tango/issues/1576
        """
        tag1 = self._create_smart_tag(self.channel, 'tag1', status='Active')
        tag2 = self._create_smart_tag(self.channel, 'tag2', influence_score=20, status='Active')

        user_profile1 = UserProfile.objects.upsert('Twitter', dict(screen_name='screen_name1'))
        user_profile2 = UserProfile.objects.upsert('Twitter', dict(screen_name='screen_name2', klout_score=90))

        post1 = self._create_db_post('Post from user 1', channel=self.channel, user_profile=user_profile1)
        post2 = self._create_db_post('Post from user 2', channel=self.channel, user_profile=user_profile2)

        self.assertEqual(post1.accepted_smart_tags, [tag1])
        self.assertEqual(post2.accepted_smart_tags, [tag1, tag2])

    def test_user_input(self):
        '''
        Should test the following cases:
        1) A tag is assigned to a post (imagine this is done by a user making the assignmnet.)
        This should result in an update to the channel_filter for the tag so this would work in
        a way that is identical to the channel which includes an explicit rule for determining
        the True assignment, but should also consider that there would be a channel_filter assessment
        whcih could learn by example. So a subsequent post like that one, which would not ordinarily
        be assigned, would now work.
        2) A tag is removed from a post. Again, the logic here would be that this should work just like
        rejection of a post in a channel. It would add an example fo rejected that could then be used
        to update the channel_fit.

        These use cases will not be the most common, as users will not want to do too much work labeling
        things, but we need to make sure it works.
        '''
        similar_posts = [
            'I need a new laptop bag',
            'I need a good laptop bag',
            'I really need a laptop bag'
        ]

        # Constrain the substring: lap
        tag1 = self._create_smart_tag(self.channel, 'Tag1', keywords=['lap'], status='Active')
        up1 = UserProfile.objects.upsert('Twitter', dict(screen_name='test_user'))
        up2 = UserProfile.objects.upsert('Twitter', dict(screen_name='test_user2'))

        # Send the post from user1, tag1 should be assigned by username
        post1 = self._create_db_post(similar_posts[0], channel=self.channel, user_profile=up1)

        # First post will be assigned because of constraint
        self.assertTrue(tag1.is_assigned(post1))

        # Send a post that similar to previous
        post2 = self._create_db_post(similar_posts[1], channel=self.channel, user_profile=up2)
        self.assertTrue(tag1.is_assigned(post2))

        # Now remove tag1 from post2
        post2.handle_remove_tag(self.user, [tag1])
        self.assertFalse(tag1.is_assigned(post2))

        # Impacts post1
        post1.reload()
        self.assertFalse(tag1.is_assigned(post1))

        # Impacts new post
        post3 = self._create_db_post(similar_posts[2], channel=self.channel, user_profile=up2)
        self.assertFalse(tag1.is_assigned(post3))

    def test_default_behavior(self):
        '''
        By default, a Smart Tag should have permissive values. So fo a new one, with only default values,
        any post will be assigned.
        '''
        smart_tag = self._create_smart_tag(self.channel, 'Title')
        smart_tag.status = 'Suspended'
        smart_tag.save()
        post = self._create_db_post('Post Content', channel=self.channel)
        '''print "Created smart_tag is " + str(smart_tag)
        print "Check if the smart tag is started...the status is " + str(smart_tag.status)
        print "Created post is " + str(post)
        print "Associated smarttags with created post are  " + str(post.smart_tags)'''
        self.assertEqual(post.smart_tags, [])
        smart_tag.status = 'Active'
        smart_tag.save()
        post = self._create_db_post('Post Content', channel=self.channel)
        self.assertEqual(post.smart_tags, [smart_tag])

        #multi channels
        channel2 = Channel.objects.create_by_user(self.user, title='Channel2')
        post = self._create_db_post('Post Content', channels=[self.channel, channel2])
        self.assertEqual(post.smart_tags, [smart_tag])

    def test_non_assignment(self):
        smart_tag = self._create_smart_tag(self.channel, 'NADA',
                                           status='Active',
                                           keywords=['laptop'])
        post = self._create_db_post('This should not trigger the tag', channel=self.channel)
        self.assertEqual(post.accepted_smart_tags, [])

        # Now verify that there are no speech act map entries for this tag
        self.assertEqual(SpeechActMap.objects(channel=smart_tag.id).count(), 0)

        self.assertEqual(ChannelHotTopics.objects(channel_num=smart_tag.counter).count(), 0)
        self.assertEqual(len([stat for stat in ChannelTopicTrends.objects()
                              if stat and stat.unpacked[0] == smart_tag.counter]), 0)

    def test_keyword_match(self):
        ''' This will be permissive. Make sure it is.'''
        chase_kwds = ["cash", "ATM", "ChaseSupport", "@Chase", "#Chase"]
        chase_tag = self._create_smart_tag(self.channel, 'Tag', status='Active',
            keywords=chase_kwds)

        match = [
            "@chasegoehring night chase:)",
            "#ATM cash-machine Support #Chas pur$#chase acash",
            "ask,;.`'-#ChaseSupport",
            "@ChaseSupport asd",
            "@chase auto loans vehicle http://t. co/D6R81fVUke. . . : chase auto loans vehicle. . . http://t. co/zJpkiJc2G1"
        ]

        for content in match:
            post = self._create_db_post(content, channel=self.channel)
            self.assertTrue(chase_tag.is_assigned(post), "Tag is not assigned to: %s" % post.plaintext_content)

    def test_conjunction(self):
        '''
        Work through the logic for ensuring that the combination of filters is respected.
        '''
        from solariat_nlp.sa_labels import NEEDS, LIKES

        label = self._create_contact_label('username',users=['username'],status='Active')

        ## test tag with defined keywords & contact label & intentions
        tag = self._create_smart_tag(self.channel, 'Tag', status='Active',
            keywords=['laptop'],
            contact_label=[label.id],
            intention_types=[NEEDS.title, LIKES.title])


        up = UserProfile.objects.upsert('Twitter', dict(screen_name='username'))

        # should not fit by username
        post = self._create_db_post('I need a laptop', channel=self.channel)
        self.assertEqual(post.accepted_smart_tags, [])

        # should not fit by username and intention
        post = self._create_db_post('Can anybody recommend a good laptop', channel=self.channel)
        self.assertEqual(post.accepted_smart_tags, [])

        # should not fit by username and intention and keyword
        post = self._create_db_post('Can anybody recommend a good foo', channel=self.channel)
        self.assertEqual(post.accepted_smart_tags, [])

        # should fit
        post = self._create_db_post('I need a laptop', channel=self.channel, user_profile=up)
        self.assertEqual(post.accepted_smart_tags, [tag])


        ## test tag with defined keywords & usernames
        tag2 = self._create_smart_tag(self.channel, 'Tag', status='Active',
            keywords=['laptop'],
            contact_label=[label.id])
        # should not fit by all parameters
        post = self._create_db_post('Can anybody recommend a good foo', channel=self.channel)
        self.assertEqual(post.accepted_smart_tags, [])

        # should not fit by username
        post = self._create_db_post('Can anybody recommend a good laptop', channel=self.channel)
        self.assertEqual(post.accepted_smart_tags, [])

        # should not fit by keywords
        post = self._create_db_post('I need a foo', channel=self.channel, user_profile=up)
        self.assertEqual(post.accepted_smart_tags, [])

        # should fit
        post = self._create_db_post('Can anybody recommend a good laptop', channel=self.channel, user_profile=up)
        self.assertEqual(post.accepted_smart_tags, [tag2])

    def test_post_accepted_rejected(self):
        """Tests filter by tag when post accepted/rejected"""
        start_date = now()
        i = self.sc.inbound_channel
        o = self.sc.outbound_channel

        # Add keyword so posts will be actionable
        i.keywords.append('laptop')
        i.save()

        # Create 2 Smart Tags, for different use keywords
        laptop_tag = self._create_smart_tag(i, 'Laptops Tag', status='Active', keywords=['laptop'])
        other_tag = self._create_smart_tag(i, 'Other Tag', status='Active', keywords=['display'])

        customer = self.customer
        agent1 = self.agent1
        agents = [agent1]

        from_ts_hour = Timeslot(point=start_date, level='hour')

        # Customer posts a tweet. Should be in the laptop_tag
        post = self._create_tweet('I need a laptop',
                                  channel=i,
                                  user_profile=customer)
        self.assertEqual(post.accepted_smart_tags, [laptop_tag])
        channel_res = self._assertData(i, None, [SpeechActMap.ACTIONABLE], post)
        tag_res = self._assertData(laptop_tag, None, [SpeechActMap.ACTIONABLE], post)
        self.assertEqual(channel_res, tag_res)

        self._assertNoData(i, None, [SpeechActMap.POTENTIAL, SpeechActMap.ACTUAL, SpeechActMap.REJECTED])
        self._assertNoData(laptop_tag, None, [SpeechActMap.POTENTIAL, SpeechActMap.ACTUAL, SpeechActMap.REJECTED])

        post.handle_reject(self.user, [i])
        channel_res = self._assertData(i, None, [SpeechActMap.REJECTED], post)
        tag_res = self._assertData(laptop_tag, None, [SpeechActMap.REJECTED], post)
        self.assertEqual(channel_res, tag_res)
        self._assertNoData(i, None, [SpeechActMap.POTENTIAL, SpeechActMap.ACTUAL, SpeechActMap.ACTIONABLE])
        self._assertNoData(laptop_tag, None, [SpeechActMap.POTENTIAL, SpeechActMap.ACTUAL, SpeechActMap.ACTIONABLE])

    @unittest.skip("Responses and Inbox are deprecated")
    def test_reject_response(self):
        """ Test that rejecting a post from inbox will also reject
        the post for all the tags assigned to that post."""
        inbound = self.sc.inbound_channel
        foo_tag = self._create_smart_tag(inbound, 'Foo Tag',
                                         status='Active', keywords=['foo'])
        self._create_smart_tag(inbound, 'Other Tag', status='Active',
                               keywords=['display'])
        customer = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        lp = self._create_db_landing_page("www.foo.com")
        self._create_db_matchable(creative="Foo Bar Baz",
                                  intention_topics = ['foo'],
                                  url=lp.url,
                                  landing_page=lp,
                                  channels=[self.channel, inbound])

        post = self._create_tweet(content='I need a foo',
                                  channel=inbound,
                                  user_profile=customer,
                                  demand_matchables=True,
                                  user_tag='contact1')

        response = Response.objects.upsert_from_post(post)
        response.handle_reject(self.user)
        channel_res = self._assertData(inbound, None, [SpeechActMap.REJECTED], post)
        tag_res = self._assertData(foo_tag, None, [SpeechActMap.REJECTED], post)
        self.assertEqual(channel_res, tag_res)

    def test_tags_added_by_similarity(self):
        """Test filter_similar_posts_task for smart tags."""
        i = self.sc.inbound_channel
        o = self.sc.outbound_channel
        tag = self._create_smart_tag(i, 'Tag', status='Active', keywords=['laptop'])

        # Add keyword so posts will be actionable
        i.keywords.append('laptop')
        i.save()

        customer = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        from_ts = Timeslot(point=now(), level='hour')

        # create 2 similar posts
        post1 = self._create_tweet('My laptop is broken.', channel=i, user_profile=customer)
        post2 = self._create_tweet('My laptop is not working.', channel=i, user_profile=customer)

        # Both should be actionable because the topic is in the channel keyword list
        self.assertTrue(i.is_assigned(post1))
        self.assertTrue(i.is_assigned(post2))

        # check posts/trends/topics data
        for channel in [i, tag]:
            hot_topics, trends, posts = get_data(channel, from_ts, None, [SpeechActMap.ACTIONABLE])
            self.assertEqual(hot_topics[0]['topic_count'], 2)
            self.assertEqual(hot_topics[0]['topic'], 'laptop')
            self.assertEqual(trends['list'][0]['count'], 2)
            self.assertEqual(set(posts), {post1, post2})

        # remove tag from one post manually - it should be removed from another post too
        post1.handle_remove_tag(self.user, [tag])
        post1.reload()
        post2.reload()
        self.assertEqual(post1.accepted_smart_tags, [])
        self.assertEqual(post2.accepted_smart_tags, [])
        # check there are no posts for tag and no stats
        self._assertNoData(tag, None, [SpeechActMap.POTENTIAL, SpeechActMap.ACTIONABLE, SpeechActMap.ACTUAL, SpeechActMap.REJECTED])

    def test_channel_stats(self):
        """Test posts counter for smart tags"""
        i = self.sc.inbound_channel
        tag1 = self._create_smart_tag(i, 'Laptops Tag', status='Active', keywords=['laptop'])
        tag2 = self._create_smart_tag(i, 'Other Tag', status='Active', keywords=['support', 'help'])
        customer = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        for channel in [i, tag1, tag2]:
            self.assertEqual(get_channel_stats(self.user, channel), {})

        post1 = self._create_tweet('My laptop is broken.', channel=i, user_profile=customer)
        post2 = self._create_tweet('@support help me with this', channel=i, user_profile=customer)

        self.assertEqual(get_channel_stats(self.user, i)['number_of_posts'], 2)
        for tag in [tag1, tag2]:
            self.assertEqual(get_channel_stats(self.user, tag)['number_of_posts'], 1)

        # manually add/remove tags
        post1.handle_add_tag(self.user, [tag2])
        self.assertEqual(get_channel_stats(self.user, tag1)['number_of_posts'], 1)
        self.assertEqual(get_channel_stats(self.user, tag2)['number_of_posts'], 2)

        post1.handle_remove_tag(self.user, [tag2])
        self.assertEqual(get_channel_stats(self.user, tag1)['number_of_posts'], 1)
        self.assertEqual(get_channel_stats(self.user, tag2)['number_of_posts'], 1)

        post1.handle_remove_tag(self.user, [tag1])
        post2.handle_remove_tag(self.user, [tag2])
        self.assertEqual(get_channel_stats(self.user, tag1)['number_of_posts'], 0)
        self.assertEqual(get_channel_stats(self.user, tag2)['number_of_posts'], 0)

    @unittest.skip("Test simultaneous post status update for issue #1592")
    def test_post_channel_assignment(self):
        from solariat_bottle.db.response import Response
        from solariat_bottle.commands.engage import PostResponse

        # setup dispatching channel
        from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel
        dispatching_channel = EnterpriseTwitterChannel.objects.create(title="Outbound", account=self.sc.account)
        self.sc.account.outbound_channels = {'Twitter': str(dispatching_channel.id)}
        self.sc.account.save()

        # setup outbound channel
        self.sc.outbound_channel.usernames = [
		    "solariat_brand2",
		    "solariat_brand"]
        self.sc.outbound_channel.save()

        # setup users
        user1_solariat = UserProfile.objects.upsert('Twitter', dict(screen_name='@user1_solariat'))
        user2_solariat = UserProfile.objects.upsert('Twitter', dict(screen_name='@user2_solariat'))
        solariat_brand2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@solariat_brand2'))

        matchable = self._create_db_matchable("We like candies too",
                                              intention_topics=['candies'],
                                              channels=[self.sc.inbound_channel])
        tags = [
            self._create_smart_tag(self.sc.inbound_channel, "Tag1", status='Active', keywords=['word1']),
            self._create_smart_tag(self.sc.inbound_channel, "Tag1", status='Active', keywords=['word2']),
            self._create_smart_tag(self.sc.inbound_channel, "Tag1", status='Active', keywords=['word3']),
            self._create_smart_tag(self.sc.inbound_channel, "Tag1", status='Active', keywords=['word4'])
        ]

        post = self._create_tweet("@solariat_brand I like all kind of candies. Thanks @solariat_brand2",
                                  self.sc.inbound_channel,
                                  user_profile=user1_solariat)
        self.assertEqual(post.get_assignment(self.sc.inbound_channel), 'highlighted')

        # similar to post
        post2 = self._create_tweet("@solariat_brand I like all kind of candies. Thanks @solariat_brand2",
                                  self.sc.inbound_channel,
                                  user_profile=user2_solariat)
        response = Response.objects.get(post2.response_id)

        def _post_response(user, channel, post, response):
            PostResponse(response=response, matchable=matchable).perform(user)
            post.reload()
            self.assertEqual(post.get_assignment(channel), 'accepted')

        from multiprocessing import Process
        p1 = Process(target=_post_response, args=(self.user, self.sc.inbound_channel, post2, response))

        # simulate the reply tweet came back
        p2 = Process(target=self._create_tweet,
                args=(response.content,),
                kwargs=dict(
                    channels=[dispatching_channel, self.sc.outbound_channel],
                    in_reply_to=post,
                    user_profile=solariat_brand2))

        # reply = self._create_tweet(response.content,
        #                            channels=[dispatching_channel, self.sc.outbound_channel],
        #                            in_reply_to=post,
        #                            user_profile=solariat_brand2)
        p1.start()
        p2.start()

        #p2.join()
        #p1.join()

        import time
        time.sleep(5)
        post.reload()
        self.assertEqual(post.get_assignment(self.sc.inbound_channel), 'replied')
        post2.reload()
        self.assertEqual(post2.get_assignment(self.sc.inbound_channel), 'accepted')


class SmartTagsUITestCase(UICase, SmartTagsTestHelper):
    def setUp(self):
        super(SmartTagsUITestCase, self).setUp()
        self.login()

    def _details(self, tag_id):
        data = self._get('/smart_tags/json' + "?channel=%s&id=%s" % (self.channel.id, tag_id), {})
        return data['item']

    def test_smart_tags_ep(self):
        """/smart_tags/json"""
        titles = ('title1', 'title2', 'title3')
        smart_tags = [self._create_smart_tag(self.channel, title) for title in titles]
        expected_ids = [str(x.id) for x in smart_tags]

        data = self._get('/smart_tags/json' + "?channel=%s" % self.channel.id, {})
        self.assertEqual(len(data['list']), len(titles))
        self.assertEqual(set([x['id'] for x in data['list']]), set(expected_ids))

        for tag in smart_tags:
            tag.adaptive_learning_enabled = False
            tag.save()
        data = self._get('/smart_tags/json' + "?channel=%s&adaptive_learning_enabled=%s" % (self.channel.id, True), {})
        self.assertEqual(len(data['list']), 0)

    def test_smart_tags_no_channel(self):
        channel2 = TwitterServiceChannel.objects.create_by_user(self.user, title="Second channel")

        titles = ('title1', 'title2', 'title3')
        smart_tags = [self._create_smart_tag(self.channel, title) for title in titles]
        expected_ids = [str(x.id) for x in smart_tags]

        titles = ('title1', 'title2', 'title3')
        smart_tags = [self._create_smart_tag(channel2, title) for title in titles]
        expected_ids.extend([str(x.id) for x in smart_tags])

        data = self._get('/smart_tags/json', {})
        self.assertEqual(len(data['list']), len(expected_ids))
        self.assertEqual(set([x['id'] for x in data['list']]), set(expected_ids))

    def test_smart_tag_ep(self):
        """/smart_tag/<action>/json"""
        #update, activate, deactivate, delete
        smart_tag_data = {
            'title': 'Title1'
        }
        data = self._post('/smart_tags/update/json', smart_tag_data, False)
        self.assertEqual(data['error'], 'Channel not found')

        smart_tag_data['channel'] = str(self.channel.id)

        # create
        data = self._post('/smart_tags/update/json', smart_tag_data)
        self.assertEqual(data['item']['title'], smart_tag_data['title'])
        # expected status is Active after creation
        self.assertEqual(data['item']['status'], 'Active')
        self.assertEqual(AccountEvent.objects().count(), 2)
        tag_id = data['item']['id']

        # update
        smart_tag_data['title'] = 'Updated title'
        smart_tag_data['id'] = tag_id
        data = self._post('/smart_tags/update/json', smart_tag_data)
        self.assertEqual(data['item']['title'], smart_tag_data['title'])
        self.assertEqual(AccountEvent.objects().count(), 3)

        # activate
        data = self._post('/smart_tags/activate/json', {"ids": [tag_id]})
        item = self._details(tag_id)
        self.assertEqual(item['status'], 'Active')

        # deactivate
        data = self._post('/smart_tags/deactivate/json', {"ids": [tag_id]})
        item = self._details(tag_id)
        self.assertEqual(item['status'], 'Suspended')

        # delete
        item = Channel.objects.get(tag_id)
        parent = Channel.objects.get(item.parent_channel)
        self.assertEqual(parent.smart_tags, [item])

        data = self._post('/smart_tags/delete/json', {"ids": [tag_id]})
        item.reload()
        self.assertEqual(item.status, 'Archived')
        self.assertEqual(item.parent_channel, parent.id)

        parent.__dict__.pop('_cached_smart_tags')
        self.assertEqual(parent.smart_tags, [])

    def test_smart_tag_alert(self):
        """/smart_tag/<action>/json"""
        #update, activate, deactivate, delete
        smart_tag_data = {
            'title': 'Title1',
            'alert': {
                'is_active': True,
                'posts': 100,
                'emails': [self.user.email],
            },
            'channel': str(self.channel.id)
        }
        # create
        data = self._post('/smart_tags/update/json', smart_tag_data)
        self.assertEqual(data['item']['title'], smart_tag_data['title'])
        # expected status is Active after creation
        self.assertEqual(data['item']['status'], 'Active')
        self.assertEqual(data['item']['alert']['is_active'], True)
        tag_id = data['item']['id']

        # deactivate alert
        smart_tag_data['id'] = tag_id
        smart_tag_data['title'] = 'Updated title'
        smart_tag_data['alert']['is_active'] = False
        data = self._post('/smart_tags/update/json', smart_tag_data)
        self.assertEqual(data['item']['title'], smart_tag_data['title'])
        self.assertEqual(data['item']['alert']['is_active'], False)


    def test_smart_tags_multi_commands(self):
        channel2 = TwitterServiceChannel.objects.create(account=self.channel.account,
                                                        title='C2', acl=self.channel.acl)
        tag1 = self._create_smart_tag(channel2.inbound_channel, '2 Tag1',
                                      status='Active', keywords=['post', 'content'])
        tag2 = self._create_smart_tag(channel2.inbound_channel, '2 Tag2',
                                      status='Active', keywords=['post2', 'content2'])

        posts = []
        for _ in xrange(4):
            posts.append(self._create_db_post('Post Content',
                                              channels=[channel2, self.channel]))

        # add smart tag to post
        post_data = {
            "tag" : str(tag1.id),
            "channel": str(self.channel.id),
            "posts": [p.id for p in posts]
        }
        data = self._delete('/commands/assign_tag_multi_post', post_data)
        self.assertTrue(data['ok'])
        post_data["tag"] = str(tag2.id)
        data = self._post('/commands/assign_tag_multi_post', post_data)
        self.assertTrue(data['ok'])
        [p.reload() for p in posts]
        for p in posts:
            self.assertEqual(p.tag_assignments[str(tag1.id)], 'rejected')
            self.assertEqual(p.tag_assignments[str(tag2.id)], 'starred')

    def test_post_smart_tags_ep(self):
        """/commands/assign_post_tag"""
        self.channel.account.update(selected_app=APP_GSA)
        channel2 = TwitterServiceChannel.objects.create(account=self.channel.account, title='C2',
                                                        acl=self.channel.acl)
        self._create_smart_tag(channel2.inbound_channel, '2 Tag1', status='Active', keywords=['post', 'content'])

        post = self._create_db_post('Post Content', channels=[channel2, self.channel])
        data = self._get('/commands/assign_post_tag' + "?channel=%s&post_id=%s" % (self.channel.id, post.id), {})
        self.assertEqual(len(data['item']), 0)
        label=self._create_contact_label('test_user',users=['@test_user'])

        tag1 = self._create_smart_tag(self.channel, 'Tag1', status='Active', keywords=['post', 'content'])
        tag2 = self._create_smart_tag(self.channel, 'Tag2', status='Active', contact_label=[label.id])
        tag3 = self._create_smart_tag(self.channel, 'Tag3', status='Active', adaptive_learning_enabled=False)
        tag4 = self._create_smart_tag(self.channel, 'Tag4', status='Active', skip_keywords=['post'],
                                      adaptive_learning_enabled=False)
        post = self._create_db_post('Post Content', channels=[self.channel, channel2], demand_matchables=True)
        #post = self._create_db_post('Post Content', channels=[self.channel, channel2])
        self.assertEqual(len(post.accepted_smart_tags), 3,
                         [t.title for t in post.accepted_smart_tags])

        # fetch post smart tags
        data = self._get('/commands/assign_post_tag' + "?channel=%s&post_id=%s" % (self.channel.id, post.id), {})
        self.assertEqual(len(data['item']), 2)
        self.assertEqual(data['item'][0]['id'], str(tag1.id))

        # add smart tag to post
        post_data = dict(channel=str(self.channel.id),
                         post_id=str(post.id))
        post_data['ids'] = [str(tag2.id)]
        data = self._post('/commands/assign_post_tag', post_data)
        self.assertEqual(len(data['item']), 3)
        self.assertEqual(set(x['id'] for x in data['item']), {str(tag1.id), str(tag2.id), str(tag3.id)})

        import json
        base_filter = {'channel_id': None,
                       'intentions': ['asks','consideration','needs','likes','problem']
                       }
        self.login()

        # remove smart tags from the post
        post_data['ids'] = [str(tag1.id), str(tag2.id)]
        data = self._delete('/commands/assign_post_tag', post_data)

        # try to add readonly tag
        post_data['ids'] = [str(tag4.id)]
        data = self._post('/commands/assign_post_tag', post_data, expected_result=False)
        self.assertEqual(TaskMessage.objects.count(), 1)

        # try to remove readonly tag
        post_data['ids'] = [str(tag3.id)]
        data = self._delete('/commands/assign_post_tag', post_data, expected_result=False)
        self.assertEqual(TaskMessage.objects.count(), 2)
        for err in TaskMessage.objects():
            self.assertEqual(err.content, 'Smart Tag is read only')
