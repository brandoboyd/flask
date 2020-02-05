import json

from solariat_bottle.db.user import User
from solariat.db.abstract import DoesNotExist
from solariat_bottle.db.roles import AGENT, STAFF

from .base import UICase


class LoginTest(UICase):
    def test_login(self):
        resp = self.login()
        self.assertEqual(
            resp.status_code, 200)

    def test_case_sensitivity(self):
        resp = self.client.post('/login',
                                 data = dict( email=self.user.email.upper(), 
                                              password='12345'),
                                 follow_redirects = True)
        self.assertEqual(resp.status_code, 200)

    def test_wrong_password(self):
        resp = self.client.post('/login',
                                 data = dict( email=self.user.email.upper(), 
                                              password='12345_wrong'),
                                 follow_redirects = True)
        self.assertEqual(resp.status_code, 401)
        

class AccountEditChange(UICase):
    
    def setUp(self):
        UICase.setUp(self)
        self.login()
        self.superuser = self._create_db_user(email="superuser@all.com", roles=[STAFF])
        self.superuser.is_superuser = True
        self.superuser.save()
        self.user_one = self._create_db_user(email="first_user@all.com", roles=[AGENT])
        self.user_one.is_superuser = False
        self.user_one.save()
        self.user_two = self._create_db_user(email="second_user@all.com", roles=[AGENT])
        self.user_two.is_superuser = False
        self.user_two.save()
    
    def test_password_reset(self):
        # Test that superuser can change password to any non-superuser
        self.login(self.superuser.email)
        url = '/users/' + self.user_one.email + '/password'
        data = dict(password='new_password')
        resp = self.client.post(url, data = data, follow_redirects = True)
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])
        # Test that normal user cannot change password for superuser
        self.login(self.user_two.email)
        url = '/users/' + self.superuser.email + '/password'
        data = dict(password='new_password')
        resp = self.client.post(url, data = data, follow_redirects = True)
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])
        # Test that superuser cannot change password for other superuser
        new_superuser = self._create_db_user(email="new_superuser@all.com", roles=[STAFF])
        new_superuser.is_superuser = True
        new_superuser.save()
        self.login(new_superuser.email)
        url = '/users/' + self.superuser.email + '/password'
        data = dict(password='new_password')
        resp = self.client.post(url, data = data, follow_redirects = True)
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])

    def test_remove_user(self):
        """
        Tests that removed user is archived and cannot login.
        """
        password = '123456' 
        email = 'foo@solariat.com'

        resp = self.login(email=email, password=password)

        user = self._create_db_user(email=email, password=password, roles=[AGENT])
        user.save()

        assert User.objects.get(id=str(user.id))

        resp = self.login(email=email, password=password)
        self.assertEqual(resp.status_code, 200)

        resp = self.logout()
        self.assertEqual(resp.status_code, 200)

        user.delete()

        with self.assertRaises(DoesNotExist):
            User.objects.get(id=str(user.id))

        assert User.objects.get(id=str(user.id), include_safe_deletes=True)

        resp = self.login(email=email, password=password)
        self.assertEqual(resp.status_code, 401)
