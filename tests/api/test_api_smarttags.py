import json

from solariat_bottle.settings import get_var
from solariat_bottle.db.account import Account
from solariat_bottle.api.exceptions import ResourceDoesNotExist
from solariat_bottle.db.auth import default_access_groups
from solariat_bottle.db.channel.base import SmartTagChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.roles import ADMIN
from solariat_bottle.tests.base import RestCase


class APIChannelsCase(RestCase):

    # used in test_delete
    def _create_obj(self):
        # we use one of the existing channels
        self.obj_id = self.channel.id

    def test_channel_account_configurations(self):
        # Setup the test environment, two users, two accounts, each with a service channel
        # and a smart tag channel
        new_acc1 = Account.objects.create(name='TestAccount1')
        new_acc2 = Account.objects.create(name='TestAccount2')
        user_1_mail = 'admin1@test_channels.com'
        user_password = 'password'
        user_2_mail = 'admin2@test_channels.com'
        admin_user_1 = self._create_db_user(email=user_1_mail, password=user_password, roles=[ADMIN])
        admin_user_2 = self._create_db_user(email=user_2_mail, password=user_password, roles=[ADMIN])
        new_acc1.add_perm(admin_user_1)
        new_acc2.add_perm(admin_user_2)
        tschn1 = TwitterServiceChannel.objects.create_by_user(admin_user_1, title='TSC')
        acl = admin_user_1.groups + default_access_groups(admin_user_1)
        st1 = SmartTagChannel.objects.create_by_user(admin_user_1,
                                                     parent_channel=tschn1.id,
                                                     title='tag',
                                                     status='Active',
                                                     acl=acl)
        tschn2 = TwitterServiceChannel.objects.create_by_user(admin_user_2, title='TSC')
        acl = admin_user_2.groups + default_access_groups(admin_user_2)
        st2 = SmartTagChannel.objects.create_by_user(admin_user_2,
                                                     parent_channel=tschn2.id,
                                                     title='tag',
                                                     status='Active',
                                                     acl=acl)
        st3 = SmartTagChannel.objects.create_by_user(admin_user_2,
                                                     parent_channel=tschn2.id,
                                                     title='tag2',
                                                     status='Active',
                                                     acl=acl)
        # Setup done

        # Now using first user, just do a simple non-filtered request to the channels endpoints
        token = self.get_token(user_1_mail, user_password)
        post_data = dict(token=token)
        data = json.dumps(post_data)
        resp = self.client.get('/api/v2.0/smarttags',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        channels_list = data['list']
        # Only service channel should be returned
        self.assertEqual(len(channels_list), 1)
        self.assertEqual(channels_list[0]['id'], str(st1.id))

        # Filter based on a given channel name
        post_data['title'] = 'tag'
        data = json.dumps(post_data)
        resp = self.client.get('/api/v2.0/smarttags',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        channels_list = data['list']
        self.assertEqual(len(channels_list), 1)
        self.assertEqual(channels_list[0]['id'], str(st1.id))

        # Same thing for second user, initial call should return only the service channels
        token = self.get_token(user_2_mail, user_password)
        post_data = dict(token=token)
        data = json.dumps(post_data)
        resp = self.client.get('/api/v2.0/smarttags',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        channels_list = data['list']
        self.assertEqual(len(channels_list), 2)
        channels_ids = [str(item['id']) for item in channels_list]
        self.assertEqual(set(channels_ids), set([str(item.id) for item in (st2, st3)]))

        # Give permissions to the second user to the service channel
        # At this point we'd expect he still gets only the initial service channel
        # because we automatically filter by the current account
        st2.add_perm(admin_user_1)
        token = self.get_token(user_1_mail, user_password)
        post_data = dict(token=token)
        data = json.dumps(post_data)
        resp = self.client.get('/api/v2.0/smarttags',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        channels_list = resp_data['list']
        self.assertEqual(len(channels_list), 1)
        self.assertEqual(channels_list[0]['id'], str(st1.id))

        # Specifically ask for channels from the other account, get a list
        # of the service channel which we just shared
        post_data = dict(token=token,
                         account=str(new_acc2.id))
        data = json.dumps(post_data)
        resp = self.client.get('/api/v2.0/smarttags',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        channels_list = resp_data['list']
        self.assertEqual(len(channels_list), 1)
        self.assertEqual(channels_list[0]['id'], str(st2.id))

    def test_channel_specific_filter(self):
        new_acc1 = Account.objects.create(name='TestAccount1')
        user_mail = 'admin1@test_channels.com'
        user_password = 'password'
        admin_user = self._create_db_user(email=user_mail, password=user_password, roles=[ADMIN])
        new_acc1.add_perm(admin_user)
        tschn1 = TwitterServiceChannel.objects.create_by_user(admin_user, title='TSC1')
        tschn2 = TwitterServiceChannel.objects.create_by_user(admin_user, title='TSC2')
        st1 = SmartTagChannel.objects.create_by_user(admin_user,
                                                     parent_channel=tschn1.id,
                                                     title='tag',
                                                     status='Active')
        tschn2 = TwitterServiceChannel.objects.create_by_user(admin_user, title='TSC')
        st2 = SmartTagChannel.objects.create_by_user(admin_user,
                                                     parent_channel=tschn2.id,
                                                     title='tag2',
                                                     status='Active')
        st3 = SmartTagChannel.objects.create_by_user(admin_user,
                                                     parent_channel=tschn2.id,
                                                     title='tag3',
                                                     status='Active')
        token = self.get_token(user_mail, user_password)
        post_data = dict(token=token,
                         channel=str(tschn1.id))
        data = json.dumps(post_data)
        resp = self.client.get('/api/v2.0/smarttags',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        channels_list = data['list']
        # Only service channel should be returned
        self.assertEqual(len(channels_list), 1)
        self.assertEqual(channels_list[0]['id'], str(st1.id))
        post_data['channel'] = str(tschn2.id)
        data = json.dumps(post_data)
        resp = self.client.get('/api/v2.0/smarttags',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        print resp.data
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        channels_list = data['list']
        # Only service channel should be returned
        self.assertEqual(len(channels_list), 2)

    def test_resource_uri(self):
        new_acc1 = Account.objects.create(name='TestAccount1')
        user_email = 'admin2@test_channels.com'
        user_pass = 'pass.com'
        admin = self._create_db_user(email=user_email, password=user_pass, roles=[ADMIN])
        new_acc1.add_perm(admin)
        tsc = TwitterServiceChannel.objects.create_by_user(admin, title='TSC')
        SmartTagChannel.objects.create_by_user(admin,
                                               parent_channel=tsc.inbound_channel.id,
                                               title='tag',
                                               status='Active')
        token = self.get_token(user_email, user_pass)
        post_data = dict(token=token)
        data = json.dumps(post_data)
        resp = self.client.get('/api/v2.0/smarttags',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        channels_list = resp_data['list']
        # Only smart tag should be returned
        self.assertEqual(len(channels_list), 1)
        for channel_data in channels_list:
            test_uri = channel_data['uri'].replace(get_var('HOST_DOMAIN'), '')
            uri_resp = self.client.get(test_uri,
                                       data=data,
                                       content_type='application/json',
                                       base_url='https://localhost')
            self.assertEqual(uri_resp.status_code, 200)
            uri_data = json.loads(uri_resp.data)
            uri_channel_data = uri_data['item']
            self.assertDictEqual(channel_data, uri_channel_data)

    def test_invalid_id(self):
        token = self.get_token()
        data = json.dumps({'token': token})
        resp = self.client.get('/api/v2.0/smarttags/invalid_id',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, ResourceDoesNotExist.http_code)

    def test_smart_tag_channel_resource(self):
        token = self.get_token()
        data = json.dumps({'token': token})
        tsc = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        st = SmartTagChannel.objects.create_by_user(self.user,
                                                    parent_channel=tsc.inbound_channel.id,
                                                    title='tag',
                                                    status='Active')
        resp = self.client.get('/api/v2.0/smarttags/' + str(st.id),
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        item = resp_data['item']
        for key in ('id', 'uri', 'title', 'status', 'description', 'usernames',
                    'keywords', 'skipwords', 'watchwords', 'influence', 'intentions'):
            self.assertTrue(key in item, '%s expected in response' % key)
