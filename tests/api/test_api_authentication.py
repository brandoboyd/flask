import json
from bson.objectid import ObjectId
from datetime import datetime, timedelta

from solariat_bottle.tests.base import BaseCase, UICaseSimple, RestCase

from solariat_bottle.settings import get_var
from solariat_bottle.db.api_auth import ApplicationToken, AuthToken
from solariat_bottle.db.auth import AuthError
from solariat_bottle.db.roles import STAFF, ADMIN

class APIAuthMixin:

    def _create_superuser(self, email='super@test.com', password='password', account=None):
        super_user = self._create_db_user(email=email, roles=[STAFF], account=account or self.account)
        super_user.is_superuser = True
        super_user.set_password(password)
        super_user.save()
        super_user.reload()
        self.assertTrue(super_user.is_superuser)
        return super_user


class DBModelCase(BaseCase, APIAuthMixin):

    def test_api_auth_create(self):
        """
        Just a basic happy-flow test on a db level that the api manager works as expected
        """
        super_user = self._create_superuser()
        staff_user = self._create_db_user(email='staff@staff.com', roles=[STAFF])
        admin = self._create_db_user(email='admin@test.com', roles=[ADMIN])
        try:
            ApplicationToken.objects.create_by_user(user=admin,
                                                    creator=admin,
                                                    app_type=ApplicationToken.TYPE_ACCOUNT)
            self.fail("Only superusers should be allowed to create tokens directly")
        except AuthError:
            pass
        self.assertEqual(ApplicationToken.objects.count(), 0)

        try:
            ApplicationToken.objects.create_by_user(user=staff_user,
                                                    creator=admin,
                                                    app_type=ApplicationToken.TYPE_ACCOUNT)
            self.fail("Only superusers should be allowed to create tokens directly")
        except AuthError:
            pass
        self.assertEqual(ApplicationToken.objects.count(), 0)

        valid_token = ApplicationToken.objects.create_by_user(user=super_user,
                                                              creator=admin,
                                                              app_type=ApplicationToken.TYPE_ACCOUNT)
        self.assertEqual(ApplicationToken.objects.count(), 1)
        self.assertEqual(ApplicationToken.objects.verify_application_key(valid_token.app_key), valid_token)

    def test_invalid_key(self):
        superuser = self._create_superuser()
        valid_token = ApplicationToken.objects.create_by_user(user=superuser,
                                                              creator=superuser,
                                                              app_type=ApplicationToken.TYPE_ACCOUNT)
        self.assertEqual(ApplicationToken.objects.count(), 1)
        self.assertEqual(ApplicationToken.objects.verify_application_key(valid_token.app_key), valid_token)
        with self.assertRaises(AuthError):
            ApplicationToken.objects.verify_application_key(valid_token.app_key + '1')

    def test_invalidate_token(self):
        superuser = self._create_superuser()
        valid_token = ApplicationToken.objects.create_by_user(user=superuser,
                                                              creator=superuser,
                                                              app_type=ApplicationToken.TYPE_ACCOUNT)
        self.assertEqual(ApplicationToken.objects.count(), 1)
        self.assertEqual(ApplicationToken.objects.verify_application_key(valid_token.app_key), valid_token)
        valid_token.invalidate()
        with self.assertRaises(AuthError):
            ApplicationToken.objects.verify_application_key(valid_token.app_key)
        valid_token.validate()
        self.assertEqual(ApplicationToken.objects.verify_application_key(valid_token.app_key), valid_token)

    def test_token_request(self):
        superuser = self._create_superuser()
        admin = self._create_db_user(email='admin@test.com', roles=[ADMIN])
        requested_token = ApplicationToken.objects.request_by_user(admin, ApplicationToken.TYPE_CORPORATE)
        with self.assertRaises(AuthError):
            ApplicationToken.objects.verify_application_key(requested_token.app_key)

        self.assertEqual(requested_token.status, ApplicationToken.STATUS_REQUESTED)
        try:
            ApplicationToken.objects.validate_app_request(admin, requested_token)
            self.fail("Only superusers should be able to validate an app request")
        except AuthError:
            pass
        ApplicationToken.objects.validate_app_request(superuser, requested_token)
        requested_token.reload()
        self.assertEqual(ApplicationToken.objects.verify_application_key(requested_token.app_key), requested_token)

    def test_ensure_application(self):
        superuser = self._create_superuser()
        valid_token = ApplicationToken.objects.create_by_user(user=superuser,
                                                              creator=superuser,
                                                              app_type=ApplicationToken.TYPE_ACCOUNT)
        self.assertEqual(ApplicationToken.objects.count(), 1)
        self.assertEqual(ApplicationToken.objects._ensure_application_token(valid_token.id), valid_token)
        self.assertEqual(ApplicationToken.objects._ensure_application_token(str(valid_token.id)), valid_token)
        self.assertEqual(ApplicationToken.objects._ensure_application_token(valid_token), valid_token)


class UIAccessTestCase(UICaseSimple, APIAuthMixin):

    def test_request_app_key(self):
        # First request an api key
        admin = self._create_db_user(email='admin@test.com', roles=[ADMIN])
        self.login(user=admin)
        self.assertEqual(ApplicationToken.objects.count(), 1)
        self.client.post('api_key/request_new',
                         data=json.dumps(dict(type=ApplicationToken.TYPE_BASIC)),
                         content_type='application/json',
                         base_url='https://localhost')
        self.assertEqual(ApplicationToken.objects.count(), 2)
        app_key = ApplicationToken.objects.find_one(creator=admin)
        self.assertEqual(app_key.type, ApplicationToken.TYPE_BASIC)
        self.assertEqual(app_key.status, ApplicationToken.STATUS_REQUESTED)
        self.assertEqual(app_key.creator.id, admin.id)
        # Now try to validate that key, this should fail because we're logged in as admin
        resp = self.client.post('/api_key/%s/validate' % str(app_key.id),
                                content_type='application/json')
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])
        app_key.reload()
        self.assertEqual(app_key.status, ApplicationToken.STATUS_REQUESTED)
        # Create a superuser and login as him
        s_u = self._create_superuser()
        self.login(user=s_u, password='password')
        resp = self.client.post('/api_key/%s/validate' % str(app_key.id),
                                content_type='application/json')
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        app_key.reload()
        self.assertEqual(app_key.status, ApplicationToken.STATUS_VALID)

    def test_user_token(self):
        password = 'password'
        new_user = self._create_db_user(email="test_api@test.com",
                                        password=password,
                                        roles=[ADMIN])
        super_user = self._create_superuser(password=password)
        super_user.save()

        post_data = {'username': super_user.email,
                     'password': password}
        resp = self.client.post("/api/v1.2/authtokens",
                                data=json.dumps(post_data),
                                content_type="application/json",
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertTrue('item' in data, "Got auth response data: " + str(data))

        resp = self.client.post("/api/v2.0/authenticate",
                                data=json.dumps(post_data),
                                content_type="application/json",
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertTrue('token' in data, "Got auth response data: " + str(data))

        post_data = {'username': new_user.email,
                     'password': password}
        resp = self.client.post("/api/v1.2/authtokens",
                                data=json.dumps(post_data),
                                content_type="application/json",
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertTrue('item' in data, "Got auth response data: " + str(data))

        post_data = {'username': new_user.email,
                     'password': password}
        resp = self.client.post("/api/v2.0/authenticate",
                                data=json.dumps(post_data),
                                content_type="application/json",
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 13)
        #self.assertEqual(data['error'],
        #                 "An extra parameter 'api_key' is required for users in order to get a user token.")

        key = ApplicationToken.objects.request_by_user(new_user, app_type=ApplicationToken.TYPE_ACCOUNT)
        key.status = ApplicationToken.STATUS_VALID
        key.save()

        post_data = {'username': new_user.email,
                     'password': password,
                     'api_key': key.app_key}
        resp = self.client.post("/api/v1.2/authtokens",
                                data=json.dumps(post_data),
                                content_type="application/json",
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertTrue('item' in data, "Got auth response data: " + str(data))

        post_data = {'username': new_user.email,
                     'password': password,
                     'api_key': key.app_key}
        resp = self.client.post("/api/v2.0/authenticate",
                                data=json.dumps(post_data),
                                content_type="application/json",
                                base_url='https://localhost')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertTrue('token' in data, "Got auth response data: " + str(data))

        post_data['username'] = 'wrong'
        resp = self.client.post("/api/v2.0/authenticate",
                                data=json.dumps(post_data),
                                content_type="application/json",
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 13)

        post_data['username'] = new_user.email
        post_data['password'] = 'wrong'
        resp = self.client.post("/api/v2.0/authenticate",
                                data=json.dumps(post_data),
                                content_type="application/json",
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 13)


class APIAuthCase(RestCase, APIAuthMixin):

    def test_auth_token_api_expired(self):
        password = 'password'
        past_point = datetime.utcnow() \
                   - timedelta(seconds=get_var('TOKEN_VALID_PERIOD')*60*60 + 1)
        expired_id = ObjectId.from_datetime(past_point)
        super_user = self._create_superuser(password=password)
        super_user.save()

        token = AuthToken(id=expired_id,
                          user=super_user,
                          digest='dummy')
        token._created = past_point
        token.save()

        post_data = dict(token=token.digest)
        data = json.dumps(post_data)
        resp = self.client.get('/api/v2.0/channels',
                               data=data,
                               content_type='application/json',
                               base_url='https://localhost')
        print resp