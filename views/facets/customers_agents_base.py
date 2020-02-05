import string
from . import FacetQueryView
from . import *


class CustomersAgentsBaseView(FacetQueryView):

    def get_parameters_list(self):
        p = [
            #name                 valid_types   valid_values     value
            #--------------       -----------   ---------------  --------------
            #('from',              basestring,   is_date,         Param.REQUIRED),
            #('to',                str_or_none,  is_date_or_none, None),
            ('segments',          list,         Param.UNCHECKED, Param.REQUIRED),
            ('age_groups',        list,         Param.UNCHECKED, Param.REQUIRED),
            ('industries',        list,         Param.UNCHECKED, Param.REQUIRED),
            ('locations',         list_or_none, Param.UNCHECKED, Param.REQUIRED),
            ('genders',           list_or_none, Param.UNCHECKED, Param.REQUIRED),
            ('plot_by',           str_or_none,  Param.UNCHECKED, None),
            ('group_by',          str_or_none,  Param.UNCHECKED, None),
        ]
        return p

    def postprocess_params(self, params):
        from .customers import CustomersView
        from .agents import AgentsView

        if params.get('from') and params.get('to'):
            params['from'], params['to'] = parse_date_interval(params['from'], params['to'])

        if params['segments']:
            _or_conditions = []
            params['_and_segments_condition'] = {'$or': _or_conditions}
            if isinstance(self, CustomersView):
                segment_db_field = CustomerProfile.F.assigned_segments
            elif isinstance(self, AgentsView):
                segment_db_field = CustomerJourney.F.customer_segments

            if 'N/A' in params['segments']:
                params['segments'].remove('N/A')
                _or_conditions.append({segment_db_field: []})

            if params['segments']:
                c_segs = CustomerSegment.objects.coll.find(
                    {
                        CustomerSegment.F.display_name: {'$in': params['segments']},
                        CustomerSegment.F.account_id: self.user.account.id
                    },
                    {'_id': 1}
                )
                segment_ids = [each['_id'] for each in c_segs]
                _or_conditions.append({segment_db_field: {'$in': segment_ids}})

        for i, age_group in enumerate(params['age_groups']):
            gte_lte = map(string.strip, age_group.split('-'))
            gte, lte = map(int, (gte_lte[0] or 0, gte_lte[1] or 1000))
            params['age_groups'][i] = (gte, lte)

        return params

    def prepare_query(self, params, request_params):
        q = {
                'account_id': self.user.account.id,
                '$and': [],
        }

        if params.get('from'):
            q['created_at'] = {'$gte': params['from']}

        if params.get('to'):
            if 'created_at' not in q:
                q['created_at'] = {}

            q['created_at']['$lte'] =  params['to']

        if params['age_groups']:
            age_condition = {'$or': [{'age': {'$gte': min_age, '$lte': max_age}} for min_age, max_age in params['age_groups']]}
            q['$and'].append(age_condition)

        return q
