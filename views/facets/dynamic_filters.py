import logging
import copy
from collections import defaultdict
from datetime import datetime, timedelta
from flask import jsonify

from solariat.db.abstract import KEY_NAME, KEY_TYPE
from solariat.exc.base import AppException
from solariat.utils.timeslot import datetime_to_timestamp_ms
from solariat_bottle.db.journeys.customer_journey import CustomerJourney
from solariat_bottle.db.journeys.journey_type import JourneyType
from solariat_bottle.facets import FacetUI, FACET_GROUPBY_THRESHOLD, UNIQUE_FACET_VALUES_THRESHOLD
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.views.base import BaseView, HttpResponse
from . import app

ENTITY_PATHS = dict(
        CUSTOMER = 'customer',
        AGENT = 'agent',
        DATASET = 'dataset',
        JOURNEY = 'journey',
)


def get_schema_class(user, entity, entity_name=None):
    if entity == ENTITY_PATHS['CUSTOMER']:
        schema_class = user.account.customer_profile.get(user)

    elif entity == ENTITY_PATHS['AGENT']:
        schema_class = user.account.agent_profile.get(user)

    elif entity == ENTITY_PATHS['DATASET']:
        if entity_name is None:
            raise Exception("Name of dataset is required for dataset facets.")
        schema_class = user.account.datasets.get_dataset(user, entity_name)

    else:
        raise Exception("Entity %r is not supported." % entity)

    return schema_class


@app.route('/facet-filters/<entity>')
@app.route('/facet-filters/<entity>/<entity_name>')
@login_required
def facets_schema(user, entity, entity_name=None):
    schema_class = get_schema_class(user, entity, entity_name)
    if schema_class is None:
        return jsonify(ok=False, error="No such entity '%s' for this account or for this user" % entity)

    data = FacetUI.to_json(schema_class=schema_class)

    return jsonify(ok=True, **data)


@app.route('/facet-filters/journey/<display_name>')
@login_required
def facets_journey(user, display_name):
    jt = JourneyType.objects.find_one_by_user(user, account_id=user.account.id, display_name=display_name)

    if jt is None:
        return jsonify(ok=False, error="No such journey type %s" % display_name), 500

    rv = {
            'filters': [],
            'metrics': [],
            'group_by': [],
    }
    for key, cardinality in jt.get_journey_attributes_cardinalities().iteritems():
        # skip fields with cardinality 0 or 1
        if cardinality['count'] < 2:
            continue

        # compute group_by
        if cardinality['count'] <= FACET_GROUPBY_THRESHOLD:
            rv['group_by'].append(key)

        if cardinality['type'] == 'integer':
            rv['metrics'].append(key)

        if key in jt.journey_attributes_cardinalities:
            # For actual facets, only keep the dynamic ones since static ones are already defined
            facet_field = {
                    'name': key,
                    'type': cardinality['type'],
            }

            if cardinality['count'] > UNIQUE_FACET_VALUES_THRESHOLD:
                # for string types, skip fields with high cardinality
                if cardinality['type'] == 'string':
                    continue
            else:
                facet_field['values'] = cardinality.get('values')
            rv['filters'].append(facet_field)

    return jsonify(ok=True, **rv)


class DynamicBaseView(BaseView):
    def post(self, **request_params):
        if not hasattr(self, 'data_class') or self.data_class is None:
            self.schema_class = get_schema_class(self.user, self.entity)
            if self.schema_class is None:
                return HttpResponse(ok=False, data="No such entity '%s' for this account or for this user" % self.entity)
            self.data_class = self.schema_class.get_data_class()

        params = self._preprocess_params(request_params)
        try:
            return self.render(params)
        except Exception, err:
            logging.exception(__name__)
            raise AppException(repr(err))

    def get_match_query(self, params):
        assert self.data_class, "Firstly, set 'data_class' out of entity. Normally, it's called inside 'render' method."
        FacetUI.validate_all(self.data_class.fields, params)
        # FacetUI.get_query assumes same field name and db_field
        match_query = FacetUI.get_query(self.data_class.fields, params)
        return match_query

    def _preprocess_params(self, request_params):
        self._request_params = request_params
        # TODO validate params
        params = copy.deepcopy(request_params)
        self._process_timerange(params)
        return params

    def _process_timerange(self, params):
        if hasattr(self, 'timeline_field'):
            assert self.timeline_field not in params, ('Timeline field %r should be queried with from/to params' %
                                                       self.timeline_field)
        if params.get('from') or params.get('to'):
            params[self.timeline_field] = [params.pop('from', None), params.pop('to', None)]

    def get_schema_type(self, name):
        for schema in self.schema_class.schema:
            if schema[KEY_NAME] == name:
                return schema[KEY_TYPE]


class DetailRender(object):
    def render(self, params):
        limit = params.pop('limit', 20)

        if 'page' in params:
            page = params.pop('page')
            offset = limit * (page - 1)
        else:
            offset = params.pop('offset', 0)

        match_query = self.get_match_query(params)

        results = list(self.data_class.objects.coll.find(match_query, {'_id': 1})
                                                   .skip(offset)
                                                   .limit(limit+1))
        ids = [each['_id'] for each in results]
        results = [each.to_dict() for each in self.data_class.objects.find(id__in=ids)]
        return dict(
                list=results[:limit],
                more_data_available=len(results) > limit,
                offset=offset,
                limit=limit,
        )


class GraphRender(object):
    def get_group_by_pipeline(self, pipeline, group_by, metric, metric_aggregation):
        F = self.data_class.F
        group_items = {'_id': {}}

        # No group_by in trends graph will have single line or single stacked area
        if group_by:
            reference_field = '$'+F(group_by)
            if self.get_schema_type(group_by) == 'list':
                pipeline.append({'$unwind': reference_field})
            group_items['_id'][group_by] = reference_field

        if metric == 'count':
            metric_grouping = {'$sum': 1}
        else:
            metric_grouping = {'$'+metric_aggregation: '$'+F(metric)}

        group_items[metric] = metric_grouping
        return {'$group': group_items}

    def render(self, params):
        group_by = params.pop('group_by', None)
        metric = params.pop('metric')
        # metric_aggregation is not required when metric="count", otherwise this would be "sum", "avg"
        metric_aggregation = params.pop('metric_aggregation', 'avg')

        pipeline = [{'$match': self.get_match_query(params)}]
        self.add_group_pipeline(pipeline, group_by, metric, metric_aggregation)
        aggregated = self.data_class.objects.coll.aggregate(pipeline)

        result = self.prepare_plot_result(aggregated, group_by, metric)
        return result


class DynamicDetailView(DynamicBaseView, DetailRender):
    pass


class DynamicTrendView(DynamicBaseView, GraphRender):
    def add_group_pipeline(self, pipeline, group_by, metric, metric_aggregation):
        F = self.data_class.F
        # assume day level aggregation for now
        time_grouping = {
                'year': {'$year':      '$'+F(self.timeline_field)},
                'day' : {'$dayOfYear': '$'+F(self.timeline_field)},
        }
        group_dict = self.get_group_by_pipeline(pipeline, group_by, metric, metric_aggregation)
        group_dict['$group']['_id'].update(time_grouping)
        pipeline.append(group_dict)

    def prepare_plot_result(self, aggregated, group_by, metric):
        grouped_data = defaultdict(list)

        for entry in aggregated['result']:
            label = str(entry['_id'].get(group_by, 'All'))
            timestamp = self.get_timestamp(entry)
            grouped_data[group_by_value].append([timestamp, entry[metric]])

        rv = []
        for label, time_series_data in grouped_data.iteritems():
            time_series_data.sort(key=lambda x: x[0])
            rv.append(dict(label=label, data=time_series_data))

        self.fill_multi_series_with_zeroes(rv)
        return rv

    def get_timestamp(self, mongo_group_entry):
        date = datetime(year=mongo_group_entry['_id']['year'], month=1, day=1)
        date = date + timedelta(days=mongo_group_entry['_id']['day'] - 1)
        if 'hour' in mongo_group_entry['_id']:
            date = date + timedelta(hours=mongo_group_entry['_id']['hour'])
        timestamp = datetime_to_timestamp_ms(date)
        return timestamp

    def fill_multi_series_with_zeroes(self, multi_series):
        """
        Fills missing timestamp data in multi-series data,
        so that all series contain same timestamp data
        """
        all_timestamps = set()
        for series in multi_series:
            all_timestamps.update(each[0] for each in series['data'])

        all_timestamps = sorted(all_timestamps)

        for series in multi_series:
            series_timestamps = [each[0] for each in series['data']]
            for i, timestamp in enumerate(all_timestamps):
                if timestamp not in series_timestamps:
                    series['data'].insert(i, [timestamp, 0])


class DynamicDistributionView(DynamicBaseView, GraphRender):
    def add_group_pipeline(self, pipeline, group_by, metric, metric_aggregation):
        group_dict = self.get_group_by_pipeline(pipeline, group_by, metric, metric_aggregation)
        pipeline.append(group_dict)

    def prepare_plot_result(self, aggregated, group_by, metric):
        rv = []
        for i, entry in enumerate(aggregated['result']):
            label = str(entry['_id'].get(group_by, 'All'))
            rv.append(dict(label=label, value=[i, entry[metric]]))
        return rv


DETAIL_TAB = 'Detail'
TREND_TAB = 'Trend'
DISTRIBUTION_TAB = 'Distribution'
DEFAULT_TABS = [DETAIL_TAB, TREND_TAB, DISTRIBUTION_TAB]


class DynamicViews(object):
    @classmethod
    def register(cls, app):
        tabs = cls.tabs if hasattr(cls, 'tabs') else DEFAULT_TABS
        for tab in tabs:
            class_name = '%s%sView' % (cls.entity.title(), tab.title())
            base_classes = (globals()['Dynamic%sView' % tab.title()], cls)
            url_rules = [('/facet-search/%s/%s' % (cls.entity.lower(), tab.lower()), ['POST'])]

            view = type(class_name, base_classes, {'url_rules': url_rules})
            view.register(app)


class CustomerProfileViews(DynamicViews):
    entity = 'customer'
    tabs = [DETAIL_TAB, DISTRIBUTION_TAB]


class AgentProfileViews(DynamicViews):
    entity = 'agent'
    tabs = [DETAIL_TAB, DISTRIBUTION_TAB]


CustomerProfileViews.register(app)
AgentProfileViews.register(app)
