import copy
import json

from solariat_bottle.api.exceptions import (
    ForbiddenOperation)
from solariat_bottle.api.exceptions import (
    ValidationError, ResourceDoesNotExist)
from solariat_bottle.db.account import Account
from solariat_bottle.db.api_auth import AuthToken
from solariat_bottle.db.roles import AGENT, ADMIN


class APICaseMixin(object):
    model = None
    # obj_id is for updates and deletes
    # needs to be defined in _create_obj
    obj_id = None
    # must have only required parameters
    happy_flow_data = {}
    # for test_update
    update_data = {}
    base_url = ''

    def _create_obj(self):
        # define self.obj_id here
        raise Exception('This method needs to be implemented in specific cases')

    def _create_happy_flow_data(self):
        # some models may need `self` for creation of `self.happy_flow_data`
        pass

    def test_happy_flow(self):
        self._create_happy_flow_data()
        resp = self.do_post(self.base_url, **self.happy_flow_data)
        self.assertTrue(resp['ok'])

    def test_create_with_missing_parameters(self):
        """Requests withouth specifying some required parameters fail.
        """
        def check_bad_data(bad_data):
            resp = self.do_post(self.base_url, wrap_response=False, **bad_data)
            self.assertEqual(resp.status_code, ValidationError.http_code)
            data = json.loads(resp.data)
            self.assertTrue('code' in data)
            self.assertEqual(data['code'], ValidationError.code)

        self._create_happy_flow_data()

        # remove parameters from happy flow data, check that requests fail
        for k in self.happy_flow_data:
            bad_flow_data = copy.copy(self.happy_flow_data)
            bad_flow_data.pop(k)
            check_bad_data(bad_flow_data)

        # a request with no parameters
        check_bad_data({})

    def test_update(self):
        """Test that update works.
        """
        self._create_obj()
        # update
        resp = self.do_put(
            self.base_url + '/{}'.format(self.obj_id),
            **self.update_data)
        self.assertTrue(resp['ok'])
        # check that object was updated
        obj = self.model.objects.get(id=self.obj_id)
        for key in self.update_data:
            self.assertEqual(
                getattr(obj, key),
                self.update_data[key])

    def test_delete(self):
        """Previously created model is deleted via API.
        """
        self._create_obj()
        # delete existing document
        count_before = self.model.objects.count()
        resp = self.do_delete(self.base_url + '/{}'.format(self.obj_id))
        self.assertTrue(resp['ok'])
        count_after = self.model.objects.count()
        self.assertEqual(count_before - count_after, 1)
        # delete non-existing document
        resp = self.do_delete(self.base_url + '/{}'.format(self.obj_id), wrap_response=False)
        self.assertEqual(resp.status_code, ResourceDoesNotExist.http_code)
        data = json.loads(resp.data)
        self.assertTrue('code' in data)
        self.assertEqual(data['code'], ResourceDoesNotExist.code)

    def test_unauthorized(self):
        """Tests some unauthorized operations:
        - non-admin user cannot delete object
        - admin from another account is not authorised
        """

        # 1. non-admin user from this account cannot delete object
        # create agent
        self.user.user_roles = [AGENT]
        self.user.save()
        self._create_obj()
        resp = self.do_delete(
            self.base_url + '/{}'.format(self.obj_id), wrap_response=False)
        self.assertEqual(resp.status_code, ForbiddenOperation.http_code)
        data = json.loads(resp.data)
        self.assertTrue('code' in data)
        self.assertEqual(data['code'], ForbiddenOperation.code)
        self.assertEqual(self.model.objects.count(), 1)

        # 2. admin from another account should not be authorized
        # create user for another account
        new_account = Account.objects.create(name="NEW-TEST-ACCOUNT")
        new_user = self._create_db_user(
            email    = 'new_nobody@solariat.com',
            password = '12345',
            account  = new_account,
            roles    = [ADMIN],
        )
        # re-define auth_token which is used in requests to REST API
        self.auth_token = AuthToken.objects.create_from_user(new_user).digest
        # repeat with this user happy flow test
        self._create_happy_flow_data()
        # it should not be authorized
        resp = self.do_post(self.base_url, wrap_response=False, **self.happy_flow_data)
        self.assertEqual(resp.status_code, ForbiddenOperation.http_code)
        data = json.loads(resp.data)
        self.assertTrue('code' in data)
        self.assertEqual(data['code'], ForbiddenOperation.code)
