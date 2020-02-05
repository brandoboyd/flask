# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_nlp import sa_labels

from solariat.utils.timeslot import datetime_to_timeslot
from solariat_bottle.db.speech_act      import SpeechActMap, reset_speech_act_keys
from solariat_bottle.db.post.base       import Post
from solariat_bottle.db.channel.twitter import KeywordTrackingChannel
from solariat_bottle.tests.base import MainCase, GhostPost


class SpeechActMapCase(MainCase):

    def setUp(self):
        super(SpeechActMapCase, self).setUp()

        self.speech_acts = [
            dict(
                intention_type_id   = int(sa_labels.NEEDS.oid),
                intention_type_conf = 0.99,
                intention_topics    = ['laptop', 'stickers'],
                content             = 'I need stickers for my laptop',
                )
            ]

        self.post = GhostPost(
            channels    = [self.channel.id],
            content     = 'I need stickers for my laptop',
            speech_acts = self.speech_acts
            )

    def test_properties(self):
        content = 'I need a bike. I like Honda.'
        post = self._create_db_post(content)
        for sam in SpeechActMap.objects():
            self.assertEqual(len(sam.to_dict()['topics']), 2)

    def test_post_creation(self):
        content = 'I need a bike. I like Honda.'
        post = self._create_db_post(content)
        self.assertEqual(
            post.speech_acts[0]['content'],
            'I need a bike.')
        self.assertEqual(
            post.speech_acts[1]['content'],
            ' I like Honda.')

        time_slot = datetime_to_timeslot(post.created, 'hour')

        # single filters
        posts, are_more_posts_available = Post.objects.by_time_point(
            self.channel,
            'bike',
            time_slot,
            status    = SpeechActMap.POTENTIAL,
            intention = sa_labels.NEEDS.oid,
        )

        # verify the result has the right content
        self.assertEqual(len(posts),       1)
        self.assertEqual(posts[0].content, post.content)

        # multiple filters
        posts, are_more_posts_available = Post.objects.by_time_point(
            self.channel,
            ['bike', 'honda'],
            time_slot,
            status = SpeechActMap.POTENTIAL,
            # no explicit intention id means ALL INTENTIONS
        )

        self.assertEqual(len(posts),       1)

    def test_extra_terms(self):
        '''Using extra terms based on keyword data from the channel'''

        ktc = KeywordTrackingChannel.objects.create_by_user(
            self.user,
            title  = 'KeywordTrackingChannel',
            status = 'Active'
        )
        ktc.add_keyword('@hanDLe1')
        ktc.add_keyword('#desperate')
        ktc.add_keyword('honda')

        self.channel = ktc

        content = '@handle1 I need a bike. #despeRate, I like Honda.'
        post = self._create_db_post(content)

        # Expect to see no repetition, and proper handling of case sensitivity. Also
        # expect to see __ALL__ handled
        ''' SKIP BECAUSE NOT USING SPEECH ACT KEYS
        sa_keys = post.speech_act_keys
        self.assertEqual(len(sa_keys), len(set(sa_keys)))
        self.assertEqual(len(sa_keys), 3*3 + 2*3 + 2*3 + 1*3 )
        '''

        # Should be speech act map entries for 2 speech acts.
        sa_keys = reset_speech_act_keys(post)

        # Expectations:
        # * 1st speech act: topic and mention
        # * 2nd speech act: hash tag, and topic
        self.assertEqual(len(sa_keys), 2)

        # Also expect topic tuples to be set correctly
        self.assertEqual( [d['t'] for d in SpeechActMap.objects()[0].topic_tuples],
                          ['@handle1', '@handle1', 'bike', 'bike', 'handle1', 'handle1'])

