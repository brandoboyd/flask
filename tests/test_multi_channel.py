from ..db.channel.base import Channel
from ..db.channel_stats import ChannelStats, get_levels
from ..db.channel_hot_topics import ChannelHotTopics
import base


class PostCase(base.MainCase):
    'Test multi-channel scenarios'

    def setUp(self):
        super(PostCase, self).setUp()

        self.permissive_channel =  Channel.objects.create_by_user(
            self.user, title='Permissive',
            type='twitter', intention_types=base.SA_TYPES)

        self.restrictive_channel =  Channel.objects.create_by_user(
            self.user, title='Restrictive',
            type='twitter', intention_types=["Asks for Something"])

        self.channel = Channel.objects.create_by_user(
            self.user, title='TestChannel',
            type='twitter', intention_types=base.SA_TYPES)

        self.channels = [self.channel,
                         self.permissive_channel,
                         self.restrictive_channel]

        self.channel.add_perm(self.user)

    def test_simple_post_creation(self):
        content = 'I need a bike. I like honda.'
        post = self._create_db_post(
            channels=self.channels,
            content=content)

        for channel in [self.channel,
                        self.permissive_channel]:
            for stats in get_levels(self.channel):
                stats.reload()
                self.assertEqual(
                    stats.number_of_posts, 1)
                self.assertEqual(
                    stats.feature_counts['2'], 1)
                self.assertEqual(
                    stats.feature_counts['4'], 1)

            self.assertEqual(ChannelHotTopics.objects(
                hashed_parents=[],
                topic='bike',
                channel_num=channel.counter)[0].filter(intention=0, is_leaf=True)[0].topic_count, #"all intentions"."leaf"
            1)

    def test_permissive(self):
        'ALL Channels Fit'
        content = 'Where can I find a good bike?'
        post = self._create_db_post(
            channels=self.channels,
            content=content)

        self.assertEqual(ChannelStats.objects.count(), 3*3)
        self.assertEqual(ChannelHotTopics.objects(hashed_parents=[],
                                                  topic='bike').count(), 3*2)

