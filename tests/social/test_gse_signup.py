from nose.tools import eq_
from solariat_bottle.tests.base import UICaseSimple
from solariat_bottle.db.user import User, ValidationToken
from solariat_bottle.db.account import Account


class TestGSESignup(UICaseSimple):

    def post_signup(self, default, **kw):
        data_dict = {
                "first_name": None,
                "last_name": None,
                "email": None,
                "company_name": None,
                "identification_number": "8.5.2",
        }
        data_dict.update(default)
        res = self._post("/gse/signup", data_dict, **kw)
        print res, data_dict, kw

    def get_default_data(self):
        data = {
                "first_name": "Sujan",
                "last_name": "Shakya",
                "email": "suzan.shakya@gmail.com",
                "company_name": "Genesys Nepal",
        }
        return data

    def test_gse_signup(self):
        data = self.get_default_data()
        self.post_signup(data, expected_result=True)
        eq_(User.objects.count(email=data["email"]), 1)
        eq_(Account.objects.count(name=data["company_name"]), 1)
        user = User.objects.get(email=data["email"])
        eq_(ValidationToken.objects.count(creator=user), 1)

    def test_gse_signup_duplicate_email(self):
        data = self.get_default_data()
        self.post_signup(data)
        # signup with same email but different company_name
        data["company_name"] += "Pvt. Ltd."
        self.post_signup(data, expected_result=False)
        # check new account is not created
        eq_(Account.objects.count(name=data["company_name"]), 0)

    def test_gse_signup_failed_sendmail(self):
        from solariat_bottle.app import MAIL_SENDER
        _default_send_mail = MAIL_SENDER.send

        # mock send_mail to fail and raise
        def bad_send_mail(*arg, **kwarg):
            raise Exception("any random exception due to send_mail")

        # monkey-patch send_mail
        MAIL_SENDER.send = bad_send_mail

        data = self.get_default_data()
        self.post_signup(data, expected_result=False)
        # check no user, account or validation token are created
        eq_(User.objects.count(email=data["email"]), 0)
        eq_(Account.objects.count(name=data["company_name"]), 0)
        eq_(ValidationToken.objects.count(), 0)

        # undo moneky-patch of send_mail
        MAIL_SENDER.send = _default_send_mail

    def test_gse_signup_confirm(self):
        data = self.get_default_data()
        self.post_signup(data)
        user = User.objects.get(email=data["email"])
        token = ValidationToken.objects.get(creator=user)
        eq_(token.is_valid, True)
        res = self._post("/gse/signup/confirm?validation_token=%s" % token.digest, {"password": "random_pw"})
        token.reload()
        eq_(token.is_valid, False)
        eq_(res["redirect_url"], "/gse/signup/success")
