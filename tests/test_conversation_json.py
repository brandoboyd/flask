import json
import re
import time
from urllib import urlencode

from ..db.user_profiles.user_profile import UserProfile
from ..db.conversation   import Conversation
from .slow.test_conversations import ConversationBaseCase
from .base import UIMixin


class ConversationJsonCase(ConversationBaseCase, UIMixin):
    # overwritten in test_up_json
    url_template = '/conversation/json?%s'
    # This is the final list of post odering expected by user profile and conversation
    expected_post_orders = {'test_reply_to_two_posts' : [1, 5, 2, 4, 3], 
                            'test_reply_to_one_post' : [1, 2, 4, 5, 3]}

    def setUp(self):
        super(ConversationJsonCase, self).setUp()
        self.login()
        self.sc.add_keyword('foo')
        self.sc.add_keyword('test')
        self.sc.add_keyword('laptop')
        self.sc.add_username('@test')

    @classmethod
    def _extract_digits(cls, posts):
        """
        Extracts digits from the responses text
        to compare them to correct order.
        """
        digits = []
        for p in posts:
            digits.append(int(re.search('(\d+)', p['text']).group(1)))
        return digits

    # we overwrite these two functions in test_up_json (testing user profile)
    def create_data(self, channel, post, customer):
        return dict(channel_id=str(channel.id), post_id=long(post.id))

    def get_posts(self, resp):
        return resp['list']

    def test_reply_to_two_posts(self):
        """
        Test replying to several post inside several.
        Scenario:
        1. A customer submits 3 inbound posts - 1, 2, 3
        2. Agent submits response to post 2, and then to post 1 - 4, 5
        3. The order of posts in response of conversation/json is - 1, 5, 2, 4, 3
        """
        customer = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        support = UserProfile.objects.upsert('Twitter', dict(screen_name='@test'))

        post1 = self._create_tweet(
            user_profile=customer,
            channel=self.inbound,
            content="@test I need to fix my laptop! 1")
        # `created_at` needs to be different at least by a milisecond, so we delay by 10 ms
        time.sleep(0.01)

        post2 = self._create_tweet(
            user_profile=customer,
            channel=self.inbound,
            content="@test Guys I'm desperate here! 2")
        time.sleep(0.01)

        post3 = self._create_tweet(
            user_profile=customer,
            channel=self.inbound,
            content="@test LAST POST! 3")
        time.sleep(0.01)

        self.assertEqual(Conversation.objects.count(), 1)

        # Respond and confirm results
        reply_to_post2 = self._create_tweet(
            user_profile=support,
            content="We are doing our best 4", 
            channel=self.outbound,
            in_reply_to=post2)
        time.sleep(0.01)

        reply_to_post1 = self._create_tweet(
            user_profile=support,
            content="We've done our best 5", 
            channel=self.outbound,
            in_reply_to=post1)

        self.assertEqual(Conversation.objects.count(), 1)

        post1.reload()
        post2.reload()
        post3.reload()
        
        self.assertEqual(post1.channel_assignments[str(self.inbound.id)], "replied")
        self.assertEqual(post2.channel_assignments[str(self.inbound.id)], "replied")
        # post3 comes after post2 and we have not replied to it
        self.assertNotEqual(post3.channel_assignments[str(self.inbound.id)], "replied")

        # get the json results for user profile
        data = self.create_data(channel=self.inbound, post=post1, customer=customer)
        resp = self.client.get(self.url_template % urlencode(data))
        resp = json.loads(resp.data)
        posts = self.get_posts(resp)
        order_of_posts = self._extract_digits(posts)
        print 'order_of_posts', order_of_posts
        self.assertEqual(len(posts), 5)
        self.assertEqual(order_of_posts, self.expected_post_orders['test_reply_to_two_posts'])
        
    def test_reply_to_one_post(self):
        """
        Test replying to the same post inside several.
        Scenario:
        1. A customer submits 3 inbound posts - 1, 2, 3
        2. Agent submits response to post 2 - 4, 5
        3. The order of posts in response of conversation/json is - 1, 2, 4, 5, 3
        """
        customer = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        support = UserProfile.objects.upsert('Twitter', dict(screen_name='@test'))

        post1 = self._create_tweet(
            user_profile=customer,
            channel=self.inbound,
            content="@test I need to fix my laptop! 1")
        # `created_at` needs to be different at least by a milisecond, so we delay by 10 ms
        time.sleep(0.01)

        post2 = self._create_tweet(
            user_profile=customer,
            channel=self.inbound,
            content="@test Guys I'm desperate here! 2")
        time.sleep(0.01)

        post3 = self._create_tweet(
            user_profile=customer,
            channel=self.inbound,
            content="@test LAST POST! 3")
        time.sleep(0.01)

        self.assertEqual(Conversation.objects.count(), 1)

        # Respond and confirm results
        reply_to_post2 = self._create_tweet(
            user_profile=support,
            content="We are doing our best 4", 
            channel=self.outbound,
            in_reply_to=post2)
        time.sleep(0.01)

        reply_to_post2 = self._create_tweet(
            user_profile=support,
            content="We've done our best 5", 
            channel=self.outbound,
            in_reply_to=post2)

        self.assertEqual(Conversation.objects.count(), 1)

        post1.reload()
        post2.reload()
        post3.reload()
        
        self.assertEqual(post1.channel_assignments[str(self.inbound.id)], "replied")
        self.assertEqual(post2.channel_assignments[str(self.inbound.id)], "replied")
        # post3 comes after post2 and we have not replied to it
        self.assertNotEqual(post3.channel_assignments[str(self.inbound.id)], "replied")

        # get the json results for user profile
        data = self.create_data(channel=self.inbound, post=post1, customer=customer)
        resp = self.client.get(self.url_template % urlencode(data))
        resp = json.loads(resp.data)
        posts = self.get_posts(resp)
        order_of_posts = self._extract_digits(posts)
        print 'order_of_posts', order_of_posts
        self.assertEqual(len(posts), 5, "URL Template = %s, Resp = %s" % (self.url_template, resp))
        self.assertEqual(order_of_posts, self.expected_post_orders['test_reply_to_one_post'])
