import json
import unittest

from solariat_bottle.db.account import Account
from solariat_bottle.db.api_auth import ApplicationToken, AuthError
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.roles import ADMIN
from solariat_bottle.tests.base import RestCase


class APIHTTPSCase(RestCase):

    @unittest.skip("Removed HTTPS enforcement for now, need to follow up")
    def test_create_happy_flow_data(self):
        tschn1 = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        token = self.get_token()
        happy_flow_data = {
            'content': 'Test post',
            'channel': str(tschn1.id),
            'token': token
        }
        # First try a unsecure request over http, expect token to be broken
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 401)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 12)
        self.assertEqual(resp_data['error'],
                         "Unsecure request done over HTTP. Your token has automatically removed.")
        self.assertFalse(resp_data['ok'])

        # Now try subsequent HTTP call, should be denied
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 401)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 12)
        self.assertEqual(resp_data['error'], 'Auth token %s is expired' % token)
        self.assertFalse(resp_data['ok'])

        token = self.get_token()
        happy_flow_data['token'] = token
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])

    @unittest.skip("Removed HTTPS enforcement for now, need to follow up")
    def test_authorization_https(self):
        new_acc1 = Account.objects.create(name='TestAccount1')
        user_email = 'admin2@test_channels.com'
        user_pass = 'pass.com'
        admin = self._create_db_user(email=user_email, password=user_pass, roles=[ADMIN])
        new_acc1.add_perm(admin)
        self._create_app_key(admin)
        post_data = {'username': user_email,
                     'password': user_pass,
                     'api_key': self.app_key}
        # Check that before request, all data is valid
        admin.reload()
        self.assertTrue(admin.check_password(user_pass))
        self.assertTrue(ApplicationToken.objects.verify_application_key(self.app_key))
        # Now do an unsecure request
        resp = self.client.post("/api/v2.0/authenticate",
                                data=json.dumps(post_data),
                                content_type="application/json")
        self.assertEqual(resp.status_code, 401)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 12)
        self.assertEqual(resp_data['error'],
                         "Unsecure request done over HTTP. Your credentials have been invalidated.")
        # Check that password is not reset and key still valid
        admin.reload()
        self.assertTrue(admin.check_password(user_pass))
        try:
            ApplicationToken.objects.verify_application_key(self.app_key)
        except AuthError:
            self.fail("Should be still valid")



