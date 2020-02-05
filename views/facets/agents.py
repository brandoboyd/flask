import itertools
from collections import defaultdict

from solariat_bottle.db.journeys.customer_journey import CustomerJourney
from .customers_agents_base import CustomersAgentsBaseView
from . import *


class AgentsView(CustomersAgentsBaseView):
    url_rule = '/agent-profiles/json'

    def get_parameters_list(self):
        p = super(AgentsView, self).get_parameters_list()
        p.extend([
            #name                 valid_types   valid_values                 value
            #--------------       -----------   ---------------              --------------
            ('customer_id',       str_or_none,  Param.UNCHECKED,             Param.REQUIRED),
            ('agent_occupancy',   list,         Param.UNCHECKED,             Param.REQUIRED),
            ('locations',         list_or_none, Param.UNCHECKED,             Param.REQUIRED),
            ('genders',           list_or_none, Param.UNCHECKED,             Param.REQUIRED),
            ('limit',             int_or_none,  is_non_negative_int_or_none, None),
            ('offset',            int_or_none,  is_non_negative_int_or_none, None)
        ])
        return p

    def postprocess_params(self, params):
        params = super(AgentsView, self).postprocess_params(params)

        for i, occupancy in enumerate(params['agent_occupancy']):
            gte_lte = map(str.strip, occupancy.split('-'))
            gte, lte = [int(each[:-1]) for each in (gte_lte[0] or '0%', gte_lte[1] or '100%')]
            params['agent_occupancy'][i] = (gte, lte)

        return params

    def render(self, params, request_params):
        query = super(AgentsView, self).prepare_query(params, request_params)
        account = self.user.account
        AgentProfile = account.get_agent_profile_class()
        CustomerProfile = account.get_customer_profile_class()

        if params['customer_id']:
            customer_profile = CustomerProfile.objects.get(params['customer_id'])
            related_journeys = CustomerJourney.objects.coll.find({CustomerJourney.F.customer_id: customer_profile.id},
                                                                 {CustomerJourney.F.agents: 1})
            related_agents = [each[CustomerJourney.F.agents] for each in related_journeys]
            related_unique_agents = list(set(itertools.chain.from_iterable(related_agents)))
            customer_condition = {'_id': {'$in': related_unique_agents}}
            query['$and'].append(customer_condition)

        if '_and_segments_condition' in params:
            #related_customers = CustomerProfile.objects.coll.find(
            #                        params['_and_segments_condition'],
            #                        {CustomerProfile.F.actor_counter: 1}
            #)
            #related_customers_counters = [each[CustomerProfile.F.actor_counter] for each in related_customers]
            related_journeys = CustomerJourney.objects.coll.find(
                    params['_and_segments_condition'],
                    {CustomerJourney.F.agents: 1}
            )
            related_agents = [each[CustomerJourney.F.agents] for each in related_journeys]
            related_unique_agents = list(set(itertools.chain(*related_agents)))
            segments_condition = {'_id': {'$in': related_unique_agents}}
            query['$and'].append(segments_condition)

        if params['industries']:
            ### FIXME: the following is really really too slow
            related_customers = CustomerProfile.objects.coll.find(
                    {'industry': {'$in': params['industries']}},
                    {'_id': 1}
            )
            related_customers_id = [each['_id'] for each in related_customers]
            related_journeys = CustomerJourney.objects.coll.find(
                    {CustomerJourney.F.customer_id: {'$in': related_customers_id}},
                    {CustomerJourney.F.agents: 1}
            )
            related_agents = [each[CustomerJourney.F.agents] for each in related_journeys]
            related_unique_agents = list(set(itertools.chain.from_iterable(related_agents)))
            industries_condition = {'_id': {'$in': related_unique_agents}}
            query['$and'].append(industries_condition)

        if params['agent_occupancy']:
            occ_condition = {'$or': [{'occupancy': {'$gte': min_occ, '$lte': max_occ}} for min_occ, max_occ in params['agent_occupancy']]}
            query['$and'].append(occ_condition)

        if params['locations']:
            query['location'] = {'$in': params['locations']}

        if params['genders']:
            query['sex'] = {'$in': params['genders']}

        if not query['$and']:
            del query['$and']
        if params.get('plot_by'):
            group_by = params['group_by']
            group_by = {'gender': 'sex'}.get(group_by, group_by)

            pipeline = [
                    {'$match': query},
                    {'$group': {'_id': '$' + group_by, 'count': {'$sum': 1}}}
            ]
            if params['offset']:
                pipeline.append({'$skip': params['offset']})
            if params['limit']:
                pipeline.append({'$limit': params['limit']})
            mongo_result = AgentProfile.objects.coll.aggregate(pipeline)

            if not mongo_result['ok']:
                return dict(ok=False, error=mongo_result['error'])

            groups = mongo_result['result']
            # FIXME where is 'i' value used in UI?
            results = [{"data": [[i, group["count"]]], "label": group["_id"]} for i, group in enumerate(groups)]
        else:
            mongo_result = AgentProfile.objects.coll.find(query)
            if params['offset']:
                mongo_result.skip(params['offset'])
            if params['limit']:
                mongo_result.limit(params['limit'])
            results = self.format_agents(map(AgentProfile, mongo_result))

        pagination_parameters = {
            'limit': params['limit'],
            'offset': params['offset'],
            'more_data_available': True if len(results) == params['limit'] else False,
        }

        return dict(ok=True, list=results, **pagination_parameters)

    def format_agents(self, agents):
        agent_customers = defaultdict(set)
        for journey in CustomerJourney.objects(agent_ids__in=[agent.id for agent in agents]):
            for agent in journey.agents:
                agent_customers[agent].add(journey.customer_id)

        def to_dict(agent):
            base_dict = agent.to_dict()
            base_dict['customers_count'] = len(agent_customers[agent.id])
            return base_dict
        return map(to_dict, agents)
