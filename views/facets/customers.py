from collections import defaultdict

from solariat_bottle.db.journeys.journey_type import JourneyType

from solariat.db.abstract import ObjectId
from solariat_bottle.db.journeys.customer_journey import CustomerJourney
from .customers_agents_base import CustomersAgentsBaseView
from . import *


class CustomersView(CustomersAgentsBaseView):
    url_rule = '/customer-profiles/json'

    def get_parameters_list(self):
        p = super(CustomersView, self).get_parameters_list()
        p.extend([
            #name                 valid_types  valid_values                 value
            #--------------       -----------  ---------------              --------------
            ('from',              basestring,  is_date,                     Param.REQUIRED),
            ('to',                basestring,  is_date,                     Param.REQUIRED),
            ('agent_id',          str_or_none, Param.UNCHECKED,             Param.REQUIRED),
            ('customer_statuses', list,        Param.UNCHECKED,             Param.REQUIRED),
            ('call_intents',      list,        Param.UNCHECKED,             Param.REQUIRED),
            ('limit',             int_or_none, is_non_negative_int_or_none, None),
            ('offset',            int_or_none, is_non_negative_int_or_none, None)
        ])
        return p

    def postprocess_params(self, params):
        params = super(CustomersView, self).postprocess_params(params)

        if params['call_intents']:
            call_intents_objs = list(CustomerIntentLabel.objects.coll.find({
                'intent': {'$in': params['call_intents']}
            }, {'_id': 1}))
            params['call_intents'] = [each['_id'] for each in call_intents_objs]

        return params

    def render(self, params, request_params):
        query = super(CustomersView, self).prepare_query(params, request_params)
        CustomerProfile = self.user.account.get_customer_profile_class()

        # query['created_at'] = {'$gte': params['from'], '$lte': params['to']}
        query.pop('created_at', None)
        query['_id'] = {'$gte': ObjectId.from_datetime(params['from']), '$lte': ObjectId.from_datetime(params['to'])}

        if params['agent_id']:
            related_journeys = CustomerJourney.objects.coll.find({CustomerJourney.F.agents: ObjectId(params['agent_id'])}, {CustomerJourney.F.customer_id: 1})
            related_customers = [each[CustomerJourney.F.customer_id] for each in related_journeys]
            related_unique_customers = list(set(related_customers))
            agent_condition = {CustomerProfile.F.id: {'$in': related_unique_customers}}
            query['$and'].append(agent_condition)

        if '_and_segments_condition' in params:
            query['$and'].append(params['_and_segments_condition'])

        if params['industries']:
            query['industry'] = {'$in': params['industries']}

        if params['customer_statuses']:
            query['status'] = {'$in': params['customer_statuses']}

        if params['call_intents']:
            query['last_call_intent'] = {'$in': params['call_intents']}

        if params['locations']:
            query['location'] = {'$in': params['locations']}

        if params['genders']:
            query['sex'] = {'$in': params['genders']}

        if not query['$and']:
            del query['$and']

        if params.get('plot_by'):
            group_by = params['group_by']
            group_by = {
                    'gender': 'sex',
                    'status': 'status',
            }.get(group_by, group_by)

            if group_by == 'segment':
                pipeline = [
                    {'$match': query},
                    {'$unwind': '$assigned_segments'},
                    {'$group': {'_id': '$assigned_segments', 'count': {'$sum': 1}}},
                ]
            else:
                pipeline = [
                    {'$match': query},
                    {'$group': {'_id': '$' + group_by, 'count': {'$sum': 1}}},
                ]

            if params['offset']:
                pipeline.append({'$skip': params['offset']})
            if params['limit']:
                pipeline.append({'$limit': params['limit']})
            mongo_result = CustomerProfile.objects.coll.aggregate(pipeline)

            if not mongo_result['ok']:
                return dict(ok=False, error=mongo_result['error'])

            # if group_by == 'segment':
            #     for d in mongo_result['result']:
            #         d['_id'] = CustomerSegment.objects.get(d['_id']).display_name

            groups = mongo_result['result']
            # FIXME where is 'i' value used in UI?
            results = [{"data": [[i, group["count"]]], "label": group["_id"]} for i, group in enumerate(groups)]
        else:
            mongo_result = CustomerProfile.objects.coll.find(query)
            if params['offset']:
                mongo_result.skip(params['offset'])
            if params['limit']:
                mongo_result.limit(params['limit'])
            results = self.format_customers(map(CustomerProfile, mongo_result))
        # TODO: All the endpoitn that require pagination can have common code at least for parsing and adding params
        pagination_parameters = {
            'limit': params['limit'],
            'offset': params['offset'],
            'more_data_available': True if len(results) == params['limit'] else False,
        }

        return dict(ok=True, list=results, **pagination_parameters)

    def format_customers(self, customers):
        customer_ids = [customer.id for customer in customers]
        journeys = CustomerJourney.objects(customer_id__in=customer_ids)
        customer_data = defaultdict(lambda: {'journeys_count': 0, 'agents': set(), 'journey_type_ids': set()})

        for journey in journeys:
            customer_data[journey.customer_id]['journeys_count'] += 1
            for agent in journey.agents:
                customer_data[journey.customer_id]['agents'].add(agent)
            customer_data[journey.customer_id]['journey_type_ids'].add(journey.journey_type_id)

        def to_dict(customer):
            base_dict = customer.to_dict()
            # base_dict['assigned_segments'] = [segment.to_dict() for segment in CustomerSegment.objects.cached_find_by_ids(customer.assigned_segments)]
            data = customer_data[customer.id]
            base_dict['journeys_count'] = data['journeys_count']
            base_dict['agents_count'] = len(data['agents'])
            base_dict['journey_types_display'] = ', '.join([journey_type.display_name for journey_type in JourneyType.objects.cached_find_by_ids(data['journey_type_ids'])])
            return base_dict

        return map(to_dict, customers)
