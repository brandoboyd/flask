# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from .base import MainCase

from ..db.channel_hot_topics import ChannelHotTopics
from ..db.channel_stats import ChannelStats

class ChannelTermStatsTestCase(MainCase):

    def test_number_of_stats_discarded_with_topics(self):
        self.assertEqual(ChannelStats.objects.count(), 0)
        content = "This laptop bag should be discarded"
        self._create_db_post(content)
        # Unigrams per level for bag
        # Bigrams for laptop bag, per level
        self.assertEqual(ChannelHotTopics.objects.count(), 2*2)

        # Entry for each level
        self.assertEqual(ChannelStats.objects.count(), 3)

    def test_number_of_stats_discarded_without_topics(self):
        # Make sure we create speech acts with the default case
        self._create_db_post('This should be discarded')

        # Leave this list comprehension here as it tests topic to string
        # rendering as well as the main case objective
        self.assertEqual(len([t for t in ChannelHotTopics.objects()]), 2)


