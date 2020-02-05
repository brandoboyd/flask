from bson import ObjectId
from datetime import datetime
from solariat_bottle.views.facets import *
from solariat_bottle.db.journeys.customer_journey import CustomerJourney, STRATEGY_PLATFORM, STAGE_INDEX_SEPARATOR
from solariat_bottle.db.journeys.customer_journey import STRATEGY_DEFAULT, JourneyType, STRATEGY_EVENT_TYPE
from collections import defaultdict


class JourneyDetailsView(FacetQueryView):
    url_rule = '/journeys/json'
    model = CustomerJourney

    labeling_strategy = None

    label_strategy_map = {'event': STRATEGY_EVENT_TYPE,
                          'channel': STRATEGY_PLATFORM}

    def get_parameters_list(self):
        p = [
            #name                 valid_types   valid_values                 value
            #--------------       -----------   ---------------              --------------
            ('from',              basestring,   is_datetime_or_none,         Param.REQUIRED),
            ('to',                str_or_none,  is_datetime_or_none,         Param.REQUIRED),
            ('status',            list_or_none, Param.UNCHECKED,             None),
            ('journey_type',      list_or_none, Param.UNCHECKED,             None),
            ('labeling_strategy', str_or_none,  is_labeling_strategy,        'default'),
            ('channels',          list_or_none, Param.UNCHECKED,             None),
            ('smart_tags',        list_or_none, Param.UNCHECKED,             None),
            ('journey_tags',      list_or_none, Param.UNCHECKED,             None),
            ('sourceName',        str_or_none,  Param.UNCHECKED,             None),
            ('targetName',        str_or_none,  Param.UNCHECKED,             None),
            ('group_by',          str_or_none,  Param.UNCHECKED,             None),
            ('stage',             list_or_none, Param.UNCHECKED,             None),
            ('step',              int_or_none,  Param.UNCHECKED,             None),
            ('step_name',         basestring,   Param.UNCHECKED,             ''),
            ('limit',             int_or_none,  is_non_negative_int_or_none, None),
            ('offset',            int_or_none,  is_non_negative_int_or_none, None),
            ('short_fields',      str_or_none,  is_boolean_string_or_none,   None),
            ('force_recompute',   bool,         Param.UNCHECKED,             False),
            ('subrange_from',     str_or_none,  is_datetime_or_none,         None),
            ('subrange_to',       str_or_none,  is_datetime_or_none,         None),
            ('path',              dict,         Param.UNCHECKED,             None),
            ('metric',            str_or_none,  Param.UNCHECKED,             None),
            ('facets',            dict,         Param.UNCHECKED,             {}),
            ('path',              dict,         Param.UNCHECKED,             {}),
            ('node_sequence_agr', list_or_none, Param.UNCHECKED,             []),
            ('mcp_settings',      dict,         Param.UNCHECKED,             {})
        ]
        return p

    def postprocess_params(self, params):
        if params.get('from'):
            # TODO: Hack, fix once UI is consistent
            try:
                params['from'] = datetime.strptime(params['from'], '%Y-%m-%d %H:%M:%S')
            except:
                params['from'] = datetime.strptime(params['from'], '%m/%d/%Y')

        if params.get('to'):
            try:
                params['to'] = datetime.strptime(params['to'], '%Y-%m-%d %H:%M:%S')
            except:
                params['to'] = datetime.strptime(params['to'], '%m/%d/%Y')

        # overriding from and to in case if subrange is defined
        if params.get('subrange_from'):
            params['from'] = datetime.strptime(params['subrange_from'], '%Y-%m-%d %H:%M:%S')

        if params.get('subrange_to'):
            params['to'] = datetime.strptime(params['subrange_to'], '%Y-%m-%d %H:%M:%S')

        self.labeling_strategy = self.label_strategy_map.get(params['labeling_strategy'], STRATEGY_DEFAULT)

        if params['journey_type']:
            params['journey_type'] = [ObjectId(x) for x in params['journey_type']]

        if params['status']:
            if isinstance(params['status'], list):
                params['status'] = map(JourneyStageType.TEXT_STATUS_MAP.get, params['status'])

        return params

    def get_schema_type(self, name):
        for schema in self.model.objects.get().journey_attributes_schema:
            if schema['name'] == name:
                return schema['type']

    def prepare_common_query(self, params, request_params, F):
        match_query = {'$and': []}
        match_query[F.account_id] = self.user.account.id

        steps_to_find = []
        if params.get('sourceName') or params.get('targetName'):
            if params.get('sourceName'):
                steps_to_find.append(STAGE_INDEX_SEPARATOR.join([params['sourceName'], str(params['step'])]))

            if params.get('targetName'):
                steps_to_find.append(STAGE_INDEX_SEPARATOR.join([params['targetName'], str(params['step'] + 1)]))
        elif params.get('step_name'):
            steps_to_find.append(STAGE_INDEX_SEPARATOR.join([params['step_name'], str(params['step'])]))

        if len(steps_to_find) == 1:
            match_query[F.stage_sequences + '.' + self.labeling_strategy] = steps_to_find[0]
        elif len(steps_to_find) == 2:
            match_query['$and'].extend([{F.stage_sequences + '.' + self.labeling_strategy: steps_to_find[0]},
                                        {F.stage_sequences + '.' + self.labeling_strategy: steps_to_find[1]}])

        # if params.get('step') is not None:
        #     # In Flow diagrams, there are 2 types of drilldown: node and link
        #     # both must contain step; drilldown in node must contain step_name,
        #     # drilldown in link will definitely contain sourceName
        #     source_stage = params.get('step_name') or params.get('sourceName')
        #     match_query['%s.%d' % (F.stage_sequence_names, params['step'])] = source_stage

        if params.get('node_sequence_agr'):
            match_query[F.node_sequence_agr] = params['node_sequence_agr']
            # this is not really required because uncompleted or unterminated journey will have node_sequence_agr == []
            #primary_match[F.status] = {'$in': [JourneyStageType.TERMINATED, JourneyStageType.COMPLETED]}

        if params['status']:
            match_query[F.status] = {'$in': params['status']}

        if params['stage']:
            match_query[F.stage_name] = {'$in': params['stage']}

        if params['group_by'] == 'stage':
            params['group_by'] = 'stage_name'

        if params.get('from') and params.get('to'):
            match_query[F.last_event_date] = {'$gte': params['from'], '$lte': params['to']}

        if params['smart_tags']:
            match_query[F.smart_tags] = {'$in': [ObjectId(t_id) for t_id in params['smart_tags']]}

        if params['journey_tags'] and hasattr(F, 'journey_tags'):
            match_query[F.journey_tags] = {'$in': [ObjectId(_id) for _id in params['journey_tags']]}

        if params['channels']:
            match_query[F.channels] = {'$in': [ObjectId(c_id) for c_id in params['channels']]}

        if params['journey_type']:
            if isinstance(params['journey_type'], list):
                match_query[F.journey_type_id] = {'$in': params['journey_type']}
            else:
                match_query[F.journey_type_id] = params['journey_type']

        if params.get('facets'):
            #assert params['journey_type'], "param 'journey_type' is required for param 'facets'"
            for field, values in params['facets'].iteritems():
                match_query['%s.%s' % (F.journey_attributes, field)] = {'$in': values}

        if not match_query['$and']:
            del match_query['$and']

        return match_query

    def prepare_query(self, params, request_params, collection_name=None):
        F = self.model.F
        match_query = self.prepare_common_query(params, request_params, F)
        return match_query

    def render(self, params, request_params):
        query = self.prepare_query(params, request_params)
        # set F here because prepare_query can change the model
        F = self.model.F

        group_by = dict()
        if params['step'] is not None:
            group_by.update(
                {"stage_sequence_names": {'$max': '$' + F.stage_sequence_names}}
            )

        pipeline = []
        pipe = pipeline.append
        pipe({'$match': query})

        if params['offset']:
            pipe({'$skip': params['offset']})
        if params['limit']:
            pipe({'$limit': params['limit']})

        app.logger.debug(pipeline)
        agg_results = self.model.objects.coll.aggregate(pipeline)['result']
        # if params['step'] is not None:
        #     filtered_results = []
        #     for entry in agg_results:
        #         if len(entry['stage_sequence_names']) <= params['step']:
        #             continue
        #         if entry['stage_sequence_names'][params['step']] != params['step_name']:
        #             continue
        #         filtered_results.append(entry)
        # else:
        #     filtered_results = agg_results

        journeys = [CustomerJourney(data).to_dict() for data in agg_results]
        short_fields = ['id', 'journey_type_name', 'customer_id', 'customer_name', 'status', 'segment_names',
                        'total_effort', 'journey_tags', 'start_date', 'last_event_date', 'journey_attributes']
        for journey in journeys:
            journey['customer_id'] = str(journey['customer_id'])
            journey['journey_type_name'] = JourneyType.objects.get(journey['journey_type_id']).display_name
            if params['short_fields']:
                for key in journey.keys():
                    if key not in short_fields:
                        journey.pop(key)

        pagination_parameters = {
            'limit': params['limit'],
            'offset': params['offset'],
            'more_data_available': True if len(journeys) == params['limit'] else False,
        }

        return dict(ok=True, list=journeys, **pagination_parameters)


class JourneyPlotsView(JourneyDetailsView):
    # TODO: Refactor this into specific plots classes we can defer to, logic is starting to get too complicated
    url_rule = '/journeys/plots'
    model = CustomerJourney

    def get_parameters_list(self):
        p = super(JourneyPlotsView, self).get_parameters_list()
        p.extend([
            #name                 valid_types  valid_values     value
            #--------------       -----------  ---------------  --------------
            ('plot_type',       str_or_none, Param.UNCHECKED,   Param.REQUIRED),
            ('group_by',        str_or_none, Param.UNCHECKED,   None),
            ('level',           basestring,  is_hdm_level,      'hour'),
            ('computed_metric', str_or_none, Param.UNCHECKED,   'count')
        ])
        return p

    def get_group_by_pipeline(self, initial_pipeline, params):
        F = self.model.F
        metric_map = {
            'count': {'$sum': 1},
        }
        group_items = {'_id': {}}

        group_by_param = params['group_by']
        if group_by_param:
            if group_by_param in self.model.fields:
                # TODO is unwind check for ListField required here also?
                group_items['_id'][group_by_param] = '$' + F(group_by_param)
            else:
                group_by_reference = '$%s.%s' % (F.journey_attributes, group_by_param)
                if self.get_schema_type(group_by_param) == 'list':
                    initial_pipeline.append({'$unwind': group_by_reference})
                group_items['_id'][group_by_param] = group_by_reference

        computed_metric = params.get('computed_metric') or 'count'
        if computed_metric in metric_map:
            group_items[computed_metric] = metric_map[computed_metric]
        else:
            group_items[computed_metric] = {'$avg': '$%s.%s' % (F.journey_attributes, computed_metric)}
        return {'$group': group_items}

    def prepare_distribution_query(self, initial_pipeline, params):
        group_dict = self.get_group_by_pipeline(initial_pipeline, params)
        initial_pipeline.append(group_dict)

    def prepare_timeline_query(self, initial_pipeline, params):
        F = self.model.F
        last_updated = '$' + F.last_updated

        timeline_level = params.get('level')
        if timeline_level == 'hour':
            time_group = {"year": {'$year': last_updated},
                          "day": {'$dayOfYear': last_updated},
                          "hour": {'$hour': last_updated}}
        elif timeline_level == 'day':
            time_group = {"year": {'$year': last_updated},
                          "day": {'$dayOfYear': last_updated}}
        elif timeline_level == 'month':
            time_group = {"year": {'$year': last_updated},
                          "month": {'$month': last_updated},
                          "day": {'$dayOfYear': last_updated}}
        else:
            raise Exception("Unknown level %s" % timeline_level)

        group_dict = self.get_group_by_pipeline(initial_pipeline, params)
        group_dict['$group']['_id'].update(time_group)
        initial_pipeline.append(group_dict)

    def compute_pipeline(self, initial_pipeline, params):
        if params['plot_type'] == 'avg_distributions':
            self.prepare_distribution_query(initial_pipeline, params)
        elif params['plot_type'] == 'timeline':
            self.prepare_timeline_query(initial_pipeline, params)

    def get_timestamp(self, mongo_group_entry):
        date = datetime(year=mongo_group_entry['_id']['year'], month=1, day=1)
        date = date + timedelta(days=mongo_group_entry['_id']['day'] - 1)
        if 'hour' in mongo_group_entry['_id']:
            date = date + timedelta(hours=mongo_group_entry['_id']['hour'])
        timestamp = datetime_to_timestamp_ms(date)
        return timestamp

    def fill_with_zeroes(self, input_value, from_date, to_date):
        """
        :param input_value: Input plot array in the form [[timestamp, count], [timestamp, count], ...]
        :param from_date: Start of interval
        :param to_date: End of interval
        :return: A similar list to `input_value` that has timestamps for each hour in the interval, filled with 0
        if it was missing from input_value
        """
        value = sorted(input_value, key=lambda x: x[0])
        default_zeroes = []
        while from_date < to_date:
            timestamp = datetime_to_timestamp_ms(from_date)
            default_zeroes.append([timestamp, 0])
            from_date += timedelta(hours=1)
        gapped_filled_values = []
        second_index = 0    # Traverse the 0 filled defaults more efficiently
        for entry in value:
            last_value = gapped_filled_values[-1][0] if gapped_filled_values else -1
            while default_zeroes[second_index][0] <= last_value:
                second_index += 1
            while entry[0] > default_zeroes[second_index][0] and second_index < len(default_zeroes):
                gapped_filled_values.append(default_zeroes[second_index])
                second_index += 1
            gapped_filled_values.append(entry)

        last_value = gapped_filled_values[-1][0] if gapped_filled_values else -1

        try:
            while default_zeroes[second_index][0] <= last_value:
                second_index += 1
                gapped_filled_values.extend(default_zeroes[second_index:])
        except IndexError, err:
            app.logger.error(err)
        return gapped_filled_values

    def prepare_plot_result(self, params, result):
        computed_metric = params.get('computed_metric', 'count')
        group_by_param = params.get('group_by')
        rv = []

        if params['plot_type'] == 'timeline':
            helper_structure = defaultdict(list)

            for entry in result:
                if group_by_param:
                    group_by_value = entry['_id'][group_by_param]
                    label = CustomerJourney.metric_label(computed_metric, group_by_param, group_by_value)
                else:
                    label = "All journeys' %s" % computed_metric

                timestamp = self.get_timestamp(entry)
                helper_structure[label].append([timestamp, entry[computed_metric]])

            for key, value in helper_structure.iteritems():
                if params['level'] == 'hour':
                    rv.append(dict(label=key, data=self.fill_with_zeroes(value, params['from'], params['to'])))
                else:
                    rv.append(dict(label=key, data=sorted(value, key=lambda x: x[0])))

            self.fill_multi_series_with_zeroes(rv)
        elif params['plot_type'] == 'avg_distributions':
            for entry in result:
                if group_by_param:
                    group_by_value = entry['_id'][group_by_param]
                    label = CustomerJourney.metric_label(computed_metric, group_by_param, group_by_value)
                else:
                    label = "All journeys' %s" % computed_metric
                # TODO UI is not showing float values, so rounding to integer for the time being
                rv.append(dict(label=label, value=int(entry[computed_metric])))
        return rv

    def render(self, params, request_params):
        match_query = self.prepare_query(params, request_params)
        pipeline = [{"$match": match_query}]
        self.compute_pipeline(pipeline, params)
        app.logger.debug(pipeline)
        result = self.model.objects.coll.aggregate(pipeline)['result']
        result = self.prepare_plot_result(params, result)
        return dict(ok=True, list=result)
