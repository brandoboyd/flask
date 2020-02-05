
import unittest

from solariat_bottle.tests.base import MainCase
from solariat_bottle.db.channel_stats import ChannelStats
from solariat_bottle.db.post.base import PostMatch

@unittest.skip('Deprecated; There are gonna be new EventClick class for clicks')
class PostClickCase(MainCase):
    def test_stats_update(self):
        matchable = self._create_db_matchable('there is some foo')
        post = self._create_db_post('i need some foo')

        post_match = PostMatch.objects.create_by_user(
            self.user, post=post, rejects=[], impressions=[matchable])

        # Should be removed in 2.0
        resp = self.do_post('postclicks',
                            channels=[str(self.channel_id)],
                            post=str(post.id),
                            matchable=str(matchable.id),
                            version='v2.0',
                            wrap_response=False)
        self.assertEqual(resp.status_code, 404)

        resp = self.do_post('postclicks', 
                            channels=[str(self.channel_id)],
                            post=str(post.id),
                            matchable=str(matchable.id),
                            version='v1.2')
        self.assertTrue(resp['ok'])
        matchable.reload()
        self.assertEqual(matchable.clicked_count, 1)
        self.assertEqual(matchable.ctr, 1.0)
        stats = ChannelStats.objects.find_one()
        self.assertEqual(stats.number_of_clicks, 1)
        
        
                     
                     
