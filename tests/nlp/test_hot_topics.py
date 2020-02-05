# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
from datetime import datetime, timedelta

from nose.tools import eq_

from solariat_nlp.sa_labels  import get_sa_type_id_by_title as get_sa_type_id
from solariat_bottle.db.channel_hot_topics import ChannelHotTopics
from solariat_bottle.tests.base import MainCaseSimple, UICaseSimple
from solariat.utils.timeslot import datetime_to_timeslot, utc
from solariat.utils.lang.support import Lang


class ChannelHotTopicsTestCase(MainCaseSimple):

    def test_number_of_stats(self):
        content = "I need a mac laptop"
        '''
        topic: "mac laptop"
        stats count: ("mac laptop", "laptop") x ("day", "month")
        '''
        self._create_db_post(content)

        self.assertEqual(ChannelHotTopics.objects.count(), 2*2)

    def test_number_of_parentless(self):
        content = "I need a mac laptop"

        # 2 unigrams per level
        self._create_db_post(content)

        leaf_stats = ChannelHotTopics.objects(hashed_parents=[])
        self.assertEqual(len(leaf_stats), 1*2)  # (laptop) x (day + month)

    def test_number_of_topic_stats(self):
        content = "I need a mac laptop"

        # 1 topic - a bigram. 2 levels. 1*2
        self._create_db_post(content)

        stats = ChannelHotTopics.objects.find()
        topic_stats = [s for s in stats if s.filter(intention=0, is_leaf=True)]
        self.assertEqual(len(topic_stats), 1*2)  # ("mac laptop") x (day + month)

    def test_number_of_stats_accumulated(self):
        '''
        topics: laptop(3), laptop bag(1)
        terms:  laptop(4), bag(1)
        '''
        map(self._create_db_post, (
            "I need a laptop",
            "I need a laptop bag",
            "I love my new laptop",
            "Can someone recommend a laptop?"))

        def get_term_stats(term):
            query = {
                "topic": term,
                "hashed_parents": []
            }
            res = ChannelHotTopics.objects(**query)[:]
            assert len(res) == 2, res  # 2 for month and day timeslots
            return res[0]

        # Verify term counts is_leaf = False, intention = 0 (all intentions)
        stat = get_term_stats('bag')
        self.assertEqual(stat.filter_one(is_leaf=False, intention=0, language=Lang.EN).topic_count, 1)
        self.assertEqual(len(stat.filter(is_leaf=False, intention=0, language=Lang.FR)), 0)
        stat = get_term_stats('laptop')
        self.assertEqual(stat.filter_one(is_leaf=False, intention=0, language=Lang.EN).topic_count, 3)
        self.assertEqual(len(stat.filter(is_leaf=False, intention=0, language=Lang.FR)), 0)

    def test_number_of_stats_intention_id(self):
        content = "I need a mac laptop"

        post = self._create_db_post(content)

        intention_title = post.speech_acts[0]['intention_type']
        intention_id    = int(get_sa_type_id(intention_title))
        stats = [stat.filter(intention=intention_id, is_leaf=False)[0]
                 for stat in ChannelHotTopics.objects.find()
                 if stat.filter(intention=intention_id, is_leaf=False)]
        self.assertEqual(len(stats), 2*2)

        needs_count = sum(s.topic_count for s in stats)  # sum of term counts
        self.assertEqual(needs_count, 2*2)

        stats = [stat for stat in ChannelHotTopics.objects.find()
                         if stat.filter(intention=15)]
        self.assertEqual(len(stats), 0)

    def test_select_by_time_point(self):
        content = "I need a mac laptop"

        self._create_db_post(content)

        '''
        terms: mac laptop, laptop
        '''

        results =  ChannelHotTopics.objects.by_time_span(
            channel = self.channel,
            from_ts = datetime_to_timeslot(None, level='hour')
        )
        self.assertEqual(len(results), 0)  # we don't store HOUR hot-topics stats

        # The first test will be for root level topics.
        results =  ChannelHotTopics.objects.by_time_span(
            channel = self.channel,
            from_ts = datetime_to_timeslot(None, level='day')
        )
        expected = set(['laptop'])
        self.assertEqual(set([r['topic'] for r in results]).difference(expected),
                         set())

        # Should be the same again - despite the change in month
        results =  ChannelHotTopics.objects.by_time_span(
            channel = self.channel,
            from_ts = datetime_to_timeslot(None, level='month')
        )
        self.assertEqual(set([r['topic'] for r in results]).difference(expected),
                         set())

    def test_select_by_time_point_2(self):
        '''
        Create multiple posts and make sure the slots for
        terms get aggregated.
        '''
        content = "I need a mac laptop"

        for i in range(10):
            self._create_db_post(content)

        results = ChannelHotTopics.objects.by_time_span(
            channel = self.channel,
            from_ts = datetime_to_timeslot(None, level='day')
        )

        # Should just be 1 at the top
        self.assertEqual(len(results), 1)

        # Make sure the aggregate count is correct
        self.assertEqual(results[0]['term_count'], 10)
        self.assertEqual(results[0]['topic_count'], 0)

        # Should be 10 below for each. Only one item but counts of 10
        results = ChannelHotTopics.objects.by_time_span(
            channel      = self.channel,
            parent_topic = 'laptop',
            from_ts      = datetime_to_timeslot(None, level='day')
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['topic_count'], 10)

    def test_select_by_time_point_3(self):
        ''' Test with different post creation dates'''
        DAY_20131212 = utc(datetime(day=12, month=12, year=2013))
        DAY_20131202 = utc(datetime(day=2,  month=12, year=2013))
        DAY_20131002 = utc(datetime(day=2,  month=10, year=2013))

        for d in [ DAY_20131212, DAY_20131202, DAY_20131002]:
            self._create_db_post(
                _created=d,
                channel=self.channel,
                content = 'i need some carrot')

        # Test for 1 single day
        results =  ChannelHotTopics.objects.by_time_span(
            channel = self.channel,
            from_ts = datetime_to_timeslot(DAY_20131212, level='day')
        )
        self.assertEqual(results[0]['term_count'], 1)

        # For a month
        results =  ChannelHotTopics.objects.by_time_span(
            channel   = self.channel,
            from_ts = datetime_to_timeslot(DAY_20131212, level='month')
        )
        self.assertEqual(results[0]['term_count'], 2)

        # For a different month
        results =  ChannelHotTopics.objects.by_time_span(
            channel = self.channel,
            from_ts = datetime_to_timeslot(DAY_20131002, level='month')
        )
        self.assertEqual(results[0]['term_count'], 1)


class TestTopicDetailsSearch(UICaseSimple):
    """
    Test that asserts topic is not found yesterday or tomorrow the date of post creation
    """

    def setUp(self):
        super(TestTopicDetailsSearch, self).setUp()
        self.login()

    def get_hot_topics(self, default):
        data_dict = {
                "agents": None,
                "channel_id": None,
                "from": None,
                "to": None,
                "level": "day",
                "intentions": ["apology", "asks", "checkins", "consideration", "discarded", "gratitude",
                               "junk", "likes", "needs", "offer", "problem", "recommendation"],
                "languages": [],
                "parent_topic": None,
                "statuses": ["actionable", "actual", "rejected"],
        }
        data_dict.update(default)
        res = self._post("/hot-topics/json", data_dict)
        return res["list"]

    def topics_search_range(self, _from):
        _to = _from + timedelta(days=1)

        topics = self.get_hot_topics({
            "channel_id": str(self.channel.id),
            "from": _from.strftime("%m/%d/%Y"),
            "to": _to.strftime("%m/%d/%Y"),
        })
        return topics

    def test_topics_search_range(self):
        content = "I need a laptop @screen_name test"
        _created = utc(datetime.now())

        post = self._create_db_post(
                content=content,
                _created=_created
        )

        topics_yesterday = self.topics_search_range(_created - timedelta(days=1))
        eq_(topics_yesterday, [])

        topics_today = self.topics_search_range(_created)
        eq_(topics_today[0]['topic_count'], 1)

        topics_tomorrow = self.topics_search_range(_created + timedelta(days=1))
        eq_(topics_tomorrow, [])
