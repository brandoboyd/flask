""" Manager and its Workers that send messages via Twitter """
import functools
from solariat_bottle.utils.hash import mhash
from solariat_bottle.utils.cache import MongoDBCache
from solariat.utils.timeslot import now, datetime_to_timestamp

import re
import tweepy
from tweepy.parsers import JSONParser
from tweepy.binder import bind_api
from tweepy.utils import list_to_csv

from datetime import datetime
import contextlib
import threading

from solariat.exc.base import AppException
from solariat_bottle.db.twitter_rate_limit import TwitterRateLimit
from solariat_bottle.tasks.exceptions import TwitterCommunicationException, DirectMessageUnpermitted

from .oauth import get_twitter_oauth_credentials


MINUTE = 60  # seconds
THREAD_LOCAL_TWEEP_ERR_HANDLING_CONTEXT = threading.local()


class TwitterApiRateLimitError(TwitterCommunicationException):
    def __init__(self, method_name, wait_for, limits=None, **kwargs):
        self.method_name = method_name
        self.wait_for = wait_for
        user_info_prefix = self.user_info()

        if 'http_code' not in kwargs or 'error_code' not in kwargs:
            if kwargs.get('e', None):
                http_code, error_code = self.err_codes(kwargs['e'])
                if 'http_code' not in kwargs:
                    kwargs['http_code'] = http_code
                if 'error_code' not in kwargs:
                    kwargs['error_code'] = error_code

        is_db_hit_msg = 'Catch DB-stored RateLimit' if limits else 'Catch API RateLimit'
        self.msg = '%s%s, while invoke "%s", try again in %i seconds.' % (
            user_info_prefix, is_db_hit_msg, method_name, wait_for)
        super(TwitterApiRateLimitError, self).__init__(self.msg, **kwargs)

    def err_codes(self, e):
        error_code = -1
        if not isinstance(e, tweepy.TweepError) or e.response is None:
            return None, error_code

        resp = e.response
        msg = e.message
        if isinstance(msg[0], dict):
            error_code = msg[0].get('code', error_code)
        elif isinstance(msg[0], list):
            error_code = msg[0][0].get('code', error_code)
        return resp.status_code, error_code

    def user_info(self):
        err_ctx = get_err_context()
        screen_name = None
        if err_ctx:
            screen_name = getattr(err_ctx, 'screen_name', screen_name)
        user_info = '[%s] ' % screen_name if screen_name else ''
        return user_info


def get_err_context():
    global THREAD_LOCAL_TWEEP_ERR_HANDLING_CONTEXT
    try:
        return THREAD_LOCAL_TWEEP_ERR_HANDLING_CONTEXT
    except NameError:
        # no CONTEXT found
        return None

def clear_err_context():
    err_ctx = get_err_context()
    for key in dir(err_ctx):
        if key.startswith('_'):
            continue
        delattr(err_ctx, key)

@contextlib.contextmanager
def err_context():
    ctx = get_err_context()
    try:
        yield ctx
    except Exception as ex:
        raise ex
    finally:
        clear_err_context()

def handle_tweepy_error(err, screen_name=None, tweet_text=None, raise_ex=True, channel=None):
    """
    For a given `tweepy.error.TweepError` handle it by raising
    a proper SocialOptimzr exception with some nice message.

    Just have a nice entry where we can easily add handling for extra
    codes if needed.
    TODO: For now we just raise TwitterCommunicationException, might need to specialize it possible
    into our own hierachy of exceptions.
    """
    if not isinstance(err, AppException):
        err = AppException(err)
    error_code = None

    err_ctx = get_err_context()
    if err_ctx:
        screen_name = getattr(err_ctx, 'screen_name', screen_name)
        tweet_text = getattr(err_ctx, 'tweet_text', tweet_text)
        raise_ex = getattr(err_ctx, 'raise_ex', raise_ex)
        channel = getattr(err_ctx, 'channel', channel)

    if isinstance(err.message, str):
        msg = err.message
    else:
        if type(err.message[0]) in (dict,):
            error_code = err.message[0].get('code', None)
        elif type(err.message[0]) in (list,):
            error_code = err.message[0][0].get('code', None)
        # https://dev.twitter.com/docs/error-codes-responses
        if error_code == 32:
            msg = "Twitter could not authenticate you. <a href='/configure#/channels'>Configure</a> your outbound channel."
        elif error_code == 34:
            msg = "You are trying to send message to an invalid twitter name. "
            if screen_name: msg += "No user found with screen name: %s" % screen_name
        elif error_code == 88:
            msg = "Rate limit exceeded"
        elif error_code == 150:
            msg = "Attempt to send a direct message to someone who is not following you. "
            if screen_name: msg += "User %s needs to follow you before you can send him direct messages." % screen_name
            if raise_ex: raise DirectMessageUnpermitted(msg, error_code=error_code,
                                                        internal_code=DirectMessageUnpermitted.REFRESH_UI)
        elif error_code == 151:
            msg = "Sorry! Twitter has rejected your direct message because it contains a URL. This is a known issue they are having."
            if raise_ex: raise DirectMessageUnpermitted(msg, error_code=error_code,
                                                        internal_code=DirectMessageUnpermitted.KEEP_AS_DM)
        elif error_code == 170:
            msg = "Status is required, but got an empty value."
        elif error_code == 186:
            msg = "You are limited to 140 characters but the status you are posting is longer. "
            if tweet_text: msg += "Status: '%s' too long." % tweet_text
        elif error_code == 187:
            msg = "You are trying to post a duplicate status. "
            if tweet_text: msg += "Status: '%s' already posted." % tweet_text
        else:
            msg = "Twitter API call failed for some unhandled reason." + str(err)

    if channel is not None:
        msg += " Channel: " + str(channel)

    if raise_ex:
        raise TwitterCommunicationException(msg, error_code=error_code)
    else:
        return msg


def tweepy_user_to_user_profile(user):
    from solariat_bottle.db.user_profiles.user_profile import UserProfile

    UserProfile.objects.upsert('Twitter',
                               dict(screen_name=user.screen_name,
                                    user_id=user.id_str,
                                    name=user.name,
                                    location=user.location,
                                    platform_data=tweepy_entity_to_dict(user)))


def tweepy_entity_to_dict(entity):
    from tweepy.models import Model
    if isinstance(entity, Model):
        if hasattr(entity, '_json'):
            return getattr(entity, '_json')
        entry_dict = {}
        for key, val in entity.__dict__.iteritems():
            if key == '_api':
                continue
            if isinstance(val, Model):
                entry_dict[key] = tweepy_entity_to_dict(val)
            elif isinstance(val, datetime):
                entry_dict[key] = str(val)
            else:
                entry_dict[key] = val
        return entry_dict
    return entity


class TwitterApiExt(tweepy.API):
    """Extensions for tweepy API.

    Adds 'tweet_mode' parameter into
    home_timeline
    user_timeline
    search
    direct_messages
    sent_direct_messages

    Adds additional allowed parameters to update_status
    'tweet_mode', 'attachment_url', 'auto_populate_reply_metadata', 'exclude_reply_user_ids'

    Adds deprecation warning to update_with_media
    """

    _tweet_link_re = re.compile(r"http(s)?://(twitter\.com|t\.co)/([^\s]+)$",
                                re.IGNORECASE or re.MULTILINE or re.UNICODE)

    @staticmethod
    def extract_tweet_link(text):
        """Extracts the latest occurrence of tweet permalink in text.
        Returns a tuple of the updated text and the extracted link."""
        match = TwitterApiExt._tweet_link_re.search(text)
        link = None
        if match:
            link = match.group()
        if link:
            text = text[:text.index(link)].rstrip()
            link = link.strip()
        return text, link

    @property
    def home_timeline(self):
        """ :reference: https://dev.twitter.com/rest/reference/get/statuses/home_timeline
            :allowed_param:'since_id', 'max_id', 'count', 'tweet_mode'
        """
        return bind_api(
            api=self,
            path='/statuses/home_timeline.json',
            payload_type='status', payload_list=True,
            allowed_param=['since_id', 'max_id', 'count', 'tweet_mode'],
            require_auth=True
        )

    @property
    def user_timeline(self):
        """ :reference: https://dev.twitter.com/rest/reference/get/statuses/user_timeline
            :allowed_param:'id', 'user_id', 'screen_name', 'since_id', 'tweet_mode'
        """
        return bind_api(
            api=self,
            path='/statuses/user_timeline.json',
            payload_type='status', payload_list=True,
            allowed_param=['id', 'user_id', 'screen_name', 'since_id',
                           'max_id', 'count', 'include_rts', 'tweet_mode']
        )

    @property
    def search(self):
        """ :reference: https://dev.twitter.com/rest/reference/get/search/tweets
            :allowed_param:'q', 'lang', 'locale', 'since_id', 'geocode',
             'max_id', 'since', 'until', 'result_type', 'count',
              'include_entities', 'from', 'to', 'source', 'tweet_mode']
        """
        return bind_api(
            api=self,
            path='/search/tweets.json',
            payload_type='search_results',
            allowed_param=['q', 'lang', 'locale', 'since_id', 'geocode',
                           'max_id', 'since', 'until', 'result_type',
                           'count', 'include_entities', 'from',
                           'to', 'source', 'tweet_mode']
        )

    @property
    def direct_messages(self):
        """ :reference: https://dev.twitter.com/rest/reference/get/direct_messages
            :allowed_param:'since_id', 'max_id', 'count', 'tweet_mode'
        """
        return bind_api(
            api=self,
            path='/direct_messages.json',
            payload_type='direct_message', payload_list=True,
            allowed_param=['since_id', 'max_id', 'count', 'tweet_mode'],
            require_auth=True
        )

    @property
    def sent_direct_messages(self):
        """ :reference: https://dev.twitter.com/rest/reference/get/direct_messages/sent
            :allowed_param:'since_id', 'max_id', 'count', 'page', 'tweet_mode'
        """
        return bind_api(
            api=self,
            path='/direct_messages/sent.json',
            payload_type='direct_message', payload_list=True,
            allowed_param=['since_id', 'max_id', 'count', 'page', 'tweet_mode'],
            require_auth=True
        )

    def update_status(self, media_ids=None, *args, **kwargs):
        """ :reference: https://dev.twitter.com/rest/reference/post/statuses/update
            :reference: https://dev.twitter.com/overview/api/upcoming-changes-to-tweets
            :allowed_param:'status', 'in_reply_to_status_id', 'in_reply_to_status_id_str', 'lat', 'long', 'source', 'place_id', 'display_coordinates', 'media_ids',
            'tweet_mode', 'attachment_url', 'auto_populate_reply_metadata', 'exclude_reply_user_ids'
        """
        post_data = {}
        if media_ids is not None:
            post_data["media_ids"] = list_to_csv(media_ids)

        # extract attachment_url from tweet text
        if 'attachment_url' not in kwargs:
            text = kwargs.pop("status", None)
            text, link = TwitterApiExt.extract_tweet_link(text)
            post_data['status'] = text
            if link:
                post_data['attachment_url'] = link

        # exclude_reply_user_ids is a list of users excluded from reply metadata
        # when auto_populate_reply_metadata=true
        exclude_reply_user_ids = kwargs.pop('exclude_reply_user_ids', None)
        if exclude_reply_user_ids is not None:
            post_data['exclude_reply_user_ids'] = list_to_csv(exclude_reply_user_ids)

        api_call = bind_api(
            api=self,
            path='/statuses/update.json',
            method='POST',
            payload_type='status',
            allowed_param=['status', 'in_reply_to_status_id', 'in_reply_to_status_id_str', 'lat',
                           'long', 'source', 'place_id', 'display_coordinates',
                           'tweet_mode',
                           'attachment_url',
                           'auto_populate_reply_metadata',
                           'exclude_reply_user_ids'],
            require_auth=True
        )
        try:
            return api_call(post_data=post_data, *args, **kwargs)
        except tweepy.TweepError as exc:
            if "attachment_url parameter is invalid" in str(exc) and 'attachment_url' in post_data:
                # try sending original tweet if the extracted attachment url is invalid
                url = post_data.pop('attachment_url')
                post_data['status'] = u"%s %s" % (post_data['status'], url)
                return api_call(post_data=post_data, *args, **kwargs)
            raise exc

    def update_with_media(self, filename, *args, **kwargs):
        import logging
        logging.warning("update_with_media is deprecated. Use media_upload + update_status.")
        return super(TwitterApiExt, self).update_with_media(filename, *args, **kwargs)


class BaseTwitterApiWrapper(object):
    def __init__(self, channel=None, api=None, auth_tuple=None, **settings):
        self.api = channel and self.init_with_channel(channel) or api
        if not self.api:
            if settings:
                self.api = self.init_with_settings(**settings)
            if auth_tuple:
                # (consumer_key, consumer_secret,
                # access_token_key, access_token_secret)
                self.api = self.init_with_settings(*auth_tuple)

    @classmethod
    def make_api(cls, *args, **kwargs):
        return TwitterApiExt(*args, **kwargs)

    @classmethod
    def auth_from_settings(cls, consumer_key=None, consumer_secret=None,
                           access_token_key=None, access_token_secret=None):
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token_key, access_token_secret)
        return auth

    @classmethod
    def get_auth_parameters(cls, channel):
        (consumer_key, consumer_secret, _, access_token_key,
             access_token_secret) = get_twitter_oauth_credentials(channel)
        return consumer_key, consumer_secret, access_token_key, access_token_secret

    @classmethod
    def auth_from_channel(cls, channel):
        return cls.auth_from_settings(*cls.get_auth_parameters(channel))

    @classmethod
    def init_with_settings(cls, consumer_key=None, consumer_secret=None,
                           access_token_key=None, access_token_secret=None,
                           **kwargs):
        auth = cls.auth_from_settings(consumer_key, consumer_secret,
                                      access_token_key, access_token_secret)
        if 'parser' not in kwargs:
            kwargs['parser'] = JSONParser()
        api = cls.make_api(auth_handler=auth, **kwargs)
        return api

    @classmethod
    def init_with_channel(cls, channel, **kwargs):
        return cls.init_with_settings(*cls.get_auth_parameters(channel), **kwargs)


class TwitterApiProxy(object):

    def __init__(self, base_api):
        self.base_api = base_api

    def do_wrap(self, method_name, original_method):
        raise NotImplementedError('must return wrapped version of original_method')

    def __getattr__(self, method_name):
        original_method = getattr(self.base_api, method_name)
        if callable(original_method):
            return self.do_wrap(method_name, original_method)
        else:
            return original_method


class RateLimitedTwitterProxy(TwitterApiProxy):

    def __init__(self, base_api):
        super(RateLimitedTwitterProxy, self).__init__(base_api)
        from solariat_bottle.settings import LOGGER
        self.logger = LOGGER

    def make_request_id(self, method_name):
        auth = self.base_api.auth
        key = auth.consumer_key, auth.consumer_secret, \
              auth.access_token, auth.access_token_secret, \
              method_name
        hashed_key = mhash(key, n=128)
        return str(hashed_key)

    def calc_wait(self, reset_at):
        wait_for = reset_at - datetime_to_timestamp(now())
        return wait_for if wait_for > 0 else 0

    def get_rate_limit(self, method_name):
        request_id = self.make_request_id(method_name)
        return TwitterRateLimit.objects.find_one(id=request_id)

    def is_rate_limit_hit(self, method_name, limits):
        ''' returns seconds remaining to reset limit or None
        '''
        if limits and limits.remaining == 0:
            wait_for = self.calc_wait(limits.reset)
            if wait_for:
                self.logger.debug('[RateLimitedTwitterProxy: %s] Hit DB stored rate limits' % method_name)
                return wait_for
            else:
                if not limits.is_manual():
                    limits.delete()
                    self.logger.debug('[RateLimitedTwitterProxy: %s] Remove limits' % method_name)
                return None
        return None

    def is_headers_rate_limit(self, method_name):
        ''' check for limits in response headers
        '''
        if hasattr(self.base_api, 'last_response'):
            headers = self.base_api.last_response.headers
            found = ('X-Rate-Limit-Remaining' in headers) or \
                ('X-Rate-Limit-Reset' in headers) or \
                ('X-Rate-Limit-Limit' in headers)
            remaining = headers.get('X-Rate-Limit-Remaining')

            if found and remaining and int(remaining) == 0:
                self.logger.info('[RateLimitedTwitterProxy: %s] Found Rate Limits in Headers' % method_name)
                return True

        return False

    def is_manual_rate_limit(self, method_name, err):
        ''' check if rate limits error returned in response body
        '''
        error_code = 0
        if isinstance(err.message[0], dict):
            error_code = err.message[0].get('code', None)
        elif isinstance(err.message[0], list):
            error_code = err.message[0][0].get('code', None)

        if error_code == 88:
            self.logger.info('[RateLimitedTwitterProxy: %s] Found Rate Limits error in err msg' % method_name)
            return True

        if error_code == 185:
            self.logger.info('[RateLimitedTwitterProxy: %s] Found DAILY Rate Limits in err msg' % method_name)
            return True

        if error_code == 161:
            # http://support.twitter.com/articles/66885-i-can-t-follow-people-follow-limits
            self.logger.info('[RateLimitedTwitterProxy: %s] Found Following Rate Limits in err msg' % method_name)
            return True

        return False

    def store_manual_rate_limit_info(self, method_name, limits):
        ''' create manual rate limit in DB if such was found in response
            or increase delay if we catch limits again
            returns seconds remaining to reset limit
        '''
        if limits:
            if limits.delay < 125 * MINUTE:  # stop increasing delay after 125 min
                limits.delay *= 5
            limits.reset = datetime_to_timestamp(now()) + limits.delay
        else:
            delay = 5 * MINUTE
            reset = datetime_to_timestamp(now()) + delay
            limits = TwitterRateLimit(
                id=self.make_request_id(method_name),
                remaining=0,
                limit=-1,
                reset=reset,
                delay=delay)

        limits.save()
        self.logger.debug('[RateLimitedTwitterProxy: %s] Store manual rate limit delay: %s', method_name, limits.delay)
        return limits.delay

    def store_headers_rate_limit_info(self, method_name, limits):
        ''' returns seconds remaining to reset limit or None if no limits found
        '''
        headers = self.base_api.last_response.headers
        remaining = int(headers.get('X-Rate-Limit-Remaining'))
        reset = int(headers.get('X-Rate-Limit-Reset'))
        limit = int(headers.get('X-Rate-Limit-Limit'))

        request_id = self.make_request_id(method_name)
        wait_for = self.calc_wait(reset)
        limits = TwitterRateLimit(id=request_id, remaining=remaining, limit=limit, reset=reset)
        limits.save()
        self.logger.debug('[RateLimitedTwitterProxy: %s] Store rate limits from headers' % method_name)
        return wait_for

    def wrap_in_rate_limited(self, method_name, original_method):

        def _rate_limited(*args, **kwargs):
            limits = self.get_rate_limit(method_name)
            wait_for = self.is_rate_limit_hit(method_name, limits)
            if wait_for is not None:
                raise TwitterApiRateLimitError(method_name, wait_for, limits=limits)

            try:
                result = original_method(*args, **kwargs)
            except tweepy.TweepError as err:
                self.logger.debug('[RateLimitedTwitterProxy: %s] exception on invoking original_method' % method_name)
                wait_for = None
                if self.is_headers_rate_limit(method_name):
                    wait_for = self.store_headers_rate_limit_info(method_name, limits)
                elif self.is_manual_rate_limit(method_name, err):
                    wait_for = self.store_manual_rate_limit_info(method_name, limits)
                if wait_for is not None:
                    raise TwitterApiRateLimitError(method_name, wait_for, e=err)
                return handle_tweepy_error(err)
            else:
                if limits and limits.is_manual():
                    limits.delete()

            return result

        try:
            return functools.wraps(original_method)(_rate_limited)
        except AttributeError:
            return _rate_limited

    def do_wrap(self, method_name, original_method):
        return self.wrap_in_rate_limited(method_name, original_method)


def tweepy_cache_id(token, secret, method_name, args, kwargs):
    key = [token, secret, method_name]
    key = map(str, key)
    key.extend(map(str, args))
    [key.extend([k, str(v)]) for k, v in sorted(kwargs.iteritems())]
    return str(mhash(key, n=128))


class CachedTwitterProxy(TwitterApiProxy):

    def __init__(self, base_api, clear_cache=False):
        super(CachedTwitterProxy, self).__init__(base_api)
        from solariat_bottle.settings import LOGGER
        self.logger = LOGGER
        self.cache = MongoDBCache()
        self.clear_cache = clear_cache

    def make_cache_id(self, method_name, args, kwargs):
        auth = self.base_api.auth
        return tweepy_cache_id(auth.access_token, auth.access_token_secret, method_name,
                               args, kwargs)

    def wrap_in_cache(self, method_name, original_method):
        def _cached(*args, **kwargs):
            cache = self.cache
            cache_id = self.make_cache_id(method_name, args, kwargs)

            entry = cache.get_entry(cache_id)
            if not entry or entry.expired() or self.clear_cache:
                try:
                    res = original_method(*args, **kwargs)
                    cache.set(cache_id, res)
                    return res
                except Exception as ex:
                    if not entry:
                        self.logger.error(ex, exc_info=True)
                        raise ex
                    self.logger.warning(ex, exc_info=True)
            return entry.result()

        try:
            return functools.wraps(original_method)(_cached)
        except AttributeError:
            return _cached

    def do_wrap(self, method_name, original_method):
        return self.wrap_in_cache(method_name, original_method)


class RateLimitedTwitterApiWrapper(BaseTwitterApiWrapper):
    @classmethod
    def make_api(cls, *args, **kwargs):
        tweepy_api = super(RateLimitedTwitterApiWrapper, cls).make_api(*args, **kwargs)
        return RateLimitedTwitterProxy(tweepy_api)


class TwitterMediaFetcher(RateLimitedTwitterApiWrapper):

    @property
    def fetch_media(self):
        return self.api.wrap_in_rate_limited('fetch_media', self._fetch_media)

    def _fetch_media(self, media_url, base64encoded=True, data_uri=False):
        import base64
        import json
        import requests

        from solariat_bottle.settings import LOGGER

        auth = self.api.base_api.auth.apply_auth()

        resp = requests.get(media_url, auth=auth, stream=True)
        LOGGER.debug(u"Response headers: %s", resp.headers)

        if resp.status_code and not 200 <= resp.status_code < 300:
            try:
                error_msg = self.api.base_api.parser.parse_error(resp.text)
            except Exception:
                error_msg = "Twitter error response: status code = %s" % resp.status_code
            raise tweepy.error.TweepError(error_msg)

        data = resp.raw.read()
        if base64encoded:
            data = base64.b64encode(data)
            if data_uri:
                content_type = resp.headers.get('content-type', 'image/png')
                data = "data:%s;base64,%s" % (content_type, data)

        return {"media_data": data,
                "twitter_response_headers": json.dumps(dict(resp.headers))}


TwitterApiWrapper = RateLimitedTwitterApiWrapper
