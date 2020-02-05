from solariat_bottle.db.channel_hot_topics import ChannelHotTopics
from solariat_bottle.db.data_export import DataExport
from solariat_bottle.plots.factory import get_plotter
from solariat_bottle.tasks import process_export_task

from solariat.utils.timeslot import Timeslot, parse_datetime, datetime_to_timeslot, now, \
    timestamp_ms_to_datetime
from solariat_bottle.views.facets import get_posts, seq_types
from solariat_bottle.utils.views import render_posts

from . import FacetQueryView
from . import *


class HotTopicsView(FacetQueryView):
    url_rule = '/hot-topics/json'

    def get_parameters_list(self):
        p = super(HotTopicsView, self).get_parameters_list()
        p.extend([
            ('parent_topic', str_or_none, Param.UNCHECKED,       None),
            ('cloud_type',   str_or_none, is_cloud_type_or_none, None),
        ])
        return p

    def postprocess_params(self, params):
        params = super(HotTopicsView, self).postprocess_params(params)
        del params['plot_type']
        return params

    @staticmethod
    def get_prev_timeslot_range(from_ts, to_ts):
        from_tsp = from_ts.timestamp
        to_tsp = to_ts.timestamp
        ONE_DAY_SEC = 24 * 60 * 60

        delta = to_tsp - from_tsp + ONE_DAY_SEC
        return (
            Timeslot.from_timestamp(from_tsp - delta, level=from_ts.level),
            Timeslot.from_timestamp(to_tsp - delta, level=to_ts.level))

    def render(self, params, request_params):
        """Return json list of hot-topic stats
        """
        cloud_type = params.pop('cloud_type', None)
        if cloud_type and cloud_type != 'none':
            from_ts, to_ts = self.get_prev_timeslot_range(
                params['from_ts'], params['to_ts'])
            params['time_ranges'] = (
                (from_ts, to_ts), (params.pop('from_ts'), params.pop('to_ts')))
            params['cloud_type'] = cloud_type
            result = ChannelHotTopics.objects.batch_select(**params)[0]
        else:
            result = ChannelHotTopics.objects.by_time_span(**params)
        return {"ok": True, "list": result}


class TrendsView(FacetQueryView):
    url_rule = '/trends/json'

    def get_parameters_list(self):
        p = super(TrendsView, self).get_parameters_list()
        p.extend([
            ('level',    basestring,  is_hdm_level,    'hour'),
            ('topics',   list,        all_topic_descs, [ALL_TOPICS_desc]),
            ('group_by', str_or_none, is_group_by,     'topic'),
            ('plot_by',  basestring,  is_plot_by,      'time')
        ])
        return p

    def postprocess_params(self, params):
        params = super(TrendsView, self).postprocess_params(params)
        get_pair = lambda x: (x['topic'], x['topic_type'] != 'node')

        to_ts = params['to_ts']
        date_now = now()
        if to_ts.timestamp_ms > datetime_to_timestamp_ms(date_now):
            params['to_ts'] = Timeslot(date_now, to_ts.level)

        params['topic_pairs'] = map(get_pair, params['topics'])
        del params['topics']

        return params

    def render(self, params, request_params):
        plotter = get_plotter(**params)
        result = plotter.compute_plotting_data()
        return result


class PostsView(FacetQueryView):
    url_rule = '/posts/json'

    def get_parameters_list(self):
        p = super(PostsView, self).get_parameters_list()
        p.extend([
            ('last_query_time', long_or_none, is_long_or_none,                       None),
            ('from',            basestring,   is_datetime,                           Param.REQUIRED),
            ('to',              basestring,   is_datetime,                           Param.REQUIRED),
            ('level',           basestring,   is_hdm_level,                          'hour'),
            ('topics',          list,         all_topic_descs,                       [ALL_TOPICS_desc]),
            ('thresholds',      dict,         is_threshold_map,                      Param.REQUIRED),
            ('assignments',     list_or_none, all_p_statuses,                        None),
            ('sort_by',         basestring,   is_sort_by,                            'time'),
            ('message_type',    list_or_none, Post.MESSAGE_TYPE_MAP.keys() + [None], None),
            ('limit',           int_or_none,  is_non_negative_int_or_none,           None),
            ('offset',          int_or_none,  is_non_negative_int_or_none,           None)
        ])
        return p

    def postprocess_params(self, params):
        r = params
        from_dt = parse_datetime(r['from'])
        to_dt   = parse_datetime(r['to'])

        r['from_ts'] = datetime_to_timeslot(from_dt, 'hour')
        r['to_ts']   = datetime_to_timeslot(to_dt,   'hour')
        del r['from']
        del r['to']

        r = super(PostsView, self).postprocess_params(r)

        if r['sort_by'] == 'time':
            r['sort_map'] = {'_created': -1}
        else:
            r['sort_map'] = {'intention_confidence': -1}

        r['min_conf'] = r['thresholds']['intention']
        if r['last_query_time'] is not None:
            r['last_query_time'] = timestamp_ms_to_datetime(r['last_query_time'])

        del r['plot_type']

        return params

    def render(self, params, request_params):
        posts, are_more_posts_available = get_posts(params)

        # Pre-fetch channels
        channel = params['channel']
        # Compute the new query time, if we don't have any then just consider
        # the current datetime, otherwise consider the same one
        last_query_time = params['last_query_time']
        if last_query_time is None and posts:
            last_query_time = datetime_to_timestamp_ms(posts[0].created_at)
        elif last_query_time is not None:
            last_query_time = datetime_to_timestamp_ms(last_query_time)

        if isinstance(channel, seq_types):
            c = list(channel)[0]
        else:
            c = channel
        results = render_posts(self.user, posts, c)
        pagination_parameters = {
            'limit': params['limit'],
            'offset': params['offset'],
            'last_query_time':  last_query_time,
            'are_more_posts_available': are_more_posts_available,
        }

        return dict(ok=True, list=results, **pagination_parameters)


class ExportPostsView(PostsView):
    url_rule = '/export/posts/json'
    SUCCESS_MSG_TPL = u"The data is being gathered. It will be emailed to " \
                      u"you (%s) in a zip file shortly."

    def get_parameters_list(self):
        params = super(ExportPostsView, self).get_parameters_list()
        is_action = lambda s: s in {'submit', 'export', 'check'}
        facets = {'agents', 'intentions', 'languages', 'all_selected',
                  'message_types', 'sentiments', 'statuses'}
        is_facet_list = lambda lst: any((x in facets for x in lst)) or not lst

        params.append(('action', basestring, is_action, 'submit'))
        # a list of facet names with *all selected
        params.append(('all_selected', seq_types, is_facet_list, []))
        return params

    def render(self, params, request_params):
        action = request_params.pop('action', 'export')

        export_task = DataExport.objects.find_one_by_user(
            self.user, input_filter=request_params)

        if action == 'check':
            return dict(ok=True, task=export_task and export_task.to_json())

        if export_task and action == 'cancel':
            export_task.change_state(DataExport.State.CANCELLED)
            return dict(ok=True, task=export_task.to_json(),
                        message='Export task has been cancelled')

        if export_task and DataExport.State.CREATED < export_task.state < DataExport.State.SENDING:
            return dict(ok=True, task=export_task.to_json(),
                        message="Export task is being processed")
        else:
            export_task = DataExport.objects.create_by_user(
                self.user,
                input_filter=request_params)

        # spawn export task
        if app.config['ON_TEST']:
            process_export_task.sync(export_task, self.user, params)
            # process_export_task(export_task, self.user, params)
        else:
            process_export_task.async(export_task, self.user, params)

        # return task details immediately
        export_task.reload()
        return dict(ok=True, task=export_task.to_json(),
                    message=self.SUCCESS_MSG_TPL % self.user.email)
