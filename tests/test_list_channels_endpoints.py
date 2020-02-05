# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import json

from solariat.utils.iterfu import flatten

from ..db.channel.base    import Channel
from ..db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel as ETC

from .base import UICase


# TODO: add tests for /channels/json/


class TestListChannelsEndpointsBase(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()

        # create another generic channel (inbound by default)
        self.generic_channel = Channel.objects.create_by_user(self.user, title='generic channel')

        self.initial_count = Channel.objects.count()  # our generic channel + two Twitter channels created by BaseCase

        # create two service channels
        self.service_channel_1 = TwitterServiceChannel.objects.create_by_user(self.user, title='service channel 1')
        self.service_channel_2 = TwitterServiceChannel.objects.create_by_user(self.user, title='service channel 2')

        # touch their .inobund_channel and .outbound_channel properties to initialize the channels
        self.service_channel_1.inbound_channel
        self.service_channel_1.outbound_channel
        self.service_channel_2.inbound_channel
        self.service_channel_2.outbound_channel

        self.service_count  = TwitterServiceChannel.objects.count()
        self.inbound_count  = self.initial_count + self.service_count  # initial channels + each service channel has one inbound
        self.outbound_count = self.service_count                       # each service channel has one outbound
        self.total_count    = self.service_count + self.inbound_count + self.outbound_count

        self.assertEqual(Channel.objects.count(), self.total_count)


class TestListReplyChannelsCase(TestListChannelsEndpointsBase):

    def _fetch(self, url):
        resp = self.client.get(url, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'], data.get('error'))
        return data

    def test_reply_channels(self):
        """
        Test that when two Enterprise Twitter Channels are created
        /reply_channels/json returns two channels
        """
        data = self._fetch('/reply_channels/json')
        self.assertEqual(len(data['list']), 0)
        ETC.objects.create_by_user(
            self.user, title='ETC 1',
            account=self.account,
            access_token_key='dummy_key',
            access_token_secret='dummy_secret')
        ETC.objects.create_by_user(
            self.user, title='ETC 2',
            account=self.account,
            access_token_key='dummy_key',
            access_token_secret='dummy_secret')
        data = self._fetch('/reply_channels/json')
        self.assertEqual(len(data['list']), 2)


class TestListChannelsEndpointsCase(TestListChannelsEndpointsBase):

    def _fetch(self, url, **kw):
        resp = self.client.post(url, data=json.dumps(kw), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'], data.get('error'))
        return data

    def test_channels_by_type_all(self):
        data = self._fetch('/channels_by_type/json')  # passing no parameters implying type='all'
        self.assertEqual(len(data['list']), self.total_count)

        data = self._fetch('/channels_by_type/json', type=None)
        self.assertEqual(len(data['list']), self.total_count)

        data = self._fetch('/channels_by_type/json', type='all')
        self.assertEqual(len(data['list']), self.total_count)

        data = self._fetch('/channels_by_type/json', type=['inbound','outbound','service'])
        self.assertEqual(len(data['list']), self.total_count)

        data = self._fetch('/channels_by_type/json', serviced_only='Yes')
        self.assertEqual(len(data['list']), self.total_count - self.initial_count)

        data = self._fetch('/channels_by_type/json', type='all', serviced_only=1)
        self.assertEqual(len(data['list']), self.total_count - self.initial_count)

        data = self._fetch('/channels_by_type/json',
                           type=['inbound','outbound','service'], serviced_only=True)
        self.assertEqual(len(data['list']), self.total_count - self.initial_count)

    def test_channels_by_type_service(self):
        data = self._fetch('/channels_by_type/json', type='service')
        self.assertEqual(len(data['list']), self.service_count)

        data = self._fetch('/channels_by_type/json', type='service', serviced_only=True)
        self.assertEqual(len(data['list']), self.service_count)  # should have no effect

    def test_channels_by_type_inbound(self):
        data = self._fetch('/channels_by_type/json', type='inbound')
        self.assertEqual(len(data['list']), self.inbound_count)

        data = self._fetch('/channels_by_type/json', type='inbound', serviced_only='YES')
        self.assertEqual(len(data['list']), self.inbound_count - self.initial_count)

    def test_channels_by_type_outbound(self):
        data = self._fetch('/channels_by_type/json', type='outbound')
        self.assertEqual(len(data['list']), self.outbound_count)

        data = self._fetch('/channels_by_type/json', type='outbound', serviced_only='true')
        self.assertEqual(len(data['list']), self.outbound_count)  # we don't subscibe initial_count because
                                                                  # generic channels are inbound by default

    def test_channels_by_type_inbound_outbound(self):
        data = self._fetch('/channels_by_type/json', type=['inbound','outbound'])
        self.assertEqual(len(data['list']), self.inbound_count + self.outbound_count)

        data = self._fetch('/channels_by_type/json', type=['inbound','outbound'], serviced_only='1')
        self.assertEqual(len(data['list']), self.inbound_count + self.outbound_count - self.initial_count)

    def test_channels_by_type_inbound_service(self):
        data = self._fetch('/channels_by_type/json', type=['inbound','service'])
        self.assertEqual(len(data['list']), self.inbound_count + self.service_count)

        data = self._fetch('/channels_by_type/json', type=['inbound','service'], serviced_only='TRUE')
        self.assertEqual(len(data['list']), self.inbound_count + self.service_count - self.initial_count)

    def test_channels_by_type_parent_names(self):
        # serviced outbound, no parent names
        data = self._fetch(
            '/channels_by_type/json',
            type          = 'outbound',
            serviced_only = True,
        )
        expected_titles = set(ch.title    for ch in Channel.objects() if not ch.is_inbound and not ch.is_service)
        received_titles = set(ch['title'] for ch in data['list'])

        self.assertEqual(received_titles, expected_titles)

        # serviced inbound, parent names
        data = self._fetch(
            '/channels_by_type/json',
            type          = 'inbound',
            serviced_only = True,
            parent_names  = True
        )
        expected_titles = set(ch.title    for ch in TwitterServiceChannel.objects())
        received_titles = set(ch['title'] for ch in data['list'])

        self.assertEqual(received_titles, expected_titles)

        # all serviced, parent names
        data = self._fetch(
            '/channels_by_type/json',
            type          = 'all',
            serviced_only = True,
            parent_names  = True
        )
        expected_titles = set(ch.title    for ch in TwitterServiceChannel.objects())
        received_titles = set(ch['title'] for ch in data['list'])

        self.assertEqual(received_titles, expected_titles)

        # all channels, parent names (i.e. unserviced channels keep their original title)
        data = self._fetch(
            '/channels_by_type/json',
            type          = 'all',
            serviced_only = False,
            parent_names  = True
        )
        serviced_ids    = set(flatten((ch.inbound, ch.outbound) for ch in TwitterServiceChannel.objects()))
        expected_titles = set(ch.title    for ch in Channel.objects() if ch.id not in serviced_ids)
        received_titles = set(ch['title'] for ch in data['list'])

        self.assertEqual(received_titles, expected_titles)

