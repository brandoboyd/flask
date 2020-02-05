import random
import unittest
from nose.tools import eq_

from solariat_bottle.tests.journeys.customers_agents.base import CustomerAgentBaseCase
from solariat_bottle.tests.base import setup_customer_schema, get_schema_config
from solariat_bottle.scripts.data_load.gforce.customers import (
        LOCATION_VALUES, INTENT_LABELS, PRODUCTS,
        CUSTOMER_SENIORITY_VALUES, INDUSTRIES, STATUS, CUSTOMER_SEGMENTS,
        customer_first_name_male, customer_first_name_female, customer_last_name
)


class CustomersBaseTest(CustomerAgentBaseCase):
    def setUp(self):
        super(CustomersBaseTest, self).setUp()
        setup_customer_schema(self.user, get_schema_config(self.generate_customer_data()))

    def generate_customer_data(self):
        sex = random.choice(('M', 'F'))
        first_name = random.choice({
                'M': customer_first_name_male,
                'F': customer_first_name_female
        }[sex])
        last_name = random.choice(customer_last_name)

        data = dict(
            first_name=first_name,
            last_name=last_name,
            age=random.randint(16, 100),
            account_id=self.account.id,
            location=random.choice(LOCATION_VALUES),
            assigned_segments=[],
            assigned_labels=[],
            sex=sex,
            status=random.choice(STATUS),
            industry=random.choice(INDUSTRIES),
            products=self.choose_many(PRODUCTS),
            last_call_intent=[random.choice(INTENT_LABELS)],
            num_calls=random.randint(0, 100),
            seniority=random.choice(CUSTOMER_SENIORITY_VALUES),
            phone='01' + ''.join(random.sample('1234567890', 10))
        )
        return data

    def _create(self, **kw):
        data = self.generate_customer_data()
        data.update(kw)
        CustomerProfile = self.account.get_customer_profile_class()
        return CustomerProfile.objects.create(**data)

    def _fetch(self, **kw):
        data = {
                'from': "01/01/2016",
                'to': "12/31/2030",
                'age_groups': [],
                'agent_id': "",
                'call_intents': [],
                'customer_statuses': [],
                'genders': None,
                'industries': [],
                'locations': None,
                'segments': [],
                'limit': 50,
                'offset': 0,
        }
        data.update(kw)
        return self._post('/customer-profiles/json', data_dict=data)


class CustomersDetailsTest(CustomersBaseTest):

    def test_industries(self):
        groups = INDUSTRIES
        groups_counts = {g: random.randint(1, 10) for g in groups}
        for g, count in groups_counts.items():
            [self._create(industry=g) for i in xrange(count)]

        for facet_groups in self.combinations(groups):
            resp = self._fetch(industries=facet_groups)
            for g, samples in self.groupby(resp, 'industry'):
                eq_(groups_counts[g], len(list(samples)))

    def test_age_groups(self):
        groups = {
                '16 - 25': (16, 25),
                '26 - 35': (26, 35),
                '36 - 45': (36, 45),
                '46 -'   : (46, 100),
        }
        groups_counts = {g: random.randint(1, 10) for g in groups.values()}
        for g, count in groups_counts.items():
            [self._create(age=random.randint(*g)) for i in xrange(count)]

        for facet_groups in self.combinations(groups):
            resp = self._fetch(age_groups=facet_groups)
            self.categorize_age_groups(resp)
            for g, samples in self.groupby(resp, 'age'):
                eq_(groups_counts[g], len(list(samples)))

    def test_customer_status(self):
        groups = STATUS
        groups_counts = {g: random.randint(1, 10) for g in groups}
        for g, count in groups_counts.items():
            [self._create(status=g) for i in xrange(count)]

        for facet_groups in self.combinations(groups):
            resp = self._fetch(customer_statuses=facet_groups)
            for g, samples in self.groupby(resp, 'status'):
                eq_(groups_counts[g], len(list(samples)))

    # def test_segments(self):
    #     segment_objs = [CustomerSegment.objects.create(account_id=self.account.id,
    #                                                    **segment) for segment in CUSTOMER_SEGMENTS]
    #     groups = {o.display_name: o.id for o in segment_objs}
    #     groups_counts = {g: random.randint(1, 10) for g in groups.values()}
    #     for g, count in groups_counts.items():
    #         [self._create(assigned_segments=[g]) for i in xrange(count)]
    #
    #     for facet_groups in self.combinations(groups):
    #         resp = self._fetch(segments=facet_groups)
    #         for g, samples in self.groupby(resp, 'assigned_segments'):
    #             oid = groups[g[0]['display_name']]
    #             eq_(groups_counts[oid], len(list(samples)))


class CustomersDistributionTest(CustomersBaseTest):

    def test_plot_by_status(self):
        groups = STATUS
        groups_counts = {g: random.randint(1, 10) for g in groups}
        for g, count in groups_counts.items():
            [self._create(status=g) for i in xrange(count)]

        for facet_groups in self.combinations(groups):
            resp = self._fetch(customer_statuses=facet_groups, group_by='status', plot_by='distribution')
            expected = {k: groups_counts[k] for k in facet_groups} or groups_counts
            eq_(self.count_distribution(resp), expected)

    @unittest.skip('CustomerSegment was removed')
    def test_plot_by_segments(self):
        segment_objs = [CustomerSegment.objects.create(account_id=self.account.id,
                                                       **segment) for segment in CUSTOMER_SEGMENTS]
        groups = {o.display_name: o for o in segment_objs}
        groups_counts = {g: random.randint(1, 10) for g in groups.values()}
        for g, count in groups_counts.items():
            [self._create(assigned_segments=[g.id]) for i in xrange(count)]

        for facet_groups in self.combinations(groups):
            resp = self._fetch(segments=facet_groups, group_by='segment', plot_by='distribution')
            expected = {k.display_name: v for k, v in groups_counts.items() if not facet_groups or k.display_name in facet_groups}
            eq_(self.count_distribution(resp), expected)

    def test_plot_by_locations(self):
        groups = LOCATION_VALUES
        groups_counts = {g: random.randint(1, 10) for g in groups}
        for g, count in groups_counts.items():
            [self._create(location=g) for i in xrange(count)]

        for facet_groups in self.combinations(groups):
            resp = self._fetch(locations=facet_groups, group_by='location', plot_by='distribution')
            expected = {k: groups_counts[k] for k in facet_groups} or groups_counts
            eq_(self.count_distribution(resp), expected)

    def test_plot_by_genders(self):
        groups = ['M', 'F']
        groups_counts = {g: random.randint(1, 10) for g in groups}
        for g, count in groups_counts.items():
            [self._create(sex=g) for i in xrange(count)]

        for facet_groups in self.combinations(groups, 2):
            resp = self._fetch(genders=facet_groups, group_by='gender', plot_by='distribution')
            expected = {k: groups_counts[k] for k in facet_groups} or groups_counts
            eq_(self.count_distribution(resp), expected)

    def test_plot_by_industry(self):
        groups = INDUSTRIES
        groups_counts = {g: random.randint(1, 10) for g in groups}
        for g, count in groups_counts.items():
            [self._create(industry=g) for i in xrange(count)]

        for facet_groups in self.combinations(groups):
            resp = self._fetch(industries=facet_groups, group_by='industry', plot_by='distribution')
            expected = {k: groups_counts[k] for k in facet_groups} or groups_counts
            eq_(self.count_distribution(resp), expected)
