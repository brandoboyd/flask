# coding=utf-8
from collections import namedtuple
from solariat_bottle.db.historic_data import TwitterRestHistoricalSubscription, \
    SUBSCRIPTION_FINISHED, SUBSCRIPTION_ERROR, SUBSCRIPTION_STOPPED
from solariat_bottle.tests.base import BaseCase
from solariat_bottle.daemons.twitter.historics.timeline_request import DirectMessagesFetcher, dumps
from solariat_bottle.daemons.twitter.historics.subscriber import TwitterHistoricsSubscriber
from solariat.utils.timeslot import now, timedelta
import time
import tweepy
import unittest
import mock
import random
from solariat_bottle.settings import LOGGER


format_date = lambda d: d.strftime("%m/%d/%Y %H:%M:%S")


class FakeTwitterApiException(Exception):
    pass

class FakeHistoricLoaderException(Exception):
    pass


def check_raise_exception(method):
    def _method(*args, **kwargs):
        if FakeTwitterApi.RAISE_EXCEPTION is 1:
            raise FakeTwitterApiException('FakeTwitterApi Exception')
        if FakeTwitterApi.RAISE_EXCEPTION is True:
            FakeTwitterApi.RAISE_EXCEPTION = 1
        return method(*args, **kwargs)
    return _method


def filter_by_max_id_and_since_id(origin):
    def _method(*args, **kwargs):
        res = origin(*args, **kwargs)
        max_id = kwargs.get('max_id')
        since_id = kwargs.get('since_id')

        def between_max_and_since(tweet):
            res = True
            if max_id:
                res = res and tweet['id'] <= max_id
            if since_id:
                res = res and tweet['id'] > since_id
            return res

        if isinstance(res, dict):  # search
            res['statuses'] = [i for i in res['statuses'] if between_max_and_since(i)]
            return res
        return [i for i in res if between_max_and_since(i)]
    return _method


class FakeTwitterApi(object):
    """ All fake api methods return data unless <api_type>_DATA_LENTH reached for each method
    """

    class NextParams(object):
        def __init__(self, init_id, data_len, from_date, to_date):
            self.data_len = data_len

            self._to_date = to_date
            self.created_at = to_date
            self.created_at_inc_sec = (to_date - from_date).total_seconds() / data_len
            self.created_at_inc = timedelta(seconds=self.created_at_inc_sec)

            self._last_id = init_id
            self.id = init_id
            self.id_inc = 11

        def next(self):
            self.id -= self.id_inc
            self.created_at -= self.created_at_inc

        def fit_data_len(self, res):
            if self.data_len < len(res):
                res[:] = res[:self.data_len]
            self.data_len -= len(res)

        def __getitem__(self, index):
            """ Returns :index data item.
                index=0 more recent data item,
                the bigger index, the older data.
            """

            id = self._last_id - index * self.id_inc
            created_at = self._to_date - timedelta(seconds=(index * self.created_at_inc_sec))
            return id, created_at

    @classmethod
    def restore_settings(cls):
        cls.SEARCH_DATA_LENGTH = 500
        cls.TIMELINE_DATA_LENGTH = 500
        cls.DM_DATA_LENGTH = 500
        cls.DM_SENT_DATA_LENGTH = 500
        cls.ALL_DATA_LENGTH = sum([
            cls.SEARCH_DATA_LENGTH, cls.TIMELINE_DATA_LENGTH, cls.DM_DATA_LENGTH, cls.DM_SENT_DATA_LENGTH
        ])
        cls.CREATED_TO = now()
        cls.CREATED_FROM = cls.CREATED_TO - timedelta(days=5)
        cls.RAISE_EXCEPTION = False     # if True, return first response, fail on second
        cls.init_next_params()

    @classmethod
    def init_next_params(cls):
        NextParams = cls.NextParams
        FROM, TO = cls.CREATED_FROM, cls.CREATED_TO
        init_id = 559910001000
        many = 100 * 1000   # must be bigger than <some>_DATA_LENGTH * self.id_inc
        cls.SEARCH = NextParams(init_id, cls.SEARCH_DATA_LENGTH, FROM, TO)
        cls.TIMELINE = NextParams(init_id + many, cls.TIMELINE_DATA_LENGTH, FROM, TO)
        cls.DM = NextParams(init_id + 2 * many, cls.DM_DATA_LENGTH, FROM, TO)
        cls.DM_SENT = NextParams(init_id + 3 * many, cls.DM_SENT_DATA_LENGTH, FROM, TO)

    def __init__(self, *args, **kwargs):
        Auth = namedtuple('Auth', ['consumer_key', 'consumer_secret',
                                   'access_token', 'access_token_secret'])
        self.auth = Auth('consumer_key', 'consumer_secret',
                         'access_token', 'access_token_secret')

    def get_tweet(self, keywords=None, user_id=None, dm=False, next_params=None):
        """ When invoked, change internal counters of :id and :created_at
            for each next result item.
        """

        user_id = user_id or random.choice(xrange(100, 200))
        user_info = {
            'id_str': "%s" % user_id,
            'id': user_id,
            'screen_name': 'test_user_%s' % user_id
        }
        tweet = {
            'id': next_params.id,
            'id_str': "%s" % next_params.id,
            'created_at': str(next_params.created_at),
            'text': u"I like this %s" % random.choice(keywords or ['test']),
            'user': user_info,
        }
        if dm:
            tweet.update({
                'sender': user_info,
                'recipient': user_info,
            })
        next_params.next()
        return tweet

    @filter_by_max_id_and_since_id
    @check_raise_exception
    def user_timeline(self, **kwargs):
        next_params = self.__class__.TIMELINE
        user_id = kwargs.get('user_id')
        if next_params.data_len == 0:
            return []
        res = [self.get_tweet(user_id=user_id, next_params=next_params) for _ in xrange(kwargs.get('count'))]
        next_params.fit_data_len(res)
        return res

    @filter_by_max_id_and_since_id
    @check_raise_exception
    def search(self, **kwargs):
        next_params = self.__class__.SEARCH
        q = kwargs.get('q')
        count = kwargs.get('count')
        keywords = [k.strip('"').strip("'") for k in q.split(' OR ')]

        tweets = []
        # if not max_id and kwargs.get('lang') != 'und':
        if next_params.data_len > 0:
            for _ in range(count):
                tweets.append(self.get_tweet(keywords=keywords, next_params=next_params))
            next_params.fit_data_len(tweets)

        return {"metadata": {}, "statuses": tweets}

    @filter_by_max_id_and_since_id
    @check_raise_exception
    def direct_messages(self, **kwargs):
        next_params = self.__class__.DM
        if next_params.data_len == 0:
            return []
        res = [self.get_tweet(dm=True, next_params=next_params) for _ in xrange(kwargs.get('count'))]
        next_params.fit_data_len(res)
        return res

    @filter_by_max_id_and_since_id
    @check_raise_exception
    def sent_direct_messages(self, **kwargs):
        next_params = self.__class__.DM_SENT
        if next_params.data_len == 0:
            return []
        res = [self.get_tweet(dm=True, next_params=next_params) for _ in xrange(kwargs.get('count'))]
        next_params.fit_data_len(res)
        return res

FakeTwitterApi.restore_settings()


class TestTwitterRecovery(BaseCase):
    patched_tweepy_api = mock.patch("tweepy.API", side_effect=FakeTwitterApi)
    patched_tweepy_ext_api = mock.patch("solariat_bottle.utils.tweet.TwitterApiExt",
                                        side_effect=FakeTwitterApi)

    def setUp(self):
        super(TestTwitterRecovery, self).setUp()
        self.patched_tweepy_api.start()
        self.patched_tweepy_ext_api.start()

        from solariat_bottle import settings
        self.settings_DATASIFT_POST_USER = settings.DATASIFT_POST_USER
        settings.DATASIFT_POST_USER = self.user.email

    def tearDown(self):
        super(TestTwitterRecovery, self).tearDown()
        self.patched_tweepy_api.stop()
        self.patched_tweepy_ext_api.stop()

        from solariat_bottle import settings
        settings.DATASIFT_POST_USER = self.settings_DATASIFT_POST_USER

    # @unittest.skip('temp')
    def test_queue_integration(self):
        """ Covers full integration from starting Subscriber,
            through TwitterTimelineRequest's fetchers, HistoricLoader
            until PostCreator.create_post().
        """
        from solariat_bottle.settings import LOGGER
        from solariat_bottle.db.channel.twitter import TwitterServiceChannel
        from solariat_bottle.db.historic_data import QueuedHistoricData
        from solariat_bottle.db.post.base import Post
        from solariat_bottle.daemons.twitter.historics.timeline_request import \
            DirectMessagesRequest, SentDirectMessagesRequest, SearchRequest, UserTimelineRequest
        from solariat_bottle.db.user_profiles.user_profile import UserProfile

        # reduce amount of data for long-running integration test
        FakeTwitterApi.SEARCH_DATA_LENGTH = 50
        FakeTwitterApi.TIMELINE_DATA_LENGTH = 50
        FakeTwitterApi.DM_DATA_LENGTH = 50
        FakeTwitterApi.DM_SENT_DATA_LENGTH = 50
        FakeTwitterApi.ALL_DATA_LENGTH = 200
        FakeTwitterApi.CREATED_FROM = FakeTwitterApi.CREATED_TO - timedelta(days=1)
        FakeTwitterApi.init_next_params()
        SearchRequest.SEARCH_LIMIT = 10
        UserTimelineRequest.FETCH_LIMIT = 20
        DirectMessagesRequest.DIRECT_MESSAGES_LIMIT = 20
        SentDirectMessagesRequest.DIRECT_MESSAGES_LIMIT = 20

        profile = UserProfile.objects.upsert('Twitter', profile_data=dict(user_name='jarvis', user_id='99188210'))
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='SC')
        channel.add_username(profile.user_name)
        channel.add_keyword(u'keywörd')

        def get_id_date_pair(post_data):
            if 'twitter' in post_data:
                post_data = post_data['twitter']
            return int(post_data['id']), post_data['created_at']

        fetched_data = []
        def _save_tweets(fn):
            def decorated(tweets, *args, **kwargs):
                LOGGER.debug('PUSH_POSTS, len:%s', len(tweets))
                fetched_data.extend([get_id_date_pair(t) for t in tweets])
                return fn(tweets, *args, **kwargs)
            return decorated

        queued_data = []
        def _save_queued_data(method):
            def _method(*args, **kwargs):
                queued_data[:] = [
                    get_id_date_pair(i.solariat_post_data) for i in
                    QueuedHistoricData.objects(subscription=subscription)
                ]
                LOGGER.debug('QUEUED_POSTS, len: %s', len(queued_data))
                self.assertTrue(len(queued_data) == FakeTwitterApi.ALL_DATA_LENGTH,
                                msg="len=%d %s" % (len(queued_data), queued_data))
                self.assertEqual(set(queued_data), set(fetched_data),
                                 msg=u"\nqueued =%s\nfetched=%s" % (queued_data, fetched_data))
                return method(*args, **kwargs)
            return _method

        subscription = TwitterRestHistoricalSubscription.objects.create(
            created_by=self.user,
            channel_id=channel.id,
            from_date=FakeTwitterApi.CREATED_FROM,
            to_date=FakeTwitterApi.CREATED_TO
        )
        subscriber = TwitterHistoricsSubscriber(subscription)
        subscriber.push_posts = _save_tweets(subscriber.push_posts)
        subscriber.historic_loader.load = _save_queued_data(subscriber.historic_loader.load)

        subscriber.start_historic_load()
        self.assertEqual(subscriber.get_status(), SUBSCRIPTION_FINISHED)

        self.assertEqual(Post.objects(channels__in=[
            subscription.channel.inbound,
            subscription.channel.outbound]).count(), FakeTwitterApi.ALL_DATA_LENGTH)

        SearchRequest.SEARCH_LIMIT = 100
        UserTimelineRequest.FETCH_LIMIT = 200
        DirectMessagesRequest.DIRECT_MESSAGES_LIMIT = 200
        SentDirectMessagesRequest.DIRECT_MESSAGES_LIMIT = 200

    # @unittest.skip('temp')
    def test_recovery_after_timeline_req_failure(self):
        from solariat_bottle.db.channel.twitter import TwitterServiceChannel
        from solariat_bottle.db.user_profiles.user_profile import UserProfile
        from solariat_bottle.settings import LOGGER

        FakeTwitterApi.restore_settings()

        profile = UserProfile.objects.upsert('Twitter', dict(user_name='jarvis', user_id='99188210'))
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='ServChannel')
        channel.add_username(profile.user_name)
        channel.add_keyword(u'bmw')

        fetched_data = []
        def _save_tweets(fn):
            def decorated(tweets, *args, **kwargs):
                LOGGER.debug('PUSH_POSTS, len:%s', len(tweets))
                fetched_data.extend(tweets)
                return fn(tweets, *args, **kwargs)
            return decorated

        subscription = TwitterRestHistoricalSubscription.objects.create(
            created_by=self.user,
            channel_id=channel.id,
            from_date=FakeTwitterApi.CREATED_FROM,
            to_date=FakeTwitterApi.CREATED_TO
        )
        subscriber = TwitterHistoricsSubscriber(subscription)
        subscriber.push_posts = _save_tweets(subscriber.push_posts)

        # Emulate total crash of subscriber
        FakeTwitterApi.RAISE_EXCEPTION = True
        with self.assertRaises(FakeTwitterApiException):
            subscriber.start_historic_load()
        self.assertEqual(subscription.status, SUBSCRIPTION_ERROR)
        fetched_before_crash = len(fetched_data)

        # Get max_id param from last result
        last_max_id = min(fetched_data, key=lambda i: i['id'])['id']
        self.assertIsNotNone(last_max_id)

        # Create subscriber again, create TwitterTimelineRequests
        subscriber = TwitterHistoricsSubscriber(subscription)
        tw_timeline_req = next(subscriber.gen_requests())
        self.assertEqual(tw_timeline_req.filters.get('max_id'), last_max_id - 1)

        # Check fetching is ok after state restore
        FakeTwitterApi.RAISE_EXCEPTION = False

        # INFO: does not work if remove lines below
        # TypeError can't compare offset-naive and offset-aware datetimes
        subscription.from_date = FakeTwitterApi.CREATED_FROM
        subscription.to_date = FakeTwitterApi.CREATED_TO
        subscriber = TwitterHistoricsSubscriber(subscription)
        subscriber.push_posts = _save_tweets(subscriber.push_posts)
        subscriber.historic_loader.load = lambda: None
        fetched_data = []

        subscriber.start_historic_load()
        self.assertEqual(subscription.status, SUBSCRIPTION_FINISHED)

        fetched_after_crash = len(fetched_data)
        self.assertEqual(fetched_before_crash + fetched_after_crash, FakeTwitterApi.ALL_DATA_LENGTH,
                         'Fetched after crash: %s items' % len(fetched_data))

    # @unittest.skip('temp')
    def test_recovery_after_historic_loader_failure(self):
        from solariat_bottle.db.channel.twitter import TwitterServiceChannel
        from solariat_bottle.db.user_profiles.user_profile import UserProfile
        from solariat_bottle.settings import LOGGER

        FakeTwitterApi.restore_settings()

        profile = UserProfile.objects.upsert('Twitter', dict(user_name='jarvis', user_id='99188210'))
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='ServChannel')
        channel.add_username(profile.user_name)
        channel.add_keyword(u'bmw')

        fetched_data = []
        def _save_tweets(fn):
            def decorated(tweets, *args, **kwargs):
                LOGGER.debug('PUSH_POSTS, len:%s', len(tweets))
                fetched_data.extend(tweets)
                return fn(tweets, *args, **kwargs)
            return decorated

        # Emulate crash while HistoricLoader works
        MAKE_CRASH = True
        posts_processed = []
        def fake_crashed_load(queue_put):
            def _queue_put(item):
                if len(posts_processed) > 400 and MAKE_CRASH:
                    raise FakeHistoricLoaderException('HistoricLoader fake crash')
                posts_processed.append(item)
                res = queue_put(item)
                return res
            return _queue_put

        subscription = TwitterRestHistoricalSubscription.objects.create(
            created_by=self.user,
            channel_id=channel.id,
            from_date=FakeTwitterApi.CREATED_FROM,
            to_date=FakeTwitterApi.CREATED_TO
        )
        subscriber = TwitterHistoricsSubscriber(subscription)
        subscriber.historic_loader._find_channels = lambda x: [channel]
        subscriber.historic_loader.creator.create_post = lambda *args, **kwargs: None
        post_Q = subscriber.historic_loader.post_queue
        post_Q.put = fake_crashed_load(post_Q.put)
        with self.assertRaises(Exception):
            subscriber.start_historic_load()

        self.assertEqual(subscription.status, SUBSCRIPTION_ERROR)
        self.assertTrue(len(posts_processed) < FakeTwitterApi.ALL_DATA_LENGTH)

        # test HistoricLoader resume
        MAKE_CRASH = False
        subscription.from_date = FakeTwitterApi.CREATED_FROM
        subscription.to_date = FakeTwitterApi.CREATED_TO
        subscriber = TwitterHistoricsSubscriber(subscription)

        subscriber.push_posts = _save_tweets(subscriber.push_posts)
        subscriber.historic_loader._find_channels = lambda x: [channel]
        subscriber.historic_loader.creator.create_post = lambda *args, **kwargs: None
        post_Q = subscriber.historic_loader.post_queue
        post_Q.put = fake_crashed_load(post_Q.put)

        subscriber.start_historic_load()

        Q_size = 100
        min_data_len = FakeTwitterApi.ALL_DATA_LENGTH
        max_data_len = FakeTwitterApi.ALL_DATA_LENGTH + Q_size * 2 - 1
        self.assertTrue(len(fetched_data) == 0)
        self.assertTrue(min_data_len <= len(posts_processed) <= max_data_len)
        self.assertEqual(subscription.status, SUBSCRIPTION_FINISHED)

    # @unittest.skip('temp')
    def test_fetch_with_max_id_and_since_id(self):
        """ This tests all TwitterTimelineRequests
        """
        # when from_date/to_date are not set, max result len = DIRECT_MESSAGES_LIMIT
        FakeTwitterApi.restore_settings()
        api = FakeTwitterApi()
        last_id, _ = api.DM[0]
        first_id, _ = api.DM[DirectMessagesFetcher.DIRECT_MESSAGES_LIMIT - 1]

        res = DirectMessagesFetcher(api)
        statuses = list(res.fetch())
        self.assertEqual(len(statuses), DirectMessagesFetcher.DIRECT_MESSAGES_LIMIT)
        self.assertEqual(statuses[0]['id'], last_id)
        self.assertEqual(statuses[-1]['id'], first_id)

        # let set max_id to 51th item
        FakeTwitterApi.restore_settings()
        api = FakeTwitterApi()
        id_50, _ = api.DM[50]   # go to 51th dm

        res = DirectMessagesFetcher(api, **{"max_id": id_50})
        statuses = list(res.fetch())
        self.assertEqual(len(statuses), DirectMessagesFetcher.DIRECT_MESSAGES_LIMIT - 50)
        self.assertTrue(all(s['id'] <= id_50 for s in statuses))
        self.assertEqual(statuses[0]['id'], id_50)

        # let check since_id
        FakeTwitterApi.restore_settings()
        api = FakeTwitterApi()
        since_id, _ = api.DM[100]
        max_id, _ = api.DM[20]

        res = DirectMessagesFetcher(api, **{'max_id': max_id, 'since_id': since_id})
        statuses = list(res.fetch())
        self.assertEqual(len(statuses), 100 - 20)

    # @unittest.skip('temp')
    def test_fetch_by_date(self):
        # check start_date. let fetcher made 2 requests (max resp len: 200)
        one_sec = timedelta(seconds=1)
        FakeTwitterApi.restore_settings()
        api = FakeTwitterApi()
        _, start_date = api.DM[300]
        start_date += one_sec
        LOGGER.debug('++++++ DATES: (%s)', (start_date, api.DM[200][1], api.DM[100][1]))

        res = DirectMessagesFetcher(api, **{"start_date": start_date})
        statuses = list(res.fetch())
        self.assertEqual(len(statuses), 300)

        # checking end_date filter
        FakeTwitterApi.restore_settings()
        api = FakeTwitterApi()
        _, start_date = api.DM[300]
        _, end_date = api.DM[150]
        start_date += one_sec

        res = DirectMessagesFetcher(api, **{'start_date': start_date, 'end_date': end_date})
        statuses = list(res.fetch())
        self.assertEqual(len(statuses), 150)

        from solariat.utils.timeslot import parse_datetime
        self.assertTrue(all(start_date <= parse_datetime(s['created_at']) <= end_date for s in statuses))

    # @unittest.skip('temp')
    def test_subscription_progress(self):
        from solariat_bottle.db.channel.twitter import TwitterServiceChannel
        from solariat_bottle.db.user_profiles.user_profile import UserProfile
        from solariat_bottle.daemons.twitter.historics.timeline_request import TwitterTimelineRequest, \
            SentDirectMessagesRequest, DirectMessagesRequest, SearchRequest, UserTimelineRequest

        FakeTwitterApi.restore_settings()

        profile = UserProfile.objects.upsert('Twitter', dict(user_name='jarvis', user_id='99188210'))
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='SC')
        channel.add_username(profile.user_name)
        channel.add_keyword(u'keywörd')

        subscription = TwitterRestHistoricalSubscription.objects.create(
            created_by=self.user,
            channel_id=channel.id,
            from_date=FakeTwitterApi.CREATED_FROM,
            to_date=FakeTwitterApi.CREATED_TO
        )

        REAL_REQUESTS_PROGRESS = {
            SentDirectMessagesRequest.REQUEST_TYPE: (0, FakeTwitterApi.DM_DATA_LENGTH),
            DirectMessagesRequest.REQUEST_TYPE: (0, FakeTwitterApi.DM_SENT_DATA_LENGTH),
            SearchRequest.REQUEST_TYPE: (0, FakeTwitterApi.SEARCH_DATA_LENGTH),
            UserTimelineRequest.REQUEST_TYPE: (0, FakeTwitterApi.TIMELINE_DATA_LENGTH),
        }

        def _assert_fetch_progress_after(origin_method):
            def _decorated(*args, **kwargs):
                res = origin_method(*args, **kwargs)

                # calculate progress for each TwitterTimelineRequest based on received & total tweets
                tw_timeline_req = args[0]
                received, full_data_len = REAL_REQUESTS_PROGRESS[tw_timeline_req.REQUEST_TYPE]
                received += len(tw_timeline_req.filtered_result)
                REAL_REQUESTS_PROGRESS[tw_timeline_req.REQUEST_TYPE] = (received, full_data_len)
                req_progress_calculated = round(float(received) / full_data_len * 100)

                # filter SearchRequest lang=und
                fget = tw_timeline_req.filters.get
                lang_und = fget('lang', fget('language')) == 'und'
                if tw_timeline_req.REQUEST_TYPE == TwitterTimelineRequest.SEARCH_REQUEST and lang_und:
                    return res

                # get Subscription progress
                progress_stat = subscription.get_progress()
                stat_items = progress_stat['fetchers']['items']
                # find stat corresponding to current TwitterTimelineRequest
                req_detail_stat = [stat for stat in stat_items if stat['filters'].get('lang') != 'und']
                req_detail_stat = [stat for stat in req_detail_stat
                                   if stat['type'] == tw_timeline_req.REQUEST_TYPE][0]

                progress_total = sum([stat['progress'] for stat in stat_items])
                progress_calculated = progress_total / len(stat_items)

                # check each request progress
                self.assertEqual(req_progress_calculated, tw_timeline_req.progress)
                self.assertEqual(req_progress_calculated, req_detail_stat['progress'])
                self.assertEqual(received, req_detail_stat['posts'])

                # check total subscription progress
                self.assertEqual(progress_stat['fetchers']['progress'], progress_calculated)
                return res
            return _decorated

        HL_PREV_PROGRESS = {'val': -1}
        def _assert_load_progress_after(obj, origin_method):
            def _decorated(*args, **kwargs):
                res = origin_method(*args, **kwargs)

                progress_stat = subscription.get_progress()
                stored_state = progress_stat['loader'] or {}
                progress = obj.progress
                self.assertTrue(0 <= progress <= 100)
                self.assertTrue(progress == stored_state.get('progress', -1))
                self.assertTrue(progress > HL_PREV_PROGRESS['val'])
                HL_PREV_PROGRESS['val'] = progress

                return res
            return _decorated

        orig_execute_request = TwitterTimelineRequest.execute_request
        TwitterTimelineRequest.execute_request = _assert_fetch_progress_after(TwitterTimelineRequest.execute_request)

        subscriber = TwitterHistoricsSubscriber(subscription)
        historic_loader = subscriber.historic_loader
        post_creator = historic_loader.creator

        historic_loader.UPDATE_PROGRESS_EVERY = 0.1
        historic_loader.update_progress = _assert_load_progress_after(historic_loader, historic_loader.update_progress)
        historic_loader._find_channels = lambda x: [channel]
        post_creator.create_post = lambda *args, **kwargs: None
        subscriber.start_historic_load()

        TwitterTimelineRequest.execute_request = orig_execute_request
        self.assertEqual(subscriber.get_status(), SUBSCRIPTION_FINISHED)

    # @unittest.skip('temp')
    def test_subscription_stop(self):
        import threading
        from solariat_bottle.db.channel.twitter import TwitterServiceChannel
        from solariat_bottle.db.user_profiles.user_profile import UserProfile

        FakeTwitterApi.restore_settings()

        class RecoveryTask(threading.Thread):
            def __init__(self, subscription):
                super(RecoveryTask, self).__init__()
                self.subscription = subscription
                self.daemon = True
                self.subscriber = TwitterHistoricsSubscriber(subscription)
                self.loader_started = threading.Event()

            def run(self):
                def _loader_started(origin_method):
                    def _method(*args, **kwargs):
                        time.sleep(0.01)    # gevent context switching
                        res = origin_method(*args, **kwargs)
                        if not self.loader_started.is_set():
                            self.loader_started.set()
                        return res
                    return _method

                hl = self.subscriber.historic_loader
                hl._find_channels = _loader_started(hl._find_channels)
                self.subscriber.start_historic_load()


        profile = UserProfile.objects.upsert('Twitter', dict(user_name='another', user_id='99188210'))
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='SC')
        channel.add_username(profile.user_name)

        create_params = dict(
            created_by=self.user,
            channel_id=channel.id,
            from_date=FakeTwitterApi.CREATED_FROM,
            to_date=FakeTwitterApi.CREATED_TO
        )

        # test stop after TimelineRequests start working
        subscription = TwitterRestHistoricalSubscription.objects.create(**create_params)
        recovery_task = RecoveryTask(subscription)
        recovery_task.start()
        time.sleep(1)
        subscription.stop()
        self.wait_task(lambda: not recovery_task.isAlive(), 10)
        self.assertEqual(subscription.status, SUBSCRIPTION_STOPPED)

        FakeTwitterApi.restore_settings()

        # test stop after HistoricLoader start working
        channel = TwitterServiceChannel.objects.create_by_user(self.user, title='HL')
        channel.add_username(profile.user_name)
        create_params['channel_id'] = channel.id

        subscription = TwitterRestHistoricalSubscription.objects.create(**create_params)
        recovery_task = RecoveryTask(subscription)
        recovery_task.start()
        recovery_task.loader_started.wait()
        time.sleep(1)
        subscription.stop()
        self.wait_task(lambda: not recovery_task.isAlive(), 10)
        self.assertEqual(subscription.status, SUBSCRIPTION_STOPPED)

    def wait_task(self, check_fn, timeout=10):
        sleep_time = 0.5
        t = timeout
        while t > 0:
            if check_fn():
                break
            else:
                time.sleep(sleep_time)
                t -= sleep_time
        else:
            self.fail("Task did not finish after waiting %s seconds" % timeout)


class TestFullTextTweetsFormat(unittest.TestCase):
    def test_restapi_tweets(self):
        tweet_data = [
            "{\"contributors\": null, \"truncated\": false, \"is_quote_status\": false, \"in_reply_to_status_id\": null, \"id\": 791853006102761472, \"favorite_count\": 0, \"full_text\": \"With Online Banking you can:\\n\\nTransfer funds between your accounts - including your Canadian and US Dollar Accounts\", \"source\": \"<a href=\\\"http://www.genesys.com\\\" rel=\\\"nofollow\\\">Genesys Social Engagement.</a>\", \"retweeted\": false, \"coordinates\": null, \"entities\": {\"symbols\": [], \"user_mentions\": [], \"hashtags\": [], \"urls\": []}, \"in_reply_to_screen_name\": null, \"in_reply_to_user_id\": null, \"display_text_range\": [0, 115], \"retweet_count\": 0, \"id_str\": \"791853006102761472\", \"favorited\": false, \"user\": {\"follow_request_sent\": false, \"has_extended_profile\": false, \"profile_use_background_image\": true, \"default_profile_image\": false, \"id\": 4180491874, \"profile_background_image_url_https\": \"https://abs.twimg.com/images/themes/theme1/bg.png\", \"verified\": false, \"translator_type\": \"none\", \"profile_text_color\": \"333333\", \"profile_image_url_https\": \"https://pbs.twimg.com/profile_images/665227400112926720/cWinJ38Z_normal.png\", \"profile_sidebar_fill_color\": \"DDEEF6\", \"entities\": {\"description\": {\"urls\": []}}, \"followers_count\": 17, \"profile_sidebar_border_color\": \"C0DEED\", \"id_str\": \"4180491874\", \"profile_background_color\": \"C0DEED\", \"listed_count\": 0, \"is_translation_enabled\": false, \"utc_offset\": null, \"statuses_count\": 51, \"description\": \"\", \"friends_count\": 65, \"location\": \"\", \"profile_link_color\": \"0084B4\", \"profile_image_url\": \"http://pbs.twimg.com/profile_images/665227400112926720/cWinJ38Z_normal.png\", \"following\": false, \"geo_enabled\": false, \"profile_background_image_url\": \"http://abs.twimg.com/images/themes/theme1/bg.png\", \"screen_name\": \"ultraalliedbnk\", \"lang\": \"en\", \"profile_background_tile\": false, \"favourites_count\": 8, \"name\": \"Ultra Allied Bank\", \"notifications\": false, \"url\": null, \"created_at\": \"Fri Nov 13 17:56:07 +0000 2015\", \"contributors_enabled\": false, \"time_zone\": null, \"protected\": false, \"default_profile\": true, \"is_translator\": false}, \"geo\": null, \"in_reply_to_user_id_str\": null, \"lang\": \"en\", \"created_at\": \"Fri Oct 28 04:04:03 +0000 2016\", \"in_reply_to_status_id_str\": null, \"place\": null}",
            "{\"contributors\": null, \"truncated\": false, \"is_quote_status\": false, \"in_reply_to_status_id\": null, \"id\": 791856684465393664, \"favorite_count\": 0, \"full_text\": \"RT @BlueSkyBuz: @ultraalliedbnk \\u041c\\u043d\\u0435 \\u043d\\u0443\\u0436\\u0435\\u043d \\u043a\\u0440\\u0435\\u0434\\u0438\\u0442 \\u043d\\u0430 \\u043f\\u043e\\u043a\\u0443\\u043f\\u043a\\u0443 \\u043a\\u0432\\u0430\\u0440\\u0442\\u0438\\u0440\\u044b\", \"source\": \"<a href=\\\"http://www.genesys.com\\\" rel=\\\"nofollow\\\">Genesys Social Engagement.</a>\", \"retweeted\": true, \"coordinates\": null, \"entities\": {\"symbols\": [], \"user_mentions\": [{\"id\": 2617604258, \"indices\": [3, 14], \"id_str\": \"2617604258\", \"screen_name\": \"BlueSkyBuz\", \"name\": \"BlueSkyBuz\"}, {\"id\": 4180491874, \"indices\": [16, 31], \"id_str\": \"4180491874\", \"screen_name\": \"ultraalliedbnk\", \"name\": \"Ultra Allied Bank\"}], \"hashtags\": [], \"urls\": []}, \"in_reply_to_screen_name\": null, \"in_reply_to_user_id\": null, \"display_text_range\": [0, 68], \"retweet_count\": 1, \"id_str\": \"791856684465393664\", \"favorited\": false, \"retweeted_status\": {\"contributors\": null, \"truncated\": false, \"is_quote_status\": false, \"in_reply_to_status_id\": null, \"id\": 791856042095308800, \"favorite_count\": 0, \"full_text\": \"@ultraalliedbnk \\u041c\\u043d\\u0435 \\u043d\\u0443\\u0436\\u0435\\u043d \\u043a\\u0440\\u0435\\u0434\\u0438\\u0442 \\u043d\\u0430 \\u043f\\u043e\\u043a\\u0443\\u043f\\u043a\\u0443 \\u043a\\u0432\\u0430\\u0440\\u0442\\u0438\\u0440\\u044b\", \"source\": \"<a href=\\\"http://twitter.com\\\" rel=\\\"nofollow\\\">Twitter Web Client</a>\", \"retweeted\": true, \"coordinates\": null, \"entities\": {\"symbols\": [], \"user_mentions\": [{\"id\": 4180491874, \"indices\": [0, 15], \"id_str\": \"4180491874\", \"screen_name\": \"ultraalliedbnk\", \"name\": \"Ultra Allied Bank\"}], \"hashtags\": [], \"urls\": []}, \"in_reply_to_screen_name\": \"ultraalliedbnk\", \"in_reply_to_user_id\": 4180491874, \"display_text_range\": [0, 52], \"retweet_count\": 1, \"id_str\": \"791856042095308800\", \"favorited\": false, \"user\": {\"follow_request_sent\": false, \"has_extended_profile\": false, \"profile_use_background_image\": true, \"default_profile_image\": true, \"id\": 2617604258, \"profile_background_image_url_https\": \"https://abs.twimg.com/images/themes/theme1/bg.png\", \"verified\": false, \"translator_type\": \"none\", \"profile_text_color\": \"333333\", \"profile_image_url_https\": \"https://abs.twimg.com/sticky/default_profile_images/default_profile_3_normal.png\", \"profile_sidebar_fill_color\": \"DDEEF6\", \"entities\": {\"description\": {\"urls\": []}}, \"followers_count\": 5, \"profile_sidebar_border_color\": \"C0DEED\", \"id_str\": \"2617604258\", \"profile_background_color\": \"C0DEED\", \"listed_count\": 0, \"is_translation_enabled\": false, \"utc_offset\": null, \"statuses_count\": 86, \"description\": \"\", \"friends_count\": 8, \"location\": \"\", \"profile_link_color\": \"0084B4\", \"profile_image_url\": \"http://abs.twimg.com/sticky/default_profile_images/default_profile_3_normal.png\", \"following\": false, \"geo_enabled\": false, \"profile_background_image_url\": \"http://abs.twimg.com/images/themes/theme1/bg.png\", \"screen_name\": \"BlueSkyBuz\", \"lang\": \"en\", \"profile_background_tile\": false, \"favourites_count\": 4, \"name\": \"BlueSkyBuz\", \"notifications\": false, \"url\": null, \"created_at\": \"Fri Jul 11 16:03:11 +0000 2014\", \"contributors_enabled\": false, \"time_zone\": null, \"protected\": false, \"default_profile\": true, \"is_translator\": false}, \"geo\": null, \"in_reply_to_user_id_str\": \"4180491874\", \"lang\": \"ru\", \"created_at\": \"Fri Oct 28 04:16:07 +0000 2016\", \"in_reply_to_status_id_str\": null, \"place\": null}, \"user\": {\"follow_request_sent\": false, \"has_extended_profile\": false, \"profile_use_background_image\": true, \"default_profile_image\": false, \"id\": 4180491874, \"profile_background_image_url_https\": \"https://abs.twimg.com/images/themes/theme1/bg.png\", \"verified\": false, \"translator_type\": \"none\", \"profile_text_color\": \"333333\", \"profile_image_url_https\": \"https://pbs.twimg.com/profile_images/665227400112926720/cWinJ38Z_normal.png\", \"profile_sidebar_fill_color\": \"DDEEF6\", \"entities\": {\"description\": {\"urls\": []}}, \"followers_count\": 17, \"profile_sidebar_border_color\": \"C0DEED\", \"id_str\": \"4180491874\", \"profile_background_color\": \"C0DEED\", \"listed_count\": 0, \"is_translation_enabled\": false, \"utc_offset\": null, \"statuses_count\": 51, \"description\": \"\", \"friends_count\": 65, \"location\": \"\", \"profile_link_color\": \"0084B4\", \"profile_image_url\": \"http://pbs.twimg.com/profile_images/665227400112926720/cWinJ38Z_normal.png\", \"following\": false, \"geo_enabled\": false, \"profile_background_image_url\": \"http://abs.twimg.com/images/themes/theme1/bg.png\", \"screen_name\": \"ultraalliedbnk\", \"lang\": \"en\", \"profile_background_tile\": false, \"favourites_count\": 8, \"name\": \"Ultra Allied Bank\", \"notifications\": false, \"url\": null, \"created_at\": \"Fri Nov 13 17:56:07 +0000 2015\", \"contributors_enabled\": false, \"time_zone\": null, \"protected\": false, \"default_profile\": true, \"is_translator\": false}, \"geo\": null, \"in_reply_to_user_id_str\": null, \"lang\": \"ru\", \"created_at\": \"Fri Oct 28 04:18:40 +0000 2016\", \"in_reply_to_status_id_str\": null, \"place\": null}",
            "{\"contributors\": null, \"truncated\": false, \"is_quote_status\": false, \"in_reply_to_status_id\": 791856042095308800, \"id\": 791857414274375680, \"favorite_count\": 0, \"full_text\": \"@BlueSkyBuz No problem\", \"source\": \"<a href=\\\"http://www.genesys.com\\\" rel=\\\"nofollow\\\">Genesys Social Engagement.</a>\", \"retweeted\": false, \"coordinates\": null, \"entities\": {\"symbols\": [], \"user_mentions\": [{\"id\": 2617604258, \"indices\": [0, 11], \"id_str\": \"2617604258\", \"screen_name\": \"BlueSkyBuz\", \"name\": \"BlueSkyBuz\"}], \"hashtags\": [], \"urls\": []}, \"in_reply_to_screen_name\": \"BlueSkyBuz\", \"in_reply_to_user_id\": 2617604258, \"display_text_range\": [12, 22], \"retweet_count\": 0, \"id_str\": \"791857414274375680\", \"favorited\": false, \"user\": {\"follow_request_sent\": false, \"has_extended_profile\": false, \"profile_use_background_image\": true, \"default_profile_image\": false, \"id\": 4180491874, \"profile_background_image_url_https\": \"https://abs.twimg.com/images/themes/theme1/bg.png\", \"verified\": false, \"translator_type\": \"none\", \"profile_text_color\": \"333333\", \"profile_image_url_https\": \"https://pbs.twimg.com/profile_images/665227400112926720/cWinJ38Z_normal.png\", \"profile_sidebar_fill_color\": \"DDEEF6\", \"entities\": {\"description\": {\"urls\": []}}, \"followers_count\": 17, \"profile_sidebar_border_color\": \"C0DEED\", \"id_str\": \"4180491874\", \"profile_background_color\": \"C0DEED\", \"listed_count\": 0, \"is_translation_enabled\": false, \"utc_offset\": null, \"statuses_count\": 51, \"description\": \"\", \"friends_count\": 65, \"location\": \"\", \"profile_link_color\": \"0084B4\", \"profile_image_url\": \"http://pbs.twimg.com/profile_images/665227400112926720/cWinJ38Z_normal.png\", \"following\": false, \"geo_enabled\": false, \"profile_background_image_url\": \"http://abs.twimg.com/images/themes/theme1/bg.png\", \"screen_name\": \"ultraalliedbnk\", \"lang\": \"en\", \"profile_background_tile\": false, \"favourites_count\": 8, \"name\": \"Ultra Allied Bank\", \"notifications\": false, \"url\": null, \"created_at\": \"Fri Nov 13 17:56:07 +0000 2015\", \"contributors_enabled\": false, \"time_zone\": null, \"protected\": false, \"default_profile\": true, \"is_translator\": false}, \"geo\": null, \"in_reply_to_user_id_str\": \"2617604258\", \"lang\": \"en\", \"created_at\": \"Fri Oct 28 04:21:34 +0000 2016\", \"in_reply_to_status_id_str\": \"791856042095308800\", \"place\": null}"
        ]
        import json
        from solariat_bottle.daemons.helpers import twitter_status_to_post_dict
        from solariat_bottle.utils.tracking import lookup_tracked_channels

        for tweet in tweet_data:
            data = json.loads(tweet)
            post_fields = twitter_status_to_post_dict(data)
            tracked_channels = lookup_tracked_channels('Twitter', post_fields)
            self.assertTrue(post_fields['content'])
