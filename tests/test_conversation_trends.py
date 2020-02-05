"""
This are unit style tests for ConversationTrends.
"""

from uuid import uuid4
import unittest
from itertools import product
from datetime import datetime as dt
from solariat_bottle.db.conversation import ConversationManager

from ..db.conversation_trends  import ConversationQualityTrends, ConversationEmbeddedStats
from ..db.channel_stats_base   import ALL_AGENTS
from ..db.user_profiles.user_profile import UserProfile
from ..db.conversation         import Conversation
from ..db.roles                import AGENT
from solariat.utils.timeslot          import Timeslot
from .base               import fake_status_id
from .slow.test_conversations import ConversationBaseCase

@unittest.skip("This is no longer used, will need to be updated or removed")
class ConversationQualityTrendsCase(ConversationBaseCase):

    def setUp(self):
        ConversationBaseCase.setUp(self)
        self.setup_users()

    def setup_users(self):
        self.outbound.usernames = ['support']
        self.outbound.save()
        user = self._create_db_user(
            email='foo@solariat.com',
            password='12345',
            roles=[AGENT])
        user2 = self._create_db_user(
            email='foo2@solariat.com',
            password='12345',
            roles=[AGENT])
        user.agent_id = 4
        user2.agent_id = 5
        user.save()
        user2.save()
        self.contact = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        self.support = UserProfile.objects.upsert('Twitter', dict(screen_name='@brand', user_id=str(user.id)))
        self.support.user = user
        self.support2 = UserProfile.objects.upsert('Twitter', dict(screen_name='@brand2', user_id=str(user2.id)))
        self.support2.user = user2
        self.sc.agents=[user, user2]
        self.sc.save()
        self.sc.reload()

    def _create_conversation(self, topic="laptop", quality="unknown", agent=None):
        """2 contacts (customer and brand) posting 4 posts. """
        posts_content = [
            "@customer my %s is broken." % topic,
            "@support please try to reset your %s" % topic,
            "@customer fidn't help, %s doesn't work" % topic,
            "@support we will send you a new %s" % topic]
        agent = agent if agent else self.support
        status_id1 = fake_status_id()
        status_id2 = fake_status_id()
        status_id3 = fake_status_id()
        status_id4 = fake_status_id()
        self.contact = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer_%s' % uuid4()))
        post1 = self._create_db_post(
            channel=self.inbound,
            content=posts_content[0],
            demand_matchables=False,
            user_profile=self.contact,
            twitter=dict(
                id=status_id1))

        self._create_db_post(
            channel=self.outbound,
            content=posts_content[1],
            demand_matchables=False,
            user_profile=agent,
            twitter=dict(
                id=status_id2,
                in_reply_to_status_id=status_id1))

        self._create_db_post(
            channel=self.inbound,
            content=posts_content[2],
            demand_matchables=False,
            user_profile=self.contact,
            twitter=dict(
                id=status_id3,
                in_reply_to_status_id=status_id2))

        self._create_db_post(
            channel=self.outbound,
            content=posts_content[3],
            demand_matchables=False,
            user_profile=agent,
            twitter=dict(
                id=status_id4,
                in_reply_to_status_id=status_id3))

        self.assertEqual(Conversation.objects(posts=post1.id).count(), 1)
        conversation = Conversation.objects(posts=post1.id)[0]
        self.assertEqual(len(conversation.posts), 4)
        return conversation


    def __print_trends(self):
        """just a utility function"""
        for i, trend in enumerate(ConversationQualityTrends.objects()):
            print i, trend

    def _get_stats(self, closing_time, level, category=None):
        time_slot = Timeslot(closing_time, level)
        data = {"time_slot": time_slot.timeslot}
        if category is not None:
            category  = ConversationQualityTrends.get_category_code(category)
            data["category"] = category
        stats = [x for x in ConversationQualityTrends.objects(**data)]
        return stats

    def test_simple(self):
        """ 
        Simpliest case: close conversation and check that two 
        trends with correct levels have appeared in db
        """
        now = dt.now()
        conversation = self._create_conversation()
        conversation.close(closing_time=now)
        self.assertEqual(ConversationQualityTrends.objects.count(), 2)
        for level in ("day", "hour"):
            self.assertEqual(len(self._get_stats(now, "day")), 1)

    def test_several_conversations(self):
        """
        1. Create four conversations with different quality values
        2. Check number of trends in db
        3. Check embedded stats for these trends
        """
        now = dt.now()
        self._create_conversation(topic="iphone").close(closing_time=now, quality="unknown")
        self._create_conversation(topic="laptop").close(closing_time=now, quality="win")
        self._create_conversation(topic="samsung").close(closing_time=now, quality="win")
        self._create_conversation(topic="camera").close(closing_time=now, quality="loss")
        self.assertEqual(Conversation.objects.count(), 4)
        # self.__print_trends()
        self.assertEqual(ConversationQualityTrends.objects.count(), 6)
        for level, category in product(('hour', 'day'), ConversationQualityTrends.CATEGORY_MAP.keys()):
            stats = self._get_stats(closing_time=now, level=level, category=category)
            self.assertEqual(len(stats), 1)
            es = ConversationEmbeddedStats.unpack(stats[0].embedded_stats)
            self.assertEqual(len(es), 2)
            for es_item in es:
                if stats[0].category == ConversationQualityTrends.CATEGORY_MAP["win"]:
                    self.assertEqual(es_item["count"], 2)
                else:
                    self.assertEqual(es_item["count"], 1)

    def test_no_trends(self):
        """ Conversation wasn't closed, so there should be no trends in db
        """
        self._create_conversation(topic="laptop")
        self._create_conversation(topic="camera")
        self.assertEqual(Conversation.objects.count(), 2)
        self.assertEqual(ConversationQualityTrends.objects.count(), 0) # <-- we haven't close any conversation

    def test_two_agents(self):
        """ Two conversations were engaged by one agent.
        One more conversation was engaged by other agent.
        Check number of trends in db and check embedded stats of these  trends.
        """
        now = dt.now()
        self._create_conversation(topic="iphone", agent=self.support2).close(closing_time=now, quality="unknown")
        self._create_conversation(topic="ipod", agent=self.support).close(closing_time=now, quality="unknown")
        self._create_conversation(topic="ipad", agent=self.support).close(closing_time=now, quality="unknown")
        self.assertEqual(Conversation.objects.count(), 3)
        self.assertEqual(ConversationQualityTrends.objects.count(), 2)
        stats = self._get_stats(closing_time=now, level="day", category="unknown")
        es    = ConversationEmbeddedStats.unpack(stats[0].embedded_stats)
        self.assertEqual(len(es), 3)
        es_dict = {item.agent: item.count for item in es}
        self.assertEqual(es_dict[ALL_AGENTS], 3)
        self.assertEqual(es_dict[self.support.user.agent_id], 2)
        self.assertEqual(es_dict[self.support2.user.agent_id], 1)

    def test_merge_conversation(self):

        self._create_conversation()
        self._create_conversation()
        convs = Conversation.objects.find()[:]
        self.assertEqual(len(convs), 2)
        self.assertEqual(len(convs[0].posts), 4)
        merged = ConversationManager.merge_conversations(convs)
        convs = Conversation.objects.find()[:]
        self.assertTrue(len(convs) == 1)
        self.assertEqual(len(convs[0].posts), 8)
        self.assertEqual(len(merged.posts), 8)
