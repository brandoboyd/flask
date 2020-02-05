from datetime import date, datetime
import operator
import json
from solariat.utils.timeslot import parse_datetime, utc, timedelta, now
from solariat.utils.text import force_unicode
from solariat_bottle.daemons.twitter.parsers import DMTweetParser

from solariat_bottle.db.historic_data import QueuedHistoricData
from tweepy import TweepError
from solariat_bottle.utils.logger import Dumper
from solariat_bottle.utils.stateful import Stateful, state_updater
from solariat_bottle.utils.tweet import TwitterApiRateLimitError
from solariat_bottle.settings import LOGGER, get_var


DUMPER = Dumper(filename=get_var('TWITTER_HISTORIC_DUMP'),
                logger_name='TwitterHistoric')


def dumps(obj):
    return json.dumps(obj, indent=4, default=str)


class TwitterTimelineRequest(Stateful):
    REQUEST_TYPES = SEARCH_REQUEST, USER_REQUEST, DM_REQUEST, DM_SENT_REQUEST = \
        'SEARCH_REQUEST', 'USER_REQUEST', 'DM_REQUEST', 'DM_SENT_REQUEST'
    REQUEST_TYPE = None

    def __init__(self, subscriber, api, method, **kwargs):
        self.config = kwargs.pop('config', {})
        self.subscriber = subscriber
        self.subscription = subscriber.subscription
        self.api = api
        self.method = method
        self.filters = kwargs
        self.result = []  # list of returned tweets
        self._done = False
        self._min_date = None
        self._max_date = None
        self.dumper = DUMPER
        self._progress = 0
        self._posts = 0
        stateless = self.subscription is None
        super(TwitterTimelineRequest, self).__init__(stateless=stateless)

    @staticmethod
    def _getter(item):
        if isinstance(item, dict):
            return operator.itemgetter
        else:
            return operator.attrgetter

    @property
    def oldest(self):
        getter = self._getter(self.result[0])
        return min(self.result, key=getter('id')), getter

    @property
    def newest(self):
        getter = self._getter(self.result[0])
        return max(self.result, key=getter('id')), getter

    @property
    def max_id(self):
        ''' find new lowest id - 1 for next request '''
        if self.result:
            item, getter = self.oldest
            return getter('id')(item) - 1

    @staticmethod
    def _parse_date(created_at):
        if isinstance(created_at, (date, datetime)):
            return utc(created_at)
        return parse_datetime(created_at)

    @property
    def min_date(self):
        if not self.result:
            return
        item, getter = self.oldest
        return self._parse_date(getter('created_at')(item))

    @property
    def max_date(self):
        if not self.result:
            return
        item, getter = self.newest
        return self._parse_date(getter('created_at')(item))

    @property
    def timeline_min_date(self):
        if self._min_date is None:
            self._min_date = self.min_date
        else:
            self._min_date = min(self._min_date, self.min_date)
        return self._min_date

    @property
    def timeline_max_date(self):
        if self._max_date is None:
            self._max_date = self.max_date
        else:
            self._max_date = max(self._max_date, self.max_date)
        return self._max_date

    @property
    def post_data_format(self):
        return QueuedHistoricData.TWITTER_API_PUBLIC

    @property
    def post_data_dump(self):
        return json.dumps

    def serialize_state(self):
        self._posts += len(self.filtered_result)
        state = {
            'max_id': self.filters.get('max_id'),
            'since_id': self.filters.get('since_id'),
            'progress': self.progress,
            'posts': self._posts,
            'done': self._done,
        }
        return state

    def deserialize_state(self, state):
        get = state.get
        max_id = get('max_id')
        since_id = get('since_id')
        progress = get('progress')
        posts = get('posts')
        done = get('done')

        if max_id:
            self.filters['max_id'] = max_id
        if since_id:
            self.filters['since_id'] = since_id
        if progress:
            self._progress = progress
        if posts:
            self._posts = posts
        self._done = done
        self.subscriber.aggregate_state(self, {'restored': progress})

    def stateful_params(self):
        return {
            'subscription_id': self.subscription.id,
            'req_type': self.REQUEST_TYPE,
        }

    def get_method_params(self):
        max_id = self.filters.get('max_id')
        since_id = self.filters.get('since_id')
        params = {}
        if max_id:
            params['max_id'] = max_id
        if since_id:
            params['since_id'] = since_id
        params['tweet_mode'] = "extended"
        return params

    def filters_fulfilled(self):
        start_date = self.filters.get('start_date')
        end_date = self.filters.get('end_date')
        predicates = []
        p = predicates.append
        if start_date:
            p(utc(self.timeline_min_date) <= utc(start_date))
        if end_date:
            p(utc(self.timeline_max_date) >= utc(end_date))
        res = all(predicates)
        LOGGER.debug('[:::: filters_fulfilled ::::] %s', res)
        return res

    def done(self):
        return self._done

    @state_updater
    def execute_request(self, failfast=False):
        import time
        import datetime

        retry_attempts = 0
        max_retry_attempts = self.config.get('retry_count', 10)
        min_delay = self.config.get('min_retry_delay', 60)  # 1 minute
        incr = 2
        max_delay = self.config.get('max_retry_delay', 1800)  # 30 minutes
        delay = min_delay

        method = getattr(self.api, self.method)
        exc = None
        _start = datetime.datetime.utcnow()

        while retry_attempts < max_retry_attempts:
            try:
                params = self.get_method_params()
                if not params:
                    LOGGER.warn(u"%s.%s got no params. Filters were: %s" % (self.api, self.method, self.filters))
                    self.result = []
                else:
                    LOGGER.info(u"Executing %s.%s with params: %s\nFilters: %s" % (self.api, self.method, dumps(params), dumps(self.filters)))
                    self.result = self.parse_response(method(**params))
                    self.filtered_result = filter(self._filter_tweet, self.result)
                    self.filters.update(max_id=self.max_id)  # update filters with next max_id
            except TweepError as e:
                exc = e
                # non-rate-limit error during performing request or parsing response;
                # rate-limit errors with 420, 429 statuses are handled by tweepy
                LOGGER.error(e, exc_info=True)
                # search api may respond with {"error": "Sorry, your query is too complex. Please reduce complexity and try again."}
                if "query is too complex" in unicode(e):
                    break

                retry_attempts += 1
                time.sleep(delay)
                delay = min(max_delay, delay * incr)
            except TwitterApiRateLimitError as e:
                LOGGER.debug('[execute_request] rate limits, waiting %s seconds', e.wait_for)
                self.subscriber.aggregate_state(self, {'wait_rate_limit_reset': e.wait_for})
                raise
            else:
                LOGGER.debug('[execute_request] len(self.result)=%s', len(self.result))
                if len(self.result) == 0 or self.filters_fulfilled():
                    self._done = True
                    self.subscriber.aggregate_state(self, {'finished': True})
                else:
                    self.subscriber.aggregate_state(self, {'running': self.progress})
                break

        _elapsed = datetime.datetime.utcnow() - _start
        if exc is not None:
            LOGGER.error(u"Could not retrieve results from twitter after %s" % _elapsed)
            self.subscriber.aggregate_state(self, {'failed': str(exc)})
            if failfast is True:
                raise exc
            else:
                self.result = []
                self._done = True

    @property
    def progress(self):
        """Returns progress in percents"""
        if self._done is True:
            return 100

        # before first run of execute_request()
        if not self.result and not self._progress:
            return 0
        # when all tweets were fetched on previous iteration, or state restored
        elif not self.result:
            return self._progress

        # get progress comparing filters date interval and current min date
        start_date = self.filters.get('start_date')
        end_date = self.filters.get('end_date')
        if not end_date:
            end_date = now()

        full_interval = (end_date - start_date).total_seconds()
        ratio = (self.timeline_min_date - utc(start_date)).total_seconds() / full_interval

        if ratio < 0:           # min_date < start_date, all tweets fetched
            self._progress = 100
        elif 0 <= ratio <= 1:   # start_date < min_date < end_date, in progress
            self._progress = round((1.0 - ratio) * 100)
        else:                   # min_date > end_date, zero tweets fetched
            self._progress = 0
        return self._progress

    def _filter_tweet(self, tweet):
        predicates = []
        p = predicates.append
        tweet_date = parse_datetime(tweet['created_at'])
        start_date = self.filters.get('start_date')
        end_date = self.filters.get('end_date')

        if start_date:
            p(tweet_date >= utc(start_date))
        if end_date:
            p(tweet_date <= utc(end_date))

        return all(predicates)

    def parse_response(self, response):
        self.dumper.log(json.dumps(response))
        # self._last_response = response
        if isinstance(response, list):
            return response
        return response.get('statuses', [])

    def execute(self):
        """yields part of tweets"""
        while not self.done():
            self.execute_request()
            yield self.filtered_result

    def __iter__(self):
        return self.execute()


class DirectMessagesRequest(TwitterTimelineRequest):
    REQUEST_TYPE = TwitterTimelineRequest.DM_REQUEST
    DIRECT_MESSAGES_LIMIT = 200  # max returned direct messages per request

    def __init__(self, subscriber, api, method='direct_messages', **kwargs):
        super(DirectMessagesRequest, self).__init__(subscriber, api, method, **kwargs)

    def get_method_params(self):
        params = super(DirectMessagesRequest, self).get_method_params()
        params.update({
            "count": self.DIRECT_MESSAGES_LIMIT
        })
        return params

    @property
    def post_data_format(self):
        return QueuedHistoricData.TWITTER_API_DM

    @property
    def post_data_dump(self):
        parser = DMTweetParser()

        def _dumper(msg):
            json_dm = parser(msg)
            return json.dumps(json_dm)

        return _dumper


class SentDirectMessagesRequest(DirectMessagesRequest):
    REQUEST_TYPE = TwitterTimelineRequest.DM_SENT_REQUEST

    def __init__(self, subscriber, api, method='sent_direct_messages', **kwargs):
        super(SentDirectMessagesRequest, self).__init__(subscriber, api, method, **kwargs)


class DirectMessagesFetcher(DirectMessagesRequest):
    """ DirectMessagesFetcher fetching by batches, 200 dm in one batch.
        It stops fetching when achieving filter's 'start_date' and 'end_date'
        params. If from_date/to_date are not set, max results len - 200.
    """

    class EmptySubscription(object):
        subscription = None
        def aggregate_state(self, worker, wstate):
            pass

    def __init__(self, api, **filters):
        state_aggregator = DirectMessagesFetcher.EmptySubscription()
        super(DirectMessagesFetcher, self).__init__(state_aggregator, api, **filters)

    def fetch(self):
        while not self.done():
            self.execute_request(failfast=True)
            for dm in self.filtered_result:
                yield dm


class SearchRequest(TwitterTimelineRequest):
    MAX_KEYWORDS_COUNT = 10   # https://dev.twitter.com/rest/public/search "Best Practices"
    MAX_QUERY_SIZE = 500
    SEARCH_LIMIT = 100        # https://dev.twitter.com/rest/reference/get/search/tweets#api-param-search_count
    DATE_FORMAT = '%Y-%m-%d'  # 'YYYY-MM-DD'  # https://dev.twitter.com/rest/reference/get/search/tweets#api-param-search_until
    REQUEST_TYPE = TwitterTimelineRequest.SEARCH_REQUEST

    def __init__(self, subscriber, api, method='search', **kwargs):
        super(SearchRequest, self).__init__(subscriber, api, method, **kwargs)

    def stateful_params(self):
        params = super(SearchRequest, self).stateful_params()
        get = self.filters.get
        params.update({
            'keywords': get('keywords'),
            'lang': get('language', get('lang')),
        })
        return params

    @classmethod
    def build_query(cls, keywords=()):
        special = [' ', 'or', ':)', ':(', '-', '?',
                   'from:', 'to:',
                   'until:', 'since:',
                   'filter:', 'source:']

        def _quote_exact(phrase):
            phrase = force_unicode(phrase)
            phrase = phrase.replace("'", "\\'").replace('"', '\\"')
            for s in special:
                if s in phrase:
                    return u'"%s"' % phrase
            return phrase

        q = u' OR '.join(map(_quote_exact, keywords))
        return q

    def get_method_params(self):
        get = self.filters.get
        params = super(SearchRequest, self).get_method_params()
        params.update({
            "include_entities": True,
            "count": self.SEARCH_LIMIT,
            "q": self.build_query(get('keywords')),
            "lang": get('language', get('lang'))
        })

        if not params['q']:
            return None

        start_date = get('start_date')
        end_date = get('end_date')

        if start_date:
            start_date_str = start_date.strftime(self.DATE_FORMAT)
            params['since'] = start_date_str

        if end_date:
            if (end_date.hour, end_date.minute) != (0, 0):
                end_date = end_date + timedelta(days=1)
            end_date_str = end_date.strftime(self.DATE_FORMAT)
            params['until'] = end_date_str

        return params


class UserTimelineRequest(TwitterTimelineRequest):
    FETCH_LIMIT = 200  # https://dev.twitter.com/rest/reference/get/statuses/user_timeline#api-param-count
    REQUEST_TYPE = TwitterTimelineRequest.USER_REQUEST

    def __init__(self, subscriber, api, method='user_timeline', **kwargs):
        super(UserTimelineRequest, self).__init__(subscriber, api, method, **kwargs)

    def stateful_params(self):
        params = super(UserTimelineRequest, self).stateful_params()
        get = self.filters.get
        params.update({
            'user_id': get('user_id'),
        })
        return params

    def get_twitter_user_query(self):
        from solariat_bottle.utils.tracking import preprocess_keyword
        q = {}
        get = self.filters.get
        user_id = get('user_id')
        if user_id:
            try:
                long(user_id)
            except TypeError:
                pass
            else:
                q = {'user_id': user_id}

        # TODO: code below does not used
        screen_name = get('user_name', get('screen_name'))
        if screen_name:
            screen_name = preprocess_keyword(screen_name, strip_special_chars=True)
            q = {'screen_name': screen_name}
        return q

    def get_method_params(self):
        q = self.get_twitter_user_query()
        if not q:
            return None
        params = super(UserTimelineRequest, self).get_method_params()
        params.update({
            "count": self.FETCH_LIMIT
        })
        params.update(q)
        return params
