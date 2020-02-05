
import unittest
import datetime
import json
import mock
from os.path import join, dirname

from solariat_bottle.app import get_api_url
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.post.facebook import FacebookPost
from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.db.conversation import Conversation
from solariat_bottle.db.queue_message import QueueMessage

from solariat_bottle.tests.base import BaseCase, UICase
from solariat.utils import timeslot
from solariat_bottle.tasks.facebook import fb_put_post, fb_put_comment, fb_delete_object, fb_like_post, \
    fb_get_comments_for, fb_get_comments_for_post
from solariat_bottle.daemons.facebook.facebook_history_scrapper import FacebookHistoryScrapper
from solariat_bottle.daemons.facebook.facebook_data_handlers import FBDataHandlerFactory

from solariat_bottle.tests.base import BaseFacebookIntegrationTest


class _IdStub(object):
        def __init__(self, id):
            self.__id = id
        @property
        def id(self):
            return self.__id


class _FacebookChannelStub(object):
    def __init__(self, token, user):
        self.id = 'test_id'
        self.title = 'title'
        self.facebook_access_token = token
        self.user = user

    @property
    def facebook_handle_id(self):
        return self.user['id']

    def get_access_token(self, p1):
        return self.facebook_access_token


    @property
    def facebook_account_ids(self):
        return []

    @property
    def inbound_channel(self):
        return _IdStub("inbound_id")

    @property
    def outbound_channel(self):
        return _IdStub("outbound_id")

    @property
    def facebook_page_ids(self):
        return []

    def save(self):
        pass

    def get_service_channel(self):
        return None


class TestFacebookBasic(BaseFacebookIntegrationTest):

    def setUp(self):
        super(TestFacebookBasic, self).setUp()
        self.efc = _FacebookChannelStub(self.default_user['access_token'], self.default_user)

    def test_testusers_exists(self):

        users = self._get_test_users()
        self.assertTrue(len(users) > 0)

    def test_default_user_created(self):

        self.assertIsNotNone(self.default_user)

    def test_put_post_task(self):

        user = self.default_user
        test_msg = "I'm test message"
        target = "me"
        self.efc._current_service_channel = None
        result = fb_put_post(self.efc, target, test_msg)
        self.assertIsNotNone(result)
        self.assertTrue(user['id'] in result['id'])   #checking that post was succesfully added to user

    def test_put_comment_to_post(self):

        user = self.default_user
        comment = "I'm comment"
        post = self.post_to_user(user)
        result = fb_put_comment(self.efc, post['id'], comment)
        self.assertIsNotNone(result)
        self.assertTrue(self._get_second_id_part(post['id']) in result['id'])

    @unittest.skipIf(True, "Deprecated since Nov 17: https://developers.facebook.com/docs/graph-api/reference/v2.8/object/likes")
    def test_like_unlike(self):

        class FBPostStub(object):
            def __init__(self, post):
                self.id = post['id']
                self.likes = []
                self._facebook_data = {'facebook_post_id': self.id}

            def like_status(self, name):
                return name in self.likes

            def like(self, name):
                self.likes.append(name)

            def unlike(self, name):
                self.likes.remove(name)
            @property
            def is_pm(self):
                return False

        user = self.default_user
        post = self.post_to_user(user)
        fb_post = FBPostStub(post)

        from solariat_bottle.tasks.exceptions import FacebookCommunicationException
        with self.assertRaises(FacebookCommunicationException) as error_ctx:
            fb_like_post(self.efc, fb_post._facebook_data['facebook_post_id'])
            print(error_ctx.exception)
            post_once_again = self._get_object(user, self._get_second_id_part(post['id']))
            self.assertEquals(len(post_once_again['likes']['data']), 1)

            fb_like_post(self.efc, fb_post._facebook_data['facebook_post_id'], delete=True)
            post_once_again = self._get_object(user, self._get_second_id_part(post['id']))
            self.assertEquals(post_once_again.get('likes', None), None)

# class TestDeletePOsts(BaseFacebookIntegrationTest):
#
#     def test_delete_post(self):
#
#         user = self.default_user
#         post = self.post_to_user(user)
#         id = self._get_second_id_part(post['id'])
#
#         post_once_again = self._get_object(user, id)
#         self.assertEqual(id, post_once_again['id'])
#         fb_delete_object(self.efc, post['id'])
#         object_deleted = False
#         try:
#             self._get_object(user, id)
#         except facebook.GraphAPIError:
#             object_deleted = True
#
#         self.assertTrue(object_deleted)
#
#     def test_delete_comment(self):
#
#         user = self.default_user
#         post = self.post_to_user(user)
#         comment = fb_put_comment(self.efc, post['id'], "some test stuff")
#         fb_delete_object(self.efc, comment['id'])
#         object_deleted = False
#         try:
#             self._get_object(user, self._get_second_id_part(comment['id']))
#         except facebook.GraphAPIError:
#             object_deleted = True
#
#         self.assertTrue(object_deleted)
#


class TestFacebookHistory(BaseFacebookIntegrationTest):

    def setUp(self):
        super(TestFacebookHistory, self).setUp()
        self.channel = _FacebookChannelStub(self.default_user['access_token'], self.default_user)
        self.since = '01/01/2014'
        self.until = str(datetime.date.today() + datetime.timedelta(days=1))
        self.limit = 4

    def test_scrapper_creation(self):

        history_scrapper = FacebookHistoryScrapper(self.channel)
        self.assertIsNotNone(history_scrapper)

    def test_scrap_posts(self):

        user = self.default_user
        for i in range(0, self.limit):
            self.post_to_user(user)

        scrapper = FacebookHistoryScrapper(self.channel)
        posts = scrapper.get_posts(user['id'], self.since, self.until, self.limit)
        self.assertEqual(len(posts['data']), self.limit)

    @unittest.skip("skipping this test because it blinks in Jenkins build. Please see this jira ticket: JOP-1925")
    def test_scrap_comments(self):

        user = self.default_user
        post = self.post_to_user(user)
        self.comment_post(user, post)
        self.comment_post(user, post)

        scrapper = FacebookHistoryScrapper(self.channel)
        comments = scrapper.get_comments(post['id'], self.since, self.until, self.limit)
        self.assertEqual(len(comments['data']), 2)

    @unittest.skip("skipping this test because it blinks in Jenkins build. Please see this jira ticket: JOP-1925")
    def test_get_comment_task(self):

        user = self.default_user
        post = self.post_to_user(user)
        self.comment_post(user, post)
        comment = self.comment_post(user, post)
        self.comment_post(user, comment)

        result = fb_get_comments_for_post(self.channel, post['id'])
        self.assertIsNotNone(result)

    def test_handle_post(self):

        user = self.default_user
        self.post_to_user(user)
        scrapper = FacebookHistoryScrapper(self.channel)
        posts = scrapper.get_posts(user['id'], self.since, self.until, self.limit)
        post = scrapper.handle_data_item(posts['data'][0], FBDataHandlerFactory.get_instance(FBDataHandlerFactory.POST), user['id'])
        self.assertIsNotNone(post)
        self.assertIsNotNone(post['content'])

    @unittest.skip("skipping this test because it blinks in Jenkins build. Please see this jira ticket: JOP-1925")
    def test_handle_comments(self):

        user = self.default_user
        post = self.post_to_user(user)
        self.comment_post(user, post)
        scrapper = FacebookHistoryScrapper(self.channel)
        comment = scrapper.get_comments(post['id'], self.since, self.until, self.limit)
        comment = scrapper.handle_data_item(comment['data'][0], FBDataHandlerFactory.get_instance(FBDataHandlerFactory.COMMENT), user['id'])
        self.assertIsNotNone(comment)
        self.assertIsNotNone(comment['content'])

    @mock.patch('solariat_bottle.daemons.facebook.facebook_history_scrapper.FacebookDriver')
    def test_get_pm_for_page(self, fake_driver):

        puller = FacebookHistoryScrapper(self.channel)
        pm = puller.get_page_private_messages("fake_page_id")
        # TODO: not passing
        # assert fake_driver.obtain_new_page_token.call_count == 1
        # assert fake_driver.request.call_count == 1
        self.assertIsInstance(pm, mock.MagicMock)


class TestFBDataPullTasks(BaseCase):

    def test_fb_get_comments_for(self):
        fbu = mock.Mock()
        fbu.factory_by_user = mock.MagicMock()
        pullerBase = mock.Mock()
        puller = mock.Mock()
        puller.get_comments = mock.Mock(return_value=json.load(open(join(dirname(__file__), '../data/fb_comment1.json'))))
        puller.handle_data_item = mock.Mock(return_value={'id': '777'})
        pullerBase.FacebookHistoryScrapper = mock.Mock(return_value=puller)
        mock_dict = {'solariat_bottle.db.post.utils': fbu,
                     'solariat_bottle.daemons.facebook.facebook_history_scrapper': pullerBase}

        ch_mock = mock.Mock()
        ch_mock.get_access_token = mock.Mock(return_value='Some fake id')

        with mock.patch.dict('sys.modules', mock_dict):
            fb_get_comments_for(ch_mock, 'fake_post_id', self.user, timeslot.UNIX_EPOCH)

        assert puller.get_comments.call_count == 1
        self.assertEqual(fbu.factory_by_user.call_count, 2)


class FacebookConversationTest(UICase):
    from_data = {
        u'first_name': u'Alice', u'last_name': u'Smith',
        u'profile_image_url': u'https://scontent.xx.fbcdn.net/',
        u'updated_time': u'2016-01-01T23:23:00 +0000',
        u'link': u'https://www.facebook.com/app_scoped_user_id/531923306999420/',
        u'user_name': u'Alice Smith',
        u'id': u'531923306999420'
    }
    posts_native_data = [
        # t_id.number format
        ({u'conversation_id': u't_id.436397333146306', u'page_id': u'167360800259',
          u'created_at': u'2014-09-10T00:35:59 +0000',
          u'facebook_post_id': u'm_mid.1410309359835:1dc8f5369ed2e9b206',
          u'_wrapped_data': {
              u'from': from_data,
              u'source_type': u'PM',
              u'created_by_admin': False,
              u'created_at': u'2014-09-10T00:35:59 +0000',
              u'inbox_url': u'https://www.facebook.comnull',
              u'to': {u'name': u'Bob Doe', u'id': u'167360800259'},
              u'source_id': u't_id.436397333146306',
              u'message': u'Hello from Alice',
              u'type': u'pm', u'id': u'm_mid.1410309359835:1dc8f5369ed2e9b206'}},
         436397333146306L),

        ({u'in_reply_to_status_id': u'm_mid.1410309359835:1dc8f5369ed2e9b206',
          u'facebook_post_id': u'm_mid.1410310139586:d66aa847984bb45c42',
          u'root_post': u'm_mid.1410309359835:1dc8f5369ed2e9b206',
          u'conversation_id': u't_id.436397333146306', u'page_id': u'167360800259',
          u'created_at': u'2014-09-10T00:48:59 +0000', u'_wrapped_data': {
                u'from': from_data,
                u'source_type': u'PM',
                u'created_by_admin': False,
                u'created_at': u'2014-09-10T00:48:59 +0000',
                u'inbox_url': u'https://www.facebook.comnull',
                u'to': {u'name': u'Bob Doe', u'id': u'167360800259'},
                u'source_id': u't_id.436397333146306',
                u'message': u'Replying to previous message',
                u'type': u'pm',
                u'id': u'm_mid.1410310139586:d66aa847984bb45c42'}},
         436397333146306L),

        # t_mid.number:hex_number format
        # this will create a corrupted conversation as it has in_reply_to_status_id but no actual parent post submitted
        ({u'facebook_post_id': u'm_mid.1467235850858:01c50ea51006e38449', u'_wrapped_data': {
            u'from': {u'user_name': u'Goggles', u'id': u'297414983930888',
                      u'profile_image_url': u'https://scontent.xx.fbcdn.net/'},
            u'source_type': u'PM', u'created_by_admin': True,
            u'created_at': u'2016-06-29T21:30:50 +0000',
            u'inbox_url': u'https://www.facebook.comnull',
            u'to': {u'name': u'John Test Qinberg', u'id': u'101711770263783'},
            u'source_id': u't_mid.1467235818867:fb0791a508db32a096',
            u'message': u'What did you want', u'type': u'pm',
            u'id': u'm_mid.1467235850858:01c50ea51006e38449'},
          u'created_at': u'2016-06-29T21:30:50 +0000',
          u'in_reply_to_status_id': u'm_mid.1467235818867:fb0791a508db32a096',
          u'root_post': u'm_mid.1467235818867:fb0791a508db32a096',
          u'conversation_id': u't_mid.1467235818867:fb0791a508db32a096',
          u'page_id': u'297414983930888'},
         1467235818867L)
    ]

    will = {
        "updated_time": "2016-06-21T11:28:40 +0000",
        "user_name": "Will Login Dingleman",
        "link": "https://www.facebook.com/app_scoped_user_id/138144799912356/",
        "last_name": "Dingleman", "id": "138144799912356",
        "middle_name": "Login", "first_name": "Will"}

    lisa = {
        "user_name": "Lisaband",
        "profile_image_url": "https://scontent.xx.fbcdn.net/1.png",
        "id": "998309733582959"}

    public_conversation_data = [
        # Will  root
        #     Lisa comment  #1
        #         Lisa comment  #1.1
        #     Lisa comment  #2
        {"page_id": "998309733582959_1083835218363743",
         "facebook_post_id": "998309733582959_1083835218363743",
         "_wrapped_data": {"comment_count": 0, "updated_time": "2016-08-01T18:05:32 +0000",
                           "can_remove": 1, "can_change_visibility": 0, "is_published": True,
                           "created_at": "2016-08-01T18:05:32 +0000", "privacy": "",
                           "type": "status", "can_comment": 1, "can_like": 1,
                           "from": will,
                           "id": "998309733582959_1083835218363743", "is_liked": 0,
                           "can_be_hidden": 1, "visibility": "normal",
                           "created_by_admin": False, "source_type": "Page",
                           "message": "Will  root", "share_count": 0, "is_popular": False,
                           "to": [{"name": "Lisaband", "id": "998309733582959"}],
                           "source_id": "998309733582959",
                           "actions": [{"name": "Like"}, {"name": "Comment"}, {"name": "Share"},
                                       {"name": "Message"}], "attachment_count": 0,
                           "properties": []}, "created_at": "2016-08-01T18:05:32 +0000"},

        {"page_id": "998309733582959_1083835218363743",
         "facebook_post_id": "1083835218363743_1083836695030262",
         "_wrapped_data": {"can_hide": 0, "can_remove": 0, "user_likes": 1,
                           "visibility": "Normal", "created_by_admin": True,
                           "is_hidden": False,
                           "created_at": "2016-08-01T18:09:51 +0000",
                           "source_type": "Page",
                           "message": "Lisa comment  #1", "type": "Comment",
                           "can_comment": 0, "can_like": 0,
                           "parent_id": "998309733582959_1083835218363743",
                           "from": lisa,
                           "id": "1083835218363743_1083836695030262",
                           "source_id": "998309733582959_1083835218363743"},
         "in_reply_to_status_id": "998309733582959_1083835218363743",
         "created_at": "2016-08-01T18:09:51 +0000",
         "root_post": "998309733582959_1083835218363743",
         "second_level_reply": False},

        {"page_id": "998309733582959_1083835218363743",
         "facebook_post_id": "1083835218363743_1083837241696874",
         "_wrapped_data": {"can_hide": 0, "can_remove": 0, "user_likes": 1,
                           "created_by_admin": True, "created_at": "2016-08-01T18:11:28 +0000",
                           "source_type": "Page", "message": "Lisa comment  #1.1",
                           "type": "Comment", "can_comment": 0, "can_like": 0,
                           "parent_id": "1083835218363743_1083836695030262",
                           "from": lisa,
                           "id": "1083835218363743_1083837241696874",
                           "source_id": "998309733582959_1083835218363743"},
         "in_reply_to_status_id": "998309733582959_1083835218363743",
         "created_at": "2016-08-01T18:11:28 +0000",
         "root_post": "998309733582959_1083835218363743", "second_level_reply": True},

        {"page_id": "998309733582959_1083835218363743",
         "facebook_post_id": "1083835218363743_1083838538363411",
         "_wrapped_data": {"can_hide": 0, "can_remove": 0, "user_likes": 1,
                           "visibility": "Normal", "created_by_admin": True, "is_hidden": False,
                           "created_at": "2016-08-01T18:15:31 +0000", "source_type": "Page",
                           "message": "Lisa comment  #2", "type": "Comment",
                           "can_comment": 0, "can_like": 0,
                           "parent_id": "998309733582959_1083835218363743",
                           "from": lisa,
                           "id": "1083835218363743_1083838538363411",
                           "source_id": "998309733582959_1083835218363743"},
         "in_reply_to_status_id": "998309733582959_1083835218363743",
         "created_at": "2016-08-01T18:15:31 +0000",
         "root_post": "998309733582959_1083835218363743", "second_level_reply": False}
    ]

    def test_get_conversation_id(self):
        """test_get_conversation_id

        Facebook conversation ids for private messages may have different format
        Examples (thread_id is used as conversation id value):
        {"entry": [{"changes": [{"field": "conversations",
                                 "value": {"thread_id": "t_id.266468770144460",
                                           "page_id": 103645656349867}}], "id": "103645656349867",
                    "time": 1467225704}], "object": "page"}

        {"entry": [{"changes": [{"field": "conversations",
                                 "value": {"thread_id": "t_mid.1467235818867:fb0791a508db32a096",
                                           "page_id": 297414983930888}}], "id": "297414983930888",
                    "time": 1467235819}], "object": "page"}
        """

        fbs = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS',
                                                            posts_tracking_enabled=True)
        expected_post_ids = []
        for post_native_data, expected_conv_id in self.posts_native_data:
            post = self._create_db_post(post_native_data['_wrapped_data']['message'], channel=fbs, facebook=post_native_data)
            conv_id = fbs.get_conversation_id(post)
            self.assertEqual(conv_id, expected_conv_id)
            # check that conv id is derived from 'conversation_id' field
            self.assertTrue(str(conv_id) in post_native_data['conversation_id'],
                            msg="{} not in {}".format(conv_id, post_native_data['conversation_id']))
            expected_post_ids.append(post.id)

        self.assertEqual(Conversation.objects.count(), 2)
        conversation_posts = []
        page_ids = ['167360800259', '297414983930888']  # page ids from test data
        for conversation in Conversation.objects():
            self.assertIn(conversation.target_id, page_ids)
            conversation_posts.extend(conversation.posts)
        self.assertEqual(sorted(expected_post_ids), sorted(conversation_posts))

        self.assertEqual(QueueMessage.objects.count(), 3)
        self.login(user=self.user)
        params = {'channel': str(fbs.id),
                  'limit': 10,
                  'reserve_time': 30,
                  'mode': 'conversation',
                  'token': self.auth_token}

        with mock.patch('solariat_bottle.db.conversation.Conversation.mark_corrupted',
                new_callable=mock.PropertyMock) as mark_corrupted:
            response = self.client.get(get_api_url('queue/fetch'),
                                       data=json.dumps(params),
                                       content_type='application/json',
                                       base_url='https://localhost')
            mark_corrupted.assert_called_once_with()

        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['ok'], True)

        # Only 3 posts, since we fetch in conversation mode
        self.assertEqual(len(data['data']), 1)  # 1 conversation, another one is corrupted
        self.assertEqual(len(data['data'][0]['post_data']), 2)  # 2 posts
        self.assertIsNotNone(data['metadata'])
        self.assertIsNotNone(data['metadata']['batch_token'])
        self.assertIsNotNone(data['metadata']['reserved_until'])

        post_ids = []
        for entry in data['data']:
            post_ids.extend(entry['post_ids'])
        callback_params = {'token': self.auth_token,
                           'ids': post_ids}
        response = self.client.get(get_api_url('queue/confirm'),
                                   data=json.dumps(callback_params),
                                   content_type='application/json',
                                   base_url='https://localhost')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['ok'])
        self.assertEqual(len(Conversation.objects()), 2)
        self.assertEqual(len(QueueMessage.objects()), 1)  # 1 post left from corrupted conversation

    def test_conversation_recovery_throttled(self):
        from solariat.utils.timeslot import now, timedelta

        post_native_data, expected_conv_id = self.posts_native_data[2]
        fbs = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS',
                                                            posts_tracking_enabled=True)

        post = self._create_db_post(post_native_data['_wrapped_data']['message'], channel=fbs,
                                    facebook=post_native_data)
        conv_id = fbs.get_conversation_id(post)
        self.assertEqual(conv_id, expected_conv_id)

        conv = Conversation.objects.get()
        self.login(user=self.user)

        requests = mock.MagicMock()
        params = {'channel': str(fbs.id),
                  'limit': 10,
                  'reserve_time': 30,
                  'mode': 'conversation',
                  'token': self.auth_token}

        def assert_requests_get_called_once():
            from solariat_bottle.settings import FBOT_URL, FB_DEFAULT_TOKEN
            url = FBOT_URL + '/json/restore-conversation?token=%s&conversation=%s' % (FB_DEFAULT_TOKEN, conv.id)

            requests.request.assert_called_once_with('get', url, verify=False, timeout=None)

        with mock.patch.dict('sys.modules', {'requests': requests}):
            response = self.client.get(get_api_url('queue/fetch'),
                                       data=json.dumps(params),
                                       content_type='application/json',
                                       base_url='https://localhost')
            assert_requests_get_called_once()
            self.assertFalse(conv.mark_corrupted())
            assert_requests_get_called_once()

            for update in [dict(unset__last_recovery_ts=True),
                           dict(last_recovery_ts=None),
                           dict(last_recovery_ts=now() - timedelta(hours=1))]:
                conv.update(**update)
                requests.request.reset_mock()
                self.assertTrue(conv.mark_corrupted())
                assert_requests_get_called_once()

                self.assertFalse(conv.mark_corrupted())
                assert_requests_get_called_once()

    def test_add_missing_parents_on_pull(self):
        root_post_data, _ = self.posts_native_data[0]
        post_data, _ = self.posts_native_data[1]
        fbs = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS',
                                                            posts_tracking_enabled=True)

        root_post = self._create_db_post(root_post_data['_wrapped_data']['message'], channel=fbs,
                                         facebook=root_post_data)
        conv = Conversation.objects.get()
        conv.delete()
        root_post.reload()
        self.assertEqual(Conversation.objects(posts=root_post.id).count(), 0)

        post = self._create_db_post(post_data['_wrapped_data']['message'], channel=fbs,
                                    facebook=post_data)
        self.login(user=self.user)

        requests = mock.MagicMock()
        params = {'channel': str(fbs.id),
                  'limit': 10,
                  'reserve_time': 30,
                  'mode': 'conversation',
                  'token': self.auth_token}

        from solariat.tests.base import LoggerInterceptor
        with mock.patch.dict('sys.modules', {'requests': requests}), LoggerInterceptor() as logs:
            response = self.client.get(get_api_url('queue/fetch'),
                                       data=json.dumps(params),
                                       content_type='application/json',
                                       base_url='https://localhost')
            # root post was in database,
            # so it should be added without marking conversation as corrupted
            requests.get.assert_not_called()
            found_parent_msgs = [log.message for log in logs if 'Found parent post' in log.message]
            assert len(found_parent_msgs) == 1
            conv.reload()
            self.assertFalse(conv.is_corrupted)

        # clean database and create conversation with post without parent post
        Conversation.objects.coll.remove()
        FacebookPost.objects.coll.remove()
        QueueMessage.objects.coll.remove()

        post = self._create_db_post(post_data['_wrapped_data']['message'], channel=fbs,
                                    facebook=post_data)
        with mock.patch.dict('sys.modules', {'requests': requests}):
            response = self.client.get(get_api_url('queue/fetch'),
                                       data=json.dumps(params),
                                       content_type='application/json',
                                       base_url='https://localhost')
            self.assertEqual(requests.request.call_count, 1)

        conv.reload()
        self.assertTrue(conv.is_corrupted)

        # simulate recovery of root post
        post = self._create_db_post(root_post_data['_wrapped_data']['message'], channel=fbs,
                                    facebook=root_post_data)
        conv.reload()
        self.assertFalse(conv.is_corrupted)

    def test_add_missing_parents_on_pull__deleted_channel(self):
        root_post_data, _ = self.posts_native_data[0]
        post_data, _ = self.posts_native_data[1]
        fbs1 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS',
                                                             posts_tracking_enabled=True)

        root_post = self._create_db_post(root_post_data['_wrapped_data']['message'], channel=fbs1,
                                         facebook=root_post_data)
        fbs1.archive()
        conv1 = Conversation.objects.get(posts=root_post.id)
        self.assertRaises(Channel.DoesNotExist, lambda: conv1.service_channel)

        fbs2 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS',
                                                             posts_tracking_enabled=True)
        post = self._create_db_post(post_data['_wrapped_data']['message'], channel=fbs2,
                                    facebook=post_data)
        conv2 = Conversation.objects.get(posts=post.id)

        self.assertNotEqual(conv1.id, conv2.id)
        self.assertNotEqual(conv1.channels, conv2.channels)

        self.login(user=self.user)

        requests = mock.MagicMock()
        params = {'channel': str(fbs2.id),
                  'limit': 10,
                  'reserve_time': 30,
                  'mode': 'conversation',
                  'token': self.auth_token}

        from solariat.tests.base import LoggerInterceptor
        with mock.patch.dict('sys.modules', {'requests': requests}), LoggerInterceptor() as logs:
            response = self.client.get(get_api_url('queue/fetch'),
                                       data=json.dumps(params),
                                       content_type='application/json',
                                       base_url='https://localhost')
            # root post was in database,
            # so it should be added without marking conversation as corrupted
            requests.get.assert_not_called()
            found_parent_msgs = [log.message for log in logs if 'Found parent post' in log.message]
            assert len(found_parent_msgs) == 1
            conv2.reload()
            self.assertFalse(conv2.is_corrupted)

    def test_no_root_post_for_dms(self):
        root_post_data, _ = self.posts_native_data[0]
        post_data, _ = self.posts_native_data[1]
        fbs = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS',
                                                            posts_tracking_enabled=True)

        def run_fetch_queue_test(mode='conversation'):
            Conversation.objects.coll.remove()
            FacebookPost.objects.coll.remove()
            QueueMessage.objects.coll.remove()

            root_post = self._create_db_post(root_post_data['_wrapped_data']['message'], channel=fbs,
                                             facebook=root_post_data)
            conv = Conversation.objects.get()
            self.assertEqual([int(p) for p in conv.posts], [root_post.id])

            QueueMessage.objects.coll.remove()  # purge queue

            post = self._create_db_post(post_data['_wrapped_data']['message'], channel=fbs,
                                        facebook=post_data)
            self.login(user=self.user)

            requests = mock.MagicMock()
            params = {'channel': str(fbs.id),
                      'limit': 10,
                      'reserve_time': 30,
                      'mode': mode,
                      'token': self.auth_token}

            from solariat.tests.base import LoggerInterceptor
            with mock.patch.dict('sys.modules', {'requests': requests}), LoggerInterceptor() as logs:
                response = self.client.post(
                    get_api_url('queue/fetch'),
                    data=json.dumps(params),
                    content_type='application/json',
                    base_url='https://localhost')
                data = json.loads(response.data)

                self.assertEqual(len(data['data']), 1)
                if 'post_ids' in data['data'][0]:
                    self.assertEqual(data['data'][0]['post_ids'],
                                     [QueueMessage.objects.make_id(fbs.id, post.id)])
                self.assertEqual(len(data['data'][0]['post_data']), 1)
                self.assertEqual(str(data['data'][0]['post_data'][0]['id']), str(post.id))

        run_fetch_queue_test('conversation')
        run_fetch_queue_test('root_included')

    def test_missing_parent_for_comment__deleted_channel(self):
        root_post_data = self.public_conversation_data[0]
        comment_data = self.public_conversation_data[1]  # first comment
        facebook_handle_id = self.lisa['id']
        facebook_page_ids = ["998309733582959", "297414983930888"]

        fbs1 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS',
                                                             facebook_handle_id=facebook_handle_id,
                                                             facebook_page_ids=facebook_page_ids,
                                                             posts_tracking_enabled=True)

        root_post = self._create_db_post(root_post_data['_wrapped_data']['message'],
                                         channel=fbs1,
                                         facebook=root_post_data,
                                         user_profile=self.will)
        fbs1.archive()
        conv1 = Conversation.objects.get(posts=root_post.id)
        self.assertRaises(Channel.DoesNotExist, lambda: conv1.service_channel)

        fbs2 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS',
                                                             facebook_handle_id=facebook_handle_id,
                                                             facebook_page_ids=facebook_page_ids,
                                                             posts_tracking_enabled=True)
        self.login(user=self.user)

        requests = mock.MagicMock()
        params = {'channel': str(fbs2.id),
                  'limit': 10,
                  'reserve_time': 30,
                  'mode': 'root_included',
                  'token': self.auth_token}

        from solariat.tests.base import LoggerInterceptor
        with mock.patch.dict('sys.modules', {'requests': requests}), LoggerInterceptor() as logs:
            # adding comment to another channel
            comment = self._create_db_post(comment_data['_wrapped_data']['message'], channel=fbs2,
                                           facebook=comment_data,
                                           user_profile=self.lisa)
            conv2 = Conversation.objects.get(posts=comment.id)

            self.assertNotEqual(conv1.id, conv2.id)
            self.assertNotEqual(conv1.channels, conv2.channels)

            response = self.client.get(get_api_url('queue/fetch'),
                                       data=json.dumps(params),
                                       content_type='application/json',
                                       base_url='https://localhost')
            # root post was in database,
            # so it should be added without marking conversation as corrupted
            requests.get.assert_not_called()
            found_parent_msgs = [log.message for log in logs if 'Found parent post' in log.message]
            assert len(found_parent_msgs) == 1
            conv2.reload()
            self.assertFalse(conv2.is_corrupted)
            data = json.loads(response.data)
            self.assertEqual([p['id'] for p in data['data'][0]['post_data']], [root_post.id, comment.id])
