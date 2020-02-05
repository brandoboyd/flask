
from solariat_bottle          import settings
from solariat_bottle.settings import get_var

from solariat_bottle.tests.slow.test_smarttags import SmartTagsBaseCase


class SmartTagExtensions(SmartTagsBaseCase):

    def setUp(self):
        SmartTagsBaseCase.setUp(self)

        self.orig_filter_class = get_var('CHANNEL_FILTER_CLS')
        settings.CHANNEL_FILTER_CLS = 'OnlineChannelFilter'

        self.customer.klout_score = 50
        self.customer.save()

        # Parent Keywords
        self.sc.inbound_channel.keywords = ['camera']
        self.sc.inbound_channel.save()

        # Brand Handle
        self.sc.outbound_channel.usernames = ['brand']
        self.sc.outbound_channel.save()

        self.tag = self._create_smart_tag(self.sc.inbound_channel, 'Tag', status='Active',
                                          keywords=['luggage', 'long delays'],
                                          skip_keywords=['skip'])

    def tearDown(self):
        SmartTagsBaseCase.tearDown(self)

        settings.CHANNEL_FILTER_CLS = self.orig_filter_class


    def find_features(self, tag, post, expected_features):
        self.expect_features(tag, post, expected_features, True)

    def ignore_features(self, tag, post, expected_features):
        self.expect_features(tag, post, expected_features, False)

    def expect_features(self, channel, post, expected_features, present):
        feature_vector = channel.channel_filter.extract_features(post)
        if present:
            self.assertEqual(set(feature_vector) & expected_features, expected_features,
                             "MISSING [%s]" % ", ".join(expected_features - set(feature_vector)))
        else:
            self.assertFalse(set(feature_vector) & expected_features,
                             "LEFT WITH [%s]" % ", ".join(set(feature_vector) & expected_features))


    def test_post_vector_smart_tags(self):
        ''' The post should be tagged, and the tag should be added. Also the opposite case'''
        post = self._create_tweet('My luggage is lost',
                                  channel=self.sc.inbound_channel,
                                  user_profile=self.customer)
        self.find_features(self.sc.inbound_channel, post, {'__TAG__'})

        post = self._create_tweet('My cat is lost',
                                  channel=self.sc.inbound_channel,
                                  user_profile=self.customer)
        self.ignore_features(self.sc.inbound_channel, post, {'__TAG__'})

    def test_post_vector_kw(self):
        post = self._create_tweet('My camera is lost. The luggage is broken and my flight has been delays. I will have to skip.',
                                  channel=self.sc.inbound_channel,
                                  user_profile=self.customer)

        self.find_features(self.tag, post, {'camera', 'luggage', 'skip', '__UNKNOWN__'})
        self.ignore_features(self.tag, post, {'__KLOUT__', 'long delays'})

    def test_post_vector_whole_word(self):
        post = self._create_tweet('My camera is lost. The luggage is broken and my flight has been long delays. I will have to skip.',
                                  channel=self.sc.inbound_channel,
                                  user_profile=self.customer)

        self.find_features(self.tag, post, {'long delays'})

    def test_direct_vs_indirect(self):
        post = self._create_tweet('@brand My camera is lost :-(',
                                  channel=self.sc.inbound_channel,
                                  user_profile=self.customer)

        self.find_features(self.tag, post, {'__DIRECT__'})

    def test_klout(self):
        # Have it
        self.tag.influence_score = 30
        self.tag.save()

        post = self._create_tweet('@brand My camera is lost :-(',
                                  channel=self.sc.inbound_channel,
                                  user_profile=self.customer)

        self.find_features(self.tag, post, {'__KLOUT__'})

        # Skip it
        self.tag.influence_score = 80
        self.tag.save()
        self.ignore_features(self.tag, post, {'__KLOUT__'})



