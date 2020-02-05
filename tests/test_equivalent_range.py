""" Test a new algorithm for returning payloads for given post """
import unittest

from solariat_bottle          import settings
from solariat_bottle.settings import get_var

from .base import MainCase

@unittest.skip("Matchable is deprecated")
class EquivalentTest(MainCase):

    def _create_post(self, content):
        "Create post via API"
        return self.do_post('posts', version='v1.2', content=content,
                            channel=self.channel_id)['item']

    def test_matchable_search_limit(self):
        for i in range(10):
            self._create_db_matchable(
                creative='There is some foo in location%i' % i,
                intention_topics=['foo'])

        post = self._create_post('i need some foo')
        self.assertEqual(len(post['matchables']), get_var('MATCHABLE_SEARCH_LIMIT'))

        settings.MATCHABLE_SEARCH_LIMIT = 8
        post = self._create_post('where i can get some foo?')
        self.assertEqual(len(post['matchables']), 8)

    def test_equivalent_range(self):
        # we should get 6 paylods and
        # 3 shuffled with good relevance and 3 ordered with bad relevance

        # This test is deprecated
        return

        settings.EQUIVALENT_RANGE = 0.01

        matchable1 = self._create_db_matchable(
                creative='There you could find laptop bags',
                intention_topics=['laptop'])
        matchable2 = self._create_db_matchable(
                creative='Another place for laptops and bags',
                intention_topics=['laptop'])
        matchable3 = self._create_db_matchable(
                creative='More laptops bags to be had here.',
                intention_topics=['laptop'])

        matchable4 = self._create_db_matchable(
            creative='Computers', intention_topics=['laptop'])

        matchable5 = self._create_db_matchable(
            creative='Bag and laptop', intention_topics=['bag'])
        matchable6 = self._create_db_matchable(
            creative='Foo and bar')
        matchable7 = self._create_db_matchable(
            creative='laptop')

        settings.MATCHABLE_SEARCH_LIMIT = 6
        post = self._create_post('i need a laptop bag')
        matchables = post['matchables']

        self.assertEqual(len(matchables), 6)
        matchable_ids = [x['id'] for x in matchables]

        #scores = [ matchable['relevance'] for matchable in matchables ]
        #self.assertEqual(scores, [])
        well_relevanced = matchable_ids[:4]
        worse_relevanced = matchable_ids[4:]

        self.assertTrue(str(matchable1.id) in well_relevanced)
        self.assertTrue(str(matchable2.id) in well_relevanced)
        self.assertTrue(str(matchable3.id) in well_relevanced)
