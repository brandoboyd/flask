# coding=utf-8
import json
from mock import patch, MagicMock
import unittest

from solariat_bottle.tests.base import MainCase, UICase, UICaseSimple
from solariat.tests.base import LoggerInterceptor
from solariat_bottle.db.roles import STAFF, ADMIN

from solariat_bottle.settings import AppException

from solariat_bottle.db.account          import Account
from solariat_bottle.db.user             import User
from solariat_bottle.db.tracking         import PostFilterEntry
from solariat_bottle.db.conversation     import Conversation
from solariat_bottle.db.channel.facebook import EnterpriseFacebookChannel, FacebookServiceChannel
from solariat_bottle.db.channel.twitter  import (
    KeywordTrackingChannel, UserTrackingChannel, TwitterServiceChannel,
    TwitterTestDispatchChannel, get_sync_usernames_list)

from solariat_bottle.scripts.datasift_sync2 import update_interim_channels
from solariat_bottle.commands.configure     import ActivateChannel, SuspendChannel, DeleteChannel
from solariat_bottle.utils.post             import get_service_channel


class TwitterServiceChannelCase(MainCase):

    def setUp(self):
        super(MainCase, self).setUp()
        self.title = 'Service'
        self.sc = TwitterServiceChannel.objects.create_by_user(self.user, title=self.title)


    def _make_agent(self, n, account):
        u = User(agent_id=n+100, email="agent+%s@test.test" % (n+100))
        u.save()
        account.add_user(u)
        return u

    def test_setup(self):
        self.assertEqual(self.sc.inbound_channel.title, "%s Inbound" % self.title)
        self.assertEqual(self.sc.outbound_channel.title, "%s Outbound" % self.title)
        self.assertTrue(isinstance(self.sc.inbound_channel, KeywordTrackingChannel))
        self.assertTrue(isinstance(self.sc.outbound_channel, UserTrackingChannel))
        self.assertEqual(TwitterServiceChannel.objects.find_by_user(self.user).count(), 1)
        self.assertEqual(KeywordTrackingChannel.objects.find_by_user(self.user).count(), 1)
        self.assertEqual(UserTrackingChannel.objects.find_by_user(self.user).count(), 1)

    def test_get_service_channel(self):
        self.sc.add_username('test_handle')
        outb = TwitterTestDispatchChannel.objects.create_by_user(self.user, title="TestDispatch")
        outb.twitter_handle = 'test_handle'
        outb.save()
        sc = get_service_channel(outb)
        self.assertEqual(sc.id, self.sc.id)

        # case-insensitive lookup
        self.sc.add_username('@test_HANDLE2')
        outb.twitter_handle = 'TEST_handle2'
        outb.save()
        sc = get_service_channel(outb)
        self.assertEqual(sc.id, self.sc.id)

    def test_keywords(self):
        sc = self.sc
        self.assertEqual(sc.keywords, [])
        sc.add_keyword('#tEst')
        self.assertEqual(sc.keywords, ['#tEst'])
        self.assertEqual(sc.keywords, sc.inbound_channel.keywords)
        sc.del_keyword('#tEst')
        self.assertEqual(sc.keywords, [])
        self.assertEqual(sc.keywords, sc.inbound_channel.keywords)

    def test_users(self):
        sc = self.sc
        self.assertEqual(sc.usernames, [])
        sc.add_username('@test')
        self.assertEqual(set(sc.usernames), set(['@test', 'test']))
        self.assertEqual(sc.usernames, get_sync_usernames_list(sc.outbound_channel.usernames))
        sc.del_username('@test')
        self.assertEqual(sc.usernames, [])
        self.assertEqual(sc.usernames, get_sync_usernames_list(sc.outbound_channel.usernames))

    def test_service_channel_activation(self):
        channel = self.sc
        # service channel activates on creation
        channel.on_active()
        channel.reload()
        self.assertEqual(channel.status, "Interim")

        # this call simulates actions of datasift_sync2.py script
        update_interim_channels()
        channel.reload()
        self.assertEqual(channel.status, "Active")

    def test_status_control(self):
        sc = self.sc
        status = 'Active'
        ActivateChannel(channels=[sc]).update_state(self.user)
        # this call simulates actions of datasift_sync2.py script
        update_interim_channels()
        sc.reload()
        self.assertEqual(sc.status, status)
        self.assertEqual(sc.inbound_channel.status, status)
        self.assertEqual(sc.outbound_channel.status, status)

        status = 'Suspended'
        SuspendChannel(channels=[sc]).update_state(self.user)
        sc.reload()
        self.assertEqual(sc.status, status)
        self.assertEqual(sc.inbound_channel.status, status)
        self.assertEqual(sc.outbound_channel.status, status)

    def test_tracking(self):
        '''Test usernames tracked as keywords on service channel activation'''
        sc = self.sc
        sc.add_keyword('#test')
        sc.add_username('@test1')
        sc.add_username('test2')  # without '@'
        ActivateChannel(channels=[sc]).update_state(self.user)
        # this call simulates actions of datasift_sync2.py script
        update_interim_channels()
        sc.reload()

        # Check Filter Mapping
        post_filter_entries = [
            pf.entry
            for pf in PostFilterEntry.objects(channels=sc.inbound_channel)]
        self.assertEqual(set(post_filter_entries), {'#test', '@test1', '@test2'})  # @test2 with '@'

        post_filter_entries = [
            pf.entry
            for pf in PostFilterEntry.objects(channels=sc.outbound_channel)]
        self.assertEqual(set(post_filter_entries), {'test1', '@test1', 'test2', '@test2'})
        self.assertEqual(sc.keywords, ['#test'])
        self.assertEqual(set(sc.usernames), {'@test1', 'test1', '@test2', 'test2'})

        # user added when channel was Active
        sc.add_username('@test3')

        post_filter_entries = [
            pf.entry
            for pf in PostFilterEntry.objects(channels=sc.inbound_channel)]
        self.assertEqual(set(post_filter_entries), {'#test', '@test1', '@test2', '@test3'})

        sc.del_username('@test3')
        post_filter_entries = [
            pf.entry
            for pf in PostFilterEntry.objects(channels=sc.inbound_channel)]
        self.assertEqual(set(post_filter_entries), {'#test', '@test1', '@test2'})

        SuspendChannel(channels=[sc]).update_state(self.user)
        sc.reload()

        post_filter_entries = [
            pf.entry
            for pf in PostFilterEntry.objects(channels=sc.inbound_channel)]
        self.assertFalse(post_filter_entries)
        self.assertEqual(sc.keywords, ['#test'])
        self.assertEqual(set(sc.usernames), {'@test1', 'test1', '@test2', 'test2'})
        post_filter_entries = [
            pf.entry
            for pf in PostFilterEntry.objects(channels=sc.outbound_channel)]
        self.assertFalse(post_filter_entries)

    def test_deletion(self):
        sc = self.sc
        ActivateChannel(channels=[sc]).update_state(self.user)
        sc.reload()
        status = 'Archived'
        DeleteChannel(channels=[sc]).update_state(self.user)
        sc.reload()
        self.assertEqual(sc.status, status)
        self.assertEqual(sc.inbound_channel.status, status)
        self.assertEqual(sc.outbound_channel.status, status)

        self.assertEqual(TwitterServiceChannel.objects.find_by_user(self.user).count(), 0)
        self.assertEqual(KeywordTrackingChannel.objects.find_by_user(self.user).count(), 0)
        self.assertEqual(UserTrackingChannel.objects.find_by_user(self.user).count(), 0)

        #verify there is no post filter entries after deletion
        post_filter_entries = [
            pf.entry
            for pf in PostFilterEntry.objects(channels=[sc.inbound_channel, sc.outbound_channel])]
        self.assertFalse(post_filter_entries)

    def test_account_propagated(self):
        sc = self.sc
        account1 = Account.objects.get_or_create(name='TestAcct1')
        account2 = Account.objects.get_or_create(name='TestAcct2')
        self.user.accounts.append(account1.id)
        self.user.accounts.append(account2.id)
        sc.account = account1
        sc.save_by_user(self.user)
        sc.reload()
        self.assertEqual(sc.inbound_channel.account, account1)
        self.assertEqual(sc.outbound_channel.account, account1)

        sc.account = account2
        sc.save()
        sc.reload()
        self.assertEqual(sc.inbound_channel.account, account2)
        self.assertEqual(sc.outbound_channel.account, account2)

    def test_agents_moved_to_new_account_with_channel(self):

        title = 'Service'
        account1 = Account.objects.create(name="TEST1")
        account2 = Account.objects.create(name="TEST2")

        sc = TwitterServiceChannel.objects.create_by_user(self.user, account=account1, title=title)
        agents = [self._make_agent(agent, account1) for agent in [0, 1, 2]]
        sc.agents = agents
        sc.save()

        sc.account = account2
        sc.save()
        account1.reload()
        account2.reload()
        sc.reload()
        for agent in sc.agents:
            self.assertEqual(agent.account, account2)
            self.assertFalse(account1.can_view(agent))
            self.assertTrue(account2.can_view(agent))

    def test_multiple_common_service_channels(self):
        '''Case of multiple accouns, multiple service channels, same brand'''

        # Set the account, and set service handle
        account1 = Account.objects.create(name="TEST1")
        account1.add_perm(self.user)
        self.sc.account = account1
        self.sc.save()
        self.sc.add_username('@solariat_brand')

        account2 = Account.objects.create(name="TEST2")
        account2.add_perm(self.user)
        sc2 = TwitterServiceChannel.objects.create_by_user(self.user, account=account2, title='Service 2')
        self.sc.add_username('@solariat_brand')
        sc2.save()


        inbound_channels = [self.sc.inbound_channel, sc2.inbound_channel]
        post = self._create_db_post(content='@solariat_brand Can u please help me?',
                                    channels=inbound_channels)

        self.assertEqual(set(post.channels), set(c.id for c in inbound_channels))
        self.assertEqual(Conversation.objects.count(), 2)

        service_channels = [c.service_channel for c in Conversation.objects()]
        self.assertEqual({self.sc, sc2}, set(service_channels))

    def test_facebook_efc_configuration(self):
        efc = EnterpriseFacebookChannel.objects.create_by_user(self.user, title='OUT_FC1',
                                                               account=self.user.account)
        efc.on_active()
        fsc1 = FacebookServiceChannel.objects.create_by_user(self.user, title='INB1',
                                                             account=self.user.account)
        outbound_channel = fsc1.get_outbound_channel(self.user)
        self.assertEqual(outbound_channel.id, efc.id)
        efc2 = EnterpriseFacebookChannel.objects.create_by_user(self.user, title='OUT_FC2',
                                                               account=self.user.account)
        efc2.on_active()
        self.assertRaises(AppException, fsc1.get_outbound_channel, self.user)
        self.user.outbound_channels['Facebook'] = str(efc2.id)
        self.user.save()
        outbound_channel = fsc1.get_outbound_channel(self.user)
        self.assertEqual(outbound_channel.id, efc2.id)

    def test_facebook_sc_configuration(self):
        efc = EnterpriseFacebookChannel.objects.create_by_user(self.user, title='OUT_FC',
                                                               account=self.user.account)
        fsc1 = FacebookServiceChannel.objects.create_by_user(self.user, title='INB1',
                                                             account=self.user.account)
        fsc2 = FacebookServiceChannel.objects.create_by_user(self.user, title='INB2',
                                                             account=self.user.account)
        # No facebook page ids, so no way to tell which is the best service channel
        self.assertIsNone(efc.get_service_channel())
        # Once we have a service channel tracking this page, that is returned
        efc.facebook_page_ids = ['page1']
        efc.save()
        fsc1.facebook_page_ids = ['page1', 'page2']
        fsc1.save()
        self.assertEqual(fsc1.id, efc.get_service_channel().id)
        # If we have multiple candidates based on page ids, return the one which has
        # the largest set intersection
        efc.facebook_page_ids = ['page1', 'page2']
        efc.save()
        fsc1.facebook_page_ids = ['page1', 'page3', 'page4']
        fsc1.save()
        fsc2.facebook_page_ids = ['page1', 'page3', 'page2']
        fsc2.save()
        # We no longer have an exact match
        self.assertIsNone(efc.get_service_channel())

#TODO: add get request testing features (define how to be with facebook auth)
class TestEnhancedFacebookServiceChannel(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()
        self.efc = EnterpriseFacebookChannel.objects.create_by_user(self.user, title='OUT_FC',
                                                               account=self.user.account)
        self.fsc = FacebookServiceChannel.objects.create_by_user(self.user, title='INB1',
                                                             account=self.user.account)
        self.group = {'id':'group_id', 'name':'group_name'}
        self.event = {'id':'event_id', 'name':'event_name'}
        self.page =  {'id':'page_id', 'name':'test_page', 'access_token':'fake_token'}

    def test_post_delete_events_groups(self):

        group_url = 'channels/%s/fb/groups' % self.fsc.id
        event_url = 'channels/%s/fb/events' % self.fsc.id

        #add group and event
        resp_group = self.client.post(group_url, data=json.dumps({'groups': self.group}), content_type='application/json')
        resp_event = self.client.post(event_url, data=json.dumps({'events': self.event}), content_type='application/json')
        self.assertEquals(resp_group.status_code, 200)
        self.assertEquals(resp_event.status_code, 200)
        data_group = json.loads(resp_group.data)
        data_event = json.loads(resp_event.data)
        self.assertTrue(data_group['ok'])
        self.assertTrue(data_event['ok'])
        self.efc.reload()
        self.fsc.reload()
        self.assertEqual(len(self.fsc.tracked_fb_group_ids), 1)
        self.assertEqual(len(self.fsc.tracked_fb_groups), 1)
        self.assertEqual(len(self.fsc.tracked_fb_event_ids), 1)
        self.assertEqual(len(self.fsc.tracked_fb_events), 1)

        #remove events and groups
        resp_group = self.client.delete(group_url, data=json.dumps({'groups': self.group}), content_type='application/json')
        resp_event = self.client.delete(event_url, data=json.dumps({'events': self.event}), content_type='application/json')
        self.assertEquals(resp_group.status_code, 200)
        self.assertEquals(resp_event.status_code, 200)
        data_group = json.loads(resp_group.data)
        data_event = json.loads(resp_event.data)
        self.assertTrue(data_group['ok'])
        self.assertTrue(data_event['ok'])
        self.efc.reload()
        self.fsc.reload()
        self.assertEqual(len(self.fsc.tracked_fb_group_ids), 0)
        self.assertEqual(len(self.fsc.tracked_fb_groups), 0)
        self.assertEqual(len(self.fsc.tracked_fb_event_ids), 0)
        self.assertEqual(len(self.fsc.tracked_fb_events), 0)

    @patch("solariat_bottle.db.channel.facebook.update_page_admins")
    @patch("solariat_bottle.db.channel.facebook.unsubscribe_realtime_updates")
    @patch("solariat_bottle.db.channel.facebook.subscribe_realtime_updates")
    def test_add_delete_page(self, add, remove, update):

        page_url = 'channels/%s/fb/pages' % self.fsc.id

        #add page
        resp_page = self.client.post(page_url, data=json.dumps({'pages': self.page}), content_type='application/json')
        self.assertEquals(resp_page.status_code, 200)

        data_page = json.loads(resp_page.data)
        self.assertTrue(data_page['ok'])
        self.efc.reload()
        self.fsc.reload()
        self.assertEqual(len(self.fsc.facebook_pages), 1)
        self.assertEqual(len(self.fsc.facebook_page_ids), 1)
        add.assert_called_once_with([self.page])
        update.assert_called_once_with(self.fsc, self.page)
        #remove events and groups
        resp_page = self.client.delete(page_url, data=json.dumps({'pages': self.page}), content_type='application/json')
        self.assertEquals(resp_page.status_code, 200)
        data_page = json.loads(resp_page.data)
        self.assertTrue(data_page['ok'])
        self.efc.reload()
        self.fsc.reload()
        self.assertEqual(len(self.fsc.facebook_pages), 0)
        self.assertEqual(len(self.fsc.facebook_page_ids), 0)
        remove.assert_called_once_with([self.page])


class ServiceChannelGeneralTest(MainCase):
    def test_auto_io_creation(self):

        from solariat_bottle.db.channel.base import Channel, ServiceChannel
        from solariat_bottle.db.channel.twitter import TwitterServiceChannel
        from solariat_bottle.db.channel.facebook import FacebookServiceChannel
        from solariat_bottle.db.channel.voc import VOCServiceChannel

        sc_types = [
            ServiceChannel,
            TwitterServiceChannel,
            FacebookServiceChannel,
            VOCServiceChannel]

        for SC in sc_types:
            ch = SC.objects.create(title=SC.__name__ + 'title')
            self.assertIsInstance(ch.inbound_channel, ch.InboundChannelClass)
            self.assertIsInstance(ch.outbound_channel, ch.OutboundChannelClass)
            # check the sub-channels not created twice
            ch.__dict__.pop('inbound_channel')
            ch.__dict__.pop('outbound_channel')
            ch.inbound_channel
            ch.outbound_channel
            self.assertEqual(Channel.objects(parent_channel=ch.id).count(), 2)


class TestDispatchChannelConfiguration(UICaseSimple):
    def setUp(self):
        super(TestDispatchChannelConfiguration, self).setUp()

        fac1 = EnterpriseFacebookChannel.objects.create_by_user(
            self.user, title='OUT_FC1',
            account=self.user.account)
        fac2 = EnterpriseFacebookChannel.objects.create_by_user(
            self.user, title='OUT_FC2',
            account=self.user.account)

        fsc1 = FacebookServiceChannel.objects.create_by_user(self.user, title='INB1',
                                                             account=self.user.account)
        fsc2 = FacebookServiceChannel.objects.create_by_user(self.user, title='INB2',
                                                             account=self.user.account)
        self.fac1, self.fac2, self.fsc1, self.fsc2 = fac1, fac2, fsc1, fsc2

    def test_cached_description_invalidated_on_dispatch_channel_change(self):
        fac1, fac2, fsc1, fsc2 = self.fac1, self.fac2, self.fsc1, self.fsc2
        fsc1.channel_description = {'pages': [], 'events': [], 'id': str(fsc1.id)}
        fsc2.channel_description = {'pages': [], 'events': [], 'id': str(fsc2.id)}

        # verify description is set
        for sc in [fsc1, fsc2]:
            self.assertEqual(sc.channel_description['id'], str(sc.id))

        # assign dispatch channel - description should be erased
        fsc1.dispatch_channel = fac1
        fsc1.save()
        fsc1.reload()
        self.assertFalse(fsc1.channel_description)
        # should not affect other service channel
        self.assertEqual(fsc2.channel_description['id'], str(fsc2.id))

    def test_multiple_facebook_sc_setup(self):
        fac1, fac2, fsc1, fsc2 = self.fac1, self.fac2, self.fsc1, self.fsc2
        for fa in [fac1, fac2]:
            self.assertIsNone(fa.get_service_channel())
            self.assertFalse(fa.get_attached_service_channels())

        for sc in [fsc1, fsc2]:
            for not_attached in [False, True]:
                self.assertListEqual(sorted([str(ch.id) for ch in
                                             sc.list_dispatch_candidates(self.user, only_not_attached=not_attached)]),
                                     sorted([str(fac1.id), str(fac2.id)]))

        # setup attachments
        # fsc1 <-> fac1
        # fsc2 <-> fac2
        fsc1.dispatch_channel = fac1
        fsc1.save()
        fsc2.dispatch_channel = fac2
        fsc2.save()

        self.assertEqual(fac1.get_service_channel(), fsc1)
        self.assertEqual(fac1.get_attached_service_channels(), [fsc1])
        self.assertEqual(fac2.get_service_channel(), fsc2)
        self.assertEqual(fac2.get_attached_service_channels(), [fsc2])

        self.assertEqual(fsc1.get_outbound_channel(self.user), fac1)
        self.assertEqual(fsc2.get_outbound_channel(self.user), fac2)

        # all attached
        for sc in [fsc1, fsc2]:
            self.assertEqual(sc.list_dispatch_candidates(self.user, only_not_attached=True), [])

        # change attachments
        # fsc1 <-> fac2  (was fac1)
        fsc1.dispatch_channel = fac2
        fsc1.save()

        self.assertEqual(fac1.get_service_channel(), None)
        self.assertEqual(fac1.get_attached_service_channels(), [])
        with LoggerInterceptor() as logs:
            self.assertIn(fac2.get_service_channel(), {fsc1, fsc2})
            warnings = [log.message for log in logs if log.levelname == 'WARNING']
            self.assertTrue(warnings)
            self.assertTrue(warnings[0].startswith("We have multiple candidates for service channel matching for enterprise channel"))
        self.assertEqual(fac2.get_attached_service_channels(), [fsc1, fsc2])

        self.assertEqual(fsc1.get_outbound_channel(self.user), fac2)
        self.assertEqual(fsc2.get_outbound_channel(self.user), fac2)

        # fac1 is not attached
        for sc in [fsc1, fsc2]:
            self.assertEqual(sc.list_dispatch_candidates(self.user, only_not_attached=True), [fac1])

    def post_update_channel(self, channel, update_params):
        channel_update_url = '/configure/channel_update/json'
        update_params.update(channel_id=str(channel.id))
        result = self._post(channel_update_url, update_params)
        return result

    def assign_dispatch_channel(self, service_channel, dispatch_channel):
        return self.post_update_channel(
            service_channel,
            {'dispatch_channel': dispatch_channel and str(dispatch_channel.id)})

    def test_get_account_channels_endpoint(self):
        url = "/account_channels/%(channel_id)s"
        staff = self._create_db_user('staff@test.tst', account=self.account, roles=[STAFF])
        admin = self._create_db_user('admin@test.tst', account=self.account, roles=[ADMIN])
        fac1, fac2, fsc1, fsc2 = self.fac1, self.fac2, self.fsc1, self.fsc2

        def assert_channels(user, channels, service_channel=fsc1, only_not_attached=False):
            self.login(user=user)
            path = url % {'channel_id': service_channel.id}
            path += '?only_not_attached=%s' % only_not_attached
            result = self._get(path, {})
            self.assertEqual(len(result['data']), len(channels))
            returned_ids = [item['key'] for item in result['data']]
            expected_ids = [str(ch.id) for ch in channels]
            self.assertEqual(set(returned_ids), set(expected_ids))
            response = sorted(result['data'], key=lambda item: item['key'])
            return [{'key': item['key'], 'title': item['title']} for item in response]

        # any user should see all dispatch candidates
        for user in [staff, admin]:
            assert_channels(user, [fac1, fac2])
        result = self.assign_dispatch_channel(fsc1, fac1)
        self.assertEqual(result['item']['dispatch_channel'], str(fac1.id))

        # after assignment all users still should see all dispatch candidates
        for user in [staff, admin]:
            assert_channels(user, [fac1, fac2])
        # test that changing the assigned dispatch channel by admin user is possible
        result = self.assign_dispatch_channel(fsc1, fac2)
        self.assertEqual(result['item']['dispatch_channel'], str(fac2.id))
        result = self.assign_dispatch_channel(fsc1, fac1)
        self.assertEqual(result['item']['dispatch_channel'], str(fac1.id))

        # now change dispatch channel by staff
        self.login(user=staff)
        result = self.assign_dispatch_channel(fsc1, fac2)
        self.assertEqual(result['item']['dispatch_channel'], str(fac2.id))

        # check not attached channels
        for sc in [fsc1, fsc2]:
            assert_channels(admin, [fac1], service_channel=sc, only_not_attached=True)

        # assign the remaining channel
        result = self.assign_dispatch_channel(fsc2, fac1)
        self.assertEqual(result['item']['dispatch_channel'], str(fac1.id))

        # check the final assignments by staff user
        response = assert_channels(staff, [fac1, fac2])
        expected_data = [
            {'key': str(fac1.id),
             'title': "%s (not authenticated) attached to %s" % (fac1.title, fsc2.title)},
            {'key': str(fac2.id),
             'title': "%s (not authenticated) attached to %s" % (fac2.title, fsc1.title)}
        ]
        self.assertEqual(response, expected_data)

        fac1.update(facebook_screen_name=u'Test Screen Nâme 1',
                    facebook_access_token='test')
        fac2.update(facebook_screen_name=u'Test Screen Nâme 2',
                    facebook_access_token='test')

        response = assert_channels(staff, [fac1, fac2])
        expected_data = [
            {'key': str(fac1.id),
             'title': "%s (%s) attached to %s" % (fac1.title, fac1.facebook_screen_name, fsc2.title)},
            {'key': str(fac2.id),
             'title': "%s (%s) attached to %s" % (fac2.title, fac2.facebook_screen_name, fsc1.title)}
        ]
        self.assertEqual(response, expected_data)

        # now assign fac1 to both service channels
        with patch('solariat_bottle.db.channel.facebook.FacebookUserMixin.facebook_me', MagicMock(return_value={'id': '123456', 'name': 'F L'})):
            result = self.assign_dispatch_channel(fsc1, fac1)
            self.assertEqual(result['item']['dispatch_channel'], str(fac1.id))
            result = self.assign_dispatch_channel(fsc2, fac1)
            self.assertEqual(result['item']['dispatch_channel'], str(fac1.id))

        response = assert_channels(staff, [fac1, fac2])
        expected_data = [
            {'key': str(fac1.id),
             'title': "%s (%s) attached to %s" % (
             fac1.title, fac1.facebook_screen_name, "2 channels")},
            {'key': str(fac2.id),
             'title': "%s (%s)" % (
             fac2.title, fac2.facebook_screen_name)}
        ]
        self.assertEqual(response, expected_data)

    def test_get_outbound_channel_endpoint(self):
        url = "/get_outbound_channel/%(channel_id)s"
        self.login(user=self.user)
        result = self._get(url % {'channel_id': self.fsc1.id}, {})
        self.assertIsNone(result['channel'])

        self.assign_dispatch_channel(self.fsc1, self.fac1)
        result = self._get(url % {'channel_id': self.fsc1.id}, {})
        self.assertEqual(result['channel']['id'], str(self.fac1.id))
