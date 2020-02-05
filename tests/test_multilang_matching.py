import unittest
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.channel.twitter import KeywordTrackingChannel
from solariat_bottle.db.tracking import PostFilterEntry
from solariat_bottle.tasks import get_tracked_channels
from solariat_bottle.tests.base import MainCase


class TestMultilangChannel(MainCase):

    def setUp(self):

        MainCase.setUp(self)
        self.title = "test_ttl"
        self.etc = TwitterServiceChannel.objects.create_by_user(
                      self.user, title=self.title)


    def test_lang_to_channel_add_del(self):

        self.etc.remove_langs(["fr"])
        default_langs = ["en", "es"]
        self.etc.set_allowed_langs(default_langs, True)
        langs = self.etc.get_allowed_langs()
        self.assertEquals(langs, default_langs)

        default_langs.extend(["de"])
        self.etc.set_allowed_langs(default_langs)
        langs = self.etc.get_allowed_langs()

        self.assertEquals(sorted(langs), sorted(default_langs))
        self.etc.add_keyword("es__rock")
        self.assertTrue(len(self.etc.inbound_channel.keywords), 1)
        self.etc.remove_langs(["es", "de"])
        self.assertEquals(len(self.etc.inbound_channel.keywords), 0)
        langs = self.etc.get_allowed_langs()
        self.assertEquals(langs, ["en"])


    def test_lang_agnostic_keyword_support(self):

        self.etc.set_allowed_langs(["en", "es"])
        self.etc.add_keyword("key1")

        content = "This is test tweet for key1"
        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content))

        self.assertEquals(len(tracked_channels), 1)

    def test_add_keywords(self):

        self.etc.set_allowed_langs(["es", "de"], clear_previous=True)
        self.etc.add_keyword("key1")
        self.etc.add_skipword("skip1")

        self.assertTrue(len(self.etc.inbound_channel.keywords), 1)
        self.assertEquals(self.etc.inbound_channel.keywords, ["key1"])
        self.assertTrue(len(self.etc.inbound_channel.skipwords), 1)
        self.assertEquals(self.etc.inbound_channel.skipwords, ["skip1"])
        self.etc.add_keyword("es__key2")
        self.etc.add_skipword("de__skip2")
        self.assertTrue(len(self.etc.inbound_channel.skipwords), 2)
        self.assertTrue(len(self.etc.inbound_channel.keywords), 2)

        #this keyword should not be added, as they already added as part lang. agnostic tokens
        self.etc.add_keyword("es__key1")
        self.etc.add_skipword("es__skip1")
        self.assertTrue(len(self.etc.inbound_channel.keywords), 2)
        self.assertEquals(self.etc.inbound_channel.keywords, ["key1", "es__key2" ])
        self.assertTrue(len(self.etc.inbound_channel.skipwords), 2)
        self.assertEquals(self.etc.inbound_channel.skipwords, ["skip1", "de__skip2"])

        self.etc.del_keyword("key1")
        self.etc.del_skipword("skip1")
        self.assertEquals(len(self.etc.inbound_channel.keywords), 1)
        self.assertEquals(len(self.etc.inbound_channel.skipwords), 1)

    def test_keyword_for_lang_sepcific_channel(self):

        self.etc.set_allowed_langs(["es"], clear_previous=True)
        self.etc.add_keyword("key1")


        content = "This is test tweet for key1"
        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content))
        self.assertFalse(tracked_channels)

        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content, lang="es"))
        self.assertEquals(len(tracked_channels), 1)

        self.etc.set_allowed_langs(["en"])
        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content))
        self.assertEquals(len(tracked_channels), 1)

        self.etc.remove_langs(["es"])
        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content, lang="es"))
        self.assertFalse(tracked_channels)


    def test_lang_sepcific_keyword(self):

        self.etc.set_allowed_langs(["es"], clear_previous=True)
        self.etc.add_keyword("es__key1")

        content = "This is test tweet for key1"
        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content, lang="es"))
        self.assertEquals(len(tracked_channels), 1)

        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content))
        self.assertFalse(tracked_channels)

    def test_undefined_lang(self):
        """Should not filter out twitter posts with undefined language"""
        self.etc.set_allowed_langs(["en"], clear_previous=True)
        self.etc.add_keyword("key1")
        self.etc.add_username("test_user")
        for content, verify in [
            ("AAAAAA key1", self.assertTrue),
            ("AAAAA", self.assertFalse),
            ("@test_user AAAAA", self.assertTrue),
            ("test_user AAAAA", self.assertFalse)
        ]:
            tracked_channels = get_tracked_channels('Twitter',
                                                    dict(content=content, lang="und"))
            verify(tracked_channels)

    @unittest.skip("Skipwords disabled. TAP-660")
    def test_multilang_skipword(self):

        self.etc.set_allowed_langs(["es"], clear_previous=True)
        self.etc.add_keyword("es__key1")

        content = "This is test tweet for key1"
        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content, lang="es"))
        self.assertEquals(len(tracked_channels), 1)

        self.etc.add_skipword("key1")
        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content, lang="es"))
        self.assertEquals(len(tracked_channels), 0)

        self.etc.del_skipword("key1")
        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content, lang="es"))
        self.assertEquals(len(tracked_channels), 1)

        from solariat_bottle.db.tracking import PostFilterEntry

        print list(PostFilterEntry.objects.coll.find())
        self.etc.del_keyword("key1")
        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content, lang="es"))

        print list(PostFilterEntry.objects.coll.find())
        self.assertEquals(len(tracked_channels), 0)


class TestAddRemoveKeys(MainCase):

    def setUp(self):

        MainCase.setUp(self)
        self.title = "test_ttl"
        self.ch1 = KeywordTrackingChannel.objects.create_by_user(
                      self.user, title=self.title)
        self.ch2 = KeywordTrackingChannel.objects.create_by_user(self.user, title=self.title)
        self.ch1.set_allowed_langs(['en', 'es'])
        self.ch2.set_allowed_langs(['en', 'es'])


    def test_add_remove_keywords_skipword(self):

        self.ch1.set_allowed_langs(['en', 'es'])

        self.ch1.add_keyword('key1')
        self.assertEqual(PostFilterEntry.objects.count(), 2)

        self.ch1.del_keyword('key1')
        self.assertEqual(PostFilterEntry.objects.count(), 0)

        self.ch1.add_skipword('key1')
        self.assertEqual(PostFilterEntry.objects.count(), 2)

        self.ch1.del_skipword('key1')
        self.assertEqual(PostFilterEntry.objects.count(), 0)

    def test_add_del_same_keyword(self):

        self.ch1.add_keyword('tag')
        self.assertFalse(self.ch1.add_keyword('es__tag'))
        self.assertFalse(self.ch1.add_keyword('en__tag'))
        self.assertFalse(self.ch1.add_keyword('tag'))

        self.assertEqual(PostFilterEntry.objects.count(), 2)

        self.assertTrue(self.ch1.add_keyword('es__key1'))
        self.assertEqual(PostFilterEntry.objects.count(), 3)

        self.assertTrue(self.ch1.add_keyword('en__key1'))
        self.assertEqual(PostFilterEntry.objects.count(), 4)

        self.ch1.del_keyword('es__key1')
        self.assertEqual(PostFilterEntry.objects.count(), 3)

        self.ch1.del_keyword('en__key1')
        self.assertEqual(PostFilterEntry.objects.count(), 2)


    def test_add_del_same_skipword(self):

        self.ch1.add_skipword('tag')
        self.assertFalse(self.ch1.add_skipword('es__tag'))
        self.assertFalse(self.ch1.add_skipword('en__tag'))
        self.assertFalse(self.ch1.add_skipword('tag'))

        self.assertEqual(PostFilterEntry.objects.count(), 2)

        self.assertTrue(self.ch1.add_skipword('es__key1'))
        self.assertEqual(PostFilterEntry.objects.count(), 3)

        self.assertTrue(self.ch1.add_skipword('en__key1'))
        self.assertEqual(PostFilterEntry.objects.count(), 4)

        self.ch1.del_skipword('es__key1')
        self.assertEqual(PostFilterEntry.objects.count(), 3)

        self.ch1.del_skipword('en__key1')
        self.assertEqual(PostFilterEntry.objects.count(), 2)


    def test_postfilter_share_channels(self):

        self.ch1.add_skipword('tag')
        self.assertEqual(PostFilterEntry.objects.count(), 2)

        self.ch2.add_skipword('tag')
        self.assertEqual(PostFilterEntry.objects.count(), 2)

        self.ch1.add_keyword('en__key')
        self.assertEqual(PostFilterEntry.objects.count(), 3)

        self.ch2.add_keyword('es__key')
        self.assertEqual(PostFilterEntry.objects.count(), 4)


    def test_matching_by_keyword(self):

        self.ch1.add_keyword('key')
        self.ch2.add_keyword('es__key')
        content = "This is test tweet for key"

        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content, lang="es"))
        self.assertEqual(len(tracked_channels), 2)

        tracked_channels = get_tracked_channels('Twitter',
                                                dict(content=content, lang="en"))
        self.assertEqual(len(tracked_channels), 1)


    def test_add_remove_channel_langs(self):

        self.ch1.add_keyword("key1")
        self.ch1.add_keyword("es__key2")
        self.assertEqual(PostFilterEntry.objects.count(), 3)

        self.ch1.set_allowed_langs(['en', 'es', 'fr', 'de'], clear_previous=True)
        self.assertEqual(PostFilterEntry.objects.count(), 5)

        self.ch1.remove_langs(['es', 'fr'])
        self.assertEqual(PostFilterEntry.objects.count(), 2)


class TestAddRemoveUserActivateDeactivate(MainCase):

    def setUp(self):

        MainCase.setUp(self)
        self.title = "test_ttl"
        self.ch1 = TwitterServiceChannel.objects.create_by_user(self.user, title=self.title)
        self.ch1.set_allowed_langs(['en'])


    def test_add_remove_useraname_and_langs(self):

        self.ch1.add_username('solariat_brand')
        self.assertEqual(PostFilterEntry.objects.count(), 3)

        self.ch1.del_username('solariat_brand')
        self.assertEqual(PostFilterEntry.objects.count(), 0)


        self.ch1.add_username('solariat_brand')

        self.ch1.set_allowed_langs(["es"])
        self.assertEqual(PostFilterEntry.objects.count(), 6)

        self.ch1.remove_langs(["es"])
        self.assertEqual(PostFilterEntry.objects.count(), 3)

    def test_active_suspend(self):

        self.ch1.add_username('solariat_brand')
        self.assertEqual(PostFilterEntry.objects.count(), 3)
        self.ch1.set_allowed_langs(["es"])
        self.assertEqual(PostFilterEntry.objects.count(), 6)

        self.ch1.on_suspend()
        self.assertEqual(PostFilterEntry.objects.count(), 0)

        self.ch1.on_active()
        self.assertEqual(PostFilterEntry.objects.count(), 6)

        self.ch1.on_suspend()
        self.ch1.remove_langs(["es"])
        self.ch1.on_active()
        self.assertEqual(PostFilterEntry.objects.count(), 3)
