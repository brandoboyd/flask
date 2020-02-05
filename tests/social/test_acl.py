import json
import unittest

from solariat_bottle.tests.base import UICase
from solariat_bottle.db.account import Account
from solariat_bottle.db.user import User
from solariat_bottle.db.roles import ADMIN, STAFF, AGENT
from solariat_bottle.utils.acl import get_users_and_groups_with_perms, share_object_by_user


def make_user_perm_str(user, perm="r", add_or_change="add"):
    return make_perm_str(user.email, perm, add_or_change)

def make_perm_str(email, perm="r", add_or_change="add"):
    """
    Makes user with permission string as it received from client.
    perm = r|rw|d
    add_or_change = add|change
    """
    return "%s:%s:%s" % (email, perm, add_or_change)

@unittest.skip("Bookmarks are deprecated since Inbox is depricated")
class BookmarkShareCase(UICase):
    def setUp(self):
        UICase.setUp(self)
        self.login()
        
        # Set to auto respond
        self.channel.response_enabled = True
        self.channel.save()
        self.bookmark1 = create_bookmark(self.user, self.channel)
        self.bookmark2 = create_bookmark(self.user, self.channel)

    def test_new_perm_scenarios(self):
        current_user = self.user
        object_type = 'bookmark'
        # Multiple objects
        objects = [self.bookmark1, self.bookmark2]
        #user_count = User.objects.count()
        # Should be the same user...
        user1 = self._create_db_user(email="user1@foobar.com", password="password", roles=[AGENT])
        user2 = self._create_db_user(email="USER2@foobar.com", password="password", roles=[AGENT])
        users = [{'email': user1.email, 'action': 'add'},
                 {'email': user2.email, 'action': 'add'}]
        ok, result = share_object_by_user(current_user, object_type, objects, users, send_email=False)
        self.assertTrue(ok)
        for obj in objects:
            self.assertTrue(obj.has_perm(user1))
            self.assertTrue(obj.has_perm(user2))

    def test_share(self):
        current_user = self.user
        object_type = 'bookmark'

        objects = []
        users = []
        # test no objects to share
        ok, result = share_object_by_user(current_user, object_type, objects, users, send_email=False)
        self.assertFalse(ok)
        self.assertEquals(result, "No %(object_type)ss selected. Choose at least 1 %(object_type)s to share." % locals())

        # test no users to share with
        objects = [self.bookmark1, self.bookmark2]
        ok, result = share_object_by_user(current_user, object_type, objects, users, send_email=True)
        self.assertFalse(ok)
        self.assertEquals(result, "No Users found. Add at least 1 email address to share selected %ss." % object_type)

        # test normal use case
        user1 = self._create_db_user(email="ro@solariat.com", roles=[AGENT])
        user2 = self._create_db_user(email="w@solariat.com", roles=[ADMIN])
        self.assertFalse(self.bookmark1.has_perm(user1))
        self.assertFalse(self.bookmark2.has_perm(user1))
        self.assertFalse(self.bookmark1.has_perm(user2))
        self.assertFalse(self.bookmark2.can_edit(user2))

        objects = [self.bookmark1, self.bookmark2]
        user_perms = [
            {'email': user1.email, 'action': 'add'},
            {'email': user2.email, 'action': 'add'}
        ]
        ok, result = share_object_by_user(current_user, object_type, objects, user_perms, send_email=False)
        self.assertTrue(ok)

        # check permissions
        self.assertTrue(self.bookmark1.has_perm(user1))
        self.assertTrue(self.bookmark2.has_perm(user1))
        self.assertTrue(self.bookmark1.can_edit(user2))
        self.assertTrue(self.bookmark2.can_edit(user2))

        # test delete permission
        user_perms = [
            {'email': user1.email, 'action': 'del'},
            {'email': user2.email, 'action': 'del'}
        ]
        ok, result = share_object_by_user(current_user, object_type, objects, user_perms, send_email=False)
        self.assertTrue(ok)

        self.assertFalse(self.bookmark1.can_view(user1))
        self.assertFalse(self.bookmark2.can_view(user1))
        self.assertFalse(self.bookmark1.can_edit(user2))
        self.assertFalse(self.bookmark2.can_edit(user2))

    @unittest.skip("Deprecated after group changes")
    def test_get_users_with_perms(self):
        # If no objects passed expect superusers in result
        objects = []
        su = self._create_db_user('su@test.test', is_superuser=True, roles=[STAFF])
        user_perms, group_perms = get_users_and_groups_with_perms(objects, skip_su=False)
        self.assertEqual(len(user_perms), 1)
        self.assertEquals(user_perms[0]['perm'], 's')

        user1 = self._create_db_user(email="ro@solariat.com", roles=[AGENT])
        user2 = self._create_db_user(email="w@solariat.com", roles=[AGENT])
        # test get with rights intersection
        # user1 can read bookmark
        # user1 can edit bookmark1
        share_object_by_user(self.user, 'bookmark', [self.bookmark1], [make_user_perm_str(user1)], send_email=False)
        share_object_by_user(self.user, 'bookmark', [self.bookmark2], [make_user_perm_str(user1, 'rw')], send_email=False)
        objects = [self.bookmark1, self.bookmark2]
        user_perms, group_perms = get_users_and_groups_with_perms(objects)
        self.assertEqual(len(user_perms), 2) # self.user + user1
        for u in user_perms:
            if u["email"] == user1.email:
                self.assertEquals(u["perm"], 'r')  # 'r' is intersection for 'r' and 'rw'

        # user2 has write perm on both bookmarks
        share_object_by_user(self.user, 'bookmark', [self.bookmark1], [make_user_perm_str(user2, 'rw')], send_email=False)
        share_object_by_user(self.user, 'bookmark', [self.bookmark2], [make_user_perm_str(user2, 'rw')], send_email=False)

        user_perms, group_perms = get_users_and_groups_with_perms(objects)
        self.assertEqual(len(user_perms), 3) # self.user + user1 + user2
        for u in user_perms:
            if u["email"] == user1.email:
                self.assertEquals(u["perm"], 'r')  # 'r' is intersection for 'r' and 'rw'
            if u["email"] == user2.email:
                self.assertEquals(u["perm"], 'rw')

    @unittest.skip("Deprecated after group changes")
    def test_http_handler(self):
        # Test get users with permissions
        payload = {'a':'get',
                   'ot':'bookmark',
                   'id':[str(self.bookmark1.id)]}

        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertEquals(len(data['result']), 2)
        self.assertEqual(len(data['result']['users']), 1) # only superuser - bookmark is not shared yet
        for u in data['result']['users']:
            self.assertEquals(u['email'], self.user.email)

        # Test share bookmark with user that has no write perm on it
        user1 = self._create_db_user(email="u1@solariat.com", password="1", group="group1", account="Acc", roles=[AGENT])
        user2 = self._create_db_user(email="u2@solariat.com", password="1", group="group2", account="Acc", roles=[AGENT])
        # Share bookmarks with user1 with read-only access
        share_object_by_user(self.user, 'bookmark', [self.bookmark1, self.bookmark2], [make_user_perm_str(user1)], send_email=False)
        self.login(user1.email, "1")
        # user1 tries to share bookmarks with user2
        payload = {'a':'share',
                   'ot':'bookmark',
                   'id':[str(self.bookmark1.id), str(self.bookmark2.id)],
                   'up':[make_user_perm_str(user2)]}

        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])
        self.assertEquals(data['result'], "User has no permission to share")

        # Test share bookmark with user that has write perm on it
        # adjust permission
        share_object_by_user(self.user, 'bookmark', [self.bookmark1, self.bookmark2], [make_user_perm_str(user1, 'rw', 'change')], send_email=False)

        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        # login back with superuser
        self.login(self.user.email, "12345")

        # Test delete permissions
        payload = {'a':'share',
                   'ot':'bookmark',
                   'id':[str(self.bookmark1.id), str(self.bookmark2.id)],
                   'up':[make_user_perm_str(user2, 'd', 'change'), make_user_perm_str(user1, 'd', 'change')]}

        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        self.bookmark1.reload()
        self.bookmark2.reload()

        self.assertFalse(self.bookmark1.has_perm(user1, 'w'))
        self.assertFalse(self.bookmark2.has_perm(user1, 'w'))
        self.assertFalse(self.bookmark1.has_perm(user2, 'r'))
        self.assertFalse(self.bookmark2.has_perm(user2, 'r'))

        # Test normal share case
        payload = {'a':'share',
                   'ot':'bookmark',
                   'id':[str(self.bookmark1.id), str(self.bookmark2.id)],
                   'up':[make_user_perm_str(user2), make_user_perm_str(user1, 'rw')]}

        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        #check perms
        self.bookmark1.reload()
        self.bookmark2.reload()
        self.assertTrue(self.bookmark1.has_perm(user1, 'w'))
        self.assertTrue(self.bookmark2.has_perm(user1, 'w'))
        self.assertTrue(self.bookmark1.has_perm(user2, 'r'))
        self.assertTrue(self.bookmark2.has_perm(user2, 'r'))


class AccountShareCase(UICase):
    def setUp(self):
        UICase.setUp(self)
        self.login()

        self.account = Account.objects.create(name='solariat_test')
        self.account.add_perm(self.user)

        self.user2 = self._create_db_user(email='u2@all.com', account='Account2', roles=[AGENT])
        self.account2 = self.user2.account

    @unittest.skip("Deprecated after group changes")
    def test_user_management(self):
        # Add new not registered user
        users = list(self.account.get_users())
        payload = {'a':'share',
                   'ot':'account',
                   'id':[str(self.account.id)],
                   'up':["new_user@test.test:r:add"]}
        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])

        #test added user is actually in account now
        self.account.reload()
        existing_emails = [u.email for u in self.account.get_users()]
        self.assertIn('new_user@test.test', existing_emails)
        new_user = User.objects.get(email='new_user@test.test')
        self.assertTrue(self.account.can_view(new_user))
        self.assertEqual(self.account.get_users().count(), len(users)+1)

        # Now try to add the same user to another account
        users2 = list(self.account2.get_users())
        payload = {'a':'share',
                   'ot':'account',
                   'id':[str(self.account2.id)],
                   'up':["new_user@test.test:r:add"]}
        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

        # test user is still in their first account and has no permission to the second account
        existing_emails = [u.email for u in self.account2.get_users()]
        self.assertNotIn('new_user@test.test', existing_emails)
        self.assertFalse(self.account2.can_view(new_user))
        self.assertFalse(self.account2.can_edit(new_user))
        self.assertEqual(self.account2.get_users().count(), len(users2))

        # Try to Delete User from account 2, although they are not there
        payload = {'a':'share',
                   'ot':'account',
                   'id':[str(self.account2.id)],
                   'up':["new_user@test.test:d:change"]}
        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

        # Delete user from account 1
        self.account.reload()
        users = list(self.account.get_users())
        payload = {'a':'share',
                   'ot':'account',
                   'id':[str(self.account.id)],
                   'up':["new_user@test.test:d:change"]}
        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.account.reload()
        self.assertEqual(len(self.account.get_users()), len(users)-1)

        # Add users to account 2
        # Current user should have edit access to account 2, so let it be superuser
        self.user.is_superuser = True
        self.user.save()
        self.user.reload()

        users2 = list(self.account2.get_users())
        payload = {'a':'share',
                   'ot':'account',
                   'id':[str(self.account2.id)],
                   'up':["new_user@test.test:r:add", "new_user2@test.test:rw:add"]}
        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)

        self.assertTrue(data['ok'])
        self.assertEqual(len(self.account2.get_users()), len(users2)+2)
        emails = [u.email for u in self.account2.get_users()]
        self.assertIn('new_user@test.test', emails)
        self.assertIn('new_user2@test.test', emails)

        #check perms
        new_user = User.objects.get(email='new_user@test.test')
        new_user2 = User.objects.get(email='new_user2@test.test')

        self.account2.reload()

        self.assertTrue(self.account2.can_edit(new_user2))
        self.assertTrue(self.account2.can_view(new_user2))

        self.assertTrue(self.account2.can_view(new_user))
        self.assertFalse(self.account2.can_edit(new_user))

        #Test handler returns extended account data
        payload = {'a':'get',
                   'ot':'account',
                   'extended': 'yes',
                   'id':[str(self.account2.id)]}
        resp = self.client.post('/acl/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        for u in data['result']['users']:
            self.assertTrue('accounts' in u)


class DeleteCase(UICase):
    def setUp(self):
        UICase.setUp(self)
        self.login()
        self.account = Account.objects.create(name="Test-Delete")
        self.account.add_perm(self.user)

    def test_delete(self):
        """Tests deleting user
        """

        # deleting non-existing user
        payload = {'id': 'non-existing-id'}
        resp = self.client.post(
            '/users/delete/json', 
            data=json.dumps(payload),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

        # create a user
        user_to_delete = self._create_db_user(
            email    = 'to_delete@solariat.com',
            password = '12345',
            account  = self.account,
            roles    = [AGENT],
        )

        initial_count = User.objects.count()
        # deleting a user when non-admin
        self.user.user_roles = [AGENT]
        self.user.save()
        payload = {'id': str(user_to_delete.id)}
        resp = self.client.post(
            '/users/delete/json', 
            data=json.dumps(payload),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

        # deleting another user
        self.user.user_roles = [ADMIN]
        self.user.save()
        payload = {'id': str(user_to_delete.id)}
        resp = self.client.post(
            '/users/delete/json', 
            data=json.dumps(payload),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertEqual(User.objects.count(), initial_count - 1)

        # deleting himself
        payload = {'id': str(self.user.id)}
        resp = self.client.post(
            '/users/delete/json', 
            data=json.dumps(payload),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertEqual(User.objects.count(), initial_count - 2)
