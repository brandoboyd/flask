from solariat_bottle.daemons.twitter.stream.common import gevent_patch, sleep, \
    get_bot_params, setup_dumper

gevent_patch()

from collections import defaultdict

from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel

from solariat_bottle.daemons.helpers import DIRECT_MESSAGE, DedupQueue
from solariat_bottle.daemons.twitter.stream.argparse import parse_options, parse_kafka_options
from solariat_bottle.daemons.twitter.stream.base.bot import BaseStreamBot
from solariat_bottle.daemons.twitter.stream.base.listener import BaseListener
from solariat_bottle.daemons.twitter.stream.base.manager import StreamManager
from solariat_bottle.daemons.twitter.stream.base.stream import BaseStream
from solariat_bottle.daemons.twitter.stream.common import StreamGreenlet
from solariat_bottle.daemons.twitter.stream.eventlog import Events, UserStreamDbEvents
from solariat_bottle.utils.tweet import TwitterApiWrapper
from solariat_bottle.utils.logger import setup_logger
from solariat.utils.timeslot import now, utc
from solariat_bottle.settings import LOGGER, LOG_LEVEL

from solariat_bottle.utils.config import sync_with_keyserver, SettingsProxy
from solariat_bottle.utils.posts_tracking import log_state, PostState
from solariat_bottle.daemons.twitter.stream.base.kafka_producer import KafkaProducer
from solariat_bottle.daemons.twitter.stream.base.kafka_message_preparation import KafkaDataPreparation

sync_with_keyserver()

from solariat.utils.http_proxy import enable_proxy
enable_proxy(settings=SettingsProxy({}))


try:
    assert False  # set to True to get debugger connected to thread worker

    import threading
    import pydevd

    pydevd.connected = True
    pydevd.settrace(suspend=False)
    threading.settrace(pydevd.GetGlobalDebugger().trace_dispatch)
except (ImportError, AssertionError):
    pass


class UserStreamListener(BaseListener):

    def __init__(self, stream, stream_manager, db=UserStreamDbEvents(), api=None):
        """
        :param stream: UserStream instance
        :param stream_manager: UserStreamMulti instance
        :param db: database logger
        :param api: optional, used for parsing in tweepy Stream,
                not needed since we parse manually
        """
        super(UserStreamListener, self).__init__(stream, stream_manager, db=db, api=api)

    def on_message(self, data):
        if 'event' in data:
            self.on_event(data)
            return True
        elif 'direct_message' in data:
            self.on_direct_message(data['direct_message'])
            return True
        if 'text' in data:  # bypass tweets/retweets/replies
            return True
        return False

    def on_connect(self):
        """Emitted by Stream when connected successfully"""
        self.log_event('connect')
        self.last_keep_alive = now()
        was_offline = self.db.last_online(self.stream_id)
        since = None
        if was_offline:
            _, _, since, self.last_status_id = was_offline

        self.set_event(Events.EVENT_ONLINE)

        MAX_OFFLINE_TIME = 1.5 * 24 * 60 * 60  # 36 hours

        too_old = not since or (now() - utc(since)).total_seconds() > MAX_OFFLINE_TIME
        if not was_offline or too_old:
            return

        filters = {
            "start_date": since and utc(since),
            "end_date": self.last_keep_alive and utc(self.last_keep_alive),
            "since_id": self.last_status_id
        }
        LOGGER.info(u'[%s] fetch offline direct messages with filters %s' % (self.stream_id, filters))

        from solariat_bottle.daemons.twitter.historics.timeline_request import DirectMessagesFetcher
        from solariat_bottle.utils.tweet import TwitterApiWrapper
        from solariat_bottle.daemons.twitter.parsers import DMTweetParser

        try:
            api = TwitterApiWrapper(auth_tuple=self.auth).api
            fetcher = DirectMessagesFetcher(api, **filters)
            parse = DMTweetParser()
            for dm in fetcher.fetch():
                self.on_direct_message(parse(dm))
            else:
                LOGGER.info(u'[%s] no offline direct messages' % (self.stream_id,))
        except:
            LOGGER.exception(u"[%s] fetch offline direct messages failed" % self.stream_id)

    def on_direct_message(self, status):
        LOGGER.debug(u"[%s] direct message: %s" % (self.stream_id, status))
        if 'id' in status:
            log_state(self.channel_id, str(status['id']), PostState.ARRIVED_IN_BOT)
            self.last_status_id = status['id']
        self.bot.on_direct_message(status, self.stream, channel_id=self.channel_id)

    def on_event(self, data):
        self.log_event(u'event: %s' % data, db_log=False)
        # self.bot.on_event(data, self.stream)


class UserStreamGreenlet(StreamGreenlet):
    pass


class UserStream(BaseStream):
    def __init__(self, *args, **kwargs):
        channel_id = kwargs.pop('channel_id', None)
        super(UserStream, self).__init__(*args, **kwargs)
        self.listener.channel_id = channel_id

    @staticmethod
    def ListenerCls():
        return UserStreamListener

    def start_stream(self):
        self.stream.userstream(stall_warnings=True)


class StreamRef(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class UserStreamMulti(StreamManager):

    def __init__(self, bot_instance, logger=LOGGER):
        super(UserStreamMulti, self).__init__(bot_instance, logger=logger)
        self.username_channels = defaultdict(set)  # username to channels map,
                                                   # each username may have multiple EnterpriseTwitterChannels

    def add_stream(self, stream_ref, auth, channel=None):
        stream_key = self.stream_ref_to_key(stream_ref)

        if stream_key not in self.streams:
            self.logger.info('[%s] %s adding stream with auth: %s' % (
                stream_key, channel, auth))
            greenlet = UserStream(stream_ref, auth, self,
                                  db=UserStreamDbEvents(),
                                  bot_user_agent=self.bot_user_agent,
                                  channel_id=channel.id,
                                  ).as_greenlet()
            self.stream_threads.start(greenlet)
            self.streams[stream_key] = greenlet
        else:
            stream = self.streams[stream_key]
            existing_auth = stream.auth_params
            if existing_auth != auth:
                # update stream
                self.logger.info(
                    '[%s] %s updating stream:'
                    ' auth credentials changed\nold=%s\nnew=%s' % (
                        stream_key, channel, existing_auth, auth))
                stream.auth_params = auth

        if channel:
            self.username_channels[stream_key].add(channel)

    def remove_stream(self, stream_ref, channel=None, event=Events.EVENT_OFFLINE):
        stream_key = self.stream_ref_to_key(stream_ref)

        if channel:
            self.username_channels[stream_key].discard(channel)
            # if still have active channels for that username don't kill stream
            should_kill = not self.username_channels[stream_key]
        else:
            del self.username_channels[stream_key]
            should_kill = True

        if should_kill:
            greenlet = self.streams.pop(stream_key, None)
            greenlet._stream.listener.set_event(event)
            if greenlet:
                self.stream_threads.killone(greenlet,
                                            block=False,
                                            timeout=self.STREAM_KILL_TIMEOUT)

    @staticmethod
    def stream_ref_to_key(ref):
        if hasattr(ref, 'id'):
            uname = ref.id
        elif isinstance(ref, basestring):
            uname = ref
        else:
            raise ValueError("Undefined stream reference %s of type %s" % (
                ref, type(ref)))

        if uname.startswith('@'):
            return uname[1:].lower()
        else:
            return uname.lower()

    def sync_streams(self):
        self.logger.debug('synchronizing streams')

        def iter_users():
            usernames = []
            for channel in EnterpriseTwitterChannel.objects(status__in={'Active', 'Interim'}):
                if channel.is_authenticated and channel.twitter_handle:
                    usernames.append((
                        channel.twitter_handle,
                        TwitterApiWrapper.get_auth_parameters(channel),
                        channel))
                else:
                    self.logger.warning(u"Active channel %s (%s) is not authenticated", channel, channel.title)
            return usernames

        remaining_usernames = set(self.streams)

        for (username, auth, channel) in iter_users():
            ref = StreamRef(id=username)
            uname = self.stream_ref_to_key(ref)
            self.add_stream(ref, auth, channel)
            remaining_usernames.discard(uname)

        # kill old streams
        for username in remaining_usernames:
            self.logger.info('[%s] removing stream (channel deactivated %s)' % (
                username, self.username_channels.get(username)))
            self.remove_stream(StreamRef(id=username), event=Events.EVENT_SUSPEND)

    def process_reconnects(self):
        while self.reconnect_bucket and not self.stopped():
            stream_key = self.reconnect_bucket.pop()
            if stream_key in self.streams:
                stream = self.streams[stream_key]
                auth = stream.auth_params
                channels = self.username_channels[stream_key]
                ref = StreamRef(id=stream_key)
                for channel in channels:
                    self.remove_stream(ref, channel)
                    self.add_stream(ref, auth, channel)


class UserStreamBot(BaseStreamBot):
    def __init__(self, username, lockfile, concurrency=1, heartbeat=60,
                 stream_manager_cls=None, db_events=None, logger=LOGGER,
                 use_kafka=False, bot_user_agent='SocialAnalytics us 1.0', **kwargs):
        self.kwargs = kwargs
        self.username = username
        self.use_kafka = use_kafka
        self.bot_user_agent = bot_user_agent
        stream_manager_cls = stream_manager_cls or UserStreamMulti
        db_events = db_events or UserStreamDbEvents()
        super(UserStreamBot, self).__init__(username, lockfile, concurrency,
                                            heartbeat, stream_manager_cls,
                                            db_events, logger=logger, **kwargs)
        self.dedup_q = DedupQueue(maxlen=10)

    def dedup(self, dm):
        key = dm['id']
        return self.dedup_q.append(key)

    def on_direct_message(self, dm, stream=None, channel_id=None):
        self.checker.inc_received()

        if self.dedup(dm):
            if self.use_kafka:
                KafkaDataPreparation.on_message(self.username, (DIRECT_MESSAGE, dm), self.kwargs)
            else:
                self.creators.receive((DIRECT_MESSAGE, dm))
            log_state(channel_id, str(dm['id']), PostState.ADDED_TO_WORKER_QUEUE)
        else:
            self.logger.debug(u"Duplicated direct message %s", dm['id'])

    def on_event(self, event, stream=None):
        """Deprecated
        Handling follow/unfollow events is disabled
        in favor of the twitter api requests cache
        """
        raise DeprecationWarning("UserStreamBot.on_event")
        from solariat_bottle.tasks.twitter import twitter_stream_event_handler

        stream_data = None
        if stream:
            stream_data = {'channel_id': getattr(stream, 'channel', None),
                           'screen_name': stream.stream_id}
        self.checker.inc_received()
        if self.use_kafka:
            KafkaDataPreparation.on_event(event, stream_data)
        else:
            twitter_stream_event_handler(event, stream_data)

    def on_message(self, event_json, stream=None):
        self.dump_message(event_json)
        if 'direct_message' in event_json:
            self.on_direct_message(event_json['direct_message'])

        if 'event' in event_json and event_json['event'] in {'follow', 'unfollow'}:
            self.on_event(event_json, stream)


def main(bot_options):
    LOG_FORMAT = '%(asctime)-15s (%(threadName)-9s) %(levelname)s %(message)s'
    setup_logger(LOGGER, level=LOG_LEVEL, format=LOG_FORMAT, patch_logging=True)
    setup_dumper(bot_options)

    stream_manager_cls = None
    if bot_options.use_curl:
        from solariat_bottle.daemons.twitter.twitter_bot_dm_curl import UserStreamMulti as CurlUserStreamMulti
        stream_manager_cls = CurlUserStreamMulti
    params = get_bot_params(bot_options)
    params.update(stream_manager_cls=stream_manager_cls)
    if bot_options.use_kafka:
        kafka_options = parse_kafka_options(bot_options)
        KafkaProducer.setup_kafka_producer(kafka_options)
        params.update(use_kafka=True)
    print("Bot startup params", params)
    if bot_options.post_creator == 'factory_by_user':
        from solariat_bottle.workers import io_pool

        io_pool.run_prefork()
    tw_bot = UserStreamBot(**params)
    tw_bot.start()
    tw_bot.listen_signals(on_gevent=True)


if __name__ == '__main__':
    options = parse_options()
    main(options)
