"""
Received {u'entry': [{u'changes': [{u'field': u'feed', u'value': {u'item': u'post', u'verb': u'add', u'sender_id': 100008124789809, u'post_id': 814165888607693}}], u'id': u'757899520900997', u'time': 1405417187}], u'object': u'page'}
Got post: {'created_time': '2014-07-15T09:39:47+0000', 'message': 'A new post on a new page', 'id': '757899520900997_814165888607693'}
Pushed {'channels': ['53c3ec19cea0992596520960'], 'user_profile': {'user_name': 'Mnt Poster'}, 'url': 'https://www.facebook.com/757899520900997/posts/814165888607693', 'sender_id': '100008124789809', 'content': 'A new post on a new page', 'facebook': {'created_at': '2014-07-15T09:39:47+0000', 'facebook_post_id': '757899520900997_814165888607693', 'page_id': '757899520900997'}}


Received {u'entry': [{u'changes': [{u'field': u'feed', u'value': {u'item': u'post', u'verb': u'add', u'sender_id': 100008124789809, u'post_id': 814170268607255}}], u'id': u'757899520900997', u'time': 1405418183}], u'object': u'page'}
Got post: {'created_time': '2014-07-15T09:56:23+0000', 'message': 'Another new post on a new page', 'id': '757899520900997_814170268607255'}
Pushed {'channels': ['53c3ec19cea0992596520960'], 'user_profile': {'user_name': 'Mnt Poster'}, 'url': 'https://www.facebook.com/757899520900997/posts/814170268607255', 'sender_id': '100008124789809', 'content': 'Another new post on a new page', 'facebook': {'created_at': '2014-07-15T09:56:23+0000', 'facebook_post_id': '757899520900997_814170268607255', 'page_id': '757899520900997'}}
"""
import json
import facebook
import time
import unittest

from solariat_bottle.tests.base import BaseCase
from solariat_bottle.daemons.facebook.facebook_client import FacebookBot
from solariat_bottle.db.post.facebook import FacebookPost, parse_datetime
from solariat_bottle.db.channel.facebook import EnterpriseFacebookChannel, FacebookServiceChannel
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.utils import facebook_driver


class GraphAPIStub(object):
    """
    Stub class for actual GraphAPI to avoid facebook direct interaction during post processing.
    """
    ME_ACCOUNT = {'data': [{'access_token': 'CAAUaxYoDeUsBALC4RAptECIs2QpMe41VIi3knQpPUZB4VGx8ALgQFO813DJxjYe9xSkEVSnl3bu6kfyjVZCpuGWN9mk053PCoF3Emi4ZB7ZBkmZAkbTkZAS8S1sT5RavkLkrwiZAnvsk3DR57LzfCb1aGn17pcTs0RWLu6LUrFN9LRyiwpKUdQd',
                          'category': 'Community',
                          'id': '708605282549671',
                          'name': 'Solariat Dev Page',
                          'perms': ['ADMINISTER',
                            'EDIT_PROFILE',
                            'CREATE_CONTENT',
                            'MODERATE_CONTENT',
                            'CREATE_ADS',
                            'BASIC_ADMIN']}],
                         'paging': {'next': 'https://graph.facebook.com/v1.0/100005966506625/accounts?access_token=CAAUaxYoDeUsBAAVKaPUXDNLBysNeH3ob91Ey56UkTqpIsmjiUYtkyMMRZAwnWCLER3RScVIKEPOOBZBaHk49EvZCNR1ATfrZBP9te3ccwyAsU0zPScFUpLiL7EgZCqmrc208hmJXKWeUGuyQUZBxHaI69QPE9FWZBKGFZAkojqQLoXo7SJC37qe9RvNbGsQtDOROl0kVKhCVkV7vbJaQkePHOhmHzbN9XvCOnjnPZAd5QNPmn2kgAtkIE&limit=1000&offset=1000&__after_id=enc_Aezq2b9HI6yxEkiRxl0syOatkUcs3xrVWsUgjfKKNWgQXuVj2-xvYsr6PT5b8W4XCcRdILZu0OxODAg0kLbl86cs'}}


    OBJECTS = [{'actions': [{'link': 'https://www.facebook.com/757899520900997/posts/814165888607693',
                              'name': 'Comment'},
                             {'link': 'https://www.facebook.com/757899520900997/posts/814165888607693',
                              'name': 'Like'}],
                'created_time': '2014-07-15T09:39:47+0000',
                'from': {'id': '100008124789809',
                         'name': 'Mnt Poster'},
                'id': '757899520900997_814165888607693',
                'message': 'A new post on a new page',
                'privacy': {'value': ''},
                'to': {'data': [{'category': 'App page',
                                 'id': '757899520900997',
                                 'name': 'Monitor Solariat'}]},
                'type': 'status',
                'updated_time': '2014-07-15T09:39:47+0000'},

               {'actions': [{'link': 'https://www.facebook.com/757899520900997/posts/825258484165100',
                              'name': 'Comment'},
                             {'link': 'https://www.facebook.com/757899520900997/posts/825258484165100',
                              'name': 'Like'}],
                'created_time': '2014-07-15T09:39:49+0000',
                'from': {'id': '100008124789809',
                         'name': 'Mnt Poster'},
                'id': '757899520900997_825258484165100',
                'message': 'Testing post-reply pair',
                'privacy': {'value': ''},
                'to': {'data': [{'category': 'App page',
                                 'id': '757899520900997',
                                 'name': 'Monitor Solariat'}]},
                'type': 'status',
                'updated_time': '2014-07-15T09:39:49+0000'},

               {'actions': [{'link': 'https://www.facebook.com/757899520900997/posts/825259480831667',
                              'name': 'Comment'},
                             {'link': 'https://www.facebook.com/757899520900997/posts/825259480831667',
                              'name': 'Like'}],
                'created_time': '2014-07-15T09:39:51+0000',
                'from': {'id': '100008124789809',
                         'name': 'Mnt Poster'},
                'id': '825258484165100_825259480831667',
                'message': 'Thanks for reaching out. Testing scenario',
                'privacy': {'value': ''},
                'to': {'data': [{'category': 'App page',
                                 'id': '757899520900997',
                                 'name': 'Poster Solariat'}]},
                'type': 'status',
                'updated_time': '2014-07-15T09:39:51+0000'},

               {'first_name': 'Mnt1',
                'gender': 'female',
                'id': '100008124789809',
                'last_name': 'Poster',
                'link': 'https://www.facebook.com/profile.php?id=100008124789809',
                'locale': 'en_US',
                'name': 'Mnt Poster',
                'picture': {'data': {'is_silhouette': True,
                                     'url': 'https://fbcdn-profile-a.akamaihd.net/hprofile-ak-xpf1/t1.0-1/c15.0.50.50/p50x50/1509246_10150002137498325_1584423246374331045_n.jpg'}},
                'updated_time': '2014-04-04T12:11:53+0000'},

               {'first_name': 'Mnt',
                'gender': 'female',
                'id': '100008145211355',
                'last_name': 'Poster',
                'link': 'https://www.facebook.com/profile.php?id=100008145211355',
                'locale': 'en_US',
                'name': 'Mnt Creator',
                'picture': {'data': {'is_silhouette': True,
                                     'url': 'https://fbcdn-profile-a.akamaihd.net/hprofile-ak-xpf1/t1.0-1/c15.0.50.50/p50x50/1509246_10150002137498325_1584423246374331045_n.jpg'}},
                'updated_time': '2014-04-04T12:11:53+0000'},

               ]

    def __init__(self, access_token=None, timeout=None, version=None, channel=None):
        self.access_token = access_token
        self.timeout = timeout

    def get_object(self, object_id, **kwargs):
        if '/picture' in object_id:
            return {}
        if object_id == '/me/accounts':
            return self.ME_ACCOUNT
        for post in self.OBJECTS:
            if post['id'] == object_id:
                if 'fields' in kwargs:
                    return {field: post.get(field, "") for field in kwargs['fields'].split(',') + ['id']}
                else:
                    return post
        raise facebook.GraphAPIError({"error": {"message": "(#803) Some of the aliases you requested do not exist: %s" % object_id,
                                                "type": "OAuthException",
                                                "code": 803}})

    def request(self, *args, **kwargs):
        # Nothing to do here for now, we can't register for realtime updates in test environment
        pass


FACEBOOK_DATA = {u'entry': [{u'changes': [{u'field': u'feed',
                                           u'value': {u'item': u'post',
                                                      u'verb': u'add',
                                                      u'sender_id': 100008124789809,
                                                      u'post_id': 814165888607693}}],
                             u'id': u'757899520900997',
                             u'time': 1405417187}],
                 u'object': u'page'}

MAX_TIMEOUT = 5



@unittest.skip("No longer use python based bot")
class FacebookBotCase(BaseCase):

    def setUp(self):
        self.real_api = facebook_driver.GraphAPI
        facebook_driver.GraphAPI = GraphAPIStub
        super(FacebookBotCase, self).setUp()
        self.fb_bot = FacebookBot(username=self.user.email,
                                  lockfile="fb_bot_test_lockfile",
                                  concurrency=2,
                                  heartbeat=1)

    def tearDown(self):
        facebook_driver.GraphAPI = self.real_api
        self.fb_bot.stop()

    def test_one_post_happy_flow(self):
        """ Just a basic test of the main flow. Start a datasift bot, pass it some datasift data that
        would get matched in our system, check that it's actually created and matched properly. """
        efc_channel = EnterpriseFacebookChannel.objects.create_by_user(self.user, title="FB_ACC")
        efc_channel.facebook_access_token = 'test'
        srv_channel = FacebookServiceChannel.objects.create_by_user(self.user, title='FB_INB')

        page_id = FACEBOOK_DATA['entry'][0]['id']
        srv_channel.facebook_page_ids.append(page_id)
        efc_channel.facebook_page_ids.append(page_id)
        srv_channel.on_active()
        efc_channel.on_active()
        srv_channel.save()
        efc_channel.save()

        self.assertEqual(FacebookPost.objects.count(), 0)

        self.fb_bot.start()

        for idx in xrange(MAX_TIMEOUT):
            time.sleep(1)
            if self.fb_bot.is_running():
                break
        else:
            self.fail("Bot never got started after waiting %s seconds." % MAX_TIMEOUT)

        self.fb_bot.post_received(json.dumps(FACEBOOK_DATA))

        for idx in xrange(MAX_TIMEOUT):
            time.sleep(1)
            if not (self.fb_bot.is_busy() or self.fb_bot.is_blocked()):
                break
        else:
            self.fail("Post processing did not finish after waiting %s seconds" % MAX_TIMEOUT)

        self.assertEqual(FacebookPost.objects.count(), 1)
        created_post = FacebookPost.objects.find_one()
        expected_create_time = parse_datetime('2014-07-15T09:39:47+0000')
        self.assertEqual(expected_create_time, created_post.created_at)
        self.assertTrue(isinstance(created_post.user_profile, UserProfile))
        self.assertDictEqual(created_post.user_profile.platform_data,
                             {'first_name': 'Mnt1',
                              'gender': 'female',
                              'id': '100008124789809',
                              'last_name': 'Poster',
                              'link': 'https://www.facebook.com/profile.php?id=100008124789809',
                              'locale': 'en_US',
                              'name': 'Mnt Poster',
                              'picture': {'data': {'is_silhouette': True,
                                                   'url': 'https://fbcdn-profile-a.akamaihd.net/hprofile-ak-xpf1/t1.0-1/c15.0.50.50/p50x50/1509246_10150002137498325_1584423246374331045_n.jpg'}},
                              'updated_time': '2014-04-04T12:11:53+0000'})
        self.assertEqual(created_post.content, 'A new post on a new page')
        self.assertTrue(str(srv_channel.inbound_channel.id) in created_post.channel_assignments)
        self.assertEqual(created_post.channel_assignments[str(srv_channel.inbound_channel.id)], 'highlighted')
        self.assertDictEqual(created_post.wrapped_data,
                            {u'expanded_height': u'',
                             u'via': u'',
                             u'attachments': u'',
                             u'icon': u'',
                             u'feed_targeting': u'',
                             u'actions': [{u'link': u'https://www.facebook.com/757899520900997/posts/814165888607693',
                                           u'name': u'Comment'},
                                          {u'link': u'https://www.facebook.com/757899520900997/posts/814165888607693',
                                           u'name': u'Like'}],
                             u'height': u'',
                             u'promotion_status': u'',
                             u'shares': u'',
                             u'created_time': u'2014-07-15T09:39:47+0000',
                             u'is_hidden': u'',
                             u'id': u'757899520900997_814165888607693',
                             u'to': {u'data': [{u'category': u'App page',
                                                u'id': u'757899520900997',
                                                u'name': u'Monitor Solariat'}]},
                             u'description': u'',
                             u'story': u'',
                             u'from': {u'id': u'100008124789809',
                                       u'name': u'Mnt Poster'},
                             u'privacy': {u'value': u''},
                             u'object_id': u'',
                             u'application': u'',
                             u'expanded_width': u'',
                             u'parent_id': u'',
                             u'story_tags': u'',
                             u'coordinates': u'',
                             u'type': u'status',
                             u'status_type': u'',
                             u'is_popular': u'',
                             u'picture': u'',
                             u'scheduled_publish_time': u'',
                             u'full_picture': u'',
                             u'link': u'',
                             u'targeting': u'',
                             u'timeline_visibility': u'',
                             u'properties': u'',
                             u'insights': u'',
                             u'name': u'',
                             u'comments_mirroring_domain': u'',
                             u'call_to_action': u'',
                             u'with_tags': u'',
                             u'message': u'A new post on a new page',
                             u'message_tags': u'',
                             u'updated_time': u'2014-07-15T09:39:47+0000',
                             u'caption': u'',
                             u'place': u'',
                             u'source': u'',
                             u'child_attachments': u'',
                             u'is_published': u'',
                             u'width': u'',
                             u'likes': u''})

        self.fb_bot.stop()

        for idx in xrange(MAX_TIMEOUT * 4):
            time.sleep(1)
            if not self.fb_bot.isAlive():
                break
        else:
            self.fail("Bot never stopped after waiting %s seconds." % (4 * MAX_TIMEOUT))

    def test_post_reply(self):
        """
        Received {u'entry': [{u'changes': [{u'field': u'feed', u'value': {u'item': u'post', u'verb': u'add', u'sender_id': 100008124789809, u'post_id': u'757899520900997_825258484165100'}}], u'id': u'757899520900997', u'time': 1407237249}], u'object': u'page'}
        Got post: {'created_time': '2014-08-05T11:14:09+0000', 'message': 'Testing post-reply pair', 'id': '757899520900997_825258484165100'}
        Pushed {'channels': ['53e0bbf4cea0991f3be1fd17'], 'user_profile': {'user_name': 'Mnt Poster'}, 'url': 'https://www.facebook.com/757899520900997/posts/825258484165100', 'content': 'Testing post-reply pair', 'facebook': {'created_at': '2014-08-05T11:14:09+0000', 'facebook_post_id': '757899520900997_825258484165100', 'page_id': '757899520900997'}}

        Received {u'entry': [{u'changes': [{u'field': u'feed', u'value': {u'parent_id': u'757899520900997_825258484165100', u'comment_id': u'825258484165100_825259480831667', u'sender_id': 100008145211355, u'item': u'comment', u'verb': u'add', u'created_time': 1407237438}}], u'id': u'757899520900997', u'time': 1407237438}], u'object': u'page'}
        Got comment: {'created_time': '2014-08-05T11:17:17+0000', 'message': 'Thanks for reaching out. Testing scenario  ', 'id': '825258484165100_825259480831667'}
        Pushed {'channels': ['53e0bbf4cea0991f3be1fd18'], 'user_profile': {'user_name': 'Mnt Creator'}, 'url': 'https://www.facebook.com/permalink.php?comment_id=757899520900997_825258484165100&story_fbid=825258484165100&id=757899520900997&reply_comment_id=825259480831667', 'content': 'Thanks for reaching out. Testing scenario  ', 'facebook': {'in_reply_to_status_id': '757899520900997_757899520900997_825258484165100', 'facebook_post_id': '825258484165100_825259480831667', 'page_id': '757899520900997', 'created_at': '2014-08-05T11:17:17+0000'}}
        """
        post_data = {u'entry': [{u'changes': [{u'field': u'feed',
                                               u'value': {u'item': u'post',
                                                          u'verb': u'add',
                                                          u'sender_id': 100008124789809,
                                                          u'post_id': u'757899520900997_825258484165100'}}],
                                 u'id': u'757899520900997',
                                 u'time': 1407237249}],
                     u'object': u'page'}
        reply_data = {u'entry': [{u'changes': [{u'field': u'feed',
                                                u'value': {u'parent_id': u'757899520900997_825258484165100',
                                                           u'comment_id': u'825258484165100_825259480831667',
                                                           u'sender_id': 100008145211355,
                                                           u'item': u'comment',
                                                           u'verb': u'add',
                                                           u'created_time': 1407237438}}],
                                  u'id': u'757899520900997',
                                  u'time': 1407237438}],
                      u'object': u'page'}

        efc_channel = EnterpriseFacebookChannel.objects.create_by_user(self.user, title="FB_ACC")
        efc_channel.facebook_access_token = "test"
        srv_channel = FacebookServiceChannel.objects.create_by_user(self.user, title='FB_INB')

        page_id = post_data['entry'][0]['id']
        srv_channel.facebook_page_ids.append(page_id)
        efc_channel.facebook_page_ids.append(page_id)
        efc_channel.facebook_handle_id = str(reply_data['entry'][0]['changes'][0]['value']['sender_id'])
        srv_channel.on_active()
        efc_channel.on_active()
        srv_channel.save()
        efc_channel.save()

        self.assertEqual(FacebookPost.objects.count(), 0)

        self.fb_bot.start()

        for idx in xrange(MAX_TIMEOUT):
            time.sleep(1)
            if self.fb_bot.is_running():
                break
        else:
            self.fail("Bot never got started after waiting %s seconds." % MAX_TIMEOUT)

        self.fb_bot.post_received(json.dumps(post_data))

        for idx in xrange(MAX_TIMEOUT):
            time.sleep(1)
            if not (self.fb_bot.is_busy() or self.fb_bot.is_blocked()):
                break
        else:
            self.fail("Post processing did not finish after waiting %s seconds" % MAX_TIMEOUT)

        self.assertEqual(FacebookPost.objects.count(), 1)
        created_post = FacebookPost.objects.find_one()
        self.assertTrue(isinstance(created_post.user_profile, UserProfile))
        self.assertDictEqual(created_post.user_profile.platform_data,
                             {'first_name': 'Mnt1',
                              'gender': 'female',
                              'id': '100008124789809',
                              'last_name': 'Poster',
                              'link': 'https://www.facebook.com/profile.php?id=100008124789809',
                              'locale': 'en_US',
                              'name': 'Mnt Poster',
                              'picture': {'data': {'is_silhouette': True,
                                                   'url': 'https://fbcdn-profile-a.akamaihd.net/hprofile-ak-xpf1/t1.0-1/c15.0.50.50/p50x50/1509246_10150002137498325_1584423246374331045_n.jpg'}},
                              'updated_time': '2014-04-04T12:11:53+0000'})
        self.assertEqual(created_post.content, 'Testing post-reply pair')
        self.assertTrue(str(srv_channel.inbound_channel.id) in created_post.channel_assignments)
        self.assertEqual(created_post.channel_assignments[str(srv_channel.inbound_channel.id)], 'highlighted')

        self.fb_bot.post_received(json.dumps(reply_data))

        for idx in xrange(MAX_TIMEOUT):
            time.sleep(1)
            if not (self.fb_bot.is_busy() or self.fb_bot.is_blocked()):
                break
        else:
            self.fail("Post processing did not finish after waiting %s seconds" % MAX_TIMEOUT)

        self.assertEqual(FacebookPost.objects.count(), 2)
        created_reply = [p for p in FacebookPost.objects() if p.content == 'Thanks for reaching out. Testing scenario'][0]
        self.assertTrue(str(srv_channel.outbound_channel.id) in created_reply.channel_assignments)
        self.assertTrue(isinstance(created_reply.user_profile, UserProfile))
        self.assertDictEqual(created_reply.user_profile.platform_data,
                             {'first_name': 'Mnt',
                              'gender': 'female',
                              'id': '100008145211355',
                              'last_name': 'Poster',
                              'link': 'https://www.facebook.com/profile.php?id=100008145211355',
                              'locale': 'en_US',
                              'name': 'Mnt Creator',
                              'picture': {'data': {'is_silhouette': True,
                                                   'url': 'https://fbcdn-profile-a.akamaihd.net/hprofile-ak-xpf1/t1.0-1/c15.0.50.50/p50x50/1509246_10150002137498325_1584423246374331045_n.jpg'}},
                              'updated_time': '2014-04-04T12:11:53+0000'})

        for idx in xrange(MAX_TIMEOUT * 4):
            created_post.reload()
            if created_post.channel_assignments[str(srv_channel.inbound_channel.id)] == 'replied':
                break
        else:
            self.fail("Inbound post was never switched to replied status")

        self.fb_bot.stop()

        for idx in xrange(MAX_TIMEOUT * 4):
            time.sleep(1)
            if not self.fb_bot.isAlive():
                break
        else:
            self.fail("Bot never stopped after waiting %s seconds." % (4 * MAX_TIMEOUT))

