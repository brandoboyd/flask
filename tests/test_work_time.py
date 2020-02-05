import datetime

from solariat.db.abstract import Document
from solariat_bottle.db.work_time import DOW, WorkTimeMixin, TimeMark, DayOfWeek, PeriodicDate, StaticDate, dates_diff

from solariat_bottle.tests.base import MainCase, UICaseSimple


class AccountWorkHours(MainCase):

    def test_time_marks(self):

        time_marks = [{
                          "type": 'dayofweek',
                          "value": 'Mon',
                          "from": "08:00:00",
                          "to": "12:00:00"
                      },
                      {
                          "type": 'periodicdate',
                          "value": '01-12',  # Jan 12, any year
                          "from": "14:00:00",
                          "to": "23:59:59"
                      },
                      {
                          "type": 'staticdate',
                          "value": '2014-02-12',  # 2014, Feb 12
                          "from": "10:00:00",
                          "to": "20:00:00"
                      }]

        tms = map(TimeMark.from_json, time_marks)
        self.assertEqual([tm.to_json() for tm in tms], time_marks)

        dow, periodic, static = tms
        self.assertIsInstance(dow, (TimeMark, DayOfWeek))
        self.assertIsInstance(periodic, (TimeMark, PeriodicDate))
        self.assertIsInstance(static, (TimeMark, StaticDate))

        self.assertRaises(AssertionError, lambda: dow.time_points())
        self.assertRaises(AssertionError, lambda: dow.time_points('not date but str'))

        dt = datetime.datetime.now().date()
        from_date, to_date = dow.time_points(dt)
        self.assertEqual(from_date, datetime.datetime.combine(dt, datetime.time(8, 0, 0)))
        self.assertEqual(to_date, datetime.datetime.combine(dt, datetime.time(12, 0, 0)))

        from_date, to_date = periodic.time_points(year=2014)
        self.assertEqual(from_date, datetime.datetime(2014, 1, 12, 14, 0, 0))
        self.assertEqual(to_date, datetime.datetime(2014, 1, 12, 23, 59, 59))

        from_date, to_date = static.time_points()
        self.assertEqual(from_date, datetime.datetime(2014, 2, 12, 10, 0, 0))
        self.assertEqual(to_date, datetime.datetime(2014, 2, 12, 20, 0, 0))

        self.assertEqual(DayOfWeek(value='Sat'), DayOfWeek(value='Sat'))

    def test_mixin(self):

        class A(Document, WorkTimeMixin):
            pass
        
        a = A()

        def standard_schedule():
            def gen_8am7pm():
                for dow in DOW[:-2]:
                    yield {"value": dow,
                           "from": None,  # defaults to 00:00
                           "to": "08:00:00",
                           "type": 'dayofweek'}
                    yield {"value": dow,
                           "from": "19:00:00",
                           "to": None,    # defaults to 23:59:59
                           "type": 'dayofweek'}

            result = [
                DayOfWeek(value='Sat'),
                DayOfWeek(value='Sun')]
            result.extend(
                map(TimeMark.from_json, gen_8am7pm()))
            return result

        dows = standard_schedule()
        statics = [
            StaticDate(value="2014-12-15"),
            StaticDate(value="2014-12-16")
        ]
        periodics = [
            PeriodicDate(value="12-25"),
            PeriodicDate(value="01-01")
        ]

        a.off_time_schedule = dows + statics + periodics
        self.assertEqual(a.filter_time_marks(TimeMark.DAY_OF_WEEK), dows)
        self.assertEqual(a.filter_time_marks(TimeMark.PERIODIC_DATE), periodics)
        self.assertEqual(a.filter_time_marks(TimeMark.STATIC_DATE), statics)


        # test grouped by day of week
        groups = a.filter_time_marks(TimeMark.DAY_OF_WEEK, group=True)
        self.assertEquals(len(groups), len(DOW))

        # test generating time marks in dates interval
        d1 = datetime.datetime(2014, 12, 13, 7, 20, 17)
        d2 = datetime.datetime(2014, 12, 15, 14, 10, 1)

        a.time_zone = 'US/Eastern'
        time_points = a.generate_time_line(d1, d2)
        as_tz = WorkTimeMixin.as_tz
        edge_sum = 0
        for (tp, edge_mark) in time_points:
            edge_sum += edge_mark
            self.assertEqual(tp.tzinfo.zone, a.tz.zone)  # tp has a.tz timezone
            self.assertTrue(
                # tp is between d1 and d2 localized to a.tz
                as_tz(d1, a.tz).date() <= tp.date() <= as_tz(d2, a.tz).date(),
                "%s %s %s" % (as_tz(d1, a.tz), tp, as_tz(d2, a.tz)))
        self.assertEqual(edge_sum, 0)

        intervals = a.generate_intervals(d1, d2)
        sum_intervals = sum(intervals)
        self.assertTrue(dates_diff(d1, d2) > sum_intervals > 0, "%s %s" % (
            dates_diff(d1, d2), sum_intervals))

        self.assertAlmostEqual(a.schedule_aware_dates_diff(d1, d2), 0, places=5)

    def test_dates_diff(self):
        # Dec 13 2014  - Sat
        # Dec 14 2014  - Sun
        # Dec 15 2014  - Mon

        d_ = lambda s: datetime.datetime.strptime(s, '%Y/%m/%d %H:%M:%S')
        td_ = lambda **kwargs: datetime.timedelta(**kwargs).total_seconds()
        t_ = lambda s: datetime.datetime.strptime(s, '%H:%M:%S')

        class A(Document, WorkTimeMixin):
            pass

        a = A()

        test_cases = [
            # schedule                      # post datetime             # reply datetime
            ([DayOfWeek(value='Sun')],      d_('2014/12/13 12:00:00'),  d_('2014/12/15 08:00:00'),  td_(hours=12 + 8)),
            ([PeriodicDate(value='12-15')], d_('2014/12/13 12:00:00'),  d_('2014/12/15 08:00:00'),  td_(hours=12 + 24)),
            ([StaticDate(value='2012-12-15')],
                                            d_('2014/12/13 12:00:00'),  d_('2014/12/15 08:00:00'),  td_(hours=12 + 24 + 8)),
            ([StaticDate(value='2014-12-13')],
                                            d_('2014/12/13 12:00:00'),  d_('2014/12/15 08:00:00'),  td_(hours=24 + 8)),

            # one time mark fully overlapped by another
            ([StaticDate(value='2014-12-13'),
              DayOfWeek(value='Sat')],      d_('2014/12/13 12:00:00'),  d_('2014/12/15 08:00:00'),  td_(hours=24 + 8)),
            ([StaticDate(value='2014-12-13'),
              PeriodicDate(value='12-13')], d_('2014/12/13 12:00:00'),  d_('2014/12/15 08:00:00'),  td_(hours=24 + 8)),
            ([DayOfWeek(value='Sat'),
              PeriodicDate(value='12-13')], d_('2014/12/13 12:00:00'),  d_('2014/12/15 08:00:00'),  td_(hours=24 + 8)),

            # partial overlap
            ([DayOfWeek(value='Sat',      _from_time=t_('12:00:00'), _to_time=t_('22:00:00')),
              PeriodicDate(value='12-13', _from_time=t_('14:00:00'), _to_time=t_('23:00:00'))],
                                            d_('2014/12/13 11:00:00'),  d_('2014/12/15 08:00:00'),  td_(hours=1 + 1 + 24 + 8))

        ]

        for schedule, d1, d2, expected_diff in test_cases:
            a.off_time_schedule = schedule
            diff = a.schedule_aware_dates_diff(d1, d2)
            self.assertAlmostEqual(
                diff,
                expected_diff,
                places=5,
                msg="{} {} {}".format(diff, expected_diff, (d2-d1).total_seconds()))


class AccountScheduleUICase(UICaseSimple):
    def test_list_timezones(self):
        data = self._get('/timezones/json', {})
        self.assertTrue('common_timezones' in data)

    def test_list_country_timezones(self):
        data = self._get('/country_timezones/json', {})
        self.assertTrue({'country_timezones', 'country_names'} & set(data))

    def test_happy_flow(self):
        self.login()

        test_dataset = [
            [{
                 "type": 'dayofweek',
                 "value": 'Mon',
                 "from": "08:00:00",
                 "to": "12:00:00"
             },
             {
                 "type": 'periodicdate',
                 "value": '01-12',  # Jan 12, any year
                 "from": "14:00:00",
                 "to": "23:59:59"
             },
             {
                 "type": 'staticdate',
                 "value": '2014-02-12',  # 2014, Feb 12
                 "from": "10:00:00",
                 "to": "20:00:00"
             }],

            [{
                 "type": 'dayofweek',
                 "value": 'Mon',
                 "from": None,
                 "to": None
             }],

            [{
                 "type": 'periodicdate',
                 "value": '01-01',
                 "from": None,
                 "to": "14:00:00"
             }],

            []  # empty
        ]

        def run_test(time_marks):
            account = self.user.account
            data = {
                "time_zone": "UTC",
                "time_marks": time_marks
            }
            resp1 = self._post('/account/{}/schedule/json'.format(account.id), data)
            resp2 = self._get('/account/{}/schedule/json'.format(account.id), {})
            self.assertEqual(resp1, resp2)
            self.assertEqual(resp1['time_marks'], time_marks)
            self.assertEqual(resp1['time_zone'], 'UTC')

        for tm in test_dataset:
            run_test(tm)

    def test_error_flow(self):
        self.login()
        url = '/account/{}/schedule/json'.format(self.user.account.id)

        # bad account
        resp = self._get('/account/{}/schedule/json'.format("NO_SUCH_ACCOUNT"),
            {}, expected_result=False)
        self.assertEqual(resp['error'], 'Account not found')

        # bad user
        from solariat_bottle.db.roles import AGENT
        user = self._create_db_user('non_admin@test.test', roles=[AGENT])
        self.login(user=user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302) # admin_required redirects to login page,
                                                # it might be better to reply with 403 status
        self.login()

        # bad time_zone
        data = {'time_zone': 'BAD Timezone', 'time_marks': []}
        resp = self._post(url, data, expected_result=False)
        self.assertTrue("invalid: time_zone" in resp["error"])

        # bad time_marks
        bad_time_marks = [
            ([{'type': '*corrupted'}], 'Bad time mark'),
            ([{'type': 'dayofweek',
              'value': '*thisisnotadow',
              'from': None, 'to': None}], 'improper day of week value'),
            ([{'type': 'periodicdate',
              'value': '*wrongformat',
              'from': None, 'to': None}], "time data '*wrongformat' does not match format '%m-%d'"),
            ([{'type': 'staticdate',
              'value': '*wrongformat',
              'from': None, 'to': None}], "time data '*wrongformat' does not match format '%Y-%m-%d'"),
            ([{'type': 'staticdate',
              'value': '2014-12-16',
              'from': '23:00:00', 'to': '10:00:00'}], "from_time must be less than to_time")
        ]
        for (tms, error) in bad_time_marks:
            data = {'time_zone': 'US/Eastern', 'time_marks': tms}
            resp = self._post(url, data, expected_result=False)
            self.assertEqual(resp['error'], error, resp)