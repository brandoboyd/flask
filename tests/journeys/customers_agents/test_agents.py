import random
import uuid
from nose.tools import eq_

from solariat_bottle.tests.journeys.customers_agents.base import CustomerAgentBaseCase

from solariat_bottle.scripts.data_load.gforce.customers import (
        LOCATION_VALUES, INTENT_LABELS, PRODUCTS,
        ENGLISH_FLUENCY, AGENT_SENIORITY_VALUES,
        agent_first_name_male, agent_first_name_female, agent_last_name
)

class AgentsBaseTest(CustomerAgentBaseCase):

    def _create(self, **kw):
        sex = random.choice(('M', 'F'))
        first_name = random.choice({
                'M': agent_first_name_male,
                'F': agent_first_name_female
        }[sex])
        last_name = random.choice(agent_last_name)

        data = dict(
            account_id=self.account.id,
            first_name=first_name,
            last_name=last_name,
            age=random.randint(16, 100),
            sex=sex,
            skillset={e: 1 for e in self.choose_many(INTENT_LABELS)},
            location=random.choice(LOCATION_VALUES),
            occupancy=0,
            products=self.choose_many(PRODUCTS),
            english_fluency=random.choice(ENGLISH_FLUENCY),
            seniority=random.choice(AGENT_SENIORITY_VALUES),
            native_id=str(uuid.uuid4())
        )
        data.update(kw)
        AgentProfile = self.account.get_agent_profile_class()
        return AgentProfile.objects.create(**data)

    def _fetch(self, **kw):
        data = {
                'age_groups': [],
                'agent_occupancy': [],
                'customer_id': "",
                'genders': None,
                'industries': [],
                'locations': None,
                'segments': [],
                'limit': 50,
                'offset': 0,
        }
        data.update(kw)
        return self._post('/agent-profiles/json', data_dict=data)


class AgentsDetailsTest(AgentsBaseTest):

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


class AgentsDistributionTest(AgentsBaseTest):

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
