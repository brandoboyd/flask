import json
from datetime      import datetime, timedelta

from bson.objectid import ObjectId

from solariat.mail import Mail

from solariat_bottle.settings import get_var
from solariat_bottle.app import app
from solariat_bottle.db.api_auth     import AuthToken
from solariat_bottle.db.user         import User
from solariat_bottle.db.roles        import AGENT, ANALYST, REVIEWER, ADMIN, STAFF, SYSTEM
from solariat_bottle.db.post.base    import Post
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.account      import Account, AccountEvent
from solariat_bottle.tests.base      import BaseCase, UICase


class UserCase(BaseCase):
    def test_crud(self):
        account = Account.objects.create(name="Test-User-Account")
        user = self._create_db_user(
            email='foo@solariat.com',
            password='12345',
            account=account,
            roles=[AGENT])

        self.assertEqual(
            user.email, 'foo@solariat.com')
        self.assertTrue(
            user.check_password('12345'))
        self.assertEqual(user.current_account, account)

        user.save()

        user.external_id = '345'
        user.save()

        u_loaded = User.objects.get(email='foo@solariat.com')
        self.assertEqual(u_loaded.external_id, '345')

        initial_count = User.objects.count()
        user.delete()
        self.assertEqual(User.objects.count(), initial_count - 1)
        archived_user = User.objects.get(user.id, include_safe_deletes=True)
        self.assertNotEqual(user.email, archived_user.email)
        self.assertNotEqual(user.external_id, archived_user.external_id)
        self.assertTrue(archived_user.email.startswith('old.'))
        self.assertTrue(archived_user.external_id.startswith('old.'))

        self.assertEqual(User.objects.count(include_safe_deletes=True), initial_count)

    def test_user_removal_recreation(self):
        """ Test that in fact all unique keys are updated on user removal and a user can be recreated
        with same data """
        initial_count = User.objects.count()
        user = self._create_db_user(email='foo@solariat.com',
                                    password='12345',
                                    roles=[AGENT],
                                    external_id='345')
        self.assertEqual(user.email, 'foo@solariat.com')
        self.assertTrue(user.check_password('12345'))
        self.assertEqual(user.external_id, '345')
        user.delete()
        # Should be able to do this again now that we archived the older one
        user = self._create_db_user(email='foo@solariat.com',
                                    password='12345',
                                    roles=[AGENT],
                                    external_id='345')
        self.assertEqual(user.email, 'foo@solariat.com')
        self.assertTrue(user.check_password('12345'))
        self.assertEqual(user.external_id, '345')
        user.delete()
        # Should be able to do this again now that we archived the second one one
        user = self._create_db_user(email='foo@solariat.com',
                                    password='12345',
                                    roles=[AGENT],
                                    external_id='345')
        self.assertEqual(user.email, 'foo@solariat.com')
        self.assertTrue(user.check_password('12345'))
        self.assertEqual(user.external_id, '345')
        user.delete()
        # Could not including archived should be same, 3 new archived users should be there
        self.assertEqual(User.objects.count(), initial_count)
        self.assertEqual(User.objects.count(include_safe_deletes=True), initial_count + 3)

    def test_case_insensitive_email(self):
        User.objects.count()
        try:
            user1 = self._create_db_user(
                email='foo@solariat.com',
                password='12345',
                roles=[AGENT])
            user2 = self._create_db_user(
                email='Foo@solariat.com',
                password='12345',
                roles=[AGENT])
            self.assertEqual(user1.id, user2.id)
            self.assertTrue(False, "Should not be allowed to create user with this email just by change in case.")
        except:
            pass

    def test_auth_token(self):
        "Test auth token"
        # create already expired token
        past_point = datetime.utcnow() \
                   - timedelta(seconds=get_var('TOKEN_VALID_PERIOD')*60*60 + 1)
        expired_id = ObjectId.from_datetime(past_point)
        user = self._create_db_user(email='foo@solariat.com', password='123', roles=[AGENT])
        token = AuthToken(id=expired_id,
                          user=user,
                          digest='dummy')
        token.save()

        self.assertEqual(token.id, expired_id)
        self.assertFalse(token.is_valid)

        # this should remove expired token
        AuthToken.objects.create_from_user(user)
        self.failUnlessRaises(AuthToken.DoesNotExist,
                              AuthToken.objects.get,
                              id=expired_id)


class UserUICase(UICase):
    def post_add_to_account(self, payload):
        return self.client.post(
            '/users/add_to_account/json',
            data=json.dumps(payload),
            content_type='application/json')

    def post_remove_from_account(self, payload):
        return self.client.post(
            '/users/remove_from_account/json',
            data=json.dumps(payload),
            content_type='application/json')

    def test_add_to_account(self):
        """Test that staff users can be added to accounts by other staff users.
        https://github.com/solariat/tango/issues/3683
        """
        # non staff user cannot access this enpoint
        # self.user is ADMIN
        self.login(user=self.user)
        # create user
        user = self._create_db_user(
            email='foo@solariat.com',
            password='12345',
            roles=[STAFF])
        # add to account
        payload = {'user': {'email': user.email}}
        resp = self.post_add_to_account(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(json.loads(resp.data)['ok'])

        # make self.user STAFF
        self.user.user_roles.append(STAFF)
        self.user.save()
        resp = self.post_add_to_account(payload)
        self.assertEqual(resp.status_code, 200)
        user.reload()
        # user is added to account and it is set to current account
        self.assertEqual(user.current_account, self.user.current_account)
        self.assertIn(self.user.current_account.id, user.accounts)

        # non staff user cannot be added to account
        user = self._create_db_user(
            email='foo2@solariat.com',
            password='12345',
            roles=[ADMIN])
        payload = {'user': {'email': user.email}}
        resp = self.post_add_to_account(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(json.loads(resp.data)['ok'])

        # cannot add non-existing user
        payload = {'user': {'email': 'non-existing-user@example.com'}}
        resp = self.post_add_to_account(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(json.loads(resp.data)['ok'])

    def test_remove_from_account(self):
        """Test that staff users can be removed from accounts by other staff users.
        https://github.com/solariat/tango/issues/3696
        """

        # create user
        user = self._create_db_user(
            email='foo@solariat.com',
            password='12345',
            roles=[STAFF])

        # non staff user cannot access this enpoint
        # self.user is ADMIN
        self.login(user=self.user)
        # try to access endpoint
        payload = {'user': {'email': user.email}}
        resp = self.post_remove_from_account(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(json.loads(resp.data)['ok'])

        # make self.user STAFF and add user
        self.user.user_roles.append(STAFF)
        self.user.save()
        resp = self.post_add_to_account(payload)

        # remove user
        payload = {'user_id': str(user.id)}
        resp = self.post_remove_from_account(payload)
        # user is removed from account
        self.assertNotEqual(user.current_account, self.user.current_account)
        self.assertNotIn(self.user.current_account.id, user.accounts)

        # remove non-existing user
        payload = {'user_id': '1234'}
        resp = self.post_remove_from_account(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(json.loads(resp.data)['ok'])

        # cannot remove non-staff user
        user = self._create_db_user(
            email='foo2@example.com',
            password='123456',
            roles=[ADMIN],
            account=self.user.current_account)
        payload = {'user': {'email': user.email}}
        resp = self.post_add_to_account(payload)
        resp = self.post_remove_from_account(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(json.loads(resp.data)['ok'])

        # user is added to two accounts
        # when removed from one he stays in another
        user = self._create_db_user(
            email    = 'admin@solariat.com',
            password = '1',
            account  = 'TestAccount',
            roles    = [STAFF]
        )
        payload = {'user': {'email': user.email}}
        # user will be added to TestAccount and self.user.account
        resp = self.post_add_to_account(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.data)['ok'])
        payload = {'user_id': str(user.id)}
        resp = self.post_remove_from_account(payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.data)['ok'])
        # user is removed from account
        self.assertNotEqual(user.current_account, self.user.current_account)
        self.assertNotIn(self.user.current_account.id, user.accounts)
        self.assertEqual(len(user.accounts), 1)

    def test_staff_user_list(self):
        '''Test the staff user endpoint'''
        staff1 = self._create_db_user(email="staff1@solariat.com", password="12345", roles=[STAFF])
        staff2 = self._create_db_user(email="staff2@solariat.com", roles=[STAFF])
        admin1 = self._create_db_user(email="admin1@solariat.com", password="12345", roles=[ADMIN])

        self.login(user=staff1)

        resp = self.client.get('/users/staff/json', content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error', None))
        self.assertTrue('users' in resp)
        staff_emails = resp['users']
        self.assertEqual(len(staff_emails), 2)
        self.assertTrue('staff2@solariat.com' in staff_emails)
        self.assertFalse('admin1@solariat.com' in staff_emails)

        self.login(user=admin1)
        resp = self.client.get('/users/staff/json', content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])


class AgentCase(UICase):

    def setUp(self):
        super(AgentCase, self).setUp()
        self.account = Account.objects.create(name="AgentTest")
        self.admin_user = self._create_db_user(
            email    = 'admin@account.com',
            password = '1',
            account  = self.account,
            roles    = [ADMIN]
        )
        self._create_static_events(self.admin_user)
        #self.login(self.admin_user)

    def test_set_agent_fields(self):
        user = self._create_db_user(email='user1@account.com', roles=[AGENT])
        self.account.add_user(user)
        self.assertEqual(user.agent_id, 0)
        self.assertEqual(user.signature, None)
        self.assertEqual(user.user_profile, None)
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name='@tesT_Name'))
        user.user_profile = user_profile
        user.save()

        self.assertEqual(user.agent_id, 1)
        self.assertEqual(user.user_profile, user_profile)

        user.reload()
        self.assertEqual(user.agent_id, 1)
        self.assertEqual(user.user_profile, user_profile)

        user.signature = '^TS '
        user.save()

        self.assertEqual(user.screen_name, '@tesT_Name')
        self.assertEqual(user.normalized_screen_name, '@test_name')
        self.assertEqual(user.signature, '^ts')
        self.assertEqual(user._signature, '^TS ')
        self.assertEqual(user._user_profile, user_profile.id)

        self.assertEqual(set(user.agent_lookup), {'a:1', 's:^ts', 'u:@test_name'})

    def _make_agent(self, email, signature, screen_name):
        user = self._create_db_user(email=email, password='1', account=self.account, roles=[AGENT])
        user.account = self.account
        user.signature = signature
        if screen_name:
            user.user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        user.save()
        return user

    def test_agent_lookup(self):
        num_agents = 5
        agents = [self._make_agent("agent%s@account.com" % i, "^%s" % i, "@screen_name_%s" % i)
                  for i in range(num_agents)]
        print [(a.account, a.agent_lookup) for a in agents]

        agent3 = User.objects.find_agent(self.account, signature='^2', user_profile="@screen_name_1")
        self.assertEqual(agent3.signature, '^2')

        agent2 = User.objects.find_agent(self.account, user_profile="@screen_name_1")
        self.assertEqual(agent2.screen_name, '@screen_name_1')

        post = self._create_db_post(channels=[self.channel],
                                    content='content'+agent2.signature,
                                    user_profile=agent3.user_profile)
        agent = User.objects.find_agent_by_post(self.account, post)
        self.assertEqual(agent, agent2)

        post = self._create_db_post(channels=[self.channel],
                                    content='content',
                                    user_profile=agent3.user_profile)
        agent = User.objects.find_agent_by_post(self.account, post)
        self.assertEqual(agent, agent3)


        user = self._make_agent('agent_no_user_profile@test.test', '^SGN', None)
        agent = User.objects.find_agent(self.account, signature='^sgn', user_profile=None)
        self.assertEqual(user.agent_id, agent.agent_id)

        post = self._create_db_post(channels=[self.channel],
                                    content='post content^sgn')
        agent = User.objects.find_agent_by_post(self.account, post)
        self.assertEqual(user.agent_id, agent.agent_id)

    def test_extract_signature(self):
        up = self._make_agent('agent_no_user_profile@test.test', '^IZ', None)
        content = "You don't need an appointment.\n^IZ"
        self.assertEqual(Post(content=content, actor_id=up.id, is_inbound=False, _native_id='1').extract_signature(), '^IZ')
        content = "You don't need an appointment. ^IZ"
        self.assertEqual(Post(content=content, actor_id=up.id, is_inbound=False, _native_id='2').extract_signature(), '^IZ')

    def test_user_management_list(self):
        ""' Test the entire permissions lists for users on the user management page ""'
        def get_users(user):
            self.login(user=user)
            resp = self.client.get("/configure/account/userslist?account=" + str(self.user.account.id),
                                    content_type='application/json')
            data = json.loads(resp.data)
            self.assertTrue(data['ok'])
            return data['users']

        User.objects.remove(id__ne=1)   # Clear all users so we get cleaned results
        agent_1 = self._create_db_user(email="agent1@test.test", roles=[AGENT], account=self.user.account)
        agent_2 = self._create_db_user(email="agent2@test.test", roles=[AGENT], account=self.user.account)
        agent_1, agent_2  # to disable pyflakes warning
        agent_analyst = self._create_db_user(email="agent_analyst@test.test", roles=[AGENT, ANALYST],
                                             account=self.user.account)
        reviewer = self._create_db_user(email="reviewer@test.test", roles=[REVIEWER], account=self.user.account)
        system = self._create_db_user(email="system@test.test", roles=[SYSTEM], account=self.user.account)
        system  # to disable pyflakes warning
        staff = self._create_db_user(email="staff@test.test", roles=[STAFF], account=self.user.account)
        admin = self._create_db_user(email="admin@test.test", roles=[ADMIN], account=self.user.account)

        users = get_users(reviewer)
        # Reviewer should see all but system / staff and should edit none but themself
        self.assertTrue(len(users) == 5, len(users))
        for user in users:
            if user['id'] != str(reviewer.id):
                self.assertTrue(user['perms'], 'r')
                self.assertTrue(user['can_contact'])
            else:
                self.assertTrue(user['perms'], 'w')
                self.assertFalse(user['can_contact'])

        users = get_users(agent_1)
        # Agent should see all but system / staff and should edit none but themself
        self.assertTrue(len(users) == 5)
        for user in users:
            if user['id'] != str(agent_1.id):
                self.assertTrue(user['perms'], 'r')
                self.assertTrue(user['can_contact'])
            else:
                self.assertTrue(user['perms'], 'w')
                self.assertFalse(user['can_contact'])

        users = get_users(agent_analyst)
        # Analyst should see all but system / staff and should edit none but themself
        self.assertTrue(len(users) == 5)
        for user in users:
            if user['id'] != str(agent_analyst.id):
                self.assertTrue(user['perms'], 'r')
                self.assertTrue(user['can_contact'])
            else:
                self.assertTrue(user['perms'], 'w')
                self.assertFalse(user['can_contact'])

        users = get_users(admin)
        # Admin should see all but system and should edit all but staffs
        self.assertTrue(len(users) == 6)
        for user in users:
            if user['main_role'] != 'STAFF':
                self.assertTrue(user['perms'], 'w')
                if user['id'] != str(admin.id):
                    self.assertTrue(user['can_contact'])
            else:
                self.assertTrue(user['perms'], 'r')
                self.assertTrue(user['can_contact'])

        users = get_users(staff)
        # Admin should see all but system and should edit all
        self.assertTrue(len(users) == 6)
        for user in users:
            self.assertTrue(user['perms'], 'w')
            if user['id'] != str(staff.id):
                self.assertTrue(user['can_contact'])

    def test_agents_created_on_demand(self):
        from ..db.channel.twitter import TwitterServiceChannel
        profile1 = UserProfile.objects.upsert('Twitter', dict(user_id='11', screen_name='@profile1'))  # user
        profile2 = UserProfile.objects.upsert('Twitter', dict(user_id='22', screen_name='@profile2'))  # agent1
        profile3 = UserProfile.objects.upsert('Twitter', dict(user_id='33', screen_name='@profile3'))  # agent2
        self.assertEqual(User.objects(agent_id=-1).count(), 0)

        sc = TwitterServiceChannel.objects.create_by_user(self.admin_user, account=self.account, title='Service')

        post = self._create_db_post(
            user=self.admin_user,
            channels=[sc.inbound_channel],
            content='Content',
            user_profile=profile1,
            twitter={'id':'1111111111'})

        # Agents not created on inbound post
        self.assertEqual(self.account.get_agents().count(), 0)

        # outbound post, but not reply
        outbound_post = self._create_db_post(
            user=self.admin_user,
            channels=[sc.outbound_channel],
            content='Content',
            user_profile=profile2)

        post, outbound_post  # to disable pyflakes warning

        # Agent created on outbound
        self.assertEqual(self.account.get_agents().count(), 1)

        # Reply to inbound post
        reply = self._create_db_post(
            user=self.admin_user,
            channels=[sc.outbound_channel],
            content='Content',
            user_profile=profile2,
            twitter={'id':'1231231231', 'in_reply_to_status_id': '1111111111'})

        self.assertEqual(self.account.get_agents().count(), 1)
        user = list(self.account.get_agents())[0]
        self.assertTrue(user.agent_id > 0)
        self.assertTrue(user.user_profile, profile2)

        # Reply again and verify agents list is the same
        reply = self._create_db_post(
            user=self.admin_user,
            channels=[sc.outbound_channel],
            content='Content',
            user_profile=profile2,
            twitter={'id':'9879879871', 'in_reply_to_status_id': '1111111111'})

        self.assertEqual(self.account.get_agents().count(), 1)
        user = list(self.account.get_agents())[0]
        self.assertTrue(user.agent_id > 0)
        self.assertTrue(user.user_profile, profile2)

        # we used to post outbound posts with user_profile=None, but now we don't:

        # reply = self._create_db_post(
        #     user=self.admin_user,
        #     channels=[sc.outbound_channel],
        #     content='Content',
        #     user_profile=None,
        #     twitter={'id':'7657657651', 'in_reply_to_status_id': '1111111111'})
        # self.assertEqual(self.account.get_agents().count(), 2)
        # anon = UserProfile.objects.upsert('Twitter', dict(screen_name='anonymous'))
        # profiles = set([u.user_profile.id for u in self.account.get_agents()])
        # self.assertEqual({anon.id, profile2.id}, profiles)

        # set user_profile to None explicitly and feed it to service channel
        self.assertEqual(User.objects(agent_id=-1).count(), 0)
        reply.user_profile = None
        reply.save()
        agent = User.objects.find_agent_by_post(sc.account, reply)
        self.assertEqual(agent.agent_id, -1)
        # Still 2 agents in account, and created anonymous User with agent_id = -1
        # self.assertEqual(self.account.get_agents().count(), 2)
        self.assertEqual(User.objects(agent_id=-1).count(), 1)

        # Verify agents added to account with 'read' permission and added to service channel
        reply = self._create_db_post(
            user=self.admin_user,
            channels=[sc.outbound_channel],
            content='Content',
            user_profile=profile3,
            twitter={'id':'8238238238', 'in_reply_to_status_id': '1111111111'})

        agents = set()
        self.account.reload()
        for agent in self.account.get_agents():
            self.assertTrue(self.account.can_view(agent))
            self.assertFalse(self.account.can_edit(agent) and not agent.is_admin)
            agents.add(agent)
        sc.reload()
        self.assertEqual(len(sc.agents), 2)  #profile2, profile3
        self.assertEqual(set(sc.agents), agents)

    def test_find_agent_by_post(self):
        # user = User.objects.find_agent_by_post(account, self)
        self._make_agent("sign@account.com", "^ag", None)
        self._make_agent("nosign%s@account.com", None, "@without_signature")

        agent1 = User.objects.find_agent(self.account, signature="^ag")
        agent2 = User.objects.find_agent(self.account, user_profile="@without_signature")
        self.assertEqual(agent1.user_profile, None)
        self.assertEqual(agent1.signature, "^ag")
        self.assertEqual(agent2.user_profile.id, "@without_signature:0")
        self.assertEqual(agent2.signature, None)

        post1 = self._create_db_post(
            channels=[self.channel],
            content='content '+agent1.signature,
            user_profile=agent2.user_profile
        )
        post2 = self._create_db_post(
            channels=[self.channel],
            content='content ^nosign',
            user_profile=agent2.user_profile
        )
        user1 = User.objects.find_agent_by_post(self.account, post1)
        user2 = User.objects.find_agent_by_post(self.account, post2)
        self.assertEqual(user1.id, agent1.id)
        self.assertEqual(user2.id, agent2.id)

    def test_find_agent2(self):
        """https://github.com/solariat/tango/issues/4757
        """
        from solariat_bottle.db.user_profiles.user_profile import UserProfile
        from solariat_bottle.db.channel.twitter import TwitterServiceChannel

        acc1 = Account.objects.create(name='Acc1')

        username = '@SkyHelpTeam'
        # intentionally create a user with None email
        u = User.objects.create(email="test_no_email@test.test")
        u.data["el"] = None
        u.save()

        user_profile = UserProfile.objects.upsert('Twitter', {'screenname': username[1:]})

        def setup_sc_channel(username, account):
            self.user.is_superuser = True
            self.user.account = account
            sc = TwitterServiceChannel.objects.create_by_user(self.user, account=account, title='Test')
            sc.add_username(username)
            sc.add_keyword(username)
            return sc

        sc1 = setup_sc_channel(username, acc1)
        # create a post on outbound channel without any agent so it should
        # create a new one -
        # assigning signature on new user should not fail
        post = self._create_db_post(u'@AdrianOliver40 We have not forgotten about you Adrian ;-) As soon as we know more we will drop you a tweet and h... http://t.co/R3Nk2ln1s1',
                                    channels=[sc1.outbound_channel],
                                    user_profile=user_profile,
                                    is_inbound=False)
        print post.find_agent_id(sc1)

    def post_users_edit(self, payload):
        account_event_count = AccountEvent.objects().count()
        resp = self.client.post('/users/edit/json', data=json.dumps(payload), content_type='application/json')
        data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        # if user was edited, then AccountEvent should be created
        if payload.get('id') and data['ok'] == True:
            self.assertEqual(AccountEvent.objects().count(), account_event_count+1)
        return data

    def test_user_create_update_ui(self):
        self.login(user=self.user)
        first_name = 'agent33'
        email = 'agent33@solariat.com'
        roles = ['100', '1000', '2000']
        payload = {'first_name': first_name,
                   'last_name': 'agent33',
                   'email': email,
                   'roles': roles}
        mail = Mail(app)

        def check_outbox(outbox, payload):
            message = outbox[-1]
            self.assertTrue(message.recipients == [payload['email']])
            self.assertEqual(message.sender, "Genesys Social Analytics Notification <Notification-Only--Do-Not-Reply@" + app.config['HOST_DOMAIN'].split('//')[-1] + '>')
            self.assertEqual(message.subject, "Your Genesys Social Analytics Login Has Been Setup")

        def assert_error(error):
            data = self.post_users_edit(payload)
            self.assertFalse(data['ok'])
            self.assertEqual(data['error'], error)

        with mail.record_messages() as outbox:
            data = self.post_users_edit(payload)
            self.assertTrue(data['ok'])
            self.assertEqual(len(outbox), 1)
            check_outbox(outbox, payload)

            # try to create user with the same email
            assert_error('There is already a user with the same email.')

            # try to create user with the same first/last name in current account
            del payload['email']
            assert_error('Email needs to be provided and unique.')
            payload['email'] = 'another' + email

            del payload['first_name']
            assert_error('Both first and last name need to be provided.')
            payload['first_name'] = first_name

            del payload['roles']
            assert_error('At least one role needs to be specified.')
            payload['roles'] = roles

            assert_error('There is already a user with the same name.')
            payload['first_name'] = 'another' + first_name
            data = self.post_users_edit(payload)
            self.assertTrue(data['ok'])

            payload['id'] = 'invalid'
            payload['first_name'] = 'another one' + first_name
            assert_error('No user was found with the given id.')

            # update user
            user = data['user']
            payload['id'] = user['id']
            payload['first_name'] = first_name  # name was taken by prev. user
            assert_error('There is already a user with the same name.')

            # update with current name
            payload['first_name'] = user['first_name']
            data = self.post_users_edit(payload)
            self.assertTrue(data['ok'])

            self.assertEqual(len(outbox), 2)
            check_outbox(outbox, payload)
