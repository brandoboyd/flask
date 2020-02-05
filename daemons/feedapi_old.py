#!/usr/bin/env python2.7

""" This is a python client part of a subset of the Solariat REST API v1.2.
    Allows to create new posts.

    (deprecated)
"""

# TODO: port to httplib2 with utils.resource_pool.ResourcePool (see elasticsearch.py for example),
#       for pycurl does not play well with gevent.monkey.patch_all()

import pycurl
import json
import time
from cStringIO import StringIO
import threading

from solariat_bottle.settings    import LOGGER
from solariat_bottle.db.tracking import handle_post



class FeedAPIBase:

    def __init__(self, options):
        self.options = options
        self.buff = StringIO()
        self.conn = pycurl.Curl()
        self.conn.setopt(pycurl.WRITEFUNCTION, self.buff.write)

    def reset_buff(self):
        " clear StringIO buffer "
        self.buff.seek(0)
        self.buff.truncate()

    def handle_connection(self):
        " perform connection and handle all errors "

        try:
            self.conn.perform()
        except pycurl.error as err:
            raise InfrastructureError('pycurl.error: ' + err.args[1])

        response_code = self.conn.getinfo(self.conn.RESPONSE_CODE)
        if response_code != 200:
            raise InfrastructureError('HTTP Status: %d' % response_code)

        try:
            response = json.loads(self.buff.getvalue())
        except ValueError:
            raise ApplicationError(self.buff.getvalue())

        if not response['ok']:
            raise ApplicationError(response['error'])

        return response

    def get_channel_id(self):
        " get channel id, raise AssertionError if error "

        post_data = { 'username': self.options.username,
                      'password': self.options.password }

        self.conn.setopt(pycurl.URL, '%s/api/v1.2/authtokens' % self.options.url)
        self.conn.setopt(pycurl.POSTFIELDS, json.dumps(post_data))
        self.conn.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json'])
        self.reset_buff()
        response = self.handle_connection()
        token = response['item']['token'].encode('utf-8')

        self.conn.setopt(pycurl.URL,
            '%s/api/v1.2/channels?token=%s' % (self.options.url, token))
        self.conn.setopt(pycurl.HTTPGET, 1)
        self.reset_buff()
        response = self.handle_connection()

        channels = response['list']
        channel_id = False
        for _channel in channels:
            if _channel['title'] == self.options.channel:
                channel_id = _channel['id']
        assert channel_id, "%s: no such channel" % ( self.options.channel, )
        return channel_id


class FeedAPI(threading.Thread, FeedAPIBase):

    authtoken = None
    authtoken_expired = set()
    lock = threading.Lock()
    _counter = 0

    def __init__(self, args=(), kwargs=None):

        self.__class__._counter += 1
        threading.Thread.__init__(self, name='FeedAPI-%d' % self._counter)
        if kwargs is None:
            kwargs = {}
        self.task_queue = args[0]
        self.options = args[1]
        self.buff = StringIO()
        self.conn = pycurl.Curl()
        self.conn.setopt(pycurl.NOSIGNAL, 1)
        self.conn.setopt(pycurl.WRITEFUNCTION, self.buff.write)
        self.conn.setopt(pycurl.SSL_VERIFYPEER, 0)
        self.conn.setopt(pycurl.SSL_VERIFYHOST, 0)
        if 'User-Agent' in kwargs:
            self.conn.setopt(pycurl.USERAGENT, kwargs['User-Agent'])
        self.sleep_timeout = 30

    def run(self):

        post_data = None
        authtoken = None
        expired_authtoken = None

        while True:
            if not authtoken:
                authtoken = self.get_authtoken(expired_authtoken)
            if not post_data:
                post_data = self.task_queue.get()
            # This is used both by datasift and by twitter_bot_dm.
            # Just be safe, and in case we recieve a dict with no 'channels' key
            # do the processing here (as is the case with twitter_bot),
            # otherwise assume it was done before (as is the case with datasift_bot.
            if isinstance(post_data, dict) and 'channels' not in post_data:
                channels = handle_post('Twitter', post_data['user_profile'], post_data)
                if channels:
                    channels = [ str(c.id) for c in channels ]
                    post_data['channels'] = channels

                # we need this for getting channels only only
                if 'direct_message' in post_data:
                    del post_data['direct_message']

                post_data = json.dumps(post_data)

            self.reset_buff()
            self.conn.setopt(pycurl.POSTFIELDS, post_data)
            self.conn.setopt(pycurl.URL,
                '%s/api/v1.2/posts?token=%s' % (self.options.url, authtoken))
            self.conn.setopt(pycurl.HTTPHEADER,
                             ['Content-Type: application/json'])

            try:
                self.handle_connection()
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
                LOGGER.error(err)
                time.sleep(self.sleep_timeout)
            else:
                post_data = None
                self.task_queue.task_done()

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

    def __gen_authtoken(self):
        " request new auth token "

        post_data = { 'username': self.options.username,
                      'password': self.options.password }
        post_data = json.dumps(post_data)

        self.conn.setopt(pycurl.URL, '%s/api/v1.2/authtokens' % self.options.url)
        self.conn.setopt(pycurl.POSTFIELDS, post_data)
        self.conn.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json'])

        while True:
            self.reset_buff()
            try:
                response = self.handle_connection()
            except FeedAPIError as err:
                LOGGER.error(err)
                time.sleep(self.sleep_timeout)
            else:
                authtoken = response['item']['token'].encode('utf-8')
                self.__class__.authtoken = authtoken
                return authtoken