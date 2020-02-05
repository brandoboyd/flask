# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
import time
import unittest
from dateutil.relativedelta import relativedelta
from solariat_nlp.sa_labels import get_sa_type_id_by_title as get_sa_type_id, ALL_INTENTIONS
from solariat_nlp.utils.topics import (
    get_largest_subtopics, get_all_subtopics, get_disjoint_subset)

from solariat_bottle.tests.base import MainCase
from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
from solariat_bottle.db.post.base     import Post
from solariat_bottle.utils.id_encoder import ALL_TOPICS
from solariat.utils.timeslot import now, Timeslot, datetime_to_timeslot


def topic_extraction_strategy(name):
    from solariat_nlp.utils.topics import get_simple_parent_topics, get_root_topic, get_subtopics
    if get_subtopics == get_simple_parent_topics:
        return name == 'get_simple_parent_topics'
    if get_subtopics == get_root_topic:
        return name == 'get_root_topic'


class HelpersTestCase(MainCase):

    def test_get_largest_subtopics(self):
        examples = (
            ("super big red laptop bag", ["super big red", "big red laptop", "red laptop bag"]),
            ("big red laptop",           ["big red", "red laptop"]),
            ("laptop",                   []),
        )
        for title, outcome in examples:
            self.assertEqual(get_largest_subtopics(title), outcome)

    @unittest.skipIf(
        topic_extraction_strategy('get_root_topic'),
        "test for solariat_nlp.utils.topics.get_simple_parent_topics")
    def test_get_all_subtopics(self):
        results = get_all_subtopics("riding lawn mower")
        self.assertEqual(
            set(results),
            set(['riding lawn mower', 'lawn mower', 'mower'])
        )

    @unittest.skipIf(
        topic_extraction_strategy('get_simple_parent_topics'),
        "test for solariat_nlp.utils.topics.get_root_topic")
    def test_get_all_subtopics1(self):
        results = get_all_subtopics("small riding lawn mower")
        self.assertEqual(
            set(results),
            set(['small riding lawn mower', 'mower'])
        )
        results = get_all_subtopics("lawnmower")
        self.assertEqual(
            set(results),
            set(['lawnmower'])
        )

    def test_get_disjoint_subset(self):
        examples = [
            (["laptop", "laptop bag"], ["laptop bag"]),
            (["laptop", "cooktop"], ["laptop", "cooktop"]),
            (["riding lawn mower", "riding", "lawn", "lawn mower"], ["riding lawn mower"])
            ]

        for topics, outcome in examples:
            self.assertEqual(list(get_disjoint_subset(topics)), outcome)

class ChannelTopicTrendsTestCase(MainCase):

    def test_number_of_stats(self):
        content = "I need a mac laptop"
        '''
        topic: "mac laptop"
        stats count: ("mac laptop", "laptop", "__ALL__") x ("hour", "day")
        '''
        self._create_db_post(content)

        self.assertEqual(ChannelTopicTrends.objects.count(), (2+1)*2)

    def test_number_of_leafs(self):
        """ Note: leaf means it is a stat record for a specific topic (max tri-gram),
                  not a smaller part of the topic
        """
        content = "I need a mac laptop"

        self._create_db_post(content)
        leaf_stats = [s for s in ChannelTopicTrends.objects()
                      if s.filter(is_leaf=True)]
        self.assertEqual(len(leaf_stats), 2)  # ("mac laptop") x (hour + day)  #NO __ALL__, it is not a leaf

    def test_number_of_nodes(self):
        """ Note: node means it is a stat record for a smaller part of a bigger topic,
                  not a topic itself
        """
        content = "I need a mac laptop"

        self._create_db_post(content)

        node_stats = [True for s in ChannelTopicTrends.objects()
                      if s.filter(is_leaf=False)]
        self.assertEqual(len(node_stats), (2+1)*2)  # ("mac laptop", "laptop", "__ALL__") x (hour + day )

    def test_number_of_stats_accumulated(self):
        '''
        topics: laptop(3), laptop bag(1)
        terms:  laptop(3), bag(1)
        '''
        self._create_db_post("I need a laptop")
        self._create_db_post("I need a laptop bag")
        self._create_db_post("I love my new laptop")
        self._create_db_post("Can someone recommend a laptop?")

        def get_term_stats(term, level):
            stats = ChannelTopicTrends.objects.by_time_span(
                self.channel,
                topic_pairs = [[term, False]],
                from_ts     = Timeslot(level=level)
            )
            return tuple(stats)

        for level in ('hour', 'day'):
            laptop_stats = get_term_stats('laptop', level)
            self.assertEqual(len(laptop_stats), 1)
            node_stat = laptop_stats[0].filter(is_leaf=False, intention=int(ALL_INTENTIONS.oid))[0]
            leaf_stat = laptop_stats[0].filter(is_leaf=True, intention=int(ALL_INTENTIONS.oid))[0]
            self.assertEqual(leaf_stat.topic_count, 3)  # topics
            self.assertEqual(node_stat.topic_count, 3)  # terms (will not count to laptop bag case)

        for level in ('hour', 'day'):
            bag_stats = get_term_stats('bag', level)
            self.assertEqual(len(bag_stats), 1)
            node_stat = bag_stats[0].filter(is_leaf=False, intention=int(ALL_INTENTIONS.oid))[0]
            self.assertEqual(node_stat.topic_count, 1)

    def test_number_of_stats_intention_id(self):
        content = "I need a mac laptop"
        #topics: "mac laptop"
        #terms: "mac laptop", "laptop"
        post = self._create_db_post(content)

        intention_title = post.speech_acts[0]['intention_type']
        intention_id    = get_sa_type_id(intention_title)
        stats = [s for s in ChannelTopicTrends.objects()
                 if s.filter(intention=int(intention_id))]
        self.assertEqual(len(stats), (2+1)*2)

        needs_count = sum(s.filter(intention=int(intention_id), is_leaf=False)[0].topic_count
                          for s in ChannelTopicTrends.objects() if s.topic != ALL_TOPICS)
        self.assertEqual(needs_count, 2*2)

        stats = [s for s in ChannelTopicTrends.objects()
                 if s.filter(intention=15)]
        self.assertEqual(len(stats), 0)

    def test_select_by_time_span(self):
        content = "I need a mac laptop"

        post            = self._create_db_post(content)
        intention_title = post.speech_acts[0]['intention_type']
        intention_id    = get_sa_type_id(intention_title)

        leafs = ["mac laptop"]
        nodes = leafs + ["laptop"]

        for level in ('hour', 'day'):
            for topic in leafs:
                res = ChannelTopicTrends.objects.by_time_span(
                    channel     = self.channel,
                    topic_pairs = [[topic, True]],
                    from_ts     = Timeslot(level=level)
                )
                self.assertEqual(len(res), 1)

                embed = res[0].filter(is_leaf=True, intention=int(intention_id))[0]
                self.assertEqual(embed.topic_count, 1)

                embed = res[0].filter(is_leaf=True, intention=int(ALL_INTENTIONS.oid))[0]
                self.assertEqual(embed.topic_count, 1)

            for topic in nodes:
                res = ChannelTopicTrends.objects.by_time_span(
                    channel     = self.channel,
                    topic_pairs = [[topic, False]],
                    from_ts     = Timeslot(level=level)
                )
                self.assertEqual(len(res), 1)

                embed = res[0].filter(is_leaf=False, intention=int(intention_id))[0]
                self.assertEqual(embed.topic_count, 1)

                embed = res[0].filter(is_leaf=False, intention=int(ALL_INTENTIONS.oid))[0]
                self.assertEqual(embed.topic_count, 1)

    def test_select_by_time_span_2(self):
        '''
        Create multiple posts and make sure the slots for
        terms get aggregated.
        '''
        content = "I need a mac laptop"

        leafs = ["mac laptop"]
        nodes = leafs + ["laptop"]

        N = 5

        for i in range(N):
            self._create_db_post(content)
            time.sleep(0.01)

        for level in ('hour', 'day'):
            for topic in leafs:
                stats = ChannelTopicTrends.objects.by_time_span(
                    channel     = self.channel,
                    topic_pairs = [[topic, True]],
                    from_ts     = Timeslot(level=level),
                    to_ts       = Timeslot(level=level)
                )
                self.assertEqual(len(stats), 1)

                embed_stat = stats[0].filter(intention=int(ALL_INTENTIONS.oid), is_leaf=True)
                self.assertEqual(embed_stat[0].topic_count, N)

            for topic in nodes:
                stats = ChannelTopicTrends.objects.by_time_span(
                    channel     = self.channel,
                    topic_pairs = [[topic, False]],
                    from_ts     = Timeslot(level=level),
                    to_ts       = Timeslot(level=level)
                )
                self.assertEqual(len(stats), 1)
                embed_stat = stats[0].filter(intention=int(ALL_INTENTIONS.oid), is_leaf=False)
                self.assertEqual(embed_stat[0].topic_count, N)

    def test_select_by_time_span_3(self):
        past_dt = now() - relativedelta(months=1)  # big enough for all levels

        post1 = self._create_db_post(
            _created=past_dt,
            content = 'i need some carrot')

        post2 = self._create_db_post(
            content = 'i need some carrot')

        self.assertEqual(Post.objects(channels__in=[self.channel.id]).count(), 2)

        for level in ('hour', 'day'):
            result = ChannelTopicTrends.objects.by_time_span(
                channel     = self.channel,
                topic_pairs = [['carrot', True]],
                from_ts     = datetime_to_timeslot(past_dt, level),
                to_ts       = datetime_to_timeslot(None,    level)
            )
            self.assertEqual(len(result), 2)

            result = ChannelTopicTrends.objects.by_time_span(
                channel     = self.channel,
                topic_pairs = [['carrot', True]],
                from_ts     = datetime_to_timeslot(past_dt + relativedelta(**{level+'s':1}), level),
                to_ts       = datetime_to_timeslot(None, level)
            )
            self.assertEqual(len(result), 1)

    def _assert_topic_extraction(self, expect_topics):
        past_dt = now() - relativedelta(months=1)
        posts = [
            "I need a riding lawnmower",
            "I need a lawnmower",
            "I need a side ride push lawnmower"]
        for content in posts:
            self._create_db_post(content)

        for (topic, is_leaf, cnt) in expect_topics:
            for level in ('hour', 'day'):
                result = ChannelTopicTrends.objects.by_time_span(
                    channel=self.channel,
                    topic_pairs=[(topic, is_leaf)],
                    from_ts=datetime_to_timeslot(past_dt, level),
                    to_ts=datetime_to_timeslot(None, level)
                )
                self.assertEqual(len(result), cnt)

    @unittest.skipIf(
        topic_extraction_strategy('get_simple_parent_topics'),
        "test for solariat_nlp.utils.topics.get_root_topic")
    def test_topic_extraction_1(self):
        expect_topics = (
            ("lawnmower", False, 1),
            ("riding lawnmower", True, 1),
            ("lawnmower", True, 1),
            ("side ride push lawnmower", True, 1),

            ("ride push lawnmower", True, 0),
            ("push lawnmower", True, 0))
        self._assert_topic_extraction(expect_topics)

    @unittest.skipIf(
        topic_extraction_strategy('get_root_topic'),
        "test for solariat_nlp.utils.topics.get_simple_parent_topics")
    def test_topic_extraction_2(self):
        expect_topics = (
            ("lawnmower", False, 1),
            ("riding lawnmower", True, 1),
            ("lawnmower", True, 1),
            ("side ride push lawnmower", True, 1),
            ("ride push lawnmower", True, 1),
            ("push lawnmower", True, 1))
        self._assert_topic_extraction(expect_topics)

    @unittest.skip('skipped by Sergey Chvalyuk on May 28, 2013')
    def test_mhash_collision(self):

        self._create_db_post(
            '@XboxSupport3 just wondering if you can suggest a increased network timeout in a future update.')

        self._create_db_post('I have 2 separate phones.')

        self.assertEqual(
            ChannelTopicTrends.objects.find(topic='separate phones', channel=self.channel_id).count(), 3)
        self.assertEqual(
            ChannelTopicTrends.objects.find(topic='future update', channel=self.channel_id).count(), 3)

    def test_big_channel_counter(self):

        self.channel.counter = 8100
        self.channel.save()

        self._create_db_post('I have 2 separate phones.')
