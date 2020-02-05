# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import json
from datetime import timedelta
from urllib import urlencode

from ..db.channel.twitter import TwitterServiceChannel
from ..db.user_profiles.user_profile import UserProfile
from ..db.conversation import Conversation
from ..db.account import Account
from solariat.utils.timeslot import datetime_to_timestamp_ms, now
from .base import UIMixin
from .test_conversation_json  import ConversationJsonCase
from .slow.test_conversations import ConversationBaseCase


class UserProfileBase(ConversationBaseCase, UIMixin):

    def setUp(self):
        super(UserProfileBase, self).setUp()
        self.login()
        self.up = UserProfile.objects.upsert(
            self.channel.platform, dict(screen_name='joe',
                                        location='Bali',
                                        name='Joe',
                                        profile_image_url='some_profile_image_url'))

    def test_bare_basics(self):
        '''Make sure initial state in terms of conversations is correct'''
        post = self._create_tweet(user_profile=self.contact,
                                  channels=[self.inbound],
                                  content="Content")

        self.assertEqual(len(self.contact.get_conversations(self.user)), 1)

    def test_json_call(self):
        # Post something for joe
        post = self._create_tweet(user_profile=self.up,
                                  channels=[self.inbound],
                                  content="Content")

        # get the json results for user profile
        data = dict(channel_id=str(self.inbound.id), user_name='joe')
        resp = self.client.get('/user_profile/json?%s' % urlencode(data))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))
        self.assertTrue('user' in resp)
        user = resp['user']
        self.assertEqual(user['location'], self.up.location)
        self.assertEqual(user['profile_image_url'],
                         self.up.profile_image_url)
        self.assertEqual(user['profile_url'], self.up.profile_url)
        self.assertEqual(user['screen_name'], self.up.screen_name)
        self.assertEqual(user['user_name'], self.up.user_name)

        # There should be exactly 1 post, from the one conversation
        self.assertEqual(len(resp['list']), 1)


    def test_post_sort_order(self):
        """ Test the regression where user profile posts were not shown
        in most recent first order. Also make sure the ordering is preserved
        across multiple conversations. """
        past_created = now() - timedelta(minutes=7*24*60)

        for idx in xrange(3):
            created = past_created + timedelta(minutes=idx)
            self._create_db_post(_created=created,
                                 content='I need a laptop bag' + str(idx),
                                 user_profile=self.up)

        conv = Conversation.objects()[:][0]
        conv.is_closed = True
        conv.save(is_safe=True)

        for idx in xrange(3):
            created = past_created + timedelta(minutes=3+idx)
            self._create_db_post(_created=created,
                                 content='I need a laptop bag' + str(idx),
                                 user_profile=self.up)

        data = dict(channel_id=str(self.inbound.id), user_name='joe')
        resp = self.client.get('/user_profile/json?%s' % urlencode(data))
        self.assertEqual(resp.status_code, 200)
        u_p_data = json.loads(resp.data)['list']
        last_post_date = datetime_to_timestamp_ms(now())
        for conv_data in u_p_data:
            for post in conv_data:
                self.assertTrue(post['created_at'] <= last_post_date)
                last_post_date = post['created_at']

    def test_no_entries_from_other_channels(self):
        '''
        A user_profile can have interactions across multiple channels.
        They may not all belong to the account, or be accessible to this user.
        We must allow for filtering conversations according to channels this user
        has access to, in this account.
        '''
        account2 = Account.objects.get_or_create(name='Test')
        account2.add_perm(self.user)
        self.sc2 = TwitterServiceChannel.objects.create_by_user(self.user, account=account2, title='Service Channel 2')
        self.sc2.save()
        self.assertTrue(self.sc2.can_view(self.user))

        # Tweet from first
        self._create_tweet(user_profile=self.up, channels=[self.inbound], content="Content")

        # Tweet from second
        self._create_tweet(user_profile=self.up, channels=[self.sc2.inbound], content="Content")

        # Base case with full access
        self.assertEqual(Conversation.objects.count(), 2)
        acc1_convs = self.up.get_conversations(self.user)
        self.user.account = account2
        self.user.save()
        acc2_convs = self.up.get_conversations(self.user)
        self.assertEqual(len(acc1_convs), 1)
        self.assertEqual(len(acc2_convs), 1)
        self.assertTrue(acc1_convs[0].id != acc2_convs[0].id)

        # Restrict access
        self.sc2.del_perm(self.user)
        acc2_convs = self.up.get_conversations(self.user)
        self.assertEqual(len(self.up.get_conversations(self.user)), 0)


class UserProfileJsonOrder(ConversationJsonCase):
    """
    This tests order of posts in JSON from user profile.
    The tests are the same as in ConversationJsonCase with some minor differences.
    """

    url_template = '/user_profile/json?%s'
    expected_post_orders = {'test_reply_to_two_posts' : [3, 4, 2, 5, 1],
                            'test_reply_to_one_post' : [3, 5, 4, 2, 1]}

    def create_data(self, channel, post, customer):
        print 'user_name=', customer.user_name
        print dir(customer)
        return dict(channel_id=str(channel.id), user_name=customer.user_name)

    def get_posts(self, resp):
        # we need to get posts of the first conversation in the profile
        return resp['list'][0]
