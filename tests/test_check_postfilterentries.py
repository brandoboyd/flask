from .base import MainCase, UICase
from solariat.tests.base import LoggerInterceptor
from solariat_bottle.scripts.check_postfilterentries import check_channels, PostFilterTupleList

from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel, TwitterServiceChannel
from solariat_bottle.db.tracking import PostFilterEntry


def run_script(dry_run=False):
    options = type('Options', (), {"dryrun": dry_run})()
    check_channels(options)


class CheckPostFilterEntriesScriptTest(MainCase):
    def setUp(self):
        super(CheckPostFilterEntriesScriptTest, self).setUp()

        self.etc_test_handle = 'etc_test_handle'
        self.keywords = ['test_kwD1', 'Test_keyword2']
        self.skipwords = ['test_skipword']
        self.usernames = ['@user_sc1']

        self.etc = EnterpriseTwitterChannel.objects.create(
            title='ETC',
            twitter_handle=self.etc_test_handle)
        self.etc.save()  # trigger postfilter track()
        self.sc = TwitterServiceChannel.objects.create(
            title='SC')

        for kwd in self.keywords:
            self.sc.add_keyword(kwd)
        for swd in self.skipwords:
            self.sc.add_skipword(swd)
        for un in self.usernames:
            self.sc.add_username(un)

        self.channels = [self.etc, self.sc]

    def get_filter_entries(self):
        filter_entries = PostFilterTupleList()
        for pfe in PostFilterEntry.objects():
            filter_entries.extend_entries(pfe)
        return filter_entries

    def get_channel_entries(self):
        channel_entries = PostFilterTupleList()
        for ch in Channel.objects(id__in=[ch.id for ch in self.channels]):
            channel_entries.extend_entries(ch)
        return channel_entries

    def assert_consistent(self, is_consistent=True):
        channel_entries = self.get_channel_entries()
        filter_entries = self.get_filter_entries()
        if is_consistent:
            self.assertEqual(set(channel_entries), set(filter_entries))
        else:
            self.assertNotEqual(set(channel_entries), set(filter_entries))

    def test_normal(self):
        """With proper basic channel setup script
        should not add or delete any PostFilterEntry docs
        """
        self.assert_consistent()

        with LoggerInterceptor() as messages:
            run_script()
            self.assertFalse(messages, msg=messages)

        self.assert_consistent()

    def test_missing_entries(self):
        """Add keywords/usernames to service channel directly in db.
        Run script and check those entries are tracked.
        """
        new_keywords = ['new_kwd1', 'en__english_kwd1', 'es__spain_kwd2']
        new_skipwords = ['new_skipword1']
        new_usernames = ['@new_uname1', '@new_user2']

        self.sc.inbound_channel.update(
            pushAll__keywords=new_keywords,
            pushAll__skipwords=new_skipwords)

        self.sc.outbound_channel.update(
            pushAll__usernames=new_usernames)

        self.assert_consistent(False)

        with LoggerInterceptor() as messages:
            run_script(dry_run=True)
            self.assertEqual(len(messages), 6, msg=messages)

        self.assert_consistent(False)

        with LoggerInterceptor() as messages:
            run_script(dry_run=False)
            self.assertEqual(len(messages), 6, msg=messages)

        self.assert_consistent()

        with LoggerInterceptor() as messages:
            run_script(dry_run=False)
            self.assertFalse(messages)

        self.assert_consistent()

        # double check for lang-prefixed keywords
        self.assertTrue(PostFilterEntry.objects(
            channels=self.sc.inbound_channel,
            lang='es',
            entry='spain_kwd2').count() == 1)
        self.assertTrue(PostFilterEntry.objects(
            channels=self.sc.inbound_channel,
            lang='en',
            entry='english_kwd1').count() == 1)
        self.assertTrue(PostFilterEntry.objects(
            channels=self.sc.inbound_channel,
            entry='es__spain_kwd2').count() == 0)
        self.assertTrue(PostFilterEntry.objects(
            channels=self.sc.inbound_channel,
            entry='en__english_kwd1').count() == 0)

    def test_extra_entries(self):
        """Add some entries into PostFilterEntry collection
        that have no correspondent channels.
        Run script and check those entries were removed.
        """
        pf = PostFilterEntry.objects.get()
        pf.entry = 'new__not_in_channel_%s' % pf.entry
        pf.id = None
        pf.save()

        with LoggerInterceptor() as messages:
            run_script(dry_run=True)
            self.assertTrue(messages, msg=messages)
            self.assertEqual(messages[0].message,
                             "Found 1 extra PostFilterEntries")

        self.assert_consistent(False)

        with LoggerInterceptor() as messages:
            run_script(dry_run=False)
            self.assertEqual(messages[0].message,
                             "Found 1 extra PostFilterEntries")
            self.assertTrue(messages[1].message.startswith(
                "Untracking PostFilterEntry: USER_NAME %s" % pf.entry))
        self.assert_consistent()

    def test_non_active_channels(self):
        """Deactivate/Remove channel directly in db.
        Run script and check the correspondent postfilter entries were removed
        """
        self.sc.update(set__status='Suspended')
        self.sc.inbound_channel.update(set__status='Suspended')
        self.sc.outbound_channel.update(set__status='Suspended')

        self.assert_consistent(False)

        with LoggerInterceptor() as messages:
            run_script(dry_run=True)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0].message,
                             "Found 6 PostFilterEntries for non-active channels")
        self.assert_consistent(False)

        run_script(dry_run=False)
        self.assert_consistent()

        self.etc.update(set__status='Archived')
        self.assert_consistent(False)
        run_script(dry_run=False)
        self.assert_consistent()

        self.assertFalse(self.get_filter_entries() + self.get_channel_entries())

    def test_language_set_changed(self):
        """Change channel.languages list directly in db.
        Run script and check PostFilters updated.
        """
        self.sc.inbound_channel.update(pushAll__langs=['es'])
        self.assert_consistent(False)
        with LoggerInterceptor() as messages:
            run_script(dry_run=True)
            self.assertEqual(len(messages), 4, msg=messages)
            for m in messages:
                self.assertTrue(m.message.startswith('Missing PostFilterEntries'))
        run_script(dry_run=False)
        self.assert_consistent()