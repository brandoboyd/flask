from solariat_bottle.db import get_connection

from werkzeug.contrib.cache import BaseCache
from datetime import datetime, timedelta
from bson.binary import Binary
try:
    from solariat.utils.signed_pickle import SignedPickleError, signed_pickle as pickle
    pickle.dumps({"test": 1})
except (ImportError, SignedPickleError):
    try:
        import cPickle as pickle
    except ImportError:
        import pickle


class CacheEntry(dict):

    def __init__(self, key=None, data=None, timeout=0):
        if isinstance(key, dict):
            super(CacheEntry, self).__init__(key)
            return
        super(CacheEntry, self).__init__()
        self['_id'] = key
        if data is not None:
            data_blob = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
            self['data'] = Binary(data_blob)
            self['expiresAt'] = datetime.utcnow() + timedelta(seconds=timeout)

    def result(self):
        return pickle.loads(str(self['data']))

    def expired(self):
        now = datetime.utcnow()
        return self['expiresAt'] and self['expiresAt'] < now


class MongoDBCache(BaseCache):

    DEFAULT_TIMEOUT = 15 * 60

    def __init__(self, default_timeout=DEFAULT_TIMEOUT, coll_name=None):
        BaseCache.__init__(self, default_timeout)
        coll_name = coll_name or self.__class__.__name__
        self.coll = get_connection()[coll_name]

    def get(self, key):
        """Looks up key in the cache and returns the value for it.
        If the key does not exist `None` is returned instead.

        :param key: the key to be looked up.
        """
        entry = self.get_entry(key)
        if entry and not entry.expired():
            return entry.result()

    def get_entry(self, key):
        doc = self.coll.find_one(CacheEntry(key))
        if doc:
            return CacheEntry(doc)

    def set(self, key, value, timeout=None):
        """Adds a new key/value to the cache (overwrites value, if key already
        exists in the cache).

        :param key: the key to set
        :param value: the value for the key
        :param timeout: the cache timeout for the key (if not specified,
                        it uses the default timeout).
        """
        if timeout is None:
            timeout = self.default_timeout
        self.coll.update(CacheEntry(key), CacheEntry(key, value, timeout),
                         upsert=True, manipulate=True)

    def has(self, key):
        return self.coll.find(CacheEntry(key)).count() > 0

    def delete(self, key):
        self.coll.remove(CacheEntry(key))

    def invalidate(self, key):
        upd = {'expiresAt': datetime.utcnow() - timedelta(seconds=1)}
        self.coll.update(CacheEntry(key), {'$set': upd})

    def clear(self):
        # now = datetime_to_timestamp(datetime.now())
        # too_old = now - 15 * 60
        # self.coll.remove({'timeout': {'$lt': too_old}})
        pass
