'''
Just a wrapper for facebook GraphAPI to allow proper testing
'''
import facebook
from collections import namedtuple

from solariat.db import fields
from solariat.db.abstract import Document, Manager
from solariat.exc.base import AppException
from solariat.utils.timeslot import now, utc, timedelta
from solariat_bottle.settings import LOGGER, FACEBOOK_API_VERSION
from solariat_bottle.utils.decorators import log_response


THROTTLING_USER = 17
THROTTLING_APP = 4
THROTTLING_API_PATH = 613
ERROR_MISUSE = 368
FB_RATE_LIMIT_ERRORS = [THROTTLING_USER, THROTTLING_APP, THROTTLING_API_PATH, ERROR_MISUSE]


class FacebookRateLimitError(AppException):
    def __init__(self, msg='Rate limit error.', e=None, description=None, http_code=None,
                 code=None, path=None, remaining_time=None):
        msg = u"%s code: %s path: %s remaining time: %s" % (msg, code, path, remaining_time)
        super(FacebookRateLimitError, self).__init__(msg, e, description, http_code)


def get_page_id(post):
    # Just return the page id for a post either based on parent or by splitting ID
    from solariat_bottle.db.post.facebook import FacebookPost
    source_id = post.wrapped_data['source_id']
    parent = post.parent
    while '_' in source_id:
        if parent and isinstance(parent, FacebookPost):
            source_id = parent.wrapped_data['source_id']
            parent = parent.parent
        else:
            source_id = source_id.split('_')[0]
    return source_id


def get_page_id_candidates(post):
    return filter(None, [
        post.native_data.get('page_id'),
        get_page_id(post)
    ])


class FacebookDriver(object):

    def __init__(self, token, channel=None):

        self.api = GraphAPI(access_token=token, channel=channel)


    @log_response(logger=LOGGER)
    def request(self, target, params):
        try:
            return self.api.request(target, params)
        except Exception, ex:
            LOGGER.error("Request to target %s with params %s raised %s " % (target, params, ex))
            raise


    @log_response(logger=LOGGER)
    def post(self, path, post_data):
        try:
            return self.api.request(path, post_args=post_data)
        except Exception, ex:
            LOGGER.error("POST to path %s with post parameters %s raised %s " % (path, post_data, ex))
            raise

    @log_response(logger=LOGGER)
    def get_object(self, sender_id, fields=None):
        try:
            if fields is not None:
                result = self.api.get_object(sender_id, fields=fields)
            else:
                result = self.api.get_object(sender_id)
            return result
        except Exception, ex:
            LOGGER.error("GET for id %s with fields %s raised %s " % (sender_id, fields, ex))
            raise

    def obtain_new_page_token(self, page_id):

        target = 'me/accounts'
        accounts = self.api.request(target)['data']
        account = [acc for acc in accounts if acc['id'] == page_id][0]

        return account['access_token']


class FacebookRequestLogManager(Manager):
    def search(self, from_date, to_date, access_token=None, channel=None):
        filters = dict(
            start_time__gte=from_date,
            start_time__lte=to_date
        )
        if access_token:
            filters.update(access_token=access_token)
        if channel:
            filters.update(channel=channel)
        return self.find(**filters)


class FacebookRequestLog(Document):
    channel = fields.ObjectIdField(null=True, db_field='cl')
    access_token = fields.StringField(db_field='tok')
    path = fields.StringField(db_field='uri')
    method = fields.StringField(db_field='m')
    args = fields.StringField(db_field='arg')
    post_args = fields.StringField(db_field='parg')
    start_time = fields.DateTimeField(db_field='ts')
    end_time = fields.DateTimeField(db_field='et')
    elapsed = fields.NumField(db_field='el')
    error = fields.StringField(db_field='er', null=True)

    indexes = [('start_time', 'access_token', 'path')]
    manager = FacebookRequestLogManager


class FacebookRateLimitInfoManager(Manager):

    def add_rate_limit_info(
            self, access_token, error_code, failed_request_time,
            path, wait_until, channel, after, log_item=None):
        find = {
            "wait_until": {"$gt": after},
            "access_token": access_token,
            "error_code": error_code,
            "path": path
        }
        update = {
            "access_token": access_token,
            "error_code": error_code,
            "path": path,
            "wait_until": wait_until,
            "failed_request_time": failed_request_time,
            "channel": channel,
            "log_item": log_item
        }
        return self.coll.update(find, update, upsert=True)

    def is_token_limited(self, access_token, path):
        query = {
            "access_token": access_token,
            "wait_until": {"$gt": now()},
            "$or": [
                {
                    "error_code": {"$in": [THROTTLING_USER, THROTTLING_APP]}
                },
                {
                    "error_code": {"$in": [ERROR_MISUSE, THROTTLING_API_PATH]},
                    "path": path
                }
            ]
        }
        return self.find_one(**query)

    def get_last_rate_limit_info(self, access_token, error_code=None, path=None):
        query = {"access_token": access_token}
        if error_code:
            query["error_code"] = error_code
        if error_code in [ERROR_MISUSE, THROTTLING_API_PATH] and path:
            query["path"] = path
        result = self.find(**query).sort(id=-1)[:1]
        return result and result[0]


BackOffStrategy = namedtuple('BackOffStrategy', ['start', 'end', 'factor'])


class FacebookRateLimitInfo(Document):
    access_token = fields.StringField()
    failed_request_time = fields.DateTimeField()
    error_code = fields.NumField(null=True, choices=FB_RATE_LIMIT_ERRORS + [None])
    path = fields.StringField()
    wait_until = fields.DateTimeField()
    channel = fields.StringField()
    log_item = fields.ObjectIdField()

    indexes = [('token', 'error_code')]
    manager = FacebookRateLimitInfoManager
    LIMITS_CONFIG = {
        THROTTLING_USER: BackOffStrategy(30*60, 30*60, 1.0),
        THROTTLING_APP: BackOffStrategy(225, 60*60, 2.0),
        ERROR_MISUSE: BackOffStrategy(60 * 60, 24 * 60 * 60, 3.0),
        THROTTLING_API_PATH: BackOffStrategy(60, 60*60, 2.0)
    }

    @property
    def wait_time(self):
        return (utc(self.wait_until) - utc(self.failed_request_time)).total_seconds()

    @property
    def remaining_time(self):
        return (utc(self.wait_until) - now()).total_seconds()

    @property
    def exc(self):
        return FacebookRateLimitError(
            code=self.error_code,
            remaining_time=self.remaining_time,
            path=self.path)


class GraphAPI(facebook.GraphAPI):
    """Wrapper for facebook GraphAPI"""
    def __init__(self, access_token=None, timeout=None, version=FACEBOOK_API_VERSION, channel=None):
        super(GraphAPI, self).__init__(access_token, timeout, version)
        if hasattr(channel, 'id'):
            channel_id = channel.id
        elif isinstance(channel, (basestring, fields.ObjectId)):
            channel_id = channel
        else:
            channel_id = None
        self._channel = channel_id

    def log_request(self, path, args, post_args, method, start, stop, error=None, format_exc=unicode):
        elapsed = (stop - start).total_seconds()

        log = FacebookRequestLog(
            channel=self._channel,
            access_token=self.access_token,
            path=path,
            method=method,
            args=unicode(args),
            post_args=unicode(post_args),
            start_time=start,
            end_time=stop,
            elapsed=elapsed,
            error=error and format_exc(error)
        )
        log.save()
        return log

    def check_rate_limits(self, path):
        manager = FacebookRateLimitInfo.objects
        rate_limit_info = manager.is_token_limited(self.access_token, path)
        if rate_limit_info:
            raise rate_limit_info.exc

    def _parse_fb_error_code(self, error):
        result = error.result
        try:
            error_code = result['error_code']
        except KeyError:
            try:
                error_code = result['error']['code']
            except:
                error_code = 0

        try:
            error_code = int(error_code)
        except:
            error_code = 0
        return error_code

    def handle_rate_limit_error(self, error, path, failed_request_time, log_item):
        manager = FacebookRateLimitInfo.objects
        error_code = self._parse_fb_error_code(error)
        if error_code not in FB_RATE_LIMIT_ERRORS:
            return None

        last_rate_limit_info = manager.get_last_rate_limit_info(
            self.access_token, error_code, path)
        back_off_config = FacebookRateLimitInfo.LIMITS_CONFIG[error_code]

        if last_rate_limit_info:
            last_wait_time = last_rate_limit_info.wait_time
            wait_time = timedelta(seconds=min(
                back_off_config.end, last_wait_time * back_off_config.factor))
            if utc(last_rate_limit_info.failed_request_time + wait_time) > utc(failed_request_time):
                wait_until = last_rate_limit_info.failed_request_time + wait_time
            else:
                wait_until = timedelta(seconds=back_off_config.start) + failed_request_time
        else:
            wait_until = timedelta(seconds=back_off_config.start) + failed_request_time
        after = last_rate_limit_info and last_rate_limit_info.wait_until
        return manager.add_rate_limit_info(
            self.access_token, error_code, utc(failed_request_time), path,
            utc(wait_until), str(self._channel), after, log_item)

    def request(
            self, path, args=None, post_args=None, files=None, method=None):

        start = now()
        self.check_rate_limits(path)
        try:
            response = super(GraphAPI, self).request(path, args, post_args, files, method)
        except facebook.GraphAPIError as error:
            log_item = self.log_request(path, args, post_args, method, start, now(), error)
            self.handle_rate_limit_error(error, path, failed_request_time=start, log_item=log_item.id)
            raise error

        self.log_request(path, args, post_args, method, start, now(), error=None)
        return response
