from datetime import datetime
import json

import mock

from solariat_bottle.configurable_apps import APP_GSA
from ..db.roles           import AGENT
from ..db.account         import Account
from ..db.channel.twitter import TwitterTestDispatchChannel, TwitterServiceChannel

from ..db.user_profiles.user_profile import UserProfile
from ..settings        import AppException
from .base import UICase, UIMixin, fake_twitter_url


class FakeDatetime(datetime):
    @classmethod
    def utcnow(cls):
        return cls(2010, 1, 1)


class DispatchingChannelMixin(object):
    def _setup_dispatching_channel(self):
        self.dispatching_channel = TwitterTestDispatchChannel.objects.create(
            title="Outbound",
            account=self.sc.account)

        # has to be in self.o.usernames
        self.dispatching_channel.twitter_handle = 'solariat'
        self.dispatching_channel.twitter_handle_data = {
            'profile': {'id_str': 'solariat', 'screen_name': 'solariat'},
            'hash': hash('NoneNone') & (1 << 8)
        }
        self.dispatching_channel.save()
        self.dispatching_channel.on_active()
        self.sc.account.outbound_channels = {'Twitter': str(self.dispatching_channel.id)}
        self.sc.account.save()


class AgentCase(UICase, UIMixin, DispatchingChannelMixin):
    def setUp(self):
        super(UICase, self).setUp()

        self.account = Account.objects.get_or_create(name="TestAccount")
        self.account.update(selected_app=APP_GSA)
        self.user.account = self.account
        self.user.save()

        self.sc = TwitterServiceChannel.objects.get_or_create(
            title="TwitterServiceChannel",
            account=self.account)
        self.sc.add_perm(self.user)

        self.i = self.sc.inbound_channel
        self.o = self.sc.outbound_channel
        self.o.usernames = ['solariat']
        self.o.save()


        # customers
        self.customer = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        self.url = fake_twitter_url('customer')

        self._setup_dispatching_channel()

    def _create_agent(self, email, signature, screen_name, roles=[AGENT]):
        self.agent_password = '1'
        user = self._create_db_user(email=email, password=self.agent_password, account=self.account, roles=roles)
        user.account = self.account
        user.signature = signature
        if screen_name:
            user.user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        user.outbound_channels = {'Twitter': str(self.dispatching_channel.id)}
        user.save()
        self.sc.add_agent(user)
        self.sc.add_perm(user)
        self.i.add_perm(user)
        self.o.add_perm(user)
        # self.matchable.add_perm(user)
        self.dispatching_channel.add_perm(user)
        return user

    def _create_and_login_agent(self, email, signature, screen_name):
        user = self._create_agent(email, signature, screen_name)
        self.login(email=email, password=self.agent_password, user=user)
        return user


    def test_no_pending_for_second_agent(self):
        """
        Test that second agent does not have a post
        which is already in pendings for another user.

        Create a post.
        Create and login Agent 1.
        Check that he has the post in Pending.
        Create and login Agent 2.
        Check that he does not have the post in Pending.
        """

        post = self._create_tweet('@solariat I need a laptop',
                                  channel=self.i,
                                  user_profile=self.customer)

        agent1 = self._create_and_login_agent(
            email='agent1@test.test',
            signature='A1',
            screen_name='@agent1')


        agent2 = self._create_and_login_agent(
            email='agent2@test.test',
            signature='A2',
            screen_name='@agent2')


        del post, agent1, agent2

    @mock.patch('solariat.utils.timeslot.datetime', FakeDatetime)
    def test_pending_for_second_agent_in_future(self):
        """
        Tests that after some time responses are re-assigned to the agent
        who loads pending.
        """

        # we create agents first because the matchable needs to be shared
        # before the post is created

        agent1 = self._create_agent(
            email='agent1@test.test',
            signature='A1',
            screen_name='@agent1')

        agent2 = self._create_agent(
            email='agent2@test.test',
            signature='A2',
            screen_name='@agent2')

        post = self._create_tweet('@solariat I need a laptop',
                                  channel=self.i,
                                  user_profile=self.customer)

        # setting fake time
        FakeDatetime.utcnow = classmethod(lambda cls: datetime(2010, 1, 1))

        self.login(email='agent1@test.test', password=self.agent_password, user=agent1)

        # setting 1 year in the future
        FakeDatetime.utcnow = classmethod(lambda cls: datetime(2011, 1, 1))

        # agent 2 loads this post to his pending
        self.login(email='agent2@test.test', password=self.agent_password, user=agent2)

        # agent 1 cannot reply to response because it was assigned to 2



    def test_same_signature(self):
        self._create_agent(
            email='agent1@test.test',
            signature='A1',
            screen_name='@agent1')

        # error creating agent with the same signature
        with self.assertRaises(AppException):
            self._create_agent(
                email='agent2@test.test',
                signature='A1',
                screen_name='@agent2')
