from solariat_bottle.db.journeys.customer_journey import CustomerJourney
from solariat_bottle.db.journeys.facet_cache import facet_cache_decorator
from solariat_bottle.db.funnel import Funnel
from . import JourneyDetailsView
from . import *


class FunnelFacetView(JourneyDetailsView):
    url_rule = '/funnel/facets'
    model = Funnel

    def get_parameters_list(self):
        params = super(FunnelFacetView, self).get_parameters_list()
        params.extend([('funnel_id',         basestring,   Param.UNCHECKED, Param.REQUIRED),
                       ('force_recompute',   bool,         Param.UNCHECKED, False),])
        return params

    def postprocess_params(self, params):
        super(FunnelFacetView, self).postprocess_params(params)
        params['funnel'] = Funnel.objects.get_by_user(self.user, id=params['funnel_id'])
        params['steps'] = map(JourneyStageType.objects.get, params['funnel'].steps)
        if params['status']:
            params['status'] = [JourneyStageType.TEXT_STATUS_MAP[ss] for ss in params['status']]
        return params

    def prepare_query(self, params, request_params):
        match_query = self.prepare_common_query(params, request_params, CustomerJourney.F)
        funnel_steps = [jst.display_name for jst in JourneyStageType.objects(id__in=params['funnel'].steps)]
        if funnel_steps:
            match_query[CustomerJourney.F.stage_sequence_names + '.0'] = funnel_steps[0]
        return match_query

    # @facet_cache_decorator(page_type='funnel')
    def get_data(self, params, request_params):
        query = self.prepare_query(params, request_params)
        metric = params.get('group_by')
        funnel = params['funnel']
        steps = params['steps']
        if steps:
            # for first step, query the events in Event matching journey_stage_type with step 0
            # no need to use journey_type in query as journey_stage_type is enough
            pipeline = [
                    {'$match': query},
                    {'$group':
                        {
                            '_id': {"sequence_names": '$' + CustomerJourney.F.stage_sequence_names},
                            'count': {'$sum': 1}
                        }
                    }
            ]
            if metric:
                pipeline[1]['$group'][metric] = {'$avg': '$%s' % CustomerJourney.F.full_journey_attributes
                                                         + '.' + metric}
            agg_results = CustomerJourney.objects.coll.aggregate(pipeline)['result']
        else:
            agg_results = []

        final_result = []
        funnel_steps = [jst.display_name for jst in JourneyStageType.objects(id__in=funnel.steps)]

        for _ in funnel_steps:
            final_result.append({"count": {"stuck": 0,
                                           "sum": 0,
                                           "converted": 0,
                                           "abandoned": 0},
                                 metric: {"stuck": 0.0,
                                          "stuck_count": 0,
                                          "avg": 0.0,
                                          "abandoned": 0.0,
                                          "abandoned_count": 0,
                                          "converted": 0.0,
                                          "converted_count": 0}})
        candidate_sequences = dict()
        for entry in agg_results:
            candidate_sequences[str(entry['_id']['sequence_names'])] = entry

        def update_results(step_index, funnel_step_sequence, next_expected_step, j_entry, is_last):
            count_val = j_entry['count']
            metric_val = j_entry[metric]

            SEPARATOR = '__'
            str_repr_funnel = SEPARATOR.join(funnel_step_sequence)
            str_next_step_sequence = SEPARATOR.join(funnel_step_sequence + [next_expected_step])
            entry_str_repr_sequence = SEPARATOR.join(j_entry['_id']['sequence_names'])

            if str_repr_funnel not in entry_str_repr_sequence:
                candidate_sequences.pop(str(j_entry['_id']['sequence_names']))
                return

            if str_next_step_sequence not in entry_str_repr_sequence and not is_last:
                # We never make it to next step. Either stuck or abandoned. Stuck if the index of this is last
                if entry_str_repr_sequence.index(str_repr_funnel) + len(str_repr_funnel) == len(entry_str_repr_sequence):
                    # THis is stuck
                    final_result[step_index]['count']["stuck"] += count_val
                    final_result[step_index]['count']["sum"] += count_val
                    final_result[step_index][metric]["stuck"] += count_val * metric_val
                    final_result[step_index][metric]["stuck_count"] += count_val
                else:
                    # This is abandoned
                    final_result[step_index]['count']["abandoned"] += count_val
                    final_result[step_index]['count']["sum"] += count_val
                    final_result[step_index][metric]["abandoned"] += count_val * metric_val
                    final_result[step_index][metric]["abandoned_count"] += count_val
            else:
                # This is converted
                final_result[step_index]['count']["converted"] += count_val
                final_result[step_index]['count']["sum"] += count_val
                final_result[step_index][metric]["converted"] += count_val * metric_val
                final_result[step_index][metric]["converted_count"] += count_val

        for sequence_length in xrange(1, len(funnel_steps) + 1):
            for entry in candidate_sequences.values():
                update_results(step_index=sequence_length - 1,
                               funnel_step_sequence=funnel_steps[0:sequence_length],
                               next_expected_step=funnel_steps[sequence_length] if sequence_length < len(funnel_steps) else "None",
                               j_entry=entry,
                               is_last=sequence_length==len(funnel_steps))

        for entry in final_result:
            sum_nps = entry[metric]['stuck'] + entry[metric]['stuck'] + entry[metric]['stuck']
            count_nps = entry[metric]['stuck_count'] + entry[metric]['stuck_count'] + entry[metric]['stuck_count']
            if count_nps:
                entry[metric]['avg'] = sum_nps / count_nps
                if entry[metric]['stuck_count']:
                    entry[metric]['stuck'] = entry[metric]['stuck'] / entry[metric]['stuck_count']
                if entry[metric]['converted_count']:
                    entry[metric]['converted'] = entry[metric]['converted'] / entry[metric]['converted_count']
                if entry[metric]['abandoned_count']:
                    entry[metric]['abandoned'] = entry[metric]['abandoned'] / entry[metric]['abandoned_count']
            entry[metric].pop('abandoned_count')
            entry[metric].pop('stuck_count')
            entry[metric].pop('converted_count')

        final_result = {'data': final_result}
        return final_result

    def render(self, params, request_params):
        result = self.get_data(params=params, request_params=request_params)
        return dict(ok=True, list=result)


class FunnelStageStatisticView(FunnelFacetView):
    url_rule = '/funnel/step_summary'
    model = Funnel

    def get_parameters_list(self):
        return [
            ('funnel_id',         basestring, Param.UNCHECKED, Param.REQUIRED),
            ('stage_id',          basestring, Param.UNCHECKED, Param.REQUIRED),
            ('transition_status', basestring, Param.UNCHECKED, None)
        ]

    def postprocess_params(self, params):
        params['from'], params['to'] = parse_date_interval(params['from'], params['to'])
        params['funnel'] = Funnel.objects.get_by_user(self.user, id=params['funnel_id'])
        params['steps'] = map(JourneyStageType.objects.get, params['funnel'].steps)
        return params

    def render(self, params, request_params):
        return jsonify(ok=True, list=[])
