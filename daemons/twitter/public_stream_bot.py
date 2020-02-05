from solariat_bottle.daemons.twitter.stream.common import gevent_patch, \
    setup_dumper, get_bot_params

gevent_patch()

from solariat_bottle.daemons.helpers import PUBLIC_TWEET
from solariat_bottle.daemons.twitter.stream.argparse import parse_options, parse_kafka_options
from solariat_bottle.daemons.twitter.stream.base.bot import BaseStreamBot
from solariat_bottle.daemons.twitter.stream.base.listener import BaseListener
from solariat_bottle.daemons.twitter.stream.base.manager import StreamManager
from solariat_bottle.daemons.twitter.stream.base.stream import BaseStream
from solariat_bottle.daemons.twitter.stream.db import StreamRef
from solariat_bottle.daemons.twitter.stream.base.kafka_producer import KafkaProducer

from solariat_bottle.utils.logger import setup_logger
from solariat_bottle.utils.tracking import get_languages
from solariat_bottle.utils.posts_tracking import log_state, PostState
from solariat_bottle.settings import LOGGER, LOG_LEVEL
from solariat_bottle.daemons.twitter.stream.eventlog import PublicStreamDbEvents, Events

from solariat_bottle.utils.config import sync_with_keyserver, SettingsProxy
sync_with_keyserver()

from solariat.utils.http_proxy import enable_proxy
enable_proxy(settings=SettingsProxy({}))

from solariat_bottle.daemons.twitter.stream.auth_pool import AuthPool
auth_pool = AuthPool()

from solariat_bottle.daemons.twitter.stream.base.kafka_message_preparation import KafkaDataPreparation


class PublicStreamListener(BaseListener):
    def on_message(self, message):
        return self.bot.on_message(message, self.stream)


class PublicStream(BaseStream):
    @staticmethod
    def ListenerCls():
        return PublicStreamListener

    def start_stream(self):
        from solariat.utils.text import force_unicode

        self.stream.filter(follow=self.stream_ref.follow,
                           track=map(force_unicode, self.stream_ref.track),
                           stall_warnings=True)


class PublicStreamManager(StreamManager):
    @staticmethod
    def StreamCls():
        return PublicStream

    def add_stream(self, stream_ref):
        stream_key = self.stream_ref_to_key(stream_ref)

        if stream_key not in self.streams:
            auth = auth_pool.acquire_for_stream(stream_ref)
            stream_ref.set_added()
            self.logger.info('[%s] adding stream with auth: %s and filters %s' % (
                stream_key, auth, stream_ref.filters))
            greenlet = self.StreamCls()(stream_ref, auth, self,
                                        db=PublicStreamDbEvents(),
                                        bot_user_agent=self.bot_user_agent
                                        ).as_greenlet()
            self.stream_threads.start(greenlet)
            self.streams[stream_key] = greenlet

    def remove_stream(self, stream_ref, event=Events.EVENT_OFFLINE):
        stream_key = self.stream_ref_to_key(stream_ref)
        greenlet = self.streams.pop(stream_key, None)

        if greenlet:
            stream_ref = greenlet.stream_ref
            greenlet.listener.set_event(event)
            auth = auth_pool.release_for_stream(stream_ref)
            stream_ref.set_removed()
            self.stream_threads.killone(greenlet,
                                        block=False,
                                        timeout=self.STREAM_KILL_TIMEOUT)

    def sync_streams(self):
        self.logger.debug('synchronizing streams')
        stream_refs = self.bot_instance.get_stream_refs()
        remaining_stream_keys = set(self.streams)
        stream_refs_to_add = []

        for ref, is_new in stream_refs:
            key = self.stream_ref_to_key(ref)
            if not is_new:
                remaining_stream_keys.discard(key)
                continue
            if key not in self.streams:
                if auth_pool.get_current_capacity() > 0:
                    self.add_stream(ref)
                else:
                    stream_refs_to_add.append(ref)
                remaining_stream_keys.discard(key)

        # kill old streams
        for stream_key in remaining_stream_keys:
            greenlet = self.streams.get(stream_key)
            ref = greenlet.stream_ref
            self.logger.info(u'[%s] removing stream with filters %s...' % (
                stream_key, unicode(ref.filters)[:60]))
            self.remove_stream(ref, event=Events.EVENT_SUSPEND)

        # add new streams
        for stream_ref in stream_refs_to_add:
            self.add_stream(stream_ref)

        self.update_interim_channels()

    def update_interim_channels(self):
        from solariat_bottle.db.channel.base import Channel

        for channel in Channel.objects(status="Interim"):
            self.logger.info("activate channel: %s, %s" % (
                channel.title, channel.id))
            channel.update(status="Active")

    def process_reconnects(self):
        while self.reconnect_bucket and not self.stopped():
            stream_key = self.reconnect_bucket.pop()
            if stream_key in self.streams:
                stream = self.streams[stream_key]
                ref = stream.stream_ref
                self.remove_stream(ref)
                self.add_stream(ref)


class PublicStreamBot(BaseStreamBot):

    def __init__(self, username, lockfile, concurrency=1, heartbeat=60,
                 stream_manager_cls=None, db_events=None, logger=LOGGER,
                 only_accounts=[], exclude_accounts=[],
                 max_track=400, max_follow=5000, use_kafka=False,
                 bot_user_agent='SocialAnalytics ps 1.0', **kwargs):
        stream_manager_cls = stream_manager_cls or PublicStreamManager
        db_events = db_events or PublicStreamDbEvents()
        self.only_accounts = only_accounts
        self.exclude_accounts = exclude_accounts
        self.max_track = max_track
        self.max_follow = max_follow
        self.kwargs = kwargs
        self.username = username
        self.use_kafka = use_kafka
        self.bot_user_agent = bot_user_agent
        kwargs.update(user_agent='PublicStreamBot-FeedApi')

        super(PublicStreamBot, self).__init__(username, lockfile, concurrency,
                                              heartbeat, stream_manager_cls,
                                              db_events, logger=logger, **kwargs)

    def store(self, filters):
        items = []

        def ensure_ids(iterable):
            result = []
            for item in iterable:
                if item:
                    if hasattr(item, 'id'):
                        result.append(item.id)
                    else:
                        result.append(item)
            return result

        for item in filters:
            track, follow, accounts, channels = item
            account_ids = ensure_ids(accounts)
            channel_ids = ensure_ids(channels)
            ref, is_new = StreamRef.objects.get_or_create(
                track=track,
                follow=follow,
                languages=get_languages(channels),
                account_ids=account_ids,
                channel_ids=channel_ids)
            items.append((ref, is_new))
        return items

    def get_stream_refs(self, only_accounts=None, exclude_accounts=None):
        only_accounts = only_accounts or self.only_accounts
        exclude_accounts = exclude_accounts or self.exclude_accounts
        exclude = set(exclude_accounts)
        only = set(only_accounts) - exclude
        from solariat.utils.iterfu import flatten
        from solariat_bottle.utils.tracking import get_channel_post_filters_map, combine_and_split

        channels = set(flatten(acct.get_current_channels(status__in={'Active', 'Interim'}) for acct in only))

        channel_filters_map = get_channel_post_filters_map(channels)
        if not channels:
            channel_filters_map = {
                channel: keywords
                for channel, keywords in channel_filters_map.iteritems()
                if channel.account not in exclude
            }

        splitted_filters = combine_and_split(
            channel_filters_map,
            max_track=self.max_track,
            max_follow=self.max_follow)
        capacity = auth_pool.get_capacity()
        streams_needed = len(splitted_filters)
        if streams_needed > capacity:
            LOGGER.critical(u"Not enough apps. Required: %d Capacity: %d "
                            u"Omitting %s filters: %s" % (
                streams_needed, capacity,
                streams_needed - capacity, splitted_filters[capacity:]))
            splitted_filters = splitted_filters[:capacity]

        return self.store(splitted_filters)

    def signal(self, sgn):
        import signal

        if sgn == signal.SIGHUP:
            auth_pool.sync()
        super(PublicStreamBot, self).signal(sgn)

    def get_status(self):
        status = super(PublicStreamBot, self).get_status()
        status['auth_pool'] = auth_pool.get_status()
        return status

    def dispatch(self, event_json):
        self.creators.receive((PUBLIC_TWEET, event_json))

    def on_message(self, event_json, stream=None):
        self.dump_message(event_json)
        if 'id' in event_json:
            log_state(None, str(event_json['id']), PostState.ARRIVED_IN_BOT)
        self.checker.inc_received()
        if self.use_kafka:
            KafkaDataPreparation.on_message(self.username, (PUBLIC_TWEET, event_json), self.kwargs)
        else:
            self.dispatch(event_json)
        if 'id' in event_json:
            log_state(None, str(event_json['id']), PostState.ADDED_TO_WORKER_QUEUE)
        return True

    def on_start(self):
        StreamRef.objects.update_running_streams()


def parse_accounts(bot_options):
    from solariat_bottle.db.account import Account

    only_accounts = []
    if bot_options.only_accounts:
        only_ids = bot_options.only_accounts.split(',')
        only_accounts = Account.objects(id__in=only_ids)[:]

    exclude_accounts = []
    if bot_options.exclude_accounts:
        exclude_ids = bot_options.exclude_accounts.split(',')
        exclude_accounts = Account.objects(id__in=exclude_ids)[:]
    return {"only_accounts": only_accounts,
            "exclude_accounts": exclude_accounts}


def main(bot_options):
    LOG_FORMAT = '%(asctime)-15s (%(threadName)-9s) %(levelname)s %(message)s'
    setup_logger(LOGGER, level=LOG_LEVEL, format=LOG_FORMAT, patch_logging=True)
    setup_dumper(bot_options)
    params = get_bot_params(bot_options)
    if bot_options.use_kafka:
        kafka_options = parse_kafka_options(bot_options)
        KafkaProducer.setup_kafka_producer(kafka_options)
        params.update(use_kafka=True)
    params.update(stream_manager_cls=PublicStreamManager)
    params.update(parse_accounts(bot_options))
    print("Bot startup params", params)
    if bot_options.post_creator == 'factory_by_user':
        from solariat_bottle.workers import io_pool

        io_pool.run_prefork()
    tw_bot = PublicStreamBot(**params)
    tw_bot.start()
    tw_bot.listen_signals()


if __name__ == '__main__':
    options = parse_options()
    main(options)

