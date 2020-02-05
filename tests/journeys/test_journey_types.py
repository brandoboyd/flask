import unittest
import json
from solariat_bottle.tests.base import UICaseSimple

from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType
from solariat.utils.timeslot import now, utc


class JourneyTypesViewCase(UICaseSimple):
    journey_type_rule = '/journey_types'
    journey_stage_type_rule = '/journey_types/<jt_id>/stages'
    journey_tag_rule = '/journey_tags'

    def setUp(self):
        super(JourneyTypesViewCase, self).setUp()
        self.login()

    def test_journey_type_crud(self):
        post_data = {
            'display_name': 'web search'
        }

        # create
        resp = self.client.post(self.journey_type_rule, data=post_data)
        self.assertEqual(resp.status_code, 201)
        response_data = json.loads(resp.data)
        self.assertTrue(response_data['ok'])
        journey_type = response_data['data']
        self.assertDictContainsSubset(post_data, journey_type)
        self.assertEqual(journey_type['account_id'], str(self.user.account.id))

        journey_type_id = journey_type['id']

        # get all
        resp = self.client.get(self.journey_type_rule)
        self.assertEqual(resp.status_code, 200)
        response_data = json.loads(resp.data)
        self.assertIsInstance(response_data['data'], list)
        self.assertEqual(response_data['data'][0], journey_type)

        # get one
        resp = self.client.get(self.journey_type_rule + '/' + journey_type_id)
        self.assertEqual(resp.status_code, 200)
        response_data = json.loads(resp.data)
        self.assertIsInstance(response_data['data'], dict)
        self.assertEqual(response_data['data'], journey_type)

        # update
        journey_type = JourneyType.objects.get(journey_type_id)
        updated_at = utc(journey_type.updated_at)
        resp = self.client.put(self.journey_type_rule, data=post_data)
        self.assertEqual(resp.status_code, 405)  # can't put to /journeys
        post_data['display_name'] = 'booking'
        resp = self.client.put(self.journey_type_rule + '/' + journey_type_id, data=post_data)
        self.assertEqual(resp.status_code, 200)
        journey_type.reload()
        self.assertTrue(utc(journey_type.updated_at) > updated_at)
        response_data = json.loads(resp.data)
        self.assertTrue(response_data['ok'])
        self.assertDictContainsSubset(post_data, response_data['data'])
        self.assertEqual(response_data['data']['account_id'], str(self.user.account.id))

        # update non-existing journey type
        resp = self.client.put(self.journey_type_rule + '/' + journey_type_id+'not-exists', data=post_data)
        self.assertEqual(resp.status_code, 404)

        # delete
        resp = self.client.delete(self.journey_type_rule, data=post_data)
        self.assertEqual(resp.status_code, 405)
        resp = self.client.delete(self.journey_type_rule + '/' + journey_type_id)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(resp.data)

        # try to get deleted
        resp = self.client.get(self.journey_type_rule + '/' + journey_type_id)
        self.assertEqual(resp.status_code, 404)
        self.assertDictContainsSubset({"error": 'Not found', "ok": False}, json.loads(resp.data))

    def test_journey_type_display_name(self):
        """journey type display name should be unique per account"""
        post_data = {
            'display_name': 'purchasing'
        }
        resp = self.client.post(self.journey_type_rule, data=post_data)
        self.assertEqual(resp.status_code, 201)

        resp = self.client.post(self.journey_type_rule, data=post_data)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.data)['error'], "Journey Type with name '%(display_name)s' already exists" % post_data)

        # verify count
        resp = self.client.get(self.journey_type_rule)
        self.assertEqual(resp.status_code, 200)
        response_data = json.loads(resp.data)
        self.assertEqual(len(response_data['data']), 1)

        # create another JT and try to rename
        resp = self.client.post(self.journey_type_rule, data={'display_name': 'booking'})
        self.assertEqual(resp.status_code, 201)

        jt_id = json.loads(resp.data)['data']['id']
        resp = self.client.put(self.journey_type_rule + '/' + jt_id, data=post_data)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.data)['error'], "Journey Type with name '%(display_name)s' already exists" % post_data)

        # but should be able to save journey type with POST or PUT
        for method in [self.client.post, self.client.put]:
            resp = method(self.journey_type_rule + '/' + jt_id, data={'display_name': 'booking'})
            self.assertTrue(resp.status_code in [200, 201])

    def test_journey_stage_crud(self):
        journey_type = JourneyType.objects.create_by_user(self.user,
                                                          display_name='smooth flow',
                                                          account_id=self.user.account.id)
        url = self.journey_stage_type_rule.replace('<jt_id>', str(journey_type.id))

        # create
        post_data = {"display_name": 'Stage 1'}
        resp = self.client.post(url, data=post_data)
        self.assertEqual(resp.status_code, 201)
        journey_stage_type = json.loads(resp.data)['data']
        journey_stage_type_id = journey_stage_type['id']

        updated_at = utc(journey_type.updated_at)
        journey_type.reload()
        self.assertTrue(utc(journey_type.updated_at) > updated_at)

        self.assertEqual(len(journey_type.available_stages), 1)
        self.assertEqual(str(journey_type.available_stages[0].id), journey_stage_type_id)

        # create duplicate
        post_data = {"display_name": 'Stage 1'}
        resp = self.client.post(url, data=post_data)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.data)['error'], "Stage with name 'Stage 1' already exists")
        journey_type.reload()
        self.assertEqual(len(journey_type.available_stages), 1)
        self.assertEqual(str(journey_type.available_stages[0].id), journey_stage_type_id)

        post_data = {"display_name": 'Stage 2'}
        resp = self.client.post(url, data=post_data)

        # get all
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        stages = json.loads(resp.data)['data']
        self.assertEqual(len(stages), 2)
        self.assertEqual({s['display_name'] for s in stages}, {'Stage 1', 'Stage 2'})

        # get one
        resp = self.client.get(url + '/' + journey_stage_type_id)
        self.assertEqual(resp.status_code, 200)
        self.assertDictContainsSubset({
            'id': journey_stage_type_id,
            'display_name': journey_stage_type['display_name']
        }, json.loads(resp.data)['data'])

        # update
        # try to update first stage with the same display name
        post_data = {
            "display_name": 'Stage 1'
        }
        journey_type.reload()
        updated_at = utc(journey_type.updated_at)
        resp = self.client.put(url + '/' + journey_stage_type_id, data=post_data)
        self.assertEqual(resp.status_code, 200, msg=resp.data)
        journey_type.reload()
        self.assertTrue(utc(journey_type.updated_at) > updated_at)

        post_data = {
            "display_name": 'Stage 2'
        }
        resp = self.client.put(url + '/' + journey_stage_type_id, data=post_data)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.data)['error'], "Stage with name 'Stage 2' already exists")

        post_data['display_name'] = 'Stage 3'
        resp = self.client.put(url + '/' + journey_stage_type_id, data=post_data)
        self.assertEqual(resp.status_code, 200)
        journey_type.reload()
        self.assertEqual({s.display_name for s in journey_type.available_stages}, {'Stage 2', 'Stage 3'})

        # delete
        resp = self.client.delete(url + '/' + journey_stage_type_id)
        self.assertEqual(resp.status_code, 204)
        journey_type.reload()
        self.assertEqual({s.display_name for s in journey_type.available_stages}, {'Stage 2'})
        self.assertNotIn(journey_stage_type_id, {str(s.id) for s in journey_type.available_stages})

    def test_journey_tag(self):
        # create journey_type first
        post_data = {
            'display_name': 'web search'
        }
        resp = self.client.post(self.journey_type_rule, data=post_data)
        response_data = json.loads(resp.data)
        journey_type_dict = response_data['data']

        post_data = {
            'display_name': 'journey1tag',
            'journey_type_id': journey_type_dict['id'],
        }

        # create
        resp = self.client.post(self.journey_tag_rule, data=post_data)
        self.assertEqual(resp.status_code, 201)
        response_data = json.loads(resp.data)
        self.assertTrue(response_data['ok'])
        journey_tag = response_data['data']
        self.assertDictContainsSubset(post_data, journey_tag)
        self.assertEqual(journey_tag['account_id'], str(self.user.account.id))

        journey_tag_id = journey_tag['id']

        # get all
        resp = self.client.get(self.journey_tag_rule)
        self.assertEqual(resp.status_code, 200)
        response_data = json.loads(resp.data)
        self.assertIsInstance(response_data['data'], list)
        self.assertEqual(response_data['data'][0], journey_tag)

        # get one
        resp = self.client.get(self.journey_tag_rule + '/' + journey_tag_id)
        self.assertEqual(resp.status_code, 200)
        response_data = json.loads(resp.data)
        self.assertIsInstance(response_data['data'], dict)
        self.assertEqual(response_data['data'], journey_tag)

        # update
        resp = self.client.put(self.journey_tag_rule, data=post_data)
        self.assertEqual(resp.status_code, 405)  # can't put to /journeys
        post_data['display_name'] = 'booking'
        resp = self.client.put(self.journey_tag_rule + '/' + journey_tag_id, data=post_data)
        self.assertEqual(resp.status_code, 200)
        response_data = json.loads(resp.data)
        self.assertTrue(response_data['ok'])
        self.assertDictContainsSubset(post_data, response_data['data'])
        self.assertEqual(response_data['data']['account_id'], str(self.user.account.id))

        # update non-existing journey tag
        resp = self.client.put(self.journey_tag_rule + '/' + journey_tag_id+'not-exists', data=post_data)
        self.assertEqual(resp.status_code, 404)

        # delete
        resp = self.client.delete(self.journey_tag_rule, data=post_data)
        self.assertEqual(resp.status_code, 405)
        resp = self.client.delete(self.journey_tag_rule + '/' + journey_tag_id)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(resp.data)

        # try to get deleted
        resp = self.client.get(self.journey_tag_rule + '/' + journey_tag_id)
        self.assertEqual(resp.status_code, 404)
        self.assertDictContainsSubset({"error": 'Not found', "ok": False}, json.loads(resp.data))

    def test_journey_tag_display_name(self):
        """journey tag display name should be unique per account"""
        # create journey_type first
        post_data = {
            'display_name': 'web search'
        }
        resp = self.client.post(self.journey_type_rule, data=post_data)
        response_data = json.loads(resp.data)
        journey_type_dict = response_data['data']

        post_data = {
            'display_name': 'journey2tag',
            'journey_type_id': journey_type_dict['id'],
        }

        resp = self.client.post(self.journey_tag_rule, data=post_data)
        self.assertEqual(resp.status_code, 201)

        # validation error in server is crashing
        resp = self.client.post(self.journey_tag_rule, data=post_data)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.data)['error'], "JourneyTag with name '%(display_name)s' already exists" % post_data)

        # verify count
        resp = self.client.get(self.journey_tag_rule)
        self.assertEqual(resp.status_code, 200)
        response_data = json.loads(resp.data)
        self.assertEqual(len(response_data['data']), 1)

        # create another JT and try to rename
        resp = self.client.post(self.journey_tag_rule, data={
            'display_name': 'journey3tag',
            'journey_type_id': journey_type_dict['id'],
        })
        self.assertEqual(resp.status_code, 201)

        jt_id = json.loads(resp.data)['data']['id']
        resp = self.client.put(self.journey_tag_rule + '/' + jt_id, data=post_data)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(json.loads(resp.data)['error'], "JourneyTag with name '%(display_name)s' already exists" % post_data)

        # but should be able to save journey type with POST or PUT
        for i, method in enumerate([self.client.post, self.client.put]):
            post_data['display_name'] = 'journey%dtag' % (i+4)
            resp = method(self.journey_tag_rule + '/' + jt_id, data=post_data)
            self.assertTrue(resp.status_code in [200, 201])

    @unittest.skip('All events must be processed by journey type. '
                   'Event types listed in stage must be used only to '
                   'change customer\'s journey stage.')
    def test_filter_by_event_types(self):
        from solariat_bottle.db.events.event_type import StaticEventType
        tweet = self._create_tweet('hi there')
        profile = tweet.actor
        tw_et = StaticEventType.objects.find_one_by_user(self.user, platform='Twitter')
        fb_et = StaticEventType.objects.find_one_by_user(self.user, platform='Facebook')

        stage = JourneyStageType(
            display_name='Test',
            event_types=[str(fb_et.id)],
            match_expression="int('1')"
        )
        self.assertFalse(stage.evaluate_event(tweet, profile, []))

        stage = JourneyStageType(
            display_name='Test',
            event_types=[str(tw_et.id)],
            match_expression="int('1')"
        )
        self.assertTrue(stage.evaluate_event(tweet, profile, []))

