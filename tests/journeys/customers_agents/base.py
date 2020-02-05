import random
import itertools

from solariat_bottle.tests.base import UICase, setup_agent_schema

from solariat_bottle.db.schema_based import (
    KEY_IS_ID, KEY_NAME, KEY_TYPE, KEY_EXPRESSION, TYPE_INTEGER,
    TYPE_STRING, TYPE_BOOLEAN, TYPE_LIST, TYPE_DICT)

class CustomerAgentBaseCase(UICase):

    def setUp(self):
       super(CustomerAgentBaseCase, self).setUp()
       self.login()

       schema = list()
       schema.append({
           KEY_NAME: 'first_name',
           KEY_TYPE: TYPE_STRING,
           # KEY_EXPRESSION: 'last name',
        })
       schema.append({
           KEY_NAME: 'last_name',
           KEY_TYPE: TYPE_STRING,
           # KEY_EXPRESSION: 'last name',
        })
       schema.append({
           KEY_NAME: 'skills',
           KEY_TYPE: TYPE_DICT,
           # KEY_EXPRESSION: 'skills',
        })
       schema.append({
           KEY_NAME: 'sex',
           KEY_TYPE: TYPE_STRING,
           # KEY_EXPRESSION: 'sex',
        })
       schema.append({
           KEY_NAME: 'skillset',
           KEY_TYPE: TYPE_LIST,
           # KEY_EXPRESSION: 'skillset',
        })
       schema.append({
           KEY_NAME: 'seniority',
           KEY_TYPE: TYPE_STRING,
           # KEY_EXPRESSION: 'seniority',
        })
       schema.append({
           KEY_NAME: 'products',
           KEY_TYPE: TYPE_LIST,
           # KEY_EXPRESSION: 'products',
        })
       schema.append({
           KEY_NAME: 'age',
           KEY_TYPE: TYPE_INTEGER,
           # KEY_EXPRESSION: 'age',
        })
       schema.append({
           KEY_NAME: 'occupancy',
           KEY_TYPE: TYPE_INTEGER,
           # KEY_EXPRESSION: 'occupancy',
        })
       schema.append({
           KEY_NAME: 'english_fluency',
           KEY_TYPE: TYPE_STRING,
           # KEY_EXPRESSION: 'english_fluency',
        })
       
       setup_agent_schema(self.user, extra_schema=schema)
       

    def choose_many(self, items, min_=0, max_=None):
        if max_ is None:
            max_ = len(items)
        n_samples = random.randint(min_, max_)
        return random.sample(items, n_samples)

    def groupby(self, resp, group_by):
        key = lambda d: d[group_by]
        _sorted = sorted(resp['list'], key=key)
        return itertools.groupby(_sorted, key=key)

    def count_distribution(self, resp):
        return {elm['label']: elm['data'][0][-1] for elm in resp['list']}

    def combinations(self, groups, max_for_each_combination=1):
        r = []
        for i in xrange(len(groups)+1):
            all_combinations = list(itertools.combinations(groups, i))
            n_samples = min(max_for_each_combination, len(all_combinations))
            r.extend(random.sample(all_combinations, n_samples))
        return r

    def categorize_age_groups(self, resp):
        for each in resp['list']:
            if each['age'] < 16:
                raise Exception("Age less than 16 should not be there")
            elif each['age'] <= 25:
                each['age'] = (16, 25)
            elif each['age'] <= 35:
                each['age'] = (26, 35)
            elif each['age'] <= 45:
                each['age'] = (36, 45)
            else:
                each['age'] = (46, 100)

    def _create(self, **kw):
        raise NotImplemented

    def _fetch(self, **kw):
        raise NotImplemented
