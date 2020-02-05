import json

from solariat_bottle.db.api_channel_command import ChannelAPICommand
from solariat_bottle.db.channel.base import SmartTagChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.tests.base import RestCase


class APIChannelCommandsCase(RestCase):

    def test_create_happy_flow_data(self):
        tschn = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC', status='Suspended')
        st = SmartTagChannel.objects.create_by_user(self.user,
                                                    parent_channel=tschn.inbound_channel.id,
                                                    title='tag2',
                                                    status='Suspended')
        st2 = SmartTagChannel.objects.create_by_user(self.user,
                                                     parent_channel=self.channel.id,
                                                     title='tag2',
                                                     status='Suspended')
        token = self.get_token()
        happy_flow_data = {
            'token': token,
            'channel_id': str(tschn.id)
        }
        self.assertEqual(ChannelAPICommand.objects.count(), 0)
        # In case of service channel, we expect them to be switched to Interim state
        resp = self.client.post('/api/v2.0/activate_channel',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        tschn.reload()
        self.assertTrue(tschn.status == resp_data['item']['status'] == 'Interim')
        self.assertEqual(ChannelAPICommand.objects.count(), 1)
        created_command = ChannelAPICommand.objects.find_one()
        self.assertEqual(created_command.user.id, self.user.id)
        self.assertEqual(created_command.channel_id, str(tschn.id))
        self.assertEqual(created_command.command, 'activate')
        # In case of smart tags, we expect them to be switched directly in Active state
        happy_flow_data['channel_id'] = str(st.id)
        resp = self.client.post('/api/v2.0/activate_channel',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        st.reload()
        self.assertTrue(st.status == resp_data['item']['status'] == 'Active')
        self.assertEqual(ChannelAPICommand.objects.count(), 2)

        # In case of deactivation, we expect it directly as suspended
        happy_flow_data['channel_id'] = str(tschn.id)
        resp = self.client.post('/api/v2.0/suspend_channel',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ChannelAPICommand.objects.count(), 3)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        tschn.reload()
        self.assertTrue(tschn.status == resp_data['item']['status'] == 'Suspended')
        # In case of smart tags, we expect them to be switched directly in suspended state
        happy_flow_data['channel_id'] = str(st.id)
        resp = self.client.post('/api/v2.0/suspend_channel',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ChannelAPICommand.objects.count(), 4)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        st.reload()
        self.assertTrue(st.status == resp_data['item']['status'] == 'Suspended')

        # Deletion should be handled as 'soft' delete and only archived
        happy_flow_data['channel_id'] = str(tschn.id)
        resp = self.client.post('/api/v2.0/delete_channel',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ChannelAPICommand.objects.count(), 5)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        self.assertTrue(resp_data['item']['status'] == 'Archived')
        # We already archived the parent ServiceChannel, smart tag should also be removed
        happy_flow_data['channel_id'] = str(st.id)
        resp = self.client.post('/api/v2.0/delete_channel',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(ChannelAPICommand.objects.count(), 5)
        self.assertEqual(resp.status_code, 404)
        # On a non related smart tag channel things should work as expected
        happy_flow_data['channel_id'] = str(st2.id)
        resp = self.client.post('/api/v2.0/delete_channel',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(ChannelAPICommand.objects.count(), 6)
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        self.assertTrue(resp_data['item']['status'] == 'Archived')

    def test_invalid_methods(self):
        tschn = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        token = self.get_token()
        happy_flow_data = {
            'token': token
        }
        resp = self.client.get('/api/v2.0/delete_channel',
                               data=json.dumps(happy_flow_data),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 405)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 135)
        resp = self.client.put('/api/v2.0/delete_channel',
                               data=json.dumps(happy_flow_data),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 405)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 135)
        resp = self.client.delete('/api/v2.0/delete_channel',
                                  data=json.dumps(happy_flow_data),
                                  content_type='application/json',
                                  base_url='https://localhost')
        self.assertEqual(resp.status_code, 405)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 135)