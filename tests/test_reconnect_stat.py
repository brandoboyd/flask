import time
from datetime import datetime, timedelta
from unittest import TestCase
from solariat.tests.base import LoggerInterceptor
from solariat_bottle.daemons.twitter.stream.reconnect_stat import ReconnectStat
now = datetime.now


class ReconnectStatForTest(ReconnectStat):

    TEN_MINUTES = timedelta(seconds=0.1)
    ONE_HOUR = timedelta(seconds=1)


class TestReconnectStat(TestCase):

    def test_stat(self):
        stat = ReconnectStatForTest()

        # check 10 minutes errors
        stat.add('mike').add('mike')
        stat.add('jessy').add('jessy')
        time.sleep(0.1)

        with LoggerInterceptor() as logs:
            stat.log_frequent_reconnects(1)

            self.assertEqual(self._10min_warning_in_logs(logs), 2)
            self.assertFalse(self._1h_warning_in_logs(logs))
            self.assertFalse(self.total_warning_in_logs(logs))

        # check 1 hours errors, raise to THRESHOLD_1H
        for _ in xrange(stat.THRESHOLD_1H - 1):
            stat.add('mike').add('mike')
            stat.add('jessy').add('jessy')
            time.sleep(0.1)
            stat.log_frequent_reconnects(1)

        time.sleep(1)
        with LoggerInterceptor() as logs:
            # emulate total reconnects count lower than threshold
            stat.log_frequent_reconnects(11)

            self.assertEqual(self._1h_warning_in_logs(logs), 2)
            self.assertFalse(self.total_warning_in_logs(logs))

        # check reset every hour
        self.assertTrue(len(stat._10min_stat) == 0)
        self.assertTrue(len(stat._1h_stat) == 0)
        self.assertTrue(len(stat._1h_errors) == 0)

        # check total thresould overrun
        for _ in xrange(stat.THRESHOLD_1H):
            stat.add('mike').add('mike')
            stat.add('jessy').add('jessy', ex=Exception('FakeException'))
            time.sleep(0.1)
            stat.log_frequent_reconnects(1)

        time.sleep(1)
        with LoggerInterceptor() as logs:
            # emulate total threshold overrun
            stat.log_frequent_reconnects(10)

            self.assertEqual(self._1h_warning_in_logs(logs), 2)
            self.assertTrue(self.total_warning_in_logs(logs))
            self.assertTrue(self.ex_output_in_logs(logs))
    
    def _10min_warning_in_logs(self, logs):
        return len([1 for log in logs if 'too often for last 10 min' in log.message])

    def _1h_warning_in_logs(self, logs):
        return len([1 for log in logs if 'too often for last hour' in log.message])

    def total_warning_in_logs(self, logs):
        return len([1 for log in logs if 'TOO MANY STREAMS RECONNECTS' in log.message])

    def ex_output_in_logs(self, logs):
        return len([1 for log in logs if 'FakeException' in log.message])

