
from solariat_bottle.db.journeys.facet_cache import facet_cache_decorator
from solariat_bottle.db.journeys.customer_journey import CustomerJourney, STRATEGY_DEFAULT, STRATEGY_EVENT_TYPE
from solariat_bottle.db.journeys.customer_journey import STRATEGY_PLATFORM
from . import *


class JourneySankeyView(JourneyDetailsView):
    url_rule = "/journeys/sankey"

    model = CustomerJourney

    def get_group_by_mappings(self, group_by, result):
        # TODO: Again, drop NPS, just return metric along with a generated index
        if group_by == 'All':
            return {'All': 0}
        elif group_by == 'paths':
            unique_paths = set()
            for entry in result:
                unique_paths.add(" -> ".join(entry.stage_sequence_by_strategy(self.labeling_strategy)))
            mappings = {}
            for idx, unique_path in enumerate(list(unique_paths)):
                mappings[unique_path] = idx
            return mappings
        else:
            unique_metric_vals = set([str(val.full_journey_attributes[group_by]) for val in result])
            mappings = {}
            for idx, unique_metric in enumerate(list(unique_metric_vals)):
                mappings[unique_metric] = idx
            return mappings
        raise Exception("Unknown group by: " + str(group_by))

    def get_group_by_index(self, group_by, entry, group_mappings):
        if group_by == 'All':
            return 0
        elif group_by == 'paths':
            return group_mappings[" -> ".join(entry.stage_sequence_by_strategy(self.labeling_strategy))]
        else:
            return group_mappings[str(entry.full_journey_attributes[group_by])]

    def prepare_plot_result(self, params, result, group_by):
        nodes = dict()
        links = dict()
        node_index = 0
        group_info = self.get_group_by_mappings(group_by, result)
        for entry in result:
            sequence = entry.stage_sequence_by_strategy(self.labeling_strategy)
            prev_node = None
            for x_pos, node_name in enumerate(sequence):
                if x_pos not in nodes:
                    nodes[x_pos] = dict()
                if node_name not in nodes[x_pos]:
                    nodes[x_pos][node_name] = dict(name=node_name,
                                                   node=node_index,
                                                   count=1)
                    node_index += 1
                else:
                    nodes[x_pos][node_name]['count'] += 1

                group_index = self.get_group_by_index(group_by, entry, group_info)

                if prev_node != None:
                    prev_node_index = nodes[x_pos - 1][prev_node]['node']
                    current_node_index = nodes[x_pos][node_name]['node']
                    if prev_node_index not in links:
                        links[prev_node_index] = dict()

                    if group_index not in links[prev_node_index]:
                        links[prev_node_index][group_index] = dict()

                    if current_node_index not in links[prev_node_index][group_index]:
                        links[prev_node_index][group_index][current_node_index] = 1
                    else:
                        links[prev_node_index][group_index][current_node_index] += 1

                prev_node = node_name

        ui_links = []
        ui_nodes = []

        # Keep track of mapping from node index -> node position in list, since that is what JS lib uses
        index_mapping = dict()

        node_index = 0
        for step, step_nodes in nodes.iteritems():
            for node in step_nodes.values():
                ui_nodes.append(dict(name=node['name'],
                                     xPos=step,
                                     count=node['count']))
                index_mapping[node['node']] = node_index
                node_index += 1

        reversed_group_dict = {v: k for k, v in group_info.items()}

        for source_node, link_info in links.iteritems():
            for group_index, dest_info in link_info.iteritems():
                for dest_node, count in dest_info.iteritems():
                    ui_links.append(dict(source=index_mapping[source_node],
                                    target=index_mapping[dest_node],
                                    value=count,
                                    group_index=group_index,
                                    group_name=reversed_group_dict[group_index]))

        if links:
            return dict(nodes=ui_nodes, links=ui_links)
        else:
            return dict(nodes=ui_nodes, links=[])

    # @facet_cache_decorator(page_type='sankey')
    def get_sankey_data(self, params, result):
        result = self.prepare_plot_result(params, result, group_by=params['group_by'])
        result = {'data': result}
        return result

    def render(self, params, request_params):
        self.labeling_strategy = self.label_strategy_map.get(params['labeling_strategy'], STRATEGY_DEFAULT)
        match_query = self.prepare_query(params, request_params)
        journeys = self.model.objects.find(**match_query)[:]
        result = self.get_sankey_data(params=params, result=journeys)
        return dict(ok=True, list=result)
