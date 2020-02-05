import unittest

#from solariat_bottle.db.account import Account
from solariat_bottle.db.channel.twitter import KeywordTrackingChannel
from solariat_bottle.db.group import Group
from solariat_bottle.db.roles import AGENT, ADMIN
from solariat_bottle.utils.redirect import add_sourcing_params

from solariat_nlp.analytics import distances

from .base import MainCase, SA_TYPES, BaseCase


class BugFixes(BaseCase):

    @unittest.skip("ids work differently now")
    def test_id_decoding(self):
        '''Debug case from production environment, from test page on post creation'''
        
        post = self._create_db_post("I like foo",
                             channel=self.channel,
                             demand_matchables=True)

        post.id = 'ee15e3:test.socialoptimizr.com/posts/525bdaa6d8b21002fc51ee3e'
        post.save()
        post.set_url()
        self.assertEqual(post.url, 'test.socialoptimizr.com/posts/525bdaa6d8b21002fc51ee3e')

class Misc(MainCase):

    def setUp(self):
        MainCase.setUp(self)
        self.channel = KeywordTrackingChannel.objects.create_by_user(
            self.user, title='KeywrodTestChannel', 
            type='twitter', intention_types=SA_TYPES,
            account=self.account)

        self.channel.add_perm(self.user)

    def test_group_access_for_member(self):

        g = Group(name='g')
        g.save()
        u = self._create_db_user(email='foo@solariat.com', password='12345', roles=[AGENT],
                                 account=self.channel.account)
        self.assertFalse(self.channel.can_edit(u))
        g.add_user(u)
        g.save()
        self.channel.add_perm(u, group=g)
        u.reload()
        self.assertFalse(self.channel.can_edit(u))  # Even with perms, only admin / staff should have edit rights
        u.user_roles.append(ADMIN)
        u.save()
        self.assertTrue(self.channel.can_edit(u))
        

    def test_routing_params(self):
        'Test routing param addition'
        # Just in case
        self.assertEqual(add_sourcing_params("www.google.com?utm_source=foo", '5072aad8936aa27c25000042'),
                         "http://www.google.com?solariat_id=5072aad8936aa27c25000042&utm_source=solariat")

        self.assertEqual(add_sourcing_params("www.google.com", '5072aad8936aa27c25000042'),
                         "http://www.google.com?solariat_id=5072aad8936aa27c25000042&utm_source=solariat")

        self.assertEqual(add_sourcing_params("www.google.com?param1=foo", '5072aad8936aa27c25000042'),
                         "http://www.google.com?solariat_id=5072aad8936aa27c25000042&utm_source=solariat&param1=foo")

    def test_similarity_for_rejects(self):
        similar_enough = [
            ("Join http://t.co/DATRB6S4 and we could both win a scholarship! http://t.co/zgZlNOBL via @winscholarships",
                                       "Join http://t.co/k5DFnrjs and we could both win a scholarship! http://t.co/XDz2k02Z via @winscholarships"),
            ("@terry_kerry DO YOU HAVE YOUR TICKET to The Miss @C100_MSU Scholarship Pageant Monday 10/1!!!Tickets $3-Student $5-DAY OF SHOW!",
             "@DWill_Urkel DO YOU HAVE YOUR TICKET to The Miss @C100_MSU Scholarship Pageant Monday 10/1!!! Tickets $3-Student $5-DAY OF SHOW!")
            ]

        for case in similar_enough:
            distance = distances.calc_distance(case[0], case[1])
            self.assertTrue(distance > 0.75, distance)


    @unittest.skip("Matchables and PostMatches are depricated.")
    def test_filtering_redundant_matches(self):
        self._create_db_matchable(creative="Foo Bar Baz",
                                  intention_topics = ['foo'],
                                  url="www.foo.cm")
        self._create_db_matchable(creative="Foo Bar Baz",
                                  intention_topics = ['foo'],
                                  url="www.foo.cm")
        self._create_db_matchable(creative="Foo Bar Bing",
                                  intention_topics = ['foo'],
                                  url="www.foo.cm")
        post = self._create_db_post(content="I need a foo",
                                    demand_matchables=True);

        # Verify 2 of 3 returned
        self.assertTrue(len(post.to_dict()['matchables']) == 2,
                        post.to_dict()['matchables'])
