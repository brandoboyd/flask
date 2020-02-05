from solariat_bottle.tests.base import MainCase
from solariat_nlp.scoring import get_post_matchable_relevance
from solariat_nlp.analytics import distances
from solariat_nlp import sa_labels


import unittest

@unittest.skip('I would lke to get this working. But the changes I planned break the ranking model in NLP')
class MatchingTopics(MainCase):

    def setUp(self):
        super(MatchingTopics, self).setUp()

        # Set up matchables with extending topic n-grams
        self.m1 = self._create_db_matchable(creative='Try our bag')
        self.m2 = self._create_db_matchable(creative='Try our laptop bag')
        self.m3 = self._create_db_matchable(creative='Try our cheap laptop bag')

    def test_longer_ngrams_preference(self):
        '''
        Want to verify that if we extract an n-gram and match it with greater
        length matches, we get better scores.
        '''

        # Match on the tri-gram
        post = self._create_db_post(content='I need a cheap laptop bag',
                                    demand_matchables=True)

        matchables  = post.to_dict()['matchables']
        result_text = [ m['creative'] for m in matchables ]
        scores      = [ m['relevance'] for m in matchables ]


        self.assertEqual(len(set(scores)), 3, scores)

        self.assertEqual(result_text, [
                'Try our cheap laptop bag',
                'Try our laptop bag',
                'Try our bag'])


    def test_shorter_ngram_preference(self):
        # Match on the uni-gram
        post = self._create_db_post(content='I need a bag',
                                    demand_matchables=True)

        # Ensure scores differ
        matchables = post.to_dict()['matchables']
        scores = [m['relevance'] for m in matchables]
        result_text = [ m['creative'] for m in matchables]

        print result_text

        for m in matchables:
            print m['creative'], m['intention_topics']

        self.assertEqual(len(set(scores)), 3, scores)

        # Ensure order is correct
        self.assertEqual(result_text, [
                'Try our bag',
                'Try our laptop bag',
                'Try our cheap laptop bag' ])



    def test_relevance_with_default_case(self):
        post = self._create_db_post(content='I need a cheap laptop bag',
                                    demand_matchables=True)

        match = post.to_dict()['matchables'][0]
        self.assertTrue(match['relevance'] > 0.75, match['relevance'])

@unittest.skip("Matchables are depricated")
class RelevanceCase(MainCase):
    def get_matchable(self, post):
        payload = post._get_matchable_dicts()[0][0]
        return payload

    def test_relevance(self):
        self._create_db_matchable(creative='there is some foo')
        post = self._create_db_post(content='i need some foo',
                                    demand_matchables=True)
        payload = self.get_matchable(post)
        relevance = get_post_matchable_relevance(post, payload)
        self.assertTrue(relevance > 0)

    def test_laptop_review(self):
        self._create_db_matchable(creative='For great laptop reviews see foo.com',
                                  intention_topics=['laptop'])
        post = self._create_db_post(content='I need a laptop',
                                    demand_matchables=True)
        payload = self.get_matchable(post)
        relevance = get_post_matchable_relevance(post, payload)
        self.assertTrue(relevance > 0.85)

    def test_laptop_wrong_intention(self):
        self._create_db_matchable(creative='For great laptop reviews see foo.com',
                                  intention_topics=['laptop'],
                                  intention_types=[sa_labels.PROBLEM.title])

        try:
            self._create_db_post(content='I need a laptop',
                                        demand_matchables=True)
            self.assertTrue(False)
        except:
            pass

    def test_laptop_wrong_topic(self):
        self._create_db_matchable(creative='For great iPad and laptop reviews see foo.com',
                                  intention_topics=['ipad'])
        post = self._create_db_post(content='I need a laptop',
                                    demand_matchables=True)
        payload = self.get_matchable(post)
        relevance = get_post_matchable_relevance(post, payload)
        self.assertTrue(relevance < 0.20)
 
    def test_matching_error(self):
        content="it looks like the XBOX 360 does not support Upstream :-( All I'm getting is a 'Still loading...' screen. <Fucking hell!!!>"
        self._create_db_matchable(creative='',
                                  intention_topics=['xbox 360', 'xbox', 'upstream'],
                                  intention_types=[sa_labels.PROBLEM.title])
        post = self._create_db_post(content=content,
                                    demand_matchables=True)
        payload = self.get_matchable(post)
        relevance = get_post_matchable_relevance(post, payload)
        self.assertTrue(relevance >= 0.3, relevance)

    def test_wells_1(self):
        self._create_db_matchable(creative='You can find links to scholarship sites in this discussion in the Wells Fargo Community. https://www.wellsfargocommunity.com/thread/2082?tstart=120',
                                  intention_topics=['scholarship'],
                                  intention_types=[sa_labels.NEEDS.title]
                                  )
        post = self._create_db_post(content="Have gotten it down to 4 colleges I'm applying too. Man I hope I get a scholarship as well.",
                                    demand_matchables=True)
        payload = self.get_matchable(post)
        relevance = get_post_matchable_relevance(post, payload)
        self.assertTrue(relevance >= 0.65, relevance)

    def test_wells_2(self):
        self._create_db_matchable(creative="Congratulations on your scholarship! If you have any college planning questions, check out the Wells Fargo Community. https://www.wellsfargocommunity.com/index.jspa",
                                  intention_topics=['scholarship'],
                                  intention_types=[sa_labels.LIKES.title]
                                  )
        post = self._create_db_post(content="God is so good - i got the scholarship to go to #PASSION2013 :D",
                                    demand_matchables=True)
        payload = self.get_matchable(post)
        relevance = get_post_matchable_relevance(post, payload)
        self.assertTrue(relevance > 0.15, relevance)

    def test_wells_3(self):
        POST = "Got my scholarship back!:D"
        "Congratulations on your scholarship! If you have any college planning questions, check out the Wells Fargo Community. https://www.wellsfargocommunity.com/index.jspa"
        distance = distances.calc_distance(POST, "scholarship")
        self.assertTrue(distance > 0.4, distance)

