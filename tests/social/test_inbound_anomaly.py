#!/usr/bin/env python2.7
from solariat.tests.base import LoggerInterceptor

from solariat_bottle.db.channel.twitter import (
    TwitterServiceChannel, TwitterTestDispatchChannel)
from solariat_bottle.db.user_profiles.user_profile import UserProfile

from solariat_bottle.tests.base import MainCase, fake_twitter_url


class ChannelConfigureTestCase(MainCase):

    def make_dispatch_channel(self, title, twitter_handle, user=None):
        if user is None:
            user = self.user
        dispatch_channel = TwitterTestDispatchChannel.objects.create_by_user(user, title=title,
                                                                             review_outbound=False,
                                                                             account=self.account)
        dispatch_channel.add_perm(user)
        dispatch_channel.twitter_handle = twitter_handle
        dispatch_channel.on_active()
        dispatch_channel.save()
        dispatch_channel.account.add_perm(user)
        return dispatch_channel

    def make_service_channel(self, title, twitter_handles, user=None):
        if user == None:
            user = self.user

        sc = TwitterServiceChannel.objects.create_by_user(
            user,
            account=self.account,
            title=title)
        sc.outbound_channel.usernames = twitter_handles
        sc.outbound_channel.save()
        return sc

    def setUp(self):
        """ Just the bare essentials - an account """
        MainCase.setUp(self)
        #self.account = Account.objects.get_or_create(name='Test')
        self.account = self.user.account
        self.account.add_user(self.user)

    def _post_response(self, resp, matchable):
        from ..commands.engage import handle_post_response
        handle_post_response(True, self.user, resp, resp.post.id or resp.latest_post.id, matchable)

    def test_multi_agent_scenario(self):
        # two inbound channels for an account
        # one is with two brands (brand1, brand2), another with one (brand1).
        sc1 = self.make_service_channel("SC1", ['brand1', 'brand2'])
        # sc2
        sc2 = self.make_service_channel("SC2", ['brand1'])
        # Create outbound channel with brand1
        # dc
        self.make_dispatch_channel("DC", 'brand1', self.user)
        # Create a post to brand2
        screen_name = 'Customer'
        user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        user_brand = UserProfile.objects.upsert('Twitter', dict(screen_name='brand1'))
        url = fake_twitter_url(screen_name)
        post = self._create_db_post(
            channel=sc1.inbound_channel,
            content="@brand2 I need a laptop",
            demand_matchables=True,
            url=url,
            user_profile=user_profile)

        
        # Reply to that post
        # with LoggerInterceptor() as logs:
        reply = self._create_tweet(user_profile=user_brand,
                                   channels=[sc1.outbound_channel, sc2.outbound_channel],
                                   content="Reply to inbound post about laptop",
                                   in_reply_to=post)
        # warning_message = "Post %s channels=%s is not from service channel %s(%s): inbound=%s, outbound=%s" % (
        #     post, map(str, post.channels), sc2, sc2.title, sc2.inbound, sc2.outbound)
        # for entry in logs:
        #     if entry.message == warning_message:
        #         self.assertEqual(entry.levelname, 'WARNING')
        #         break
        # else:
        #     self.fail("Did not find " + warning_message + " in logs " + str([l.message for l in logs]))
        post.reload()
        self.assertEqual(post.get_assignment(sc1.inbound_channel), 'replied')
        self.assertEqual(post.get_assignment(sc2.inbound_channel), None)
