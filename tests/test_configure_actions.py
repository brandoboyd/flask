""" Test active/suspend Channels for configure screen """

import json
from .base import UICase
from ..db.channel.base import Channel

class ConfigureScreenCase(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()
        self.channels = [
            Channel.objects.create_by_user(self.user, title='channel1'),
            Channel.objects.create_by_user(self.user, title='channel2')
        ]

    def test_active_channels(self):

        data = {'channels': [ str(channel.id) for channel in self.channels ]}
        resp = self.client.post(
            '/commands/activate_channel',
            data=json.dumps(data), content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])

        for channel in self.channels:
            channel.reload()
            self.assertEqual(channel.status, 'Active')

    def test_suspend_channels(self):

        data = {'channels': [ str(channel.id) for channel in self.channels ]}
        resp = self.client.post(
            '/commands/suspend_channel',
            data=json.dumps(data), content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])

        for channel in self.channels:
            channel.reload()
            self.assertEqual(channel.status, 'Suspended')

    def test_delete_channels(self):

        data = {'channels': [ str(channel.id) for channel in Channel.objects() ]}
        resp = self.client.post(
            '/commands/delete_channel',
            data=json.dumps(data), content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])

        for channel in self.channels:
            channel.reload()
            self.assertEqual(channel.status, 'Archived')

        self.assertEqual(Channel.objects.find_by_user(self.user).count(), 0)
