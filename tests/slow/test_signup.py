import json

from solariat.mail import Mail

from ..base import UICaseSimple
from solariat_bottle.app import app
from solariat_bottle.db.account import Account
from solariat_bottle.db.roles import ADMIN, STAFF
from solariat_bottle.db.user import ValidationToken
from solariat_bottle.views.account import _create_trial


class SignupTestCase(UICaseSimple):

    def test_happy_flow(self):
        acc = Account.objects.create(name="TEST_VALIDATION")
        staff_user = self._create_db_user(email="staff@solariat.com", 
                                          password="12345", 
                                          roles=[STAFF], 
                                          account=acc)
        params = {'name': 'TestTrial'}
        resp, trial = _create_trial(staff_user, params)
        self.assertTrue(resp)
        new_user = self._create_db_user(email='nobody1@solariat.com',
                                        password='12345',
                                        roles=[ADMIN], account=trial)
        token = ValidationToken.objects.create_by_user(staff_user, target=new_user)

        params = {'channel': {'title': 'test',
                              'keywords': ['test'],
                              'handles': ['test'],
                              'skipwords': ['test']},
                  'password': 'password',
                  'password_confirm': 'password'}
        mail = Mail(app)
        with mail.record_messages() as outbox:
            # First mimic mail click to signup page to store token in session
            self.client.get("/signup?validation_token=" + str(token.digest))
            resp = self.client.post("/signup", data=json.dumps(params), content_type="application/json")
            self.assertEqual(resp.status_code, 200)  # Redirect to inbox
            self.assertTrue(len(outbox) == 2)
            self.assertEqual(outbox[0].recipients, [staff_user.email] + app.config['ONBOARDING_ADMIN_LIST'])

            self.assertEqual(outbox[0].sender, "Genesys Social Analytics Notification <Notification-Only--Do-Not-Reply@" + app.config['HOST_DOMAIN'].split('//')[-1] + '>')
            self.assertEqual(outbox[0].subject, "Customer just signed up! - Genesys Social Analytics")
            self.assertEqual(outbox[1].subject, "A channel has been created for a trial account you created")

        # Now test that if we attempt same thing again, token is expired
        resp = self.client.get("/signup?validation_token=" + str(token.digest))
        from solariat_bottle.views.signup import ERROR_VALIDATION_TOKEN

        self.assertTrue(ERROR_VALIDATION_TOKEN in resp.data)
        resp = self.client.post("/signup", data=json.dumps(params), content_type="application/json")
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

    def test_no_validation_token(self):
        params = {'channel': {'title': 'test',
                              'keywords': 'test',
                              'handles': 'test'},
                  'password': 'password',
                  'password_confirm': 'password'}
        resp = self.client.post("/signup", data=json.dumps(params), content_type="application/json")
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])

    def _create_trial(self, params):
        resp = self.client.post("/trials/json", data=json.dumps(params), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        return json.loads(resp.data)

    def test_create_trial(self):
        # Check other admins cannot create a trial
        acc = Account.objects.create(name="TEST_VALIDATION")
        new_user = self._create_db_user(email='nobody1@solariat.com',
                                        password='12345',
                                        roles=[ADMIN],
                                        account=acc)
        self.login(user=new_user)
        email = 'test@socialoptimizr.com'
        params = {'email': email,
                  'full_name': 'Bogdan Neacsa',
                  'account_name': ' '}  # account name cannot be empty
        data = self._create_trial(params)
        self.assertFalse(data['ok'])
        self.assertTrue(ValidationToken.objects.count() == 0)
        self.user.user_roles = [ADMIN, STAFF]
        self.user.save()
        self.login(user=self.user)

        data = self._create_trial(params)
        self.assertFalse(data['ok'])

        mail = Mail(app)
        account_name = "Valid-Account"
        with mail.record_messages() as outbox:
            params.update({"account_name": account_name})
            self._create_trial(params)
            self.assertTrue(ValidationToken.objects.count() == 1)
            self.assertEqual(len(outbox), 1)
            self.assertTrue(outbox[0].recipients == [email])
            self.assertEqual(outbox[0].sender, "Genesys Social Analytics Notification <Notification-Only--Do-Not-Reply@" + app.config['HOST_DOMAIN'].split('//')[-1] + '>')
            self.assertEqual(outbox[0].subject, "Twitter Channel Sign-up - Genesys Social Analytics")

        # check account name is unique
        data = self._create_trial(params)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], "Error creating Trial: Account with name '%s' already exists. Please provide another name." % account_name)
        params.update({"account_name": account_name + '1'})
        data = self._create_trial(params)
        self.assertFalse(data['ok'])
        from solariat_bottle.views.trials import ERROR_DUP_USER
        self.assertEqual(data['error'], ERROR_DUP_USER)
