import json
import unittest

from mock import Mock, patch
from os.path import join, dirname
from solariat_bottle.db.channel.facebook import FacebookServiceChannel, EnterpriseFacebookChannel
from solariat_bottle.db.post.base import Post
from solariat_bottle.tasks.facebook import fb_get_latest_posts, fb_get_latest_pm
from solariat_bottle.tests.base import BaseFacebookIntegrationTest, BaseCase


class TestFacebookPullModel(BaseFacebookIntegrationTest):

    def setUp(self):

        BaseFacebookIntegrationTest.setUp(self)
        self.channel = EnterpriseFacebookChannel.objects.create_by_user(self.user, title='ef1',
                                                                    account=self.user.account)
        self.fb_user = self.default_user
        self.channel.facebook_access_token = self.fb_user['access_token']
        self.channel.facebook_handle_id = self.fb_user['id']
        self.channel.save()
        self.channel.on_active()

        self.sfc = FacebookServiceChannel.objects.create_by_user(self.user, title='sf1',
                                                             account=self.user.account)

        self.sfc.facebook_handle_id = self.channel.facebook_handle_id
        self.sfc.facebook_access_token = self.channel.facebook_access_token

        self.sfc.status = 'Active'
        self.sfc.save()

    @unittest.skip("Facebook API user creation fails to grant permissions. So this basically screws up all the rest of unit tests.")
    def test_pull_user_new_data(self):
        self.fb_user = self.create_new_user()
        self.sfc.facebook_handle_id = self.fb_user['id']
        self.sfc.facebook_access_token = self.fb_user['access_token']
        self.sfc.save()

        post1 = self.post_to_user(self.fb_user)
        post2 = self.post_to_user(self.fb_user)

        self.comment_post(self.fb_user, post1)
        self.comment_post(self.fb_user, post1)
        self.comment_post(self.fb_user, post1)

        self.comment_post(self.fb_user, post2)
        self.comment_post(self.fb_user, post2)
        self.comment_post(self.fb_user, post2)

        post_count = Post.objects.find(channels=[str(self.sfc.outbound_channel.id)]).count()
        self.assertEquals(post_count, 0)
        fb_get_latest_posts(self.sfc, self.fb_user['id'], self.user)

        post_count = Post.objects.find(channels=[str(self.sfc.outbound_channel.id)]).count()
        self.assertEquals(post_count, 8)
        self.remove_fb_user(self.fb_user)

@unittest.skip("Pull tasks no longer used since migrated to java bot")
class TestFacebookPullOnFakeData(BaseCase):

    def setUp(self):
        BaseCase.setUp(self)

        self.channel = EnterpriseFacebookChannel.objects.create_by_user(self.user, title='ef1',
                                                               account=self.user.account)
        self.channel.facebook_access_token = 'fake_token'
        self.channel.facebook_handle_id = '100007396443811'
        self.channel.save()
        self.channel.on_active()

        self.sfc = FacebookServiceChannel.objects.create_by_user(self.user, title='sf1',
                                                             account=self.user.account)

        self.sfc.facebook_handle_id = self.channel.facebook_handle_id
        self.sfc.facebook_access_token = self.channel.facebook_access_token

        self.sfc.facebook_page_ids.append('1526839287537851')
        self.sfc.status = 'Active'
        self.sfc.save()

    @patch('solariat_bottle.daemons.facebook.facebook_history_scrapper.FacebookDriver')
    def test_pull_event_new_data(self, fake_driver):
        self.__configure_fake_driver(fake_driver, join(dirname(__file__), 'data/fb_event1.json'))

        fb_get_latest_posts(self.sfc, 'fake_event_id', self.user)
        post_count = Post.objects.find(channels=[str(self.sfc.outbound_channel.id)]).count() + \
                     Post.objects.find(channels=[str(self.sfc.inbound_channel.id)]).count()
        self.assertEquals(post_count, 7)


    @patch('solariat_bottle.daemons.facebook.facebook_history_scrapper.FacebookDriver')
    def test_pull_pm_new_data(self, fake_driver):
        self.__configure_fake_driver(fake_driver, join(dirname(__file__), 'data/fb_pm1.json'))

        fb_get_latest_pm(self.sfc, self.sfc.facebook_page_ids[0], self.user)
        self.assertEqual(len(self.sfc.tracked_fb_message_threads_ids), 2)
        post_count = Post.objects.find(channels=[str(self.sfc.outbound_channel.id)]).count() + \
                     Post.objects.find(channels=[str(self.sfc.inbound_channel.id)]).count()
        self.assertEquals(post_count, 7)

        self.__configure_fake_driver(fake_driver, join(dirname(__file__), 'data/fb_pm2.json'))
        fb_get_latest_pm(self.sfc, self.sfc.facebook_page_ids[0], self.user)
        self.assertEqual(len(self.sfc.tracked_fb_message_threads_ids), 2)
        post_count = Post.objects.find(channels=[str(self.sfc.outbound_channel.id)]).count() + \
                     Post.objects.find(channels=[str(self.sfc.inbound_channel.id)]).count()
        self.assertEquals(post_count, 9)


    def __configure_fake_driver(self, fake_driver, json_path):
        mock = Mock
        request = Mock(return_value=json.load(open(json_path)))
        get_object = Mock(return_value={'name':'Some Name', 'username':'1111', 'data': 'test', 'url': 'test_url'})
        obtain_new_page_token = Mock(return_value="this is fake token")
        mock.request = request
        mock.get_object = get_object
        mock.obtain_new_page_token = obtain_new_page_token
        fake_driver.return_value = mock



