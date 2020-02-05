from solariat_bottle.tests.base import MainCase
from solariat_bottle.db.channel.twitter import KeywordTrackingChannel
from solariat_bottle.db.channel_hot_topics import ChannelHotTopics
from solariat.utils.lang.support import Lang

EN = Lang.EN


class KeywordTopic(MainCase):

    def setUp(self):
        MainCase.setUp(self)

    def test_keyword_topic_added(self):

        """ keyword topic 'python' added as leaf node """

        ktc = KeywordTrackingChannel.objects.create_by_user(
            self.user, title='KeywordTrackingChannel', status='Active')
        ktc.add_keyword('python')

        self._create_db_post(
            channel=ktc,
            content='I am looking for intermediate python course for under $500')

        stats = ChannelHotTopics.objects.get(topic='python')
        self.assertEqual(len(stats.filter(intention=0, language=EN, is_leaf=True)), 1)
        self.assertEqual(len(stats.filter(intention=0, language=EN, is_leaf=False)), 1)

    def test_keyword_topic_skipped(self):

        """ keyword topic 'python' skipped
            because it was extracted from content """

        ktc = KeywordTrackingChannel.objects.create_by_user(
            self.user, title='KeywordTrackingChannel', status='Active')
        ktc.add_keyword('python')

        self._create_db_post(
            channel=ktc,
            content='I like a python in a zoo')

        stats = ChannelHotTopics.objects.get(topic='python')

        self.assertEqual(1,
            stats.filter(intention=0, is_leaf=True)[0].topic_count)

        self.assertEqual(1,
            stats.filter(intention=0, is_leaf=False)[0].topic_count)
