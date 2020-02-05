# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
import json
import unittest

from random import randint
from datetime import timedelta

from solariat.utils.timeslot import now
from solariat_bottle.db.auth import default_access_groups
from solariat_bottle.db.account import Account
from solariat_bottle.db.channel.base import SmartTagChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.roles import ADMIN, AGENT, ANALYST

from .base import UICase


class BasePostsEndpointCase(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()

        self.created_at = now()
        self.created_at_str = self.created_at.strftime('%Y-%m-%d %H:%M:%S')

        for content in (
            'I need a bike. I like Honda.',
            'Can somebody recommend a sturdy laptop?',
            'I need an affordabl laptop. And a laptop bag',
            'Whatever you buy, let it be an Apple laptop',
            'I would like to have a thin and lightweight laptop.'
        ):
            self._create_db_post(
                content  = content,
                _created = now()
            )

    def _fetch(self, url, **kw):
        if kw.get('return_full_response', False):
            return_full_response = True
            del kw['return_full_response']
        else:
            return_full_response = False
        #resp = self.client.post(url, data=json.dumps(kw), content_type='application/json')
        data = self._post(url, kw)
        #self.assertEqual(resp.status_code, 200)
        #data = json.loads(resp.data)
        #self.assertTrue(data['ok'], data.get('error'))
        self.assertTrue('list' in data)
        if return_full_response:
            return data
        return data['list']


class TestPostsJson(BasePostsEndpointCase):

    def get_posts(self, topic_type, **kw):
        if 'topics' in kw:
            kw['topics'] = [dict(topic=t, topic_type=topic_type) for t in kw['topics']]
        return self._fetch('/posts/json', **kw)

    def test_responses_ok(self):
        """ Date out of scope so no results returned."""
        posts = self.get_posts('leaf', **{
                'channel_id' : str(self.channel.id),
                'from'       : '2011-03-24 15:00:00',
                'to'         : '2011-03-24 16:00:00',
                'topics'     : ['laptop'],
                'intentions' : ['needs'],
                'thresholds' : dict(intention=.5),
                })

        self.assertEqual(len(posts), 0)

        # empty statuses list
        posts = self.get_posts('leaf', **{
                'channel_id' : str(self.channel.id),
                'from'       : '2011-03-24 15:00:00',
                'to'         : '2011-03-24 16:00:00',
                'topics'     : ['laptop'],
                'intentions' : ['needs'],
                'thresholds' : dict(intention=.5),
                'statuses':[]
                })

        self.assertEqual(len(posts), 0)

        # empty agents list
        posts = self.get_posts('leaf', **{
                'channel_id' : str(self.channel.id),
                'from'       : '2011-03-24 15:00:00',
                'to'         : '2011-03-24 16:00:00',
                'topics'     : ['laptop'],
                'intentions' : [],
                'thresholds' : dict(intention=.5),
                'statuses':[],
                'agents':[]
                })

    def test_no_intentions(self):
        posts = self.get_posts('node', **{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'topics'     : ['laptop'],
            'intentions' : [],
            'thresholds' : dict(intention=.1),
            'statuses'   : ['actionable']
        })

        self.assertTrue(len(posts) >= 4)

    def test_post_intentions(self):
        self.get_posts('node', **{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'topics'     : ['laptop'],
            'intentions' : ['needs', 'asks', 'recommendation'],
            'thresholds' : dict(intention=.1),
            'statuses'   : ['actionable']
        })


    def test_post_no_topic(self):
        posts = self.get_posts('node',**{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'intentions' : ['needs', 'asks'],
            'thresholds' : dict(intention=.1),
            'statuses'   : ['actionable']
        })
        self.assertEqual(len(posts), 4)

        posts = self.get_posts('node',**{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'intentions' : ['needs', 'asks'],
            'thresholds' : dict(intention=.1),
            'statuses'   : ['actionable'],
            'agents'     : None
        })
        self.assertEqual(len(posts), 4)

        posts = self.get_posts('node',**{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'intentions' : ['needs', 'asks'],
            'thresholds' : dict(intention=.1),
            'statuses'   : None,
            'agents'     : None
        })
        self.assertEqual(len(posts), 4)

    def test_posts_many_topics(self):
        posts = self.get_posts('node', **{
                'channel_id' : str(self.channel.id),
                'from'       : self.created_at_str,
                'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'topics'     : ['bike', 'laptop'],
                'intentions' : ['needs', 'likes', 'asks', 'recommendation'],
                'thresholds' : dict(intention=.1),
                'statuses'   : ['actionable']
                })
        self.assertEqual(len(posts), 5)

    def test_matching_sentiments(self):
        """
        Contents based on setup are:

        (u'I need a bike. I like Honda.', Positive),
        (u'Can somebody recommend a sturdy laptop?', Neutral),
        (u'I need an affordabl laptop. And a laptop bag', Neutral),
        (u'Whatever you buy, let it be an Apple laptop', Neutral),
        (u'I would like to have a thin and lightweight laptop.', Neutral)
        """
        posts = self.get_posts('node', **{
                'channel_id' : str(self.channel.id),
                'from'       : self.created_at_str,
                'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'topics'     : ['bike', 'laptop'],
                'sentiments' : ['neutral'],
                'thresholds' : dict(intention=.1),
                'statuses'   : ['actionable']
                })
        # import ipdb; ipdb.set_trace()
        self.assertEqual(len(posts), 5)

    def test_nonmatching_sentiments(self):
        """
        Contents based on setup are:

        (u'I need a bike. I like Honda.', Positive),
        (u'Can somebody recommend a sturdy laptop?', Neutral),
        (u'I need an affordabl laptop. And a laptop bag', Neutral),
        (u'Whatever you buy, let it be an Apple laptop', Neutral),
        (u'I would like to have a thin and lightweight laptop.', Neutral)
        """
        posts = self.get_posts('node', **{
                'channel_id' : str(self.channel.id),
                'from'       : self.created_at_str,
                'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'topics'     : ['bike', 'laptop'],
                'sentiments' : ['positive', 'negative'],
                'thresholds' : dict(intention=.1),
                'statuses'   : ['actionable']
                })
        self.assertEqual(len(posts), 0)
        
    def test_posts_message_type(self):
        posts = self.get_posts('leaf', **{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'thresholds' : dict(intention=.1),
            'message_type' : [0]
        })
        # All posts should be by default message_type = 0 (public)
        self.assertTrue(len(posts) >= 4)
        
        posts = self.get_posts('leaf', **{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'thresholds' : dict(intention=.1),
            'message_type' : [1]
        })
        # All posts should be by default message_type = 0 (public)
        self.assertTrue(len(posts) == 0)
        
        self._create_db_post(
            content="This will be direct message",
            _created=now(),
            _message_type=1
        )
        posts = self.get_posts('leaf', **{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'thresholds' : dict(intention=.1),
            'message_type' : [1]
        })
        # All posts should be by default message_type = 0 (public)
        self.assertEqual(len(posts), 1)

    def test_posts_sorted_by_date(self):
        """
        Generate a bunch of random posts, all having some randomly generated
        dates in a [1 month before today .. 1 month after today] interval.
        Check then that they are properly sorted by date.
        """
        no_random_posts_to_gen = 15
        posts_content = ['I need a bike. I like Honda.',
                        'Can somebody recommend a sturdy laptop?',
                        'I need an affordabl laptop. And a laptop bag']
        for _ in xrange(no_random_posts_to_gen):
            post_content_idx = randint(0, len(posts_content) - 1)
            days_offset = randint(0, 58)
            hours_offset = randint(0, 24)
            minutes_offset = randint(0, 60)
            seconds_offeset = randint(0, 60)
            if days_offset < 29:
                created_at = self.created_at - timedelta(days=days_offset, 
                                                         hours=hours_offset,
                                                         minutes=minutes_offset,
                                                         seconds=seconds_offeset)
            else:
                created_at = self.created_at + timedelta(days=days_offset - 29, 
                                                         hours=hours_offset,
                                                         minutes=minutes_offset,
                                                         seconds=seconds_offeset)
            self._create_db_post(
                content  = posts_content[post_content_idx],
                _created = created_at
            )
            
        posts = self.get_posts('node', **{
                'from': (self.created_at - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'), 
                'to': (self.created_at + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'), 
                'topics': ['bike', 'laptop'], 
                'sort_by': 'time', 
                'channel_id': str(self.channel.id), 
                'thresholds': {'intention': 0, 'influence': 0, 'receptivity': 0}, 
                'statuses': ['actionable', 'actual', 'potential', 'rejected']})
        self.assertTrue(len(posts) >= 15, 
                        "At least 15 posts were generated and should be returned. Instead got %s" % len(posts))
        for idx in xrange(0, len(posts) - 1):
            self.assertTrue(posts[idx]['created_at'] >= posts[idx + 1]['created_at'], 
                            "Posts %s and %s were not propery sorted." % (posts[idx], posts[idx + 1]))

    def test_pagination(self):
        """
        Test pagination of /posts/json endpoint.
        """
         
        parameters = {
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'topics'     : ['bike', 'laptop', 'honda'],
            'intentions' : ['needs', 'likes', 'asks', 'recommendation'],
            'thresholds' : dict(intention=.1),
            'sort_by': 'time', 
            'limit'      : 2,
            'offset'     : 0,
        }
        
        # get first page

        response = self.get_posts('node',
                return_full_response=True,
                **parameters)

        print json.dumps(response)

        self.assertTrue('limit' in response)
        self.assertTrue('offset' in response)
        self.assertTrue('are_more_posts_available' in response)
        self.assertTrue('list' in response)

        print response

        self.assertEqual(len(response['list']), 2)
        self.assertEqual(len(response['list']), 2)

        self.assertTrue(response['are_more_posts_available'])
        
        # get second page

        parameters['offset'] = 2
        response = self.get_posts('node',
                return_full_response=True,
                **parameters)
        self.assertEqual(len(response['list']), 2)
        self.assertTrue(response['are_more_posts_available'])

        # get last page

        parameters['offset'] = 4
        response = self.get_posts('node',
                return_full_response=True,
                **parameters)
        self.assertEqual(len(response['list']), 1)
        self.assertFalse(response['are_more_posts_available'])

        # fetching page after last one

        parameters['offset'] = 10
        response = self.get_posts('node',
                return_full_response=True,
                **parameters)
        self.assertEqual(len(response['list']), 0)
        self.assertFalse(response['are_more_posts_available'])

    def test_language_queries(self):
        q = {
            'channel_id' : str(self.channel.id),
            'from'       : self.created_at_str,
            'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'topics'     : ['bike', 'laptop'],
            'sentiments' : ['neutral'],
            'thresholds' : dict(intention=.1),
            'statuses'   : ['actionable'],
            'languages'  : ['en']
        }
        posts = self.get_posts('node', **q)
        self.assertEqual(len(posts), 5)

        q['languages'] = []
        posts = self.get_posts('node', **q)
        self.assertEqual(len(posts), 5)

        q['languages'] = ['zh']
        posts = self.get_posts('node', **q)
        self.assertEqual(len(posts), 0)


@unittest.skip("We don't support api v1.2 anymore")
class TestPostsDetailsJson(BasePostsEndpointCase):

    '''
    def _get_token(self, username, password):
        post_data = {'username': username,
                     'password': password}
        resp = self.client.post("/api/v1.2/authtokens", data=json.dumps(post_data), content_type="application/json")
        data = json.loads(resp.data)
        self.assertTrue('item' in data, "Got auth response data: " + str(data))
        return data['item']['token']
    '''
    def _post_text(self, post_text, channel_id, token):
        post_data = dict(token=token,
                         channel_id=channel_id,
                         content=post_text,
                         sync=True)
        data = json.dumps(post_data)
        resp = self.client.post('/api/v1.2/posts/info',
                                data=data,
                                content_type='application/json')
        data = json.loads(resp.data)
        return data

    def test_get_post_details(self):
        user_mail = "admin_benchmark@solariat.com"
        user_pass = 'password'
        account = Account.objects.create(name="Search-Account")
        user = self._create_db_user(email=user_mail, password=user_pass, account=account,
                                    roles=[ADMIN, AGENT, ANALYST])
        channel = TwitterServiceChannel.objects.create_by_user(user, title="Matching Channel").inbound_channel
        acl = user.groups + default_access_groups(user)
        SmartTagChannel.objects.create_by_user(
                user,
                parent_channel=channel.id,
                title='tag',
                status='Active',
                acl=acl
            )
        token = self.get_token(user_mail, user_pass)

        posted_text = "This is a test message"
        response = self._post_text(posted_text, str(channel.id), token)

        data = response['item']

        self.assertTrue('content' in data and data['content'] == posted_text)
        self.assertTrue('smart_tags' in data)
        self.assertEqual(len(data['smart_tags']), 1)
        self.assertEqual(data['smart_tags'][0][0], 'tag')

        # try to send empty content
        def assert_error(content, channel_id, error_message):
            data = self._post_text(content, str(channel_id), token)
            self.assertFalse(data['ok'])
            self.assertTrue('error' in data)
            self.assertTrue(error_message in data['error'],
                            msg=u"%s not in %s" % (error_message, data['error']))

        for content in (' ', '   ', '   \r\t\n'):
            assert_error(content, channel.id, 'parameter value is invalid: content=')

        assert_error(posted_text, 'wrong-channel-id', "No Channel for {'id': u'wrong-channel-id'}")

    def test_post_excluded_tag(self):
        user_mail = "admin_benchmark@solariat.com"
        user_pass = 'password'
        account = Account.objects.create(name="Search-Account")
        user = self._create_db_user(email=user_mail, password=user_pass, account=account,
                                    roles=[ADMIN, AGENT, ANALYST])
        channel = TwitterServiceChannel.objects.create_by_user(user, title="Matching Channel").inbound_channel
        acl = user.groups + default_access_groups(user)
        st = SmartTagChannel.objects.create_by_user(
                user,
                parent_channel=channel.id,
                title='tag',
                status='Active',
                acl=acl
            )
        token = self.get_token(user_mail, user_pass)

        posted_text = "This is a test message"
        response = self._post_text(posted_text, str(channel.id), token)

        data = response['item']
        self.assertEqual(len(data['smart_tags']), 1)
        self.assertEqual(data['smart_tags'][0][0], 'tag')
        self.assertTrue(data['smart_tags'][0][1] > 0)

        # Now add a skipword to the smart tag
        st.skip_keywords.append('test')
        st.save()
        response = self._post_text(posted_text, str(channel.id), token)

        data = response['item']
        self.assertEqual(len(data['smart_tags']), 1)
        self.assertEqual(data['smart_tags'][0][0], 'tag')
        self.assertTrue(data['smart_tags'][0][1] == 0)

