from solariat_bottle.tests.base import BaseCase
from solariat_bottle.tests.data import __file__ as data_path
from solariat_bottle.utils.tweet import RateLimitedTwitterApiWrapper, TwitterApiRateLimitError, TwitterMediaFetcher
from solariat.utils.timeslot import now, datetime_to_timestamp

from mock import patch, PropertyMock
import tweepy
import requests
import json
from functools import partial
import os
from StringIO import StringIO


DATA_PATH = os.path.dirname(data_path)
QUARTER_HOUR_SEC = 15 * 60
RATE_LIMIT_CODE = 88
DAILY_RATE_LIMIT_CODE = 185

def fake_send_dm_rate_limit_headers_full(api_proxy, id_or_username, text=None):
    api = api_proxy.base_api
    resp = requests.Response()
    setattr(api, 'last_response', resp)
    resp.headers['X-Rate-Limit-Limit'] = '15'
    resp.headers['X-Rate-Limit-Remaining'] = '15'
    resp.headers['X-Rate-Limit-Reset'] = str(datetime_to_timestamp(now()) + QUARTER_HOUR_SEC)

    json_file = os.path.join(DATA_PATH, 'tw_dm.json')
    with open(json_file) as f:
        dm_json = json.load(f)

    dm = tweepy.models.DirectMessage.parse(api, dm_json)
    return dm

def fake_send_dm_rate_limit_headers_zero_remains(api_proxy, id_or_username, text=None):
    resp = requests.Response()
    setattr(api_proxy.base_api, 'last_response', resp)
    resp.headers['X-Rate-Limit-Limit'] = '15'
    resp.headers['X-Rate-Limit-Remaining'] = '0'
    resp.headers['X-Rate-Limit-Reset'] = str(datetime_to_timestamp(now()) + QUARTER_HOUR_SEC)
    raise tweepy.TweepError('Test rate limits (from headers) hit.', resp)

def fake_send_dm_rate_limit_in_err_body(api_proxy, id_or_username, text=None, code=RATE_LIMIT_CODE):
    resp = requests.Response()
    resp.status_code = 429
    setattr(api_proxy.base_api, 'last_response', resp)
    twitter_rate_limit_parsed = [{"code": code, "message": "Rate limit exceeded"}]
    raise tweepy.TweepError(twitter_rate_limit_parsed, resp)

def fake_download_media_err_response():
    resp = requests.Response()
    resp.status_code = 429  # Too Many Requests
    resp.encoding = 'utf8'
    resp._content = '{"errors":[{"message":"some rate limit happen","code":88}]}'.encode('utf8')
    resp._content_consumed = True
    return resp

def fake_download_media_success_response():
    media_file = os.path.join(DATA_PATH, 'tw_media.jpg')
    with open(media_file) as f:
        file_like = StringIO(f.read())

    resp = requests.Response()
    resp.status_code = 200
    resp.raw = file_like
    return resp

def get_test_auth_settings():
    return 'test_consumer_key', 'test_consumet_secret', 'test_access_token', 'test_access_token_secret'


class TestTwitterRateLimits(BaseCase):
    """docstring for TestTwitterRateLimits"""

    METHOD_NAME = 'send_direct_message'

    def test_headers_rate_limits_full(self):
        with patch('tweepy.API.%s' % self.METHOD_NAME, new_callable=PropertyMock) as send_dm_mock:
            api_proxy = RateLimitedTwitterApiWrapper.init_with_settings(get_test_auth_settings())
            send_dm_mock.return_value = partial(fake_send_dm_rate_limit_headers_full, api_proxy)

            resp = api_proxy.send_direct_message('username', text='some text')
            self.assertTrue(isinstance(resp, tweepy.models.DirectMessage))
            self.assertTrue(hasattr(api_proxy.base_api, 'last_response'), "api methods patched incorrect, api should \
                                            have :last_response attribute")

            limits = api_proxy.get_rate_limit(self.METHOD_NAME)
            self.assertTrue(limits is None, "No rate limits must be stored")

    def test_headers_rate_limits_hit(self):
        with patch('tweepy.API.%s' % self.METHOD_NAME, new_callable=PropertyMock) as send_dm_mock:
            api_proxy = RateLimitedTwitterApiWrapper.init_with_settings(get_test_auth_settings())
            send_dm_mock.return_value = partial(fake_send_dm_rate_limit_headers_zero_remains, api_proxy)

            with self.assertRaises(TwitterApiRateLimitError) as assert_cm:
                api_proxy.send_direct_message('username', text='some text')
            rate_limit_err = assert_cm.exception
            self.assertTrue(0 < rate_limit_err.wait_for <= QUARTER_HOUR_SEC,
                            "TwitterApiRateLimitError.wait_for param is incorrect")
            self.assertTrue(hasattr(api_proxy.base_api, 'last_response'),
                            "api methods patched incorrect, api should have :last_response attribute")

            # - check there is DB stored limit
            limits = api_proxy.get_rate_limit(self.METHOD_NAME)
            self.assertTrue(limits, "Rate limits must be stored")
            self.assertFalse(limits.is_manual(), "This is headers rate limits test")

            # call api again:
            # - check api does not called, and TwitterApiRateLimitError raised
            # - check there is the same DB stored limit
            reset = limits.reset
            delattr(api_proxy.base_api, 'last_response')
            with self.assertRaises(TwitterApiRateLimitError) as assert_cm:
                api_proxy.send_direct_message('username', text='another text')
            limits = api_proxy.get_rate_limit(self.METHOD_NAME)
            self.assertFalse(hasattr(api_proxy.base_api, 'last_response'),
                             "API method must not be called after a RateLimits is stored")
            self.assertEqual(reset, limits.reset, "Limits should not be changed in near 15 minutes")

            # check rate limits removed after successfull call
            limits.reset = datetime_to_timestamp(now()) - 1
            limits.save()
            send_dm_mock.return_value = partial(fake_send_dm_rate_limit_headers_full, api_proxy)
            resp = api_proxy.send_direct_message('username', text='success')
            self.assertTrue(isinstance(resp, tweepy.models.DirectMessage), "Got DM, response is OK")
            limits = api_proxy.get_rate_limit(self.METHOD_NAME)
            self.assertEqual(limits, None, "Rate Limits must be removed after successfull api call")

    def test_error_resp_rate_limits_hit(self):
        with patch('tweepy.API.%s' % self.METHOD_NAME, new_callable=PropertyMock) as send_dm_mock:
            api_proxy = RateLimitedTwitterApiWrapper.init_with_settings(get_test_auth_settings())
            send_dm_mock.return_value = partial(fake_send_dm_rate_limit_in_err_body, api_proxy)

            with self.assertRaises(TwitterApiRateLimitError) as assert_cm:
                api_proxy.send_direct_message('username', text='some text')
            rate_limit_err = assert_cm.exception
            self.assertTrue(0 < rate_limit_err.wait_for <= QUARTER_HOUR_SEC,
                            "TwitterApiRateLimitError wait_for params is incorrect")

            # - check there is DB stored limit
            limits = api_proxy.get_rate_limit(self.METHOD_NAME)
            self.assertTrue(limits, "Rate limits must be stored")
            self.assertTrue(limits.is_manual(), "This is error code based rate limits test")

            # call api again:
            # - check api does not called, and TwitterApiRateLimitError raised
            # - check there is the same DB stored limit
            reset = limits.reset
            delay = limits.delay
            delattr(api_proxy.base_api, 'last_response')
            with self.assertRaises(TwitterApiRateLimitError) as assert_cm:
                api_proxy.send_direct_message('username', text='another text')
            limits = api_proxy.get_rate_limit(self.METHOD_NAME)
            self.assertFalse(hasattr(api_proxy.base_api, 'last_response'),
                             "API method must not be called after a RateLimits is stored")
            self.assertEqual(reset, limits.reset, "Limits should not be changed in near 15 minutes")
            self.assertEqual(delay, limits.delay, "Limits should not be changed in near 15 minutes")

            # emulate we had wait for limits reset and try to execute api with error:
            # limits delay must be raised in 5 times
            # in the same test, we try another - DAILY rate limits code
            delay = limits.delay
            limits.reset = datetime_to_timestamp(now()) - 1
            limits.save()
            send_dm_mock.return_value = partial(fake_send_dm_rate_limit_in_err_body, api_proxy,
                                                code=DAILY_RATE_LIMIT_CODE)
            with self.assertRaises(TwitterApiRateLimitError):
                api_proxy.send_direct_message('username', text='totally another text')
            limits = api_proxy.get_rate_limit(self.METHOD_NAME)
            self.assertEqual(delay * 5, limits.delay)

            # check, limits.delay not increased > 125min
            delattr(api_proxy.base_api, 'last_response')
            for _ in xrange(5):
                limits = api_proxy.get_rate_limit(self.METHOD_NAME)
                limits.reset = datetime_to_timestamp(now()) - 1
                limits.save()
                with self.assertRaises(TwitterApiRateLimitError):
                    api_proxy.send_direct_message('username', text='totally another text')

            limits = api_proxy.get_rate_limit(self.METHOD_NAME)
            self.assertEqual(limits.delay, 125 * 60,
                             "Manual Rate Limits delay must not be > 125 min, but it is: %s sec" % limits.delay)

            # check is reset time updated
            wait_for = api_proxy.calc_wait(limits.reset)
            self.assertTrue(float(wait_for) / (125 * 60) > 0.99, "Manual Rate Limits reset time must be + 125 min now")

            # check rate limits removed after successfull call
            limits.reset = datetime_to_timestamp(now()) - 1
            limits.save()
            send_dm_mock.return_value = partial(fake_send_dm_rate_limit_headers_full, api_proxy)
            resp = api_proxy.send_direct_message('username', text='success')
            self.assertTrue(isinstance(resp, tweepy.models.DirectMessage), "Got DM, response is OK")
            limits = api_proxy.get_rate_limit(self.METHOD_NAME)
            self.assertEqual(limits, None, "Manual Rate Limits must be removed after successfull api call")

    def test_media_fetching_rate_limits_hit(self):
        with patch('requests.get') as get_resp_mock:
            FETCH_MEDIA_METHOD_NAME = "fetch_media"
            get_resp_mock.return_value = fake_download_media_err_response()

            fetcher = TwitterMediaFetcher(auth_tuple=get_test_auth_settings())
            media_url = 'https://ton.twitter.com/1.1/ton/data/dm/idfrom/idto/name.jpg'
            with self.assertRaises(TwitterApiRateLimitError):
                resp = fetcher.fetch_media(media_url)

            limits = fetcher.api.get_rate_limit(FETCH_MEDIA_METHOD_NAME)
            self.assertTrue(limits is not None, "Limits must be stored to DB")
            limits.reset = datetime_to_timestamp(now()) - 1
            limits.save()
            get_resp_mock.return_value = fake_download_media_success_response()
            resp = fetcher.fetch_media(media_url)
            self.assertTrue('media_data' in resp, "Something goes wrong")

            limits = fetcher.api.get_rate_limit(FETCH_MEDIA_METHOD_NAME)
            self.assertTrue(limits is None, "Limits must be deleted after successfull call")
