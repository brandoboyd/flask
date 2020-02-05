from solariat.utils.timeslot import now
from solariat_bottle.tests.base import BaseCase
from solariat_bottle.utils.tweet import RateLimitedTwitterApiWrapper, TwitterApiRateLimitError, CachedTwitterProxy
from solariat_bottle.utils.cache import MongoDBCache, CacheEntry
from mock import patch, PropertyMock
import tweepy
import requests
from functools import partial


def get_test_auth_settings():
    return 'test_consumer_key', 'test_consumet_secret', 'test_access_token', 'test_access_token_secret'


class TestMongoDBCache(BaseCase):
    """docstring for TestTwitterRateLimits"""

    METHOD_NAME = 'show_friendship'

    def setUp(self):
        super(TestMongoDBCache, self).setUp()
        self.api_calls = 0

    def api_show_friendship_success(self, api, source_id=5091001, target_id=None):
        self.api_calls += 1
        return {
            "relationship": {
                "target": {
                    "id_str": str(target_id),
                    "id": target_id,
                    "screen_name": "ernie",
                    "following": True,
                    "followed_by": False,
                },
                "source": {
                    "can_dm": True,
                    "id_str": str(source_id),
                    "id": source_id,
                    "following": False,
                    "followed_by": True,
                },
            }
        }

    def api_show_friendship_error(self, api, source_id=5091001, target_id=None):
        self.api_calls += 1
        resp = requests.Response()
        resp.status_code = 429
        setattr(api.base_api, 'last_response', resp)
        twitter_rate_limit_parsed = [{"code": 88, "message": "Rate limit exceeded"}]
        raise tweepy.TweepError(twitter_rate_limit_parsed, resp)

    def test_cache_unit(self):
        cache = MongoDBCache()
        self.assertTrue(cache.get(1) is None)
        key, val = 1, 1
        cache.set(key, val)
        self.assertEqual(cache.get(key), val)
        self.assertEqual(cache.get_entry(key).result(), val)
        self.assertTrue(cache.has(key))
        self.assertFalse(cache.get_entry(key).expired())
        cache.delete(key)
        self.assertTrue(cache.get(key) is None)

        # test expiration
        cache.set(key, val, timeout=0)
        self.assertTrue(cache.get_entry(key).expired())
        self.assertEqual(cache.get(key), None)

    def test_cache_integration(self):
        with patch('tweepy.API.%s' % self.METHOD_NAME, new_callable=PropertyMock) as show_friendship:
            api_proxy = RateLimitedTwitterApiWrapper.init_with_settings(get_test_auth_settings())
            show_friendship.return_value = partial(self.api_show_friendship_success, api_proxy)
            api = CachedTwitterProxy(api_proxy)
            kwargs = dict(target_id=4901238411)

            # set cache
            resp = api.show_friendship(**kwargs)
            self.assertTrue('relationship' in resp)
            self.assertEqual(self.api_calls, 1)

            # use cache
            cached_resp = api.show_friendship(**kwargs)
            self.assertEqual(self.api_calls, 1, 'API must not be requested')
            self.assertEqual(resp, cached_resp)

            # emulate error, cached value should be used
            show_friendship.return_value = partial(self.api_show_friendship_error, api_proxy)
            api = CachedTwitterProxy(api_proxy)
            cache = api.cache

            key = api.make_cache_id('show_friendship', {}, kwargs)
            expired = now()
            cache.coll.update(CacheEntry(key), {'$set': {'expiresAt': expired}})

            resp = api.show_friendship(**kwargs)
            self.assertEqual(self.api_calls, 2)
            self.assertEqual(resp, cached_resp)

            # emulate exception, when no cache found
            cache.coll.remove(CacheEntry(key))
            with self.assertRaises(TwitterApiRateLimitError) as assert_cm:
                resp = api.show_friendship(**kwargs)
