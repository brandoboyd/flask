import unittest

from datetime import datetime, timedelta

from bson.objectid import ObjectId

from solariat_bottle.tests.base import MainCase

from solariat_bottle.db.post.base import Post
from solariat_bottle.db.channel_stats import ChannelStats
from solariat_bottle.db.channel.base import SmartTagChannel
from solariat_bottle.db.channel_stats import aggregate_stats


class StatsCase(MainCase):
    def setUp(self):
        MainCase.setUp(self)
        past_id = ObjectId.from_datetime(
            datetime.now() - timedelta(minutes=7*24*60))
        post1 = self._create_db_post(
            id=past_id, channel=self.channel,
            content = 'i need some foo')
        #Post.objects.insert(post1.data)

        past_id = ObjectId.from_datetime(
            datetime.now() - timedelta(minutes=7*24*60+10))
        post2 = self._create_db_post(
            id=past_id, channel=self.channel,
            content='where i can find a foo?')
        #Post.objects.insert(post2.data)

        post3 = self._create_db_post(
            channel=self.channel, content='i need some foo')
        post4 = self._create_db_post(
            channel=self.channel, content='where i can find a foo?')
        post5 = self._create_db_post(channel=self.channel, content='LOL')
        self.assertEqual(Post.objects(channels__in=[self.channel.id]).count(), 5)

    def test_numbers(self):
        month_stats = list(ChannelStats.objects.by_time_span(
            self.user, self.channel, level='month'))
        number_of_posts = sum([x.number_of_posts for x in month_stats])
        number_of_actionable_posts = sum([
                x.number_of_actionable_posts for x in month_stats])
        self.assertEqual(number_of_posts, 5)


class ClassifierStatsCase(MainCase):

    def setUp(self):
        MainCase.setUp(self)
        self.smart_tag = SmartTagChannel.objects.create_by_user(
                                                        self.user,
                                                        title="stats_tag",
                                                        status='Active',
                                                        keywords=['laptop'],
                                                        parent_channel=self.channel.id,
                                                        account=self.channel.account)
        self.channel.keywords.append("laptop")

    def _get_stats(self, channel_or_smart_tag):
        return aggregate_stats(
            self.user, channel_or_smart_tag.id,
            from_=None, to_=None, 
            level='month',
            aggregate=(
                'number_of_false_negative',
                'number_of_true_positive',
                'number_of_false_positive')
            )[str(channel_or_smart_tag.id)]


    def test_channel_stats(self):
        post = self._create_db_post(channel=self.channel,
                                         content='i need some laptop')
        post2 = self._create_db_post(channel=self.channel,
                                         content='My laptop is broken')
        post2_similar = self._create_db_post(channel=self.channel,
                                         content='My laptop is broken again')

        # replying to a post case
        post.handle_reply(self.user, [self.channel])
        stats = self._get_stats(self.channel)
        self.assertEqual(stats["number_of_true_positive"], 1)

        # rejecting post case
        self.assertTrue(self.channel.is_assigned(post2))
        self.assertTrue(self.channel.is_assigned(post2_similar))
        # rejecting one post
        post2.handle_reject(self.user, [self.channel])
        post2.reload()
        post2_similar.reload()
        stats = self._get_stats(self.channel)
        self.assertFalse(self.channel.is_assigned(post2))
        # similar post should be rejected now too
        self.assertFalse(self.channel.is_assigned(post2_similar))
        # but stats should count only first post
        self.assertEqual(stats["number_of_false_positive"], 1)

        # accepting post
        post2.handle_accept(self.user, [self.channel])
        stats = self._get_stats(self.channel)
        self.assertEqual(stats["number_of_false_negative"], 1)


    def test_smart_tag_stats(self):
        post = self._create_db_post(channel=self.channel,
                                         content='i need some laptop')
        # adding tag scenario
        post.set_assignment(self.smart_tag, "rejected")
        # post.tag_assignments.get(str(self.smart_tag.id))
        post.handle_add_tag(self.user, [self.smart_tag])
        # post.tag_assignments.get(str(self.smart_tag.id))
        stats = self._get_stats(self.smart_tag)
        self.assertEqual(stats["number_of_false_negative"], 1)

        # removing tag scenario
        post.handle_remove_tag(self.user, [self.smart_tag])
        stats = self._get_stats(self.smart_tag)
        self.assertEqual(stats["number_of_false_positive"], 1)

        # confirming tag (which was assigned automatically) scenario
        post = self._create_db_post('i need a laptop')
        post_status = post.get_assignment(self.smart_tag, tags=True)
        # Keep adding smart tag to similar post until we get a default
        # of highlighted.
        while post_status == 'discarded':
            post.handle_add_tag(self.user, [self.smart_tag])
            post = self._create_db_post(channel=self.channel,
                                        content='i need a laptop')
            post_status = post.get_assignment(self.smart_tag, tags=True)
        
        post.handle_add_tag(self.user, [self.smart_tag])
        stats = self._get_stats(self.smart_tag)
        self.assertEqual(stats["number_of_true_positive"], 1)


