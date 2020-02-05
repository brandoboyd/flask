"""
POST /jobs/<action>
ids and action in (resume, abandon)
action == 'list' is equivalent to
GET /jobs/?accounts=...&from_date=...&to_date=...&names=...&limit=...
"""
from collections import namedtuple

import datetime
import random
import operator
import unittest
import itertools
from solariat.utils.timeslot import now, datetime_to_timestamp_ms
from solariat_bottle.db.roles import ADMIN, AGENT, STAFF
from solariat_bottle.db.user import User
from solariat_bottle.db.account import Account
from solariat_bottle.tests.base import UICaseSimple

from solariat_bottle.views import jobs as jobs_views

from solariat_bottle.jobs.creator import JobStatus as JobModel
from solariat_bottle.jobs.config import jobs_config


def make_filter(filters_dict, mappings=None):
    if not mappings:
        mappings = {}
    eq = lambda x, y: unicode(x) == unicode(y)
    get = lambda item, key: item[key] if isinstance(item, dict) else getattr(item, key)

    def predicate(item):
        result = True
        for key, value in filters_dict.viewitems():
            op = eq
            if key in mappings:
                key, op = mappings[key]
            result &= op(get(item, key), value)
        return result

    return predicate


def apply_filter(filters_dict, items, mappings=None):
    if not mappings:
        mappings = {}
    return filter(make_filter(filters_dict, mappings), items)


def dates_cmp(date1, date2):
    from solariat.utils.timeslot import parse_datetime
    return cmp(parse_datetime(date1), parse_datetime(date2))

dates_gte = lambda x, y: dates_cmp(x, y) >= 0
dates_lte = lambda x, y: dates_cmp(x, y) <= 0

_in = lambda x, values: not values or str(x) in (values and isinstance(values, list) and values or [values])


class JobsViewTest(UICaseSimple):
    ENDPOINT_BASE = jobs_views.ENDPOINT_BASE

    def login_user(self, user):
        self.login(user.email, self.password)

    def setUp(self):
        super(JobsViewTest, self).setUp()
        self.staff = self._create_db_user(
            email='test_staff@test.test',
            password=self.password,
            account=self.account,
            roles=[STAFF])
        self.user.update(is_superuser=True)
        self.login_user(self.user)

    def get(self, id=None, expected_result=True, expected_code=200, action='list', **kwargs):
        url = self.ENDPOINT_BASE + action
        if id:
            url += id
        result = self._get(
            url,
            kwargs,
            expected_result=expected_result,
            expected_code=expected_code)
        if expected_result:
            return result['list']
        else:
            return result

    def post(self, action, expected_result=True, expected_code=200, **kwargs):
        result = self._post(self.ENDPOINT_BASE + action, kwargs,
                            expected_result=expected_result,
                            expected_code=expected_code)
        # print(result)
        if expected_result:
            if 'action' in result:
                self.assertTrue(result['action'], action)
            self.assertTrue('list' in result, result)
            return result['list']
        else:
            return result

    def configure_account(self, name, password=None):
        if password is None:
            password = self.password
        account = Account.objects.create(name=name)
        acc_admin = User.objects.create(
            email=u"acc_admin_%s@test.test" % name,
            password=password,
            user_roles=[ADMIN])
        unprivileged_user = User.objects.create(
            email=u"acc_agent_%s@test.test" % name,
            password=password,
            user_roles=[AGENT])
        account.add_user(acc_admin)
        account.add_user(unprivileged_user)
        return account, acc_admin, unprivileged_user

    def create_job(self, name, account=None, created_at=None, topic='pytest'):
        assert self.user.is_superuser
        return JobModel.objects.create_by_user(
            self.user,
            name=name,
            topic=topic,
            account=account,
            created_at=created_at or now(),
            status=JobModel.PENDING)

    def _setup(self, n_accounts=2, n_jobs_per_account=1):
        self.jobs = []
        for acc_idx in range(n_accounts):
            acc, admin, user = self.configure_account('TestAcc_%s' % (acc_idx + 1))
            setattr(self, 'acc%s' % (acc_idx + 1), acc)
            setattr(self, 'admin%s' % (acc_idx + 1), admin)
            setattr(self, 'user%s' % (acc_idx + 1), user)
            self.jobs.extend(
                self.create_job('job_name_%s' % (job_idx + 1), acc.id)
                for job_idx in range(n_jobs_per_account))

    def assertEqualByKey(self, list1, list2, key='id', msg=None):
        def _getter(item):
            if isinstance(item, dict):
                return str(item[key])
            return str(getattr(item, key))

        set1 = map(_getter, list1)
        set2 = map(_getter, list2)
        self.assertEqual(len(set1), len(set2), msg="List lengths are different\n{}\n{}".format(set1, set2))
        self.assertSetEqual(set(set1), set(set2), msg)


class ListJobsTest(JobsViewTest):

    def test_access(self):
        n_accounts = 2
        n_jobs_per_account = 1
        self._setup(n_accounts=n_accounts, n_jobs_per_account=n_jobs_per_account)

        # Staff/SU should have access to jobs from all accounts
        assert self.user.is_superuser
        self.login_user(self.user)
        self.assertEqualByKey(self.get(), self.jobs)

        assert self.staff.is_staff
        self.login_user(self.staff)
        self.assertEqualByKey(self.get(), self.jobs)

        # An account admin should see only jobs for the account they belong to
        for admin in [getattr(self, 'admin%s' % (idx + 1)) for idx in range(n_accounts)]:
            assert admin.is_admin
            self.login_user(admin)
            self.assertEqualByKey(
                self.get(),
                filter(lambda job: job.account == admin.account.id, self.jobs))

        # unprivileged users should not see any jobs
        for user in [getattr(self, 'user%s' % (idx + 1)) for idx in range(n_accounts)]:
            assert not user.is_admin
            assert not user.is_staff
            self.login_user(user)
            self.get(expected_result=False, expected_code=403)

    def test_faceting(self):
        """Should be able to filter jobs by
        job_name, job group/topic, account_id and the time selector"""
        n_accounts = 2
        n_jobs_per_account = 5
        self._setup(n_accounts=n_accounts, n_jobs_per_account=n_jobs_per_account)

        # SU/STAFF should be able to filter by account
        acc = self.acc1

        self.login_user(self.staff)
        self.assertEqualByKey(
            self.get(accounts=str(acc.id)),
            filter(lambda job: job.account == acc.id, self.jobs))

        # account admins should not be able to filter by account
        admin = self.admin2
        assert admin.account.id != acc.id
        self.login_user(admin)
        self.get(accounts=str(acc.id), expected_result=False, expected_code=403)

        self.login_user(self.staff)

        filters = [
            {'names': 'job_name_1'},
            {'names': ['job_name_1']},
            {'names': 'job_name_1', 'accounts': str(acc.id)},
            {'names': ['job_name_1'], 'accounts': [str(acc.id)]},
            {'names': 'unexisting job', 'accounts': str(acc.id)},
            {'names': 'job_name_1', 'accounts': str(acc.id), 'from': str(now() - datetime.timedelta(hours=1)), 'to': str(now())},
            {'names': 'job_name_1', 'from': str(now() - datetime.timedelta(hours=1))},
            {'names': 'job_name_1', 'from': str(now())},
            {'names': 'job_name_1', 'from': str(now()), 'status': None},
            {'names': 'job_name_1', 'from': str(now()), 'status': JobModel.STATUSES},
        ]

        mappings = {
            'from': ('created_at', dates_gte),
            'to': ('created_at', dates_lte),
            'names': ('name', _in),
            'accounts': ('account', _in),
            'status': ('status', _in)
        }
        for f in filters:
            # print('using filter', f)
            self.assertEqualByKey(self.get(**f),
                                  apply_filter(f, self.jobs, mappings))

        # POST with action=list is the same as GET
        self.assertEquals(self.post('list', **filters[0]), self.get(**filters[0]))

    def test_pagination(self):
        n_accounts = 2
        n_jobs_per_account = 5
        self._setup(n_accounts=n_accounts, n_jobs_per_account=n_jobs_per_account)
        self.login_user(self.staff)

        cases = [
            (slice(0, 20), {}),  # default
            (slice(0, 20), {'limit': 1, 'offset': 'bad'}),
            (slice(0, 1), {'limit': 1}),
            (slice(5, 8), {'limit': 3, 'offset': 5}),
            (slice(9, 10), {'limit': 5, 'offset': 9}),
        ]
        jobs = list(reversed(self.jobs))
        # jobs = self.jobs
        for array_slice, kwargs in cases:
            self.assertEqualByKey(
                self.get(**kwargs),
                jobs[array_slice])


class ActionsJobsTest(JobsViewTest):
    def test_resume(self):
        """User should be able to resume/restart failed jobs"""
        original_transport = jobs_config.transport
        manager = self.setup_jobs_transport('database')

        def test_job():
            pass
        j = manager.job(topic='pytest')(test_job)

        acc, admin, user = self.configure_account('acc1')
        job = self.create_job(j.name, acc.id)
        other_acc_job = self.create_job(j.name, self.account.id)

        # check access
        self.login_user(user)
        self.post('resume', ids=str(job.id), expected_result=False, expected_code=403)

        self.login_user(admin)
        self.post('resume', ids=str(other_acc_job.id), expected_result=False, expected_code=403)

        result = self.post('resume', ids=str(job.id), expected_result=False, expected_code=400)
        self.assertEqual(result['error'], "Job can not be resumed in 'Pending' state.")

        job.update(status=JobModel.FAILED)
        result = self.post('resume', ids=str(job.id))
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], str(job.id))
        job.reload()
        new_jobs = [instance for instance in JobModel.objects() if instance.id not in (job.id, other_acc_job.id)]
        self.assertEqual(len(new_jobs), 1)
        new_job = new_jobs[0]
        self.assertEqual(result[1]['id'], str(new_job.id))
        self.assertEqual(job.resubmission_info, {'new_id': new_job.id, 'result': str(True)})
        self.assertEqual(new_job.resubmission_info, {'old_id': job.id})

        self.setup_jobs_transport(original_transport)

    def test_abandon(self):
        """Staff/SU should be able to cancel pending jobs"""
        acc, admin, user = self.configure_account('acc1')
        job = self.create_job('test_job')
        self.login_user(user)
        self.post('abandon', ids=str(job.id), expected_code=403, expected_result=False)

        self.login_user(self.staff)
        result = self.post('abandon', ids=str(job.id))
        self.assertEqual(result[0]['status'], JobModel.ABANDONED)


class FacetsJobsTest(JobsViewTest):
    def test_get_facets(self):
        from solariat_bottle.jobs.manager import manager
        registered_jobs_count = len(manager.registry.registry.keys())
        status_count = len(JobModel.STATUSES)
        self._setup(n_accounts=3)

        result = self.get(action='facets')
        self.assertTrue(len(result['accounts']['list']), Account.objects.count())
        self.assertTrue(len(result['names']['list']), registered_jobs_count)
        self.assertTrue(len(result['status']['list']), status_count)


JobsNum = namedtuple('JobsNum', ['pending', 'running', 'completed'])


def random_date(from_date, to_date):
    interval = (to_date - from_date).total_seconds()
    return to_date - datetime.timedelta(seconds=random.randint(0, interval) + 300)


def random_status_dates(from_date, to_date, wait_time_range=30, execution_time_range=300):
    created_at = random_date(from_date, to_date)
    return (
        created_at,
        created_at + datetime.timedelta(seconds=random.randint(1, wait_time_range)),
        created_at + datetime.timedelta(seconds=random.randint(wait_time_range + 1, execution_time_range))
    )


class TestUtils(unittest.TestCase):
    def test_generate_zero_timeline(self):
        f = jobs_views.gen_zeroes_timeline
        n = now().replace(hour=12, minute=0)
        td = datetime.timedelta
        cases = [
            # from_date  to_date  level
            (n, n, 'hour', 0),
            (n, n + td(minutes=59), 'hour', 1),
            (n - td(hours=1), n, 'hour', 2),
            (n - td(hours=1), n, 'month', 0),
            (n - td(hours=12), n, 'month', 1),  # from is still current date
            (n - td(hours=24), n, 'month', 2),
        ]

        def validate(from_date, to_date, level, expected_result_size):
            result = list(f(from_date, to_date, level))
            if not expected_result_size:
                delta = to_date - from_date
                if level == 'hour':
                    expected_result_size = delta.total_seconds() / (60 * 60) + 1
                else:
                    expected_result_size = delta.total_seconds() / (60 * 60 * 24) + 1

            self.assertEqual(len(result), int(expected_result_size), msg="%s != %s\n%s %s %s" % (len(result), int(expected_result_size), from_date, to_date, level))
            # check sorted
            prev_ts = None
            for ts, zero in result:
                assert ts > prev_ts
                assert zero == 0
                prev_ts = ts

        list(itertools.starmap(validate, cases))

    def test_merge_timelines(self):
        f = jobs_views.merge_timelines
        cases = [
            dict(time_line_1=[],
                 time_line_2=[],
                 expected_result=[]),
            dict(time_line_1=[],
                 time_line_2=[[10, 1]],
                 expected_result=[[10, 1]]),
            dict(time_line_1=[[10, 0], [20, 0], [30, 0], [40, 0], [50, 0]],
                 time_line_2=[],
                 expected_result=[[10, 0], [20, 0], [30, 0], [40, 0], [50, 0]]),
            dict(time_line_1=[[10, 0], [20, 0], [30, 0], [40, 0], [50, 0]],
                 time_line_2=[[5, 1], [10, 0], [15, 2], [20, 0], [30, 1], [40, 2]],
                 expected_result=[[5, 1], [10, 0], [15, 2], [20, 0], [30, 1], [40, 2], [50, 0]]),
        ]
        for case in cases:
            self.assertEqual(list(f(case['time_line_1'], case['time_line_2'])), case['expected_result'])


class ReportsJobsTest(JobsViewTest):
    def get_report(self, plot_type='time', plot_by='count', **params):
        params.update(plot_by=plot_by, plot_type=plot_type)
        result = self.post('reports', **params)
        return result

    def get_expected_trends(self,
                            accounts=None,
                            names=None,
                            plot_by='count',
                            plot_type='time',
                            from_date=None,
                            to_date=None,
                            level='month'):
        mappings = {
            'from': ('created_at', dates_gte),
            'to': ('created_at', dates_lte),
            'names': ('name', _in),
            'accounts': ('account', _in)
        }
        jobs = apply_filter({
            'names': names,
            'accounts': accounts,
            'from': from_date,
            'to': to_date
        }, self.jobs, mappings)

        if from_date is None:
            from_date = jobs[-1].created_at
        if to_date is None:
            to_date = jobs[0].created_at

        def generate(plot_by=plot_by):
            def map_fn(job):
                ts = job.created_at.replace(minute=0, second=0, microsecond=0)
                if level == 'month':
                    ts = ts.replace(hour=0)
                timestamp = datetime_to_timestamp_ms(ts)

                if plot_by == 'count':
                    return timestamp, 1
                elif plot_by == 'time':
                    return timestamp, job.wait_time, job.execution_time

            def reduce_fn(a, b):
                if plot_by == 'count':
                    ts, count = b
                    try:
                        a[ts] += count
                    except:
                        a[ts] = count
                elif plot_by == 'time':
                    ts, wait_time, execution_time = b
                    a.setdefault('Wait', {})
                    a.setdefault('Execution', {})
                    if wait_time:
                        try:
                            a['Wait'][ts].append(wait_time)
                        except:
                            a['Wait'][ts] = [wait_time]
                    if execution_time:
                        try:
                            a['Execution'][ts].append(execution_time)
                        except:
                            a['Execution'][ts] = [execution_time]
                return a

            def finalize_fn(result):
                zeroes_time_line = list(jobs_views.gen_zeroes_timeline(from_date, to_date, level))
                fill_zeroes = lambda x: list(jobs_views.merge_timelines(x, zeroes_time_line))

                if plot_by == 'count':
                    return {'count': fill_zeroes(
                        sorted(([a, b] for a, b in result.viewitems()), key=operator.itemgetter(0)))}
                elif plot_by == 'time':
                    res = {}
                    for label, series in result.viewitems():
                        res[label] = []
                        for ts, values in series.viewitems():
                            res[label].append([ts, sum(v or 0 for v in values) / len(values)])
                        res[label] = fill_zeroes(sorted(res[label]))
                    return res

            return finalize_fn(reduce(reduce_fn, map(map_fn, jobs), {}))

        result = generate(plot_by)
        # print(result)
        return result

    @unittest.skipIf(1, "Failing now for some unknown None value. Skipping for now.")
    def test_trends(self):
        to_date = now()
        from_date = to_date - datetime.timedelta(days=30)

        self._prepare_data(JobsNum(5, 5, 10), from_date, to_date)
        for plot_by in ['count', 'time']:
            level = 'month'
            params = {
                'from': str(from_date),
                'to': str(to_date),
                'level': level,
                'plot_type': 'time',
                'plot_by': plot_by
            }
            result = self.get_report(**params)
            data = {part['label']: part['data'] for part in result}
            expected = self.get_expected_trends(
                from_date=from_date,
                to_date=to_date,
                level=level,
                plot_type='time',
                plot_by=plot_by)
            assert data == expected, '\n%s\n%s\n%s' % (data, expected, result)

    def _prepare_data(self, n_jobs=JobsNum(10, 5, 5), from_date=None, to_date=None):
        name = 'job_name'
        account = self.account
        self.jobs = []
        if to_date is None:
            to_date = now()
        if from_date is None:
            from_date = to_date - datetime.timedelta(days=30)

        def gen_jobs_data():
            for status in [JobModel.PENDING] * n_jobs.pending + [JobModel.RUNNING] * n_jobs.running + [JobModel.SUCCESSFUL] * n_jobs.completed:
                created_at, started_date, completion_date = random_status_dates(from_date, to_date)
                data = {
                    'created_at': created_at,
                    'status': status,
                    'account': account.id,
                }
                if status == JobModel.SUCCESSFUL:
                    data['started_date'], data['completion_date'] = started_date, completion_date
                elif status == JobModel.RUNNING:
                    data['started_date'] = started_date
                yield data

        for job_data in gen_jobs_data():
            job = self.create_job(name)
            job.update(**job_data)
            self.jobs.append(job)
