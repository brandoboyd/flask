# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_nlp.utils.topics import get_largest_subtopics, gen_topic_tree

from solariat_bottle.tests.base import MainCase, datasift_date_format
from solariat_bottle.db.channel_stats_base import ExtendedEmbeddedStats, ALL_AGENTS, ALL_INTENTIONS_INT
from solariat_bottle.db.channel_hot_topics import ChannelHotTopics
from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
from solariat_bottle.db.channel.twitter    import TwitterServiceChannel
from solariat_bottle.db.post.base          import Post, SpeechActMap
from solariat_bottle.db.account            import Account
from solariat.utils.timeslot import datetime_to_timeslot, now, parse_date, Timeslot
from solariat.utils.lang.support import Lang
from solariat_bottle.utils.hash            import mhash
from solariat_bottle.utils.id_encoder      import ALL_TOPICS


def stat_construct(args):
    agent, is_leaf, intention, language, _ = args
    return ExtendedEmbeddedStats(agent=agent,
                                 is_leaf=is_leaf,
                                 intention=intention,
                                 language=language)

Leaf = Topic = True
Node = Term = False
HELP = 10
JUNK = 12
EN = Lang.EN
LALL = Lang.ALL


class BaseStatsCase(MainCase):
    def assert_stats(self, stat, expected_stats):
        stats = ExtendedEmbeddedStats.unpack(stat.embedded_stats)
        self.assertEqual(set(stats), set(map(stat_construct, expected_stats)))

        for (agent, is_leaf, intention, language, topic_count) in expected_stats:
            filtered = stat.filter(
                agent     = agent,
                is_leaf   = is_leaf,
                intention = intention,
                language  = language
            )
            self.assertEqual(len(filtered), 1, repr(filtered))
            self.assertEqual(filtered[0].topic_count, topic_count)


class HotTopicsCase(BaseStatsCase):

    def test_stat_update(self):
        Leaf = Topic = True
        Node = Term = False
        HELP = 10
        JUNK = 12
        EN = Lang.EN
        LALL = Lang.ALL

        time_slot = datetime_to_timeslot(now(), 'day')

        topic = 'laptop'
        agent_id = 12345
        hashed_parents = map(mhash, get_largest_subtopics(topic))

        stat = ChannelHotTopics(channel_num=self.channel.counter,
                                time_slot=time_slot,
                                topic=topic,
                                status=0,
                                hashed_parents=hashed_parents)

        stat.compute_increments(is_leaf=True, intention_id=JUNK, agent=None, lang_id=Lang.EN, n=1)
        stat.compute_increments(is_leaf=False, intention_id=HELP, agent=None, lang_id=Lang.EN, n=1)
        stat.upsert()
        stat = ChannelHotTopics.objects.get(id=stat.id)
        stat.compute_increments(is_leaf=True, intention_id=JUNK, agent=agent_id, n=2)
        stat.upsert()

        stat.reload()

        expected_stats = [
            # agent | is_leaf | intent | language | topic_count
            (ALL_AGENTS, Term,  ALL_INTENTIONS_INT, LALL, 1),
            (ALL_AGENTS, Term,  ALL_INTENTIONS_INT, EN,   1),
            (ALL_AGENTS, Term,  HELP,               LALL, 1),
            (ALL_AGENTS, Term,  HELP,               EN,   1),

            (ALL_AGENTS, Topic, ALL_INTENTIONS_INT, LALL, 1 + 2),  # +2 from specific agent
            (ALL_AGENTS, Topic, JUNK,               LALL, 1 + 2),
            (ALL_AGENTS, Topic, JUNK,               EN,   1),
            (ALL_AGENTS, Topic, ALL_INTENTIONS_INT, EN,   1),

            (agent_id,   Topic, ALL_INTENTIONS_INT, LALL, 2),
            (agent_id,   Topic, JUNK,               LALL, 2)
        ]

        self.assert_stats(stat, expected_stats)

        self.assertFalse(stat.filter(agent=0, is_leaf=True, intention=10))  #no such combination

    def test_stats_retrieving(self):
        time_slot = datetime_to_timeslot(now(), 'day')
        topics = ('laptop', 'laptop bag', 'good laptop bag', 'good laptop')
        for topic in topics:
            for term, is_leaf in gen_topic_tree(topic):
                ChannelHotTopics.increment(
                    self.channel, time_slot, term, status=0, intention_id=0,
                    is_leaf=is_leaf, lang_id=Lang.EN, agent=1)

        stats = ChannelHotTopics.objects.by_time_span(
            channel=self.channel,
            from_ts=datetime_to_timeslot(None, 'day'),
            languages=['en'])

        expected_result = [{u'term_count': 2, u'topic': u'laptop', u'topic_count': 1},
                           {u'term_count': 2, u'topic': u'bag', u'topic_count': 0}]

        self.assertListEqual(stats, expected_result)


class TopicTrendsCase(BaseStatsCase):
    def test_stat_update(self):
        time_slot = datetime_to_timeslot(now(), 'hour')

        topic = 'laptop'
        agent_id = 12345

        stat = ChannelTopicTrends(channel=self.channel,
                                time_slot=time_slot,
                                topic=topic,
                                status=0)

        stat.compute_increments(is_leaf=True, intention_ids=JUNK, agent=None,
                                inc_dict={'topic_count': 1}, n=1)
        stat.compute_increments(is_leaf=False, intention_ids=HELP, agent=None,
                                inc_dict={'topic_count': 1}, n=1)
        stat.upsert()

        stat = ChannelTopicTrends.objects.get(id=stat.id)

        stat.compute_increments(is_leaf=True, intention_ids=JUNK, agent=agent_id,
                                inc_dict={'topic_count': 2}, n=1)

        stat.compute_increments(is_leaf=False,
                                intention_ids=HELP,
                                agent=None,
                                lang_id=EN,
                                inc_dict={'topic_count': 2}, n=1)
        stat.upsert()

        stat.reload()

        expected_stats = [
            (ALL_AGENTS,    Term,   ALL_INTENTIONS_INT,     LALL,   1 + 2),  # +2 for EN
            (ALL_AGENTS,    Term,   HELP,                   LALL,   1 + 2),

            (ALL_AGENTS,    Term,   ALL_INTENTIONS_INT,     EN,     2),
            (ALL_AGENTS,    Term,   HELP,                   EN,     2),

            (ALL_AGENTS,    Topic,  ALL_INTENTIONS_INT,     LALL,   1 + 2),  # +2 from specific agent
            (ALL_AGENTS,    Topic,  JUNK,                   LALL,   1 + 2),
            (agent_id,      Topic,  ALL_INTENTIONS_INT,     LALL,   2),
            (agent_id,      Topic,  JUNK,                   LALL,   2)
        ]

        self.assert_stats(stat, expected_stats)

        self.assertFalse(stat.filter(agent=0, is_leaf=True, intention=10))  # no such combination


class SAMAndStatsCase(MainCase):
    def test_multi_post(self):
        contents = ['Any recommendations for a basketball scholarship? I need a basketball scholarship.',
                    'Any recommendations for a basketball scholarship? I need a basketball scholarship.',
                    'I love my display!',
                    'My display is just not working out for me :-(',
                    'Any recommendations for a display?',
                    'I like my display'
                    ]

        for content in contents:
            post = self._create_db_post(content, channel=self.channel)

        from solariat_bottle.db.speech_act import SpeechActMap

        stats_by_topic_intention = {}

        #Calculating stats iterating through SAM
        from solariat_bottle.db.post.base import Post
        for post in Post.objects(channels__in=[self.channel.id]):
            for sa in post.speech_acts:
                topics = sa['intention_topics']
                int_id = sa['intention_type_id']
                topics.append('__ALL__')
                for topic in topics:
                    if topic in stats_by_topic_intention:
                        if str(int_id) in stats_by_topic_intention[topic]:
                            stats_by_topic_intention[topic][str(int_id)] += 1
                        else:
                            stats_by_topic_intention[topic][str(int_id)] = 1
                    else:
                        stats_by_topic_intention[topic] = {str(int_id): 1}

        expected_stats_from_sam = {u'basketball scholarship': {'1': 2, '2': 2},
                                   u'display': {'1': 1, '3': 1, '4': 2},
                                   '__ALL__': {'1': 3, '3': 1, '2': 2, '4': 2}}

        self.assertDictEqual(stats_by_topic_intention, expected_stats_from_sam)

        time_slot = datetime_to_timeslot(Post.objects(channels__in=[self.channel.id]).limit(1)[0].created_at, 'hour')
        status = SpeechActMap.ACTIONABLE

        #Now verify SAM stats correspond to ChannelTopicTrends stats
        for topic, sa_stats in stats_by_topic_intention.iteritems():
            if topic == '__ALL__':
                continue

            stat = ChannelTopicTrends(channel=self.channel,
                                      time_slot=time_slot,
                                      topic=topic,
                                      status=status)
            stat.reload()
            ctt_by_int = {}
            filtered = stat.filter(is_leaf=True, intention__ne=0)

            for s in filtered:
                ctt_by_int[str(s.intention)] = s.topic_count
            self.assertDictEqual(ctt_by_int, sa_stats)


class StatusTransitionCase(MainCase):
    def setUp(self):
        super(StatusTransitionCase, self).setUp()
        account = Account.objects.get_or_create(name='Test')
        account.add_perm(self.user)

        self.sc = TwitterServiceChannel.objects.create_by_user(
            self.user,
            account=account,
            title='Service Channel')
        self.inbound = self.sc.inbound_channel
        self.outbound = self.sc.outbound_channel
        self.outbound.usernames = ['brand']
        self.outbound.save()
        self.sc.save()

    def get_stats(self, channel, agents):
        statuses = [SpeechActMap.POTENTIAL, SpeechActMap.ACTIONABLE, SpeechActMap.ACTUAL, SpeechActMap.REJECTED]
        stats = ChannelTopicTrends.objects.by_time_span(
            channel      = channel,
            from_ts      = Timeslot(0),
            to_ts        = Timeslot(None),
            statuses     = statuses,
            group_by     = 'status',
            plot_by      = 'distribution',
            plot_type    = 'topics',
            agents       = agents,
            no_transform = True)

        result = {}
        for status in statuses:
            result.setdefault(status, 0)
        for s in stats:
            result[int(s['_id']['grp'])] = s['count']
        return result

    def get_inbound_stats(self, agents=None):
        return self.get_stats(self.inbound, agents)

    def get_outbound_stats(self, agents=None):
        return self.get_stats(self.outbound, agents)

    def get_inbound_post(self):
        statuses = [SpeechActMap.POTENTIAL, SpeechActMap.ACTIONABLE, SpeechActMap.ACTUAL, SpeechActMap.REJECTED]
        time_slot = datetime_to_timeslot(self.inbound_post_created_at, 'hour')
        posts, are_more_posts_available = Post.objects.by_time_point(self.inbound, ALL_TOPICS, time_slot, status=statuses)
        self.assertEqual(len(posts), 1)
        return posts[0]

    def test_status(self):
        from solariat_bottle.db.user import User
        agent = User(email='agent@test.test')
        agent.signature = '^AG'
        agent.save()
        self.sc.account.add_user(agent)

        # Create inbound post
        self.inbound_post_created_at = parse_date("05/07/2013")
        parent_id = "123456789"
        twitter_data = {'twitter':{'id': parent_id,
                                   'created_at': datasift_date_format(self.inbound_post_created_at)}}
        self.inbound_post = self._create_db_post(
            channels=[self.inbound],
            content="@brand I need a foo. Does anyone have a foo? ",
            **twitter_data)
        self.inbound_post.reload()
        self.assertTrue(self.inbound.is_assigned(self.inbound_post))

        agents = None
        inbound_post = self.get_inbound_post()
        self.assertEqual(len(inbound_post.channel_assignments), 1)
        self.assertEqual(inbound_post.channel_assignments[str(self.inbound.id)], 'highlighted')

        stats = self.get_inbound_stats(agents)
        self.assertEqual(stats[SpeechActMap.POTENTIAL], 0)
        self.assertEqual(stats[SpeechActMap.ACTUAL], 0)
        self.assertEqual(stats[SpeechActMap.ACTIONABLE], 2)
        self.assertEqual(stats[SpeechActMap.REJECTED], 0)

        # Reply to inbound post
        twitter_data['twitter']['id'] = '987654231'
        twitter_data['twitter']['in_reply_to_status_id'] = parent_id
        twitter_data['twitter']['created_at'] = datasift_date_format(now())
        self.outbound_post = self._create_db_post(
            user_profile={'user_name': 'agent_test_name'},
            channels=[self.outbound],
            content="Response content. ^AG",
            **twitter_data)

        self.inbound_post.reload()
        self.outbound_post.reload()

        for agents in (None, [agent]):
            stats = self.get_inbound_stats(agents)
            self.assertEqual(stats[SpeechActMap.POTENTIAL], 0)
            self.assertEqual(stats[SpeechActMap.ACTUAL], 2)
            self.assertEqual(stats[SpeechActMap.ACTIONABLE], 0)
            self.assertEqual(stats[SpeechActMap.REJECTED], 0)

            stats = self.get_outbound_stats(agents)
            self.assertEqual(stats[SpeechActMap.POTENTIAL], 0)
            self.assertEqual(stats[SpeechActMap.ACTUAL], 0)
            self.assertEqual(stats[SpeechActMap.ACTIONABLE], 1)
            self.assertEqual(stats[SpeechActMap.REJECTED], 0)

        self.assertEqual(self.inbound_post.channel_assignments[str(self.inbound.id)], 'replied')
        self.assertEqual(len(self.inbound_post.channel_assignments), 1)

        inbound_post = self.get_inbound_post()
        self.assertEqual(len(inbound_post.channel_assignments), 1)
        self.assertEqual(inbound_post.channel_assignments[str(self.inbound.id)], 'replied')

