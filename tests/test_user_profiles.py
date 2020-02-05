import json

from solariat_bottle.db.user_profiles.social_profile import TwitterProfile as UserProfile, UserProfile as BaseProfile

from .base import MainCase, UICase


class UserProfileCase(MainCase):

    def setUp(self):
        MainCase.setUp(self)
        id = UserProfile.make_id(self.channel.platform, 'joe_blow')
        self.assertEqual(id, "joe_blow:0")
        self.up = UserProfile.objects.create(id=id,
                                             user_name="joe_blow")
        self.assertEqual(self.up.profile_url, "https://twitter.com/joe_blow")

    def test_id_allocation(self):
        self.assertEqual(self.up.platform, self.channel.platform)
        self.assertEqual(self.up.user_name, 'joe_blow')

    def test_get(self):
        up = UserProfile.objects.get_by_platform(self.channel.platform,
                                                 'joe_blow')
        self.assertEqual(up.id, self.up.id)
        self.assertEqual(up.profile_image_url, None)

    def test_upsert(self):
        up = BaseProfile.objects.upsert('Twitter', dict(screen_name='joe_blow_0'))
        self.assertEqual(up.profile_url, "https://twitter.com/joe_blow_0")

        up = UserProfile.objects.upsert(self.channel.platform, dict(screen_name='joe_blow'))
        self.assertEqual(up.id, self.up.id)
        self.assertEqual(up.profile_url, "https://twitter.com/joe_blow")

        up = UserProfile.objects.upsert(self.channel.platform, dict(screen_name='joe_schmow'))
        self.assertNotEqual(up.id, self.up.id)
        up = UserProfile.objects.upsert(self.channel.platform,
                                        dict(screen_name='joe_schmow',
                                             location="Hawaii",
                                             profile_image_url="foo.jpg"))

        self.assertEqual(up.location, "Hawaii")
        self.assertEqual(up.profile_image_url, "foo.jpg")

        up = UserProfile.objects.upsert(self.channel.platform,
                                        dict(screen_name='joe_schmow',
                                             profile_image_url="bar.jpg",
                                             klout_score=40))
        self.assertEqual(up.location, "Hawaii")
        self.assertEqual(up.klout_score, 40)
        self.assertEqual(up.profile_image_url, "bar.jpg")

        up = UserProfile.objects.upsert(self.channel.platform,
                                        dict(screen_name='joe_schmow',
                                             location="Texas",
                                             klout_score=50))
        self.assertEqual(up.location, "Texas")
        self.assertEqual(up.klout_score, 50)
        self.assertEqual(up.profile_image_url, "bar.jpg")

    def test_post_creation(self):
        # Post with anonymous
        post = self._create_db_post("I need a foo")
        self.assertEqual(
            post.user_profile.id,
            UserProfile.objects.get_by_platform(self.channel.platform, post.user_profile.user_name).id
        )

        post = self._create_db_post(
            content = "I need a foo",
            user_profile = dict(
                name="Jack Black",
                user_name="jb",
                location="L",
                klout_score=50
            )
        )
        self.assertFalse(post.user_profile == None)
        self.assertEqual(post.user_profile.user_name, "jb")
        self.assertEqual(post.user_profile.klout_score, 50)
        self.assertTrue(post.user_profile.to_dict != {})

    def test_post_get_user_profile(self):
        up = UserProfile.objects.upsert('Twitter', dict(screen_name='screen_name'))
        post = self._create_db_post(
            channels=[self.channel], user_profile=up, content='test')
        self.assertEqual(post.get_user_profile(), up)
        up.delete()
        post.clear_ref_cache()
        self.assertEqual(post.get_user_profile(), BaseProfile.non_existing_profile())
        self.assertEqual(post.user_profile, None)

class ProfileTabTest(UICase):
    def setUp(self):
        UICase.setUp(self)
        self.login()

    def test_stub(self):
        self.client.post(
            '/user_profile/json',
            data         = json.dumps({}),
            content_type = 'application/json'
        )

