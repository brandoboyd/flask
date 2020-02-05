from datetime import datetime, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from solariat_bottle          import settings
from solariat_bottle.configurable_apps import APP_GSA
from solariat_bottle.settings import get_var, LOGGER
from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
from solariat_bottle.db.channel_hot_topics   import ChannelHotTopics
from solariat_bottle.db.channel.twitter      import TwitterServiceChannel
from solariat_bottle.db.channel_stats        import ChannelStats
from solariat_bottle.db.channel.base         import Channel
from solariat_bottle.db.conversation         import Conversation
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.speech_act           import SpeechActMap
from solariat_bottle.db.post.base            import Post
from solariat_bottle.db.account              import Account
from solariat.utils.timeslot import (
    datetime_to_timeslot, now, Timeslot, decode_timeslot)
from solariat_bottle.utils.purging  import (
    fetch_child_topics, get_document_ids, mark_items_to_keep,
    mark_and_sweep_topics, purge_channel_stats, purge_stats,
    discard_outdated_topics_for_month_level, purge_corresponding_trends,
    purge_channel_entities, purge_channel_outdated_posts_and_sas)
from ..base import MainCase

class Purging(MainCase):

    def setUp(self):
        super(Purging, self).setUp()
        # Start Fresh
        ChannelHotTopics.objects.coll.remove()
        self.assertEqual(ChannelHotTopics.objects.count(), 0)

        self.this_month = datetime_to_timeslot(now(), 'month')
        self.this_day   = datetime_to_timeslot(now(), 'day')


    def _create_posts(self, content_list):
        for (_created, content) in content_list:
            self._create_db_post(content=content,
                                 user_tag=self.user.email,
                                 _created=_created)

    def _make_laptops_and_icecream(self, _created=None):
        '''
        Expect the following:
         cream:
            ice cream
         laptop:
            mac laptop
         bag

        A total of 5 entries - per day and month slot
        '''
        if _created == None:
            _created = now()

        posts = [
            "I need a mac laptop",
            "I need a laptop",
            "I need a bag",
            "I like ice cream",
            "I hate ice cream",
            "I love ice cream"]
        content_list = []
        for content in posts:
            _created = _created + timedelta(seconds=1)
            content_list.append((_created, content))

        self._create_posts(content_list)

    def test_discard_all(self):
        ''' Creat the posts way in the past and make sure we drop them all'''
        before = ChannelHotTopics.objects().count()
        DAY_10022011 = pytz.utc.localize(datetime(day=2,  month=10, year=2011))
        self._make_laptops_and_icecream(DAY_10022011)
        purge_stats(self.channel)
        after  = ChannelHotTopics.objects().count()
        self.assertEqual(after, before)

    def test_leave_months_only(self):
        before = ChannelHotTopics.objects().count()
        DAY_TWO_WEEKS_AGO = now() - timedelta(days=15)
        self._make_laptops_and_icecream(DAY_TWO_WEEKS_AGO)
        delta  = ChannelHotTopics.objects().count() - before
        purge_stats(self.channel)
        after = ChannelHotTopics.objects().count() - before
        # The days should be all gone
        self.assertEqual(after, delta/2)

    def test_task(self):
        from solariat_bottle.tasks.stats import purge_all_channel_stats
        self._make_laptops_and_icecream()
        purge_all_channel_stats(self.channel)

    def test_purge_none(self):
        TWO_DAYS_AGO = now() - timedelta(days=2)
        self._make_laptops_and_icecream(TWO_DAYS_AGO)
        stats = purge_stats(self.channel)
        last_purged = stats["last_purged"]
        days = stats["purge_days"]
        months = stats["purge_months"]
        self.channel.reload()
        self.assertEqual(datetime_to_timeslot(self.channel.last_purged, 'hour'),
                         datetime_to_timeslot(last_purged, 'hour'))

        # Should have purged over 15 days for time slots since we never urged before
        self.assertEqual(len(days), 15)
        # Months purged depends on how far in we are to the month when we run the test
        self.assertTrue(len(months) in [2, 3])

        import solariat_bottle.utils.purging

        class MockLocaltime(object):
            tm_mday = 6

        solariat_bottle.utils.purging.localtime = MockLocaltime
        stats = purge_stats(self.channel)
        last_purged = stats["last_purged"]
        days = stats["purge_days"]
        months = stats["purge_months"]
        self.assertEqual(len(days), 1)
        self.assertEqual(days[0], decode_timeslot(Timeslot(level='day').timeslot))
        self.assertEqual(len(months), 0)

        class MockLocaltime(object):
            tm_mday = 8

        solariat_bottle.utils.purging.localtime = MockLocaltime
        stats = purge_stats(self.channel)
        last_purged = stats["last_purged"]
        days = stats["purge_days"]
        months = stats["purge_months"]
        self.assertEqual(len(days), 1)
        self.assertEqual(len(months), 1)
        self.assertEqual(months[0], decode_timeslot(Timeslot(level='month').timeslot))

    def test_purging_policy(self):
        self._make_laptops_and_icecream()
        settings.PURGING_POLICY = {"0": 1, "1": 1, "2": 1}
        stats = mark_and_sweep_topics(self.channel, self.this_month)

        # Should keep the crea, and ice cream slots, and remove the rest
        self.assertEqual(stats, (5, 2, 3))

    def test_topic_query(self):
        '''
        Simple test for selecting the top topics
        '''
        self._make_laptops_and_icecream()

        # Root Topics
        results = fetch_child_topics(self.channel, self.this_month, 2)
        self.assertEqual(results, ['cream', 'laptop'])

        # Child Topics
        results = fetch_child_topics(self.channel, self.this_month, 10, 'laptop')
        self.assertEqual(results, ['mac laptop'])

    def test_docs_from_topics(self):
        '''
        Make sure we can get the ids we want and can fetch the docs for them
        '''
        self._make_laptops_and_icecream()
        doc_ids = [x for x in get_document_ids(self.channel, self.this_month, ['laptop', 'cream'])]

        items = ChannelHotTopics.objects(id__in=doc_ids)
        self.assertEqual(set([item.topic for item in items]), set(['laptop', 'cream']))

    def test_marking_items(self):
        '''
        Make sure we mark what we expect to mark - correctly
        '''

        self._make_laptops_and_icecream()

        # All of them
        marked = mark_items_to_keep(self.channel, self.this_month, 100)
        marked += mark_items_to_keep(self.channel,self.this_day, 100)
        self.assertEqual(marked, ChannelHotTopics.objects.count())

        # None of them
        marked = mark_items_to_keep(self.channel, self.this_month, rank=0)
        self.assertEqual(marked, 0)

        # Just the top topic - which will be ice cream
        marked = mark_items_to_keep(self.channel, self.this_month, 1)
        self.assertEqual(marked, 2)

    def test_mark_and_sweep_remove_all(self):
        self._make_laptops_and_icecream()
        stats = mark_and_sweep_topics(self.channel, self.this_month, 0)
        self.assertEqual(stats, (5, 0, 5))
        # print_db_records()
        # removing corresponding trends
        stats = purge_corresponding_trends(self.channel, self.this_month)
        # print_db_records()
        self.assertEqual(stats, (6, 1, 5))

    def test_mark_and_sweep_keep_all(self):
        self._make_laptops_and_icecream()
        stats = mark_and_sweep_topics(self.channel, self.this_month, 100)
        self.assertEqual(stats, (5, 5, 0))

        # removing corresponding trends
        stats = purge_corresponding_trends(self.channel, self.this_month)
        self.assertEqual(stats, (6, 6, 0))

    def test_mark_and_sweep_some(self):
        self._make_laptops_and_icecream()
        stats = mark_and_sweep_topics(self.channel, self.this_month, 2)
        self.assertEqual(stats, (5, 4, 1))

        # removing corresponding trends
        stats = purge_corresponding_trends(self.channel, self.this_month)
        self.assertEqual(stats, (6, 5, 1))

        # And now remove the rest
        stats = mark_and_sweep_topics(self.channel, self.this_month, 0)
        self.assertEqual(stats, (4, 0, 4))

        # removing all trends
        stats = purge_corresponding_trends(self.channel, self.this_month)
        self.assertEqual(stats, (5, 1, 4))

    def test_outdated_trends1(self):
        """
        all existing day stats should be removed, cause it's too old
        """
        date_now = now()
        date_old = now() - relativedelta(months=get_var('TOPIC_TRENDS_DAY_STATS_KEEP_MONTHS'), days=1)

        self._make_laptops_and_icecream(_created=date_old)
        total_trends = ChannelTopicTrends.objects().count()
        hour_trends = total_trends/2
        day_trends  = total_trends/2

        stats = purge_stats(self.channel)
        self.assertEqual(day_trends, 6)
        self.assertEqual(hour_trends, 6)
        self.assertEqual(stats['discard_junk_stats']['trends_day_count'], 6)
        self.assertEqual(stats['discard_junk_stats']['trends_hour_count'], 0)

    def test_outdated_trends2(self):
        """
        all existing stats should be kept, cause it's not too old
        """
        date_now = now()
        date_old = now() - relativedelta(months=get_var('TOPIC_TRENDS_DAY_STATS_KEEP_MONTHS'))

        self._make_laptops_and_icecream(_created=date_now)
        total_trends = ChannelTopicTrends.objects().count()
        hour_trends = total_trends/2
        day_trends  = total_trends/2

        stats = purge_stats(self.channel)
        self.assertEqual(day_trends, 6)
        self.assertEqual(hour_trends, 6)
        self.assertEqual(stats['discard_junk_stats']['trends_day_count'], 0)
        self.assertEqual(stats['discard_junk_stats']['trends_hour_count'], 0)

    def test_outdated_trends3(self):
        """
        all existing hour stats should be removed, cause it's too old
        """
        date_now = now()
        date_old = now() - relativedelta(days=get_var('TOPIC_TRENDS_HOUR_STATS_KEEP_DAYS'), hours=1)

        LOGGER.info("11111111, %s, %s, %s" % (date_now, date_old, get_var('TOPIC_TRENDS_HOUR_STATS_KEEP_DAYS')))
        self._make_laptops_and_icecream(_created=date_old)
        total_trends = ChannelTopicTrends.objects().count()
        hour_trends = total_trends/2
        day_trends  = total_trends/2

        stats = purge_stats(self.channel)
        self.assertEqual(day_trends, 6)
        self.assertEqual(hour_trends, 6)
        self.assertEqual(stats['discard_junk_stats']['trends_day_count'], 0)
        self.assertEqual(stats['discard_junk_stats']['trends_hour_count'], 6)

    def test_outdated_trends4(self):
        """
        all existing hour stats should be kept
        """
        date_now = now()
        date_old = now() - relativedelta(days=get_var('TOPIC_TRENDS_HOUR_STATS_KEEP_DAYS')-1, hours=23)
        self._make_laptops_and_icecream(_created=date_old)
        total_trends = ChannelTopicTrends.objects().count()
        hour_trends = total_trends/2
        day_trends  = total_trends/2

        stats = purge_stats(self.channel)
        self.assertEqual(day_trends, 6)
        self.assertEqual(hour_trends, 6)
        self.assertEqual(stats['discard_junk_stats']['trends_day_count'], 0)
        self.assertEqual(stats['discard_junk_stats']['trends_hour_count'], 0)

    def _make_posts_and_stats(self):
        date_now = now()
        date_old = now() - timedelta(days=get_var('CHANNEL_STATS_KEEP_DAYS')+1)

        content_list = [ (date_old, "old post") ]
        self._create_posts(content_list)
        content_list = [ (date_now, "new post") ]
        self._create_posts(content_list)

    def test_purge_channel_stats(self):
        ChannelStats.objects.coll.remove()
        self.assertEqual(ChannelStats.objects.count(), 0)

        self._make_posts_and_stats()
        self.assertEqual(ChannelStats.objects.count(), 6)

        purge_channel_stats(self.channel)
        self.assertEqual(ChannelStats.objects.count(), 3)

    def test_discard_junk(self):
        LONG_TIME_AGO = now() - timedelta(days=(get_var('HOT_TOPICS_MONTH_STATS_KEEP_MONTHS')+1)*30)
        ChannelHotTopics.objects.coll.remove()
        self._make_laptops_and_icecream(LONG_TIME_AGO)
        self.assertEqual(ChannelHotTopics.objects.count(), 10)
        print_db_records()
        discard_outdated_topics_for_month_level(self.channel)
        self.assertEqual(ChannelHotTopics.objects.count(), 5)

class PurgingConvsAndRelated(MainCase):

    def _make_setup_for_conversations(self):
        account = Account.objects.get_or_create(name='Test', selected_app=APP_GSA)
        self.user.account = account
        self.user.save()
        self.sc = TwitterServiceChannel.objects.create_by_user(
            self.user,
            account=account,
            title='Service Channel')
        self.inbound = self.sc.inbound_channel
        self.outbound = self.sc.outbound_channel
        self.sc.save()
        self.outbound.usernames = ['test']
        self.outbound.save()
        self.channel = self.inbound
        self.contact = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        self.support = UserProfile.objects.upsert('Twitter', dict(screen_name='@test'))
        #settings.CHANNEL_ENTITIES_KEEP_DAYS = 0

    def test_purge_conversations_1(self):
        """ Deleting outdated conversation of two posts"""
        self._make_setup_for_conversations()
        self._create_db_post(
            channel=self.sc.inbound,
            content="I need a foo.",
            demand_matchables=True,
            user_profile={'screen_name': 'customer'}
        )
        self._create_db_post(
            channel=self.sc.inbound,
            content="Does anyone have a foo?",
            demand_matchables=True,
            user_profile={'screen_name': 'customer'}
        )

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Post.objects.count(), 2)
        self.assertEqual(SpeechActMap.objects.count(), 2)

        inbound_channel = Channel.objects.get(id=self.sc.inbound)
        purge_channel_entities(
            inbound_channel,
            run_in_prod_mod=True,
            now_date=now()+timedelta(days=get_var("CHANNEL_ENTITIES_KEEP_DAYS")+1))

        self.assertEqual(Conversation.objects.count(), 0)
        self.assertEqual(SpeechActMap.objects.count(), 0)
        self.assertEqual(Post.objects.count(), 0)

    def test_purge_conversations_2(self):
        """ Deleting outdated conversation using inbound and outbound channels """
        self._make_setup_for_conversations()
        # Generate inbound
        post = self._create_tweet(
            user_profile=self.contact,
            channels=[self.inbound],
            content="I need a foo. Does anyone have a foo?")

        # reply to post in outbound channels
        self._create_tweet(
            user_profile=self.support,
            channels=[self.outbound],
            content="I do",
            in_reply_to=post)

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Post.objects.count(), 2)
        self.assertEqual(SpeechActMap.objects.count(), 3)

        inbound_channel = Channel.objects.get(id=self.sc.inbound)
        purge_channel_entities(
            inbound_channel,
            run_in_prod_mod=True,
            now_date=now()+timedelta(days=get_var("CHANNEL_ENTITIES_KEEP_DAYS")+1))

        self.assertEqual(Conversation.objects.count(), 0)
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(SpeechActMap.objects.count(), 1)

        outbound_channel = Channel.objects.get(id=self.sc.outbound)
        purge_channel_entities(
            outbound_channel,
            run_in_prod_mod=True,
            now_date=now()+timedelta(days=get_var("CHANNEL_ENTITIES_KEEP_DAYS")+1))

        self.assertEqual(Conversation.objects.count(), 0)
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(SpeechActMap.objects.count(), 0)

    def test_purge_conversations_3(self):
        self._make_setup_for_conversations()
        self._create_db_post(
            channel=self.sc.inbound,
            content="I need a foo. Does anyone have a foo?",
            demand_matchables=True,
        )

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(SpeechActMap.objects.count(), 2)

        inbound_channel = Channel.objects.get(id=self.sc.inbound)
        purge_channel_entities(
            inbound_channel,
            run_in_prod_mod=True,
            now_date=now()+timedelta(days=get_var("CHANNEL_ENTITIES_KEEP_DAYS")-1))

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(SpeechActMap.objects.count(), 2)

    def test_outdated_posts_and_sas1(self):   
        self._make_setup_for_conversations()
        self._create_db_post(
            channel=self.sc.inbound,
            content="I need a foo. Does anyone have a foo?",
            demand_matchables=True )
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(SpeechActMap.objects.count(), 2)
        inbound_channel = Channel.objects.get(id=self.sc.inbound)
        purge_channel_outdated_posts_and_sas(
            inbound_channel, 
            now_date=now()+timedelta(days=get_var("CHANNEL_ENTITIES_KEEP_DAYS")+1),
            run_in_prod_mod=True)
        self.assertEqual(SpeechActMap.objects.count(), 0)
        self.assertEqual(Post.objects.count(), 0)

    def test_outdated_posts_and_sas2(self):   
        self._make_setup_for_conversations()
        self._create_db_post(
            channel=self.sc.inbound,
            content="I need a foo. Does anyone have a foo?",
            demand_matchables=True )
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(SpeechActMap.objects.count(), 2)
        inbound_channel = Channel.objects.get(id=self.sc.inbound)
        purge_channel_outdated_posts_and_sas(
            inbound_channel, 
            now_date=now()+timedelta(days=get_var("CHANNEL_ENTITIES_KEEP_DAYS")-1),
            run_in_prod_mod=True)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(SpeechActMap.objects.count(), 2)


def print_db_records():
    # print "Topics:"
    # for row in ChannelHotTopics.objects():
    #     print "{0: ^14s} | {1: ^4s}".format(row.topic, decode_timeslot(row.time_slot))
    # print
    print "Trends:"
    for row in ChannelTopicTrends.objects():
        print u"{0: ^14s} | {1: ^4s}".format(row.topic, decode_timeslot(row.time_slot))
    print
    print

