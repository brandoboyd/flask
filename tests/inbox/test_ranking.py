""" Test construction for post/matchable response
"""

import unittest

from solariat_bottle.configurable_apps import APP_GSA
from solariat_bottle.tests.base import MainCase

from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel, TwitterServiceChannel

@unittest.skip("Matchables are depricated")
class RankingTest(MainCase):
    "Test response create/delete when post create/delete"

    def setUp(self):
        MainCase.setUp(self)
        self.account.update(selected_app=APP_GSA)
        self.dispatch = EnterpriseTwitterChannel.objects.create_by_user(self.user, title='out test', status='Active',
                                                                        access_token_key='test',
                                                                        access_token_secret='test')
        self.user.outbound_channels['Twitter'] = str(self.dispatch.id)
        self.user.save()
        self.channel = TwitterServiceChannel.objects.create_by_user(self.user, title="test me", status='Active')

        self.matchable1 = self._create_db_matchable('there is some food', intention_topics=['food'],
                                                    channels=[self.channel.inbound_channel])
        self.matchable2 = self._create_db_matchable('little mor food', intention_topics=['bar'],
                                                    channels=[self.channel.inbound_channel])

        #Matchable.objects.withdraw()
        #Matchable.objects.deploy()
        self.post = self._create_db_post('i need some food', demand_matchables=True)
        self.assertEqual(self.matchable1.get_from_es()['ranking_model'], self.matchable1.ranking_model)
        self.resps = Response.objects.find_by_user(self.user, id=self.post.response_id)

    def test_index_update(self):
        Matchable.objects.withdraw()
        Matchable.objects.deploy()

    def test_ranking_model(self):
        "Basics of the matchable mods"

        # Proper initialization on demand
        rm = self.matchable1.ranking_model
        self.assertEqual(rm, self.matchable1._ranking_model)

        # Make sure it is persisted
        self.matchable1.save()
        matchable =  Matchable.objects.get(id=self.matchable1.id)
        self.assertEqual(rm, matchable._ranking_model)


    def test_update_handling(self):
        'Handle updates to the ranking model.'
        rm = self.matchable1.ranking_model
        self.matchable1.reset_ranking_model()
        matchable = Matchable.objects.get(id=self.matchable1.id)
        self.assertEqual(rm, matchable._ranking_model)
        self.assertEqual(matchable.ranking_model['needs__food']['impressions'],  1)

        self.matchable1.update_ranking_model(self.post)
        matchable = Matchable.objects.get(id=self.matchable1.id)
        self.assertEqual(matchable.ranking_model['needs__food']['impressions'],  2)

        self.assertEqual(self.matchable2.ranking_model['needs__bar']['impressions'],  1)
        resp = self.resps[0]
        engage.handle_post_response(True, self.user, resp, resp.post.id, self.matchable2)

        self.assertEqual(self.matchable2.ranking_model['needs__bar']['impressions'],  1)

        post = self._create_db_post('i need some bar', demand_matchables=True)
        resps = Response.objects.find_by_user(self.user, id=post.response_id)
        engage.handle_post_response(True, self.user, resps[0], resps[0].post.id, self.matchable2)

        self.assertEqual(self.matchable2.ranking_model['needs__bar']['impressions'],  2)
        self.assertEqual(self.matchable2.to_dict()['ranking_model']['needs__bar'],
                         self.matchable2.ranking_model['needs__bar'])

    def test_rank_improvement(self):
        resp = self.resps[0]
        self.assertEqual(resp.matchable, self.matchable1)
        for i in range(0, 3):
            post = self._create_db_post(self.post.content, demand_matchables=True)
            resp = Response.objects.find_by_user(self.user, id=post.response_id)[0]
            last_matched = resp.matchable
            engage.handle_post_response(True, self.user, resp, resp.post.id, self.matchable2)
            MatchableCollection().index.refresh()

        self.assertEqual(last_matched, self.matchable2)



