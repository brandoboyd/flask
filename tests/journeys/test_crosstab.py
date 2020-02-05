
import itertools
import json
import os

from solariat.tests.base import LoggerInterceptor

from solariat_bottle.tests.journeys.test_funnel import FunnelTest
from datetime import timedelta, datetime as dt

from solariat_bottle.db.journeys.customer_journey import CustomerJourney
from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType
from solariat_bottle.db.journeys.facet_cache import FacetCache
from solariat_bottle.db.user import User
from solariat_bottle.tests.journeys.base import JourneyByPathGenerationTest


class CrosstabCase(JourneyByPathGenerationTest, FunnelTest):

    def setUp(self):
        JourneyByPathGenerationTest.setUp(self)

    def __set_up_user(self):
        self.user = User.objects.get(email='super_user@solariat.com')
        password = 'password'
        self.username = self.user.email
        self.user.set_password(password)
        self.user.save()
        self.username = self.user.email
        self.password = password

    def __set_up_data(self):
        from solariat_bottle.scripts.data_load.gforce.customers import (
            setup_customer_schema, setup_agent_schema, generate_customers, generate_agents)

        setup_customer_schema(self.user)
        setup_agent_schema(self.user)
        
        paths = [
            # Purchasing
            ('Purchasing', 
                [('twitter', 1, 'Research'), ('twitter', 1, 'Select Product')], 
                ('',)),
            ('Purchasing', 
                [('twitter', 1, 'Research'), ('twitter', 1, 'Select Product'), ('twitter', 1, 'Purchase'), ('nps', 1, 'Purchase', 'detractor')], 
                ('',)),
            # Tech Support
            ('Tech Support', 
                [('twitter', 1, 'Report Issue'), ('twitter', 1, 'Consult'), ('twitter', 1, 'Abandon'), ('nps', 1, 'Abandon', 'passive')], 
                ('',)),
            ('Tech Support', 
                [('twitter', 1, 'Report Issue'), ('twitter', 1, 'Consult'), ('twitter', 1, 'Abandon'), ('nps', 1, 'Abandon', 'passive')], 
                ('',)),
            ('Tech Support', 
                [('twitter', 1, 'Report Issue'), ('twitter', 1, 'Consult'), ('twitter', 1, 'Resolve'), ('nps', 1, 'Resolve', 'promoter')], 
                ('',)),
            # Billing
            ('Billing', 
                [('twitter', 1, 'Submit Request'), ('twitter', 1, 'Consult'), ('twitter', 1, 'Abandon'), ('nps', 1, 'Abandon', 'promoter')], 
                ('',)),
            ('Billing', 
                [('twitter', 1, 'Submit Request'), ('twitter', 1, 'Consult')], 
                ('',)),
            ('Billing', 
                [('twitter', 1, 'Submit Request'), ('twitter', 1, 'Consult')], 
                ('',)),
            ('Billing', 
                [('twitter', 1, 'Submit Request'), ('twitter', 1, 'Consult'), ('twitter', 1, 'Resolve'), ('nps', 1, 'Resolve', 'detractor')], 
                ('',)),
            ('Billing', 
                [('twitter', 1, 'Submit Request'), ('twitter', 1, 'Consult'), ('twitter', 1, 'Resolve'), ('nps', 1, 'Resolve', 'passive')], 
                ('',)),
        ]

        n_customers = len(paths)
        customers = generate_customers(
            self.account.id,
            n_customers=n_customers,
            status='REGULAR')
        CustomerProfile = self.account.get_customer_profile_class()
        self.assertEqual(CustomerProfile.objects.count(), n_customers)
        customer_journey_counts = [(customer, 1) for customer in customers]

        with LoggerInterceptor() as logs:
            self._create_journeys_with_paths(paths, customer_journey_counts, stick_to_paths=True)

        messages = [log.message for log in logs if 'No actor' in log.message]
        self.assertFalse(messages, msg=u'Got "No actor " warnings:\n%s' % '\n'.join(messages))
        self.assertEqual(CustomerProfile.objects.count(), n_customers)

        messages = [log.message for log in logs if 'has non-existing customer id' in log.message]
        self.assertFalse(messages, msg=u'Got errors in event.compute_journey_information\n%s' % '\n'.join(messages))

        self.assertEqual(CustomerJourney.objects.count(), len(paths))
        self.assertEqual(JourneyType.objects().count(), 3)
        self.assertEqual(JourneyStageType.objects().count(), 15)

    import unittest
    @unittest.skipIf(True, "Skipping for now until after release.")
    def test_stats(self):
        self._setup_user_account()
        self._account_configured = True
        self.__set_up_data()

        self.journey_type = JourneyType.objects()[0]

        now = dt.now()
        period = (now - timedelta(days=90), now + timedelta(days=1))
        self.start_date, self.end_date = period

        self.login(self.user.email, self.password)
        date_format = '%Y-%m-%d %H:%M:%S'
        widgets = [
            'journey_volumes_by_journey_type',
            'nps_by_journey_type',
            'status_by_journey_type',
            'nps_by_journey_tag',
            'nps_trends',
        ]
        post_params = {
            "from": self.start_date.strftime(date_format),
            "to": self.end_date.strftime(date_format),
            "widgets": widgets,
            "range_alias": "this_month",
            "journey_type": [str(x.id) for x in JourneyType.objects()],
        }
        resp = self.client.post(
            '/crossfilter/json',
            data=json.dumps(post_params),
            content_type='application/json',
            base_url='https://localhost')
        # import ipdb
        # ipdb.set_trace()
        data = json.loads(resp.data)['data']
        # checking status
        self.assertEqual(resp.status_code, 200)

        # checking journey_volumes_by_journey_type
        labels = data['journey_volumes_by_journey_type']['labels']
        volumes = data['journey_volumes_by_journey_type']['data']
        counts = {}
        # import ipdb; ipdb.set_trace()
        for k in labels:
            counts[labels[k]] = volumes[k]
        # import ipdb; ipdb.set_trace()
        self.assertEqual(
            counts,
            {u'Tech Support': 3, u'Purchasing': 2, u'Billing': 5})

        # checking nps_by_journey_type
        volumes = data["nps_by_journey_type"]["data"]
        counts = {}
        for k in labels:
            counts[labels[k]] = volumes[k]
        self.assertEqual(counts['Tech Support'], {u'passive': 0, u'promoter': 2, u'detractor': 1, 'n/a': 0})
        self.assertEqual(counts['Purchasing'], {u'passive': 0, u'promoter': 0, u'detractor': 1, 'n/a': 1})
        self.assertEqual(counts['Billing'], {u'passive': 0, u'promoter': 1, u'detractor': 2, 'n/a': 2})

        # checking status_by_journey_type
        volumes = data["status_by_journey_type"]["data"]
        counts = {}
        for k in labels:
            counts[labels[k]] = volumes[k]
        self.assertEqual(counts['Tech Support'], {u'finished': 1, u'ongoing': 0, u'abandoned': 2})
        self.assertEqual(counts['Purchasing'], {u'finished': 1, u'ongoing': 1, u'abandoned': 0})
        self.assertEqual(counts['Billing'], {u'finished': 2, u'ongoing': 2, u'abandoned': 1})
    
        # checking nps_trends
        volumes = data["nps_trends"]["data"]
        nps_trends = volumes.copy()
        # checking that timeseries is not empty
        self.assertNotEqual(len(volumes), 0)

        # checking nps_by_journey_tag 
        labels = data["nps_by_journey_tag"]["labels"]
        volumes = data["nps_by_journey_tag"]["data"]
        # checking that timeseries is not empty
        values = [str(x.values()) for x in volumes.values()]
        value_counts = {x: values.count(x) for x in set(values)}
        self.assertTrue(len(value_counts) > 6, value_counts)

        # now lets check that cache was created
        self.assertEqual(FacetCache.objects().count(), 1)
        # now lets check that if we request 
        # the same info with force_recompute 
        # caches created_at field will change
        cache = FacetCache.objects()[0]
        old_created_at = cache.created_at
        post_params['force_recompute'] = True
        resp = self.client.post(
            '/crossfilter/json',
            data=json.dumps(post_params),
            content_type='application/json',
            base_url='https://localhost')
        cache.reload()
        self.assertNotEqual(old_created_at, cache.reload())
        self.assertEqual(FacetCache.objects().count(), 1)

        ##########################
        # testing sankey caching #
        ##########################
        post_params.pop('widgets')
        post_params.pop('force_recompute')
        post_params.pop('range_alias')
        post_params.pop('journey_type')
        post_params.update({
            'group_by': 'nps',
        })
        resp = self.client.post(
            '/journeys/sankey',
            data=json.dumps(post_params),
            content_type='application/json',
            base_url='https://localhost')
        resp_data = json.loads(resp.data)
        # lets check that we getting sankey response
        self.assertEqual(resp_data['ok'], True)
        # lets check that sankey cache exist
        self.assertEqual(FacetCache.objects().count(), 2)
        self.assertEqual(FacetCache.objects(page_type='sankey').count(), 1)

        ########################
        # testing funnel cache #
        ########################
        created_data = json.loads(
            self.create_funnel(
                name='funnel_name', journey_type=self.journey_type).data)
        date_format = '%m/%d/%Y'
        data = {
            'funnel_id': created_data['data']['id'],
            'from': self.start_date.strftime(date_format),
            'to': self.end_date.strftime(date_format),
        }
        resp = self.client.post('/funnel/facets', data=json.dumps(data), content_type='application/json')
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['list'])
        self.assertEqual(FacetCache.objects().count(), 3)
        self.assertEqual(FacetCache.objects(page_type='funnel').count(), 1)

        # checking that date_list param (with time gaps) works
        date_format = '%Y-%m-%d %H:%M:%S'
        subrange_start = now - timedelta(days=30)
        subrange_end = self.end_date
        post_params = {
            "from": self.start_date.strftime(date_format),
            "to": self.end_date.strftime(date_format),
            "widgets": widgets,
            "range_alias": "this_month",
            "journey_type": [str(x.id) for x in JourneyType.objects()],
            "subrange_from": subrange_start.strftime(date_format),
            "subrange_to": subrange_end.strftime(date_format)
        }
        resp = self.client.post(
            '/crossfilter/json',
            data=json.dumps(post_params),
            content_type='application/json',
            base_url='https://localhost')
        data = json.loads(resp.data)['data']
        new_nps_trends = json.loads(resp.data)['data']['nps_trends']['data']
        self.assertEqual(resp.status_code, 200)
        for date_, value_ in new_nps_trends.items():
            self.assertEqual(value_, nps_trends[date_])


