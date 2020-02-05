# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from datetime import timedelta

from flask import request
from flask.views import View

from solariat_nlp.sa_labels import SATYPE_NAME_TO_ID_MAP
from solariat_nlp.sentiment import all_sentiments, translate_sentiments_to_intentions
from solariat.utils.lang.support import LANG_MAP, get_lang_code
from solariat.utils.timeslot import datetime_to_timestamp_ms, parse_date_interval, Timeslot

from solariat_bottle.app import app
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.journeys.journey_type import JourneyStageType
from solariat_bottle.db.post.base import Post
from solariat_bottle.db.speech_act import SpeechActMap
from solariat_bottle.db.user import User
from solariat_bottle.utils.decorators import login_required, timed_event
from solariat_bottle.utils.id_encoder import ALL_TOPICS
from solariat_bottle.utils.views import Parameters, Param, datetime_re, date_re, jsonify_response as jsonify


# --- predicates used by param validation code in views ---
str_or_none = (basestring, type(None))
list_or_none = (list, tuple, type(None))
int_or_none = (int, type(None))
list_or_str = (list, basestring)
long_or_none = (long, int, type(None))
dict_or_none = (dict, type(None))

is_date = date_re.match
is_date_or_none = lambda v: v is None or is_date(v)
is_datetime = lambda v: datetime_re.match(v) or date_re.match(v)
is_datetime_or_none = lambda v: v is None or is_datetime(v)

is_non_negative_int_or_none = lambda v: (
    (v is None) or (isinstance(v, int) and v >= 0)
)
is_long_or_none = lambda v: (
    (v is None) or isinstance(v, long) or isinstance(v, int)
)

is_intention = lambda v: v in SATYPE_NAME_TO_ID_MAP
is_p_status = lambda v: v in {'actionable', 'actual', 'potential', 'rejected'}
is_hdm_level = lambda v: v in {'hour', 'day', 'month', None}
is_journey_metric = lambda v: v in {'count', 'nps', 'csat', None}
is_nps = lambda v: v is None or set(v).intersection({'promoter', 'detractor', 'passive', 'n/a', None}) == set(v)
is_boolean_string_or_none = lambda v: v in ('true', 'false', None)
is_dm_level = lambda v: v in {'day', 'month'}
is_topic_desc = lambda v: (
    isinstance(v, dict)
    and isinstance(v.get('topic'), basestring)
    and v.get('topic_type') in {'leaf', 'node'}
)
is_threshold_map = lambda v: all(
    (isinstance(v.get(key), (float, int)) and (0 <= v[key] <= 1.0))
    for key in ['intention']  # ['influence','receptivity']
)
is_group_by = lambda v: v in {'topic', 'sentiment', 'intention', 'status', 'agent', 'lang', 'time', None}
is_plot_type = lambda v: v in {
    'inbound-volume', 'response-time', 'response-volume',  # partial reports
    'missed-posts', 'sentiment', 'top-topics',  # extended reports
    'topics',  # analytics plots
}
is_plot_by = lambda v: v in {'time','distribution'}
is_sort_by = lambda v: v in {'time','confidence'}
is_topic_plot = lambda v: v in {'sentiment', 'top-topics', 'topics', 'missed-posts'}
is_partial_trend = lambda v: v in {
    'response-time', 'response-volume', 'inbound-volume'}
is_problem = lambda v: v in {'top-topics'}

is_cloud_type = lambda v: v in {'none', 'delta', 'percent'}
is_cloud_type_or_none = lambda v: v is None or is_cloud_type(v)
is_language_code = lambda v: get_lang_code(v) in LANG_MAP  # allows lang code or name ("en"|"English")
is_labeling_strategy = lambda v: v in {'default', 'channel', 'event', None}

all_p_statuses  = lambda l: all(map(is_p_status,   l or []))
all_intentions  = lambda l: all(map(is_intention,  l or []))
all_topic_descs = lambda l: all(map(is_topic_desc, l or []))
all_languages   = lambda l: all(map(is_language_code, l or []))

ALL_TOPICS_desc = dict(topic=ALL_TOPICS, topic_type='node')

default_statuses_by_plot_type = {
    'response-time': [SpeechActMap.ACTUAL],
    'response-volume': [SpeechActMap.ACTUAL],
    'sentiment': [SpeechActMap.ACTIONABLE, SpeechActMap.ACTUAL],
    'missed-posts': [SpeechActMap.ACTIONABLE],
    'inbound-volume': [SpeechActMap.ACTIONABLE, SpeechActMap.ACTUAL],
    'top-topics': [SpeechActMap.ACTIONABLE, SpeechActMap.ACTUAL],
}


# --- utils ---
seq_types = (list, tuple, set)

def get_channels(user, channel_id):
    """
    :param user:
    :param channel_id: can be a list or a string

    :returns result: a list or just a single Channel object
    """
    if isinstance(channel_id, seq_types):
        result = []
        for c_id in channel_id:
            result.append(Channel.objects.get_by_user(user, id=c_id))
    else:
        result = Channel.objects.get_by_user(user, id=channel_id)
    return result


def get_statuses(statuses, plot_type):
    '''
    If statuses are provided, use them. Otherewise we can look for
    report specific defaults.
    '''
    return statuses or default_statuses_by_plot_type.get(plot_type,
                                                         [SpeechActMap.POTENTIAL,
                                                          SpeechActMap.ACTIONABLE,
                                                          SpeechActMap.ACTUAL,
                                                          SpeechActMap.REJECTED])


def get_agents(user, user_ids):
    # If we filter by account here, then all filters by deleted agents
    # will result in an empty list and thus an invalid filter  (basically
    # all agents will be considered when filtering by a deleted one)
    # Since we already have a channel_id when retrieving data which is
    # binding to an account, I believe we can skip this.
    #if user.account:
    #    agents = user.account.get_users(id__in=user_ids, agent_id__ne=0)
    #else:
    #    agents = User.objects(id__in=user_ids, agent_id__ne=0)
    #return agents[:]
    return User.objects(id__in=user_ids, agent_id__ne=0)[:]


def set_languages_param(r, default=None):
    """Sets up languages list.
    If list from UI is empty - fill it with current channel languages
    :param r: mutated request parameters dict
    """
    lang_key = 'languages'
    if lang_key in r:
        if r[lang_key]:
            r[lang_key] = [get_lang_code(lang) for lang in r[lang_key]]
        else:
            channel = r['channel']
            if default is not None:
                r[lang_key] = default
            elif hasattr(channel, 'langs'):
                r[lang_key] = r['channel'].langs


def nps_label_to_values(label):
    if label == 'promoter':
        return [9, 10]
    elif label == 'passive':
        return [7, 8]
    elif label == 'detractor':
        return [0, 1, 2, 3, 4, 5, 6]
    elif label == 'n/a':
        return [None]
    else:
        raise Exception("invalid nps label (%r given)" % label)


def nps_value_to_label(value):
    if value is None:
        return 'n/a'
    elif 0 <= value <= 6:
        return 'detractor'
    elif value in (7, 8):
        return 'passive'
    elif value in (9, 10):
        return 'promoter'
    else:
        raise Exception("invalid nps value (%r given)" % value)


class FacetQueryView(View):
    methods = ['POST']
    url_rule = None

    # Note for flask 0.8+: this should work instead of overriding as_view():
    # decorators = [login_required, timed_event]
    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        view = super(FacetQueryView, cls).as_view(name, *class_args, **class_kwargs)
        return login_required(timed_event(view))

    def get_parameters_list(self):
        return [
            #name            valid_types   valid_values     value
            #--------------  -----------   ---------------  --------------
            ('channel_id',   list_or_str,  Param.UNCHECKED, Param.REQUIRED),
            ('from',         basestring,   is_date_or_none, None),
            ('to',           str_or_none,  is_date_or_none, None),
            ('level',        basestring,   is_dm_level,     'day'),
            ('sentiments',   list_or_none, all_sentiments,  None),
            ('intentions',   list_or_none, all_intentions,  None),
            ('statuses',     list_or_none, all_p_statuses,  []),
            ('agents',       list_or_none, Param.UNCHECKED, []),
            ('plot_type',    basestring,   is_plot_type,    'topics'),
            ('languages',    list_or_none, all_languages, None),
        ]

    def postprocess_params(self, params):
        r = params
        if 'channel_id' in r:
            r['channel'] = get_channels(self.user, r['channel_id'])
            set_languages_param(r)

        if 'from' in r and 'to' in r:
            from_date = r['from']
            to_date   = r['to'] or from_date
            from_dt, to_dt = parse_date_interval(from_date, to_date)
            r['from_ts'] = Timeslot(from_dt, r['level'])
            r['to_ts']   = Timeslot(to_dt,   r['level'])

        r['agents'] = get_agents(self.user, r['agents'] or [])

        r['statuses'] = get_statuses(r['statuses'], r['plot_type'])

        if r['sentiments'] is not None:
            assert r['intentions'] is None, 'intentions and sentiments cannot be set together'
            r['intentions'] = translate_sentiments_to_intentions(r['sentiments'])

        # for some reports we show only problem posts
        if is_problem(r['plot_type']):
            r['intentions'] = [SATYPE_NAME_TO_ID_MAP['problem']]

        # -- cleanup --
        del r['channel_id']
        r.pop('from', None)
        r.pop('to', None)
        del r['sentiments']
        del r['level']

        return params

    def validate_params(self, data=None):
        if data is None and not hasattr(request, 'json'):
            raise RuntimeError('no json parameters provided')

        params = Parameters(*[Param(*p) for p in self.get_parameters_list()])
        params.update(data or request.json)
        params.check()
        return params.as_dict()

    def render(self, params, request_params):
        raise NotImplemented

    def dispatch_request(self, *args, **kwargs):
        """
        :param user: authenticated user, provided by login_required decorator
        """
        self.user = kwargs.get('user')

        try:
            valid_request_params = self.validate_params()
            params = self.postprocess_params(valid_request_params.copy())
            result = self.render(params, valid_request_params)
        except Exception, exc:
            app.logger.error('error on %s' % self.url_rule, exc_info=True)
            return jsonify(ok=False, error=str(exc)), 500
        else:
            return jsonify(result)

    def fill_multi_series_with_zeroes(self, multi_series, from_date=None, to_date=None):
        """
        Fills missing timestamp data in multi-series data,
        so that all series contain same timestamp data
        """
        if from_date and to_date:
            all_timestamps = []
            start_date = from_date
            while start_date <= to_date:
                all_timestamps.append(datetime_to_timestamp_ms(start_date))
                start_date = start_date + timedelta(hours=24)
        else:
            all_timestamps = set()
            for series in multi_series:
                all_timestamps.update(each[0] for each in series['data'])

            all_timestamps = sorted(all_timestamps)

        for series in multi_series:
            series_timestamps = [each[0] for each in series['data']]
            for i, timestamp in enumerate(all_timestamps):
                if timestamp not in series_timestamps:
                    series['data'].insert(i, [timestamp, 0])


def get_posts(params):
    return Post.objects.by_time_point(
        params['channel'],
        params['topics'],
        params['from_ts'],
        params['to_ts'],
        status=set(params['statuses'] or []) | set(params['assignments'] or []),
        intention=params['intentions'],
        min_conf=params['min_conf'],
        agents=params['agents'],
        languages=params['languages'],
        sort_by=params['sort_by'],
        message_type=params['message_type'],
        offset=params['offset'],
        limit=params['limit'],
        last_query_time=params['last_query_time']
    )


@app.route('/journeys/facet_options', methods=['GET'])
@login_required
def journey_facet_options(user):
    opts = {
        "journey_type": {
            "stageStatuses": [{"id": status, "text": text} for status, text in JourneyStageType.STATUS_TEXT_MAP.items()]
        }
        # ,
        # "customer_segments": {
        #     "options": [{"id": str(seg.id), "text": seg.display_name} for seg in CustomerSegment.objects()]
        # }
    }
    return jsonify(opts)


def parse_param_ranges(ranges, key):
    query = {'$or': []}
    for i, range_ in enumerate(ranges):
        gte, lte = map(str.strip, range_.split('-'))

        key_condition = {}
        if gte:
            key_condition['$gte'] = int(gte)
        if lte:
            key_condition['$lte'] = int(lte)

        query['$or'].append({key: key_condition})
    return query


from .interactions import HotTopicsView, TrendsView, PostsView, ExportPostsView


# DROPPING BECAUSE IT IS HARDWIRED
from .customers import CustomersView
from .agents import AgentsView

from .journeys import JourneyDetailsView, JourneyPlotsView
from .sankey import JourneySankeyView
from .most_common_path import JourneyMCPView
from .funnel import FunnelFacetView, FunnelStageStatisticView
from .predictors import PredictorsView
from .crossfilter import CrossFilterView
from . import dynamic_filters


class_views = [
        TrendsView, HotTopicsView, PostsView, ExportPostsView,  # Analytics Tab
        CustomersView,                                          # Customers Tab
        AgentsView,                                             # Agents Tab
        JourneyPlotsView, JourneyDetailsView,                   # Journeys Trends/Distribution, Details Tab
        JourneySankeyView,                                      # Journeys Paths Tab
        JourneyMCPView,                                         # Journeys MCP Tab
        FunnelFacetView, FunnelStageStatisticView,              # Journeys Funnels Tab

        PredictorsView,                                         # Predictors Metrics Tab
        CrossFilterView,                                        # CrossFilter data
]


for cls_view in class_views:
    app.add_url_rule(cls_view.url_rule,
                     view_func=cls_view.as_view(cls_view.__name__))
