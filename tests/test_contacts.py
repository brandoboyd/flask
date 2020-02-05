import unittest
import json

from .base import MainCase, UICase
from ..db.tracking import (
    PostFilterEntry, PostFilterStream,)
from ..db.channel.base import (Channel, ContactChannel)
from ..db.account import Account
from ..db.user_profiles.user_profile import UserProfile

@unittest.skip("ContactChannel is deprecated. Related code should be removed")
class ContactChannelCase(MainCase):

    def setUp(self):
        MainCase.setUp(self)
        self.stream = PostFilterStream.get()
        
    def test_unique(self):
        account = self.account
        ch1 = account.get_contact_channel(platform="Twitter")
        ch2 = account.get_contact_channel(platform="Twitter")
        self.assertEqual(ch1.id, ch2.id)
        ch3 = account.get_contact_channel(platform="Facebook")
        ch4 = account.get_contact_channel(platform="Facebook")
        self.assertEqual(ch3.id, ch4.id)
        self.assertEqual(ContactChannel.objects(account=account).count(), 2)

    def test_methods(self):
        #Add two users
        account = self.account
        contacts = account.get_contact_channel(platform="Twitter")
        users = ['screen_name1', UserProfile.objects.upsert('Twitter', dict(screen_name='screen_name2'))]
        for user in users:
            contacts.add_username(user)

        usernames = contacts.usernames
        self.assertTrue('screen_name1' in usernames, 'screen_name1 not in %s' % usernames)
        self.assertTrue('screen_name2' in usernames, 'screen_name2 not in %s' % usernames)
        self.assertEqual(len(usernames), 2)
        #test users tracked
        self.assertTrue(PostFilterEntry.objects.count() == 2)
        #test Contacts channel stored in user profiles
        u_p1 = UserProfile.objects.get_by_platform('Twitter', 'screen_name1')
        self.assertTrue(contacts.id in u_p1.contact_channels,
                        "Contacts:" + str(u_p1.contact_channels))
        u_p2 = UserProfile.objects.get_by_platform('Twitter', 'screen_name1')
        self.assertTrue(contacts.id in u_p2.contact_channels)

        #Remove users
        for u in users:
            contacts.del_username(u)
        #test no tracking
        self.assertTrue(PostFilterEntry.objects.count() == 0)
        #test Contacts channel removed from user profiles
        self.assertFalse(UserProfile.objects.get_by_platform('Twitter', 'screen_name1').contact_channels)
        self.assertFalse(UserProfile.objects.get_by_platform('Twitter', 'screen_name2').contact_channels)

    @unittest.skip('Disabled ContactChannel functionality, refer to db.conversation.sync_contacts()')
    def test_contacts_added_when_post_created(self):
        user_profile = UserProfile.objects.upsert("Twitter", dict(screen_name="screen_name1"))
        from solariat_bottle.db.tracking import PostFilterStream

        stream = PostFilterStream.get()

        #setup accounts
        account = Account.objects.get_or_create(name="Test Account")
        account2 = Account.objects.get_or_create(name="Test Account2")
        self.user.account = account
        self.user.save()
        account2.add_user(self.user)

        from ..db.channel.twitter import TwitterServiceChannel
        service_channel1 = TwitterServiceChannel.objects.create_by_user(self.user,
                                                                 account=account,
                                                                 title='Service')
        service_channel2 = TwitterServiceChannel.objects.create_by_user(self.user,
                                                                 account=account2,
                                                                 title='Service')

        self.assertFalse(user_profile.screen_name in account.get_contact_channel("Twitter").usernames)
        self.assertFalse(user_profile.screen_name in account2.get_contact_channel("Twitter").usernames)

        channels = [service_channel1, service_channel2]
        #create inbound post from user_profile
        self._create_db_post(
            channels=channels,
            content="Test Post",
            user_profile=user_profile,
            url='https://twitter.com/fake/status/fake.status')

        #test user_profile is in contact channels for both accounts
        self.assertTrue(user_profile.screen_name in account.get_contact_channel("Twitter").usernames)
        self.assertTrue(user_profile.screen_name in account2.get_contact_channel("Twitter").usernames)


class ContactsUITest(UICase):

    def setUp(self):
        UICase.setUp(self)

        self.user.account = Account.objects.get_or_create(name="TEST_ACCOUNT")
        self.user.save()
        self.account = self.user.account
        self.channel.account = self.account
        self.channel.save()

        self.login()

        # Create User Tracking Channels
        self.ut1 = self._create_user_tracking_channel('user_tracker_1', ['u1', 'u2'])
        self.etc1 = self._create_enterprise_twitter_channel('Channel1', 'twitter_handle1')

        self.profile1 = UserProfile.objects.upsert('Twitter', dict(screen_name='screen_name1'))
        self.profile2 = UserProfile.objects.upsert('Twitter', dict(screen_name='screen_name2'))

        self.matchable = self._create_db_matchable(
            'A new laptop is here!', intention_topics=['laptop'])

        post1 = self._create_db_post('I need a laptop',
            user_profile=self.profile1)

        post2 = self._create_db_post('I need a new laptop',
            user_profile=self.profile2)

        self.response1 = Response.objects.upsert_from_post(post1)
        self.response2 = Response.objects.upsert_from_post(post2)

    def _create_channel(self, _type, title):
        res = self._post('/configure/channels/json', dict(type=_type,
            title=title,
            platform='Twitter'))
        channel = Channel.objects.get(res['id'])

        # All such channels should be inactive initially
        self.assertEqual(channel.status, 'Suspended')
        return channel

    def _create_user_tracking_channel(self, title, usernames):
        c = self._create_channel('usertracking', title)
        c.status = 'Active'
        c.save()
        for username in usernames:
            self._post('/tracking/usernames/json',
                dict(channel_id=str(c.id), username=username))
        return c

    def _create_enterprise_twitter_channel(self, title, handle):
        c = self._create_channel('enterprisetwitter', title)
        self._post('/configure/channel_update/json',
            dict(channel_id=str(c.id), twitter_handle=handle))
        c.reload()
        return c

    def _post_response(self, response):
        resp = self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(response.id), str(response.matchable.id), str(self.response.post.id)))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        response.reload()
        self.assertEqual(response.status, 'posted')

    def _retweet_response(self, response):
        resp = self.client.post('/commands/retweet_response',
            data='{"response":"%s"}' % str(response.id))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        response.reload()
        self.assertEqual(response.status, 'retweeted')

    @unittest.skip('Disabled ContactChannel functionality, refer to Channel.sync_contacts()')
    def test_track_on_post(self):
        #user profile should not be tracked
        self.assertEqual(PostFilterEntry.objects(entry=self.profile1.screen_name).count(), 0)
        self._post_response(self.response1)
        self.assertTrue(self.profile1.screen_name in self.account.get_contact_channel('Twitter').usernames)
        self.assertEqual(PostFilterEntry.objects(entry=self.profile1.screen_name).count(), 1)

    @unittest.skip('Disabled ContactChannel functionality, refer to Channel.sync_contacts()')
    def test_track_on_retweeted(self):
        self.assertEqual(PostFilterEntry.objects(entry=self.profile2.screen_name).count(), 0)
        self._retweet_response(self.response2)
        self.assertTrue(self.profile2.screen_name in self.account.get_contact_channel('Twitter').usernames)
        self.assertEqual(PostFilterEntry.objects(entry=self.profile2.screen_name).count(), 1)

    @unittest.skip('Disabled ContactChannel functionality, refer to Channel.sync_contacts()')
    def test_track_on_user_added_to_user_tracking_channel(self):
        #no posts created for user tracking channel so there are no contacts
        self.assertFalse('screen_name3' in self.account.get_contact_channel('Twitter').usernames)
        self.assertEqual(PostFilterEntry.objects(entry='screen_name3').count(), 0)
        self.ut1.add_username('screen_name3')
        self.assertTrue('screen_name3' in self.account.get_contact_channel('Twitter').usernames)
        self.assertEqual(PostFilterEntry.objects(entry='screen_name3').count(), 1)
