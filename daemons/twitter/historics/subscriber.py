from solariat.utils.timeslot import datetime_to_timestamp, parse_datetime, now
from solariat_bottle.daemons.twitter.historics.timeline_request import \
    DirectMessagesRequest, SentDirectMessagesRequest, SearchRequest, UserTimelineRequest, dumps
from solariat_bottle.daemons.twitter.historics.historic_loader import HistoricLoader
from solariat_bottle.daemons.twitter.historics.timeline_request import TwitterTimelineRequest
from solariat_bottle.daemons.helpers import Stoppable
from solariat_bottle.daemons.base import BaseHistoricSubscriber
from solariat_bottle.db.historic_data import QueuedHistoricData, \
    SUBSCRIPTION_CREATED, SUBSCRIPTION_RUNNING, SUBSCRIPTION_FINISHED, \
    SUBSCRIPTION_STOPPED, SUBSCRIPTION_ERROR, SUBSCRIPTION_WAITING_LIMITS_RESET
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.jobs.manager import state_producer
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.tweet import BaseTwitterApiWrapper
from solariat_bottle.utils.posts_tracking import log_state, PostState
from solariat_bottle.utils.tweet import RateLimitedTwitterApiWrapper, TwitterApiRateLimitError

from tweepy.parsers import JSONParser


def get_api_from_channel(channel):
    return RateLimitedTwitterApiWrapper.init_with_channel(channel)


class TwitterHistoricsSubscriber(BaseHistoricSubscriber, Stoppable):

    def __init__(self, subscription):
        self.subscription = subscription
        self.channels = self._get_candidate_channels()
        self.queue_channel = subscription.service_channel
        self.from_date = subscription.from_date
        self.to_date = subscription.to_date
        self.subscription.update(status=SUBSCRIPTION_CREATED)
        self.state = {}
        self.historic_loader = HistoricLoader(self.subscription, self.channels, self)
        super(TwitterHistoricsSubscriber, self).__init__()

    def start_historic_load(self):
        self.subscription.update(status=SUBSCRIPTION_RUNNING)
        self.run()

    def get_status(self):
        self.subscription.reload()
        if self.subscription.status == SUBSCRIPTION_STOPPED:
            self.stop()
        return self.subscription.status

    def _get_candidate_channels(self):
        sc = self.subscription.service_channel
        dispatch_channel = self.subscription.outbound_channel
        channel = self.subscription.channel
        candidates = set()
        if sc:
            candidates.add(sc.inbound)
            candidates.add(sc.outbound)
        if dispatch_channel:
            candidates.add(dispatch_channel.id)
        if channel:
            candidates.add(channel.id)
        return Channel.objects.ensure_channels(candidates)

    def _get_filters(self):
        return {
            "start_date": self.from_date,
            "end_date": self.to_date
        }

    def split_keywords(self, channel_filters_map):
        from solariat_bottle.utils.tracking import combine_and_split

        parts = []
        max_track = SearchRequest.MAX_KEYWORDS_COUNT
        max_size = SearchRequest.MAX_QUERY_SIZE

        def _all_valid(parts):
            return all(len(SearchRequest.build_query(p[0])) < max_size for p in parts)

        while True:
            parts = combine_and_split(channel_filters_map, max_track=max_track)
            if _all_valid(parts):
                break
            max_track -= 1
            if max_track == 0:
                LOGGER.error(u"Can't break search keywords onto valid parts.\n"
                             u"Filters: %s" % channel_filters_map)
                break
        return parts

    def gen_requests(self):
        from solariat_bottle.utils.tracking import get_channel_post_filters_map, get_languages

        def _find_authenticated(channels):
            channel = None
            for channel in channels:
                if channel.is_authenticated:
                    return channel
            return channel

        channel_filters_map = get_channel_post_filters_map(self.channels)
        langs = get_languages(channel_filters_map.keys())

        parts = self.split_keywords(channel_filters_map)
        params = self._get_filters()

        channel = _find_authenticated(self.channels)
        api = get_api_from_channel(channel)
        yield DirectMessagesRequest(self, api=api, **params)
        yield SentDirectMessagesRequest(self, api=api, **params)

        for (keywords, user_ids, accounts, channels) in parts:
            channel = _find_authenticated(channels)
            api = get_api_from_channel(channel)

            for language in langs:
                yield SearchRequest(self,
                                    api=api,
                                    keywords=keywords,
                                    language=language,
                                    **params)

            for user_id in user_ids:
                yield UserTimelineRequest(self,
                                          api=api,
                                          user_id=user_id,
                                          **params)

    def push_posts(self, tweets, post_data_format=None, post_data_dump=None):
        insert_data = dict(
            subscription=self.subscription,
            post_data_format=post_data_format)

        for tweet in tweets:
            log_state(self.subscription.channel.id, str(tweet['id']), PostState.ARRIVED_IN_RECOVERY)
            try:
                insert_data.update({"post_data": post_data_dump(tweet),
                                    "timestamp": datetime_to_timestamp(parse_datetime(tweet['created_at']))})
                QueuedHistoricData.objects.create(**insert_data)
                log_state(self.subscription.channel.id,
                          str(tweet['id']), PostState.ADDED_TO_WORKER_QUEUE)
            except:
                LOGGER.exception(u'QueuedHistoricData.objects.create: %s' % insert_data)
        return len(tweets)

    def update_status(self, status):
        self.subscription.reload()
        if self.subscription.status == SUBSCRIPTION_STOPPED:
            self.stop()

        self.subscription.update(status=status)

    @state_producer
    def aggregate_state(self, worker, wstate):
        LOGGER.debug('[aggregate state invoked] worker: %s', worker)
        state = self.state
        if worker in state:
            name, _, _ = state[worker]
            state[worker] = [name, wstate, now()]
        else:
            idx = len([1 for w in state if type(w) == type(worker)])
            name = '%s_%s' % (type(worker).__name__, idx)
            state[worker] = [name, wstate, now()]
        # res = {name: [wstate, dt] for name, wstate, dt in state.values()}
        return {name: wstate}

    def run(self):
        try:
            requests = list(self.gen_requests())
            for idx, request in enumerate(requests):
                if self.stopped():
                    break
                for tweets in request:
                    if self.stopped():
                        break
                    self.push_posts(tweets,
                                    post_data_format=request.post_data_format,
                                    post_data_dump=request.post_data_dump)
                    self.update_status(SUBSCRIPTION_RUNNING)

            self.historic_loader.load()

            if self.stopped():
                self.update_status(SUBSCRIPTION_STOPPED)
                # update status, then wait for creator's work done
                self.historic_loader.creator.join()
                self.aggregate_state(self.historic_loader, {'finished': True})
            else:
                self.update_status(SUBSCRIPTION_FINISHED)
        except TwitterApiRateLimitError as e:
            LOGGER.warning('Waiting rate limits reset. Restart is needed in: %s sec.' % e.wait_for)
            self.update_status(SUBSCRIPTION_WAITING_LIMITS_RESET)
            raise
        except Exception:
            LOGGER.exception('Subscriber exception:', exc_info=True)
            self.update_status(SUBSCRIPTION_ERROR)
            raise
