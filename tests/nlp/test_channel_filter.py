import pytz
import unittest
import json
from datetime    import date, timedelta
from collections import defaultdict

from solariat_bottle          import settings
from solariat_bottle.configurable_apps import APP_GSA

from solariat_bottle.db.channel_hot_topics import ChannelHotTopics
from solariat_bottle.db.channel.twitter    import EnterpriseTwitterChannel as ETC
from solariat_bottle.db.channel.base       import Channel
from solariat_bottle.db.speech_act         import SpeechActMap
from solariat_bottle.db.post.base          import Post
from solariat_bottle.db.roles              import AGENT
from solariat_bottle.db                    import channel_filter as cf

from solariat.utils.timeslot import (
    parse_date_interval, utc, now, datetime_to_timeslot)


from solariat_bottle.tests.base import UICase, SA_TYPES


def time_range():
    base_dt = utc(date.today())
    from_dt = base_dt - timedelta(hours=24)
    to_dt   = base_dt + timedelta(hours=24)
    return {
        'from' : from_dt .strftime("%m/%d/%Y"),
        'to'   : to_dt   .strftime("%m/%d/%Y")
    }

def get_channel_stats(user, channel, from_, to_, level):
    from solariat_bottle.db.channel_stats import ChannelStats

    fields = [
        'number_of_starred_posts',
        'number_of_highlighted_posts',
        'number_of_rejected_posts',
        'number_of_discarded_posts'
    ]

    #aggregate stats
    result = defaultdict(int)
    for stats in ChannelStats.objects.by_time_span(
        user,
        channel,
        start_time = from_,
        end_time   = to_,
        level      = level
    ):
        for f in fields:
            result[f] += getattr(stats, f)

    return result

def filtered_speech_acts(channels, assignments):
    res = []
    for p in Post.objects(channels__in=[c.id for c in channels]):
        for c in p.channels:
            assert str(c) in p.channel_assignments, str(c)
            if p.channel_assignments[str(c)] in assignments:
                res.append(p)
    return res

def add_user_to_account(user, account):
    ''' Sets user up as a general purpose account team member '''

    # Add to account
    account.add_user(user)

    # Add access for channels
    for channel in account.get_current_channels():
        channel.add_perm(user)


@unittest.skip("""
This testsuite uses ESBasedChannelFilter implementation.
We decided to get rid of ES, so this TestSuite is obsolete now.
""")
class ChannelFilterBaseCase(UICase):
    def setUp(self):
        UICase.setUp(self)

        update_settings = dict(
            CHANNEL_FILTER_CLS       = 'ESBasedChannelFilter', #'DbChannelFilter'<<
            POST_MATCH_INDEX_NAME    = 'test_channelfilteritems',
            POST_MATCH_DOCUMENT_NAME = 'test_channelfilteritem'
        )
        self.stored_settings = {}
        for k, v in update_settings.items():
            if hasattr(settings, k):
                self.stored_settings[k] = getattr(settings, k)
            else:
                self.stored_settings[k] = '!delete'
            setattr(settings, k, v)

        for c in Channel.objects():
            c.delete()

        self.time_range = time_range()

        self.created_at     = now()
        self.created_at_str = self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        
        # Inbound Channel Setup.
        self.channel = Channel.objects.create_by_user(
            self.user, title='TestChannel',
            account=self.account,
            type='twitter', intention_types=SA_TYPES)

        self.inbound = self.channel

        self.channel_extra = Channel.objects.create_by_user(
            self.user, title='TestChannel Extra',
            account=self.account,
            type='twitter', intention_types=SA_TYPES)

        self.outbound = ETC.objects.create_by_user(
            self.user, title='Compliance Review Outbound',
            account=self.account,
            access_token_key='dummy_key',
            access_token_secret='dummy_secret')

        # User and account
        self.account.outbound_channels = {'Twitter':str(self.outbound.id)}
        self.account.selected_app = APP_GSA
        self.account.save()
        #self.user.account = self.account
        #self.user.save()
        self.login()

        self.channels = [self.channel, self.channel_extra]

        #create posts
        contents = [
            "I need a laptop",
            "I need a new laptop",
            "I need a laptop too",
            "Any recommendation about a good laptop?",
            "I need a phone",
            "I need some foo"
        ]

        self.posts = []

        for content in contents:
            self.posts.append(self._create_db_post(content,
                                                   channels=self.channels,
                                                   demand_matchables=False))

        self.relevant_channels = [self.channel, self.inbound, self.outbound]

        self.NEED_LAPTOPS = set([p.plaintext_content for p in self.posts[:3]])

    def tearDown(self):
        for k, v in self.stored_settings.items():
            if v == '!delete':
                delattr(settings, k)
            else:
                setattr(settings, k, v)
        super(ChannelFilterBaseCase, self).tearDown()

    def _reject_post(self, post, user=None, channels=None):
        settings.ON_TEST = True  #ensure task queue completed
        user = user or self.user
        if not user.account:
            user.account = self.account
            user.save()

        if channels is None:
            channels = self.channels

        return post.handle_reject(user, channels)

    def _star_post(self, post):
        settings.ON_TEST = True  #ensure task queue completed
        return post.handle_accept(self.user, self.channels)

    def _fetch(self, data):
        '''
        Obtain posts for a time range and intention type.
        '''
        resp = self.client.post('/posts/json',
            data=json.dumps(data),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))
        return resp

    def _fetch_posts(self, topics, time_point, intentions, **kw):
        #'channel_id': kw.get('channel_id') or self.channel_id,
        data = {
            'channel_id' : str(self.channel_id),
            'from'       : time_point,
            'to'         : (self.created_at + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),
            'intentions' : intentions,
            'thresholds' : dict(intention=.1)
        }

        if topics != []:
            data['topics'] = topics

        data['topics'] = [ dict(topic=t, topic_type='leaf') for t in data['topics']]

        # Handle filter for assignments in terms of statuses.
        if 'assignments' not in kw or kw.get('assignments') == None:
            assignments = set(SpeechActMap.STATUS_MAP.keys())
        else:
            assignments = kw.get('assignments')

        data['statuses'] = [
            SpeechActMap.STATUS_NAME_MAP[SpeechActMap.STATUS_MAP[a]]
            for a in assignments ]

        resp = self._fetch(data)

        self.assertTrue('list' in resp)

        return resp['list']

    def _get_laptop_posts(self, assignments=None, print_it=False):

        all_posts = []
        posts_content = set()
        for channel in self.channels:

            posts = self._fetch_posts(
                ['laptop'],
                self.created_at_str,
                ['asks', 'needs', 'consideration'],
                channel_id = str(channel.id),
                assignments   = assignments)

            for post in posts:
                if post['text'] not in posts_content:
                    all_posts.append(post)
                    posts_content.add(post['text'])

        if print_it:
            print posts_content

        return all_posts

    def get_stats(self, channels=None, stats=['number_of_starred_posts', 'number_of_highlighted_posts']):
        if not channels:
            channels = self.channels

        level = 'month'

        from_dt, to_dt = parse_date_interval(self.time_range['from'], self.time_range['to'])

        stats_by_channel = {}
        for channel in channels:
            cs = get_channel_stats(self.user, channel, from_dt, to_dt, level)
            stats_by_channel[str(channel.id)] = tuple(map(cs.get, stats))

        return stats_by_channel

    def _get_accept_stats(self, channels=None):
        """Returns counters for starred/highlighted posts by channel
            {channel_id1: (starred_counter1, highlighted_counter1),
            channel_id2: (starred_counter1, highlighted_counter2), ...}
        """
        return self.get_stats(channels)

    def _get_reject_stats(self, channels=None):
        "Returns counters for rejected/discarded posts by channel"
        return self.get_stats(channels, ['number_of_rejected_posts', 'number_of_discarded_posts'])

class PostRejectTestCase(ChannelFilterBaseCase):

    def _get_stats(self, channel=None):
        '''Helper method to couunt all the occurences for a parent topic'''
        if not channel:
            channel = self.channel

        stats = ChannelHotTopics.objects.by_time_span(
            channel,
            statuses = [SpeechActMap.REJECTED],
            from_ts  = datetime_to_timeslot(self.created_at, 'month')
        )

        stats = [s for s in stats if s['topic'] == 'laptop']
        assert len(stats) <= 1
        if stats == []:
            topic_count = 0
        else:
            topic_count = stats[0]['topic_count']

        return topic_count, self._get_reject_stats([channel])[str(channel.id)]

    def test_counters(self):
        settings.ON_TEST = True  #ensure task queue completed
        self._reject_post(self.posts[0])
        self.assertEqual(self.channel.channel_filter.reject_count, 1)
        self.assertEqual(self.channel.channel_filter.accept_count, 0)
        self._star_post(self.posts[1])
        self.assertEqual(self.channel.channel_filter.accept_count, 1)
        self.channel.channel_filter.retrain()
        self.assertEqual(self.channel.channel_filter.accept_count, 1)
        self.assertEqual(self.channel.channel_filter.reject_count, 1)
        self.channel.channel_filter.reset()
        self.assertEqual(self.channel.channel_filter.accept_count, 0)
        self.assertEqual(self.channel.channel_filter.reject_count, 0)


    def test_reject(self):
        '''
        Start with all posts actionable. Then reject one and make sure the signal
        propagates correctly.
        '''
        settings.ON_TEST = True  #ensure task queue completed
        post = self.posts[0]
        post.reload()

        # Reject one and make sure it is no longer assigned
        self._reject_post(post, channels=[self.channel])
        self.assertEqual(self.channel.is_assigned(post), False)

        # Note that the rejected and discarded stats resolve to the same REJECTED state internally
        self.assertEqual(len(filtered_speech_acts(self.relevant_channels, ['rejected', 'discarded'])), 1+5)
        posts = self._get_laptop_posts(assignments=['rejected'])
        self.assertEqual(len(posts), 4)
        posts = self._get_laptop_posts(assignments=['discarded'])
        self.assertEqual(len(posts), 4)

        #one left unfiltered after we reject for other channel
        self._reject_post(post, channels=[self.channel_extra])
        self.assertEqual(len(filtered_speech_acts(self.relevant_channels, ['rejected', 'discarded'])), 11)
        posts = self._get_laptop_posts(assignments=['highlighted', 'starred'])
        self.assertEqual(len(posts), 0)
        tc, post_count = self._get_stats()
        self.assertEqual(post_count, (1, 5))

        # now make a new post with the same topic and intention as rejected one
        post = self._create_db_post('I need a laptop')
        # it should be filtered out
        self.assertEqual(post.channel_assignments[str(self.channel.id)], 'discarded')
        term_count, post_count = self._get_stats()
        self.assertEqual(term_count, tc+1)
        self.assertEqual(post_count, (1, 6))

        #Now reject the "Any recommendations about a good laptop?"
        #and check the term counters for 'laptop' rejected
        self._reject_post(self.posts[3])
        term_count, post_count = self._get_stats()
        self.assertEqual(term_count, 5)
        self.assertEquals(post_count, (2, 5))

        posts = self._get_laptop_posts(assignments=['rejected'])
        self.assertEqual(len(posts), 4)
        posts = self._get_laptop_posts(assignments=['discarded'])
        self.assertEqual(len(posts), 4)

    def test_reject_after_star(self):
        settings.ON_TEST = True  #ensure task queue completed

        initial_count = len(self._get_laptop_posts())
        post = self.posts[0]
        self._star_post(post)  #first star
        post.reload()
        self._reject_post(post)  #then reject
        posts = self._get_laptop_posts()
        self.assertEqual(len(posts), initial_count)

        term_count, post_count = self._get_stats()
        self.assertEquals(post_count, (1, 5))  # 1 rejected and related ones discarded

        #now make a new post with the same topic and intention as rejected one
        self._create_db_post('I need a laptop')
        term_count, post_count = self._get_stats()
        self.assertEqual(post_count, (1, 6))  # +1 discarded post

        accept_stats = self._get_accept_stats([self.channel])[str(self.channel.id)]
        self.assertEqual(accept_stats, (0, 0))

    def test_reject_ui(self):
        #Test ui call
        post = self.posts[0]
        data = {'posts':[post.id],
                'channels':[str(channel_id) for channel_id in post.channels]}

        resp = self.client.post('/commands/reject_post',
            data=json.dumps(data),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))

        posts = self._get_laptop_posts(assignments=['discarded'])
        self.assertEqual(len(posts), 4) #propagate now further than just intention, so for now laptop topics

        term_count, post_count = self._get_stats()
        self.assertEquals(post_count[0], 1)  # 1 rejected
        self.assertEquals(term_count, 4)

        # Now add in the same post again, and verify that it is filtered correctly
        post = self.posts[0]
        data = dict(content=post.plaintext_content,
                    channel=str(post.channels[0]),
                    message_type=False)
        resp = self.client.post('/commands/create_post',
                                data=json.dumps(data))

        resp = json.loads(resp.data)
        self.assertEqual(resp['item']['platform'], post.platform)
        self.assertEqual(resp['item']['channel_assignments'], {data['channel']: 'discarded'})

class PostStarTestCase(ChannelFilterBaseCase):
    def _get_stats(self):
        channel = self.channel
        return self._get_accept_stats([channel])[str(channel.id)]

    def test_star(self):
        posts = self._get_laptop_posts()
        self.assertEqual(len(posts), 4)
        post_count = self._get_stats()
        self.assertEquals(post_count, (0, 6))
        settings.ON_TEST = True  #ensure task queue completed
        post = self.posts[0]

        # Since nothing has happened to the post yet, we will query for candidates
        # and expect all needs, for a laptop.

        self._star_post(post)

        posts = self._get_laptop_posts(assignments=['assigned', 'highlighted', 'starred'])
        self.assertEqual(len(posts), 4)

        post_count = self._get_stats()
        self.assertEquals(post_count, (1, 5))  # 1 starred and 5 highlighted

        #now make a new post with the same topic and intention as starred one
        self._create_db_post('I need a laptop')
        post_count = self._get_stats()
        self.assertEqual(post_count, (1, 6))  #3+1 starred post

    def test_star_after_reject(self):
        ''' Make sure we correctly handle the state transition for first
        rejecting the post, and then starring it. Causes a transition
        of state back to available
        '''
        posts = self._get_laptop_posts()
        self.assertEqual(len(posts), 4)
        post_count = self._get_stats()
        self.assertEquals(post_count, (0, 6))

        settings.ON_TEST = True  #ensure task queue completed
        post = self.posts[0]

        #first reject
        self._reject_post(post)
        self.assertEquals(self._get_stats(), (0, 0))

        #then star
        self._star_post(post)
        self.assertEqual({p.plaintext_content for p in Post.objects(channels__in=[self.channel.id])
                         if self.channel.is_assigned(p)}.intersection(self.NEED_LAPTOPS),
                         self.NEED_LAPTOPS)

        self.assertEquals(self._get_stats(), (1, 5))

        #now make a new post with the same topic and intention as starred one
        self._create_db_post('I need a laptop')
        post_count = self._get_stats()
        self.assertEqual(post_count, (1, 6))

        # Check all rejected ones
        reject_stats = self._get_reject_stats([self.channel])[str(self.channel.id)]
        self.assertEqual(reject_stats, (0, 0))

class FilteredPostsQueryCase(ChannelFilterBaseCase):

    def test_get_unfiltered(self):
        ''' Because the channel has no keywords set which match, nothing will be retrurned
        '''
        posts = self._get_laptop_posts(assignments=['assigned', 'starred', 'highlighted'])
        self.assertEqual(len(posts), 4)

    def test_get_starred_posts(self):
        ''' Simple case for starring a post.
        '''
        self._star_post(self.posts[0])
        #expected 1 starred and 2 highlighted (NEEDS)

        posts = self._get_laptop_posts(assignments=['starred', 'highlighted'])
        self.assertEqual(len(posts), 4)


    def test_get_rejected_posts(self):
        '''' REJECTED posts arise if posts are rejected or discarded.
        '''
        self._reject_post(self.posts[0])
        #expected 1 rejected and 2 discarded

        self.assertEqual({p.plaintext_content for p in Post.objects(channels__in=[self.channel.id])
                         if not self.channel.is_assigned(p)}.intersection(self.NEED_LAPTOPS),
                         self.NEED_LAPTOPS)

        # Now that we propagate similarity further than simple intention name, every laptop post
        # should be rejected.
        posts = self._get_laptop_posts(assignments=['starred', 'highlighted'])
        self.assertEqual(len(posts), 0)


@unittest.skip("Response and inbox are deprecated")
class EngageFilteringCase(ChannelFilterBaseCase):

    def setUp(self):
        super(EngageFilteringCase, self).setUp()

        # Configure outbound
        self.outbound.review_outbound = True
        self.outbound.save()

        # Set up the reviewer
        self.reviewer = self._create_db_user(account=self.account,
                                             email='reviewer@solariat.com',
                                             password='12345', roles=[AGENT])
        add_user_to_account(self.reviewer, self.account)
        review_team = self.outbound.get_review_team()
        review_team.add_user(self.reviewer)

        # Set up the lowly social operator
        self.team_member = self._create_db_user(account=self.account,
                                                email='team_member@solariat.com',
                                                password='12345', roles=[AGENT])
        add_user_to_account(self.team_member, self.account)



        self.outbound.add_perm(self.reviewer)
        self.outbound.add_perm(self.team_member)
        self.reviewer.reload()
        self.team_member.reload()
        self.outbound.reload()

    def test_engage_reject_with_single_channel(self):
        # Log in the team member, who has review rights
        self.login(self.team_member.email)

        # Reject the response
        resp = Response.objects()[0]
        self.assertFalse(resp.channel.can_edit(self.team_member))   # Agent should no longer have edit rights to channel
        self.assertTrue(resp.can_edit(self.team_member))   # He should have it to response however

        # Verify channel assignment policy - deterministic.
        self.assertEqual(resp.channel, self.channel)

        # The response is Pending. And we will have a reviewer reject it. If
        # a pending response is rejected then we assume that applies to
        # the inbound channel, and this means that the post is rejected.
        self.assertEqual(resp.status, 'pending')
        engage.do_reject(resp, self.team_member)


        # Confirm the post is rejected for the inbound channel
        resp.reload()
        self.assertEqual(resp.post.channel_assignments[str(self.channel.id)],
                         'rejected')

        # The rejection is for the post and the response is not re-assigned.
        self.assertEqual(resp.channel, self.inbound)

        # We should also expect similar responses to be discarded
        self.assertEqual(len(list(Response.objects(status__in=['rejected']))), 1)


    def test_engage_post_noreview(self):
        # Log in as reviewer
        self.login(self.reviewer.email)
        # Reviewer should no longer have edit to channel
        self.assertFalse(self.outbound.can_edit(self.reviewer), self.outbound.title)
        resp = Response.objects()[0]
        original_channel = resp.channel
        self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                                    str(resp.id), str(resp.matchable.id), str(resp.post.id)))
        #engage.do_post(True, resp, str(resp.post.id), resp.matchable, self.reviewer)
        resp.reload()

        # Posted because we are a reviewer
        self.assertTrue(resp.status, 'posted')
        self.assertTrue(resp.channel, self.outbound)

        # Because it is posted, would expect to have learned something. Should see the original
        # channel with an entry in it.
        original_channel.reload()
        original_channel.channel_filter.reload()
        learned = [ p.vector['content'] for p in original_channel.channel_filter.accepted_items ]
        self.assertTrue(resp.post.plaintext_content in learned)

        # Since no review is required, would also expect to see that the outbound
        # channel filter has been updated
        resp.channel.channel_filter.reload()
        self.assertEqual(resp.channel.channel_filter.accepted_items[0].vector['content'],
                         resp.content)
        self.assertEqual(resp.channel.apply_filter(resp)[0], 'highlighted')


    def test_engage_post_reviewrequired(self):
        # First post as the team member, and it will require a review
        self.login(self.team_member.email)
        resp = Response.objects()[0]
        original_channel = resp.channel

        # Now switch to the reviewr, and post it
        engage.do_post(True, resp, str(resp.post.id), resp.matchable, self.team_member)
        resp.reload()

        # It should be in a pending state, but we should have learned for the original channel
        original_channel.channel_filter.reload()
        self.assertTrue(resp.post.plaintext_content in [
                p.vector['content'] for p in original_channel.channel_filter.accepted_items])

        # No learning on the outbound channel - wait for reviewer
        resp.channel.channel_filter.reload()
        self.assertEqual(list(resp.channel.channel_filter.accepted_items), [])

    def test_engage_post_reviewer(self):
        # Post again - review required
        self.login(self.team_member.email)
        resp = Response.objects()[0]
        self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                                str(resp.id), str(resp.matchable.id), str(resp.post.id)))
        #engage.do_post(True, resp, str(resp.post.id), resp.matchable, self.team_member)
        resp.reload()

        # review it and confirm result
        self.login(self.reviewer.email)
        self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(resp.id), str(resp.matchable.id), str(resp.post.id)))
        #engage.do_post(True, resp, str(resp.post.id), resp.matchable, self.reviewer)
        resp.reload()
        resp.channel.channel_filter.reload()
        self.assertEqual(resp.channel.channel_filter.accepted_items[0].vector['content'], resp.content)

    def test_engage_reject_reviewer(self):
        # Post again - review required. Team member doing something.
        self.login(self.team_member.email)
        resp = Response.objects()[0]
        print "A", resp
        engage.do_post(True, resp, str(resp.post.id), resp.matchable, self.team_member)
        resp.reload()
        print "B", resp

        # review it and confirm result
        self.login(self.reviewer)
        before_count = Post.objects(channels__in=[c.id for c in self.relevant_channels]).count()
        engage.do_reject(resp, self.reviewer)

        # The outbound post should be created in a rejected state
        after_count = Post.objects(channels__in=[c.id for c in self.relevant_channels]).count()
        self.assertEqual(after_count, before_count + 1)
        resp.reload()
        print "C", resp
        resp.channel.channel_filter.reload()

        rejected_posts = [post for post in Post.objects(channels=str(resp.channel.id))
                          if resp.matchable.creative in post.plaintext_content]

        # Should be no acepted items
        self.assertEqual(list(resp.channel.channel_filter.accepted_items), [])

        # 2 rejected items. For now, one for the in/out pair, and one for just the outbound.
        print "C", resp
        self.assertEqual(len(resp.channel.channel_filter.rejected_items), 2)
        possible_rejected_items = [resp.id] + [rej.id for rej in rejected_posts]
        for item in resp.channel.channel_filter.rejected_items:
            self.assertTrue(item['item_id'] in possible_rejected_items,
                            (item['item_id'], possible_rejected_items))
            if item['item_id'] == resp.id:
                self.assertEqual(resp.content, item.vector['content'])
            elif item['item_id'] in [rej.id for rej in rejected_posts]:
                self.assertEqual(rejected_posts[0].plaintext_content, item.vector['content'])

    def test_auto_dispatch(self):
        '''
        If we have a review, and a new response is submitted for review,
        want to be able to threshold it, and skip the review if necessary
        '''
        # Reviewer can just post first one
        self.login(self.reviewer.email)
        resp = Response.objects()[0]
        self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                                    str(resp.id), str(resp.matchable.id), str(resp.post.id)))
        #engage.do_post(True, resp, str(resp.post.id), resp.matchable, self.reviewer)
        resp.reload()
        self.assertEqual(resp.status, 'posted')

        # New post and response
        new_post = self._create_db_post('Post different content. Should ask fore review.',
                                    channels=self.channels,
                                    demand_matchables=True)

        new_response = Response.objects.upsert_from_post(new_post)

        # Switch to team member.
        self.login(self.team_member.email)

        # The response is pretty much identical, so when the team member
        # posts it, it should end up posted
        # review it and confirm result
        self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                            str(new_response.id), str(new_response.matchable.id), str(new_response.post.id)))
        #engage.do_post(True, new_response, str(new_response.post.id), new_response.matchable, self.team_member)
        new_response.reload()
        self.assertEqual(new_response.status, 'review-post')

    def test_auto_filter(self):
        '''
        Team member posts, reveiwer declines, team member posts again. Auto-filterd
        '''
        # Team member can just post first one
        self.login(self.team_member.email)
        resp = Response.objects()[0]
        self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(resp.id), str(resp.matchable.id), str(resp.post.id)))
        #engage.do_post(True, resp, str(resp.post.id), resp.matchable, self.team_member)
        resp.reload()
        self.assertEqual(resp.status, 'review-post')

        # Reviewer rejects
        self.login(self.reviewer.email)
        engage.do_reject(resp, self.reviewer)
        resp.reload()
        self.assertEqual(resp.status, 'rejected')

        # New post and response
        self.login(self.team_member.email)
        new_post = self._create_db_post(resp.post.content,
                                    channels=self.channels,
                                    demand_matchables=True)
        new_response = Response.objects.upsert_from_post(new_post)
        self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(new_response.id), str(new_response.matchable.id), str(new_response.post.id)))
        #engage.do_post(True, new_response, str(new_response.post.id), new_response.matchable, self.team_member)
        new_response.reload()
        self.assertEqual(new_response.status, 'filtered')

    def test_retweet(self):
        self.login(self.reviewer.email)
        resp = Response.objects()[0]
        self.client.post('/commands/retweet_response',
                                        data='{"response":"%s"}' % str(resp.id))
        #engage.do_retweet(True, resp, self.reviewer)
        resp.reload()
        self.assertEqual(resp.status, 'retweeted')
        self.assertTrue(resp.channel.channel_filter.accepted_items[0].vector['content'].find("__RETWEETED__") > 0)

        # New post and response
        self.login(self.team_member.email)
        new_post = self._create_db_post('Post different content. Should ask fore review.',
                                    channels=self.channels,
                                    demand_matchables=True)
        new_response = Response.objects.upsert_from_post(new_post)

        # Retweet - and see the result is dispatched
        self.client.post('/commands/retweet_response',
                                        data='{"response":"%s"}' % str(new_response.id))
        #engage.do_retweet(True, new_response, self.team_member)
        new_response.reload()
        self.assertEqual(new_response.status, 'review-retweet')

class ContentFilterTestCase(ChannelFilterBaseCase):

    def test_basics(self):
        filter_item = cf.ChannelFilterItem(channel_filter=self.channel.channel_filter,
                                           item_id=self.channel.id, # For grins
                                           vector=dict(content='I need a laptop'),
                                           filter_type='starred')

        filter_item.save()
        filter_item.deploy(refresh=True)
        self.assertTrue(filter_item.is_active)
        filter_item.withdraw(refresh=True, make_inactive=True)
        self.assertFalse(filter_item.is_active)
        results = filter_item.objects.search(
            channel=self.channel,
            item=dict(content='I need a laptop'),
            filter_type=filter_item.filter_type)
        self.assertEqual(results, [])

        # Now redeploy and test matching
        filter_item.deploy(refresh=True)
        filter_item = cf.ChannelFilterItem(channel_filter=self.channel.channel_filter,
                                           item_id=self.outbound.id,
                                           vector=dict(content='I need a laptop bag'),
                                           filter_type='starred')

        filter_item.save()
        filter_item.deploy(refresh=True)

        results = filter_item.objects.search(
            channel=self.channel,
            item=dict(content='I need a laptop and shoes and a bag'),
            filter_type=filter_item.filter_type)

        self.assertEqual(results[0]['content'], 'I need a laptop bag', results)

    def test_reject(self):
        post = self.posts[0]
        self.assertEqual(cf.ChannelFilterItem.objects.count(), 0)
        self._reject_post(post)  #first reject
        self.assertEqual(cf.ChannelFilterItem.objects.count(), len(post.channels))
        self._star_post(post)
        self.assertEqual(cf.ChannelFilterItem.objects.count(), len(post.channels))

        results = self.channel.channel_filter._search(
            item=dict(content=post.plaintext_content),
            filter_type='accepted')

        self.assertEqual(results[0]['content'], post.content, results)


if __name__ == '__main__':
    unittest.main()
