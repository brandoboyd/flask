from copy import copy
import json

from mock import patch
from requests.exceptions import ConnectionError

from solariat_bottle.settings          import LOGGER
from solariat_bottle.db.roles          import STAFF, AGENT
from solariat_bottle.db.user           import User
from solariat_bottle.integration.angel import views, restapi
from solariat_bottle.settings          import get_var

from .base import BaseCase, RestCase


ANGEL_REST_PATH = '/api/v1.2/angel/'
ANGEL_ENDPOINT  = '/angel'
TOKEN_STR = 'token=7f000001-0b-1461e02dc0d-6334fc3b-a56%407f000001-04-13c1e8de5d7-9a635eec-0f4%408727c665%401400662842381%4013%406e99c7d62f81ce19551a4d27138733eb'  # NOQA
CXB_ID = '7f000001-04-13c1e8de5d7-9a635eec-0f4'
CXB_ID_STR = 'cxb_id=' + CXB_ID


class AngelAPITest(RestCase):
    def setUp(self):
        RestCase.setUp(self)
        self.api_token = get_var('ANGEL_API_TOKEN')

        # superuser is needed for Angel user creation
        self.su = self._create_db_user(email="superuser@all.com", roles=[STAFF])
        self.su.is_superuser = True
        self.su.save()

    def do_post(self, path, **kw):
        "Emulate POST request"

        path = restapi.get_angel_url(path)

        kw['api_token'] = self.api_token
        data = json.dumps(kw)

        LOGGER.debug("Performing POST to %s with %s" % (path, data))
        response = self.client.post(path, data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        return json.loads(response.data)
        
    
    def test_user_creation(self):
        # user is created successfuly
        data = {
            'account_name': 'Account-Name',
            'email': 'email@test.com',
            'cxb_id': '1234-abc',
        }
        resp = self.do_post('users', **data)
        self.assertTrue(resp['ok'])
        u = resp['user']
        self.assertEqual(u['email'], data['email'])
        self.assertEqual(u['external_id'], 'cxb_id:' + data['cxb_id'])
        a = resp['account']
        LOGGER.debug(a)
        self.assertEqual(a['name'], data['account_name'])
        self.assertEqual(a['account_type'], 'Angel')

        # errors if some parameters are not specified
        for k in data:
            bad_data = copy(data)
            bad_data.pop(k)
            resp = self.do_post('users', **bad_data)
            self.assertFalse(resp['ok'])

        # a user with duplicate email is not created
        different_data = {
            'account_name': 'Account-Name-2',
            'email': 'email2@test.com',
            'cxb_id': '1234-abc2',
        }

        bad_data = copy(different_data)
        bad_data['email'] = data['email']
        resp = self.do_post('users', **bad_data)
        self.assertFalse(resp['ok'])

        # a user with duplicated external id is not created
        bad_data = copy(different_data)
        bad_data['account_name'] = data['account_name']
        resp = self.do_post('users', **bad_data)
        self.assertFalse(resp['ok'])

        # a user with duplicated account name is not created
        bad_data = copy(different_data)
        bad_data['cxb_id'] = data['cxb_id']
        resp = self.do_post('users', **bad_data)
        print resp
        self.assertFalse(resp['ok'])

        # account is created with different data
        # resp = self.do_post('users', **different_data)
        # print resp
        # self.assertTrue(resp['ok'])

    def test_invalid_account_name(self):
        """
        Test that an invalid account name will not result in invalid user being created.
        """
        user_count = User.objects.count()
        data = {
            'account_name': ' ',  # empty account name is not allowed
            'email': 'email@test.com',
            'cxb_id': '1234-abc',
        }
        resp = self.do_post('users', **data)
        # Response should fail because we don't have a valid account name
        self.assertFalse(resp['ok'])
        self.assertEqual(User.objects.count(), user_count)

        data['account_name'] = 'TestAngel'
        resp = self.do_post('users', **data)
        # Response should fail because we don't have a valid account name
        self.assertTrue(resp['ok'])
        self.assertEqual(User.objects.count(), user_count + 1)

    def test_orphan_user_handled(self):
        user = self._create_db_user(email='email@test.com', password='password', roles=[AGENT])
        self.assertEqual(user.accounts, [])

        data = {
            'account_name': 'TestAngel',
            'email': 'email@test.com',
            'cxb_id': '1234-abc',
        }
        resp = self.do_post('users', **data)
        # Response should pass even with duplicate email since that's an orphan user
        self.assertTrue(resp['ok'])

        # Now test that if we do another test with the same user, but that does have an account
        # then we should expect that to fail
        data = {
            'account_name': 'TestAngel22',
            'email': 'email@test.com',
            'cxb_id': '1234-abc',
        }
        resp = self.do_post('users', **data)
        # Response should pass even with duplicate email since that's an orphan user
        self.assertFalse(resp['ok'])


class AngelEndpointTest(BaseCase):
    def setUp(self):
        BaseCase.setUp(self)
        from solariat_bottle.app import app
        self.client = app.test_client()

    def _create_angel_user(self):
        self._create_db_user(
            email='foo@solariat.com',
            password='12345',
            external_id='cxb_id:' + CXB_ID,
            roles=[AGENT]
        )

    def _call_angel_endpoint(self):
        return self.client.get(
            '{}?{}&{}'.format(ANGEL_ENDPOINT, TOKEN_STR, CXB_ID_STR),
            follow_redirects=True)

    def test_endpoint_request(self):

        # nothing is specified
        response = self.client.get('{}'.format(ANGEL_ENDPOINT), follow_redirects=True)
        self.assertIn('Please specify token and cxb_id', response.data)

        # token is specified cxb_id not
        response = self.client.get(
            '{}?{}'.format(ANGEL_ENDPOINT, TOKEN_STR), follow_redirects=True)
        self.assertIn('Please specify cxb_id', response.data)

        # cxb_id is specified token is not
        response = self.client.get(
            '{}?{}'.format(ANGEL_ENDPOINT, CXB_ID_STR), follow_redirects=True)
        self.assertIn('Please specify token', response.data)

        # both are specified but no user with such cxb_id in our db
        response = self.client.get(
            '{}?{}&{}'.format(ANGEL_ENDPOINT, TOKEN_STR, CXB_ID_STR),
            follow_redirects=True)
        self.assertIn('No user with such cxb_id. Please create one first.', response.data)

    @patch.object(views.requests, 'get')
    def test_angel_auth_invalid(self, get):
        self._create_angel_user()

        class MockResponse(object):
            status_code = 200

            def json(self):
                return {
                    u'tokenCertificationResponse': {
                        u'status': u'invalid',
                        u'code': 200,
                        u'cxb_id': u''}}

        get.return_value = MockResponse()
        response = self._call_angel_endpoint()
        self.assertIn('Angel does not authenticate this user.', response.data)

        class MockResponse(object):
            status_code = 400

        get.return_value = MockResponse()
        response = self._call_angel_endpoint()
        self.assertIn('No right response from Angel.', response.data)

        class MockResponse(object):
            status_code = 200

            def json(self):
                raise ValueError

        get.return_value = MockResponse()
        response = self._call_angel_endpoint()
        self.assertIn('No json returned from Angel.', response.data)

        class MockResponse(object):
            status_code = 200

            def json(self):
                raise Exception
        get.return_value = MockResponse()
        response = self._call_angel_endpoint()
        self.assertIn('Error parsing Angel response.', response.data)

    @patch.object(views.requests, 'get')
    def test_angel_connection_error(self, get):
        self._create_angel_user()
        get.side_effect = ConnectionError
        response = self._call_angel_endpoint()
        self.assertIn('Connection error to Angel validation server.', response.data)

    @patch.object(views.requests, 'get')
    def test_angel_auth_valid(self, get):
        """
        Valid user is logged in and is redirected to /inbound.
        """
        class MockResponse(object):
            status_code = 200

            def json(self):
                return {
                    u'tokenCertificationResponse': {
                        u'status': u'valid',
                        u'code': 200,
                        u'cxb_id': u''}}

        get.return_value = MockResponse()

        self._create_angel_user()
        response = self._call_angel_endpoint()
        self.assertEquals(response.status_code, 200)
