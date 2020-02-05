#!/usr/bin/env python2.7

import json
import httplib2
import gevent

from gevent import monkey; monkey.patch_socket()
from gevent.coros import RLock

from solariat_bottle.settings import LOGGER


class FeedAPIError(Exception):
    "Base class for all FeedAPI exceptions."

class InfrastructureError(FeedAPIError):
    """Raised when httplib2 fails
    or HTTP server returns non 200 status."""

class ApplicationError(FeedAPIError):
    """Raised when HTTP server returns 200
    but json output non ok."""

class FeedAPI:

    authtoken = None
    authtoken_expired = set()
    lock = RLock()

    def __init__(self, queue, options):
        self.task_queue = queue
        self.options = options
        self.http = httplib2.Http(disable_ssl_certificate_validation=True)
        self.sleep_timeout = 30

    def handle_connection(self, url, method, body, headers=None):
        " perform connection and handle all errors "

        try:
            response, content = self.http.request(url, method, body, headers)
        except Exception as err:
            raise InfrastructureError(str(err))

        if response.status != 200:
            raise InfrastructureError('HTTP Status: %d' % response.status)

        try:
            data = json.loads(content)
        except ValueError:
            raise ApplicationError(content)

        if not data['ok']:
            raise ApplicationError(data['error'])

        return data

    def __gen_authtoken(self):
        " request new auth token "

        post_data = {
            'username': self.options.username,
            'password': self.options.password
        }

        url = '%s/api/v1.2/authtokens' % self.options.url
        headers = {'Content-Type': 'application/json'}
        body = json.dumps(post_data)

        while True:
            try:
                response = self.handle_connection(url, 'POST', body, headers)
            except FeedAPIError as err:
                LOGGER.error(err, exc_info=True)
                gevent.sleep(self.sleep_timeout)
            else:
                authtoken = response['item']['token'].encode('utf-8')
                self.__class__.authtoken = authtoken
                return authtoken

    def get_authtoken(self, old_authtoken):
        " exclusively tries to get new auth token or return cached "

        with self.lock:
            if old_authtoken == None:
                if self.__class__.authtoken:
                    return self.__class__.authtoken
                return self.__gen_authtoken()
            if old_authtoken not in self.__class__.authtoken_expired:
                self.__class__.authtoken_expired.add(old_authtoken)
                return self.__gen_authtoken()
            return self.__class__.authtoken

    def run(self):

        post_data = None
        authtoken = None
        expired_authtoken = None

        while True:
            if not authtoken:
                authtoken = self.get_authtoken(expired_authtoken)
            if not post_data:
                post_data = self.task_queue.get()

            url = '%s/api/v1.2/posts?token=%s' % (
                    self.options.url, authtoken)
            headers = {'Content-Type': 'application/json'}

            try:
                self.handle_connection(url, 'POST', post_data, headers)
            except ApplicationError as err:
                if str(err) == 'Auth token %s is expired' % authtoken:
                    LOGGER.info(err)
                    expired_authtoken = authtoken
                    authtoken = None
                else:
                    LOGGER.error(err)
                    post_data = None
                    self.task_queue.task_done()
            except InfrastructureError as err:
                LOGGER.error(err, exc_info=True)
                gevent.sleep(self.sleep_timeout)
            else:
                post_data = None
                self.task_queue.task_done()
