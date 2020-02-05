from pprint import pprint

import itertools
import numpy
import math

from solariat_bottle.db.journeys.facet_cache import facet_cache_decorator
from solariat_bottle.db.events.event_type import BaseEventType
from solariat_bottle.db.journeys.journey_type import JourneyStageType, STATUS_ABANDONED
from solariat_bottle.db.journeys.journey_type import JourneyType
from solariat_bottle.db.journeys.customer_journey import CustomerJourney
from .journeys import JourneyDetailsView

PATHS_CONF = [
    {'path_id': 'MostCommonPath', 'label' : 'Most Common Path'},
    {'path_id': 'LongestDuration', 'label' : 'Longest Duration (average)'},
    {'path_id': 'ShortestDuration', 'label' : 'Shortest Duration (average)'},
    {'path_id': 'AbandonmentRate', 'label' : 'Abandonment Rate (average)'},
    {'path_id': 'HighestNPSScore', 'label' : 'Highest NPS Score (average)'},
]

METRICS_CONF = [
    {'id': 'avg_duration',     'label': 'Average Duration', },
    {'id': 'abandonment_rate', 'label': 'Abandonment Rate', },
    {'id': 'nps',              'label': 'NPS',              },
    {'id': 'percentage',       'label': '% of Paths',       },
]


class JourneyMCPView(JourneyDetailsView):

    url_rule = '/journeys/mcp'
    model = CustomerJourney

    def compute_pipeline(self, params, request_params, main_attr, main_attr_measure, stats_to_collect):
        pipeline = []
        pipe = pipeline.append
        F = self.model.F

        # mcp should only tager finished journeys
        match = self.prepare_query(params, request_params, collection_name=self.model.__name__)
        match.update({F.status: {'$in': [JourneyStageType.TERMINATED, JourneyStageType.COMPLETED]}})
        pipe({'$match': match})

        # add group_by
        group_by = {
                '_id': {'node_sequence_agr': '$' + F.node_sequence_agr},
                'journeys_count': {'$sum': 1},
                'duration': {'$avg': '$%s.%s' % (F.journey_attributes, 'duration') },
                'node_stats': {'$push': '$%s' % F.node_sequence },
                'status': {'$push': '$%s' % F.status },
        }
        for attr_label, aggregate_expr in stats_to_collect:
            group_by[attr_label] = aggregate_expr

        pipe({'$group': group_by})
        # sort by count in descending order to pick the first one
        direction = -1 if main_attr_measure == 'max' else 1
        if main_attr != 'most_common_path':
            pipe({'$sort': {main_attr: direction}})
        else:
            pipe({'$sort': {'journeys_count': direction}})

        pipe({'$limit': params.get('limit')})
        # Pick the first one, TODO: following ones could also be MCP if they have the same count
        return pipeline

    # @facet_cache_decorator(page_type='mcp')
    def get_path_data(self, params, request_params, path):
        main_attr_label = path['label']
        aggr_func = path['measure']
        main_attr = 'most_common_path'  # this is main attr
        journey_type = JourneyType.objects.get(request_params['journey_type'][0])
        if main_attr_label in ["Common Path", "Most Common Path"]:
            main_attr = 'most_common_path'
        else:
            for item in journey_type.journey_attributes_schema:
                if item['label'] == main_attr_label:
                    main_attr = item['name']

        stats_to_collect = self.__get_stats_to_collect(journey_type)
        pipeline = self.compute_pipeline(
            params,
            request_params,
            main_attr=main_attr,
            main_attr_measure=aggr_func,
            stats_to_collect=stats_to_collect)
        print "PIPELINE " + str(pipeline)
        initial_result = self.model.objects.coll.aggregate(pipeline)['result']
        print "RESULT " + str(initial_result)
        formatted_result_list = []

        for result in initial_result:
            formatted_result = self.add_stages_and_stats(main_attr, aggr_func, params, result)
            formatted_result = self.add_metrics(formatted_result, result, stats_to_collect)
            formatted_result_list.append(formatted_result)
        if main_attr != 'most_common_path':
            if aggr_func == 'min':
                formatted_result_list = sorted(formatted_result_list, key=lambda x: x['metrics'][main_attr]['value'])
            else:
                formatted_result_list = sorted(formatted_result_list, key=lambda x: -x['metrics'][main_attr]['value'])
        return {'data': formatted_result_list}

    def add_metrics(self, formatted_result, result, stats_to_collect):
        for item in stats_to_collect:
            dyn_metric_name = item[0]
            formatted_result['metrics'][dyn_metric_name] = {
                'label': dyn_metric_name,
                'measure': 'avg',
                'value': round(result[dyn_metric_name])
            }
        return formatted_result

    def add_stages_and_stats(self, path_id, aggr_func, params, result):
        account = self.user.account
        # basic template
        formatted_result = {
            'path_id': path_id,
            'group_by': path_id,
            'measure': aggr_func,
            'label': path_id,
            'no_of_journeys': 0,
            'metrics' : {
                'percentage': {'label': '% of paths', 'value': 0},
            },
            'stages': [],
            'node_sequence_agr': result['_id']['node_sequence_agr'],  # this will be used for drilldown
        }

        # getting counts for nodes
        node_stats = []
        for node_name in result['_id']['node_sequence_agr']:
            node_stats.append([])
        for trace in result['node_stats']:
            for i, item in enumerate(trace):
                node_stats[i].append(item.values()[0])
        for i, item in enumerate(node_stats):
            node_stats[i] = int(math.ceil(sum(item)/len(item)))

        # getting basic counts
        journey_type_id = params['journey_type'][0]
        no_of_all_journeys = CustomerJourney.objects(
                status__in=[JourneyStageType.COMPLETED, JourneyStageType.TERMINATED],
                journey_type_id=journey_type_id).count()
        no_of_abandoned_journeys = result['status'].count(JourneyStageType.TERMINATED)

        formatted_result['no_of_journeys'] = result['journeys_count']
        formatted_result['no_of_abandoned_journeys'] = no_of_abandoned_journeys

        if result:
            # percentage
            percentage = "%.1f"  % ((float(result['journeys_count']) / no_of_all_journeys)*100) if no_of_all_journeys else '0'
            formatted_result['metrics']['percentage']['value'] = percentage
            # abandonment rate
            # abandonment_rate = "%.1f"  % ((float(no_of_abandoned_journeys) / no_of_all_journeys)*100) if no_of_abandoned_journeys else '0'
            # formatted_result['metrics']['abandonment_rate']['value'] = abandonment_rate

            # populating stage and nodes info for the front-end
            stages = formatted_result['stages']
            for i, node in enumerate(result['_id']['node_sequence_agr']):
                stage_type_name, event_type_name = node.split(':')
                stage_type = JourneyStageType.objects.get(journey_type_id=params['journey_type'][0],
                                                          display_name=stage_type_name)

                event_type = BaseEventType.objects.get_by_display_name(
                    self.user.account.id, event_type_name)  # event_type_name from Event.event_type
                stage = {
                        'label': stage_type_name,
                        'stage_type_id': str(stage_type.id),
                        'nodes': [] }
                if  0 == len(stages) or stages[-1]['label'] != stage_type_name:
                    stages.append(stage)

                stages[-1]['nodes'].append({
                    'label': "%s %s" % (node_stats[i], event_type_name),
                    'name': event_type_name,
                    'count': node_stats[i],
                    'platform': event_type.platform,
                    'event_type_id': str(event_type.id) })
        return formatted_result

    def __get_stats_to_collect(self, journey_type):
        stats_to_collect = []
        for attribute in journey_type.journey_attributes_schema:
            if attribute['type'] in ['integer', 'float']:
                item = (attribute['name'], {'$avg': '$%s.%s' % (self.model.F.journey_attributes, attribute['name'])})
                stats_to_collect.append(item)
        return stats_to_collect

    def render(self, params, request_params):
        path = request_params.get('path')

        result = self.get_path_data(params=params, request_params=request_params, path=path)
        print '-' * 100
        print path
        pprint(result)
        return dict(ok=True, paths=result)



