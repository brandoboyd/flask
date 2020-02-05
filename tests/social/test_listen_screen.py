# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from datetime import datetime, timedelta
import json
import unittest

from solariat_bottle.db.post.base     import Post
from solariat_bottle.db.channel.base  import Channel
from solariat_bottle.db.channel_stats import ChannelStats, no_post_created
from solariat_bottle.db.roles         import AGENT
from solariat.utils.timeslot   import now, utc, timestamp_ms_to_datetime

from solariat_bottle.tests.base import UICase


class TestGetPostsCase(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()


    def _fetch(self, data):
        resp = self.client.post('/posts/json',
                                data=json.dumps(data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))
        return resp

    def _fetch_posts(self, terms, from_, to_, intentions, channel=None, limit=None, offset=None,
                     last_query_time=None):
        channel = channel or self.channel
        data = {'channel_id': str(channel.id),
                'from': from_,
                'to': to_,
                'intentions': intentions,
                'thresholds' : {'influence' : 0, 'intention' : 0, 'receptivity' : 0}}
        if limit: data['limit'] = limit
        if offset: data['offset'] = offset
        if last_query_time: data['last_query_time'] = last_query_time

        if terms != []:
            data['topics'] = terms

        resp = self._fetch(data)

        self.assertTrue('list' in resp)

        return resp['list'], resp['last_query_time']


    def test_pagination_offset(self):
        """ Test that pagination doesn't bring back the same post multiple times """
        past_created = now() - timedelta(minutes=7*24*60)

        for idx in xrange(22):
            created = past_created + timedelta(minutes=idx)
            self._create_db_post(
                _created=created,
                content='I need a new laptop. My display is also bad. I want a new scholarship offer. ' + str(idx))

        to_date = now().strftime("%Y-%m-%d %H:%M:%S")
        from_date = (now() - timedelta(minutes=8*24*60)).strftime("%Y-%m-%d %H:%M:%S")

        previous_slot_contents = []
        limit = 10
        offset = 0

        (posts, last_query_time) = self._fetch_posts([], from_date, to_date, ['asks', 'needs'], self.channel,
                                                        limit=limit, offset=offset)
        self.assertEqual(len(posts), limit)

        # First test that without any new posts, filtering works just fine
        while posts:
            for p in posts:
                self.assertTrue(p['text'] not in previous_slot_contents)
            previous_slot_contents.extend([p['text'] for p in posts])
            offset += limit
            (posts, last_query_time) = self._fetch_posts([], from_date, to_date,
                                                        ['asks', 'needs'], self.channel,
                                                        limit=limit, offset=offset,
                                                        last_query_time=last_query_time)

        # Now test edge case where some new posts arrive after you already
        # have a batch of posts loaded, and check if we have any duplicates
        offset = 0
        (first_posts_batch, last_query_time) = self._fetch_posts([], from_date, to_date,
                                                                    ['asks', 'needs'], self.channel,
                                                                    limit=limit, offset=offset)
        first_content_batch = [p['text'] for p in first_posts_batch]

        date = timestamp_ms_to_datetime(last_query_time)
        for idx in xrange(27, 30):
            # These should all be newer than the existing one due to higher timedelta
            created = date + timedelta(minutes=idx)
            self._create_db_post(
                _created=created,
                content='I need a new laptop. My display is also bad. I want a new scholarship offer.' + str(idx))
        offset += limit
        # First if we don't pass in the last query time, we would expect 3 duplicates,
        # for the three new posts which arrived and would screw up the offset
        (new_posts_batch, _) = self._fetch_posts([], from_date, to_date,
                                                 ['asks', 'needs'], self.channel,
                                                 limit=limit, offset=offset,
                                                 last_query_time=None)
        duplicates = []
        for post in new_posts_batch:
            if post['text'] in first_content_batch:
                duplicates.append(post['text'])
        self.assertEqual(len(duplicates), 3)

        previous_slot_contents = []
        offset = 0
        (posts, last_query_time) = self._fetch_posts([], from_date, to_date,
                                                     ['asks', 'needs'], self.channel,
                                                     limit=limit, offset=offset,
                                                     last_query_time=last_query_time)
        while posts:
            for p in posts:
                self.assertTrue(p['text'] not in previous_slot_contents)
            previous_slot_contents.extend([p['text'] for p in posts])
            offset += limit
            (posts, last_query_time) = self._fetch_posts([], from_date, to_date,
                                                        ['asks', 'needs'], self.channel,
                                                        limit=limit, offset=offset,
                                                        last_query_time=last_query_time)



    @unittest.skip('Time range queries are not really supported')
    def test_get_posts(self):
        posts = self._fetch_posts(['carrot'], '01/01/2010',
                                  '01/02/2010',
                                  ['asks', 'needs'])
        self.assertEqual(len(posts), 0)

        posts = self._fetch_posts(['carrot', 'bar'], '01/01/2010',
                                  '01/01/2020',
                                  ['asks', 'needs'])
        self.assertEqual(len(posts), 4)

        day_ago = now() - timedelta(minutes=25*60)
        posts = self._fetch_posts(['carrot', 'bar'], '01/01/2010',
                                  day_ago.strftime('%m/%d/%Y'),
                                  ['asks', 'needs'])
        self.assertEqual(len(posts), 2)

        posts = self._fetch_posts(['carrot'], '01/01/2010', '01/01/2020',
                                  ['problem'])
        self.assertEqual(len(posts), 0)

        posts = self._fetch_posts(['carrot'], '01/01/2010', '01/01/2020',
                                  ['asks'])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['id_str'], str(self.post2.id))

        posts = self._fetch_posts([], '01/01/2010', '01/01/2020',
                                  ['asks', 'needs'])

        self.assertEqual(len(posts), 4)


class ListScreenMiscCase(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()
        self.post = self._create_db_post('I need a laptop bag',
                                         demand_matchables=True)

        from solariat_bottle.db.account import Account
        self.account1 = Account.objects.create(name='Acct1')

        for ch in Channel.objects.find_by_user(self.user):
            ch.account = self.account1
            ch.save()
            # Account switching now means we need to refresh permissions on this new account
            ch.add_perm(self.user)

        self.account1.add_user(self.user)
        self.user.current_account = self.account1
        self.user.reload()
        self.account2 = Account.objects.create(name='Acct2')

    def test_feedback(self):
        data = json.dumps(
            dict(post_id=self.post.id,
                 vote=False))
        resp = self.client.post('/feedback/json',
                                data=data,
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))
        self.post.reload()
        self.assertFalse(self.post.get_vote(self.user))

    @unittest.skip("Bookmark is deprecated")
    def test_channels_and_bookmarks_query(self):
        bmark = Bookmark.objects.create_by_user(
            self.user,
            title    = "Bookmark",
            channels = Channel.objects.find_by_user(self.user),
            start    = now() - timedelta(days=100),
            end      = now()
        )
        resp = self.client.post('/channels_and_bookmarks/json',
                                data={},
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertEqual(len(resp['list']), 2)
        bookmarks = [ x['bookmark_id'] for x in resp['list'] if x['type'] == 'bookmark' ]
        self.assertEqual(len(bookmarks), 1)
        self.assertTrue(str(bmark.id) in bookmarks)

    @unittest.skip("Bookmark is deprecated")
    def test_channels_and_bookmarks_su(self):
        su = self._create_db_user('su@solariat.com', account=self.account1, roles=[AGENT])
        su.is_superuser = True
        su.save()
        self.account2.add_user(su)
        su.save()

        bmark = Bookmark.objects.create_by_user(
            su,
            title    = "Bookmark",
            channels = Channel.objects.find_by_user(su),
            start    = now() - timedelta(days=100),
            end      = now()
        )
        self.login(su.email)
        resp = self.client.post('/channels_and_bookmarks/json',
            data={},
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertEqual(len(resp['list']), 2)
        bookmarks = [ x['bookmark_id'] for x in resp['list'] if x['type'] == 'bookmark' ]
        self.assertEqual(len(bookmarks), 1)
        self.assertTrue(str(bmark.id) in bookmarks)

        #change account
        su.current_account = self.account2
        resp = self.client.post('/channels_and_bookmarks/json',
            data={},
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertEqual(len(resp['list']), 0)


class TrendsCase(UICase):
    def setUp(self):
        UICase.setUp(self)
        self.login()

    def _create_posts(self):
        past_created = now() - timedelta(minutes=7*24*60)
        post1 = self._create_db_post(
            _created=past_created,
            content='i need some carrot')

        past_created = now() - timedelta(minutes=7*24*60+10)
        post2 = self._create_db_post(
            _created=past_created,
            content='Where I can buy a carrot?')

        self._create_db_post(content='i need some carrot')
        self._create_db_post(content='Where I can buy a carrot?')

        self.assertEqual(Post.objects(channels__in=[self.channel.id]).count(), 4)

        # It doubles, because of the built in topic __ALL__
        #self.assertEqual(SpeechActMap.objects.count(), 8)

    def _fetch(self, data):
        resp = self.client.post('/trends/json',
                                data=json.dumps(data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))
        return resp

    def test_time_plotting_all(self):

        self._create_posts()
        now_dt = now()

        data = {
            'channel_id' : self.channel_id,
            'from'       : (now_dt - timedelta(days=9)).strftime('%m/%d/%Y'),
            'to'         : now_dt.strftime('%m/%d/%Y'),
            'level'      : 'hour',
            'topics'     : [{'topic':'carrot', 'topic_type':'node'}],
            'plot_by'    : 'time'
            }

        results = self._fetch(data).get('list')
        self.assertTrue(results)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['level'],       'hour')
        self.assertEqual(results[0]['label'],       'carrot')
        self.assertEqual(results[0]['count'],       4)
        # self.assertEqual(results[0]['intention'],   'all')
        # self.assertEqual(results[0]['topic_type'],  'node')
        # number of results is variable since the level is 'hour'
        self.assertTrue(len(results[0]['data']) >= 9*24)
        self.assertTrue(len(results[0]['data']) <= 10*24)

        #print [(ts,c) for ts,c in results[0]['data'] if c]
        #self.assertEqual([c for _,c in results[0]['data'] if c],  [2, 2])  #need fix: depends on time running?
        self.assertEqual([c for _,c in results[0]['data'] if c][-1], 2)

    def test_share_plotting_asks(self):

        self._create_posts()
        now_dt = now()

        # pure topics are now only in sentiment report (top-topics only has problem posts)
        data = {
            'channel_id' : self.channel_id,
            'from'       : (now_dt - timedelta(days=9)).strftime('%m/%d/%Y'),
            'to'         : now_dt.strftime('%m/%d/%Y'),
            'level'      : 'day',
            'topics'     : [{'topic':'carrot', 'topic_type':'leaf'}],
            'intentions' : ['asks'],
            'plot_by'    : 'distribution',
            'group_by'   : 'topic',
            'plot_type'  : 'sentiment',
            }

        results = self._fetch(data)['list']
        self.assertEqual(
            results,
            [dict(
                # level      = 'day',
                data       = [[2, 2]],
                label      = 'carrot',
                # count      = 2,
                # intention  = 'asks',
                topic_type = 'leaf'
            )]
        )

    def test_share_plotting_all(self):

        self._create_posts()
        now_dt = now()

        data = {
            'channel_id' : self.channel_id,
            'from'       : (now_dt - timedelta(days=9)).strftime('%m/%d/%Y'),
            'to'         : now_dt.strftime('%m/%d/%Y'),
            'level'      : 'hour',
            'topics'     : [{'topic':'carrot', 'topic_type':'node'}],
            'intentions' : ['all'],
            'plot_by'    : 'distribution'
            }

        results = self._fetch(data)['list']
        self.assertEqual(
            results,
            [dict(
                data       = [[2, 4]],
                label      = 'carrot',
                topic_type = 'node',
            )]
        )

    #def test_stack_plotting(self):
    #    self._create_posts()
    #    now_dt = now()
    #    data = {
    #        'channel_id' : self.channel_id,
    #        'from'       : (now_dt - timedelta(days=9)).strftime('%m/%d/%Y'),
    #        'to'         : now_dt.strftime('%m/%d/%Y'),
    #        'terms'      : ['carrot'],
    #        'intentions' : ['asks', 'needs'],
    #        'plot_by'    : 'stack'
    #        }
    #    data = self._fetch(data)
    #    self.assertTrue(data.get('list'), data)

    #    self.assertEqual(data['list'], [
    #            {u'color': 1, u'data': [[2, 2]], u'stack': u'carrot', u'label': u'carrot||2||asks'},
    #            {u'color': 2, u'data': [[2, 2]], u'stack': u'carrot', u'label': u'carrot||2||needs'}])

class StatsCase(UICase):
    def setUp(self):
        UICase.setUp(self)
        self.login()
        first_date = utc(datetime(2012, 1, 1))
        post1 = self._create_db_post(
            _created=first_date,
            content = 'i need some carrot')
        self.assertEqual(Post.objects(channels__in=[self.channel.id]).count(), 1)

        # 1 jan + 10 minutes
        second_date  = first_date + timedelta(minutes=10)
        post2 = self._create_db_post(
            _created=second_date,
            content='where i can buy a carrot?')
        self.assertEqual(Post.objects(channels__in=[self.channel.id]).count(), 2)

        # 1 jan + 7 days
        third_date = first_date + timedelta(minutes=7*60*24)
        post3 = self._create_db_post(
            _created = third_date,
            content='i need some carrot')
        self.assertEqual(Post.objects(channels__in=[self.channel.id]).count(), 3)

        forth_date = third_date + timedelta(minutes=10)
        post4 = self._create_db_post(
            _created=forth_date,
            content='where i can buy a carrot?')
        self.assertEqual(Post.objects(channels__in=[self.channel.id]).count(), 4)

        # This will not be created, only for stats
        post5 = Post(channels=[self.channel.id],
                     content='LOL',
                     actor_id=post4.user_profile.id,
                     is_inbound=True,
                     _native_id='1',
                     _created=post4._created)
        self.assertEqual(Post.objects(channels__in=[self.channel.id]).count(), 4)
        no_post_created(
            post5,
            utc(forth_date + timedelta(minutes=10)))
        self.now = now()

    def _fetch(self, data):
        resp = self.client.post('/channel_stats/json',
                                data=json.dumps(data),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))
        return resp

    def test_performance_stats(self):
        nop = sum(
            x.number_of_posts for x in \
            ChannelStats.objects.by_time_span(self.user, self.channel, level='day')
        )
        self.assertEqual(nop, 5)
        data = {
            'channel_id' : self.channel_id,
            'from'       : '01/01/2012',
            'to'         : '01/31/2012',
            'level'      : 'day',
            'intention'  : 'all',
            'stats_type' : ['number_of_posts']
            }
        data = self._fetch(data)
        self.assertTrue('list' in data)
        items = data['list']
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(len(item['data']), 31)
        self.assertEqual(item['data'][0][1], 2)
        self.assertEqual(item['data'][7][1], 3)

        data = {
            'channel_id' : self.channel_id,
            'from'       : '01/01/2012',
            'to'         : '01/31/2012',
            'level'      : 'month',
            'intention'  : 'all',
            'stats_type' : ['number_of_posts', 'number_of_actionable_posts']
            }

        data = self._fetch(data)
        self.assertTrue('list' in data)
        items = data['list']
        self.assertEqual(len(items), 2)
        for item in items:
            if item['label'] == 'number_of_posts':
                self.assertEqual(item['count'], 5)
            if item['label'] == 'number_of_actionable_posts':
                self.assertEqual(item['count'], 4)


    def test_speech_acts_stats_needs(self):
        data = {
            'channel_id' : self.channel_id,
            'from'       : '01/01/2012',
            'to'         : '01/31/2012',
            'level'      : 'hour',
            'stats_type' : 'speech_acts',
            'intention'  : 'needs',
            }

        data = self._fetch(data)
        self.assertTrue('list' in data)
        items = data['list']
        self.assertEqual(len(items),                           1)       # always 1 (a single intention or "all")
        self.assertEqual(items[0]['label'],                    'needs')
        self.assertEqual(items[0]['count'],                    2)       # total 2 times
        self.assertEqual([c for _,c in items[0]['data'] if c], [1,1])   # 2 timeslots, 1 in each

    def test_speech_acts_stats_all(self):
        data = {
            'channel_id' : self.channel_id,
            'from'       : '01/01/2012',
            'to'         : '01/31/2012',
            'level'      : 'day',
            'stats_type' : 'speech_acts',
            'intention'  : 'all',
            }

        data = self._fetch(data)
        self.assertTrue('list' in data)
        items = data['list']
        self.assertEqual(len(items),                           1)       # always 1 (a single intention or "all")
        self.assertEqual(items[0]['label'],                    'all')
        self.assertEqual(items[0]['count'],                    4)       # total 4 times
        self.assertEqual([c for _,c in items[0]['data'] if c], [2,2])   # two timeslots, 2 in each

