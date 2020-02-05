# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import random
import string
from itertools import cycle
import unittest

from solariat_bottle.tests.base import MainCase
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.conversation    import Conversation
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.speech_act   import SpeechActMap


def content_gen(keywords=[]):
    #keywords = ['test', '#test', 'Test', '#teST']
    keyword = cycle(keywords)

    while True:
        content = ''.join(random.choice(string.ascii_letters) for i in xrange(40))
        if not keywords:
            yield content
        else:
            yield "%s %s" % (content, keyword.next())


class ActionabilityCase(MainCase):
    def setUp(self):
        super(ActionabilityCase, self).setUp()
        self.sc = TwitterServiceChannel.objects.create_by_user(
            self.user,
            title='Service Channel')
        self.inbound = self.sc.inbound_channel
        self.outbound = self.sc.outbound_channel
        self.sc.save()
        self.sc.add_keyword('test_keyword')
        self.sc.add_keyword('test')
        self.sc.add_keyword('#test')
        self.sc.add_keyword('car')
        self.sc.add_keyword('@handle')
        self.sc.add_keyword('bank of the west')
        self.sc.add_keyword('Bank of America')
        self.sc.add_keyword('student loan')
        self.sc.add_username('@test')
        self.sc.add_username('@test_another')
        self.customer = UserProfile.objects.upsert('Twitter',
                                                   dict(user_id='1234567',
                                                        user_name='JohnDoe'))

    def make_post(self, content, reset=True):
        if reset:
            for c in Conversation.objects():
                c.delete()

        post = self._create_tweet(
            content=content,
            channel=self.inbound,
            user_profile=self.customer.to_dict()
        )

        return post

    @unittest.skip('Fails for issue 1771 because the tagger does not recognize the keyword as a noun.')
    def test_actionable_on_keyword(self):
        post = self.make_post("I need a test_keyword")
        self.assertEqual(post.get_assignment(self.sc), 'highlighted')

    def test_topic_matching(self):
        for content in [ "I hate #test",
                         "I hate  bank of the west"
                         "I hate  bank of America"
                         "Student Loan Debt: The Importance Of Early Financial Education [INFOGRAPHIC] http://t.co/FIkSQJLGu7"]:
            post = self.make_post(content)
            self.assertTrue(self.sc.match(post))


    def test_mentions(self):
        post = self.make_post("@test This is junk @handle @test_another")
        self.assertEqual(self.sc.mentions(post), ['@test', '@test_another'])
        self.assertEqual(self.sc.addressees(post), ['@test'], self.sc.addressees(post))
        post = self.make_post("@test @test_another What do you think of this?")
        self.assertEqual(self.sc.mentions(post), ['@test', '@test_another'])
        self.assertEqual(self.sc.addressees(post), ['@test', '@test_another'])

    def test_direct(self):
        post = self.make_post("@test This is junk")
        self.assertEqual(Conversation.objects.count(), 1)
        thread = self.sc.upsert_conversation(post)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(thread.service_channel.find_direction(post), "direct")
        self.assertTrue(self.sc.match(post))
        print post.channel_assignments
        self.assertEqual(SpeechActMap.STATUS_MAP[post.channel_assignments[str(self.sc.inbound)]],
                         SpeechActMap.ACTIONABLE)

    def test_individual(self):
        ''' Verify we can pick up if the post is directed at a specific individual
        that is not the brand'''
        post = self.make_post("@anyone_at_all This is junk")
        self.assertEqual(self.sc.find_direction(post), "individual")

    def test_mentioned(self):
        # About the mention
        post = self.make_post("I really hate @test")
        self.assertTrue(self.sc.match(post))

        # Mentioned, but about something else
        post = self.make_post("I really hate my laptop, @test")
        self.assertTrue(self.sc.match(post))

        # Not mentioned, and about something else
        post = self.make_post("I really hate my laptop")
        self.assertFalse(self.sc.match(post))

        # Not mentioned, but actionale about a keyword
        post = self.make_post("I need a car")
        self.assertTrue(self.sc.match(post))


    def test_already_actionable(self):
        '''
        Changing the semantics of this. The post should be individually
        judged for actionability.
        '''
        # About the mention
        post = self.make_post("I really hate @test")
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertTrue(self.sc.match(post))

        post = self.make_post("This is bogus")
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertFalse(self.sc.match(post))

    def test_direct_keyword(self):
        #posts started with a keyword that is a twitter handle are actionable
        post = self.make_post("@handle This is junk")
        self.assertTrue(self.sc.match(post))


    def test_no_learning(self):
        '''
        Make sure that if learning is disabled, it does the right thing.
        '''

        self.inbound.adaptive_learning_enabled = False
        self.inbound.save()
        post = self.make_post("I need a car")
        self.assertEqual(post.get_assignment(self.sc), 'highlighted')

        post = self.make_post("I need a SOMEFOO")
        self.assertEqual(post.get_assignment(self.sc), 'discarded')
