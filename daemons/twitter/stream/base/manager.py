import time
from solariat_bottle.daemons.helpers import StoppableThread
from solariat_bottle.settings import LOGGER
from gevent.pool import Group
from solariat_bottle.daemons.twitter.stream.eventlog import Events
from solariat_bottle.daemons.twitter.stream.base.stream import BaseStream
from solariat_bottle.daemons.twitter.stream.common import on_test, sleep
from solariat_bottle.daemons.twitter.stream.reconnect_stat import ReconnectStat
from solariat.utils.timeslot import now


class StreamManager(StoppableThread):
    STREAM_KILL_TIMEOUT = 30
    SYNC_INTERVAL = 60

    @staticmethod
    def StreamCls():
        return BaseStream

    def __init__(self, bot_instance, logger=LOGGER):
        super(StreamManager, self).__init__(name=self.__class__.__name__)
        self.daemon = True
        self.logger = logger
        self.streams = {}  # stream key to stream map

        self.last_sync = None
        self.bot_instance = bot_instance
        self.bot_user_agent = bot_instance.bot_user_agent

        self.stream_threads = Group()
        self.reconnect_bucket = set()
        self.reconnect_stat = ReconnectStat()

    @staticmethod
    def stream_ref_to_key(ref):
        """
        :param ref: instance of StreamRef or stream id
        :return: stream id
        """
        if hasattr(ref, 'key'):
            return ref.key
        elif hasattr(ref, 'id'):
            return ref.id
        elif isinstance(ref, (int, long, basestring)):
            return ref
        else:
            raise ValueError("Undefined stream reference %s of type %s" % (
                ref, type(ref)))

    def add_stream(self, stream_ref, *args, **kwargs):
        raise NotImplementedError()

    def remove_stream(self, stream_ref):
        raise NotImplementedError()

    def heartbeat(self):
        for greenlet in self.stream_threads:
            stream = greenlet._stream
            if stream.is_alive():
                stream.listener.set_event(Events.EVENT_KEEP_ALIVE)

    def sync_streams(self):
        self.logger.debug('synchronizing streams')

    def process_reconnects(self):
        self.logger.debug('processing reconnect bucket')

    def run(self):
        while not self.stopped():
            try:
                # process usernames in reconnect bucket
                self.process_reconnects()
                self.reconnect_stat.log_frequent_reconnects(len(self.streams))

                # scan db for changes
                if not self.last_sync or (time.time() - self.last_sync) > self.SYNC_INTERVAL:
                    self.sync_streams()
                    self.last_sync = time.time()
            except Exception, err:
                LOGGER.error(err, exc_info=True)
            finally:
                # switch greenlet
                if on_test():
                    sleep(1.0)
                else:
                    sleep(max(1.0, self.SYNC_INTERVAL / 2))

    def on_disconnect(self, stream_ref, exc=None):
        """Handler for disconnect events
        :param stream_ref: twitter stream reference
        :param exc: exception raised during processing stream
        """
        stream_key = self.stream_ref_to_key(stream_ref)
        if stream_key in self.streams:
            self.reconnect_stat.add(stream_key, ex=exc)
            if exc is None:
                # don't reconnect immediately when unexpected exception occurred,
                # this can be continuous network failure or inner bot error,
                # let next sync_streams() handle it
                self.reconnect_bucket.add(stream_key)
            else:
                self.remove_stream(stream_ref)
        else:
            self.sync_streams()
            self.last_sync = time.time()

    def stop(self):
        self.logger.info("STOP StreamManager")
        self.logger.info("StreamManager: stop workers")
        self.stream_threads.kill(
            block=True,
            timeout=len(self.stream_threads) * self.STREAM_KILL_TIMEOUT)
        self.logger.info("StreamManager: stop main thread")
        super(StreamManager, self).stop()

    def isAlive(self):
        main_thread_running = super(StreamManager, self).isAlive()
        streams_running = len(self.stream_threads) > 0
        self.logger.debug("StreamManager.isAlive main: %s workers: %s" % (
            main_thread_running, streams_running))
        return main_thread_running or streams_running

    def get_status(self):
        max_show = 10
        stream_keys = sorted(self.streams.keys())

        stream_stats = {
            "alive": self.isAlive(),
            "reconnect_bucket": list(self.reconnect_bucket),
            "last_sync": self.last_sync,
            "streams": {
                "total": len(self.stream_threads),
                "alive": len(filter(
                    lambda greenlet: greenlet._stream.is_alive(),
                    self.stream_threads)),
                "stream_keys_slice": map(str, stream_keys[:max_show])
            }
        }
        return stream_stats