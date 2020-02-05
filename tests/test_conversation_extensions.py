import unittest

from ..db.conversation   import Conversation
from ..db.user_profiles.user_profile import UserProfile

from .slow.test_conversations import ConversationBaseCase


class ConversationInboundChannelFilterCase(ConversationBaseCase):
    def setUp(self):
        super(ConversationInboundChannelFilterCase, self).setUp()
        self.sc.add_keyword('foo')
        self.sc.add_keyword('test')
        self.sc.add_keyword('laptop')
        self.sc.add_username('@test')

    def test_inbound_filter_learning_from_outbound(self):
        '''
        Simple base case that we can transition post to reply based on
        connection to service channel
        '''
        post = self._create_tweet(
            user_profile=UserProfile.objects.upsert('Twitter', dict(screen_name='customer')),
            channel=self.inbound,
            content="@test I need a laptop")

        self.assertEqual(post.channel_assignments[str(self.inbound.id)], 'highlighted')

        self._create_tweet(
            user_profile=UserProfile.objects.upsert('Twitter', {'screenname': 'customer'}),
            channel=self.outbound,
            content="We have just the one for you.",
            in_reply_to=post)

        post.reload()
        self.assertEqual(post.channel_assignments[str(self.inbound.id)], 'replied')


    def test_two_posts_and_one_reply_status_chain(self):
        '''
        Scenario:
        1. A customer named Joe submits an inbound post (status of the posts is actionable)
        2. And another
        3. There is only 1 conversations created.
        '''
        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        self._create_tweet(
            user_profile=customer1,
            channel=self.inbound,
            content="I need to fix my laptop")
        self._create_tweet(
            user_profile=customer1,
            channel=self.inbound,
            content="I need to fix my laptop - now!!! Getting agitated")
        self.assertEqual(Conversation.objects.count(), 1)

    def test_reply_to_several_posts_from_one_user(self):
        """
        Scenario:
        1. A customer submits 2 inbound posts
        2. Agent submit just one response
        3. System updates the status of all three inbound posts in updated to replied
        """
        customer = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        support = UserProfile.objects.upsert('Twitter', dict(screen_name='@test'))

        post1 = self._create_tweet(
            user_profile=customer,
            channel=self.inbound,
            content="@test I need to fix my laptop!")

        self.assertEqual(post1.channel_assignments[str(self.inbound.id)], 'highlighted')

        post2 = self._create_tweet(
            user_profile=customer,
            channel=self.inbound,
            content="@test Guys I'm desperate here!")

        self.assertEqual(post2.channel_assignments[str(self.inbound.id)], 'highlighted')

        self.assertEqual(Conversation.objects.count(), 1)

        # Respond and confirm results
        self._create_tweet(
            user_profile=support,
            content="We are doing our best",
            channel=self.outbound,
            in_reply_to=post2)

        self.assertEqual(Conversation.objects.count(), 1)

        post1.reload()
        post2.reload()
        self.assertEqual(post2.channel_assignments[str(self.inbound.id)], "replied")
        self.assertEqual(post1.channel_assignments[str(self.inbound.id)], "replied")

    def test_two_posts_from_different_users_unrelated_do_not_aggregate(self):
        '''
        2 posts from 2 users
        Results in 2 conversations
        '''
        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        # Tweet from another custmer and verify that the conversation count == 2
        self._create_tweet(
            user_profile=customer1,
            channel=self.inbound,
            content="I need to fix my laptop bag")

        customer2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer2'))
        self._create_tweet(
            user_profile=customer2,
            channel=self.inbound,
            content="I need to fix my laptop bag")

        self.assertEqual(Conversation.objects.count(), 2)

    def test_reply_to_several_posts_from_different_users(self):
        """
        Scenario:
        1. A customer named Joe submits an inbound post (status of the posts is actionable)
        2. Another customer name Tom submits an inbound post as part of the conversation.
        3. An agent submits a response as part of the conversation.
        4. System updates both Joe's and Tom's posts to replied.
        """
        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        customer2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer2'))
        support = UserProfile.objects.upsert('Twitter', dict(screen_name='@test'))

        post1 = self._create_tweet(
            user_profile=customer1,
            channel=self.inbound,
            content="@test I need to fix my laptop!")
        self.assertEqual(post1.channel_assignments[str(self.inbound.id)], 'highlighted')

        # Set this one up as a reply to the original contact
        post2 = self._create_tweet(
            user_profile=customer2,
            channel=self.inbound,
            content="@test Please, help my friend.",
            in_reply_to=post1)

        self.assertEqual(post2.channel_assignments[str(self.inbound.id)], 'highlighted')

        self.assertEqual(Conversation.objects.count(), 1)


        reply_to_post2 = self._create_tweet(
            user_profile=support,
            content="We are doing our best.",
            channel=self.outbound,
            in_reply_to=post2)

        post1.reload()
        post2.reload()

        self.assertEqual(post1.channel_assignments[str(self.inbound.id)], "replied")
        self.assertEqual(post2.channel_assignments[str(self.inbound.id)], "replied")
        self.assertEqual([post1.id, post2.id], reply_to_post2.reply_to)


    def test_conversation_closure(self):
        '''
        Scenario:
        1. A customer named Joe submits an inbound post (status of the posts is actionable)
        2. Close the conversation
        3. Customer goes again
        4. There is another conversation created.
        5. There is anothe response created
        '''
        customer1 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer1'))
        self._create_tweet(
            user_profile=customer1,
            channel=self.inbound,
            content="I need to fix my laptop")

        conv = Conversation.objects()[0]
        conv.is_closed = True
        conv.save(is_safe=True)

        self._create_tweet(
            user_profile=customer1,
            channel=self.inbound,
            content="I need to fix my laptop - now!!! Getting agitated")
        self.assertEqual(Conversation.objects.count(), 2)

@unittest.skip("Response is deprecated")
class ResponseReusageCase(ConversationBaseCase):

    def setUp(self):
        super(ResponseReusageCase, self).setUp()

        self.matchable = self._create_db_matchable(creative="Everyone needs foo.",
                                                   intention_topics = ['foo'])

    def test_response_reusage(self):
        """ If post1 is in inbound channel and post1 has a response, then
        the same response object should be returned for new post (post2) in
        this channel.
        """

        post1 = self._create_db_post(content="@test I need a foo.",
                                     channel=self.sc.inbound,
                                     demand_matchables=True,
                                     user_profile={'screen_name': 'customer'})
        self.assertTrue(self.sc.inbound_channel.is_assigned(post1))

        conv1 = self.sc.upsert_conversation(post1)
        post2 = self._create_db_post(content="I still need a foo!",
                                     channel=self.sc.inbound,
                                     demand_matchables=True,
                                     user_profile={'screen_name': 'customer'})
        conv2 = self.sc.upsert_conversation(post2)

        resp1 = Response.objects.upsert_from_post(post1)
        resp2 = Response.objects.upsert_from_post(post2)
        self.assertEqual(conv1.id, conv2.id)
        self.assertEqual(resp1.id, resp2.id)
        self.assertTrue(resp2.post_date > resp1.post_date)


    def test_no_reuse_after_closure(self):
        '''
        1. User posts.
        2. Conversation is closed.
        3. User posts again
        4. 2 response bjects present
        '''

        self._create_tweet(content="I need a foo.",channel=self.sc.inbound)
        conv  = Conversation.objects()[0]
        conv.is_closed = True
        conv.save(is_safe=True)
        self._create_tweet(content="I still need a foo.",channel=self.sc.inbound)
        self.assertEqual(Response.objects().count(), 2)

    def test_response_reusage_after_replied(self):
        """ If post1 has a reply, then for a new post (post2),
        a new response obj should be created. The response obj of the post1
        shouldn't be reused.
        """

        post1 = self._create_tweet(
            content="I need a foo.",
            channel=self.inbound,
            demand_matchables=True)

        resp1 = Response.objects.upsert_from_post(post1)

        support = UserProfile.objects.upsert('Twitter', dict(screen_name='@test2'))
        self._create_tweet(
            user_profile=support,
            content="We cant help you right now. Sorry.",
            channel=self.outbound,
            demand_matchables=True,
            in_reply_to=post1)

        post2 = self._create_tweet(
            content="I still need a foo.",
            channel=self.inbound,
            demand_matchables=True)
        resp2 = Response.objects.upsert_from_post(post2)
        self.assertNotEqual(resp1.id, resp2.id)
