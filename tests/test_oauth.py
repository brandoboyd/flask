import tweepy
from datetime import datetime
import unittest

from ..db.channel.twitter import EnterpriseTwitterChannel as ETC
from ..db.account         import Account
from ..scripts            import set_account_types
from ..utils.oauth        import get_twitter_oauth_handler
from ..tasks.twitter      import tw_normal_reply

from .base import BaseCase


class OAuthTest(BaseCase):

    def setUp(self):
        super(OAuthTest, self).setUp()
        #self.account = self._create_internal_account("TEST")
        self.native_channel = ETC.objects.create(title='Test Twitter Channel', account=self.account)
        self.hs_account = self._create_internal_account('TEST-HS', 'HootSuite')
        self.hs_channel = ETC.objects.create(title='Test Twitter Channel', account=self.hs_account)
        self.sf_account = self._create_internal_account('TEST-SF', 'Salesforce')
        self.sf_channel = ETC.objects.create(title='Test Twitter Channel', account=self.sf_account)
        self.channels   = [self.native_channel, self.hs_channel, self.sf_channel]

    def _create_internal_account(self, name, account_type="Native"):
        return Account.objects.create(name=name, account_type=account_type)

    def test_script(self):
        set_account_types.main('test')

    def test_channel_property(self):
        self.assertFalse(self.native_channel.is_authenticated)

        self.native_channel.access_token_key = ''
        self.assertFalse(self.native_channel.is_authenticated)

        self.native_channel.access_token_key = 'ccc'
        self.assertFalse(self.native_channel.is_authenticated)
        self.native_channel.access_token_secret = 'ddd'
        self.assertTrue(self.native_channel.is_authenticated)

    @unittest.skip("No connection")
    def test_request_token(self):
        auth = get_twitter_oauth_handler(self.native_channel.id, 
                                         callback_url='/twitter_callback/' + 
                                         str(self.native_channel.id))

        
        auth.request_token = auth._get_request_token()
        url = auth._get_oauth_url('authorize')

        req = tweepy.oauth.OAuthRequest.from_token_and_callback(
            token=auth.request_token,
            http_url=url,
            parameters={'force_login': 'true'}
        )
        redirect_url = req.to_url()
        self.assertFalse(redirect_url == "")

    @unittest.skip("No connection")
    def test_tw_send_post(self):
        tasks = []

        # post multiple tweets asynchronously
        for ch in self.channels:
            task = tw_normal_reply.async(ch, "On: %s-%s. I need a potato: %s" % (ch.title, ch.id, datetime.now()))
            tasks.append(task)

        for task in tasks:
            self.assertTrue(task.result() is not None)

