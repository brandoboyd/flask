
import json
import os
import unittest

from pprint import pprint
from time import sleep

from datetime import datetime, timedelta
from solariat_bottle.configurable_apps import CONFIGURABLE_APPS, APP_JOURNEYS
from solariat.tests.base import LoggerInterceptor
from solariat_bottle.tests.base import UICaseSimple

from solariat_bottle.db.account import Account
from solariat_bottle.db.channel.base import SmartTagChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.channel.voc import VOCServiceChannel
from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType
from solariat_bottle.db.journeys.journey_stage import JourneyStage
from solariat_bottle.db.journeys.journey_tag import JourneyTag
from solariat_bottle.db.journeys.customer_journey import CustomerJourney
from solariat_bottle.scripts.data_load.generate_journey_data import \
    initialize_journeys, setup_journey_type_with_stage, generate_dataset, \
    AVG_JOURNEY_TIME_LENGTHS, STATUS_RANDOM_LIMITS
from solariat_bottle.scripts.agents.random_data_generator import SEGMENTS
from solariat_bottle.scripts.data_load.generate_journey_data import create_event_types, get_fb_event_type, get_chat_event_type, get_tweet_event_type
from solariat_bottle.tasks.journeys import process_event_batch
from solariat_bottle.tests.journeys.base import JourneyByPathGenerationTest

from solariat_bottle.scripts.data_load.gforce.customers import setup_customer_schema, setup_agent_schema

skip_long_tests = True


class JourneyCase(UICaseSimple):

    def setUp(self):
        super(JourneyCase, self).setUp()
        from solariat_bottle.db.roles import ADMIN

        self.username = self.user.email
        self.password = os.urandom(16).encode('hex')

        self.account = Account.objects.create(name='Journey Account')
        self.account.add_perm(self.user)
        self.account.available_apps = CONFIGURABLE_APPS
        self.account.selected_app = APP_JOURNEYS
        self.account.save()


        self.user.account = self.account
        self.user.user_roles = [ADMIN]
        self.user.is_superuser = True
        self.user.set_password(self.password)

        setup_customer_schema(self.user)
        setup_agent_schema(self.user)

        self.channel = TwitterServiceChannel.objects.create_by_user(self.user,
                                                                    title="Twitter Channel - Service")
        create_event_types(self.user)
        self.journey_type = JourneyType.objects.create(display_name="Test Journey Type",
                                                       account_id=self.account.id)
        stage_names = ['Begin', 'Intermediate 1', 'Intermediate 2', 'End', 'End Abandoned']
        stages = [JourneyStageType.objects.create(display_name=display_name,
                                                  account_id=self.account.id,
                                                  journey_type_id=self.journey_type.id,
                                                  status=JourneyStageType.IN_PROGRESS,
                                                  event_types=[get_chat_event_type(id=True),
                                                               get_fb_event_type(id=True),
                                                               get_tweet_event_type(id=True)]) for display_name in stage_names]
        stages[-2].status = JourneyStageType.COMPLETED
        stages[-2].save()
        stages[-1].status = JourneyStageType.TERMINATED
        stages[-1].save()

        for idx, stage in enumerate(stages):
            stage.match_expression = "match_regex(event, 'plaintext_content', 'stage%s') and event.event_type in ['%s', '%s', '%s']" % (
                str(idx), get_tweet_event_type(), get_chat_event_type(), get_fb_event_type())
            stage.save()

        self.journey_type.available_stages = stages
        self.journey_type.save()

        CustomerProfile = self.account.get_customer_profile_class()
        from bson.objectid import ObjectId
        self.customer = CustomerProfile.objects.get_or_create(id=str(ObjectId()),
                                                              customer_full_name='Test Last',
                                                              account_id=str(self.account.id))
        actor_num = self.customer.actor_num
        self.login(self.username, self.password)

    def _fetch_journeys(self, from_date, to_date, segments=None, status=None, journey_type=None, url='/journeys/json',
                        **kwargs):
        #'channel_id': kw.get('channel_id') or self.channel_id,
        data = {
            'from'              : from_date.strftime('%Y-%m-%d %H:%M:%S'),
            'to'                : to_date.strftime('%Y-%m-%d %H:%M:%S'),
            'customer_segments' : segments,
            'status'            : status,
            'journey_type'      : journey_type and [journey_type],
            'group_by': kwargs.get('group_by', 'all') or 'all'
        }
        data.update(kwargs)

        resp = self.client.post(url,
                                data=json.dumps(data),
                                content_type='application/json')
        print resp
        print resp.data
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))

        self.assertTrue('list' in resp)

        return resp['list']

    def test_journey_setup(self):
        journey_type = JourneyType.objects.find_one()
        print journey_type.data
        print journey_type.available_stages

        self.assertEqual(CustomerJourney.objects.count(), 0)
        self._create_db_post(content="Post to twitter channel - no stage",
                             actor_id=str(self.customer.id),
                             event_type=get_tweet_event_type(),
                             channel=self.channel.inbound)
        self.assertEqual(CustomerJourney.objects.count(), 0)
        self.assertEqual(journey_type.journeys_num, 0)

        self._create_db_post(content="Post to twitter channel - with stage0",
                             channel=self.channel.inbound,
                             event_type=get_tweet_event_type(),
                             actor_id=str(self.customer.id))
        process_event_batch(self.channel.account.id, 100)
        self.assertEqual(CustomerJourney.objects.count(), 1)
        journey_type.reload()
        self.assertEqual(journey_type.journeys_num, 1)

        journey = CustomerJourney.objects.find_one()
        set_stage = journey.current_stage
        self.assertEqual(set_stage, 'Begin')

        self._create_db_post(content="Post to twitter channel - no stage 1",
                             actor_id=str(self.customer.id),
                             event_type=get_tweet_event_type(),
                             channel=self.channel.inbound)
        process_event_batch(self.channel.account.id, 100)
        self.assertEqual(CustomerJourney.objects.count(), 1)
        journey.reload()
        self.assertEqual(journey.current_stage, set_stage)
        journey_type.reload()
        self.assertEqual(journey_type.journeys_num, 1)

        self._create_db_post(content="Post to twitter channel - with stage1",
                             actor_id=str(self.customer.id),
                             event_type=get_tweet_event_type(),
                             channel=self.channel.inbound)
        process_event_batch(self.channel.account.id, 100)
        self.assertEqual(CustomerJourney.objects.count(), 1)
        journey.reload()
        self.assertNotEqual(journey.current_stage, set_stage)

    def test_journey_timeline(self):
        jt = lambda pair: setup_journey_type_with_stage(pair, self.channel.account)
        journey_type = JourneyType.objects.find_one()
        print journey_type.data
        print journey_type.available_stages

        self.assertEqual(CustomerJourney.objects.count(), 0)
        self._create_db_post(content="Post to twitter channel - no stage",
                             actor_id=str(self.customer.id),
                             event_type=get_tweet_event_type(),
                             channel=self.channel.inbound)
        self.assertEqual(CustomerJourney.objects.count(), 0)

        self._create_db_post(content="Post to twitter channel - with stage0",
                             channel=self.channel.inbound,
                             event_type=get_tweet_event_type(),
                             actor_id=str(self.customer.id))
        process_event_batch(self.channel.account.id, 100)
        self.assertEqual(CustomerJourney.objects.count(), 1)

        journey = CustomerJourney.objects.find_one()
        set_stage = journey.current_stage
        self.assertEqual(set_stage, 'Begin')

        self._create_db_post(content="Post to twitter channel - no stage 1",
                             actor_id=str(self.customer.id),
                             event_type=get_tweet_event_type(),
                             channel=self.channel.inbound)
        process_event_batch(self.channel.account.id, 100)
        self.assertEqual(CustomerJourney.objects.count(), 1)

        timeline = self.client.get('/omni/journeys/%s/json' % str(journey.id),
                                   content_type='application/json')
        timeline = json.loads(timeline.data)

        self.assertTrue('customer' in timeline.get('item', {}))
        self.assertTrue('timeline_data' in timeline.get('item', {}))

    def test_journeys_smart_tags(self):
        jt = lambda pair: setup_journey_type_with_stage(pair, self.channel.account)
        journey_type = JourneyType.objects.find_one()

        self._create_db_post(content="Post to twitter channel - with stage0",
                             channel=self.channel.inbound,
                             event_type=get_tweet_event_type(),
                             actor_id=str(self.customer.id))
        process_event_batch(self.channel.account.id, 100)
        self.assertEqual(CustomerJourney.objects.count(), 1)
        journey = CustomerJourney.objects.find_one()
        self.assertEqual(len(journey.smart_tags), 0)
        tag = SmartTagChannel.objects.create_by_user(self.user,
                                                     title='Some tag',
                                                     parent_channel=self.channel.inbound,
                                                     account=self.user.account)

        data = dict(tag_id=str(tag.id))
        resp = self.client.post('/omni/journeys/%s/smart_tags' % str(journey.id),
                                data=json.dumps(data),
                                content_type='application/json')
        journey.reload()
        self.assertEqual(len(journey.smart_tags), 1)

        resp = self.client.delete('/omni/journeys/%s/smart_tags' % str(journey.id),
                                  data=json.dumps(data),
                                  content_type='application/json')
        journey.reload()
        self.assertEqual(len(journey.smart_tags), 0)

    def test_fill_with_zeroes(self):
        from solariat_bottle.views.facets.journeys import JourneyPlotsView
        input_value = [[1458615600000, 2], [1458637200000, 1], [1458658800000, 1], [1458644400000, 1], [1458648000000, 1], [1458680400000, 4], [1458662400000, 2], [1458673200000, 1], [1458676800000, 2], [1458622800000, 1], [1458666000000, 1], [1458684000000, 4]]
        from_date = datetime.strptime('2016-03-22', '%Y-%m-%d')
        to_date = datetime.strptime('2016-03-23', '%Y-%m-%d')
        plots_view = JourneyPlotsView()

        filled_value = plots_view.fill_with_zeroes(input_value, from_date, to_date)
        self.assertTrue(len(filled_value))

    # @unittest.skipIf(skip_long_tests, 'This takes too long')
    @unittest.skip("TOO LONG")
    def test_generated_data_plots(self):
        self._setup_data_generator()
        self.assertEqual(CustomerJourney.objects.count(), 0)
        n_journeys = 20
        generate_dataset(n_sample=1 * n_journeys, n_agents=20, seed=0, account_id=self.channel.account.id,
                         n_kept_customers=n_journeys)
        n_journeys_created = initialize_journeys(self.user, self.channel.account, n_journeys=n_journeys)
        self.assertEqual(CustomerJourney.objects.count(), n_journeys_created)
        self._test_generated_data(data_generated=True, n_journeys_created=n_journeys_created)

        for journey_type, length in AVG_JOURNEY_TIME_LENGTHS.iteritems():
            to_date = datetime.now()
            from_date = to_date - timedelta(minutes=2 * length)
            journeys = self._fetch_journeys(from_date=from_date, to_date=to_date,
                                            url='/journeys/plots', plot_type='avg_distributions',
                                            computed_metric='nps', group_by='status')#, journey_type=journey_type)
            sorted_scores = sorted(journeys, key=lambda x: x['value'])
            self.assertTrue(set([x['label'] for x in sorted_scores]).issubset(set(["ongoing", "abandoned", "finished"])))
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        journeys = self._fetch_journeys(from_date=from_date, to_date=to_date,
                                        url='/journeys/plots', plot_type='timeline',
                                        level='day', group_by=None)#, journey_type=journey_type)
        self.assertEqual(len(journeys), 1) # avgNPS, avgCSAT and journeyCount
        for data in journeys:
            self.assertTrue('data' in data and 'label' in data)
            self.assertTrue(isinstance(data['data'], list))
            if data['data']:
                for entry in data['data']:
                    self.assertTrue(isinstance(entry, list))
                    self.assertEqual(len(entry), 2)

                for idx, entry in enumerate(data['data'][1:]):
                    self.assertTrue(data['data'][idx][0] < entry[0])

        to_date = datetime.now()
        from_date = to_date - timedelta(days=90)
        cj = CustomerJourney.objects.find_one()

        resp = self.client.get('/facet-filters/journey/%s' % cj.journey_type.display_name,
                               content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)

        filters = {resp['filters'][0]['name']: [resp['filters'][0]['values'][0]]}
        journeys = self._fetch_journeys(from_date=from_date, to_date=to_date,
                                        url='/journeys/sankey', group_by=resp['metrics'][0],
                                        facets=filters)#, journey_type=journey_type)
        self.assertEqual(set(journeys.keys()), set([u'nodes', u'links']))
        self.assertTrue(len(journeys['nodes']) > 0)
        self.assertTrue(len(journeys['links']) > 0)

        journey = CustomerJourney.objects.find_one()
        stage = journey.stage_sequence[0]
        #Try to get the info and timeline for one journey
        resp = self.client.get('/journey/%s/stages' % str(journey.id),
                               content_type='application/json')
        data = json.loads(resp.data)['item']
        self.assertTrue('customer' in data and 'journey' in data)
        for stage in JourneyStage.objects():
            resp = self.client.get('/journey/%s/%s/events' % (str(stage.journey_id), str(stage.id)),
                                   content_type='application/json')
            data = json.loads(resp.data)['item']
            self.assertSetEqual(set(data.keys()), set([u'nextPage', u'events', u'pageSize']))
            self.assertTrue(len(data['events']) >= 1, msg=resp.data)
            self.assertSetEqual(set(data['events'][0].keys()), set([u'content', u'channels', u'platform', u'agents',
                                                                   u'stageId', u'messagesCount']))
            self.assertTrue(len(data['events'][0]['content']) >= 1, msg=resp.data)

    # @unittest.skipIf(skip_long_tests, 'This takes too long')
    def _test_generated_data(self, data_generated=False, n_journeys_created=5):
        if not data_generated:
            self._setup_data_generator()
            n_journeys = 5
            self.assertEqual(CustomerJourney.objects.count(), 0)
            generate_dataset(n_sample=1 * n_journeys, n_agents=20, seed=0, account_id=self.channel.account.id,
                             n_kept_customers=n_journeys)
            n_journeys_created = initialize_journeys(self.user, self.channel.account, n_journeys=n_journeys)
            assert n_journeys_created >= n_journeys, "%s >= %s" % (n_journeys_created, n_journeys)
            self.assertEqual(CustomerJourney.objects.count(), n_journeys_created)

        from solariat_bottle.db.journeys.customer_journey import CustomerJourney

        def checksum(filters, exclusive_filters=True):
            filters_str = u"Filters%s: %s" % (exclusive_filters and " (exclusive)" or '', unicode(filters))
            to_date = datetime.now()
            from_date = to_date - timedelta(days=90)

            fetched_journeys = []
            fetched_journeys_detailed = []
            for kw in filters:
                journeys = self._fetch_journeys(
                    from_date=from_date,
                    to_date=to_date,
                    channels=[str(self.tsc.inbound), str(self.fsc.inbound), str(self.csc.inbound)],
                    **kw)
                for journey in journeys:
                    print journeys.to_json()
                fetched_journeys_detailed.append((kw, [journey['id'] for journey in journeys]))

            self.assertEqual(CustomerJourney.objects.count(), n_journeys_created)
            self.assertEqual(
                len(set(fetched_journeys)),
                n_journeys_created,
                msg=u"Filters did not cover all created journeys\n%s != %s\n%s\n%s" % (
                    len(set(fetched_journeys)),
                    n_journeys_created,
                    filters_str,
                    fetched_journeys_detailed
                ))

            if not exclusive_filters:
                return

            self.assertEqual(
                len(fetched_journeys),
                n_journeys_created,
                msg=u"Fetched journeys don't sum up to created\n%s != %s\n%s\n%s\n%s" % (
                    len(fetched_journeys),
                    n_journeys_created,
                    fetched_journeys,
                    filters_str,
                    fetched_journeys_detailed))

        checksum([{'journey_type': str(JourneyType.objects.get(display_name=journey_type_name).id)}
                  for journey_type_name in AVG_JOURNEY_TIME_LENGTHS])
        checksum([{'status': [status_data[0]]} for status_data in STATUS_RANDOM_LIMITS])
        checksum([{'nps': [nps]} for nps in {'promoter', 'detractor', 'passive', 'n/a'}])
        checksum([{'segments': [segment['display_name']]} for segment in SEGMENTS + [{'display_name': 'N/A'}]], exclusive_filters=False)

    def _setup_data_generator(self):
        # ensure using test client
        from solariat_bottle.scripts.data_load.demo_helpers.api_client import client
        client.options.base_url = ''
        client.options.username = self.username
        client.options.password = self.password

        # setup channels map
        from solariat_bottle.scripts.data_load.generate_journey_data import CHANNELS_MAP
        from solariat_bottle.db.channel.facebook import FacebookServiceChannel
        from solariat_bottle.db.channel.chat import ChatServiceChannel
        from solariat_bottle.scripts.data_load import generate_journey_data

        # shorten journeys
        generate_journey_data.AVG_JOURNEY_EVENT_LENGTHS = {
            event: 12
            for event, length in generate_journey_data.AVG_JOURNEY_EVENT_LENGTHS.items()
        }
        # disable chat loads
        from solariat_bottle.scripts.data_load import generate_journey_data
        generate_journey_data.MAX_CHAT_SESSIONS_PER_STAGE = 0

        user = self.user
        account = user.account
        account.update(account_type='GSE')

        self.tsc = TwitterServiceChannel.objects.create_by_user(
            user,
            title="TSC Journeys - TW")

        self.fsc = FacebookServiceChannel.objects.create_by_user(
            user,
            title="TSC Journeys - FB")

        self.csc = ChatServiceChannel.objects.create_by_user(
            user,
            title="TSC Journeys - CHAT")

        voc_channel = VOCServiceChannel.objects.create_by_user(user,
                                                               title='NPS Channel')

        CHANNELS_MAP['Twitter'] = dict(channel=self.tsc,
                                       tags=[str(SmartTagChannel.objects.create_by_user(user,
                                                                                        title=name,
                                                                                        parent_channel=self.tsc.inbound,
                                                                                        account=user.account).id)
                                             for name in ('TW-TAG1', 'TW-TAG2', 'TW-TAG3')])
        CHANNELS_MAP['Facebook'] = dict(channel=self.fsc,
                                        tags=[str(SmartTagChannel.objects.create_by_user(user,
                                                                                         title=name,
                                                                                         parent_channel=self.tsc.inbound,
                                                                                         account=user.account).id)
                                              for name in ('FB-TAG1', 'FB-TAG2', 'FB-TAG3')])
        CHANNELS_MAP['Chat'] = dict(channel=self.csc,
                                    tags=[str(SmartTagChannel.objects.create_by_user(user,
                                                                                     title=name,
                                                                                     parent_channel=self.tsc.inbound,
                                                                                     account=user.account).id)
                                          for name in ('CHAT-TAG1', 'CHAT-TAG2', 'CHAT-TAG3')])
        CHANNELS_MAP['VOC'] = dict(channel=voc_channel,
                                   tags=[str(SmartTagChannel.objects.create_by_user(user,
                                                                                    title=name,
                                                                                    parent_channel=voc_channel.inbound,
                                                                                    account=user.account).id)])

    @unittest.skipIf(True, "No longer valid. Need proper journey tag implementation.")
    def test_smart_tag_rule(self):
        stage_sequences = [JourneyStageType.objects.get(
            journey_type_id=self.journey_type.id,
            display_name=stage.display_name
        ).id for stage in self.journey_type.available_stages]

        smt = SmartTagChannel.objects.create_by_user(
            self.user,
            status='Active',
            title='%s (%s)' % ('SmartTagTest', self.channel.platform),
            parent_channel=self.channel.inbound,
            keywords=['#assign_me1'],
            skip_keywords=[],
            account=self.account
        )
        smt2 = SmartTagChannel.objects.create_by_user(
            self.user,
            status='Active',
            title='%s (%s)' % ('SmartTagTest2', self.channel.platform),
            parent_channel=self.channel.inbound,
            keywords=['#assign_me2'],
            skip_keywords=[],
            account=self.account
        )

        tags_data = [
            ('TestJourneyTag1', [smt.id], [smt2.id]),  # with a skipped smart tag
            ('TestJourneyTag2', [smt.id], []),         # with no skipped smart tags
            ('NotAssignedTag', [], []),                # this should never be assigned
        ]
        journey_tags_map = {}
        for journey_tag_name, key_smart_tags, skip_smart_tags in tags_data:
            journey_tags_map[journey_tag_name] = \
            JourneyTag.objects.create(
                journey_type_id=self.journey_type.id,
                display_name=journey_tag_name,
                tracked_stage_sequences=stage_sequences,
                account_id=self.account.id,
                key_smart_tags=key_smart_tags,
                skip_smart_tags=skip_smart_tags
            )

        post1 = self._create_db_post(
            content="Post to twitter channel - with stage0 #assign_me1",
            actor_id=str(self.customer.id),
            event_type=get_tweet_event_type(),
            channel=self.channel.inbound,
        )
        process_event_batch(self.channel.account.id, 100)

        journey = CustomerJourney.objects.find_one(customer_id=self.customer.id)
        self.assertEqual(set(journey.journey_tags), {
            journey_tags_map['TestJourneyTag1'].id,
            journey_tags_map['TestJourneyTag2'].id
        })

        # now add skipping smart tag
        post1.handle_accept(self.user, [smt2])
        # journey.process_event(post1)
        # journey.update(addToSet__smart_tags=smt2.id)  # emulate journey.process_event()
        post1.apply_smart_tags_to_journeys()

        # post should be assigned with smart tag #assign_me2,
        # which is a skipping smart tag for the TestJourneyTag1 journey tag,
        # therefore TestJourneyTag1 should be removed from journey tags list
        journey.reload()
        self.assertEqual(journey.journey_tags, [journey_tags_map['TestJourneyTag2'].id])

        # post2 is assigned with a skipping smart tag,
        # so journey tags should remain the same
        post2 = self._create_db_post(
            content="Post to twitter channel - with stage1 #assign_me2",
            actor_id=str(self.customer.id),
            event_type=get_chat_event_type(),
            channel=self.channel.inbound,
        )
        process_event_batch(self.channel.account.id, 100)
        journey.reload()
        self.assertEqual(journey.journey_tags, [journey_tags_map['TestJourneyTag2'].id])

        # now remove skipping tag from posts and re-evaluate journey tags
        post1.handle_reject(self.user, [smt2])
        post2.handle_reject(self.user, [smt2])
        post1.reload()
        post2.reload()
        post1.apply_smart_tags_to_journeys()
        post2.apply_smart_tags_to_journeys()

        journey.reload()
        self.assertEqual(journey.journey_tags, [journey_tags_map['TestJourneyTag2'].id])

        # now since we rejected skipping tag from both of previous posts,
        # another post assigned with first smart tag should add TestJourneyTag1 back
        post3 = self._create_db_post(
            content="Post to twitter channel - with stage2 #assign_me1",
            actor_id=str(self.customer.id),
            event_type=get_chat_event_type(),
            channel=self.channel.inbound,
        )
        process_event_batch(self.channel.account.id, 100)
        journey.reload()
        self.assertEqual(set(journey.journey_tags), {
            journey_tags_map['TestJourneyTag1'].id,
            journey_tags_map['TestJourneyTag2'].id
        })

    def test_expression_context(self):
        expected1 = {
            'context': ['agents', 'current_event', 'current_stage', 'customer_profile', 'event_sequence',
                        'previous_stage',
                        'stage_sequence'],
            'functions': ['int(<value>)', 'pow(<value>, <value>)', 'log(<value>)', 'str(<value>)',
                          'aggregate(<input_sequence>, <field_name>, <aggregate_function>)'],
            'stage_statuses': ['ongoing', 'finished', 'abandoned', 'closed'],
            'stages': ['Begin', 'Intermediate 1', 'Intermediate 2', 'End', 'End Abandoned']}
        expected2 = {
            'context': ['agents', 'current_event', 'current_stage', 'customer_profile', 'event_sequence',
                        'previous_stage',
                        'stage_sequence'],
            'event_types': [u'Chat -> Chat message',
                            u'Twitter -> Tweet',
                            u'Facebook -> Post'],
            'functions': ['int(<value>)', 'pow(<value>, <value>)', 'log(<value>)', 'str(<value>)',
                          'aggregate(<input_sequence>, <field_name>, <aggregate_function>)',]}


        # test suggestions for UI
        result1 = self.journey_type.get_expression_context()
        self.assertTrue("context" in result1)
        self.assertTrue(result1["context"])
        self.assertTrue("functions" in result1)
        self.assertTrue(result1["functions"])
        self.assertEqual(result1['context'], CustomerJourney.get_properties())
        self.assertEqual(result1['functions'], expected1['functions'], "GOT: %s and EXPECTED: %s" % (result1['functions'],
                                                                                                     expected1['functions']))
        self.assertEqual(result1['stage_statuses'], expected1['stage_statuses'])
        self.assertEqual(result1['stages'], expected1['stages'])

        # test suggestions for UI
        stage = self.journey_type.available_stages[0]
        result2 = stage.get_expression_context()
        self.assertTrue("context" in result2)
        self.assertTrue(result2["context"])
        self.assertTrue("functions" in result2)
        self.assertTrue(result2["functions"])
        self.assertEqual(result2['context'], ['event_sequence', 'event', 'customer_profile', 'current_event', 'status',
                                              'event_types', 'journey_index',
                                              'CONSTANT_ONE_HOUR', 'CONSTANT_ONE_DAYS',
                                              'CONSTANT_DATE_NOW', 'status_text'])
        self.assertEqual(result2['functions'], expected2['functions'])
        self.assertEqual(set(result2['event_types']), set(expected2['event_types']))
        # test suggestions for UI
        self.assertTrue("expression_context" in self.journey_type.to_dict())
        self.assertTrue("expression_context" in stage.to_dict())


    @unittest.skip("tempopary skipping because this test is fixed on a branch we going to merge in soon")
    def test_path_analysis(self):

        # for strategy in [PLATFORM_STRATEGY, EVENT_STRATEGY]:
        #     LabelingStrategy.objects.create(account_id=self.account.id, display_name=strategy)

        # setting up data for testing
        self._setup_data_generator()
        self.assertEqual(CustomerJourney.objects.count(), 0)
        n_journeys = 3
        generate_dataset(n_sample=1 * n_journeys, n_agents=1, seed=0, account_id=self.channel.account.id, n_kept_customers=n_journeys)
        n_journeys_created = initialize_journeys(
            self.user, self.channel.account, n_journeys=n_journeys,
            only_one_journey_type_for_testing=True)
        self.assertEqual(CustomerJourney.objects.count(), n_journeys_created)

        cj = CustomerJourney.objects()[0]
        journey_type_for_request = cj.journey_type
        length = 30
        to_date = datetime.now()
        from_date = to_date - timedelta(days=length)
        jt_id = self.journey_type.id
        result = self._fetch_path_analysis(
            from_date=from_date, to_date=to_date,
            journey_type=[str(journey_type_for_request.id)],
            url='/journeys/mcp')
        # print 1111, cj.journey_type.display_name, cj.journey_type.id
        # import ipdb; ipdb.set_trace()


        # test properties aviability now
        # and actual values being correct
        post1 = self._create_db_post(
            content="Post to twitter channel - with stage0 #assign_me1",
            actor_id=str(self.customer.id),
            event_type=get_tweet_event_type(),
            channel=self.channel.inbound)
        post2 = self._create_db_post(
            content="Post to twitter channel - with stage1 #assign_me2",
            actor_id=str(self.customer.id),
            event_type=get_chat_event_type(),
            channel=self.channel.inbound)

        journey = CustomerJourney.objects.find_one(customer_id=self.customer.id)
        journey_stage = JourneyStage.objects.get(id=journey.stage_sequence[0])

        self.assertEqual(journey.current_event, "Chat message")
        self.assertEqual(journey.current_stage, "Intermediate 1")
        self.assertEqual(journey.previous_stage, "Begin")
        self.assertEqual(journey.stage_sequence, [u'Begin', u'Intermediate 1'])
        self.assertEqual(journey.event_sequence, ["Tweet", "Chat message"])

    def _fetch_path_analysis(self, url, from_date, to_date, limit=1, *args, **kwargs):
        url = '/journeys/mcp'
        data = {
            'from'              : from_date.strftime('%Y-%m-%d %H:%M:%S'),
            'to'                : to_date.strftime('%Y-%m-%d %H:%M:%S'),
            'limit'             : limit,
            # 'customer_segments' : segments,
            # 'status'            : status,
            # 'journey_type'      : journey_type and [journey_type],
            # 'group_by': kwargs.get('group_by', 'all') or 'all'
        }
        data.update(kwargs)
        resp = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)

        # import ipdb; ipdb.set_trace()
        self.assertTrue(resp['ok'], resp.get('error'))
        return resp

    def __setup_data_for_mcp_basic(self):
        journey_attributes_schema = [
                {'name': 'cost', 'label': 'cost', 'type': 'integer', 'field_expr': "4"},
                {'name': 'revenue', 'label': 'revenue', 'type': 'integer', 'field_expr': "3"},
                {'name': 'roi', 'label': 'roi', 'type': 'integer', 'field_expr': "1 + 1"},
                {'name': 'duration', 'label': 'duration', 'type': 'integer',
                    'field_expr': "days + 1"},
                {'label': 'Abandonment Rate',
                    'name': 'abandonment_rate',
                    'type': 'integer',
                    'field_expr': "is_abandoned * 100"}
        ]
        journey_type = JourneyType.objects()[0]
        journey_type.journey_attributes_schema = journey_attributes_schema
        journey_type.save()

        # setting up labels
        # for strategy in [PLATFORM_STRATEGY, EVENT_STRATEGY]:
        #     LabelingStrategy.objects.create(account_id=self.account.id, display_name=strategy)
        return journey_type

    def test_path_analysis(self):

        journey_type = self.__setup_data_for_mcp_basic()
        self.__make_journeys(n_journeys=4)

        # preparing request params
        to_date = datetime.now() + timedelta(days=1) # temporary will deal with it later
        from_date = to_date - timedelta(days=90)
        journey_type_for_request = CustomerJourney.objects()[0].journey_type

        # querying backend endpoint
        result1 = self._fetch_path_analysis(
            from_date=from_date, to_date=to_date,
            path={"label": "Most Common Path", "measure": "max"},
            journey_type=[str(journey_type_for_request.id)],
            url='/journeys/mcp')

        result2 = self._fetch_path_analysis(
            from_date=from_date, to_date=to_date,
            path={"label": "revenue", "measure": "max"},
            journey_type=[str(journey_type_for_request.id)],
            url='/journeys/mcp')

        self.assertTrue(result1['paths']['data'])
        self.assertTrue(result2['paths']['data'])


    def __make_journeys(self, n_journeys, is_abandoned=False, node1_count=3, node2_count=2):
        CustomerProfile = self.account.get_customer_profile_class()
        for i in range(n_journeys):
            customer =  CustomerProfile.objects.get_or_create(customer_full_name='Test Last %s %s' % (i, is_abandoned),
                                                              account_id=self.account.id)
            self._create_db_post(content="Post to twitter channel - no stage",
                                 actor_id=str(customer.id),
                                 event_type=get_tweet_event_type(),
                                 channel=self.channel.inbound)
            sleep(1)
            self._create_db_post(content="Post to twitter channel - with stage0",
                                 channel=self.channel.inbound,
                                 event_type=get_tweet_event_type(),
                                 actor_id=str(customer.id))
            sleep(1)
            # three event of same type below
            for i in range(node1_count):
                self._create_db_post(content="Post to twitter channel - with stage1",
                                     channel=self.channel.inbound,
                                     event_type=get_tweet_event_type(),
                                     actor_id=str(customer.id))
                sleep(1)
            # two event of same type below
            for i in range(node2_count):
                self._create_db_post(content="Post to twitter channel - with stage2",
                                channel=self.channel.inbound,
                                event_type=get_tweet_event_type(),
                                actor_id=str(customer.id))
                sleep(1)

            if is_abandoned:
                content = "Post to twitter channel - with stage4"
            else:
                content = "Post to twitter channel - with stage3"
            self._create_db_post(content=content,
                                 channel=self.channel.inbound,
                                 event_type=get_tweet_event_type(),
                                 actor_id=str(customer.id))
            sleep(1)
        process_event_batch(self.channel.account.id, 1000)

    def test_path_analysis_complex(self):

        journey_type = self.__setup_data_for_mcp_basic()
        n_journeys = 10
        n_journeys_abandoned = 4
        node1_count = 3
        node2_count = 2
        self.__make_journeys(n_journeys=n_journeys, is_abandoned=False, node1_count=node1_count, node2_count=node2_count)
        self.__make_journeys(n_journeys=4, is_abandoned=True, node1_count=node1_count, node2_count=node2_count)

        # inserting rtificial values for attribute
        revenue_vals = [6, 6, 5, 5, 4, 4, 3, 3, 2, 2]
        for i, cj in enumerate(CustomerJourney.objects(status=JourneyStageType.COMPLETED)):
            cj.journey_attributes['revenue'] = revenue_vals[i]
            cj.save()
        for i, cj in enumerate(CustomerJourney.objects(status=JourneyStageType.TERMINATED)):
            cj.journey_attributes['revenue'] = revenue_vals[i]
            cj.save()

        # preparing request params
        to_date = datetime.now() + timedelta(days=1) # temporary will deal with it later
        from_date = to_date - timedelta(days=90)
        journey_type_for_request = CustomerJourney.objects()[0].journey_type

        sleep(2)

        # querying backend endpoint
        mcp_result = self._fetch_path_analysis(
            from_date=from_date, to_date=to_date,
            path={"label": "Most Common Path", "measure": "max"},
            journey_type=[str(journey_type_for_request.id)],
            url='/journeys/mcp')['paths']

        revenue_result = self._fetch_path_analysis(
            from_date=from_date, to_date=to_date,
            path={"label": "revenue", "measure": "max"},
            journey_type=[str(journey_type_for_request.id)],
            url='/journeys/mcp')['paths']

        self.assertTrue(mcp_result['data'])
        mcp_result = mcp_result['data'][0]
        self.assertEqual(mcp_result['measure'], 'max')
        self.assertEqual(mcp_result['metrics']['abandonment_rate']['value'], 0.0)
        self.assertEqual(
            mcp_result['metrics']['percentage']['value'],
            "%.1f" % (float(n_journeys)/(n_journeys+n_journeys_abandoned) * 100)
        )
        self.assertEqual(mcp_result['no_of_abandoned_journeys'], 0)
        self.assertEqual(mcp_result['no_of_journeys'], n_journeys)
        self.assertEqual(mcp_result['stages'][1]['nodes'][0]['count'], 3)

        self.assertTrue(revenue_result['data'])
        revenue_result = revenue_result['data'][0]
        self.assertEqual(revenue_result['measure'], 'max')
        self.assertEqual(
            revenue_result['metrics']['percentage']['value'],
            "%.1f" % (float(n_journeys_abandoned)/(n_journeys+n_journeys_abandoned) * 100)
        )
        self.assertEqual(revenue_result['metrics']['abandonment_rate']['value'], 100.0)
        # self.assertEqual(revenue_result['metrics']['percentage']['value'], '71.4')
        self.assertEqual(revenue_result['stages'][1]['nodes'][0]['count'], 3)
        self.assertEqual(revenue_result['stages'][2]['nodes'][0]['count'], 2)
        self.assertEqual(revenue_result['no_of_abandoned_journeys'], n_journeys_abandoned)
        self.assertEqual(revenue_result['no_of_journeys'], n_journeys_abandoned)

        pprint(revenue_result)

    def test_path_analysis_with_limit(self):

        journey_type = self.__setup_data_for_mcp_basic()
        n_journeys = 1
        n_journeys_abandoned = 1
        node1_count = 1
        node2_count = 1
        self.__make_journeys(n_journeys=n_journeys, is_abandoned=False, node1_count=node1_count, node2_count=node2_count)
        self.__make_journeys(n_journeys=4, is_abandoned=True, node1_count=node1_count, node2_count=node2_count)

        # inserting rtificial values for attribute
        revenue_vals = [6, 5, 4, 3, 2]
        for i, cj in enumerate(CustomerJourney.objects(status=JourneyStageType.COMPLETED)):
            cj.journey_attributes['revenue'] = revenue_vals[i]
            cj.save()
        for i, cj in enumerate(CustomerJourney.objects(status=JourneyStageType.TERMINATED)):
            cj.journey_attributes['revenue'] = revenue_vals[i]
            cj.save()

        # preparing request params
        to_date = datetime.now() + timedelta(days=1) # temporary will deal with it later
        from_date = to_date - timedelta(days=90)
        journey_type_for_request = CustomerJourney.objects()[0].journey_type

        sleep(2)

        # querying backend endpoint
        mcp_result = self._fetch_path_analysis(
            from_date=from_date, to_date=to_date,
            path={"label": "Most Common Path", "measure": "max"},
            journey_type=[str(journey_type_for_request.id)],
            limit=2,
            url='/journeys/mcp')['paths']

        revenue_result = self._fetch_path_analysis(
            from_date=from_date, to_date=to_date,
            path={"label": "revenue", "measure": "max"},
            journey_type=[str(journey_type_for_request.id)],
            limit=2,
            url='/journeys/mcp')['paths']

        self.assertTrue(mcp_result['data'])
        self.assertEqual(len(mcp_result['data']), 2)

        self.assertTrue(revenue_result['data'])
        self.assertEqual(len(revenue_result['data']), 2)

    def test_journey_insights_analysis(self):
        from solariat.utils.timeslot import datetime_to_timestamp

        print 'Making 10 journeys for Insights Analysis...\n'
        journey_type = self.__setup_data_for_mcp_basic()
        self.__make_journeys(n_journeys=10)

        revenue_vals = xrange(11)
        for i, cj in enumerate(CustomerJourney.objects(journey_type_id=journey_type.id)):
            cj.journey_attributes['revenue'] = revenue_vals[i]
            cj.save()

        revenue_metric = [attr for attr in journey_type.journey_attributes_schema if attr['name'] == 'revenue'][0]

        _request_data = {'filters': {'journey_type': [str(journey_type.id)]},
                         'analyzed_metric': revenue_metric['name'],
                         'metric_type': 'Numeric',
                         'application': 'Journey Analytics',
                         'title': 'TEST_JOURNEY_ANALYSIS'
                         }

        current = datetime.now()
        three_montsh_ago = current - timedelta(days=90)
        to_date = current + timedelta(days=10)
        _request_data['filters']['from'] = three_montsh_ago.strftime('%Y-%m-%d %H:%M:%S')
        _request_data['filters']['to'] = to_date.strftime('%Y-%m-%d %H:%M:%S')
        _request_data['filters']['timerange'] = [datetime_to_timestamp(three_montsh_ago),
                                                 datetime_to_timestamp(to_date)]

        # REGRESSION
        regr_analysis_data = _request_data.copy()
        regr_analysis_data.update({"metric_values": [0, 10],
                                   "metric_values_range": [0, 10],
                                   "analysis_type": "regression"})
        response_regression = self.client.post('/analyzers',
                                               data=json.dumps(regr_analysis_data),
                                               content_type='application/json')
        response_regression = json.loads(response_regression.data)
        self.assertTrue(response_regression['ok'])
        from time import sleep
        sleep(2)
        analyzers_list = json.loads(self.client.get('/analyzers', content_type='application/json').data)
        response_regression = analyzers_list['list'][0]
        self.assertTrue('timerange_results' in response_regression)
        self.assertTrue('results' in response_regression)
        self.assertTrue(response_regression['results'])
        self.assertTrue(response_regression['timerange_results'])

        # CLASSIFICATION
        classification_analysis_data = _request_data.copy()
        classification_analysis_data.update({"metric_values": [3, 6],
                                             "analysis_type": "classification",
                                             "metric_values_range": [0, 10]})
        response_classification = self.client.post('/analyzers',
                                                   data=json.dumps(classification_analysis_data),
                                                   content_type='application/json')
        response_classification = json.loads(response_classification.data)
        self.assertTrue(response_classification['ok'])
        sleep(2)
        analyzers_list = json.loads(self.client.get('/analyzers', content_type='application/json').data)
        response_regression = analyzers_list['list'][1]
        self.assertTrue('timerange_results' in response_regression)
        self.assertTrue('results' in response_regression)
        self.assertTrue(response_regression['results'])
        self.assertTrue(response_regression['timerange_results'])

        res = self.client.get('/analyzers')
        data = json.loads(res.data)
        self.assertEqual(len(data), 2)  # 2 Insight Analysis should be created


class ChatPostsErrorsCase(JourneyByPathGenerationTest):

    @unittest.skip('This is really quite broken. The journey data creation code is so convoluted it is hard to figure ths out. But we need to.')
    def test_chat_path(self):
        from solariat_bottle.scripts.data_load.gforce.customers import generate_customers, generate_agents
        n_customers = 5
        self._setup_user_account()


        self.user.account = self.account
        setup_customer_schema(self.user)
        setup_agent_schema(self.user)

        customers = generate_customers(self.account.id, n_customers=n_customers)
        CustomerProfile = self.account.get_customer_profile_class()
        self.assertEqual(CustomerProfile.objects.count(), n_customers)


        agents = generate_agents(self.account.id)
        AgentProfile = self.account.get_agent_profile_class()
        self.assertEqual(AgentProfile.objects.count(), len(agents))

        paths = [
            ('Purchasing', [('chat', 1, 'Research'), ('voice', 1, 'Purchase'), ('nps', 1, 'Purchase', 'promoter')], ('good_agent', 'cs:%s' % customers[0].status)),
            ('Tech Support', [('chat', 1, 'Report Issue'), ('voice', 1, 'Resolve'), ('nps', 1, 'Resolve', 'promoter')], ('good_agent', 'cs:%s' % customers[0].status)),
            ('Billing', [('chat', 1, 'Submit Request'), ('voice', 1, 'Resolve'), ('nps', 1, 'Resolve', 'promoter')], ('good_agent', 'cs:%s' % customers[0].status))
        ]
        customer_journey_counts = [(customers[0], len(paths))]

        with LoggerInterceptor() as logs:
            self._create_journeys_with_paths(paths, customer_journey_counts)

        messages = [log.message for log in logs if 'has non-existing customer id' in log.message]
        self.assertFalse(messages, msg=u'Got errors in event.compute_journey_information\n%s' % '\n'.join(messages))
        self.assertEqual(CustomerJourney.objects.count(), len(paths))


