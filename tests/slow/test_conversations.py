# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
import unittest
import json
import unittest
from datetime import timedelta
from solariat_bottle.db.post.facebook import FacebookPost
from solariat.tests.base import LoggerInterceptor

from solariat.utils.lang.support import Lang
from solariat.utils import timeslot

from solariat_bottle          import settings
from solariat_bottle.settings import get_var
from solariat_bottle.configurable_apps import APP_GSA

from solariat_bottle.db.post.base            import Post
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.conversation         import Conversation
from solariat_bottle.db.channel.base         import SmartTagChannel, Channel
from solariat_bottle.db.channel_filter       import ChannelFilter
from solariat_bottle.db.channel_hot_topics   import ChannelHotTopics
from solariat_bottle.db.channel_trends       import ChannelTrends
from solariat_bottle.db.channel_trends       import ALL_AGENTS
from solariat_bottle.db.channel.twitter      import (
    TwitterTestDispatchChannel, TwitterServiceChannel)
from solariat_bottle.utils.views             import reorder_posts
from ..base import (
    UICase, content_gen, datasift_date_format,
    fake_status_id, fake_twitter_url)


class ConversationBaseCase(UICase):

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
        self.account.set_outbound_channel(self.dispatch_channel)
        self.account.update(selected_app=APP_GSA)

    def setUp(self):
        super(ConversationBaseCase, self).setUp()
        self.make_setup()

class AssignmentTests(ConversationBaseCase):

    def _post_reply(self, inbounds, outbounds):
        ''' Generate an inbound outbound pair for all inbound outbounds.
        '''

        # Reset
        Conversation.objects.remove()
        Post.objects.remove()

        # Generate inbound
        post = self._create_tweet(
            user_profile=self.contact,
            channels=inbounds,
            content="@test Content")

        # reply to post in outbound channels
        reply = self._create_tweet(
            user_profile=self.support,
            channels=outbounds,
            content="Content",
            in_reply_to=post)

        post.reload()
        return post, reply

    def setUp(self):
        super(AssignmentTests, self).setUp()
        #account = Account.objects.get_or_create(name='Test-Acct')
        self.sc1 = self.sc
        self.sc1.account = self.account
        self.sc1.save()
        self.sc1.add_username('@test')
        self.sc2 = TwitterServiceChannel.objects.create_by_user(
            self.user,
            title='Service Channel 2')
        self.sc2.add_username('@test')


    def test_no_parent(self):
        '''All replies to inbound but no parent post for one channel'''
        post, reply = self._post_reply(
            [self.sc1],
            [self.sc1.outbound, self.sc2.outbound]
        )

        # Replied to post, so it became actionable (highlighted)
        self.assertEqual(post.channel_assignments[str(self.sc1.inbound)], 'replied')

    def test_reply_status_unchangeable(self):
        post, _ = self._post_reply(
            [self.sc1],
            [self.sc1.outbound, self.sc2.outbound]
        )
        self.assertEqual(post.channel_assignments[str(self.sc1.inbound)], 'replied')

        post.handle_accept(self.user, [self.sc1.inbound_channel])
        post.reload()
        self.assertEqual(post.channel_assignments[str(self.sc1.inbound)], 'replied')

        post.handle_reject(self.user, [self.sc1.inbound_channel])
        post.reload()
        self.assertEqual(post.channel_assignments[str(self.sc1.inbound)], 'replied')

    def test_route_parent_post_failure(self):
        with LoggerInterceptor() as logs:
            post, _ = self._post_reply(
                [self.sc1.inbound_channel],
                [self.sc2.outbound]
            )

        # warnings = ''.join([log.message for log in logs if log.levelname == 'WARNING'])
        # warn_msg = 'is not from service channel'
        # self.assertIn(warn_msg, warnings)

        self.assertNotEqual(post.channel_assignments[str(self.sc1.inbound)], 'replied')

    def test_multi_channel_conversation_1_of_2(self):
        '''
        respond to one of 2 outbound channels, and check post status
        '''
        post, reply = self._post_reply(
            [self.sc1.inbound, self.sc2.inbound],
            [self.sc1.outbound]
        )

        # Check conversation post counts
        self.assertEqual(Conversation.objects(channel=self.sc1.id).count(), 1)
        self.assertEqual(Conversation.objects(channel=self.sc2.id).count(), 1)
        c1 = Conversation.objects.get(channel=self.sc1.id)
        self.assertEqual(len(c1.posts), 2)
        self.assertEqual(set(c1.posts), { post.id, reply.id })
        c2 = Conversation.objects.get(channel=self.sc2.id)
        self.assertEqual(len(c2.posts), 1)

        # verify post channel assignments
        self.assertEqual(post.channel_assignments[str(self.sc1.inbound)], 'replied')
        self.assertEqual(post.channel_assignments[str(self.sc2.inbound)], 'highlighted')

    def test_multi_channel_conversation_all(self):
        '''
        respond to both, all set. This case covers where a post appears in many outbound channels.
        This will be rare, but it could happen - especially where customers are monitoring
        their competitirs. A single post can appear in multiple channels, and thus also
        multiple conversations, since conversations are scoped by channel
        '''
        post, reply = self._post_reply(
            [self.sc1.inbound, self.sc2.inbound],
            [self.sc1.outbound, self.sc2.outbound]
        )

        self.assertEqual(post.channel_assignments[str(self.sc1.inbound)], 'replied')
        self.assertEqual(post.channel_assignments[str(self.sc2.inbound)], 'replied')

    def test_multiple_conversations_edge_case(self):
        ''' Test that in case we have multiple conversations for the same post
        we treat that rare excuses correctly by removing all but one '''
        screen_name = 'customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))

        url = fake_twitter_url(screen_name)

        post = self._create_db_post(
                                    channel=self.inbound,
                                    content="I need a foo. Does anyone have a foo?",
                                    demand_matchables=False,
                                    url=url,
                                    user_profile=user_profile)

        self.assertEqual(len(Conversation.objects()), 1)
        Conversation.objects.create_conversation(self.sc, [post], conversation_id=self.sc.get_conversation_id(post))
        self.assertEqual(len(Conversation.objects()), 2)

        self._create_tweet(
            user_profile=self.support,
            channels=[self.outbound],
            content="Content", in_reply_to=post)
        # Even if for some reasone we had 2 conversation, once we reply, we
        # should be left only with one
        self.assertEqual(len(Conversation.objects()), 1)

        screen_name = 'customer2'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name)
        post2 = self._create_db_post(
                                    channel=self.inbound,
                                    content="I need a foo. Does anyone have a foo?",
                                    demand_matchables=False,
                                    url=url,
                                    user_profile={'user_name': 'twitter_agent'})

        screen_name = 'customer3'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name)
        post3 = self._create_db_post(
                                    channel=self.inbound,
                                    content="I need a foo. Does anyone have a foo?",
                                    demand_matchables=False,
                                    url=url,
                                    user_profile=user_profile)

        self.assertEqual(len(Conversation.objects()), 3)

        conv2 = Conversation.objects.create_conversation(self.sc, [post, post2, post3],
                                                         conversation_id=self.sc.get_conversation_id(post))
        self.assertEqual(len(Conversation.objects()), 4)

        # In case two conversations for same post/channel combination are present
        # and one of them has more posts than the other (THIS IN FACT SHOULD NEVER HAPPEN)
        # keep the one with more data in it.
        self._create_tweet(user_profile=self.support, channels=[self.outbound],
                           content="Content", in_reply_to=post)
        self.assertEqual(len(Conversation.objects()), 3)
        self.assertTrue(conv2.id in [c.id for c in Conversation.objects()])

    @unittest.skip('With our current event model we dont handle such'
                    'situations anymore and give priprity to outbound channel'
    )
    def test_mixed_up_service_channels(self):
        '''Initial posts from inbound and outbound. Responses on outbound and inbound.
        So this tests the case of brand initiated responses.'''
        post, reply = self._post_reply(
            [self.sc1, self.sc2.outbound],
            [self.sc1.outbound, self.sc2.inbound]
        )
        # expected 2 conversation with 2 post in both
        self.assertEqual(Conversation.objects(channel=self.sc1.id).count(), 1)
        self.assertEqual(Conversation.objects(channel=self.sc2.id).count(), 1)
        c1 = Conversation.objects.get(channel=self.sc1.id)
        self.assertEqual(len(c1.posts), 2)
        self.assertEqual(set(c1.posts), { post.id, reply.id })

        c2 = Conversation.objects.get(channel=self.sc2.id)
        self.assertEqual(len(c2.posts), 2)
        self.assertEqual(set(c2.posts), { post.id, reply.id })

        # Replied to post, so it became actual.
        self.assertEqual(post.channel_assignments[str(self.sc1.inbound)], 'replied')

        # Not for this channel though
        self.assertEqual(post.channel_assignments[str(self.sc2.outbound)], 'highlighted')

    def test_reply_on_inbound(self):
        """ One of replies goes to inbound """

        post, reply = self._post_reply(
            [self.sc1, self.sc2],
            [self.sc1.inbound, self.sc2.outbound]
        )

        # Reply will only trigger state change for sc2 - which is outbound
        self.assertEqual(post.channel_assignments[str(self.sc1.inbound)], 'highlighted')
        self.assertEqual(post.channel_assignments[str(self.sc2.inbound)], 'replied')


class ConversationCase(ConversationBaseCase):
    DEFAULT_ENGLISH_CONTENT = "This is truly english message which should be easily recognized"
    def test_basic_creation(self):
        screen_name = 'customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))

        url = fake_twitter_url(screen_name)

        post = self._create_db_post(
            channel=self.inbound,
            content="I need a foo. Does anyone have a foo?",
            demand_matchables=False,
            url=url,
            user_profile=user_profile)

        # No verify look works with closure flag
        conv = Conversation.objects()[0]
        self.assertEqual(conv.contacts, [ post.user_profile.id ])
        self.assertEqual(list(conv.posts), [ post.id ])

        # Since open, should return when we do not include closed.
        self.assertEqual([conv.id],  [c.id for c in 
                                      Conversation.objects.lookup_by_posts(self.sc, [post], include_closed=False)])
        # And when we do
        self.assertEqual([conv.id],  [c.id for c in 
                                      Conversation.objects.lookup_by_posts(self.sc, [post], include_closed=True)])

        # Now close it and make sure it does so - selectively
        conv.is_closed = True
        conv.save(is_safe=True)
        self.assertEqual([conv.id],  [c.id for c in 
                                      Conversation.objects.lookup_by_posts(self.sc, [post], include_closed=True)])
        # And when we do
        self.assertFalse(conv.id in [c.id for c in 
                                     Conversation.objects.lookup_by_posts(self.sc, [post], include_closed=False)])

    def test_reorder_posts_complex(self):
        class DummyPost():

            def __init__(self, id, parent, created_at):
                self.id = id
                self.parent = parent
                self.created_at = created_at

            def __repr__(self):
                return str(self.id)

        root = DummyPost(id=1,
                         parent=None,
                         created_at=0)
        child1 = DummyPost(id=2,
                           parent=root,
                           created_at=1)
        child2 = DummyPost(id=3,
                           parent=root,
                           created_at=2)
        child3 = DummyPost(id=4,
                           parent=root,
                           created_at=3)
        second_level_child1 = DummyPost(id=5,
                                        parent=child1,
                                        created_at=4)
        second_level_child2 = DummyPost(id=6,
                                        parent=child1,
                                        created_at=5)
        second_level_child3 = DummyPost(id=7,
                                        parent=child2,
                                        created_at=6)
        second_level_child4 = DummyPost(id=8,
                                        parent=child3,
                                        created_at=7)
        third_level_child = DummyPost(id=9,
                                      parent=second_level_child1,
                                      created_at=8)

        posts = [root, child1, child2, child3, second_level_child1, second_level_child2, second_level_child3,
                 second_level_child4, third_level_child]
        # The expected order if we consider a reply to be set right after it's parent
        expected = '[1, 2, 5, 9, 6, 3, 7, 4, 8]'
        self.assertEqual(expected, str(reorder_posts(posts)))
        childx = DummyPost(id=10,
                           parent=root,
                           created_at=-1)
        expected = '[1, 10]'
        self.assertEqual(expected, str(reorder_posts([root, childx])))

    def test_user_history_no_reply(self):
        """ Regression for bug where user history was not considered
        until a reply from brand was issued """
        screen_name = 'new_customer'
        self.inbound.add_keyword('foo')
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name)

        self._create_db_post(channel=self.inbound, content="I need a foo. Does anyone have a foo?" + str(99),
                            demand_matchables=False, url=url, user_profile=user_profile)
        # Only first post, should be false
        user_profile.reload()
        self.assertFalse(user_profile.has_history(self.inbound))

        conv = Conversation.objects()[:][0]
        conv.is_closed = True
        conv.save(is_safe=True)
        url = fake_twitter_url(screen_name)
        self._create_db_post(channel=self.inbound, content="I need a foo. Does anyone have a foo?" + str(98),
                            demand_matchables=False, url=url, user_profile=user_profile)

        # At this point, we should have two conversations with one post each, so user history should be present
        user_profile.reload()
        self.assertTrue(user_profile.has_history(self.inbound))

        # Create two separate posts, user history should be already present
        for idx in xrange(2):
            url = fake_twitter_url(screen_name)
            self._create_db_post(channel=self.inbound, content="I need a foo. Does anyone have a foo?" + str(idx),
                                demand_matchables=False, url=url, user_profile=user_profile)
        user_profile.reload()
        self.assertTrue(user_profile.has_history(self.inbound))

    def test_conversations_removal(self):
        screen_name = 'customer'
        self.inbound.add_keyword('foo')
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))

        url = fake_twitter_url(screen_name)


        kw = {'status' : 'Active', 'keywords' : ['foo']}
        SmartTagChannel.objects.create_by_user(
                                                self.user,
                                                title='Foo Tag',
                                                parent_channel=self.inbound.id,
                                                account=self.inbound.account,
                                                **kw)

        # As long as we don't pass the spam limit, all posts should be
        # in the same conversation and in the same response
        for idx in xrange(get_var('INBOUND_SPAM_LIMIT')):
            url = fake_twitter_url(screen_name)
            self._create_db_post(
                                    channel=self.inbound,
                                    content="I need a foo. Does anyone have a foo?" + str(idx),
                                    demand_matchables=False,
                                    url=url,
                                    user_profile=user_profile)
        self.assertEqual(Conversation.objects().count(), 1)
        conv = Conversation.objects()[0]
        self.assertEqual(len(conv.posts), get_var('INBOUND_SPAM_LIMIT'))

        url = fake_twitter_url(screen_name)
        self._create_db_post(
                                channel=self.inbound,
                                content="I need a foo. Does anyone have another foo?",
                                demand_matchables=False,
                                url=url,
                                user_profile=user_profile)
        self.assertEqual(Conversation.objects().count(), 1)
        conv = Conversation.objects()[0]
        self.assertEqual(len(conv.posts), 1)

    def test_conversations_user_history(self):
        self.login()
        sc1 = TwitterServiceChannel.objects.create_by_user(
            self.user,
            account=self.user.account,
            title='Service Channel')
        inbound1 = sc1.inbound_channel
        outbound1 = sc1.outbound_channel
        outbound1.usernames = ['test']
        outbound1.save()
        self.user.outbound_channels['Twitter'] = str(self.outbound.id)
        self.user.save()
        screen_name = 'Customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name)

        post = self._create_db_post(
            channel=self.inbound,
            content="I need a foo. Does anyone have a foo?",
            demand_matchables=True,
            url=url,
            user_profile=user_profile,
            twitter={'id': fake_status_id()})
        self.assertEqual(Conversation.objects().count(), 1)

        url = fake_twitter_url(screen_name)
        post2 = self._create_db_post(
            channel=inbound1,
            content="I need a foo. Does anyone have a foo?",
            demand_matchables=True,
            url=url,
            user_profile=user_profile,
            twitter={'id': fake_status_id()})
        self.assertEqual(Conversation.objects().count(), 2)

        self.assertEqual(Conversation.objects().count(), 2)

        # Check that conversations by user profile are separable
        conversations = user_profile.get_conversations(self.user, self.inbound)
        self.assertEqual(len(conversations), 1)
        conversations = user_profile.get_conversations(self.user, inbound1)
        self.assertEqual(len(conversations), 1)

    @unittest.skip("Deprecating this case since Inbox is deprecated")
    def test_conversation_through_engage(self):
        self.user.outbound_channels['Twitter'] = str(self.outbound.id)
        self.user.save()
        screen_name = 'Customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))

        url = fake_twitter_url(screen_name)

        matchable = self._create_db_matchable(creative="Foo Bar Baz",
            intention_topics=['foo'],
            url=url,
            channels=[self.inbound, self.outbound])

        post = self._create_db_post(
            channel=self.inbound,
            content="I need a foo. Does anyone have a foo?",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)

        # This behavior is deprecated - conversation created on every inbound
        # #post1 should not initiate a new thread since user is not in contacts and not tracked
        # self.assertEqual(Conversation.objects().count(), 0)
        self.assertEqual(Conversation.objects().count(), 1)


        response = Response.objects.get(id=post.response_id)
        assert matchable == response.matchable
        self._post_response(response, response.matchable)
        post.reload()
        assert(post.is_root_post())
        self.assertEqual(Conversation.objects().count(), 1)

        reply_status_id = post.native_id

        thread_len = 3
        self.assertEqual(len(Conversation.objects.get().posts), 2)
        for i in range(thread_len):
            twitter_data = \
                {'twitter':
                     {'id': "%s%s" % (fake_status_id(), i),
                      'in_reply_to_status_id': reply_status_id
                     }
                }

            post = self._create_db_post(
                channels=[self.inbound],
                content="I need a foo. Does anyone have a foo? " + content_gen().next(),
                user_profile=user_profile,
                url=fake_twitter_url(screen_name, status_id=fake_status_id()),
                **twitter_data)

            response = Response.objects.upsert_from_post(post)
            self._post_response(response, response.matchable)
            self.assertEqual(len(Conversation.objects.get().posts), (i + 2) * 2)

        self.assertEqual(Conversation.objects().count(), 1)
        self.assertEqual(len(Conversation.objects.get().posts), (thread_len + 1) * 2)

        #print "-------------------------- DOING STATS RESET ---------------------------"
        #from solariat_bottle.scripts.reset_stats2 import do_it
        #do_it()
        #self.assertTrue(False)

    def test_outer_conversation(self):
        """Test threads created properly
        when no tweets posted from system
        and tweet authors are tracked"""

        #Users taking part in conversation
        screen_names = ['screeN_Name_1', 'UserName_2']
        for screen_name in screen_names:
            self.sc.add_username(screen_name)

        user_profiles = [UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
                         for screen_name in screen_names]

        i = 0
        posts_num = 10
        reply_to = None
        first_post = None

        while i < posts_num:
            i += 1
            profile = user_profiles[i % len(screen_names)]
            url = fake_twitter_url(profile.screen_name)

            twitter_data = {'twitter':{'id': fake_status_id()}}
            if reply_to:
                twitter_data['twitter']['in_reply_to_status_id'] = reply_to

            post = self._create_db_post(
                channel=self.sc,
                content=content_gen(base_content=self.DEFAULT_ENGLISH_CONTENT).next(),
                url=url,
                user_profile=profile,
                **twitter_data)
            if not first_post:
                first_post = post

            post.reload()
            reply_to = post.native_id

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(len(Conversation.objects.get().posts), posts_num)

    def test_outer_conversation_no_track(self):
        """Tests conversation is being created
        having only Inbound and Outbound posts
        and no tracked users.
        """
        cg = content_gen(['test', '#test', 'Test', '#teST'])

        #Users taking part in conversation
        screen_names = ['Customer', 'Support']
        # converstion should start with Customer
        # screen_names = ['Support', 'Customer']

        user_profiles = [UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
                         for screen_name in screen_names]

        channels = {'Customer': self.inbound,
                    'Support': self.outbound}

        i = 0
        posts_num = 10
        reply_to = None
        first_post = None

        while i < posts_num:
            i += 1
            profile = user_profiles[i % len(screen_names)]
            url = fake_twitter_url(profile.screen_name)

            twitter_data = {'twitter': {'id': fake_status_id()}}
            if reply_to:
                twitter_data['twitter']['in_reply_to_status_id'] = reply_to

            channel = channels.get(profile.screen_name)

            post = self._create_db_post(
                channel=channel,
                content=cg.next(),
                url=url,
                user_profile=self.support,
                **twitter_data)

            if not first_post:
                first_post = post

            post.reload()
            reply_to = post.native_id

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(len(Conversation.objects.get().posts), posts_num)

    def test_incomplete(self):
        """Tests conversation incomplete status (no parent post)"""
        thread = Conversation.objects.create(channel=self.sc.id)
        parent_status = fake_status_id()
        twitter_data = {
            'twitter': {
                'id': fake_status_id(),
                'in_reply_to_status_id': parent_status
            }
        }

        post = self._create_db_post(
            channel=self.inbound,
            content="new foo in foostore",
            **twitter_data)

        self.assertFalse(thread.is_incomplete)

        thread.add_posts([post])
        thread.reload()

        self.assertTrue(thread.is_incomplete)

        #add missing parent
        twitter_data = {
            'twitter': {
                'id': parent_status
            }
        }

        post = self._create_db_post(
            channel=self.outbound,
            content="new foo",
            user_profile=self.support,
            **twitter_data)
        thread.add_posts([post])
        thread.reload()

        self.assertFalse(thread.is_incomplete)

    @unittest.skip("deprecating Response")
    def test_handle_response_filtered_update(self):
        '''
        Inbound post gets allocated to a response, but then gets
        filtered out. Thus we want the response to go from
        pending to filtered.
        '''

        screen_name = 'customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name, status_id=fake_status_id())


        # Make sure initial post will be actionable
        self.inbound.add_keyword('laptop')

        p1 = self._create_db_post(
            channel=self.inbound,
            content="I need a laptop. Does anyone have a laptop? P1",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)

        response = Response.objects()[0]
        conv     = Conversation.objects()[0]
        self.assertEqual(response.post.id, p1.id)
        self.assertEqual(response.status, 'pending')
        self.assertTrue(self.inbound.is_assigned(p1))

        # Create a similar post
        other_screen_name = "Joe_blow"
        other_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=other_screen_name))
        other_url = fake_twitter_url(other_screen_name, status_id=fake_status_id())
        p2 = self._create_db_post(
            channel=self.inbound,
            content="I need a laptop. Does anyone have a laptop? P2",
            demand_matchables=True,
            url=other_url,
            user_profile=other_profile)

        # Should be 2 conversations
        conv.reload()
        self.assertEqual(len(Response.objects()), 2)
        self.assertEqual(len(Conversation.objects()), 2)

        p2.handle_reject(self.user, [self.inbound])
        p1.reload()
        response.reload()
        self.assertFalse(self.inbound.is_assigned(p1))
        self.assertEqual(response.status, 'filtered')

    def test_reject_channel_filt(self):
        # Have a bunch of posts with a similar topic, eg laptop
        # some of them state needs, other problems, handle_accept
        # on a need then reject a problem. Make sure filtering works correctly.
        screen_name = 'customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name, status_id=fake_status_id())

        # Make sure initial posts will be actionable
        self.inbound.add_keyword('display')
        needs = ['I need a new display', 'I want a new display', 'I need a better display',
                 'I need a display', 'I need another display', 'I need some better display']
        problems = ['I have a problem with my display', 'My display is not working',
                    'My display is not working properly', 'My new display is not working',
                    'I have problems with my dislay', 'The display is not working.']
        needs_posts = []
        problem_posts = []
        for idx in xrange(len(needs)):
            screen_name = 'need_customer_' + str(idx)
            user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
            url = fake_twitter_url(screen_name, status_id=fake_status_id())
            needs_posts.append(self._create_db_post(
                                                    channel=self.inbound,
                                                    content=needs[idx],
                                                    demand_matchables=True,
                                                    url=url,
                                                    user_profile=user_profile))
        for idx in xrange(len(problems)):
            screen_name = 'problem_customer_' + str(idx)
            user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
            url = fake_twitter_url(screen_name, status_id=fake_status_id())
            problem_posts.append(self._create_db_post(
                                                    channel=self.inbound,
                                                    content=problems[idx],
                                                    demand_matchables=True,
                                                    url=url,
                                                    user_profile=user_profile))
        # Accept a few needs and reject a fre problems, check that everything
        # propagates as expected
        for idx in xrange(3, 6):
            needs_posts[idx].handle_accept(self.user, [self.inbound])
            problem_posts[idx].handle_reject(self.user, [self.inbound])
        #needs_posts[3].handle_accept(self.user, [self.inbound])
        #problem_posts[3].handle_reject(self.user, [self.inbound])
        for idx in xrange(3):
            need_p = needs_posts[idx]
            problem_p = problem_posts[idx]
            need_p.reload()
            problem_p.reload()
            self.assertEqual(need_p.channel_assignments[str(self.inbound.id)], 'highlighted')
            self.assertEqual(problem_p.channel_assignments[str(self.inbound.id)], 'discarded')

    @unittest.skip("Deprecating this case, since Responses and Inbox are deprected")
    def test_reject_intention_propagation(self):
        # Now after recent changes, the filter should propagate even
        # further than just similar intention, so just rejecting
        # a laptop need should also propagate to laptop problems if
        # classifier is not trained for more than that.
        screen_name = 'customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name, status_id=fake_status_id())

        self._create_db_matchable(creative="Foo Bar Baz",
                                  intention_topics=['laptop'],
                                  url=url,
                                  channels=[self.inbound, self.outbound])

        # Make sure initial posts will be actionable
        self.inbound.add_keyword('laptop')
        needs_and_problems = ['I need a new laptop', 'I want a new laptop',
                              'I need a better laptop', 'I have a problem with my laptop',
                              'My laptop is not working', 'My laptop is not working properly']
        posts = []
        for idx in xrange(len(needs_and_problems)):
            # Create 55 new responses and conversations
            screen_name = 'customer_' + str(idx)
            user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
            url = fake_twitter_url(screen_name, status_id=fake_status_id())
            posts.append(self._create_db_post(
                                                channel=self.inbound,
                                                content=needs_and_problems[idx],
                                                demand_matchables=True,
                                                url=url,
                                                user_profile=user_profile))
        posts[5].handle_reject(self.user, [self.inbound])
        for idx in xrange(5):
            need_p = posts[idx]
            need_p.reload()
            self.assertEqual(need_p.channel_assignments[str(self.inbound.id)], 'discarded')
            need_resp = Response.objects.get(need_p.response_id)
            self.assertEqual(need_resp.status, 'filtered')

    @unittest.skip("deprecating Response")
    def test_post_reject_similar_filter_responses_limit(self):
        # Have a large bunch of posts. Then just reject the latest one
        # and check that we propagate both up to 50 responses ago and
        # for all posts in same conversation
        screen_name = 'customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name, status_id=fake_status_id())

        # Make sure initial post will be actionable
        self.inbound.add_keyword('laptop')

        p1 = self._create_db_post(
            channel=self.inbound,
            content="I need a laptop. Does anyone have a laptop? P1",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)

        response = Response.objects()[0]
        conv     = Conversation.objects()[0]
        self.assertEqual(response.post.id, p1.id)
        self.assertEqual(response.status, 'pending')
        self.assertTrue(self.inbound.is_assigned(p1))

        for idx in xrange(95):
            # Create 55 new responses and conversations
            screen_name = 'customer_' + str(idx)
            user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
            url = fake_twitter_url(screen_name, status_id=fake_status_id())
            self._create_db_post(
                        channel=self.inbound,
                        content="I need a laptop. Does anyone have a laptop? P1" + str(idx),
                        demand_matchables=True,
                        url=url,
                        user_profile=user_profile)

        # Create a similar post
        other_screen_name = "Joe_blow"
        other_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=other_screen_name))
        other_url = fake_twitter_url(other_screen_name, status_id=fake_status_id())
        p2 = self._create_db_post(
            channel=self.inbound,
            content="I need a laptop. Does anyone have a laptop? P2",
            demand_matchables=True,
            url=other_url,
            user_profile=other_profile)

        # Should be 2 conversations
        conv.reload()
        self.assertEqual(len(Response.objects()), 97)
        self.assertEqual(len(Conversation.objects()), 97)

        p2.handle_reject(self.user, [self.inbound])
        p1.reload()
        response.reload()

        # At this point we should have anything between 50 to 60
        # filtered responses and the rest pending.
        # This is because we take 10 similar posts + the posts from the
        # latest 50 response (the unique set of this)
        filtered_count = Response.objects(status='filtered').count()
        pending_count = Response.objects(status='pending').count()
        rejected_count = Response.objects(status='rejected').count()
        self.assertTrue(50 <= filtered_count <= 60)
        self.assertTrue(filtered_count + pending_count + rejected_count == 97)
        self.assertEqual(rejected_count, 1)

    def test_smart_tag_rejection(self):
        stc = SmartTagChannel.objects.create_by_user(
                                            self.user,
                                            title='laptop tag',
                                            parent_channel=self.inbound.id,
                                            account=self.inbound.account,
                                            keywords=['laptop'], status='Active')
        screen_name = 'customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        url = fake_twitter_url(screen_name, status_id=fake_status_id())

        # Make sure initial post will be actionable
        self.inbound.add_keyword('laptop')

        p1 = self._create_db_post(
            channel=self.inbound,
            content="I need a laptop. Does anyone have a laptop? P1",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)
        url = fake_twitter_url(screen_name, status_id=fake_status_id())
        self._create_db_post(
            channel=self.inbound,
            content="I really need a laptop. Does anyone have a laptop? P1",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)
        url = fake_twitter_url(screen_name, status_id=fake_status_id())
        self._create_db_post(
            channel=self.inbound,
            content="How are we on that laptop problem? P1",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)

        conv     = Conversation.objects()[0]
        self.assertTrue(self.inbound.is_assigned(p1))
        self.assertTrue(str(stc.id) in p1.tag_assignments)
        self.assertTrue(len(conv.posts), 1)

        # Now create a whole bunch of other posts/ responses then just
        # remove the tag from one of the posts from the conversation.
        # This should remove the tag from all the posts in the conversation.
        for idx in xrange(95):
            # Create 55 new responses and conversations
            screen_name = 'customer_' + str(idx)
            user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
            url = fake_twitter_url(screen_name, status_id=fake_status_id())
            self._create_db_post(
                        channel=self.inbound,
                        content="I need a laptop. Does anyone have a laptop? P1" + str(idx),
                        demand_matchables=True,
                        url=url,
                        user_profile=user_profile)

        # Create a new post from the same conversation and remove the tag
        url = fake_twitter_url(screen_name, status_id=fake_status_id())
        p4 = self._create_db_post(
            channel=self.inbound,
            content="Still no answer on my laptop problem? P1",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)

        p4.handle_remove_tag(self.user, [stc])
        self.assertFalse(stc.is_assigned(p4))

        conversation = Conversation.objects.lookup_conversations(self.sc, [p4])[0]
        self.assertTrue(len(conversation.posts), 2)
        for post in conversation.query_posts():
            self.assertFalse(stc.is_assigned(post))

    @unittest.skip("deprecated")
    def test_response_status_update(self):
        screen_name = 'customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))

        url = fake_twitter_url(screen_name, status_id=fake_status_id())
        self._create_db_matchable(creative="Foo Bar Baz",
                                  intention_topics=['foo'],
                                  url=url,
                                  channels=[self.inbound, self.outbound])
        self._create_db_matchable(creative="Foo Bar Baz",
                                  intention_topics=['laptop'],
                                  url=url,
                                  channels=[self.inbound, self.outbound])
        self.inbound.add_keyword('foo')
        first_discarded_post = self._create_db_post(
            channel=self.inbound,
            content="I need a laptop. Does anyone have a laptop?",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)

        url = fake_twitter_url(screen_name, status_id=fake_status_id())
        second_discarded_post = self._create_db_post(
            channel=self.inbound,
            content="I really need that laptop.",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)

        conv = Conversation.objects()[0]
        conversation_ids = [first_discarded_post.id, second_discarded_post.id]
        self.assertEqual(conv.contacts, [first_discarded_post.user_profile.id])
        self.assertEqual(list(conv.posts), conversation_ids)
        self.assertEqual(first_discarded_post.get_assignment(self.inbound), 'discarded')
        self.assertEqual(second_discarded_post.get_assignment(self.inbound), 'discarded')

        url = fake_twitter_url(screen_name, status_id=fake_status_id())
        first_valid_post = self._create_db_post(
                                    channel=self.inbound,
                                    content="I need a foo. Does anyone have a foo?",
                                    demand_matchables=True,
                                    url=url,
                                    user_profile=user_profile)
        url = fake_twitter_url(screen_name, status_id=fake_status_id())
        second_valid_post = self._create_db_post(
                                    channel=self.inbound,
                                    content="I really need that foo.",
                                    demand_matchables=True,
                                    url=url,
                                    user_profile=user_profile)
        conversation_ids.append(first_valid_post.id)
        conversation_ids.append(second_valid_post.id)
        conv = Conversation.objects()[0]
        self.assertEqual(conv.contacts, [first_discarded_post.user_profile.id])
        self.assertEqual(list(conv.posts), conversation_ids)
        self.assertEqual(first_valid_post.get_assignment(self.inbound), 'highlighted')
        self.assertEqual(second_valid_post.get_assignment(self.inbound), 'highlighted')

        ## At this point we should have one conversation, two responses for it
        ## in rejected state and one pending with two different posts. Check for that now.
        first_disc_response = conv.get_response_for_post(first_discarded_post)
        second_disc_response = conv.get_response_for_post(second_discarded_post)
        self.assertNotEqual(first_disc_response.id,
                            second_disc_response.id) # Should be the different
        first_valid_response = conv.get_response_for_post(first_valid_post)
        second_valid_response = conv.get_response_for_post(second_valid_post)
        self.assertEqual(first_valid_response.id,
                         second_valid_response.id) # Should be the same
        self.assertNotEqual(first_disc_response.id,
                            first_valid_response.id) # Should be different
        self.assertNotEqual(second_disc_response.id,
                            first_valid_response.id) # Should be different

        # Test that origin post and latest post works for response.
        self.assertEqual(first_valid_response.post.id, first_valid_post.id)
        self.assertEqual(first_valid_response.latest_post.id, second_valid_post.id)

        #Now check that getting posts for response work properly.
        first_disc_posts = first_disc_response.posts
        self.assertEqual([p.id for p in first_disc_posts],
                         [first_discarded_post.id])
        self.assertEqual(first_disc_response.status, 'filtered')
        second_disc_posts = second_disc_response.posts
        self.assertEqual([p.id for p in second_disc_posts],
                         [second_discarded_post.id])
        self.assertEqual(second_disc_response.status, 'filtered')
        valid_posts = first_valid_response.posts
        self.assertEqual([p.id for p in valid_posts],
                         [first_valid_post.id, second_valid_post.id])
        self.assertEqual(first_valid_response.status, 'pending')

        # Now play around with post status updates and check that response
        # is also updating properly it's status
        # First change one of the pending posts to rejected
        first_valid_post._handle_filter([self.inbound], 'rejected')
        first_valid_response = Response.objects.get(first_valid_response.id)
        self.assertEqual(first_valid_response.status, 'rejected')
        for post in first_valid_response.posts:
            self.assertEqual(post.get_assignment(self.inbound), 'rejected')

        # Now change it to actionable and make sure response is back in pending
        first_valid_post._handle_filter([self.inbound], 'actionable')
        first_valid_response = Response.objects.get(first_valid_response.id)
        self.assertEqual(first_valid_response.status, 'pending')
        for post in first_valid_response.posts:
            self.assertEqual(post.get_assignment(self.inbound), 'actionable')

        # Finally, if there is already a pending post, try to change another one
        # and expect that is not the case, since we can have at most one pending
        # response for a conversation.
        second_discarded_post._handle_filter([self.inbound], 'actionable')
        first_disc_response = Response.objects.get(first_disc_response.id)
        self.assertEqual(first_disc_response.status, 'filtered')
        second_discarded_post = Post.objects.get(second_discarded_post.id)
        self.assertEqual(second_discarded_post.get_assignment(self.inbound), 'actionable')

    def test_stats(self):
        """Test conversation stats
        - volume
        - average latency
        """
        cg = content_gen(['test', '#test', 'Test', '#teST'], base_content="I need a")

        from solariat.utils.timeslot  import parse_date

        posts_num = 10
        now    = parse_date('03/15/2013')
        period = (now - timedelta(days=10), now)
        period_sec = (period[1] - period[0]).total_seconds() - 1

        incr = int(period_sec / (posts_num - 1))
        created_dates = [period[0] + timedelta(seconds=i*incr) for i in range(posts_num)]
        created_dates = map(datasift_date_format, created_dates)

        #Users taking part in conversation
        screen_names = ['Customer', 'Support']

        user_profiles = [UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
                         for screen_name in screen_names]

        channels = {'Customer': self.inbound,
                    'Support': self.outbound}
        self.sc.add_username('@Support')
        #Do not add keywords until fixed
        # self.sc.add_keyword('test')
        # self.sc.add_keyword('#test')

        i = 0
        reply_to = None
        first_post = None

        while i < posts_num:
            profile = user_profiles[i % len(screen_names)]
            url = fake_twitter_url(profile.screen_name)

            twitter_data = {'twitter':
                                {'id': fake_status_id(),
                                 'created_at': created_dates[i]}
                            }
            if reply_to:
                twitter_data['twitter']['in_reply_to_status_id'] = reply_to

            #Do not include mentions until fixed
            #twitter_data['twitter']['mentions'] = self.sc.usernames

            channel = channels.get(profile.screen_name)

            post = self._create_db_post(
                channel=channel,
                content=cg.next(),
                url=url,
                user_profile=self.support,
                **twitter_data)

            if not first_post:
                first_post = post

            post.reload()
            reply_to = post.native_id
            i += 1

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(len(Conversation.objects.get().posts), posts_num)

        conversation = Conversation.objects.get()
        stats = ChannelHotTopics.objects(channel_num=conversation.service_channel.inbound_channel.counter)
        self.assertTrue(stats.count() > 0)

        #by time span
        from_, to_ = period
        from solariat.utils.timeslot import datetime_to_timeslot

        for level in ('day', 'hour'):  #no 'hour' stats
            from_ts = datetime_to_timeslot(from_, level)
            to_ts = datetime_to_timeslot(to_, level)
            stats = list(ChannelTrends.objects.find(
                time_slot__gte=from_ts,
                time_slot__lte=to_ts))
            volume = 0
            avg_response_time = 0
            for stat in stats:
                for es in stat.filter(agent=ALL_AGENTS, language=Lang.ALL):
                    volume += es.response_volume
                    avg_response_time += es.response_time
            avg_response_time /= volume

            self.assertEqual(volume, posts_num / 2)
            self.assertEqual(int(avg_response_time), int(incr))

    def test_channel_assignment(self):
        post_content = "@test #test test post writen in english, that's for sure"
        post = self._create_db_post(post_content,
                                    user_profile={'screen_name': 'client'},
                                    channels=[self.inbound])
        post = self._create_db_post(post_content,
                                    user_profile={'screen_name': 'agent'},
                                    channels=[self.outbound])
        self.assertTrue(set(post.channels) == set([self.outbound.id]))
        self.assertEqual(len(post.channel_assignments), 1)
        self.assertTrue(str(self.outbound.id) in post.channel_assignments)

        post = self._create_db_post(post_content,
                                    channels=[self.inbound])
        self.assertTrue(set(post.channels) == set([self.inbound.id]))
        self.assertEqual(len(post.channel_assignments), 1)
        self.assertTrue(str(self.inbound.id) in post.channel_assignments)

    def test_amplify(self):
        "Tests the retweets are stored in amplifiers list."
        original_status_id = fake_status_id()
        original_tweet = {
            'twitter': {
                'id': original_status_id,
                'created_at': timeslot.now(),
            }
        }
        original_author = UserProfile.objects.upsert('Twitter', dict(screen_name='first', user_id="1"))
        retweeter = UserProfile.objects.upsert('Twitter', dict(screen_name='second', user_id="2"))

        retweet_id = fake_status_id()
        retweet = {
            'twitter': {
                'id': retweet_id,
                'retweet':
                    {
                        'id': retweet_id,
                        #'text': content_gen().next(),
                        'created_at': timeslot.now(),
                        'user': {
                            'id': 2,
                            'screen_name': 'second'
                        }
                    },
                'retweeted':
                    {
                        'id': original_status_id,
                        'user': {
                            'id': 1,
                            'screen_name': 'first'
                        }
                    }

            }
        }

        post1 = self._create_db_post(
            user_profile=original_author,
            channel=self.sc,
            content=content_gen().next(),
            **original_tweet)

        post2 = self._create_db_post(
            user_profile=retweeter,
            channel=self.sc,
            content=content_gen().next(),
            **retweet)

        conversation = Conversation.objects.get(channel=self.sc.id)
        # import ipdb; ipdb.set_trace()
        self.assertEqual(len(conversation.amplifiers), 1)
        self.assertEqual(conversation.amplifiers[0], post2.id)

    def test_multi_service_channel(self):
        
        sc1 = self.sc
        sc1.add_username('@test')
        sc2 = TwitterServiceChannel.objects.create_by_user(
            self.user,
            title='Service Channel 2')
        sc2.add_username('@test')

        contact = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        support = UserProfile.objects.upsert('Twitter', dict(screen_name='@test'))

        post = self._create_tweet(
            user_profile=contact,
            channels=[sc1],
            content="Content")
        self.assertEqual(Conversation.objects(channel=sc1.id).count(), 1)

        self._create_tweet(
            user_profile=support,
            channels=[sc2],
            content="Content",
            in_reply_to=post)
        # Conversation split between two service channels
        self.assertEqual(Conversation.objects(channel=sc2.id).count(), 1)
        self.assertEqual(Conversation.objects(channel=sc1.id).count(), 1)

    def test_extra_cases(self):
        # user2 responds or retweets post of user1
        contact1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@contact1', user_id='1111111111'))
        contact2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@contact2', user_id='2222222222'))
        support = UserProfile.objects.upsert('Twitter', dict(screen_name='@support', user_id='33333333333'))

        status_id = fake_status_id()
        twitter_data = {'twitter': {'id': status_id, 'created_at': timeslot.now()}}
        post = self._create_db_post(
            user_profile=contact1,
            channels=[self.sc.inbound_channel],
            content="@support My foo is not working out for me",
            **twitter_data)
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)

        # reply to post only in one channel
        twitter_data['twitter']['id'] = fake_status_id()
        twitter_data['twitter']['in_reply_to_status_id'] = status_id
        post_reply = self._create_db_post(
            user_profile=contact2,
            channels=[self.sc.inbound_channel],
            content="@contact1 @support I have the same problem",
            **twitter_data)
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)

        # contact2 replied to contact1 post
        # now just send another inbound post from contact1
        post = self._create_db_post(
            user_profile=contact2,
            channels=[self.sc.inbound_channel],
            content="@support will this post be added to 2 conversations?",
            twitter={"id": fake_status_id()})
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)

        twitter_data['twitter']['id'] = fake_status_id()
        twitter_data['twitter']['in_reply_to_status_id'] = status_id
        reply = self._create_db_post(
            user_profile=self.support,
            channels=[self.sc.outbound_channel],
            content="@contact1 Response",
            **twitter_data)
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)

        twitter_data['twitter']['id'] = fake_status_id()
        twitter_data['twitter']['in_reply_to_status_id'] = post.native_id
        reply2 = self._create_db_post(
            user_profile=self.support,
            channels=[self.sc.outbound_channel],
            content="@contact2 Response",
            **twitter_data)
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)

        # contact1 answers contact2
        twitter_data['twitter']['id'] = fake_status_id()
        twitter_data['twitter']['in_reply_to_status_id'] = post.native_id
        message = self._create_db_post(
            user_profile=support,
            channels=[self.sc.inbound_channel],
            content="@contact2 asd",
            **twitter_data)
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)

    def test_outbound_post_author(self):
        """Outbound post author should not be used for conversation lookup
        """
        contact1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@contact1', user_id="1111111111"))
        contact2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@contact2', user_id="2222222222"))
        support =  UserProfile.objects.upsert('Twitter', dict(screen_name='@support',  user_id="3333333333"))

        status_id1 = fake_status_id()
        twitter_data = {
            'twitter': {
                'id': status_id1,
                # 'created_at': timeslot.now(),
            }
        }

        in_post1 = self._create_db_post(
            user_profile=contact1,
            channels=[self.sc],
            content="I need some foo",
            **twitter_data)
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)

        status_id2 = fake_status_id()
        twitter_data['twitter']['id'] = status_id2
        in_post2 = self._create_db_post(
            user_profile=contact2,
            channels=[self.sc],
            content="I like my foo",
            **twitter_data)
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 2)

        # Reply to first post
        twitter_data['twitter']['id'] = fake_status_id()
        twitter_data['twitter']['in_reply_to_status_id'] = status_id1
        reply1 = self._create_db_post(
            user_profile=self.support,
            channels=[self.sc.outbound_channel],
            content="Content",
            **twitter_data)

        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 2)

        # Reply to second post
        twitter_data['twitter']['id'] = fake_status_id()
        twitter_data['twitter']['in_reply_to_status_id'] = status_id2
        reply2 = self._create_db_post(
            user_profile=self.support,
            channels=[self.sc.outbound_channel],
            content="Content",
            **twitter_data)
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 2)

        # Both conversation should have 2 posts and 1 contact
        for c in Conversation.objects():
            self.assertEqual(len(c.posts), 2)
            #print c.contacts
            self.assertEqual(len(c.contacts), 1)
            if str(in_post1.id) in c.posts:
                self.assertEqual(c.contacts, [contact1.id])
            if str(in_post2.id) in c.posts:
                self.assertEqual(c.contacts, [contact2.id])

    def test_intermediate_inbound_reply(self):
        screen_name = '@contact1'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name='@contact1', user_id="1111111111"))
        support =  UserProfile.objects.upsert('Twitter', dict(screen_name='@support',  user_id="3333333333"))

        self.inbound.add_keyword('foo')
        url = fake_twitter_url(screen_name)

        self.inbound.add_keyword('foo')

        status_id = fake_status_id()
        status_id1 = str(status_id) + '1'
        twitter_data = {
            'twitter': {
                'id': status_id1,
                # 'created_at': timeslot.now(),
            }
        }
        in_post1 = self._create_db_post(
                                    channel=self.inbound,
                                    content="I need a foo. Does anyone have a foo?",
                                    demand_matchables=True,
                                    user_profile=user_profile,
                                    **twitter_data)

        status_id2 = str(status_id) + '2'
        twitter_data['twitter']['id'] = status_id2
        in_post2 = self._create_db_post(
                                    channel=self.inbound,
                                    content="I need some more foo. Does anyone have a foo?",
                                    demand_matchables=True,
                                    user_profile=user_profile,
                                    **twitter_data)

        status_id3 = str(status_id) + '3'
        twitter_data['twitter']['id'] = status_id3
        in_post3 = self._create_db_post(
                                    channel=self.inbound,
                                    content="I need even more foo. Does anyone have a foo?",
                                    demand_matchables=True,
                                    user_profile=user_profile,
                                    **twitter_data)

        status_id4 = str(status_id) + '4'
        twitter_data['twitter']['id'] = status_id4
        in_post4 = self._create_db_post(
                                    channel=self.inbound,
                                    content="I need extra foo. Does anyone have a foo?",
                                    demand_matchables=True,
                                    user_profile=user_profile,
                                    **twitter_data)

        # Reply to first post
        twitter_data['twitter']['id'] = fake_status_id()
        twitter_data['twitter']['in_reply_to_status_id'] = status_id2
        reply1 = self._create_db_post(
                                    channel=self.outbound,
                                    content="Here you go, take your damned foo!",
                                    demand_matchables=True,
                                    user_profile=support,
                                    **twitter_data)
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)
        conv = Conversation.objects()[0]
        self.assertEqual(len(conv.posts), 5)

    def test_reply_on_intermediate_inbound_after_reply_to_latest(self):
        # Github issue #3989
        customer1_screen = '@contact1'
        customer2_screen = '@contact2'
        customer3_screen = '@contact3'
        brand_screen = 'brand'

        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name=customer1_screen, user_id="1111111111"))
        customer2 = UserProfile.objects.upsert('Twitter', dict(screen_name=customer2_screen, user_id="2222222222"))
        customer3 = UserProfile.objects.upsert('Twitter', dict(screen_name=customer3_screen, user_id="3333333333"))
        brand = UserProfile.objects.upsert('Twitter', dict(screen_name=brand_screen,  user_id="4444444444"))

        self.inbound.add_keyword('foo')
        url = fake_twitter_url(customer1_screen)
        self.inbound.add_keyword('foo')

        status_id = fake_status_id()
        status_id1 = str(status_id) + '1'
        twitter_data = {
            'twitter': {
                'id': status_id1,
                # 'created_at': timeslot.now(),
            }
        }
        in_post1 = self._create_db_post(channel=self.inbound,
                                        content="I need a foo. Does anyone have a foo?",
                                        demand_matchables=True,
                                        user_profile=customer1,
                                        **twitter_data)

        status_id2 = str(status_id) + '2'
        twitter_data['twitter']['id'] = status_id2
        twitter_data['twitter']['in_reply_to_status_id'] = status_id1
        in_post2 = self._create_db_post(channel=self.inbound,
                                        content="I need some more foo. Does anyone have a foo?",
                                        demand_matchables=True,
                                        user_profile=customer2,
                                        **twitter_data)

        status_id3 = str(status_id) + '3'
        twitter_data['twitter']['id'] = status_id3
        twitter_data['twitter']['in_reply_to_status_id'] = status_id1
        in_post3 = self._create_db_post(channel=self.inbound,
                                        content="I need even more foo. Does anyone have a foo?",
                                        demand_matchables=True,
                                        user_profile=customer3,
                                        **twitter_data)
        # We have 3 inbound posts, in the form of
        # root
        #  child1
        #  child2
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)
        conv = Conversation.objects()[0]
        self.assertEqual(len(conv.posts), 3)

        # Posting is async
        # Reply to latest post
        twitter_data['twitter']['id'] = str(status_id) + '4'
        twitter_data['twitter']['in_reply_to_status_id'] = status_id3
        reply1 = self._create_db_post(channel=self.outbound,
                                      content="Here you go, take your damned foo!",
                                      demand_matchables=True,
                                      user_profile=self.support,
                                      **twitter_data)
        # Now we replied, no pending responses should exist and conversation length should be up to 4
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)
        conv = Conversation.objects()[0]
        self.assertEqual(len(conv.posts), 4)
        for post in [in_post1, in_post2, in_post3]:
            post.reload()
            self.assertEqual(post.get_assignment(self.inbound), 'replied')

        # Now reply to the middle one aswell, expect still 0 responses pending
        twitter_data['twitter']['id'] = str(status_id) + '5'
        twitter_data['twitter']['in_reply_to_status_id'] = status_id2
        reply1 = self._create_db_post(channel=self.outbound,
                                      content="Here you go, take your damned foo again!",
                                      demand_matchables=True,
                                      user_profile=self.support,
                                      **twitter_data)
        # Now we replied, no pending responses should exist and conversation length should be up to 4
        self.assertEqual(Conversation.objects(channel=self.sc.id).count(), 1)
        conv = Conversation.objects()[0]
        self.assertEqual(len(conv.posts), 5)

    def test_posts_addition(self):
        """
        Testing that Conversation.add_posts(posts) call
        handles post ordering correctly
        """

        status_id    = fake_status_id()
        contact1     = UserProfile.objects.upsert('Twitter', dict(screen_name='@contact1', user_id="1111111111"))
        twitter_data = {'twitter': {'id': status_id, 'created_at': timeslot.now()}}
        post1        = self._create_db_post(
            user_profile=contact1,
            channels=[self.sc],
            content="I need some foo",
            **twitter_data)

        # getting conversation after one ost was created
        conversation = Conversation.objects.get(channel=self.sc.id)

        twitter_data['twitter']['id']         = fake_status_id()
        twitter_data['twitter']['created_at'] = timeslot.now()
        post2        = self._create_db_post(
            user_profile=contact1,
            channels=[self.sc],
            content="I need some foo2",
            **twitter_data)

        twitter_data['twitter']['id']         = fake_status_id()
        twitter_data['twitter']['created_at'] = timeslot.now()
        post3        = self._create_db_post(
            user_profile=contact1,
            channels=[self.sc],
            content="I need some foo3",
            **twitter_data)

        new_posts       = [post2, post3]
        correct_id_list = [p.id for p in [post1, post2, post3]]

        conversation.add_posts(new_posts)
        self.assertEqual(list(conversation.posts), correct_id_list)

class PostsStatsUICase(UICase):
    def setUp(self):
        super(PostsStatsUICase, self).setUp()
        self.login()

        self.sc = TwitterServiceChannel.objects.create_by_user(
            self.user,
            title='Service Channel 2')

        self.from_date = timeslot.now()
        self.to_date = self.from_date + timedelta(minutes=1)

    def _fetch(self, channel, topics, agents):
        DATE_TIME = "%Y-%m-%d %H:%M:%S"
        DATE = "%m/%d/%Y"
        def format_date(dt, format=DATE_TIME):
            return dt.strftime(format)

        def fetch_hot_topics(data):
            data['level'] = 'month'
            data['parent_topic'] = None
            data['from'] = format_date(data['from'], DATE)
            data['to'] = format_date(data['to'], DATE)
            data.pop('topics')
            resp = self.client.post('/hot-topics/json',
                                data=json.dumps(data),
                                content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            resp = json.loads(resp.data)
            self.assertTrue(resp['ok'])
            return resp

        def fetch_topic_trends(data):
            # Distribution by agent query
            data["plot_by"] = "distribution"
            data["group_by"] = "agent"
            data["plot_type"] = "sentiment"
            data['from'] = format_date(data['from'], DATE)
            data['to'] = format_date(data['to'], DATE)

            resp = self.client.post('/trends/json',
                                data=json.dumps(data),
                                content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            resp = json.loads(resp.data)
            self.assertTrue(resp['ok'])
            return resp

        def fetch_posts(data):
            data['from'] = format_date(data['from'], DATE_TIME)
            data['to'] = format_date(data['to'], DATE_TIME)
            data['thresholds'] = {"intention": 0.0}
            resp = self.client.post('/posts/json',
                                data=json.dumps(data),
                                content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            resp = json.loads(resp.data)
            self.assertTrue(resp['ok'])
            return resp

        data = {
            'channel_id' : str(channel.id),
            'from'       : self.from_date,
            'to'         : self.to_date,
            'agents'     : agents and [str(a.id) for a in agents] or [],
            'topics'     : [{'topic': topic, 'topic_type': 'leaf'} for topic in topics],
            'statuses'   : ['actionable', 'actual', 'potential', 'rejected']
        }

        result = fetch_hot_topics(data.copy()), fetch_topic_trends(data.copy()), fetch_posts(data.copy())
        return result

    def test_stats_and_posts(self):
        """Create conversation and verify
        /hot-topics/, /trends/, /posts/ return consistent result"""
        contact = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        support = UserProfile.objects.upsert('Twitter', dict(screen_name='@test'))
        self.sc.add_username(support.user_name)

        from solariat_bottle.db.user import User
        agent = User(email='agent@test.test')
        agent.user_profile = support
        agent.save()
        self.sc.account.add_user(agent)

        # hot topics now only show problem posts
        status_id = fake_status_id()
        twitter_data = {'twitter': {'id': status_id}}
        post = self._create_db_post(
            user_profile=contact,
            channels=[self.sc.inbound_channel],
            content="I have a problem with laptop",
            **twitter_data)

        # Test Inbound
        hot_topics, topic_trends, posts = self._fetch(self.sc.inbound_channel, ['laptop'], None)
        self.assertEqual(len(hot_topics['list']), 1)
        self.assertDictEqual(hot_topics['list'][0], {"topic":"laptop", "topic_count":1, "term_count":1})

        self.assertEqual(len(topic_trends['list']), 1)  # by all agents
        self.assertEqual(topic_trends['list'][0]['data'][0], [2, 1])
        self.assertEqual(topic_trends['list'][0]['label'], 'all')

        self.assertEqual(len(posts['list']), 1)
        self.assertEqual(posts['list'][0]['id_str'], str(post.id))

        # All zeroes for agent query
        hot_topics, topic_trends, posts = self._fetch(self.sc.inbound_channel, ['laptop'], [agent])
        self.assertEqual(len(hot_topics['list']), 0)
        self.assertEqual(len(topic_trends['list']), 0)
        self.assertEqual(len(posts['list']), 0)


        twitter_data['twitter']['id'] = fake_status_id()
        twitter_data['twitter']['in_reply_to_status_id'] = status_id
        reply = self._create_db_post(
            user_profile=support,
            channels=[self.sc.outbound_channel],
            content="Do you need a phone?",
            **twitter_data)

        # Test Inbound after reply
        hot_topics, topic_trends, posts = self._fetch(self.sc.inbound_channel, ['laptop'], None)
        self.assertEqual(len(hot_topics['list']), 1)
        self.assertEqual(len(topic_trends['list']), 1)  # by all_agents
        self.assertEqual(topic_trends['list'][0]['data'][0], [2, 1])
        self.assertEqual(topic_trends['list'][0]['label'], 'agent@test.test')
        self.assertEqual(len(posts['list']), 1)

        hot_topics, topic_trends, posts = self._fetch(self.sc.inbound_channel, ['laptop'], [agent])
        self.assertEqual(len(hot_topics['list']), 1)
        self.assertEqual(len(topic_trends['list']), 1)  # by @test agent
        self.assertEqual(topic_trends['list'][0]['data'][0], [2, 1])
        self.assertEqual(topic_trends['list'][0]['label'], agent.email)
        self.assertEqual(len(posts['list']), 1)

        # Test Outbound after reply
        hot_topics, topic_trends, posts = self._fetch(self.sc.outbound_channel, ['phone'], None)
        self.assertEqual(len(hot_topics['list']), 1)
        self.assertEqual(len(topic_trends['list']), 1)  # by all_agents
        self.assertEqual(topic_trends['list'][0]['data'][0], [2, 1])
        self.assertEqual(topic_trends['list'][0]['label'], 'agent@test.test')
        self.assertEqual(len(posts['list']), 1)

        hot_topics, topic_trends, posts = self._fetch(self.sc.outbound_channel, ['phone'], [agent])
        self.assertEqual(len(hot_topics['list']), 1)
        self.assertEqual(len(topic_trends['list']), 1)  # by @test agent
        self.assertEqual(topic_trends['list'][0]['data'][0], [2, 1])
        self.assertEqual(topic_trends['list'][0]['label'], agent.email)

        self.assertEqual(len(posts['list']), 1)
        self.assertEqual(posts['list'][0]['id_str'], str(reply.id))

        '''
        TODO: FIGURE OUT HOW THIS GOT HERE
        self.assertEqual([post1.id, post2.id], reply_to_post2.reply_to)
        '''

class TestLeariningCase(ConversationBaseCase):

    def setUp(self):
        super(TestLeariningCase, self).setUp()

        self.orig_filter_class = get_var('CHANNEL_FILTER_CLS')
        settings.CHANNEL_FILTER_CLS = 'OnlineChannelFilter'

    def tearDown(self):
        super(TestLeariningCase, self).tearDown()

        settings.CHANNEL_FILTER_CLS = self.orig_filter_class


    def test_learning_is_not_trigered_on_reply(self):
        """reply post shouldn't trigger learning process"""
        ChannelFilter.objects.remove()
        # Generate inbound
        post = self._create_tweet(
            user_profile=self.contact,
            channels=[self.sc],
            content="Content")

        channel_filter = ChannelFilter.objects()
        self.assertEqual(channel_filter.count(), 1)
        self.assertEqual(channel_filter[0].counter, 0)

        # reply to post in outbound channels
        reply = self._create_tweet(
            user_profile=self.support,
            channels=[self.sc],
            content="Content",
            in_reply_to=post)
        reply.handle_reply(self.user, [self.sc])

        channel_filter = ChannelFilter.objects()
        self.assertEqual(channel_filter.count(), 1)
        self.assertEqual(channel_filter[0].counter, 0)


@unittest.skip("Use scripts/for_debug/facebook_dbg/load_facebook_posts.py instead")
class ConversationsParallelCase(UICase):
    def get_expected_event_ids(self):
        from solariat_bottle.scripts.for_debug.facebook_dbg.gen_post_data import get_expected_event_ids
        return get_expected_event_ids()

    @staticmethod
    def gen_post_data(channel):
        from solariat_bottle.scripts.for_debug.facebook_dbg.gen_post_data import gen_post_data
        return gen_post_data(channel)

    def test_building_conversation(self):
        user = self.user
        user.update(is_superuser=True)

        def setup_profiles():
            usernames = [
                'Lisa Bim',
                u'\u041c\u0430\u0448\u0430 \u041f\u043b\u0435\u0442\u043d\u0435\u0432\u0430']
            profiles = []
            for username in usernames:
                profile = UserProfile.objects.upsert(platform='Facebook', profile_data=dict(user_name=username))
                profiles.append(profile)
            return profiles

        def setup_channel():
            from solariat_bottle.db.channel.facebook import FacebookServiceChannel
            sc = FacebookServiceChannel.objects.create_by_user(user, title='FBS', status='Active')
            sc.facebook_page_ids = [u'254277654916277']
            sc.facebook_handle_id = u'106453879753925'
            sc.page_admins = {
                u'254277654916277': [{u'id': u'106453879753925',
                u'name': u'Hope Zillon',
                u'perms': [u'ADMINISTER',
                 u'EDIT_PROFILE',
                 u'CREATE_CONTENT',
                 u'MODERATE_CONTENT',
                 u'CREATE_ADS',
                 u'BASIC_ADMIN'],
                 u'role': u'Admin'}]}
            sc.facebook_access_token = u'fake'
            sc.save()
            return sc

        setup_profiles()
        service_channel = setup_channel()

        def send_post(post_data):
            import traceback
            from solariat_bottle.db.post.utils import factory_by_user

            try:
                return factory_by_user(user, **post_data)
            except:
                with open('test_building_conversation.output.txt', 'a') as out:
                    out.write(traceback.format_exc())
                    out.write('\n')
                    out.flush()
                return None

        from solariat_bottle.tests.base import ProcessPool
        pool = ProcessPool()

        posts = list(self.gen_post_data(service_channel.inbound_channel))
        import random
        random.shuffle(posts)
        result = pool.map(send_post, posts)

        print result
        # conversation sanity check
        self.assertEqual(Conversation.objects(channel=service_channel.id).count(), 1)
        conv = Conversation.objects.get(channel=service_channel.id)
        missing_posts = set(self.get_expected_event_ids()) - set(conv.posts)
        if missing_posts:
            for post in FacebookPost.objects(id__in=missing_posts):
                print(post.plaintext_content)
            assert False, missing_posts
        self.assertEqual(len(set(conv.posts)), 21)



