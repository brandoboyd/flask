# coding=utf-8
import json
import random
import unittest

from solariat_bottle.configurable_apps import APP_GSA
from solariat_nlp.sa_labels import get_sa_type_title_by_name as get_sa_type_by_name

from solariat_bottle.tests.base import UICase, ProcessPool
from solariat_bottle.db.user import User
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel, EnterpriseTwitterChannel, KeywordTrackingChannel
from solariat_bottle.db.roles import AGENT
from solariat.utils.timeslot import parse_datetime


def gen_profile():
    user_id = random.randint(1e6, 1e7)
    return {"user_id": str(user_id), "user_name": "Name_%s" % user_id}

@unittest.skip("Responses and Matchables are deprecated")
class EngageScreenTest(UICase):
    def setUp(self):
        super(EngageScreenTest, self).setUp()
        self.account.update(selected_app=APP_GSA)
        self.matchable = self._create_db_matchable('there is some carrot',
                                              intention_topics=['carrot'])

    def create_responses(self, n=4, channel=None):
        from solariat.utils.iterfu import take
        from itertools import cycle

        actionable_content = [
            'i need some carrot',   # need
            'i hate my carrot!',    # problem
            'where can I find some carrot?'  # ask
        ]
        map(lambda content: self._create_db_post(content,
                                                 channel=channel,
                                                 demand_matchables=True,
                                                 user_profile=gen_profile()),
            take(n, cycle(actionable_content)))

    def fetch_responses(self, filter_):
        resp = self.client.post('/responses/json',
                                data=json.dumps(filter_),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'], msg=data)
        self.assertTrue('list' in data)
        return data['list']

    def _get_response_dicts(self, filter_):
        self.login()
        return self.fetch_responses(filter_)

    @unittest.skip('deprecated')
    def test_type_filter(self):
        self._create_db_post('i like carrot', demand_matchables=True, message_type=1)
        self._create_db_post('i hate my carrot!', demand_matchables=True, message_type=1)
        base_filter = {'channel_id': None,
                       'intentions': ['asks','consideration','needs','likes','problem']
                       }
        all_responses = self._get_response_dicts(base_filter)
        
        base_filter['message_type'] = [0]
        public_messages = self._get_response_dicts(base_filter)
        
        base_filter['message_type'] = [1]
        direct_messages = self._get_response_dicts(base_filter)
        
        self.assertTrue(len(all_responses) > len(public_messages), "%s > %s" % (len(all_responses), len(public_messages)))
        self.assertTrue(len(all_responses) > len(direct_messages), "%s > %s" % (len(all_responses), len(direct_messages)))
        self.assertTrue(len(all_responses) == len(public_messages) + len(direct_messages), 
                        "%s == %s" % (len(all_responses), len(public_messages) + len(direct_messages)))
        
    def test_skipped_responses(self):
        self.create_responses()
        base_filter = {'channel_id': str(self.channel.id),
                       'intentions': ['asks','consideration','needs','likes','problem']
                       }
        # Get total responses
        all_responses = self._get_response_dicts(base_filter)
        len_orig_responses = len(all_responses)

        # Get the first response and skip it for the current user
        r0 = all_responses[0]
        response = Response.objects.get(r0['id'])
        self.assertFalse(self.user.id in response.skipped_list)

        self.client.post('/commands/skip_response', data='{"responses": ["%s"]}'%(response.id))
        response = Response.objects.get(r0['id'])        
        self.assertTrue(self.user.id in response.skipped_list)
        
        # Get total responses, again, after skipping one
        all_responses = self._get_response_dicts(base_filter)
        
        self.assertFalse(r0['id'] in [r['id'] for r in all_responses], "Skipped response being returned to user")

        # Change user and assert the post is returned again
        self.user = self._create_db_user(email='somebody@solariat.com', password='12345', roles=[AGENT])

        self.channel.add_perm(self.user)

        all_responses = self._get_response_dicts(base_filter)
        self.assertFalse(len(all_responses) == 0)
        self.assertTrue(r0['id'] in [r['id'] for r in all_responses],
                        "skipped response not being returned for another user")
        
    def test_removed_matchable(self):
        self.create_responses()
        base_filter = {'channel_id': None,
                       'intentions': ['asks','consideration','needs','likes','problem']
                       }
        # Get total responses
        all_responses = self._get_response_dicts(base_filter)
        # Even if we remove the matchable, it should still be matched
        self.matchable.objects.remove_by_user(self.user, self.matchable.id)
        new_responses = self._get_response_dicts(base_filter)
        self.assertEqual(len(all_responses), len(new_responses))
        self.assertEqual(str(all_responses[0]['match']['matchable']['id']), str(self.matchable.id))
        
    def test_channel_filter(self):
        self.create_responses()
        'Make sure sum of individual responses matches all'
        base_filter = {'channel_id': None,
                       'intentions': ['asks','consideration','needs','likes','problem']
                       }
        # Get total responses
        all_responses = self._get_response_dicts(base_filter)

        by_channel = []
        for c in Channel.objects():
            base_filter['channel_id'] = str(c.id)
            by_channel.extend(self._get_response_dicts(base_filter))

        self.assertEqual(len(by_channel), len(all_responses))
        
    def test_delta_responses(self):
        self.create_responses()
        base_filter = {'channel_id': None,
                       'intentions': ['asks','consideration','needs','likes','problem']
                       }
        # For a delta of 1 we should get only 1 response
        base_filter['delta_responses'] = 1 
        delta_high = self._get_response_dicts(base_filter)
        self.assertEqual(1, len(delta_high))
        # For a delta of 2 we should get only 1 response
        base_filter['delta_responses'] = 2 
        delta_high = self._get_response_dicts(base_filter)
        self.assertEqual(2, len(delta_high))

    @unittest.skip('Deprecated')
    def test_post_bookmark(self):
        def _create_bookmark(title, terms, intentions):
            intention_types = [get_sa_type_by_name(name)
                               for name in intentions]
            from solariat_bottle.db.bookmark import Bookmark
            from datetime import datetime, timedelta
            start = datetime.now() - timedelta(days=100)
            end = datetime.now() + timedelta(days=1)
            return Bookmark.objects.create_by_user(
                self.user, title=title,
                channels=[self.channel],
                start=start,
                end=end,
                intention_topics=terms,
                intention_types=intention_types)

        bookmark1 = _create_bookmark(
            'test1',
            ['carrot'],
            ['asks', 'needs', 'consideration'])

        bookmark2 = _create_bookmark(
            'test2',
            terms=['bar'],
            intentions=['asks', 'needs', 'consideration'])

        bookmark3 = _create_bookmark(
            title='test_bookmark2',
            terms=['carrot'],
            intentions=['likes'])

        resps1 = self._get_response_dicts(
            {'bookmark_id': str(bookmark1.id)})
        resps2 = self._get_response_dicts(
            {'bookmark_id': str(bookmark2.id)})
        resps3 = self._get_response_dicts(
            {'bookmark_id': str(bookmark3.id)})

        self.assertEqual(len(resps1), 2)
        self.assertEqual(len(resps2), 0)
        self.assertEqual(len(resps3), 1)

    @unittest.skip("Deprecated because of smart tags")
    def test_skip_filtering(self):
        filter_ = {'channel_id': None,
                   'intentions': ['asks','consideration','needs','likes','problem'],
                   'skip_creative': ['Carrot']}
        # Filter no carrot
        responses = self._get_response_dicts(filter_)
        self.assertEqual(len(responses), 0)
        # Filter no "hate"
        filter_['skip_creative'] = ['hate']
        responses = self._get_response_dicts(filter_)
        self.assertEqual(len(responses), 3)

    @unittest.skip('deprecated')
    def test_intent_filtering(self):
        filter_ = {"intentions": ["asks","consideration","needs","likes","problem"]}
        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 4)

    @unittest.skip('deprecated')
    def test_threshold_filtering(self):
        filter_ = {"intentions": ["asks","consideration","needs","likes","problem"],
                   'thresholds': {"actionability":0,"intention":0,"relevance":0}}
        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 4)
        filter_ = {"intentions": ["asks","consideration","needs","likes","problem"],
                   'thresholds':{
                "actionability":1,"intention":1,"relevance":1}}
        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 0)

    @unittest.skip('deprecated')
    def test_filtering_asks(self):
        filter_ = {"intentions": ["asks"]}
        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 1)
        self.assertEqual(
            response_dicts[0]['post']['stats']['intention']['type'], 'asks')


    @unittest.skip('deprecated')
    def test_filtering_needs(self):
        filter_ = {"intentions": ["needs"]}
        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 1)
        self.assertEqual(
            response_dicts[0]['post']['stats']['intention']['type'], 'needs')

    @unittest.skip('deprecated')
    def test_filtering_likes(self):
        filter_ = {"intentions": ["likes"]}
        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 1)
        self.assertEqual(
            response_dicts[0]['post']['stats']['intention']['type'], 'likes')

    @unittest.skip('deprecated')
    def test_filtering_problem(self):
        filter_ = {"intentions": ["problem"]}
        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 1)
        self.assertEqual(
            response_dicts[0]['post']['stats']['intention']['type'],
            'problem')


    def test_sort_by_and_date_range(self):
        self.create_responses()
        [resp1, resp2, resp3, resp4] = list(Response.objects.find())
        filter_ = {'intentions': ['asks','needs','likes','problem']}
        resp4.post_date = parse_datetime('2010-01-01 00:00:00')
        resp4.relevance = 9
        resp4.intention_confidence = 0.9
        resp4.save()
        resp3.post_date = parse_datetime('2010-01-03 00:00:00')
        resp3.intention_confidence = 0.99
        resp3.relevance = 8
        resp3.save()
        resp2.post_date = parse_datetime('2010-01-04 00:00:00')
        resp2.relevance = 7
        resp2.intention_confidence = 0.8
        resp2.save()
        resp1.relevance = 6
        resp1.post_date  = parse_datetime('2010-01-05 00:00:00')
        resp1.intention_confidence = 0.7
        resp1.save()

        for r in Response.objects.find():
            print r.post.plaintext_content, r.intention_confidence

        self.assertFalse(resp1.to_ui(self.user)['has_history'])
        self.assertFalse(resp1.to_ui(self.user)['has_more_matches'])

        filter_['sort_by'] = 'time'
        resp_dicts = self._get_response_dicts(filter_)
        
        self.assertEqual(resp_dicts[0]['id'], str(resp1.id))

        # filter_['sort_by'] = 'relevance'
        # resp_dicts = self._get_response_dicts(filter_)
        # self.assertEqual(resp_dicts[0]['id'], str(resp4.id))

        return
        '''
        Deprecated....

        filter_['sort_by'] = 'confidence'
        resp_dicts = self._get_response_dicts(filter_)

        # Should not be the lowest confidence one: consideration
        self.assertEqual(resp_dicts[0]['post']['intentions'][0]['content'],
                         resp3.post.content)

        filter_.update({'from':'2010-01-01 00:00:00', 'to': '2010-01-02 00:00:00'})
        resp_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(resp_dicts), 1)
        self.assertEqual(resp_dicts[0]['id'], str(resp4.id))
        '''

    def test_assignment(self):
        self.create_responses()
        filter_ = {"channel_id": str(self.channel.id)}

        assignee = self._create_db_user( email='assignee@solariat.com', password='12345', roles=[AGENT])
        current_user = self.user

        for response in Response.objects():
            response.assignee = assignee.id
            response.save()

        # Should not get any
        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 0)

        # Reset - and should get more
        for response in Response.objects():
            response.assignee = current_user.id
            response.save()

        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 4)

        for response in Response.objects():
            response.assignee = None
            response.save()

        response_dicts = self._get_response_dicts(filter_)
        self.assertEqual(len(response_dicts), 4)

        # Verify that no assignment has taken place for this user
        resp = Response.objects.get(id=response_dicts[0]['id'])
        self.assertEqual(resp.assignee, None)

        # Now set the channel configurations correctly so that it should
        # result in an assignment when we query.
        current_user.outbound_channels[resp.post.platform] = self.channel.id
        current_user.save()
        response_dicts = self._get_response_dicts(filter_)
        resp = Response.objects.get(id=response_dicts[0]['id'])
        self.assertEqual(resp.assignee, current_user.id)

    def assertDictEqual(self, d1, d2, msg=None):
        def sort_dict(d):
            sd = {}
            for key in sorted(d):
                sd[key] = list(sorted(d[key]))
            return sd
        d1 = sort_dict(d1)
        d2 = sort_dict(d2)
        self.assertEqual(set(d1), set(d2), msg=u"Dicts have different keys set\n{}\n{}".format(set(d1), set(d2)))
        for key, value in d1.items():
            self.assertEqual(value, d2[key], msg=u"Values for key {} are not equal\n{}\n{}".format(key, value, d2[key]))

    def setup_channels(self, uname='test_brand'):
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        channel.inbound_channel.add_perm(self.user)
        channel.add_keyword('carrot')
        channel.add_username(uname)
        dispatch_channel = EnterpriseTwitterChannel.objects.create_by_user(
            self.user,
            title='ETC',
            twitter_handle=uname,
            access_token_key='nonempty',
            access_token_secret='nonempty')
        return channel, dispatch_channel

    @unittest.skip("ProcessPool conflicts with gevent")
    def test_assignment_parallel(self):
        import pymongo
        from solariat.utils.timer import TimedMethodProxy

        channel, dispatch_channel = self.setup_channels()
        self._create_db_matchable('Here is the carrot', intention_topics=['carrot'], channels=[channel.inbound_channel, channel])

        def setup(n_responses, n_agents):
            # setup responses
            self.create_responses(n_responses, channel.inbound_channel)
            # setup agents
            for i in range(0, n_agents):
                assignee = self._create_db_user(
                    email='assignee+%d@solariat.com' % i,
                    password='12345',
                    account=self.user.account,
                    roles=[AGENT])
                channel.add_perm(assignee)
                channel.inbound_channel.add_perm(assignee)
                dispatch_channel.add_perm(assignee)

        def fetch(params):
            agent_n, fetch_limit = params
            agent_email = 'assignee+%d@solariat.com' % agent_n
            self.login(agent_email, '12345')
            user = User.objects.get(email=agent_email)
            filter_ = {'channel_id': str(channel.inbound_channel.id),
                       'limit': fetch_limit}
            return user.id, self.fetch_responses(filter_)

        def do_test(n_responses, n_agents, responses_fetch_limit):
            setup(n_responses, n_agents)

            pool = ProcessPool(n_agents)
            results = pool.map(fetch, [(i, responses_fetch_limit) for i in range(0, n_agents)])
            return results

        with TimedMethodProxy(pymongo.database.Database, 'command', threshold=0.001, override=True):
            # 3 agents simultaneously fetch 5 response out of 10
            fetch_limit = 5
            fetch_results = do_test(n_responses=10, n_agents=3,
                                    responses_fetch_limit=fetch_limit)
            # expect: 1. all responses assigned
            # 2. each agent should have not more than fetch_limit responses assigned
            # 3. each agent should have non-intersecting set of responses

            # 1.
            agents = User.objects(email__regex='^assignee+')[:]
            responses = Response.objects(channel=channel.inbound_channel)[:]

            responses_by_agents_db = {}
            for agent in agents:
                responses_by_agents_db[str(agent.id)] = []

            for response in responses:
                if response.assignee is not None:
                    self.assertIn(response.assignee, [a.id for a in agents])
                    responses_by_agents_db[str(response.assignee)].append(response.id)

            responses_by_agents_ui = {}
            for agent in agents:
                responses_by_agents_ui[str(agent.id)] = []

            for (assignee_id, responses) in fetch_results:
                responses_by_agents_ui[str(assignee_id)].extend([
                    r['id'] for r in responses
                ])

            self.assertDictEqual(responses_by_agents_db, responses_by_agents_ui)
            # 2. and 3.
            seen_responses = set()
            for agent_id, response_ids in responses_by_agents_ui.items():
                self.assertTrue(len(response_ids) <= fetch_limit)
                if set(response_ids).intersection(seen_responses):
                    assert False, "Responses assigned to agent %s are already" \
                                  " assigned to another agent" % agent_id
                seen_responses = seen_responses.union(set(response_ids))

    def _get_posts_from_responses(self, filter_):
        data = self._get_response_dicts(filter_)
        return [(r['post']['text'], r['post']['lang']) for r in data]

    def test_filtering_by_lang(self):
        channel = KeywordTrackingChannel.objects.create_by_user(
            self.user, title='ETC')
        self._create_db_matchable('Here is your carrot', channels=[channel], _lang_code='en')
        self._create_db_matchable(u'Aquí está su zanahoria', channels=[channel], _lang_code='es')

        posts = [
            (u'I need some carrot', 'en'),
            (u'Where I can find some carrot?', 'en'),
            (u'Necesito un poco de zanahoria', 'es'),
            (u'¿Dónde puedo encontrar un poco de zanahoria?', 'es'),
            (u'Je ai besoin de la carotte', 'fr')  # No match
        ]

        map(lambda (content, lang): self._create_db_post(
            content, lang=lang, channel=channel), posts)

        language_filters = [
            ["en", "es"],
            ["en"],
            ["es"],
            [],
            None
        ]
        for langs in language_filters:
            filter_ = {
                "channel_id": str(channel.id),
                "languages": langs}
            posts_from_responses = self._get_posts_from_responses(filter_)
            self.assertEqual(
                set(filter(lambda (_, lang): not langs or lang in langs, posts)),
                set(posts_from_responses),
                msg="Lang Filter {} failed\n{}".format(langs, posts_from_responses))

    def test_brands_reply(self):
        """Tests no responses created for outbound posts"""
        # 1. Setup service channel / dispatch channel
        # 2. send a post to brand
        # 3. Reply with custom response
        # 4. Route a reply
        # 5. check there is no extra responses created
        # 6. create a matchable and repeat 1-5
        brand = 'brand'
        channel, dispatch_channel = self.setup_channels(brand)
        user = self._create_db_user(email='su@test.test', password='test', is_superuser=True)
        user.account = self.account
        user.save()
        profiles = set()

        def do_test(matchable):
            profile = gen_profile()
            user_name = profile['user_name']
            profiles.add(user_name)
            post = self._create_db_post(
                '@%s I need some carrot' % brand,
                channel=channel,
                user_profile=profile)

            response = Response.objects.get(id=id_from_post_id(post.id))
            self.assertIsInstance(response.matchable, matchable.__class__)
            assert response.matchable == matchable

            # post custom response
            creative = "U could find some carrot there"
            self.login(user.email, 'test')
            data = dict(creative=creative,
                        response=str(response.id),
                        latest_post=str(response.post.id))
            resp = self.client.post('/commands/custom_response', data=json.dumps(data))
            resp = json.loads(resp.data)

            # check responses and conversations
            self.assertEqual(Response.objects(conversation_id=None).count(), 0)
            self.assertEqual(
                Response.objects(channel__in=[channel, channel.inbound_channel, channel.outbound_channel]).count(),
                0)
            self.assertEqual(Response.objects(conversation_id=response.conversation.id).count(), 1)
            self.assertEqual(Response.objects(channel__in=[dispatch_channel]).count(), len(profiles))

        matchable = EmptyMatchable.get()
        do_test(matchable)

        matchable = self._create_db_matchable('Here is your carrot',
                                              intention_topics=['carrot'],
                                              channels=[channel.inbound_channel])
        do_test(matchable)
