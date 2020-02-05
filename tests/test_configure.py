#!/usr/bin/env python2.7

import unittest
import random
import json

from solariat_bottle.configurable_apps import APP_NPS, APP_GSA, APP_GSE, CONFIGURABLE_APPS

from solariat_bottle.settings import AppException, LOGGER

from solariat_bottle.db.roles           import ADMIN, AGENT, STAFF
from solariat_bottle.db.account         import Account, AccountEvent
from solariat_bottle.db.channel.base    import Channel
from solariat_bottle.db.channel.twitter import (
    TwitterServiceChannel, TwitterTestDispatchChannel, EnterpriseTwitterChannel)

from solariat_bottle.views.configure import CHANNEL_TYPE_MAP, CHANNEL_TYPES_LIST, CHANNEL_TYPES_LIST_ADMINS
from solariat_bottle.views.account   import _delete_account

from .base import UICase, SA_TYPES, fake_status_id, MainCase, BaseCase

from solariat_bottle.tests.social.twitter_helpers import \
    gen_twitter_user, get_user_profile, FakeTwitterAPI
from solariat_bottle.tasks import twitter


class ConfigureTestCase(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.account.selected_app = APP_GSA
        self.account.save()
        self.login()

    def test_channel_types(self):
        # Initial user is only admin, should have access only to that list
        resp = self.client.get('/configure/channel_types/json')
        data = json.loads(resp.data)
        for channel_type in CHANNEL_TYPES_LIST_ADMINS:
            self.assertTrue(channel_type in data['list'])
        # Add staff role, check again
        self.user.user_roles.append(STAFF)
        self.user.save()
        resp = self.client.get('/configure/channel_types/json')
        data = json.loads(resp.data)
        for channel_type in CHANNEL_TYPES_LIST:
            self.assertTrue(channel_type in data['list'])
        # Remove admin roles, leave only agent role, check list is empty
        self.user.user_roles = [AGENT]
        self.user.save()
        resp = self.client.get('/configure/channel_types/json')
        data = json.loads(resp.data)
        self.assertEqual(data['list'], [])

    @unittest.skip('Endpoint is obsolete')
    def test_event_types(self):
        from solariat_bottle.scripts.data_load.generate_journey_data import create_event_types
        create_event_types(self.user)

        resp = self.client.get('/configure/twitter/event_types')
        data = json.loads(resp.data)
        self.assertTrue(len(data['list']) >= 1)
        print data['list']

        resp = self.client.get('/configure/facebook/event_types')
        data = json.loads(resp.data)
        self.assertTrue(len(data['list']) >= 1)
        print data['list']

        resp = self.client.get('/configure/nps/event_types')
        data = json.loads(resp.data)
        self.assertTrue(len(data['list']) >= 1)
        print data['list']

        resp = self.client.get('/configure/chat/event_types')
        data = json.loads(resp.data)
        self.assertTrue(len(data['list']) >= 1)
        print data['list']

        resp = self.client.get('/configure/email/event_types')
        data = json.loads(resp.data)
        self.assertTrue(len(data['list']) >= 1)
        print data['list']

        resp = self.client.get('/configure/web/event_types')
        data = json.loads(resp.data)
        self.assertTrue(len(data['list']) >= 1)
        print data['list']

    def test_create_channel(self):

        channel_type = random.choice(CHANNEL_TYPE_MAP.keys())
        channel_title = 'test channel'
        data = {'type': channel_type, 'title': channel_title}

        resp = self.client.post('/configure/channels/json',
                                data=json.dumps(data),
                                content_type='application/json')
        data = json.loads(resp.data)

        channel_class = CHANNEL_TYPE_MAP[channel_type]
        channel = channel_class.objects.find_one_by_user(self.user, id=data['id'])
        self.assertEqual(channel.title, channel_title)

    def test_update_channel(self):

        moderated_relevance_threshold = round(random.random(), 3)
        moderated_intention_threshold = round(random.random(), 3)

        data = {'channel_id': str(self.channel.id),
                'moderated_relevance_threshold': moderated_relevance_threshold,
                'moderated_intention_threshold': moderated_intention_threshold}

        resp = self.client.post('/configure/channel_update/json',
                                data=json.dumps(data),
                                content_type='application/json')
        # there are should be two event in AccountEvent collection: login event and "channel edit" event
        self.assertEqual(AccountEvent.objects().count(), 2)
        data = json.loads(resp.data)
        self.channel.reload()
        self.assertEqual(
            self.channel.moderated_relevance_threshold,
            moderated_relevance_threshold)
        self.assertEqual(
            self.channel.moderated_intention_threshold,
            moderated_intention_threshold)

    @unittest.skip("queue_endpoint_attached is always True only for GSE accounts")
    def test_create_queue_attached_service_channel(self):

        def create_service_channel(attached_to_queue):
            channel_type = 'service'
            channel_title = 'test channel'
            data = {'type': channel_type, 'title': channel_title, 'queue_endpoint_attached': attached_to_queue,
                    'history_time_period': 100}
            resp = self.client.post('/configure/channels/json',
                                    data=json.dumps(data),
                                    content_type='application/json')
            data = json.loads(resp.data)
            print "GOT DATA " + str(data)
            channel = TwitterServiceChannel.objects.find_one_by_user(self.user, id=data['id'])
            self.assertEqual(channel.title, channel_title)
            self.assertEqual(channel.queue_endpoint_attached, attached_to_queue)

        create_service_channel(True)
        create_service_channel(False)

    @unittest.skip("queue_endpoint_attached is always True only for GSE accounts")
    def test_update_queue_attached_service_channel(self):

        channel_type = 'service'
        channel_title = 'test channel'
        post_data = {'type': channel_type, 'title': channel_title, 'queue_endpoint_attached': True}
        resp = self.client.post('/configure/channels/json',
                                data=json.dumps(post_data),
                                content_type='application/json')
        data = json.loads(resp.data)
        channel = TwitterServiceChannel.objects.find_one_by_user(self.user, id=data['id'])

        post_data = {'channel_id': str(data['id']),
                     'queue_endpoint_attached': False}

        self.client.post('/configure/channel_update/json',
                         data=json.dumps(post_data),
                         content_type='application/json')
        channel.reload()
        self.assertEqual(channel.queue_endpoint_attached, False)

        post_data['queue_endpoint_attached'] = True
        self.client.post('/configure/channel_update/json',
                         data=json.dumps(post_data),
                         content_type='application/json')
        channel.reload()
        self.assertEqual(channel.queue_endpoint_attached, True)

    def test_queue_endpoint_attached(self):
        # special_accounts = {'GSE', 'Skunkworks'}
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='SC')
        account = self.user.account
        # for account_type in Account.ACCOUNT_TYPES:
        #     account.update(account_type=account_type)
        #     channel.reload()
        #     self.assertEqual(channel.queue_endpoint_attached, account_type in special_accounts)

        message_queue_apps = [APP_GSA, APP_GSE, APP_NPS]
        for account_app in CONFIGURABLE_APPS:
            account.update(selected_app=account_app)
            channel.reload()
            self.assertEqual(channel.queue_endpoint_attached, account_app in message_queue_apps)

    def test_update_history_time_period(self):

        channel_type = 'service'
        channel_title = 'test channel'
        post_data = {'type': channel_type, 'title': channel_title, 'history_time_period': 10}
        resp = self.client.post('/configure/channels/json',
                                data=json.dumps(post_data),
                                content_type='application/json')
        data = json.loads(resp.data)
        channel = TwitterServiceChannel.objects.find_one_by_user(self.user, id=data['id'])

        post_data = {'channel_id': str(data['id']),
                     'history_time_period': 11}

        self.client.post('/configure/channel_update/json',
                         data=json.dumps(post_data),
                         content_type='application/json')
        channel.reload()
        self.assertEqual(channel.history_time_period, 11)

        post_data['history_time_period'] = 13
        self.client.post('/configure/channel_update/json',
                         data=json.dumps(post_data),
                         content_type='application/json')
        channel.reload()
        self.assertEqual(channel.history_time_period, 13)

    def test_friends_followers_settings(self):

        channel_type = 'service'
        channel_title = 'test channel'
        post_data = {'type': channel_type, 'title': channel_title,
                     'auto_refresh_followers': 11, 'auto_refresh_friends': 12}
        resp = self.client.post('/configure/channels/json',
                                data=json.dumps(post_data),
                                content_type='application/json')
        data = json.loads(resp.data)
        channel = TwitterServiceChannel.objects.find_one_by_user(self.user, id=data['id'])

        post_data = {'channel_id': str(data['id']),
                     'auto_refresh_followers': 15,
                     'auto_refresh_friends': 17}

        self.client.post('/configure/channel_update/json',
                         data=json.dumps(post_data),
                         content_type='application/json')
        channel.reload()
        self.assertEqual(channel.auto_refresh_followers, 15)
        self.assertEqual(channel.auto_refresh_friends, 17)


class ChannelConfigureTestCase(MainCase):

    def make_dispatch_channel(self, title, twitter_handle, user=None):
        if user is None:
            user = self.user
        dispatch_channel = TwitterTestDispatchChannel.objects.create_by_user(user, title=title,
                                                                             review_outbound=False,
                                                                             account=self.account)
        dispatch_channel.add_perm(user)
        dispatch_channel.twitter_handle = twitter_handle
        dispatch_channel.save()
        dispatch_channel.on_active()
        dispatch_channel.account.add_perm(user)
        return dispatch_channel

    def make_service_channel(self, title, twitter_handles, user=None):
        if user == None:
            user = self.user

        sc = TwitterServiceChannel.objects.create_by_user(
            user,
            account=self.account,
            title=title)
        sc.outbound_channel.usernames = twitter_handles
        sc.outbound_channel.save()
        return sc

    def setUp(self):
        ''' Just the bare essentials - an account
        '''
        MainCase.setUp(self)
        #self.account = Account.objects.get_or_create(name='Test')
        self.account = self.user.account
        #self.account.add_user(self.user)

    def command_delete_channel(self, channel):
        from ..commands.configure import DeleteChannel

        DeleteChannel(channels=[channel]).update_state(self.user)

    def test_account_removal(self):
        # Test that we only archive account, since we still keep references
        # towards it from channels posts etc
        self.user.accounts = []
        account = Account.objects.create_by_user(self.user, name="TEST2")
        Account.objects.create_by_user(self.user, name="TEST3")
        sc = EnterpriseTwitterChannel.objects.create_by_user(self.user, account=account,
                                                             title="Chan2")
        self.assertEqual(len(Account.objects.find_by_user(self.user)), 2)
        res, _ = _delete_account(self.user, account)
        self.assertFalse(res)
        self.command_delete_channel(sc)
        res, _ = _delete_account(self.user, account)
        self.assertTrue(res)
        self.assertEqual(len(Account.objects.find_by_user(self.user)), 1)
        sc.reload()
        self.assertEqual(sc.status, 'Archived')
        for channel in EnterpriseTwitterChannel.objects(status='Active'):
            self.assertTrue(str(channel.id) != str(sc.id))
        self.assertEqual(sc.account.id, account.id)


    def test_service_channel_configuration(self):
        # Set up a service channel
        sc = self.make_service_channel("SC1", ['brand1'])
        self.assertEqual(sc.get_outbound_channel(self.user), None)

    def test_dispatch_only(self):
        dispatch_channel = self.make_dispatch_channel("D1", "B1")
        self.assertEqual(dispatch_channel.get_outbound_channel(self.user), dispatch_channel)

    def test_base_case_for_sc(self):
        sc = self.make_service_channel("SC1", ['brand1'])
        dispatch_channel = self.make_dispatch_channel("D1", "brand1")
        self.assertEqual(sc.get_outbound_channel(self.user), dispatch_channel)
        self.assertEqual(sc.inbound_channel.get_outbound_channel(self.user), dispatch_channel)
        self.assertEqual(sc.outbound_channel.get_outbound_channel(self.user), dispatch_channel)
        sc2 = self.make_service_channel("SC2", ['@brand1'])
        self.assertEqual(sc2.get_outbound_channel(self.user), dispatch_channel)
        self.assertEqual(sc2.inbound_channel.get_outbound_channel(self.user), dispatch_channel)
        self.assertEqual(sc2.outbound_channel.get_outbound_channel(self.user), dispatch_channel)

    def test_configuration_error(self):
        ''' More than once candidate is a configuration error'''
        sc = self.make_service_channel("SC1", ['brand1'])
        self.make_dispatch_channel("D1", "brand1")
        self.make_dispatch_channel("D2", "brand1")

        try:
            sc.get_outbound_channel(self.user)
            self.assertFalse(True, "This should not be possible.")
        except AppException:
            pass

    def test_multi_agent_scenario(self):
        sc = self.make_service_channel("SC1", ['brand1', 'brand2'])
        dispatch_channel_1 = self.make_dispatch_channel("D1", "brand1")
        dispatch_channel_2 = self.make_dispatch_channel("D2", "brand2")

        #try:
        #    ch = sc.get_outbound_channel(self.user)
        #    self.assertFalse(True, "This should not be possible: %s" % (ch.title if ch else "NONE"))
        #except AppException, exc:
        #    pass

        # Now, remove access from one of the channels, and confirm it works
        dispatch_channel_2.del_perm(self.user)
        LOGGER.debug("SC IS %s", sc)
        self.assertEqual(sc.get_outbound_channel(self.user), dispatch_channel_1)

    def test_multi_agent_defaults(self):
        '''
        2 options, but disambiguated by configuration
        '''
        sc = self.make_service_channel("SC1", ['brand1', 'brand2'])
        dispatch_channel_1 = self.make_dispatch_channel("D1", "brand1")
        dispatch_channel_2 = self.make_dispatch_channel("D2", "brand2")
        dispatch_channel_2 # to disable pyflakes warning
        self.user.outbound_channels['Twitter'] = str(dispatch_channel_1.id)
        self.user.save()
        self.assertEqual(sc.get_outbound_channel(self.user), dispatch_channel_1)

    def test_incompatible_dispatch_channel(self):
        '''
        The configured channel will not work for this service channel
        '''
        sc = self.make_service_channel("SC1", ['brand'])
        dispatch_channel_1 = self.make_dispatch_channel("D1", "brand1")
        self.user.outbound_channels['Twitter'] = str(dispatch_channel_1.id)
        self.user.save()
        self.assertEqual(sc.get_outbound_channel(self.user), None)

    def test_case_sensitivity(self):
        '''
        Matching should ignore case. This bit us with HS.
        '''
        sc = self.make_service_channel("SC1", ['brand'])
        dispatch_channel_1 = self.make_dispatch_channel("D1", "Brand")
        self.assertEqual(sc.get_outbound_channel(self.user), dispatch_channel_1)

    def test_channel_fit_dominates(self):
        '''
        We want the service channel binding to over-ride user configuration.
        '''
        sc = self.make_service_channel("SC1", ['brand2'])
        dispatch_channel_1 = self.make_dispatch_channel("D1", "brand1")
        dispatch_channel_2 = self.make_dispatch_channel("D2", "brand2")
        self.user.outbound_channels['Twitter'] = str(dispatch_channel_1.id)
        self.user.save()
        self.assertEqual(sc.get_outbound_channel(self.user), dispatch_channel_2)

    def test_channel_fit_is_hard_constraint(self):
        '''
        We want to error out if we do not have a way to disambiguate
        '''
        sc = self.make_service_channel("SC1", ['brand1', 'brand2'])
        dispatch_channel_1 = self.make_dispatch_channel("D1", "brand1")
        dispatch_channel_2 = self.make_dispatch_channel("D2", "brand2")
        dispatch_channel_3 = self.make_dispatch_channel("D3", "brand3")
        dispatch_channel_1, dispatch_channel_2 # to disable pyflakes warning
        self.user.outbound_channels['Twitter'] = str(dispatch_channel_3.id)
        self.user.save()
        try:
            sc.get_outbound_channel(self.user)
            assert False, "Should never get here. Expect it to error out"
        except AppException:
            pass


class ConfigureDefaultOutboundChannelsCase(UICase):

    def setUp(self):
        UICase.setUp(self)

        self.account = Account.objects.get_or_create(name='TEST_ACCOUNT')
        self.user = self._create_db_user(email="nobody@nowhere.com", account="solariat_test", roles=[ADMIN])
        self.user.account = self.account
        self.user.save()
        self.login()

        self._create_static_events(self.user)
        self.channel = TwitterServiceChannel.objects.create_by_user(
            self.user, title='TestChannel',
            account=self.account,
            type='twitter', intention_types=SA_TYPES)
        self.account.add_perm(self.user)

        self.agents = {}
        self._create_db_post(
            'I need a foo',
            channel=self.channel,
            twitter={"id": "1111111111"})

        for agent_name in ['mary', 'joe', 'jill']:
            user = self._create_db_user(account=self.account,
                                        email='%s@solariat.com' % agent_name,
                                        password='12345',
                                        roles=[AGENT])
            user.signature = '^'+agent_name
            user.save()
            self._create_db_post(
                'Reply from ^%s' % agent_name,
                channel=self.channel.outbound_channel,
                user_profile={'screen_name': 'agent_screen_name'},
                twitter={"id": fake_status_id(), "in_reply_to_status_id": "1111111111"})
            self.agents[agent_name] = user

        existing_channels = list(Channel.objects.find_by_user(self.user))

        from ..db.channel.twitter import EnterpriseTwitterChannel, KeywordTrackingChannel, UserTrackingChannel
        from ..db.channel.facebook import EnterpriseFacebookChannel
        self.channels = [
            UserTrackingChannel.objects.create_by_user(self.user, title="UserTracking", type="twitter", account=self.user.account),
            KeywordTrackingChannel.objects.create_by_user(self.user, title="KeywordTracking", type="twitter", account=self.user.account),
            EnterpriseTwitterChannel.objects.create_by_user(self.user, title='ETwitterC_1', type='twitter', account=self.user.account),
            EnterpriseFacebookChannel.objects.create_by_user(self.user, title='EFacebookC_2', type='facebook', account=self.user.account),
            EnterpriseTwitterChannel.objects.create_by_user(self.user, title='ETwitterC_3', type='twitter', account=self.user.account)
        ]
        self.channels.extend(existing_channels)
        self.dispatchable_channels = [ch for ch in self.channels if ch.is_dispatchable and not ch.is_inbound]

        from ..db.channel.base import PLATFORM_MAP
        self.platforms = PLATFORM_MAP.keys()  #['Twitter', 'Facebook', 'LinkedIn']

    def test_agent_query(self):
        'Fetch agents for display in search, by channel'
        self.channel.reload()

        for ka in self.agents:
            self.channel.account.del_perm(self.agents[ka])

        self.login()
        url = '/configure/agents/json?channel_id=%s' % str(self.channel.id)
        self.channel.reload()
        resp = self.client.get(url, content_type='application/json')

        print resp.data
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['ok'], True)
        # Since none for the agents have view permissions on the account,
        # then the list will be empty
        self.assertEqual(set([a.display_agent for a in self.agents.values()]),
                         set(a['display_name'] for a in data['list']))
        for a in data['list']:
            self.assertFalse(a['can_view'])
        # Now set the account on all agents, and expect to get back the full list
        for ka in self.agents:
            self.channel.account.add_perm(self.agents[ka])
        self.channel.reload()
        resp = self.client.get(url, content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['ok'], True)
        self.assertEqual(set(a['display_name'] for a in data['list']),
                         set([a.display_agent for a in self.agents.values()]))
        for a in data['list']:
            self.assertTrue(a['can_view'])

        # Log in as another user.
        self.user = self.agents['mary']
        self.channel.del_perm(self.user)
        self.account.del_perm(self.user)
        self.login()
        resp = self.client.get(url,
                               content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        #No access to channel.
        self.assertFalse(data['ok'])

        # Now add access to the channel, but not a admin
        # Re-add account permissions so we can add channel aswell
        self.account.add_perm(self.user)
        self.channel.add_perm(self.user)
        self.user.user_roles = [AGENT]
        self.assertFalse(self.account.can_edit(self.user))
        resp = self.client.get(url, content_type='application/json')
        data = json.loads(resp.data)
        print data
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['list']), 1)

        # Test with bogus channel id
        resp = self.client.get('/configure/agents/json?channel_id=FOO',
                               content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

        # Test with no channel id
        payload = {}
        resp = self.client.get('/configure/agents/json',
                               data=json.dumps(payload),
                               content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

    def test_get_outbound_channels_for_user(self):
        self.user.outbound_channels['Twitter'] = str(self.dispatchable_channels[0].id)
        self.user.save()
        resp = self.client.get('/configure/outbound_channels/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)['data']

        for platform in self.platforms:
            self.assertEqual(len(data.get(platform, [])),
                             len(filter(lambda x:x.platform==platform, self.dispatchable_channels)),
                             "%s fetched != %s dispatchable for platform %s" % (
                                 len(data.get(platform, [])),
                                 len(filter(lambda x:x.platform==platform, self.dispatchable_channels)),
                                 platform
                                                                               ))

        channel_ids = [str(ch.id) for ch in self.channels]
        for platform in self.platforms:
            for ch in data.get(platform, []):
                if ch.get('selected', False):
                    self.assertEquals(self.user.outbound_channels[platform], ch['id'])
                else:
                    self.assertIn(ch['id'], channel_ids)

    def test_get_outbound_channels_for_account(self):
        account = self.user.account
        channel1_id = str(self.dispatchable_channels[0].id)
        account.outbound_channels['Twitter'] = channel1_id
        account.save()

        resp = self.client.get('/configure/outbound_channels/json?account=%s' % account.name)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)['data']

        for platform in self.platforms:
            self.assertEqual(len(data.get(platform, [])), len(filter(lambda x:x.platform==platform, self.dispatchable_channels)))

        channel_ids = [str(ch.id) for ch in self.channels]
        for platform in self.platforms:
            for ch in data.get(platform, []):
                if ch.get('selected', False):
                    self.assertEquals(account.outbound_channels[platform], ch['id'])
                else:
                    self.assertIn(ch['id'], channel_ids)


    def test_setup_outbound_channels_for_user(self):
        #Try to set Facebook channel as Twitter
        channel2_id = str(filter(lambda x:x.platform=='Facebook', self.dispatchable_channels)[0].id)
        payload = {'oc': {'Twitter': channel2_id}}

        resp = self.client.post('/configure/outbound_channels/json',
            data=json.dumps(payload),
            content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

        #Try to set non-dispatchable channel as the outbound channel
        nd_channel = filter(lambda x:not x.is_dispatchable, self.channels)[0]
        nd_channel_platform = nd_channel.platform
        payload = {'oc': {nd_channel_platform: str(nd_channel.id)}}

        resp = self.client.post('/configure/outbound_channels/json',
            data=json.dumps(payload),
            content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

        #Normal Case
        d_channel = filter(lambda x: x.is_dispatchable, self.channels)[0]
        d_channel_platform = d_channel.platform
        payload = {'oc': {d_channel_platform: str(d_channel.id)}}
        resp = self.client.post('/configure/outbound_channels/json',
            data=json.dumps(payload),
            content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        self.user.reload()
        self.assertEquals(self.user.outbound_channels[d_channel_platform], str(d_channel.id))

    def test_setup_outbound_channels_for_account(self):
        account = self.user.account

        #Try to set Facebook channel as Twitter
        channel2_id = str(filter(lambda x:x.platform=='Facebook', self.dispatchable_channels)[0].id)

        payload = {'oc': {'Twitter': channel2_id},
                   'account': account.name}

        resp = self.client.post('/configure/outbound_channels/json',
            data=json.dumps(payload),
            content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

        #Try to set non-dispatchable channel as the outbound channel
        nd_channel = filter(lambda x:not x.is_dispatchable, self.channels)[0]
        nd_channel_platform = nd_channel.platform
        payload = {'oc': {nd_channel_platform: str(nd_channel.id)},
                   'account': account.name}

        resp = self.client.post('/configure/outbound_channels/json',
            data=json.dumps(payload),
            content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

        #Normal Case
        d_channel = filter(lambda x: x.is_dispatchable, self.channels)[0]
        d_channel_platform = d_channel.platform
        payload = {'oc': {d_channel_platform: str(d_channel.id)},
                   'account_id': str(account.id)}

        resp = self.client.post('/configure/outbound_channels/json',
            data=json.dumps(payload),
            content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        account.reload()
        self.assertEqual(account.outbound_channels[d_channel_platform], str(d_channel.id))


if __name__ == '__main__':
    unittest.main()
