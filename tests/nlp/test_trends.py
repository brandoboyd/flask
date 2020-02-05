# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
"""
This are unit style tests for ChannelTrends.
For integration style tests see .test_trends_endpoints
"""

from dateutil.relativedelta import relativedelta

from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
from solariat_bottle.db.channel_hot_topics   import ChannelHotTopics
from solariat_bottle.db.channel_stats_base   import EmbeddedStats
from solariat_bottle.db.channel_trends       import ChannelTrends
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat.utils.timeslot import now, Timeslot
from solariat_bottle.scripts.reset_stats import do_it
from solariat_bottle.tests.base               import fake_twitter_url
from solariat_bottle.tasks import stats as stats_tasks
from solariat_bottle.tests.slow.test_conversations import ConversationBaseCase


class ChannelTrendsBaseCase(ConversationBaseCase):
    def _create_posts(self):
        """2 contacts posting 4 posts each.
        """
        posts = []
        posts_content = [
            "@test I need a laptop",
            "@test I like a laptop",
            "@test I need a foo.",
            "@test Can someone recommend a laptop?"]

        def creation_loop(user_profile):
            for content in posts_content:
                url = fake_twitter_url(user_profile.screen_name)
                posts.append(
                    self._create_db_post(
                        channel=self.inbound,
                        content=content,
                        demand_matchables=False,
                        url=url,
                        user_profile=user_profile))

        creation_loop(self.contact)

        self.contact2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        url = fake_twitter_url(self.contact.screen_name)
        creation_loop(self.contact2)
        return posts

    def _get_stats(self, level):
        stats = ChannelTrends.objects.by_time_span(
            self.channel,
            from_ts = Timeslot(level=level)
        )
        return tuple(stats)


class ChannelTrendsTestCase(ChannelTrendsBaseCase):
    def test_number_of_stats(self):
        content = "I need a mac laptop"
        '''
        stats count: 1 post x ("hour", "day")
        (in contrast with ChannelTopicTrends where each topic is counted)
        '''
        self._create_db_post(content)

        self.assertEqual(ChannelTrends.objects.count(), 1*2)

    def test_by_time_span(self):
        self._create_posts()
        for level in ('hour', 'day'):
            stats = self._get_stats(level)
            self.assertEqual(len(stats), 1)

    def test_embedded_stats(self):
        self._create_posts()
        for level in ('hour', 'day'):
            stats = self._get_stats(level)
            es = EmbeddedStats.unpack(stats[0].embedded_stats)
            self.assertEqual(es[0].response_volume, 0)
            self.assertEqual(es[0].response_time, 0)
            # 2x4, 4 posts from 2 contacts
            self.assertEqual(es[0].post_count, 8)

    def test_stats_status(self):
        posts = self._create_posts()
        self.assertEqual(len(posts), 8)

        stats = self._get_stats('hour')
        self.assertEqual(len(stats), 1)

        # reply to some posts - first posts from the first contact
        self._create_tweet(
            user_profile=self.support,
            content="We are doing our best",
            channel=self.outbound,
            in_reply_to=posts[0])

        stats = self._get_stats('hour')

        # two ChannelTrends with different statuses
        self.assertEqual(len(stats), 2)

        # reject a post - last post from the second contact
        posts[-1].handle_reject(self.support, [self.inbound])
        stats = self._get_stats('hour')

        # three ChannelTrends with different statuses
        self.assertEqual(len(stats), 3)


class ChannelStatsRecomputeCase(ChannelTrendsBaseCase):

    def _process_es(self, stat):
        es_data = []
        for data in stat.data['es']:
            keys = tuple(sorted(data.keys()))
            values = tuple(sorted(data.values()))
            es_data.append((keys, values))
        return tuple(es_data)

    def _store_existing_data(self):
        # Keep track of what was in database when this was called
        self.ctt = {}
        self.ctt_bk = {}
        self.cht = {}
        self.ct = {}
        self.ctt_count = ChannelTopicTrends.objects.count()
        self.cht_count = ChannelHotTopics.objects.count()
        self.ct_count = ChannelTrends.objects.count()
        for ctt in ChannelTopicTrends.objects():
            self.ctt_bk[ctt.data['_id']] = ctt.data
            self.ctt[ctt.data['_id']] = self._process_es(ctt)
        for cht in ChannelHotTopics.objects():
            self.cht[cht.data['_id']] = self._process_es(cht)
        for ct in ChannelTrends.objects():
            self.ct[ct.data['_id']] = self._process_es(ct)


    def _clear_existing_data(self):
        ChannelTopicTrends.objects.coll.remove({'_id' : {'$ne' : 0}})
        ChannelHotTopics.objects.coll.remove({'_id' : {'$ne' : 0}})
        ChannelTrends.objects.coll.remove({'_id' : {'$ne' : 0}})
        self.assertEqual(ChannelTopicTrends.objects.count(), 0)
        self.assertEqual(ChannelHotTopics.objects.count(), 0)
        self.assertEqual(ChannelTrends.objects.count(), 0)


    def _compare_existing_data(self):
        # Compare what is currently in database with what we have stored
        for ctt in ChannelTopicTrends.objects():
            for data in ctt.data['es']:
                keys = tuple(sorted(data.keys()))
                values = tuple(sorted(data.values()))
                self.assertTrue((keys, values) in self.ctt[ctt.data['_id']])
        for cht in ChannelHotTopics.objects():
            for data in cht.data['es']:
                keys = tuple(sorted(data.keys()))
                values = tuple(sorted(data.values()))
                self.assertTrue((keys, values) in self.cht[cht.data['_id']])
        for ct in ChannelTrends.objects():
            for data in ct.data['es']:
                keys = tuple(sorted(data.keys()))
                values = tuple(sorted(data.values()))
                self.assertTrue((keys, values) in self.ct[ct.data['_id']])


    def test_stats_recompute(self):
        url = fake_twitter_url(self.contact.screen_name)
        posts_content = [
            "@test I need a laptop",
            "@test I like a laptop",
            "@test I need a foo.",
            "@test Can someone recommend a laptop?"]

        previous_post = None
        for content in posts_content:
            url = fake_twitter_url(self.contact.screen_name)
            previous_post = self._create_db_post(channel=self.inbound, content=content,
                                 demand_matchables=False, url=url, user_profile=self.contact)
        # reply to some posts - first posts from the first contact
        self._create_tweet(user_profile=self.support, content="We are doing our best",
                           channel=self.outbound, in_reply_to=previous_post, url=fake_twitter_url(self.support.screen_name))
        url = fake_twitter_url(self.contact.screen_name)
        last_post = self._create_db_post(channel=self.inbound, content="I am also having car problems!",
                                         demand_matchables=False, url=url, user_profile=self.contact)
        last_post.handle_reject(self.support, [self.inbound])

        stats_tasks.MAX_BATCH_SIZE = 1

        to_date = now()
        from_date = now() - relativedelta(days=30)
        self._store_existing_data()
        # Just recomputing the stats should give us the same results
        do_it(account_name=self.inbound.account.name, ignore_purging=False,
              from_date=from_date, to_date=to_date)
        self.assertTrue(ChannelTopicTrends.objects.count() == self.ctt_count)
        self.assertTrue(ChannelHotTopics.objects.count() == self.cht_count)
        self.assertEqual(ChannelTrends.objects.count(), self.ct_count)
        self._compare_existing_data()
        do_it(account_name=self.inbound.account.name, ignore_purging=True,
              from_date=from_date, to_date=to_date)
        self.assertTrue(ChannelTopicTrends.objects.count() == self.ctt_count)
        self.assertTrue(ChannelHotTopics.objects.count() == self.cht_count)
        self.assertEqual(ChannelTrends.objects.count(), self.ct_count)
        self._compare_existing_data()

        # Now if we remove existing data we should get rhoughly the same results
        # Stats with counts of 0 won't matter anymore
        self._clear_existing_data()
        do_it(account_name=self.inbound.account.name, ignore_purging=True,
              from_date=from_date, to_date=to_date)
        # We had actionable switched to actual / rejected. In db we don't remove entries where count=0
        # So now that we cleared all then recomputed (recovery mode) we will have less entries
        self.assertTrue(ChannelTopicTrends.objects.count() < self.ctt_count)
        self.assertTrue(ChannelHotTopics.objects.count() < self.cht_count)
        self.assertTrue(ChannelTrends.objects.count() < self.ct_count)
        self._compare_existing_data()

