from solariat_bottle.settings import LOGGER
from Queue import Queue
from threading import RLock


class AuthPool(object):
    _lock = RLock()

    def __init__(self):
        self._resource = Queue()
        self._in_use = {}
        self.sync()

    def put(self, auth):
        with self._lock:
            if auth not in set(self._resource.queue):
                self._resource.put(auth)

    def sync(self):
        if self._in_use:
            LOGGER.warn(u"Sync auth pool while in use {}".format(self._in_use))
            self._in_use = {}
        for auth in AuthPool.get_auth_pool():
            self.put(auth)

    def get_status(self):
        return {
            'capacity': self.get_capacity(),
            'available': self.get_current_capacity(),
            'in_use': len(self._in_use)
        }

    @staticmethod
    def get_auth_pool():
        """Fetching AUTH_POOL from settings,
        AUTH_POOL is a list of tuples [(
            TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET,
            TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET), (...)]
        """
        from solariat_bottle.utils.config import sync_with_keyserver
        from solariat_bottle import settings

        sync_with_keyserver()
        return settings.get_var('AUTH_POOL', [AuthPool.get_auth_tuple()])

    @staticmethod
    def get_auth_tuple():
        from solariat_bottle.settings import \
            TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, \
            TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET

        return TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, \
               TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET

    def get_current_capacity(self):
        return self._resource.qsize()

    def get_capacity(self):
        return self._resource.qsize() + len(self._in_use)

    def acquire_for_stream(self, ref):
        LOGGER.info(u"Acquiring auth for stream %s" % ref)
        with self._lock:
            auth = self._resource.get()
            self._in_use[ref.key] = auth
            LOGGER.debug(u"In use: {}".format(self._in_use))
        return auth

    def release_for_stream(self, ref):
        LOGGER.info(u"Releasing auth for stream %s" % ref)
        with self._lock:
            if ref.key in self._in_use:
                auth = self._in_use.pop(ref.key)
                self.put(auth)
            else:
                auth = None
            LOGGER.debug(u"In use: {}".format(self._in_use))
        return auth