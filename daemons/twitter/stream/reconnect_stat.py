from solariat_bottle.settings import LOGGER
from collections import defaultdict
from datetime import datetime, timedelta
now = datetime.utcnow


class ReconnectStat(object):

    THRESHOLD_10MIN = 2  # 2 reconnects for a 10 minutes
    THRESHOLD_1H = 3  # 3 fired THRESHOLD_10MIN for last hour
    THRESHOLD_TOTAL = 0.2  # 20 % of streams did reconnect
    TEN_MINUTES = timedelta(minutes=10)
    ONE_HOUR = timedelta(hours=1)

    def __init__(self):
        self._10min_stat = defaultdict(list)    # list of typles (datetime, exception)
        self._1h_stat = defaultdict(int)        # counter of 10 min threshould overruns
        self._1h_errors = defaultdict(list)
        self._1h_total_warnings = 0             # counter for total streams 1h threshold overruns
        self._last_10min_check = now()
        self._last_1h_check = now()
        self._streams_count = 0

    def add(self, key, at=None, ex=None):
        self._10min_stat[key].append((at or now(), ex))
        return self

    def update_streams_count(self, count):
        self._streams_count = max(self._streams_count, count)

    def check_10min_interval(self, streams_count):
        _now = now()
        if _now - self._last_10min_check < self.TEN_MINUTES:
            return

        self.update_streams_count(streams_count)

        for key, reconn_errors in self._10min_stat.viewitems():
            reconn_count = len(reconn_errors)
            if reconn_count >= self.THRESHOLD_10MIN:
                self._1h_stat[key] += 1
                errors = [item[1] for item in reconn_errors if item[1] is not None]
                self._1h_errors[key].extend(errors)
                LOGGER.warning('[%s] reconnects happens too often for last 10 min: %s' %
                               (key, errors))

        self._last_10min_check = now()
        self._10min_stat.clear()

    def check_1h_interval(self, streams_count):
        _now = now()
        if _now - self._last_1h_check < self.ONE_HOUR:
            return

        self.update_streams_count(streams_count)

        for key, errors_cnt in self._1h_stat.viewitems():
            if errors_cnt >= self.THRESHOLD_1H:
                self._1h_total_warnings += 1
                LOGGER.warning('[%s] reconnects happens too often for last hour: %s' %
                               (key, self._1h_errors[key]))

        self._last_1h_check = now()
        self._1h_stat.clear()
        self._1h_errors.clear()

        if self._streams_count:
            total_rate = float(self._1h_total_warnings) / self._streams_count
            total_rate = round(total_rate, 3)
            if total_rate >= self.THRESHOLD_TOTAL:
                LOGGER.warning('TOO MANY STREAMS RECONNECTS')

        self._1h_total_warnings = 0
        self._streams_count = 0

    def log_frequent_reconnects(self, streams_count):
        self.check_10min_interval(streams_count)
        self.check_1h_interval(streams_count)
