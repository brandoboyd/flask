# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_bottle          import settings
from solariat_bottle.settings import get_var

from solariat_bottle.db.channel.twitter import TwitterChannel
from solariat_bottle.db.channel_filter  import (
    OnlineChannelFilter, ChannelFilter, ChannelFilterItem,
    migrate_channel_filter)

from solariat_bottle.tests.base           import MainCase, SA_TYPES
from solariat_bottle.tests.slow.test_smarttags import SmartTagsTestHelper


class OnlineChannelFilterCase(MainCase, SmartTagsTestHelper):

    def setUp(self):
        self.orig_filter_cls = get_var('CHANNEL_FILTER_CLS')
        settings.CHANNEL_FILTER_CLS = 'OnlineChannelFilter'

        super(OnlineChannelFilterCase, self).setUp()

        self.cf = self.channel.channel_filter

        self.laptop_tag = self._create_smart_tag(self.channel,
                                                 'Laptops Tag',
                                                 status='Active',
                                                 keywords=['laptop'])

        self.display_tag = self._create_smart_tag(self.channel,
                                                  'Other Tag',
                                                  status='Active',
                                                  keywords=['display'])

    def tearDown(self):
        settings.CHANNEL_FILTER_CLS = self.orig_filter_cls

        super(OnlineChannelFilterCase, self).tearDown()

    def _create_post(self, content, lang=None):
        p = self._create_db_post(content=content, lang=lang)
        return p

    def test_migration(self):
        ''' Create a few channels and migrate channel filters for them'''
        stored_filter_cls = get_var('CHANNEL_FILTER_CLS')
        settings.CHANNEL_FILTER_CLS = 'DbChannelFilter'

        channels = []
        channel_filters = []
        for i in range(1):
            self.channel = TwitterChannel.objects.create_by_user(
                self.user, title='C%d' %i,
                type='twitter', intention_types=SA_TYPES)
            self.channel.channel_filter.handle_accept(self._create_post("I need a laptop"))
            self.channel.channel_filter.handle_reject(self._create_post("I hate my laptop"))
            channels.append(self.channel)
            channel_filters.append(self.channel.channel_filter)

        for channel in channels:
            migrate_channel_filter(channel, 'OnlineChannelFilter')
            self.channel = channel
            self.assertTrue(self.channel.channel_filter._predict_fit(
                    self._create_post("I need a laptop")) > 0.5)
            self.assertTrue(self.channel.channel_filter._predict_fit(
                    self._create_post("I hate my laptop")) < 0.5)
        settings.CHANNEL_FILTER_CLS = stored_filter_cls

    def test_persistence(self):
        ''' Make sure we can retrieve a traine model and use it'''
        self.cf.save()
        self.assertFalse(self.cf.requires_refresh)
        self.assertEqual(len(OnlineChannelFilter.objects()), 1)

        # Train it (saves to db implicitly)
        self.cf.handle_accept(self._create_post("I need a laptop"))
        self.cf.handle_reject(self._create_post("I hate my laptop"))

        # Score it
        packed_before = self.cf.packed_clf
        score_before  = self.cf._predict_fit(self._create_post("I need a laptop"))

        # Now pull from the database and score again
        db_cf = OnlineChannelFilter.objects.get(id=self.cf.id)
        packed_after = db_cf.packed_clf
        score_after  = db_cf._predict_fit(self._create_post("I need a laptop"))

        self.assertEqual(len(packed_before), len(packed_after))

        # Scores should be the same if persisted correctly
        self.assertEqual(score_before, score_after)

        # Now retrain and check again
        db_cf.retrain()
        score_after  = db_cf._predict_fit(self._create_post("I need a laptop"))
        self.assertTrue(score_after > 0.5)

        # Also, the original object should be out of date
        self.assertTrue(self.cf.requires_refresh)
        self.assertFalse(db_cf.requires_refresh)

        # Now reset
        for cf in ChannelFilter.objects(): cf.reset()

        self.assertEqual(ChannelFilterItem.objects.count(), 0)
        cf = self.channel.channel_filter
        score  = cf._predict_fit(self._create_post("I need a laptop"))
        self.assertEqual(score, 0.5)

    def _prime(self, accept_list, reject_list, repetitions=3):
        for i in range(repetitions):
            for p in accept_list:
                self.channel.channel_filter.handle_accept(self._create_post(p))
            for p in reject_list:
                self.channel.channel_filter.handle_reject(self._create_post(p))

    def test_assignment(self):
        ''' Make sure actionability is working correctly '''
        self._prime(["I need a laptop"], ["I hate my laptop"])
        post = self._create_post("I need a laptop")
        self.assertEqual(post.get_assignment(self.channel), 'highlighted')
        post = self._create_post("I really hate my laptop")
        self.assertEqual(post.get_assignment(self.channel), 'discarded')

    def test_all_same(self):
        '''Works ok when all cases are positive'''
        self._prime(["I need a laptop"], [], repetitions=3)
        post = self._create_post("I need a laptop")
        self.assertEqual(post.get_assignment(self.channel), 'highlighted')

        # Now create a single counter example
        self.channel.channel_filter.handle_reject(self._create_post("I hate my cat"))
        post = self._create_post("My cat sucks")
        self.assertEqual(post.get_assignment(self.channel), 'discarded')
        post = self._create_post("I need a laptop")
        self.assertEqual(post.get_assignment(self.channel), 'highlighted')

    def _create_and_tag(self, content, tag, lang=None):
        post = self._create_post(content, lang=lang)
        post.handle_add_tag(self.user, [tag])
        return post

    def test_tagging(self):
        ''' Make sure learning working for tag changes'''

        # Train with tag assignment
        self._create_and_tag("I hate my laptop", self.laptop_tag)
        self._create_and_tag("I love my laptop", self.laptop_tag)

        # Now learned
        post = self._create_post("I like my laptop")
        self.assertEqual(post.accepted_smart_tags, [self.laptop_tag])

        # Now train negative case
        post.handle_remove_tag(self.user, [self.laptop_tag])

        # Learned
        post = self._create_post("I love my laptop")
        self.assertEqual(post.accepted_smart_tags, [])

    def test_counters(self):
        settings.ON_TEST = True  #ensure task queue completed

        p0 = self._create_and_tag("I hate my laptop", self.laptop_tag)
        p1 = self._create_and_tag("I love my laptop", self.laptop_tag)

        for i in range(0, 2):
            self._create_post("I hate my laptop")

        self.assertEqual(self.laptop_tag.channel_filter.accept_count, 2)
        self.laptop_tag.channel_filter.reset()
        self.assertEqual(self.laptop_tag.channel_filter.accept_count, 0)

        p1.handle_remove_tag(self.user, [self.laptop_tag])
        self.assertEqual(self.laptop_tag.channel_filter.accept_count, 0)
        self.assertEqual(self.laptop_tag.channel_filter.reject_count, 1)

    def test_language_feature(self):
        NOT_ACTIONABLE = "rejected"
        ACTIONABLE = "starred"

        from solariat_bottle.db.channel.twitter import TwitterServiceChannel

        sc = TwitterServiceChannel.objects.create_by_user(
            self.user,
            title='Service Channel')

        sc.add_keyword('foozball')
        inbound = sc.inbound_channel

        posts = [
            ('fr', "J'adore Foozball",          NOT_ACTIONABLE),
            ('en', 'I love Foozball',           ACTIONABLE),
            ('es', 'Foozball es bueno!',        ACTIONABLE),
            ('fr', 'Foozball est tres bien!',   NOT_ACTIONABLE)
        ]
        for (lang, content, status) in posts:
            post = self._create_db_post(content, channel=sc, lang=lang)
            handle_filter = post.handle_reject if status == NOT_ACTIONABLE else post.handle_accept
            handle_filter(None, [inbound])

        cf = inbound.channel_filter
        for (lang, content, status) in posts:
            post = self._create_db_post(content, channel=sc, lang=lang)
            # print cf.make_post_vector(post)
            # print cf.clf.vectorizer.transform([cf.make_post_vector(post)])
            fit = cf._predict_fit(post)
            # print fit
            if status == ACTIONABLE:
                self.assertTrue(fit > 0.5)
            else:
                self.assertTrue(fit < 0.5)
