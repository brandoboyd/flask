""" Test construction for post/matchable response
"""
import json
import datetime as dt

from solariat.mail import Mail

from solariat_bottle.app import app
from solariat_bottle.db.roles        import AGENT, STAFF, ADMIN
from solariat_bottle.db.account      import Account, Package, THRESHOLD_WARNING, THRESHOLD_SURPASSED_WARNING
from solariat_bottle.db.channel.base import Channel, ServiceChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.channel.twitter import TwitterChannel
from solariat_bottle.db.user import User
from solariat_bottle.db.group import Group
from solariat_bottle.db.api_auth import ApplicationToken

from solariat_bottle.settings import AppException

from solariat_bottle.db.account import account_stats, all_account_stats

from solariat_bottle.tests.base                import MainCase, UICase, SA_TYPES
from solariat_bottle.tests.slow.test_smarttags import SmartTagsTestHelper

from solariat.utils.timeslot    import datetime_to_timestamp_ms

now = dt.datetime.now
yesterday = now() - dt.timedelta(days=1)
tomorrow = now() + dt.timedelta(days=1)


class AccountTest(MainCase):

    def setUp(self):
        MainCase.setUp(self)
        self.account = Account(name="Solariat Test")
        self.account.save()
        self.user.account = self.account
        self.user.save()
        self.account.add_perm(self.user)
        
    def test_angel_account_name_format(self):
        '''Assert that Angel integration account name types are allowed by the system'''

        # # Removed in #3885 
        # invalid_account_name = "Un$upported Acc*nt Name!"
        # with self.assertRaises(AppException):
        #     Account.objects.create_by_user(self.user, name=invalid_account_name)
            
        account_name = "Ivana_BBBW(0a140220-04-13118333b6b-64c24491-6e9)"
        account = Account.objects.create_by_user(self.user, name=account_name, account_type="Angel")

        self.assertTrue(account is not None)
        self.assertEqual(account.name, account_name)

    def test_no_account_or_team(self):
        user = self._create_db_user(email='x@solariat.com', password='12345', roles=[AGENT])
        self.assertEqual(user.team, [])
        
    def test_team(self):
        self.assertEqual(self.user.team, [])

        x = self._create_db_user(email='x@solariat.com',
                                 password='12345',
                                 account=self.account,
                                 roles=[AGENT])

        self.assertEqual([t.email for t in self.user.team], [x.email])

        y = self._create_db_user(email='y@solariat.com',
                                 password='12345',
                                 account=self.account,
                                 roles=[AGENT])

        self.assertEqual(sorted([t.email for t in self.user.team]),
                         sorted([x.email, y.email]))

    def test_admin(self):
        self.assertEqual(self.user.is_admin, True)
        self.assertEqual([u.email for u in self.account.admins],
                         [self.user.email])

    def test_integration_accounts(self):
        angel = Account.objects.create_by_user(self.user, name="Test-Angel", account_type="Angel")
        self.assertTrue(angel is not None)
        self.assertTrue(angel.name == 'Test-Angel')
        self.assertTrue(angel.account_type == "Angel")

    def test_outbound_channels(self):
        from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel
        ChannelCls = EnterpriseTwitterChannel
        self.assertEqual(self.user.get_outbound_channel("Twitter"), None)

        # Set for account and check defaults
        outbound_1 = ChannelCls.objects.create_by_user(
            self.user, title='Outbound1', 
            type='twitter', intention_types=SA_TYPES)
        self.account.outbound_channels[outbound_1.platform] = outbound_1.id
        self.account.save()

        self.assertEqual(self.user.get_outbound_channel("Twitter").id, 
                         outbound_1.id)

        outbound_2 = ChannelCls.objects.create_by_user(
            self.user, title='Outbound1', 
            type='twitter', intention_types=SA_TYPES)
        self.user.outbound_channels[outbound_2.platform] = outbound_2.id
        self.user.save()

        self.assertEqual(self.user.get_outbound_channel("Twitter").id, 
                         outbound_2.id)

    def test_add_del_perm(self):
        # test user should be added to account when permission is added
        user1 = self._create_db_user(email="u1@all.com", roles=[AGENT])
        user2 = self._create_db_user(email="u2@all.com", roles=[ADMIN])

        users = list(self.account.get_users())
        self.account.add_perm(user1)
        self.assertTrue(self.account.can_view(user1))

        self.account.add_perm(user2)
        self.assertTrue(self.account.can_view(user2))
        self.assertTrue(self.account.can_edit(user2))
        self.assertEquals(len(users) + 2, len(self.account.get_users()))

        # test user deleted from account
        self.account.del_perm(user1)  # We should only have 1 user left
        self.assertEquals(len(users) + 1, len(self.account.get_users()))

    def test_crud_acl(self):
        n_accounts = len(self.user.accounts)

        # Create a new account by the user
        expiry_date = dt.datetime.now() + dt.timedelta(days=1)
        account = Account.objects.create_by_user(self.user, name="TestAccountCRUD", end_date=expiry_date)

        acc_id = str(account.id)
        self.assertTrue(account is not None)
        self.assertEqual(account.name, "TestAccountCRUD")
        self.assertTrue(account.has_perm(self.user))
        self.assertEqual(len(self.user.accounts), n_accounts + 1)
        self.assertEqual(account.end_date, expiry_date)
        # Retrieve it by the user
        retrieved_account = Account.objects.get_by_user(self.user, id=acc_id)
        self.assertEqual(account, retrieved_account)

        # Delete the account
        new_user = self._create_db_user(email="admin@solariat.com", roles=[ADMIN], account=account)
        channel = ServiceChannel.objects.create(title="TestChannel", account=account)
        group = Group.objects.create_by_user(new_user, "TestGroup", None, [str(self.user.id)], [],
                                             [str(channel.id)], [], [])

        self.assertTrue(new_user in account.get_users())
        Account.objects.remove_by_user(self.user, acc_id)
        # The admin user should be also removed

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(str(new_user.id))
        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(str(group.id))
        self.user.reload()
        self.assertEqual(len(self.user.accounts), n_accounts)
        self.assertTrue(acc_id not in self.user.accounts)
        with self.assertRaises(Account.DoesNotExist):
            account = Account.objects.get_by_user(self.user, id=acc_id)


    def test_common_cases(self):
        acct1 = Account(name='NewAccount1')
        acct2 = Account(name='NewAccount2')
        acct1.save()
        acct2.save()

        user1 = self._create_db_user(email="u1@all.com", roles=[AGENT])
        user2 = self._create_db_user(email="u2@all.com", roles=[AGENT])

        #Add both users to account with 'read' permission (default)
        acct1.add_user('u1@all.com')
        acct1.add_user('u2@all.com')
        current_users = [u.email for u in acct1.get_current_users()]
        self.assertEqual(set(current_users), set(['u1@all.com', 'u2@all.com']))
        user1.reload()
        user2.reload()

        #Users should have the acct1 as their current account
        for u in [user1, user2]:
            #accounts() lookup
            self.assertTrue(acct1.id in u.accounts)
            self.assertFalse(acct2.id in u.accounts)
            u.reload()
            #Current account was set to the first account users were added to
            self.assertTrue(u.current_account == u.account == acct1)
            #Total number of available accounts is 1
            self.assertEqual(u.available_accounts.count(), 1)

        #Add users to another account
        for u in [user1, user2]:
            acct2.add_user(u, 'rw')
            #Current account should remain the previous set...
            u.reload()
            self.assertTrue(u.current_account == u.account == acct1)
            #...unless we change it
            u.current_account = acct2
            u.reload()
            self.assertTrue(u.current_account == acct2)
            self.assertEqual(u.available_accounts.count(), 2)

        #Now acct1 should have 0 current users and 2 users with read access
        #acct2  2 current users  2 have write access
        self.assertEqual(len(acct1.get_all_users()), 2)
        self.assertTrue(acct1.get_current_users().count() == acct1.get_users().count() == 0)

        self.assertEqual(len(acct2.get_all_users()), 2)
        self.assertTrue(acct2.get_current_users().count() == acct2.get_users().count() == 2)

        #Remove user from their current account - superuser can do this
        acct2.del_user(user1)  #Note: del_user deletes both 'rw' perms by default
        self.assertEqual(len(acct2.get_all_users()), 1)
        self.assertEqual(len(acct2.get_current_users()), 1)
        user1.reload()
        self.assertFalse(bool(user1.account)) # account is None

        #Now the acct2 should be not settable for user1
        user1.current_account = acct2
        user1.reload()
        self.assertFalse(bool(user1.account)) # still None

        user1.current_account = acct1
        user1.reload()
        self.assertEqual(user1.account, acct1)

    def test_channels_are_being_filtered_by_account(self):
        accounts = [
            Account.objects.create(name="Acct1"),
            Account.objects.create(name="Acct2")
        ]

        channels = [
            Channel.objects.create_by_user(self.user, title='channel1'),
            Channel.objects.create_by_user(self.user, title='channel2')
        ]

        channels[0].account = accounts[0]
        channels[0].save()
        channels[1].account = accounts[1]
        channels[1].save()

        for a in accounts:
            a.add_user(self.user)
        #The current account is 'Solariat Test' so there should be no channels
        self.assertFalse(list(Channel.objects.find_by_user(self.user)))

        self.user.current_account = accounts[0]
        self.user.reload()

        # Now re-add permissions
        channels[0].add_perm(self.user)
        channels[1].add_perm(self.user)
        ch = list(Channel.objects.find_by_user(self.user))
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0].id, channels[0].id)

        self.user.current_account = accounts[1]
        self.user.reload()
        ch = list(Channel.objects.find_by_user(self.user))
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0].id, channels[1].id)

    def test_pricing_packages(self):
        params = {'name': 'TestAcctInternal'}
        account = Account.objects.create_by_user(self.user, **params)

        self.assertTrue(account is not None)
        self.assertEqual(account.account_type, 'Native')
        self.assertTrue(account.package is not None)        
        self.assertEqual(account.package.name, 'Internal')

        params = {'name':  'TestAcctPackage1',
                  'account_type': 'Native', 
                  'package': 'Silver'}

        account = Account.objects.create_by_user(self.user, **params)

        self.assertTrue(account is not None)
        self.assertEqual(account.account_type, 'Native')
        self.assertTrue(account.package is not None)
        self.assertEqual(account.package.name, 'Silver')

        params = {'name': 'TestAcctPackage2',
                  'account_type':  'Skunkworks',
                  'package': 'Bronze'}

        account = Account.objects.create_by_user(self.user, **params)

        self.assertTrue(account is not None)
        self.assertEqual(account.package.name, params['package'])
        self.assertEqual(account.account_type, params['account_type'])
        self.assertTrue(account.is_active)

        params = {'name': 'TestAcctPackage3',
                  'account_type': 'Native',
                  'package': 'Foo'}

        self.assertRaises(AppException, 
                          Account.objects.create_by_user, 
                          self.user, 
                          **params)

        #today = dt.datetime.now()
        #yesterday = today - dt.timedelta(days=1)

        params = {'name': 'TestAcctExpired',
                  'package': 'Trial',
                  'end_date': yesterday}

        account = Account.objects.create_by_user(self.user, **params)
        self.assertTrue(account is not None)
        self.assertFalse(account.is_active)

    def test_csm(self):
        '''Test the customer success manager field logic'''
        # Create an account, if the user is not staff no CSM should be set
        self.assertFalse(self.user.is_staff)
        account = Account.objects.create_by_user(self.user, name="TesAcctCSM")
        self.assertTrue(account.customer_success_manager is None)

        # Add the staff role to the user and try again, this time CSM should be altered
        self.user.user_roles.append(STAFF)
        #self.user.save()

        self.assertTrue(self.user.is_staff)
        account = Account.objects.create_by_user(self.user, name="TestAcctCSM2")
        self.assertTrue(account.customer_success_manager is not None)
        self.assertEqual(account.customer_success_manager, self.user)

        # Superusers should not be assigned as a CSM
        su = self._create_db_user(email="super_user@solariat.com", password="12345", is_superuser=True)
        account = Account.objects.create_by_user(su, name="TestAcctSU")
        self.assertTrue(account.customer_success_manager is None)

    def test_empty_pricing_packages(self):
        '''Test that the proper pricing packages are created in the case that they don't exist'''

        Package.objects.coll.drop()

        account = Account.objects.create_by_user(self.user, name="TestAcctInternal")

        self.assertTrue(isinstance(account.package, Package))
        self.assertEqual(account.package.name, 'Internal')

    def test_account_acl(self):
        '''Test Account ACL issues #3640, #3701'''
        # Super user creates an account
        su = self._create_db_user(is_superuser=True, email="super_user@solariat.com", password="12345")
        account = Account.objects.create_by_user(su, name='TestAcctACL')
        acc_id = str(account.id)
        # Assign a staff user
        staff = self._create_db_user(email="staff@solariat.com", password="12345", roles=[STAFF], account=account)

        self.assertTrue(acc_id in staff.accounts)

        n_account = Account.objects.get_by_user(staff, acc_id)
        self.assertEqual(account, n_account)

        self.account.add_perm(staff)
        
        n_account = Account.objects.get_by_user(staff, id=str(self.account.id))
        self.assertEqual(self.account, n_account)

        no_access_account = Account.objects.create_by_user(su, name='TestNoAccess')
        with self.assertRaises(AppException):
            Account.objects.get_by_user(staff, str(no_access_account.id))

        with self.assertRaises(AppException):
            Account.objects.get_by_user(staff, name="TestNoAccess")

        staff_accounts = Account.objects.find_by_user(staff)
        self.assertEqual(staff_accounts.count(), 2)

        staff_accounts = Account.objects.find_by_user(staff, name="TestAcctACL")
        self.assertEqual(staff_accounts.count(), 1)
        self.assertEqual(staff_accounts[0], account)  

        # Superuser should see all accounts
        num_acc = Account.objects.count()      
        n_account = Account.objects.find_by_user(su)
        self.assertEqual(n_account.count(), num_acc)

        # Superuser should be able to get an account they may not be assigned to
        n_account = Account.objects.get_by_user(su, str(self.account.id))
        self.assertTrue(n_account is not None)
        self.assertTrue(str(n_account.id) not in su.accounts)

        # Delete account via superuser
        Account.objects.remove_by_user(su, name="TestAcctACL")

        with self.assertRaises(Account.DoesNotExist):
            Account.objects.get(name="TestAcctACL")

        with self.assertRaises(AppException):
            Account.objects.remove_by_user(staff, name="TestNoAccess")

    def test_account_status(self):
        '''Test the various account status states'''

        # A normal account should be active
        account = Account.objects.create_by_user(self.user, name="TestAcctStatus")
        self.assertTrue(account.is_active)

        # Expire the account
        yesterday = dt.datetime.now() - dt.timedelta(days=1)
        account.end_date = yesterday
        account.save()

        self.assertFalse(account.is_active)

        # TODO Add a state to indicate Volume Thresholding status


class AccountPostsVolumeNotificationsTest(AccountTest):

    def test_accounts_threshold(self):
        params = {'name':  'TestAcctPackage1',
                  'package': 'Bronze'}
        #print 'starting test test_accounts_threshold'
        account = Account.objects.create_by_user(self.user, **params)
        self.user._set_current_account(account)

        # Check threshold sent flags on the account
        self.assertFalse(account.is_threshold_warning_sent)
        self.assertFalse(account.is_threshold_surpassed_sent)

        account.set_threshold_warning(THRESHOLD_WARNING)
        self.assertTrue(account.is_threshold_warning_sent)

        account.set_threshold_warning(THRESHOLD_SURPASSED_WARNING)
        self.assertTrue(account.is_threshold_surpassed_sent)

        # Clear the threshold warnings
        account.clear_threshold_warnings()
        self.assertFalse(account.is_threshold_warning_sent)
        self.assertFalse(account.is_threshold_surpassed_sent)

        # Alter the pricing package volume threshold limit
        self.assertEqual(account.package.name, 'Bronze')
        volume_limit = 10
        account.package.volume = volume_limit
        account.package.save()

        #Create a channel for publishing posts
        channel = TwitterChannel.objects.create_by_user(self.user,
                                                        title='TestChannel2',
                                                        intention_types=SA_TYPES)
        channel.account = account
        channel.save()
        #print 'The new account create is ' + str(account)
        #print 'Current channel account is ' + str(account)
        self.assertEqual(channel.account, account)
        # Check the warning at the appropriate amount
        first_limit_posts = account.volume_warning_limit + 1

        # Create enough posts to trigger the warning
        mail = Mail(app)
        with app.test_request_context():
            with mail.record_messages() as outbox:
                params = {'channels': [str(channel.id)],
                          'content': "Test Content"}
                for n in range(first_limit_posts):
                    print 'Sending post number ' + str(n)
                    self._create_db_post(**params)

                self.assertTrue(len(outbox) > 0)
                self.assertTrue(self.user.email in outbox[0].recipients)
        account.reload()
        #print 'Thresold warning for account is ' + str(account.threshold_warning)
        #print 'Thresold warning sent flag for account is ' + str(account.is_threshold_warning_sent)
        self.assertTrue(account.is_threshold_warning_sent)

        # Create the rest to hit the volume limit
        mail = Mail(app)
        with app.test_request_context():
            with mail.record_messages() as outbox:
                for x in range(volume_limit - first_limit_posts):
                    #print 'Sending post number ' + str(n)
                    self._create_db_post(
                        channels=[channel],
                        content = "Test Content")

                # Make sure admin user gets the surpassed message email
                self.assertTrue(len(outbox) > 0)
                self.assertTrue(self.user.email in outbox[0].recipients)
        #print 'Thresold warning for account is ' + str(account.threshold_warning)
        #print 'Thresold surpassed sent flag for account is ' + str(account.is_threshold_surpassed_sent)
        account.reload()
        self.assertTrue(account.is_threshold_surpassed_sent)

    def test_daily_threshold_notification(self):
        account = self.account
        daily_post_limit = 2
        notification = account.daily_post_volume_notification
        notification.posts_limit = daily_post_limit
        notification.alert_emails = ['notified_1@test.local', 'notified_2@test.local']
        app.config['DAILY_VOLUME_ALERT_RECIPIENTS'] = ['admin@test.local'] + notification.alert_emails[:1]
        expected_notified_emails = set(notification.alert_emails + app.config['DAILY_VOLUME_ALERT_RECIPIENTS'])

        account.update(_daily_post_volume_notification=notification)

        channel = TwitterChannel.objects.create_by_user(self.user,
                                                        account=account,
                                                        title='TestChannel2',
                                                        intention_types=SA_TYPES)
        # from solariat_bottle.tests.base import ProcessPool
        # pool = ProcessPool(proc_num=3)
        #
        def create_post(params):
            assert isinstance(params, dict), params
            # with open('test.sending.txt.log', 'a') as log:
            #     log.write(str(params))
            #     log.write('\n\n')
            return self._create_db_post(**params)

        mail = Mail(app)
        with app.test_request_context():
            recipients = []
            with mail.record_messages() as outbox:
                map(create_post, (
                    dict(channels=[channel],
                         content="Test Content %s" % x)
                    for x in range(2*daily_post_limit + 1)))

                self.assertEqual(len(outbox), len(expected_notified_emails),
                                 msg="Expected %s emails. Got %s." % (len(expected_notified_emails), len(outbox)))
                for msg in outbox:
                    recipients.extend(msg.recipients)
                self.assertEqual(set(expected_notified_emails), set(recipients))

            account.reload()
            self.assertEqual(account.daily_post_volume_notification.status, account.daily_post_volume_notification.IDLE)
            with mail.record_messages() as outbox:
                for _ in range(daily_post_limit + 1):
                    self._create_db_post(channels=[channel],
                                         content="Extra post")
                self.assertFalse(outbox, msg="Expected no emails. Got %s." % len(outbox))


class AccountActionsTest(UICase, SmartTagsTestHelper):

    def setUp(self):
        UICase.setUp(self)
        self.login()

        self.na_acct = Account.objects.create(name="NotAccessible")

        self.accounts = [
            Account.objects.create(name="Acct1"),
            Account.objects.create(name="Acct2")
        ]

        for a in self.accounts:
            a.add_user(self.user)
        self.user.current_account = self.accounts[0]

        self.su = self._create_db_user(email="superuser@all.com", roles=[STAFF])
        self.su.is_superuser = True
        self.su.save()

    def _call_api(self, url, method="POST", assert_false=False, *args, **kwargs):
        '''Helper function to call and check on json API calls'''
        try:
            func = getattr(self.client, method.lower())
        except AttributeError:
            self.fail("Invalid API method: {}".format(method))
        
        if method.upper() in set(["POST", "PUT"]):
            kwargs = {'data': json.dumps(kwargs)}

        kwargs['content_type'] = 'application/json'
        resp = func(url, *args, **kwargs)
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        
        if assert_false:
            self.assertFalse(resp['ok'], resp)
        else:
            self.assertTrue(resp['ok'], resp.get('error'))

        return resp

    def test_su_has_all_accounts(self):
        self.assertEqual(len(self.su.available_accounts), Account.objects.count())

    def test_account_names(self):
        """Account names have some limitations

        https://github.com/solariat/tango/issues/3274
        """

        # can not be blank
        with self.assertRaises(AppException):
            Account.objects.create(name='')
        with self.assertRaises(AppException):
            Account.objects.create(name='   \n')

        #  -- Removed via #3885 --
        # # can not contain spaces
        # with self.assertRaises(AppException):
        #     Account.objects.create(name='name with spaces')

        #  -- Removed via #3675 --
        # should not be longer than 20 characters.
        # with self.assertRaises(AppException):
        #    Account.objects.create(name='123456789012345678901')

        #  -- Removed via #3885 --
        # # should only contain numbers, alpha characters or dashes
        # Account.objects.create(name='ok-name')
        # Account.objects.create(name='ok-name-2')

    def test_create_reserver_account_name(self):
        try:
            Account.objects.create(name=Account.NO_ACCOUNT)
            self.fail("Should not be allowed to create account named %s" % Account.NO_ACCOUNT)
        except Account.ReservedNameException:
            pass

    def test_get_current_account(self):
        resp = self._call_api('/account/json', method="GET")
        
        account = resp['account']
        self.assertTrue(account is not None)

        self.login(self.su)
        resp = self._call_api('/account/json', method="GET")
        
        account = resp['account']
        self.assertTrue(account is not None)

    def test_set_current_account(self):
        #test corrupted post
        for data in [{}, {'account_id': 'No such account id'}]:
            resp = self._call_api(
                '/configure/account/json',
                assert_false=True,
                **data)

        #test set current account for non-privileged user
        data = {'account_id': str(self.accounts[1].id)}
        resp = self._call_api('/configure/account/json', **data)

        self.user.reload()
        self.assertEqual(self.user.current_account.id, self.accounts[1].id)

        #test can't set account that user has no access to
        self.assertFalse(self.na_acct.id in self.user.accounts)
        data = {'account_id': str(self.na_acct.id)}
        resp = self._call_api('/configure/account/json', assert_false=True, **data)

        self.user.reload()
        self.assertEqual(self.user.current_account.id, self.accounts[1].id)

        #test set current account by superuser for other user
        self.login(self.su.email)
        data = {'account_id': str(self.accounts[0].id), 'email': self.user.email}
        resp = self._call_api('/configure/account/json', **data)

        self.user.reload()
        self.assertEqual(self.user.current_account.id, self.accounts[0].id)

        #test that superuser can set account that user has no access to
        data = {'account_id': str(self.na_acct.id), 'email': self.user.email}
        resp = self._call_api('/configure/account/json', **data)

        self.user.reload()
        self.assertEqual(self.user.current_account.id, self.na_acct.id)

    def test_account_create_empty_end_date(self):
        params = {'name': 'TestAcct', 'account_type': 'Native', 'package': 'Gold', 'end_date': ''}
        self.login(user=self.su)
        resp = self._call_api('/accounts/json', **params)
        self.assertTrue('account' in resp)

    def test_account_create_and_update(self):
        '''Test the various /configure/ endpoints for accounts'''

        # Create new accounts one an internal account and another a paid package account
        params = {'name': 'TestAcct', 'account_type': 'Native', 'package':'Gold'}
        self.user.update(user_roles=[])
        resp = self._call_api('/accounts/json', assert_false=True, **params)

        # Log in as staff user and try again
        self.login(user=self.su)
        resp = self._call_api('/accounts/json', **params)

        self.assertTrue('account' in resp)
        account = resp['account']
        account_id = account['id']

        self.assertEqual(account['account_type'], 'Native')
        self.assertEqual(account['package'], 'Gold')

        # Update the account's pay package
        params = {'accountId': account_id, 
                  'accountName':  'TestAcct',
                  'accountType': 'Native',
                  'pricingPackage': 'Bronze'}
        resp = self._call_api('/configure/account_update/json', **params)

        self.assertTrue('data' in resp)
        self.assertEqual(resp['data'], {})

        # Test with a specified end_date parameter
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        tomorrow_fmt = tomorrow.strftime('%m/%d/%Y')
        params = {'name': 'TestExpiringAcct', 
                  'package':'Bronze', 
                  'end_date': tomorrow_fmt
                }

        resp = self._call_api('/accounts/json', **params)
        self.assertTrue(resp['account']['end_date'], datetime_to_timestamp_ms(tomorrow))

        # Test GET
        params = {'accountId': account_id}

        resp = self._call_api('/configure/account_update/json?accountId={}'.format(account_id),
                               method="GET")
        self.assertTrue('data' in resp)

        self.assertEqual(resp['data']['accountType'], 'Native')
        self.assertEqual(resp['data']['pricingPackage'], 'Bronze')

        # Update via the PUT request
        note = "Test Note\nSecond Line"
        params = {'id':  account_id,
                  'name': 'TestAcct', 
                  'account_type': 'Native',
                  'package': 'Gold',
                  'notes':  note}
        resp = self._call_api('/accounts/json', method="PUT", **params)

        self.assertTrue('account' in resp)
        account = resp['account']
        self.assertEqual(account['package'], 'Gold')
        self.assertEqual(account['notes'], note)

        params = {"name": "TestSkunk", "account_type": "Skunkworks"}
        resp = self._call_api('/accounts/json', **params)
        self.assertTrue('account' in resp)
        account = resp['account']
        self.assertEqual(account['account_type'], "Skunkworks")
        self.assertEqual(account['package'], 'Internal')

        #  Account delete
        #  Switch user account
        self.su.current_account = self.accounts[0]
        self.su.save()

        resp = self._call_api('/accounts/json?id={}'.format(account_id), method="DELETE")

        resp = self._call_api('/account/json?name=TestAcct', method="GET")
        # If account is not present, return the current account
        self.assertEqual(resp['account']['name'], 'Acct1')

    def test_delete_account(self):
        # case #1:
        # user tries to delete account with channels
        self.login(self.su.email)
        account = self.accounts[0]
        Channel.objects.create(account=account, title='testChannel')
        resp = self._call_api(
            '/accounts/json?id=' + str(account.id),
            assert_false=True,
            method="DELETE")
        self.assertTrue(resp['error'].startswith("You can not delete an account that contains channels."))

        # case #2:
        # user tries to delete account with no channels but some users
        staff = User.objects.create(account=account, user_roles=[STAFF], email='staff@test.test')
        acc2 = Account.objects.create(name='acc2')
        acc2.add_user(staff)
        staff.account = account
        staff.save()

        staff_users = [u for u in account.get_users() if u.is_staff]
        self.assertTrue(staff_users)

        staff_user_ids = [u.id for u in staff_users]

        Channel.objects.remove(account=account)
        resp = self._call_api(
            '/accounts/json?id=' + str(account.id),
            method="DELETE")
        
        # staff users preserved
        self.assertEqual(set(staff_users), set(list(User.objects(id__in=staff_user_ids))))

        staff.reload()
        self.assertEqual(staff.account, acc2)

    def test_delete_account_with_tags(self):
        self.login(self.su.email)
        account = self.accounts[0]
        chan1 = TwitterServiceChannel.objects.create(account=account, title='testChannel')
        self._create_smart_tag(chan1.inbound_channel, "Tag1")
        initial_count = Account.objects.count()
        resp = self._call_api('/accounts/json?id=' + str(account.id),
                              assert_false=True,
                              method="DELETE")
        self.assertTrue(resp['error'].startswith("You can not delete an account that contains channels."))
        self.assertTrue(Account.objects.count() == initial_count)
        chan1.archive()
        resp = self._call_api('/accounts/json?id=' + str(account.id),
                              assert_false=False,
                              method="DELETE")
        self.assertTrue(resp['ok'])
        self.assertTrue(Account.objects.count() == initial_count - 1)

    def test_account_admins(self):
        '''Ensure account admins are displayed properly with the appropriate logic'''
        self.login(user=self.su)
    
        resp = self._call_api('/accounts/json', name='TestAcctAdmins')
        self.assertTrue('account' in resp)
        account = resp['account']
        self.assertTrue('admin' in account)
        self.assertEqual(account['admin']['email'], None)

        self.login(user=self.user)
        resp = self._call_api('/account/json?name=TestAcct', method="GET")
        self.assertTrue('account' in resp)
        account = resp['account']
        self.assertTrue('admin' in account)
        admin = account['admin']
        self.assertTrue('email' in admin)
        self.assertEqual(admin['email'], self.user.email)

    def test_account_status(self):
        account = Account.objects.create(name="TestStatusAcct")
        admin_user = self._create_db_user(email="admin@solariat.com", 
                                          password='12345', 
                                          roles=[ADMIN],
                                          account=account)
        admin_user.current_account = account
        # User should be able to login and ping the current account
        self.login(user=admin_user)

        resp = self._call_api('/account/json', method="GET")
        self.assertTrue('account' in resp)
        ret_acc = resp['account']
        self.assertTrue('is_active' in ret_acc)
        self.assertTrue(ret_acc['is_active'])

        self.assertEqual(ret_acc['id'], str(account.id))

        # Make account expired
        account.end_date = yesterday
        account.save()

        self.logout()
        resp = self.login(user=admin_user)
        self.assertEqual(resp.status_code, 401)

    def test_gse_api_key(self):
        # gse_api_key should be auto-created for existing GSE accounts
        n = ApplicationToken.objects.count()
        acct = Account.objects.create(name='TestAcct1', account_type='GSE')
        self.assertIsNone(acct._gse_api_key)
        acct.gse_api_key  # force lazy app token creation
        self.assertIsNone(acct._gse_api_key.creator)
        self.assertEqual(acct._gse_api_key.app_key, acct.gse_api_key)
        self.assertEqual(ApplicationToken.objects.count(), n + 1)
        self.assertEqual(ApplicationToken.objects.get(app_key=acct.gse_api_key), acct._gse_api_key)

        # gse_api_key should be created for new GSE accounts
        self.login(user=self.su)
        params = {'name': 'TestAcct2', 'account_type': 'GSE', 'package': 'Gold'}
        resp = self._call_api('/accounts/json', **params)
        acct = Account.objects.get(resp['account']['id'])
        self.assertEqual(ApplicationToken.objects.count(), n + 2)
        self.assertTrue(acct._gse_api_key)
        self.assertEqual(acct._gse_api_key.creator, self.su)
        self.assertEqual(acct._gse_api_key.app_key, acct.gse_api_key)


class AccountStats(MainCase, SmartTagsTestHelper):

    def setUp(self):
        MainCase.setUp(self)
        self.account = Account(name="Solariat Test")
        self.account.save()
        self.user.account = self.account
        self.user.save()
        self.account.add_perm(self.user)
        self.channel.account = self.account
        self.channel.save()
        self._create_smart_tag(self.channel, 'laptop', status='Active'),

    def test_single_post_added(self):
        """
        Count of posts for account should increase by one when a post is added.

        This is for issue #2007
        https://github.com/solariat/tango/issues/2007

        Previously when smart tag channel was in the account
        number of posts was aggregated in it too.
        """
        content = '@screen_name I need a laptop'
        self._create_db_post(content)
        self._create_smart_tag(self.channel, 'tag1', status='Active'),
        # just one post is added
        self.assertEqual(
            account_stats(self.account, self.user).get('number_of_posts'),
            1)

    def test_account_stats(self):
        """Account stats should not sum up stats of
        deleted (archived) channels"""
        content = '@screen_name I need a laptop'
        channels_num = 4
        archived_channels_num = 3  # should be <= channels_num
        posts_per_channel = 1

        channels = [
            Channel.objects.create_by_user(self.user, account=self.account,
                                           title='Channel#%d' % _)
            for _ in range(channels_num)]

        posts = [self._create_db_post(content=content + " #%d" % _, channel=channel)
                 for channel in channels
                 for _ in range(posts_per_channel)]

        self.assertEqual(
            account_stats(self.account, self.user).get('number_of_posts'),
            channels_num * posts_per_channel)

        from solariat_bottle.commands.configure import DeleteChannel
        DeleteChannel(channels=channels[:archived_channels_num]).update_state(
            self.user)

        self.assertEqual(
            account_stats(self.account, self.user).get('number_of_posts'),
            (channels_num - archived_channels_num) * posts_per_channel)

        self.assertEqual(
            all_account_stats(self.account, self.user).get('number_of_posts'),
            channels_num * posts_per_channel)
