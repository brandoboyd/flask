from solariat.gevent import gevent_patch
gevent_patch()

import gevent
from solariat_bottle.daemons.helpers import StoppableThread
from tweepy.streaming import Stream
import time


def sleep(seconds):
    # print('%s.%s(%s)' % (time.sleep.__module__, time.sleep.__name__, seconds))
    time.sleep(seconds)


def on_test():
    from solariat_bottle.settings import get_var

    return get_var('ON_TEST')


def setup_dumper(options):
    from logging          import NullHandler, getLogger, Formatter, INFO
    from logging.handlers import WatchedFileHandler

    dumper = getLogger('dumper')
    dumper.setLevel(INFO)

    if options.dumpfile:
        handler = WatchedFileHandler(options.dumpfile, delay=True)
    else:
        handler = NullHandler()

    dumper.addHandler(handler)

    formatter = Formatter("%(message)s")
    handler.setFormatter(formatter)

    return dumper


def get_bot_params(options):
    from solariat_bottle.daemons.helpers import PostCreator, FeedApiPostCreator
    post_creator_factory = {
        'factory_by_user': PostCreator,
        'http_post_api': FeedApiPostCreator
    }
    params = dict(
        username=options.username,
        lockfile=options.lockfile,
        concurrency=options.concurrency,
        multiprocess_concurrency=options.multiprocess_concurrency,
        password=options.password,
        url=options.url,
        post_creator=post_creator_factory.get(options.post_creator))
    if options.bot_user_agent:
        params['bot_user_agent'] = options.bot_user_agent
    return params


class StreamWrapper(Stream):
    """Thin wrapper to notify StreamListener when connection closed by twitter.
    tweepy==3.3.0 does not.
    """
    def on_closed(self, resp):
        """Twitter closed response -
        should be handled the same way as on_disconnect.
        """
        self.listener.on_closed()


class StreamGreenlet(gevent.Greenlet):
    def __init__(self, stream):
        self._stream = stream
        super(StreamGreenlet, self).__init__(run=stream.run)

    def __getattr__(self, item):
        if item in {'auth_params', 'stream_ref', 'stream_id', 'listener'}:
            # proxy some methods to inner stream for easier access
            return getattr(self._stream, item)

    def kill(self, exception=gevent.GreenletExit, block=True, timeout=None):
        self._stream.kill()
        super(StreamGreenlet, self).kill(exception, block, timeout)


class TestStream(StoppableThread):
    def __init__(self, listener, *args, **kwargs):
        super(TestStream, self).__init__(*args, **kwargs)
        self.listener = listener
        from Queue import Queue

        self.q = Queue()

    def proxy(self, method, *args, **kwargs):
        print('call %s.%s' % (self.listener.__class__.__name__, method))
        return getattr(self.listener, method)(*args, **kwargs)

    def send(self, event='on_data', *args, **kwargs):
        if event == 'on_data' and isinstance(args[0], dict):
            # userstream listener expects json string
            import json
            msg = json.dumps(args[0])
            args = (msg,) + tuple(args[1:])
            self.listener.keep_alive()

        self.q.put((event, args, kwargs))

    def next(self):
        event, args, kwargs = self.q.get()
        self.proxy(event, *args, **kwargs)

    def run(self):
        from Queue import Empty

        self._stop.clear()
        while not self.stopped():
            try:
                self.next()
            except Empty:
                sleep(5.0)
                pass
