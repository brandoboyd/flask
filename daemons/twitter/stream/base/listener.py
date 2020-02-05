import time
import json
from tweepy.streaming import StreamListener
from solariat_bottle.daemons.twitter.stream.eventlog import InMemEvents, Events
from solariat_bottle.settings import LOGGER
from solariat.utils.timeslot import now

sleep = time.sleep


class BaseListener(StreamListener):

    def __init__(self, stream, stream_manager, db=None, api=None, logger=LOGGER):

        super(BaseListener, self).__init__(api=api)
        self.logger = logger
        self.last_keep_alive = None
        self.last_event = None
        self.last_status_id = None
        self.stream = stream
        self.stream_id = stream.stream_id
        self.auth = stream.auth_params

        self.db = db or InMemEvents()
        self.stream_manager = stream_manager
        self.bot = stream_manager.bot_instance

    def on_message(self, message):
        """Override in subclasses"""
        raise NotImplementedError("on_message() undefined")

    def on_data(self, raw_data):
        """Called when raw data is received from connection.

        Override this method if you wish to manually handle
        the stream data. Return False to stop stream and close connection.
        """
        try:
            data = json.loads(raw_data)
        except ValueError:
            self.log_event("on_data() can't decode json: %s" % raw_data)
            return
        finally:
            self.last_keep_alive = now()

        if self.on_message(data):
            return
        # twitter warning events
        elif 'limit' in data:
            if self.on_limit(data['limit']) is False:
                return False
        elif 'disconnect' in data:
            if self.on_disconnect(data['disconnect']) is False:
                return False
        elif 'warning' in data:
            # warnings can be received only with stall_warnings=True
            if self.on_warning(data['warning']) is False:
                return False
        else:
            self.log_event("unknown message type: " + str(raw_data))

    def log_event(self, msg, db_log=True):
        self.logger.info(u"[%s] %s" % (self.stream_id, msg))
        if db_log:
            self.db.add_message(self.stream_id, msg, now())

    def on_connect(self):
        """Emitted by Stream when connected successfully"""
        self.log_event('connect')
        self.last_keep_alive = now()
        self.set_event(Events.EVENT_ONLINE)

    def keep_alive(self):
        """Emitted by Stream when twitter sends \r\n bytes or message chunks"""
        self.last_keep_alive = now()

    def on_error(self, status):
        """Emitted by Stream when http status != 200.
        Return False to break Stream reconnect loop.
        For 420 (rate limit) and 503 status codes let
        tweepy use back off reconnecting strategy."""
        self.log_event('http error %s' % status)
        self.set_event(Events.EVENT_OFFLINE)
        if status not in (420, 503):
            return False

    def on_exception(self, exception):
        """Emitted by Stream on exceptions during connection
        or stream data handling"""
        self.logger.warning(u"[%s]", self.stream_id, exc_info=True)
        self.log_event(u'exception %s' % exception)
        self.reconnect(exc=exception)

    def on_timeout(self):
        """Emitted by Stream on network connection timeout"""
        self.log_event('timeout')
        # no need to reconnect - Stream will snooze connection automatically
        self.set_event(Events.EVENT_OFFLINE)
        return True

    def on_closed(self):
        """Emitted by Stream when connection suddenly closed by twitter"""
        self.log_event('closed')
        self.reconnect()

    def on_limit(self, track):
        """Filtered stream has matched more Tweets
        than its current rate limit allows to be delivered.
        https://dev.twitter.com/streaming/overview/messages-types#limit_notices
        Emitted from self.on_data()
        """
        self.log_event('limit %s' % track)

    def set_event(self, event_type):
        # when stream killed due to channel deactivation
        # SUSPEND is set just before OFFLINE - keep only first
        already_set = (self.last_event and self.last_keep_alive and
                       self.last_event[0] == Events.EVENT_SUSPEND and
                       event_type == Events.EVENT_OFFLINE and
                       (self.last_event[2] - self.last_keep_alive).total_seconds() <= 1.0)
        # print('ALREADY SET', already_set, event_type)
        if event_type is not None and not already_set:
            self.last_event = (event_type, self.stream_id, self.last_keep_alive, self.last_status_id)
            # print('ADD event', self.last_event)
            self.db.add_event(*self.last_event)

    def reconnect(self, exc=None):
        self.log_event('reconnect')
        self.set_event(Events.EVENT_OFFLINE)
        self.stream_manager.on_disconnect(self.stream_id, exc=exc)

    def on_disconnect(self, notice):
        """https://dev.twitter.com/streaming/overview/messages-types#disconnect_messages
        Emitted from self.on_data()
        """
        self.log_event('disconnect %s' % (notice,))
        self.reconnect()  # let manager restart stream
        return False

    def on_warning(self, notice):
        """https://dev.twitter.com/streaming/overview/messages-types#stall_warnings
        Emitted from self.on_data()
        """
        self.log_event('warning %s' % notice)

    def on_kill(self):
        """Stop event from bot"""
        self.set_event(Events.EVENT_OFFLINE)
