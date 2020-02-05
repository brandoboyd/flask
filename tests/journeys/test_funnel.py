import json
from nose.tools import eq_, assert_in

from solariat_bottle.tests.base import UICaseSimple
from solariat_bottle.db.funnel import Funnel
from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType
from solariat_bottle.scripts.data_load.generate_journey_data import create_event_types, get_fb_event_type, get_chat_event_type, get_tweet_event_type


class FunnelTest(UICaseSimple):

    def setUp(self):
        super(FunnelTest, self).setUp()
        self.login()
        self._create_journey_type()

    def create_funnel(self, name='journey-conversions', journey_type=None, steps=None):
        if journey_type is None:
            journey_type = self.journey_type

        if steps is None:
            steps = [str(jst.id) for jst in journey_type.available_stages]

        self.create_data = dict(
                name = name,
                description = 'test about %s' % name,
                journey_type = str(journey_type.id),
                steps = steps
        )
        resp = self.client.post('/funnels', data=json.dumps(self.create_data))
        return resp

    def _create_journey_type(self):
        create_event_types(self.user)
        self.journey_type = JourneyType.objects.create(display_name="Test Journey Type",
                                                       account_id=self.account.id)
        stage_names = ['Begin', 'Intermediate 1', 'Intermediate 2', 'End']
        stages = [JourneyStageType.objects.create(display_name=display_name,
                                                  account_id=self.account.id,
                                                  journey_type_id=self.journey_type.id,
                                                  event_types=[get_chat_event_type(),
                                                               get_fb_event_type(),
                                                               get_tweet_event_type()]) for display_name in stage_names]
        for idx, stage in enumerate(stages):
            stage.match_expression = "match_regex(event, 'plaintext_content', 'stage%s') and event.event_type in ['%s', '%s', '%s']" % (
                str(idx), get_tweet_event_type(), get_chat_event_type(), get_fb_event_type())
            stage.save()
        self.journey_type.available_stages = stages
        self.journey_type.save()


class FunnelSettingsTest(FunnelTest):
    def test_create(self):
        resp = self.create_funnel()
        eq_(resp.status_code, 201)
        eq_(Funnel.objects.count(), 1)

        f = Funnel.objects.find_by_user(self.user).next()
        eq_(f.owner, self.user)

        resp_data = json.loads(resp.data)
        eq_(resp_data['ok'], True)
        for each in ['id', 'description', 'journey_type', 'steps', 'owner', 'created']:
            assert_in(each, resp_data['data'])

        eq_(resp_data['data']['journey_type'], self.create_data['journey_type'])
        eq_(resp_data['data']['steps'], self.create_data['steps'])

    def test_read_single(self):
        created_data = json.loads(self.create_funnel().data)
        got_data = json.loads(self.client.get('/funnels/' + created_data['data']['id']).data)

        eq_(created_data['data'], got_data['data'])

    def test_update(self):
        created_data = json.loads(self.create_funnel().data)
        created_data['data']['name'] = 'Updated Journey Conversion'
        put_data = json.loads(self.client.put('/funnels/' + created_data['data']['id'], data=json.dumps(created_data['data'])).data)

        eq_(put_data['data'], created_data['data'])

    def test_delete(self):
        created_data = json.loads(self.create_funnel().data)
        resp = self.client.delete('/funnels/' + created_data['data']['id'])
        eq_(resp.data, '')
        eq_(Funnel.objects.count(), 0)


class FunnelViewTest(FunnelTest):
    def test_no_steps(self):
        created_data = json.loads(self.create_funnel(steps=[]).data)
        data = {
                'funnel_id': created_data['data']['id'],
                'from': "01/01/2014",
                'to': "01/01/2015",
        }
        resp = self.client.post('/funnel/facets', data=json.dumps(data), content_type='application/json')
        eq_(json.loads(resp.data), {u'list': {u'data': []}, u'ok': True})

    def test_no_data_in_any_step(self):
        created_data = json.loads(self.create_funnel().data)
        # TODO: add some test journey data to the steps
        data = {
                'funnel_id': created_data['data']['id'],
                'from': "01/01/2014",
                'to': "01/01/2015",
                'group_by': 'nps'
        }
        resp = self.client.post('/funnel/facets', data=json.dumps(data), content_type='application/json')
        expected_data = {
                'list': {'data': [
                    {
                        'count': {'stuck': 0, 'sum': 0, 'converted': 0, 'abandoned': 0},
                        'nps': {'stuck': 0.0, 'converted': 0.0, 'avg': 0.0, 'abandoned': 0.0}
                    },
                        {'count': {'stuck': 0, 'sum': 0, 'converted': 0, 'abandoned': 0},
                        'nps': {'stuck': 0.0, 'converted': 0.0, 'avg': 0.0, 'abandoned': 0.0}
                    },
                    {
                        'count': {'stuck': 0, 'sum': 0, 'converted': 0, 'abandoned': 0},
                        'nps': {'stuck': 0.0, 'converted': 0.0, 'avg': 0.0, 'abandoned': 0.0}
                    },
                    {
                        'count': {'stuck': 0, 'sum': 0, 'converted': 0, 'abandoned': 0},
                        'nps': {'stuck': 0.0, 'converted': 0.0, 'avg': 0.0, 'abandoned': 0.0}
                    }
                ]},
                'ok': True
        }

        eq_(json.loads(resp.data), expected_data)
