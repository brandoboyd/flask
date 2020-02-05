import json
import unittest

from solariat_bottle.db.account import Account
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.channel.base import SmartTagChannel as STC
from solariat_bottle.db.group import Group
from solariat_bottle.db.user import User
from solariat_bottle.db.roles import AGENT, ANALYST, ADMIN
from solariat_bottle.tests.base import MainCase, UICase
from solariat.tests.base import LoggerInterceptor
from solariat_bottle.settings import AppException


class GroupCase(MainCase):

    def test_group_setup(self):
        user1 = self._create_db_user(email="test_user1@test.test", roles=[AGENT])
        user2 = self._create_db_user(email="test_use2@test.test", roles=[AGENT])
        group = Group.objects.create_by_user(self.user,
                                             name="group1",
                                             channels=[],
                                             smart_tags=[],
                                             roles=[],
                                             description="group1 description",
                                             members=[user1.id, str(user2.id)])
        user1.reload()
        user2.reload()

        self.assertTrue(group.id in user1.groups)
        self.assertTrue(user1 in group.members)
        self.assertTrue(user1 in group.get_all_users())

        self.assertTrue(group.id in user2.groups)
        self.assertTrue(user2 in group.members)
        self.assertTrue(user2 in group.get_all_users())

    def test_group_create(self):
        acct1 = Account.objects.get_or_create(name='test_acct1')
        acct2 = Account.objects.get_or_create(name='test_acct2')
        kw = {
            'name': 'name',
            'description': 'description',
            'members': [],
            'channels': [],
            'account': acct1,
            'smart_tags': [],
            'roles': []}
        group1 = Group.objects.create(**kw)
        assert group1.id
        # can create group with the same name for another account
        kw['account'] = acct2
        group2 = Group.objects.create(**kw)
        assert group2.id
        # cannot create group with the same name for account
        # where a group with such name already exists
        with self.assertRaises(AppException):
            Group.objects.create(**kw)

    def test_group_save(self):
        acct = Account.objects.get_or_create(name='test_acct')
        kw = {
            'name': 'name',
            'description': 'description',
            'members': [],
            'channels': [],
            'account': acct,
            'smart_tags': [],
            'roles': []}
        group1 = Group.objects.create(**kw)
        assert group1.id
        # can create group with different name for this account
        kw['name'] = 'different name'
        group2 = Group.objects.create(**kw)
        assert group2.id
        # cannot change name of new group to existing
        with self.assertRaises(AppException):
            group2.save(name='name')
        group2.name = 'name'
        with self.assertRaises(AppException):
            group2.save()


class GroupsUICase(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.account = Account.objects.create(name='solariat_test')
        self.account.add_perm(self.user)
        self.user.account = self.account
        self.user.save()
        self.login()

    def _get_groups(self):
        resp = self.client.get('/groups/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue('data' in data)
        return data['data']

    def _get_members(self, group_id):
        payload = {'id': group_id}
        resp = self.client.post('/groups/get_users/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        print data
        self.assertTrue(data['ok'])
        return data['users']

    def _update_members(self, group_id, users_perms):
        payload = {'up':users_perms, 'id':[group_id]}
        resp = self.client.post('/groups/update_users/json', data=json.dumps(payload), content_type='application/json')
        self.assertEquals(resp.status_code, 200)
        data = json.loads(resp.data)
        print data
        self.assertTrue(data['ok'])
        return data

    def test_fetch_groups(self):
        user = self._create_db_user(email="user1@test.test", roles=[ADMIN], account=self.user.account)
        self.login(user=user)
        group1 = Group.objects.create_by_user(user, name="Grp1", description="Grp1", members=[],
                                              channels=[], smart_tags=[], roles=[])
        group2 = Group.objects.create_by_user(user, name="Grp2", description="Grp1", members=[],
                                              channels=[], smart_tags=[], roles=[])
        groups = self._get_groups()
        self.assertEqual(len(groups), 2)

    def test_member_create_groups(self):
        """
        Test case where a group exists with no users. Then a user is created with that group
        as one of the specific group. Check that the group also reflects this and picks up the
        newly created user as a member.
        """
        group1 = Group.objects.create_by_user(self.user, name="Grp1", description="Grp1", members=[],
                                              channels=[], smart_tags=[], roles=[])
        payload = {'groups': [str(group1.id)],
                   'first_name': 'agent3',
                   'last_name': 'agent3',
                   'email': 'agent3@solariat.com',
                   'roles': ['100', '1000', '2000']}
        self.client.post('/users/edit/json', data=json.dumps(payload), content_type='application/json')
        user = User.objects.get(email='agent3@solariat.com')
        self.assertEqual(len(user.groups), 1)
        group_data = self.client.get('/groups/json?id=' + str(group1.id))
        resp_data = json.loads(group_data.data)
        self.assertTrue(resp_data['ok'])
        self.assertEqual(len(resp_data['group']['members']), 1)
        self.assertEqual(resp_data['group']['members'][0], str(user.id))

    def test_get_members(self):
        user = self._create_db_user(email="user1@test.test", roles=[ADMIN], account=self.user.account)
        self.login(user=user)
        group1 = Group.objects.create_by_user(user, name="Grp1", description="Grp1", members=[str(user.id)],
                                              channels=[], smart_tags=[], roles=[])
        users = self._get_members(str(group1.id))
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['email'], user.email)
        self.assertEqual(users[0]['id'], str(user.id))

    def test_group_crud_ui(self):
        test_channel = TwitterServiceChannel.objects.create_by_user(self.user, title="Test Service Channel")
        # Have a agent before we create any groups
        one_agent = self._create_db_user(email='one_agent@solariat.com', password='12345',
                                         account=self.account, roles=[ADMIN])
        payload = {'description': 'Test',
                   'roles': [AGENT, ANALYST],
                   'channels': [str(test_channel.id)],
                   'members': [], 'smart_tags': [], 'name': 'Test Groups'}
        # Create a group now, don't specify any members, just use roles for permission in batch
        group_creation = self.client.post('/groups/json',
                                          data=json.dumps(payload), content_type='application/json')
        self.assertEqual(group_creation.status_code, 200)
        group = json.loads(group_creation.data)['group']
        # Create two more agents now, have roles which would give them access to group
        analyst_agent = self._create_db_user(email='analysy_agent@solariat.com', password='12345',
                                             account=self.account, roles=[AGENT, ANALYST])
        only_agent = self._create_db_user(email='agent@solariat.com', password='12345',
                                          account=self.account, roles=[AGENT])
        # Check that group is part of all agents but not of admin
        one_agent.reload()
        self.assertFalse(group['id'] in one_agent.groups)
        self.assertTrue(group['id'] in analyst_agent.groups)
        self.assertTrue(group['id'] in only_agent.groups)

        # Now update the group and remove the agent roles, check that the actual permissions
        # on the users were updated properly
        payload['id'] = group['id']
        payload['roles'] = [ANALYST]

        self.client.post('/groups/json', data=json.dumps(payload), content_type='application/json')
        only_agent.reload()
        one_agent.reload()
        analyst_agent.reload()
        # At this point, only the analyst would have permissions
        self.assertFalse(group['id'] in one_agent.groups)
        self.assertTrue(group['id'] in analyst_agent.groups)
        self.assertFalse(group['id'] in only_agent.groups)
        # Re-add agent2 role, at this point two people will have access
        payload['roles'] = [ANALYST, AGENT]
        self.client.post('/groups/json', data=json.dumps(payload), content_type='application/json')
        only_agent.reload()
        one_agent.reload()
        analyst_agent.reload()
        # At this point, both users would have permissions
        self.assertFalse(group['id'] in one_agent.groups)
        self.assertTrue(group['id'] in analyst_agent.groups)
        self.assertTrue(group['id'] in only_agent.groups)

    def test_same_name(self):
        test_channel1 = TwitterServiceChannel.objects.create_by_user(
            self.user, title="Test Service Channel 1")
        payload = {'description': 'Test',
                   'roles': [AGENT, ANALYST],
                   'channels': [str(test_channel1.id)],
                   'members': [], 'smart_tags': [], 'name': 'Test Groups'}
        group_creation = self.client.post('/groups/json',
                                          data=json.dumps(payload), content_type='application/json')
        self.assertEqual(group_creation.status_code, 200)
        self.assertTrue(json.loads(group_creation.data)['ok'])
        # change active account of the current user
        account2 = Account.objects.create(name="TEST-ACCOUNT2")
        self.user.account = account2
        self.user.save()
        test_channel2 = TwitterServiceChannel.objects.create_by_user(
            self.user, title="Test Service Channel 2")
        payload2 = payload.copy()
        payload2['channels'] = [str(test_channel2.id)]
        group_creation = self.client.post('/groups/json',
                                          data=json.dumps(payload2), content_type='application/json')
        self.assertEqual(group_creation.status_code, 200)
        self.assertTrue(json.loads(group_creation.data)['ok'])
        self.assertEqual(Group.objects.count(), 2)
        # create group with the same name for the same account fails
        group_creation = self.client.post('/groups/json',
                                          data=json.dumps(payload2), content_type='application/json')
        self.assertEqual(group_creation.status_code, 200)
        self.assertFalse(json.loads(group_creation.data)['ok'])
        self.assertEqual(Group.objects.count(), 2)

    def test_group_smart_tag_autoadd(self):
        """ Test that if group is set on smart tag creation, tag is automatically added to group. Issue #3478"
        """
        test_channel = TwitterServiceChannel.objects.create_by_user(self.user, title="Test Service Channel")
        payload = {'description': 'Test',
                   'roles': [AGENT, ANALYST],
                   'channels': [str(test_channel.id)],
                   'members': [], 'smart_tags': [], 'name': 'Test Groups'}
        # Create a group now, don't specify any members, just use roles for permission in batch
        group_creation = self.client.post('/groups/json',
                                          data=json.dumps(payload), content_type='application/json')
        group = json.loads(group_creation.data)['group']
        smart_tag_data = {'title': 'TAG',
                          'description': 'TAG',
                          'groups': [group['id']],
                          'channel': str(test_channel.inbound_channel.id)}
        resp = self._post('/smart_tags/create/json', smart_tag_data)
        tag_data = resp['item']

        group_entity = Group.objects.get(group['id'])
        self.assertTrue(str(group_entity.smart_tags[0].id) == str(tag_data['id']))

    def test_group_smart_tag_deleted(self):
        """Test the unsafely removed smart tag channel
        is pulled from group smart tags list. Issue #3632, #3583
        """
        test_channel = TwitterServiceChannel.objects.create_by_user(
            self.user, title="Test Service Channel")
        other_user = self._create_db_user(email='tester_testerson@stuff.com', roles=[AGENT])
        smart_tag = STC.objects.create_by_user(
            self.user,
            title="Tag",
            parent_channel=test_channel.id,
            account=test_channel.account)
        payload = {'description': 'Test',
                   'roles': [AGENT, ANALYST],
                   'channels': [str(test_channel.id)],
                   'members': [str(other_user.id)],
                   'smart_tags': [str(smart_tag.id)],
                   'name': 'Test Groups'}
        self.client.post('/groups/json', data=json.dumps(payload),
                         content_type='application/json')
        groups = self._get_groups()
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['smart_tags'], [str(smart_tag.id)])

        smart_tag.reload()
        other_user.reload()
        self.assertTrue(smart_tag.has_perm(other_user))
        self.assertTrue(str(groups[0]['id']) in smart_tag.acl)

        smart_tag.delete()

        with LoggerInterceptor() as logs:
            groups = self._get_groups()
            group = Group.objects.get(groups[0]['id'])
            self.assertTrue(logs[0].message.startswith(
                "DBRefs pulled from %s.%s:" % (group, Group.smart_tags.db_field)
            ))
            self.assertTrue(str(smart_tag.id) in logs[0].message)

        self.assertEqual(groups[0]['smart_tags'], [])

    def test_group_implicit_members(self):
        """Tests that only users explicitly added to a group are shown as its members.
        """
        test_channel = TwitterServiceChannel.objects.create_by_user(self.user, title="Test Service Channel")
        # Have a agent before we create any groups
        self._create_db_user(email='one_agent@solariat.com', password='12345',
                                         account=self.account, roles=[ADMIN])
        payload = {'description': 'Test',
                   'roles': [AGENT, ANALYST],
                   'channels': [str(test_channel.id)],
                   'members': [], 'smart_tags': [], 'name': 'Test Groups'}

        # Create a group now, don't specify any members, just use roles for permission in batch
        group_creation = self.client.post('/groups/json',
                                          data=json.dumps(payload), content_type='application/json')
        self.assertEqual(group_creation.status_code, 200)
        group = json.loads(group_creation.data)['group']

        # Create two more agents now, have roles which would give them access to group
        self._create_db_user(email='analysy_agent@solariat.com', password='12345',
                                             account=self.account, roles=[AGENT, ANALYST])
        only_agent = self._create_db_user(email='agent@solariat.com', password='12345',
                                          account=self.account, roles=[AGENT])

        # Check that group json has empty members 
        # since no members were added to the group explicitly
        get_resp_data = json.loads(
            self.client.get('/groups/json?id={}'.format(group['id'])).data)
        self.assertEqual(len(get_resp_data['group']['members']), 0)

        # Update this group with one explicit member
        payload['id'] = group['id']
        payload['members'] = [str(only_agent.id)]
        group_update = self.client.post('/groups/json',
                                          data=json.dumps(payload), content_type='application/json')
        self.assertEqual(group_update.status_code, 200)
        get_resp_data = json.loads(
            self.client.get('/groups/json?id={}'.format(group['id'])).data)
        self.assertEqual(len(get_resp_data['group']['members']), 1)

        # Create new group with one explicit member
        payload.pop('id')
        payload['name'] = 'Test Groups 2'
        payload['members'] = [str(only_agent.id)]
        group_creation = self.client.post('/groups/json',
                                          data=json.dumps(payload), content_type='application/json')
        self.assertEqual(group_creation.status_code, 200)
        group = json.loads(group_creation.data)['group']
        get_resp_data = json.loads(
            self.client.get('/groups/json?id={}'.format(group['id'])).data)
        self.assertEqual(len(get_resp_data['group']['members']), 1)

    @unittest.skip("Deprecated")
    def test_update_members(self):
        user = self._create_db_user(email="user1@test.test", account=self.account, roles=[AGENT])
        user2 = self._create_db_user(email="user2@test.test", account=self.account, roles=[AGENT])

        group1 = Group.objects.create_by_user(user, name="Grp1", description="Grp1", members=[],
                                              channels=[], smart_tags=[], roles=[])
        group1.add_user(self.user, 'rw')
        group1.add_user(user, 'rw')
        group1.add_user(user2, 'rw')
        self.user.reload()
        user.reload()

        users = self._get_members(str(group1.id))
        self.assertEqual(len(users), 3)

        #delete write perm for 'user' and remove 'user2' from group
        up = ["%s:r:change" % user.email,
              "%s:d:change" % user2.email]
        self._update_members(str(group1.id), up)

        self.user.reload()
        user.reload()

        users = self._get_members(str(group1.id))
        self.assertEqual(len(users), 2)
        for u in users:
            if u['id'] == str(user.id):
                self.assertEqual(u['perm'], 'r')
            else:
                self.assertEqual(u['id'], str(self.user.id))
                self.assertEqual(u['perm'], 'rw')
