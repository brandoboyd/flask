from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter
from flask import jsonify, render_template
import operator
from solariat_bottle.utils.views import Param, Parameters, get_paging_params
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.app import app
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.db.account import Account
from solariat.utils.timeslot import parse_datetime, datetime_to_timestamp_ms

from solariat_bottle.jobs.creator import JobStatus as JobModel
from solariat_bottle.views.facets import FacetQueryView, is_hdm_level


ENDPOINT_BASE = '/jobs/'
ACCESS_DENIED_ERROR = 'User is not authorized to perform this operation'


def gen_zeroes_timeline(from_date, to_date, level='hour'):
    from_date = from_date.replace(minute=0, second=0, microsecond=0)
    to_date = to_date.replace(minute=0, second=0, microsecond=0)
    if level != 'hour':
        from_date = from_date.replace(hour=0)
        to_date = to_date.replace(hour=0)
    from_date = datetime_to_timestamp_ms(from_date)
    to_date = datetime_to_timestamp_ms(to_date)
    while from_date <= to_date:
        yield [from_date, 0]
        if level == 'hour':
            from_date += 60 * 60 * 1000  # 1 hour in ms
        else:
            from_date += 24 * 60 * 60 * 1000  # 1 day in ms


def merge_timelines(st1, st2, merge_values=operator.add):
    """Merges 2 sorted time lines.

    :param st1: sorted iterable of time points [timestamp, value]
    :param st2: -
    :param merge_values: merging operation for values
    :return: generator of merged time lines
    """
    import heapq
    prev = (None, None)
    for time_point in heapq.merge(st1, st2):
        if prev[0] is None:
            prev = time_point
            continue
        ts, val = time_point
        assert ts >= prev[0], "%s should be <= %s" % (prev[0], ts)
        if ts == prev[0]:
            prev = [ts, merge_values(val, prev[1] or 0)]
        else:
            yield prev
            prev = time_point
    if prev[0] is not None:
        yield prev


def _get_items(id_=None):
    request_data = _get_request_data()
    ids = request_data.get('ids', request_data.get('id'))
    if ids is None:
        ids = []
    if not isinstance(ids, list):
        ids = [ids]
    if id_:
        ids.append(id_)

    return JobModel.objects.find(id__in=ids)


def to_list(maybe_list, transform=unicode):
    if not maybe_list:
        return []
    if not isinstance(maybe_list, list):
        maybe_list = [maybe_list]
    return map(transform, maybe_list)


def _parse_filters():
    request_data = _get_request_data()

    params = Parameters(
        Param('accounts', (basestring, type(None), list), Param.UNCHECKED, None),
        Param('names', (basestring, type(None), list), Param.UNCHECKED, None),
        Param('status', (basestring, type(None), list), Param.UNCHECKED, None),
        Param('from', (basestring, long, float, type(None)), Param.UNCHECKED, None),
        Param('to', (basestring, long, float, type(None)), Param.UNCHECKED, None),

        Param('limit', (basestring, int, type(None)), Param.UNCHECKED, 20),
        Param('offset', (basestring, int, type(None)), Param.UNCHECKED, 0),
    )
    params.update(request_data)
    params.check()

    def postprocess_params(data):
        filters = {}
        if data['accounts']:
            filters['account__in'] = to_list(data['accounts'], lambda x: Account.objects.get(x).id)
        if data['names']:
            filters['name__in'] = to_list(data['names'])
        if data['status']:
            filters['status__in'] = to_list(data['status'])
        if data['from']:
            filters['created_at__gte'] = parse_datetime(data['from'])
        if data['to']:
            filters['created_at__lte'] = parse_datetime(data['to'])
        return filters, get_paging_params(data)

    return postprocess_params(params.as_dict())


def check_access(user, action=None, account_id=None):
    if user.is_staff:
        return True
    else:
        if user.is_admin and (not account_id or user.account.id == account_id) and action != 'abandon':
            return True
    return False


def shorten_job_name(name, max_len=25):
    if '.' in name:
        base_name = name.rsplit('.', 1)[1]
    else:
        base_name = name
    return base_name[:max_len]


def get_facet_options(user):
    from solariat_bottle.jobs.manager import manager

    account_to_ui = lambda acct: {'id': str(acct.id), 'display': acct.name}
    facets = {}
    if user.is_staff:
        facets['accounts'] = {
            'original_title': 'Accounts',
            'title': 'All Accounts',
            'all': True,
            'list': map(account_to_ui, Account.objects.find_by_user(user))
        }
    facets['names'] = {
        'original_title': 'Job Name',
        'title': 'All Jobs',
        'all': True,
        'list': [{'id': x, 'display': shorten_job_name(x), 'tooltip': x}
                 for x in sorted(set(manager.registry.registry).union(
                set(JobModel.objects.coll.distinct(JobModel.name.db_field))))]
    }
    facets['status'] = {
        'original_title': 'Job Status',
        'title': 'All Statuses',
        'all': True,
        'list': [{'id': x, 'display': x} for x in JobModel.STATUSES]
    }
    return facets


def get_reports_options():
    options = [
        {'id': 'count',
         'title': 'Jobs Count'},
        {'id': 'time',
         'title': 'Job Duration',
         'series': ['Wait', 'Execution']}
    ]
    return options


def Response(list=None, ok=True, status=200, **kwargs):
    data = kwargs
    data.update(ok=ok)
    if list is not None:
        data.update(list=list)
    resp = jsonify(data)
    resp.status_code = status
    return resp


def to_dict(item):
    assert isinstance(item, JobModel), "%s is not %s" % (type(item), JobModel)

    def get_account_name(acct_id):
        acct = Account.objects.find_one(acct_id)
        if acct:
            return acct.name

    fields = ('id', 'account', 'status',
              'topic', 'name',
              'created_at', 'started_date', 'completion_date')
    data = item.to_dict(fields_to_show=fields)
    data.update({
        'account_name': get_account_name(item.account),
        'wait_time': item.wait_time,
        'execution_time': item.execution_time
    })
    return data


@app.route('/<any(jobs):page>')
@login_required()
def jobs_page(user, page, filter_by=None, id=None):
    return render_template("/jobs/%s.html" % page,
                           user=user,
                           section=page,
                           top_level=page)


@app.route('/jobs/partials/<page>')
@login_required()
def jobs_partials_handler(user, page):
    return render_template("/jobs/partials/%s.html" % page,
                            user=user,
                            top_level=page)


@app.route(ENDPOINT_BASE + 'facets', methods=['GET'])
@login_required
def jobs_facets(user):
    return Response(get_facet_options(user))


@app.route(ENDPOINT_BASE + 'reports/options', methods=['GET'])
@login_required
def jobs_report_options(user):
    return Response(get_reports_options())


@app.route(ENDPOINT_BASE + 'list', methods=['GET'])
@login_required
def jobs_list(user):
    try:
        filters, paging_params = _parse_filters()
    except (Account.DoesNotExist, ValueError), exc:
        return Response(status=400, ok=False, error=unicode(exc))

    account_id = filters.get('account__in') and filters.get('account__in')[0]
    # print(filters)
    if not check_access(user, 'list', account_id):
        return Response(status=403, ok=False, error=ACCESS_DENIED_ERROR)

    if user.is_admin and not user.is_staff and not filters.get('account'):
        filters['account'] = user.account.id

    pagination = slice(paging_params['offset'],
                       paging_params['offset'] + paging_params['limit'] + 1)
    items = JobModel.objects.find(**filters)\
        .sort(id=-1)[pagination]
    return Response(list=map(to_dict, items[:paging_params['limit']]),
                    more_results_available=len(items) > paging_params['limit'])


@app.route(ENDPOINT_BASE + '<action>', methods=['POST', 'PUT'])
@app.route(ENDPOINT_BASE + '<action>/<id_>', methods=['POST', 'PUT'])
@login_required
def jobs_action(user, action, id_=None):
    if action == 'list':
        return jobs_list(user=user)

    if not check_access(user, action):
        return Response(status=403, ok=False, error=ACCESS_DENIED_ERROR)

    items = list(_get_items(id_))
    for item in items:
        if not item.can_edit(user):
            return Response(status=403, ok=False, error=ACCESS_DENIED_ERROR)

    response_jobs_list = []
    try:
        if action == 'resume':
            for item in items:
                updated = item.resume()
                response_jobs_list.extend(updated)
        elif action == 'abandon':
            for item in items:
                item.abandon()
                response_jobs_list.append(item)
    except RuntimeError as e:
        return Response(action=action, ok=False, status=400, error=unicode(e))

    return Response(action=action, list=[to_dict(item) for item in response_jobs_list])


class JobsReportsView(FacetQueryView):
    url_rule = ENDPOINT_BASE + 'reports'

    @classmethod
    def register(cls, app):
        app.add_url_rule(cls.url_rule,
                         view_func=cls.as_view(cls.__name__),
                         methods=['GET', 'POST'])

    def get_parameters_list(self):
        return [
            ('from',            basestring,   Param.UNCHECKED,  Param.REQUIRED),
            ('to',              basestring,   Param.UNCHECKED,  Param.REQUIRED),
            ('level',           basestring,   is_hdm_level,     Param.REQUIRED),
            ('plot_type',       basestring,   Param.UNCHECKED,  Param.REQUIRED),
            ('plot_by',         basestring,   Param.UNCHECKED,  Param.REQUIRED),
            ('accounts', (basestring, type(None), list), Param.UNCHECKED, None),
            ('names', (basestring, type(None), list), Param.UNCHECKED, None),
            ('status', (basestring, type(None), list), Param.UNCHECKED, None),
        ]

    def postprocess_params(self, params):
        r = params
        r['from'], r['to'] = map(parse_datetime, (r['from'], r['to']))
        return params

    def prepare_match_query(self, params):
        q = {}
        F = JobModel.F

        q[F.created_at] = {'$gte': params['from'], '$lte': params['to']}
        accounts = to_list(params['accounts'], lambda x: Account.objects.get(x).id)
        if accounts:
            q[F.account] = {'$in': accounts}
        if params['names']:
            q[F.name] = {'$in': to_list(params['names'])}
        if params['status']:
            q[F.status] = {'$in': to_list(params['status'])}
        return {'$match': q}

    def prepare_projection(self, params):
        if params['plot_by'] in ('time', 'wait_time', 'execution_time'):
            F = JobModel.F
            projection = {
                'wait_time': {'$cond': [
                    {'$and': [F('$started_date'), F("$created_at")]},
                    {'$divide': [{'$subtract': [F('$started_date'), F("$created_at")]}, 1000.0]},
                    None
                ]},

                'execution_time': {'$cond': [
                    {'$and': [F('$started_date'), F("$completion_date")]},
                    {'$divide': [{'$subtract': [F('$completion_date'), F("$started_date")]}, 1000.0]},
                    None
                ]},

                'created_at': 1
            }
            return {'$project': projection}

    def prepare_group_query(self, params):
        F = JobModel.F
        created_at = F('$created_at')

        group_by_map = {
            'count': {'$sum': 1},
            'time': [
                ('Wait', {'$avg': '$wait_time'}),
                ('Execution', {'$avg': '$execution_time'}),
            ],
        }

        timeline_level = params['level']
        if timeline_level == 'hour':
            time_group = {"year": {'$year'     : created_at},
                          "day" : {'$dayOfYear': created_at},
                          "hour": {'$hour'     : created_at}}
        elif timeline_level == 'day':
            time_group = {"year": {'$year'     : created_at},
                          "day" : {'$dayOfYear': created_at}}
        elif timeline_level == 'month':
            time_group = {"year": {'$year'     : created_at},
                          "month": {'$month'   : created_at},
                          "day" : {'$dayOfYear': created_at}}
        else:
            raise Exception("Unknown level %s" % timeline_level)

        group_dict = {
            '$group': {
                "_id": time_group,
            }
        }
        computed_metric = params['plot_by']

        if isinstance(group_by_map[computed_metric], list):
            for field, field_value in group_by_map[computed_metric]:
                group_dict['$group'][field] = field_value
        else:
            group_dict['$group'][computed_metric] = group_by_map[computed_metric]

        return group_dict

    def prepare_plot_result(self, params, result):
        computed_metric = params['plot_by']
        if params['plot_type'] == 'time':
            helper_structure = defaultdict(list)
            for entry in result:
                date = datetime(year=entry['_id']['year'], month=1, day=1)
                date = date + timedelta(days=entry['_id']['day'] - 1)
                if 'hour' in entry['_id']:
                    date = date + timedelta(hours=entry['_id']['hour'])
                timestamp = datetime_to_timestamp_ms(date)

                if computed_metric == 'time':
                    for each in ['Wait', 'Execution']:
                        helper_structure[each].append([timestamp, entry[each]])
                else:
                    helper_structure[computed_metric].append([timestamp, entry[computed_metric]])

            result = []
            sort_by_timestamp = lambda values: sorted(values, key=itemgetter(0))
            for key, value in helper_structure.viewitems():
                result.append(dict(label=key, data=sort_by_timestamp(value)))
        return result

    def fill_time_line(self, data, params):
        # filter(lambda (ts, val): val, data)
        return list(merge_timelines(
            data,
            list(gen_zeroes_timeline(params['from'], params['to'], params['level']))))

    def compute_trends_data(self, params):
        pipeline = [q for q in (
            self.prepare_match_query(params),
            self.prepare_projection(params),
            self.prepare_group_query(params)) if q]

        result = JobModel.objects.coll.aggregate(pipeline)['result']
        result = self.prepare_plot_result(params, result)

        for each in result:
            data = each['data']
            each['data'] = self.fill_time_line(data, params)
            each['average'] = sum(l[1] for l in data) / float(len(data))
            # each['model'] = model_data
            # each['label'] = each['label'] + ':' + model_data['display_name']

        return result

    def render(self, params, request_params):
        return dict(ok=True, list=self.compute_trends_data(params))


JobsReportsView.register(app)
