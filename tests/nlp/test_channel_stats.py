# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import unittest
from solariat_bottle.tests.base import MainCase


from solariat_bottle.db.channel_stats import get_levels, ChannelStats 
from solariat_bottle.db.channel_trends import ReportsEmbeddedStats
from solariat.utils import timeslot
from solariat_bottle.db.post.base import Post
from solariat.utils.lang.support import Lang


LALL = Lang.ALL
atoi = hash  # agent string to integer representation

class EmbeddedDocumentTest(MainCase):

    def setUp(self):
        super(MainCase, self).setUp()

        self.collection = []
        for agent in map(atoi, ['jack', 'jill', 'mary']):
            item = ReportsEmbeddedStats(agent=agent)
            self.collection.append(item)

    def test_CRUD(self):
        # start with a default
        es = ReportsEmbeddedStats()
        self.assertDictEqual(ReportsEmbeddedStats.to_mongo(es.to_dict()),
                             {'at': 0, 'rt': 0, 'rv': 0, 'pt': 0, 'le': LALL})

        # Test field use with proper saved structure
        es.response_volume = 10
        es.agent = atoi('jack')
        expected = {'at': atoi('jack'), 'rt': 0, 'rv': 10, 'pt': 0, 'le': LALL}
        self.assertDictEqual(ReportsEmbeddedStats.to_mongo(es.to_dict()),
                             expected)

        # Test we can recover it correctly
        es_new = ReportsEmbeddedStats(expected)
        self.assertDictEqual(ReportsEmbeddedStats.to_mongo(es_new.to_dict()),
                             expected)

        # Now make sure the match
        self.assertTrue(es_new == es)

        # Modify counter - will still be matched
        es_new.response_time = 25
        self.assertTrue(es_new == es)

        # Modify agent and make sure they are not macthed
        es_new.agent = atoi('jill')
        self.assertFalse(es_new == es)

    def test_collection_handling(self):
        mongo_list = ReportsEmbeddedStats.pack(self.collection)
        new_collection = ReportsEmbeddedStats.unpack(mongo_list)
        self.assertListEqual(self.collection, new_collection)

#     def test_split(self):
#         UNMATCHED = ReportsEmbeddedStats(agent=atoi('not_found'), is_leaf=True, intention=0)
#         items_to_match = [
#             ReportsEmbeddedStats(agent=atoi('jack'), is_leaf=True, intention=5),
#             ReportsEmbeddedStats(agent=atoi('jack'), is_leaf=False, intention=5),
#             ReportsEmbeddedStats(agent=atoi('jill'), is_leaf=True, intention=0),
#             UNMATCHED,
#             ]
#
#         unmatched_collection, matched_items, not_found = ReportsEmbeddedStats.split(self.collection,
#                                                                              items_to_match)
#
#         self.assertListEqual(not_found, items_to_match[3:])
#         self.assertListEqual(matched_items, items_to_match[:3])
#         self.assertEqual(len(unmatched_collection), len(self.collection) - len(matched_items))

    def test_setting_stats(self):
        es = ReportsEmbeddedStats(agent=atoi('jack'), response_time=2)
        es.inc('response_time', 10)
        self.assertEqual(es.response_time, 12)
        es.inc('response_time', 9)
        self.assertEqual(es.response_time, 21)

        es.set('response_volume', 100)
        self.assertEqual(es.response_volume, 100)


    def test_collection_update(self):
        items_to_match = [
            ReportsEmbeddedStats(agent=atoi('jack'), ),
            ReportsEmbeddedStats(agent=atoi('jack'), ),
            ReportsEmbeddedStats(agent=atoi('jill'), ),
            ReportsEmbeddedStats(agent=atoi('not_found'), ),
            ]

        inc_dict = {'response_volume': 1, 'response_time':24}
        for item in items_to_match:
            for key, value in inc_dict.iteritems():
                item.inc(key, value)
        # Start with the empty list, and default values
        updated = ReportsEmbeddedStats.update_list([],
                                            items_to_match)

        unpacked = ReportsEmbeddedStats.unpack(updated)
        self.assertListEqual(unpacked, items_to_match)
        self.assertEqual(unpacked[0].response_time, 24)
        updated = ReportsEmbeddedStats.update_list(updated,
                                            items_to_match[:1])
        unpacked = ReportsEmbeddedStats.unpack(updated)
        self.assertEqual(unpacked[-1].response_time, 48)
        self.assertEqual(unpacked[0].response_time, 24)
        self.assertEqual(set([str(s.agent) for s in unpacked]),
                         set([str(s.agent) for s in items_to_match]))

    def test_key_generation(self):
        pass


class DbChannelStatsTest(MainCase):
    def test_create(self):
        for stat in get_levels(self.channel):
            stat.save()
        self.assertEqual(
            ChannelStats.objects.count(), 3)

    def test_inc(self):
        stats = list(get_levels(self.channel))[0]
        stats.inc('number_of_clicks', 1)
        stats.inc('number_of_impressions', 10)
        stored_stats = ChannelStats.objects.get(time_slot=stats.time_slot)
        self.assertEqual(
            stored_stats.number_of_clicks, 1)
        self.assertEqual(
            stored_stats.number_of_impressions, 10)

    def test_post_stats(self):
        self.assertEqual(ChannelStats.objects().count(), 0)
        response = self.do_post(
            'posts',
            version='v1.2',
            channel=str(self.channel.id),
            content='i need a foo for bar but not baz')

        # Should have allocated stats for each level
        self.assertEqual(ChannelStats.objects().count(), 3)

        post = Post.objects()[0]
        for stats in get_levels(self.channel, post.created):
            stats.reload()
            #print stats.to_dict()
            self.assertEqual(stats.number_of_posts, 1)
            self.assertEqual(stats.feature_counts, {'0':1, '2':1})

    @unittest.skip("Depricating this case, because Responses are depricated.")
    def test_impressions(self):
        "Test impressions stats"

        pl1 = self._create_db_matchable('foo')
        pl2 = self._create_db_matchable('bar')
        pl3 = self._create_db_matchable('baz')

        response = self.do_post(
            'posts',
            version='v1.2',
            channel=str(self.channel.id),
            content='i need a foo for bar but not baz')

        post_dict = response['item']

        #matchables = post_dict['matchables']

        response = self.do_post('postmatches',
                                version='v1.2',
                                post=post_dict['id'],
                                impressions=[str(pl1.id), str(pl2.id)],
                                rejects=[str(pl3.id)])

        self.assertEqual(response['item']['rejects'][0],
                         str(pl3.id))

        time_slot = timeslot.datetime_to_timeslot(Post.objects()[0].created)

        response = self.do_get('channelstats',
                               version='v1.2',
                               channel=str(self.channel.id),
                               time_slot=time_slot) # month stats object
        stats = response['list'][0]
        self.assertEqual(stats['number_of_impressions'], 2)


class ChannelStatsRestCase(MainCase):
    pass
