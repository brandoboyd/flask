import json
import os

from solariat_bottle.db.post.twitter import TwitterPost

from solariat_bottle.db.post.utils  import factory_by_user
from solariat_bottle.db.channel.base import SmartTagChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.db.conversation import Conversation
from solariat_bottle.db.post.facebook import FacebookPost
from solariat_bottle.db.channel.chat  import ChatServiceChannel as CSC
from solariat_bottle.db.post.chat  import ChatPost

from solariat_bottle.tests.base import RestCase


class APIPostsCase(RestCase):

    def test_create_happy_flow_data(self):

        tschn1 = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        SmartTagChannel.objects.create_by_user(self.user,
                                               parent_channel=tschn1.inbound_channel.id,
                                               title='tag1',
                                               status='Active')
        st2 = SmartTagChannel.objects.create_by_user(self.user,
                                               parent_channel=tschn1.inbound_channel.id,
                                               title='tag2',
                                               status='Active')
        token = self.get_token()
        happy_flow_data = {
            'content': 'I am having some laptop problems',
            'lang': 'en',
            'channel': str(tschn1.id),
            'token': token
        }
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])

    def test_fb_dump_concurrency_serial(self):
        FacebookPost.objects.remove(id__ne=1)
        Conversation.objects.remove(id__ne=1)

        fb_srv = FacebookServiceChannel.objects.create_by_user(self.user, title='FSC')
        channel_id = str(fb_srv.id)

        self.assertEquals(FacebookPost.objects.count(), 0)
        self.assertEquals(Conversation.objects.count(), 0)

        data_dump = open(os.path.join(os.path.dirname(__file__), 'data', 'fb_dump.json'))
        n_posts = 0
        root_ids = []
        for line in data_dump.readlines():
            n_posts += 1
            post_data = json.loads(line)
            post_data['channel'] = channel_id
            post = factory_by_user(self.user, **post_data)
            root_ids.append(post.get_conversation_root_id())

        self.assertEquals(FacebookPost.objects.count(), 25)
        self.assertEquals(Conversation.objects.count(), 1)
        conv = Conversation.objects.find_one()
        self.assertEqual(FacebookPost.objects.count(), len(conv.posts))
        self.assertEquals(FacebookPost.objects.count(), n_posts)
        self.assertTrue(conv.has_initial_root_post())

    # def test_fb_dump_concurrency_parallel(self):
    #     from solariat_bottle.tests.base import ProcessPool
    #     FacebookPost.objects.remove(id__ne=1)
    #     Conversation.objects.remove(id__ne=1)
    #     from bson import ObjectId
    #
    #     fb_srv = FacebookServiceChannel.objects.create_by_user(self.user, title='FSC')
    #     channel_id = ObjectId("55f8a9649d929d3c15f40dbf")
    #     fb_srv.id = channel_id
    #     fb_srv.save()
    #
    #     self.assertEquals(FacebookPost.objects.count(), 0)
    #     self.assertEquals(Conversation.objects.count(), 0)
    #
    #     data_dump = open(os.path.join(os.path.dirname(__file__), 'data', 'fb_dump.json'))
    #     n_posts = 25
    #     post_data = []
    #     for line in data_dump.readlines():
    #         post_data.append(line)
    #
    #     def gen_data():
    #         for data in post_data:
    #             yield data
    #
    #     def create_post(data):
    #         post = factory_by_user(self.user, **json.loads(data))
    #         conv = Conversation.objects.find_one()
    #         print "NR POSTS: " + str(len(conv.posts))
    #
    #     pool = ProcessPool(8)
    #     pool.map(create_post, gen_data())
    #
    #     from time import sleep
    #     sleep(10)
    #
    #     self.assertEquals(FacebookPost.objects.count(), 25)
    #     self.assertEquals(Conversation.objects.count(), 1)
    #     conv = Conversation.objects.find_one()
    #     self.assertEqual(FacebookPost.objects.count(), len(conv.posts))
    #     self.assertEquals(FacebookPost.objects.count(), n_posts)
    #     self.assertTrue(conv.has_initial_root_post())

    def test_create_empty_content(self):
        tschn1 = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        SmartTagChannel.objects.create_by_user(self.user,
                                               parent_channel=tschn1.inbound_channel.id,
                                               title='tag1',
                                               status='Active')
        st2 = SmartTagChannel.objects.create_by_user(self.user,
                                               parent_channel=tschn1.inbound_channel.id,
                                               title='tag2',
                                               status='Active')
        token = self.get_token()
        happy_flow_data = {
            'content': '',
            'lang': 'en',
            'channel': str(tschn1.id),
            'token': token
        }
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])

    def test_required_field_missing(self):
        token = self.get_token()
        happy_flow_data = {
            'content': 'Test post',
            'lang': 'en',
            'token': token
        }
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertEqual(data['code'], 113)

    def test_post_resource(self):
        tschn1 = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        SmartTagChannel.objects.create_by_user(self.user,
                                               parent_channel=tschn1.inbound_channel.id,
                                               title='tag1',
                                               status='Active')
        st2 = SmartTagChannel.objects.create_by_user(self.user,
                                               parent_channel=tschn1.inbound_channel.id,
                                               title='tag2',
                                               status='Active')
        token = self.get_token()
        happy_flow_data = {
            'content': 'Test post',
            'channel': str(tschn1.id),
            'token': token
        }

        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')

        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        for item in ('content', 'utterances', 'smart_tags', 'actionability', 'sentiment'):
            self.assertTrue(item in post_data['item'])
        for ut_item in ('content', 'topics', 'topic_confidence', 'intention_type', 'intention_type_confidence',
                        'sentiment'):
            self.assertTrue(ut_item in post_data['item']['utterances'][0], '%s not in %s')
        for st_item in ('name', 'confidence', 'uri', 'id'):
            self.assertTrue(st_item in post_data['item']['smart_tags'][0])

    def test_queue_control(self):
        twitter_sc = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        facebook_sc = FacebookServiceChannel.objects.create_by_user(self.user, title='FSC')

        posts_data = [
            # twitter sample post
            {"content": "@solariat_brand can you help with my laptop problems?",
             "user_profile": {"id": 1411050992, "user_name": "user1_solariat"},
             "twitter": {"created_at": "Tue, 08 Jul 2014 12:24:58 +0000",
                         "filter_level": "medium",
                         "id": "486486097535721472",
                         "in_reply_to_screen_name": "solariat_brand",
                         "in_reply_to_user_id": "1411000506",
                         "lang": "en",
                         "mention_ids": [1411000506],
                         "mentions": ["solariat_brand"],
                         "source": "<a href=\"http://twitter.com\" rel=\"nofollow\">Twitter Web Client</a>",
                         "text": "@solariat_brand can you help with my laptop problems?",
                         "user": {"name": "user1_solariat",
                                  "url": "http://www.web.com",
                                  "description": "Teacher",
                                  "location": "San Francisco",
                                  "statuses_count": 1905,
                                  "followers_count": 8,
                                  "friends_count": 13,
                                  "screen_name": "user1_solariat",
                                  "profile_image_url": "http://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg",
                                  "profile_image_url_https": "https://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg",
                                  "lang": "en",
                                  "listed_count": 0,
                                  "id": 1411050992,
                                  "id_str": "1411050992",
                                  "geo_enabled": False,
                                  "verified": False,
                                  "favourites_count": 1,
                                  "created_at": "Tue, 07 May 2013 19:35:50 +0000"}
                         },
             "channels": [str(twitter_sc.inbound)]},
            # facebook sample post
            {u'channel': str(facebook_sc.id),
             u'content': u'This is conversation root',
             u'facebook': {u'_wrapped_data': {u'actions': [{u'name': u'Comment'},
                                                           {u'name': u'Like'}],
                                              u'attachment_count': 0,
                                              u'can_be_hidden': 1,
                                              u'can_change_visibility': 1,
                                              u'can_comment': 1,
                                              u'can_like': 1,
                                              u'can_remove': 1,
                                              u'comment_count': 0,
                                              u'created_at': u'2015-08-05T13:36:04 +0000',
                                              u'created_by_admin': 1,
                                              u'from': {u'category': u'Community',
                                                        u'id': u'1526839287537851',
                                                        u'name': u'Software architect party'},
                                              u'id': u'1526839287537851_1680168048871640',
                                              u'is_liked': 0,
                                              u'is_popular': False,
                                              u'is_published': False,
                                              u'message': u'This is conversation root',
                                              u'privacy': u'EVERYONE',
                                              u'properties': [],
                                              u'share_count': 0,
                                              u'source_id': u'1526839287537851',
                                              u'source_type': u'Page',
                                              u'to': [],
                                              u'type': u'status',
                                              u'updated_time': u'2015-08-05T13:36:04 +0000'},
                           u'created_at': u'2015-08-05T13:36:04 +0000',
                           u'facebook_post_id': u'1526839287537851_1680168048871640',
                           u'page_id': u'1526839287537851'},
             u'user_profile': {u'id': u'1526839287537851',
                               u'user_name': u'Software architect party'}}
        ]

        def send_api_posts(post_data, add_to_queue):
            content = json.dumps(post_data)
            data = dict(content=0,
                        serialized_to_json=True,
                        post_object_data=content,
                        channel=0,
                        add_to_queue=add_to_queue,
                        token=self.get_token())
            if add_to_queue is None:
                del data['add_to_queue']

            resp = self.client.post('/api/v2.0/posts',
                                    data=json.dumps(data),
                                    content_type='application/json',
                                    base_url='https://localhost')
            return resp.data

        negative_values = ['false', 'False', 'no', False, 'n']
        positive_values = [None, ''] + ['true', 'True', 'yes', True, 'y']

        from solariat_bottle.db.queue_message import QueueMessage

        def cleanup():
            QueueMessage.objects.coll.remove()
            FacebookPost.objects.coll.remove()

        for post_data in posts_data:
            for add_to_queue in negative_values:
                cleanup()
                response = send_api_posts(post_data, add_to_queue)
                print response
                self.assertEqual(QueueMessage.objects.count(), 0)

            for add_to_queue in positive_values:
                cleanup()
                response = send_api_posts(post_data, add_to_queue)
                print response
                self.assertEqual(
                    QueueMessage.objects.count(), 1,
                    msg="posts_data={}\nadd_to_queue={}".format(str(post_data), add_to_queue))
                if post_data.get('twitter'):
                    self.assertEqual(TwitterPost(QueueMessage.objects.get().post_data).native_data,
                                     post_data['twitter'])
                elif post_data.get('facebook'):
                    self.assertEqual(FacebookPost(QueueMessage.objects.get().post_data).native_data,
                                     post_data['facebook'])


class APIChatCase(RestCase):

    def setUp(self):
        super(APIChatCase, self).setUp()
        self.sc = CSC.objects.create_by_user(
            self.user,
            title = 'test chat service channel')
        self.token = self.get_token()
        self.session_id = 'sessionid12334234'

    def test_correct_creation(self):
        happy_flow_data = {
            'content': 'I am having some chat post for genesys',
            'lang': 'en',
            'channel': str(self.sc.inbound),
            'token': self.token,
            'extra_fields': {'chat': {'session_id': self.session_id }}
        }
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        self.assertEqual(ChatPost.objects().count(), 1)
        chat_post = ChatPost.objects()[0]
        self.assertEqual(chat_post.session_id, self.session_id)

    def test_incorrect_creation(self):
        happy_flow_data = {
            'content': 'I am having some chat post for genesys',
            'lang': 'en',
            'channel': str(self.sc.inbound),
            'token': self.token,
        }
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        self.assertEqual(ChatPost.objects().count(), 1)
        chat_post = ChatPost.objects()[0]
        self.assertNotEqual(chat_post.session_id, self.session_id)


