from solariat_bottle.tests.base import BaseCase
from solariat_bottle.db.channel.base import Channel, CompoundChannel
from solariat_bottle.db.channel.twitter import UserTrackingChannel, KeywordTrackingChannel
from solariat_bottle.db.post.base import find_channels_and_compounds
import unittest


@unittest.skip('deprecating for now as this proved not to be a very good idea.')
class CompoundChannelCase(BaseCase):
    def setUp(self):
        BaseCase.setUp(self)

        self.channel1 = UserTrackingChannel.objects.create_by_user(self.user, title="UserTracking1")
        self.channel2 = KeywordTrackingChannel.objects.create_by_user(self.user, title="KeywordTracking1")
        self.channel3 = KeywordTrackingChannel.objects.create_by_user(self.user, title="KeywordTracking2")
        self.channel4 = UserTrackingChannel.objects.create_by_user(self.user, title="UserTracking2")

        self.compound_channel1 = CompoundChannel.objects.create_by_user(self.user, title="CompoundChannel1")
        self.compound_channel1.channels = [self.channel1, self.channel2]
        self.compound_channel1.save()

        self.compound_channel2 = CompoundChannel.objects.create_by_user(self.user, title="CompoundChannel2")
        self.compound_channel2.channels = [self.channel3, self.channel4]
        self.compound_channel2.save()

        self.compound_channel3 = CompoundChannel.objects.create_by_user(self.user, title="CompoundChannel3")
        self.compound_channel3.channels = [self.channel2, self.channel3]
        self.compound_channel3.save()

        self.standalone_channel = UserTrackingChannel.objects.create_by_user(self.user, title="UserTracking3")

    def test_find_channels_and_compounds(self):
        """
        C1 = [1, 2]
        C2 = [3, 4]
        C3 = [2, 3]
        """
        channels = find_channels_and_compounds([self.channel1], self.user)
        self.assertTrue(self.channel1 in  channels)
        self.assertTrue(self.channel2 in  channels)
        self.assertTrue(self.compound_channel1 in  channels)

        self.assertFalse(self.channel3 in  channels)
        self.assertFalse(self.channel4 in  channels)
        self.assertFalse(self.compound_channel2 in  channels)
        self.assertFalse(self.compound_channel3 in  channels)

        channels = find_channels_and_compounds([self.channel2], self.user)
        self.assertTrue(self.channel1 in  channels)
        self.assertTrue(self.channel2 in  channels)
        self.assertTrue(self.channel3 in  channels)
        self.assertTrue(self.compound_channel1 in  channels)
        self.assertTrue(self.compound_channel3 in  channels)

        self.assertFalse(self.channel4 in  channels)
        self.assertFalse(self.compound_channel2 in  channels)

        channels = find_channels_and_compounds([self.standalone_channel], self.user)
        self.assertTrue(self.standalone_channel in channels)

    def test_post_creation(self):
        content = 'I need a bike . I like Honda .'
        post = self._create_db_post(
            channel=self.channel1,
            content=content)
        post.reload()

        #post should appear in compound_channel1 and channel2
        post_channels = list(Channel.objects(id__in=post.channels))
        self.assertTrue(self.compound_channel1 in post_channels)
        self.assertTrue(self.channel2 in post_channels)
        self.assertTrue(self.channel1 in post_channels)

    def test_post_creation_chain(self):
        content = 'I need a bike . I like Honda .'
        post = self._create_db_post(
            channel=self.channel2,
            content=content)
        post.reload()

        post_channel_ids = post.channels
        self.assertTrue(self.compound_channel1.id in post_channel_ids)
        self.assertTrue(self.compound_channel3.id in post_channel_ids)
        self.assertTrue(self.channel1.id in post_channel_ids)
        self.assertTrue(self.channel2.id in post_channel_ids)
        self.assertTrue(self.channel3.id in post_channel_ids)
