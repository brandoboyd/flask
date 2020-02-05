#!/usr/bin/env python2.7
#
# https://dev.twitter.com/docs/streaming-apis/connecting
#

'''
A twitter bot that tracks direct messages for channels that have a
valid twitter oAuth configured.
'''
import time
import socket

import pycurl
import oauth2
import tweepy

from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel

from solariat_bottle.utils.oauth     import get_twitter_oauth_credentials
from solariat_bottle.daemons.helpers import (
    StoppableThread
)

from solariat_bottle.settings     import LOGGER
from solariat_bottle.utils.config import sync_with_keyserver
sync_with_keyserver()


try:
    assert False  # set to True to get debugger connected to thread worker

    import threading
    import pydevd

    pydevd.connected = True
    pydevd.settrace(suspend=False)
    threading.settrace(pydevd.GetGlobalDebugger().trace_dispatch)
except (ImportError, AssertionError):
    pass


class Namespace:
    pass


class TimeoutBasket:
    " hold curl easy handles for timeout period "
    def __init__(self, timeout):
        self.timeout = timeout
        self.basket = {}

    def add(self, conn):
        " add curl easy handle to basket "
        if conn not in self.basket:
            self.basket[conn] = time.time()

    def get(self):
        " query curl easy handle from basket "
        if not len(self.basket):
            return None
        conn = min(self.basket, key=lambda x: self.basket[x])
        if (time.time() - self.basket[conn]) >= self.timeout:
            del self.basket[conn]
            return conn
        return None


class UserStream():
    # For now just use userstreams, as site streams are not yet stable
    # (https://dev.twitter.com/docs/streaming-apis/streams/site)
    TWITTER_STREAM_API_HOST = 'userstream.twitter.com'
    TWITTER_STREAM_API_PATH = '/2/user.json'

    def __init__(self, options, mstream):

        self.url = "https://%s%s" % (self.TWITTER_STREAM_API_HOST,
                                     self.TWITTER_STREAM_API_PATH)

        self.channel         = options.channel
        self.CONSUMER_KEY    = options.CONSUMER_KEY
        self.CONSUMER_SECRET = options.CONSUMER_SECRET
        self.ACCESS_KEY      = options.ACCESS_KEY
        self.ACCESS_SECRET   = options.ACCESS_SECRET

        self.conn = pycurl.Curl()
        self.conn.ustream = self
        self.conn.setopt(pycurl.URL,                self.url)
        self.conn.setopt(pycurl.HEADER,             False)
        self.conn.setopt(pycurl.SSL_VERIFYPEER,     True)
        self.conn.setopt(pycurl.VERBOSE,            0)
        self.conn.setopt(pycurl.WRITEFUNCTION,      self.on_receive)
        self.conn.setopt(pycurl.OPENSOCKETFUNCTION, self.__opensocket)

        self.buff = ""
        self.post_fields = {'channel': self.channel, 'content': False}
        self.me = self.__get_me()
        self.keepalive_timeout   = 120
        self.keepalive_lastcheck = int(time.time())
        self.mstream = mstream
        self.__stopped = False

    def __opensocket(self, family, socktype, protocol, *args, **kwargs):
        " set a timer, 90 second TCP level socket timeout "
        LOGGER.debug('__opensocket(%s, %s, %s)' % (family, socktype, protocol))
        LOGGER.debug('__opensocket args=%s kwargs=%s' % (args, kwargs))

        sock = socket.socket(family, socktype, protocol)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 90)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 10)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 2)
        return sock

    def __get_me(self):
        """
        Get the twitter handle (screen name) for this configured user stream.
        """
        auth = tweepy.OAuthHandler(self.CONSUMER_KEY, self.CONSUMER_SECRET)
        auth.set_access_token(self.ACCESS_KEY, secret=self.ACCESS_SECRET)
        api = tweepy.API(auth)
        return api.me().screen_name

    def __oauth(self):
        """ Get oauth authorization token. """
        CONSUMER = oauth2.Consumer(self.CONSUMER_KEY,
                                   self.CONSUMER_SECRET)
        access_token = oauth2.Token(key=self.ACCESS_KEY,
                                    secret=self.ACCESS_SECRET)

        params = {
            'oauth_version': "1.0",
            'oauth_nonce': oauth2.generate_nonce(),
            'oauth_timestamp': int(time.time()),
            'oauth_token': access_token.key,
            'oauth_consumer_key': CONSUMER.key
        }

        req = oauth2.Request(method="GET",
                             url=self.url,
                             parameters=params,
                             is_form_encoded=True)

        req.sign_request(oauth2.SignatureMethod_HMAC_SHA1(),
                         CONSUMER,
                         access_token)

        return req.to_header()['Authorization'].encode('utf-8')

    def gen_auth_header(self):
        self.conn.setopt(pycurl.HTTPHEADER,
                         ['Authorization: ' + self.__oauth()])

    def on_receive(self, data):
        """
        Called whenever a new direct message is recieved. Keep buffering data
        until valid message is recieved fully. After that extract whatever is
        required from the full json and push to the `incoming_posts_queue` for
        further concurent processing.
        """
        if self.__stopped:
            self.mstream.stop()
            return -1
        if data:
            self.keep_alive()

        if data.strip():
            if len(data) <= 60:
                log_val = data
            else:
                log_val = '%s...%s' % (data[:40], data[-17:])
            LOGGER.debug('received %r (%u bytes)', log_val, len(data))
            # do not append empty data (\r\n) in buffer
            self.buff += data

        if data.endswith("\r\n") and self.buff.strip():
            self.mstream.received_message(self.buff, self)    # Pass it on to bot for processing
            self.buff = ""

    def keep_alive(self):
        self.keepalive_lastcheck = int(time.time())

    def check_alive(self):
        connection_timeout = int(time.time()) - self.keepalive_lastcheck
        if connection_timeout > self.keepalive_timeout:
            LOGGER.error('[@%s] TCP connection timeout', self.me)
            self.keepalive_lastcheck = int(time.time())
            return False
        return True

    # def clone(self):
    #     self.stop()
    #     return UserStreamOld(self.options, self.mstream)

    def stop(self):
        try:
            self.conn.close()
        finally:
            self.__stopped = True


class UserStreamMulti(StoppableThread):
    " allows to handle multiple instances of UserStream objects "

    def __init__(self, post_queue, bot_instance):
        super(UserStreamMulti, self).__init__()
        self.m          = pycurl.CurlMulti()
        self.tb         = TimeoutBasket(60)
        self.handles    = []
        self.last_sync  = None
        self.post_queue = post_queue
        self.bot_instance    = bot_instance

    def add_stream(self, ustream):
        if ustream not in self.handles:
            self.handles.append(ustream)
            ustream.gen_auth_header()
            self.m.add_handle(ustream.conn)

    def del_stream(self, ustream):
        if ustream in self.handles:
            if self.tb.basket.has_key(ustream.conn):
                del self.tb.basket[ustream.conn]
            else:
                self.m.remove_handle(ustream.conn)
            self.handles.remove(ustream)

    def _get_stream_opts(self, channel):
        options = Namespace()
        options.channel = str(channel.id)
        (consumer_key, consumer_secret, _,
            access_token_key, access_token_secret) = get_twitter_oauth_credentials(channel)
        # Extract options here and pass to channel since we need this
        # when we compare for new channels.
        options.CONSUMER_KEY = consumer_key
        options.CONSUMER_SECRET = consumer_secret
        options.ACCESS_KEY = access_token_key
        options.ACCESS_SECRET = access_token_secret
        options.title = channel.title
        return options

    @staticmethod
    def _cmp_keys(a, b):
        # We will assume two channels are the same if they have the same consumer keys and the
        # same oauth tokens (eg. a user might have logged out then log in again)
        if a.CONSUMER_KEY == b.CONSUMER_KEY and \
           a.CONSUMER_SECRET == b.CONSUMER_SECRET and \
           a.ACCESS_KEY == b.ACCESS_KEY and \
           a.ACCESS_SECRET == b.ACCESS_SECRET:
            return True
        return False

    def _add_channel_stream(self, channel_id, old_channels, new_channels, update=False):
        """
        Either add or update a channels stream given by channel_id;
        NOTE: uses _channels and new_channels from this namespace.
        """
        try:
            ustream = UserStream(new_channels[channel_id], self)
            self.add_stream(ustream)
            if update:
                self.del_stream(old_channels[channel_id])
                LOGGER.info("'%s' channel keys updated", new_channels[channel_id].title)
            else:
                LOGGER.info("'%s' channel added", new_channels[channel_id].title)
        except tweepy.error.TweepError as e:
            LOGGER.error("'%s' channel failed: %s", new_channels[channel_id].title, str(e))

    def received_message(self, post_message, stream=None):
        self.bot_instance.post_received(post_message, stream)

    def sync_streams(self):
        """
        In case new channels are added, or old ones are suspended / logged out
        we need to also reflect those changes in the UserStreams we are tracking.
        """
        LOGGER.debug('synchronizing streams')

        _channels = {}
        for ustream in self.handles:
            _channels[ustream.channel] = ustream

        new_channels = {}
        # Get a list of all the EnterpriseTwitterChannel channels that are currently active
        for channel in EnterpriseTwitterChannel.objects(status='Active'):
            try:
                if ( channel.access_token_key and
                     channel.access_token_secret ):
                    options = self._get_stream_opts(channel)
                    new_channels[options.channel] = options
            except Exception, ex:
                LOGGER.error("'%s' channel failed: %s", channel, ex)

        for channel_id in new_channels.keys():
            # Go through the list of channels currently active
            if channel_id in _channels:
                if not self._cmp_keys(_channels[channel_id], new_channels[channel_id]):
                    # This means that for some reason the auth tokens have changed.
                    # Just delete the old stream and add a new one
                    self._add_channel_stream(channel_id, _channels, new_channels, True)
                del _channels[channel_id]   # This is updated, just remove from old channels
            else:
                self._add_channel_stream(channel_id, _channels, new_channels)

        # All that remains now in _channels should be unneeded channels
        for channel_id in _channels:
            self.del_stream(_channels[channel_id])
            LOGGER.info("'%s' channel removed", channel_id)

    def heartbeat(self):
        pass

    def run(self):
        while not self.stopped():
            try:
                if not self.last_sync or (time.time() - self.last_sync) > 60:
                    self.sync_streams()
                    self.last_sync = time.time()

                for ustream in self.handles:
                    ustream.check_alive()

                # not_alive_streams = []
                # for ustream in self.handles:
                #     if not ustream.check_alive():
                #         not_alive_streams.append(ustream)
                #
                # for ustream in not_alive_streams:
                #     self.add_stream(ustream.clone())

                # Run the internal curl state machine for the multi stack
                num_handles = 0
                while not self.stopped():
                    ret, num_handles = self.m.perform()
                    if ret != pycurl.E_CALL_MULTI_PERFORM:
                        break
                # Check for curl objects which have terminated, and re-start them
                while not self.stopped():
                    num_q, ok_list, err_list = self.m.info_read()
                    for ch in ok_list:
                        self.m.remove_handle(ch)
                        RESPONSE_CODE = ch.getinfo(ch.RESPONSE_CODE)
                        LOGGER.error('[@%s] HTTP Status: %d', ch.ustream.me, RESPONSE_CODE)

                        if RESPONSE_CODE == 401:
                            self.tb.add(ch)
                        else:
                            ch.ustream.gen_auth_header()
                            self.m.add_handle(ch)

                    for ch, errno, errmsg in err_list:
                        self.m.remove_handle(ch)
                        LOGGER.error('[@%s] errno: %s %s', ch.ustream.me, errno, errmsg)
                        ch.ustream.gen_auth_header()
                        self.m.add_handle(ch)
                    if num_q == 0:
                        break

                # query for easy handles from TimeoutBasket
                while not self.stopped():
                    ch = self.tb.get()
                    if ch:
                        ch.ustream.gen_auth_header()
                        self.m.add_handle(ch)
                    else:
                        break

                if num_handles > 0:
                    self.m.select(1.0)
                else:
                    time.sleep(1.0)

            except Exception, err:
                LOGGER.error(err, exc_info=True)
                # pause for a bit on any unexpected errors
                time.sleep(5.0)

    def stop(self):
        for stream in self.handles:
            stream.stop()
            del stream
        super(UserStreamMulti, self).stop()


if __name__ == '__main__':
    # this is just an alias for twitter_stream_bot
    from twitter_stream_bot import parse_options, main

    options = parse_options()
    main(options)
