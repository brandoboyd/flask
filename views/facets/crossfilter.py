
import time
from datetime import datetime, timedelta, date
from bson import ObjectId

from .journeys import JourneyDetailsView
from solariat_bottle.db.journeys.facet_cache import facet_cache_decorator
from solariat_bottle.views.facets import (
    list_or_none, str_or_none, nps_value_to_label)
from solariat_bottle.utils.views import Param
from solariat_bottle.db.journeys.customer_journey import (
    CustomerJourney, PLATFORM_STRATEGY, EVENT_STRATEGY)
from solariat_bottle.db.journeys.journey_type import (
    JourneyType, JourneyStageType)
from solariat_bottle.db.journeys.journey_tag import JourneyTag


class CrossFilterView(JourneyDetailsView):

    url_rule = '/crossfilter/json'

    def get_parameters_list(self):
        p = super(CrossFilterView, self).get_parameters_list()
        p += [
            ('widgets', list_or_none, Param.UNCHECKED, Param.REQUIRED),
            ('range_alias', str_or_none, Param.UNCHECKED, None),
        ]
        return p

    # def postprocess_params(self, params):
    #     if params.get('from'):
    #         params['from'] = datetime.strptime(params['from'], '%Y-%m-%d %H:%M:%S')

    #     if params.get('to'):
    #         params['to'] = datetime.strptime(params['to'], '%Y-%m-%d %H:%M:%S')

    #     # Set up the labeling strategy by mapping the param passed in. This check is required because
    #     # None is passed in
    #     if params['labeling_strategy'] == None:
    #         params['labeling_strategy'] = 'default'

    #     labeling_strategy = dict(default=None,
    #                              channel=PLATFORM_STRATEGY,
    #                              event=EVENT_STRATEGY)[params['labeling_strategy']]
    #     params['labeling_strategy'] = labeling_strategy
    #     if params['journey_type']:
    #         params['journey_type'] = [ObjectId(x) for x in params['journey_type']]

    #     if params['status']:
    #         if isinstance(params['status'], list):
    #             params['status'] = map(JourneyStageType.TEXT_STATUS_MAP.get, params['status'])

    #     return params

    def _get_status_by_journey_type(self, initial_pipeline, journey_types):
        t0 = datetime.now()
        pipeline = initial_pipeline[:]
        pipeline.append(
            {"$group": {
                "_id": {"jt": "$jt", "ss": "$ss"},
                "count": {"$sum": 1}}}
        )

        t0 = datetime.now()
        journey_volumes = CustomerJourney.objects.coll.aggregate(pipeline)
        tdelta = str(datetime.now() - t0)

        result = {}
        default_dict = {k: 0 for k in JourneyStageType.STATUS_TEXT_MAP.values()}
        result['data'] = {str(jt.id): default_dict.copy() for jt in journey_types}
        result['legends'] = {str(k): v for k, v in JourneyStageType.STATUS_TEXT_MAP.items()}
        result['labels'] = {str(jt.id): jt.display_name for jt in journey_types}
        for data in journey_volumes['result']:
            jt_id = str(data['_id']['jt'])
            label = str(JourneyStageType.STATUS_TEXT_MAP[data['_id']['ss']])
            result['data'][jt_id][str(label)] = data['count']
        return tdelta, result, pipeline

    def _get_nps_by_journey_type(self, initial_pipeline, journey_types):
        t0 = datetime.now()
        pipeline = initial_pipeline[:]
        pipeline.append(
            {"$group": {
                "_id": {"jt": "$jt", "nps": "$nps"},
                "count": {"$sum": 1}}}
        )

        t0 = datetime.now()
        journey_volumes = CustomerJourney.objects.coll.aggregate(pipeline)
        tdelta = str(datetime.now() - t0)

        result = {}
        result['legends'] = ['detractor', 'passive', 'promoter', 'n/a']
        result['labels'] = {str(jt.id): jt.display_name for jt in journey_types}
        default_dict = {k: 0 for k in result['legends']}
        result['data'] = {str(jt.id): default_dict.copy() for jt in journey_types}

        for data in journey_volumes['result']:
            jt_id = str(data['_id']['jt'])
            label = nps_value_to_label(data['_id']['nps'])
            result['data'].setdefault(jt_id, default_dict.copy())
            result['data'][jt_id][label] += data['count']

        return tdelta, result, pipeline

    def _get_journey_volumes_by_journey_type(self, initial_pipeline, journey_types):
        t0 = datetime.now()
        pipeline = initial_pipeline[:]
        pipeline.append(
            {"$group": {
                "_id": {"jt": "$jt"},
                "count": {"$sum": 1}}}
        )
        journey_volumes = CustomerJourney.objects.coll.aggregate(pipeline)
        tdelta = str(datetime.now() - t0)
        result = {}
        result['data'] = {str(jt.id): 0 for jt in journey_types}
        result['labels'] = {str(jt.id): jt.display_name for jt in journey_types}
        for data in journey_volumes['result']:
            result['data'][str(data['_id']['jt'])] = data['count']
        return tdelta, result, pipeline

    def _get_nps_by_journey_tag(self, initial_pipeline, journey_types):
        t0 = datetime.now()
        journey_tags = JourneyTag.objects(account_id=self.user.account.id)[:]
        default_dict = {'detractor': 0, 'passive': 0, 'promoter': 0, 'n/a': 0}
        result = {'data': {}, 'labels': {}}
        result['labels'] = {str(jt.id): '%s.%s' % (jt.journey_type.display_name, jt.display_name) for jt in journey_tags}
        # executing pipeline query for each journey tag of given account
        timedelta_stats = []
        pipelines = []
        for journey_tag in journey_tags:
            journey_tag_id = str(journey_tag.id)
            pipeline = initial_pipeline[:]
            pipeline.append({'$match': {"jts": journey_tag.id}})
            pipeline.append(
                {"$group": {
                    "_id": {"nps": "$nps"},
                    "count": {"$sum": 1}}}
            )

            t0 = datetime.now()
            pipelines.append(pipeline)
            journey_volumes = CustomerJourney.objects.coll.aggregate(pipeline)
            timedelta_stats.append(str(datetime.now() - t0))

            # preparing data for response, transforming nps values from numbers to verbal labels
            for data in journey_volumes['result']:
                label = nps_value_to_label(data['_id']['nps'])
                result['data'].setdefault(journey_tag_id, default_dict.copy())
                result['data'][journey_tag_id][label] += data['count']
        return str(timedelta_stats), result, pipelines

    def _get_nps_trends(self, initial_pipeline, journey_types, range_alias):
        t0 = datetime.now()
        pipeline = initial_pipeline[:]
        is_output_weekly = 'month' in range_alias
        mongo_aggregation_func = '$week' if is_output_weekly else '$dayOfMonth'
        # import ipdb; ipdb.set_trace()
        pipeline.append(
            {"$group": {
                "_id": {
                    "week_or_day": {mongo_aggregation_func: "$ed"},
                    "month": {"$month": "$ed"},
                    "year": {"$year": "$ed"}},
                "avg": {"$avg": "$nps"}}}
        )

        t0 = datetime.now()
        journey_volumes = CustomerJourney.objects.coll.aggregate(pipeline)
        tdelta = str(datetime.now() - t0)

        result = {'data': {}}
        for item in journey_volumes['result']:
            if is_output_weekly:
                # getting first week date
                year_start = date(item['_id']['year'], 1, 1)
                year_first_week = year_start
                while year_first_week.weekday() != 0:
                    year_first_week -= timedelta(days=1)
                # adding weeks, to match the given date
                dt = year_first_week + timedelta(days=(item['_id']['week_or_day'])*7)
            else:
                dt_args = item['_id']['year'], item['_id']['month'], item['_id']['week_or_day']
                dt = date(*dt_args)
            timestamp = str(int(time.mktime(dt.timetuple())))
            # here I multiply by 10 for representation on dashboard widget
            value = int(item['avg'] * 10)
            result['data'][timestamp] = value

        result['granularity'] = 'week' if is_output_weekly else 'day'

        return tdelta, result, pipeline

    def prepare_query(self, params, request_params):
        primary_match, group_last, secondary_match = super(CrossFilterView, self).prepare_query(
            params,
            request_params,
            collection_name=self.model.__name__)
        # if params['subrange_from'] and params['subrange_to']:
        #     del secondary_match['ed']
        #     secondary_match['ed'] = {
        #         '$gte': params['subrange_from'],
        #         '$lte': params['subrange_to']}
        return primary_match, group_last, secondary_match

    def _compute_stats(self, params, request_params):
        journey_types = self.user.account.get_journey_types()
        if not params['journey_type']:
            params['journey_type'] = [jt.id for jt in journey_types]
        primary_match, group_last, secondary_match = self.prepare_query(
            params,
            request_params)
        initial_pipeline = [{"$match": primary_match}, {"$match": secondary_match}]

        widgets = params['widgets']
        if not widgets:
            widgets = [
                'status_by_journey_type', 'nps_by_journey_type',
                'journey_volumes_by_journey_type', 'nps_by_journey_tag',
                'nps_trends'
            ]

        t0 = datetime.now()
        time_stats = {}
        pipelines = {}
        data = {}

        # here we calling pipelines and capturing timedeltas
        for widget in widgets:
            args = [initial_pipeline, journey_types]
            func_name = '_get_%s' % widget
            if widget == 'nps_trends':
                args.append(params['range_alias'])
                timedelta, widget_data, pipeline = (getattr(self, func_name))(*args)
            else:
                timedelta, widget_data, pipeline = (getattr(self, func_name))(*args)
            time_stats[widget] = timedelta
            pipelines[widget] = str(pipeline)
            data[widget] = widget_data

        time_stats['total'] = str(datetime.now() - t0)
        data['pipelines'] = pipelines

        track_time = False
        if track_time:
            data['time_stats'] = time_stats
        return data

    @facet_cache_decorator(page_type='dashboard')
    def get_data(self, params, request_params):
        result = self._compute_stats(params=params, request_params=request_params)
        return result

    def render(self, params, request_params):
        data = self.get_data(params=params, request_params=request_params)
        return dict(ok=True, data=data)

