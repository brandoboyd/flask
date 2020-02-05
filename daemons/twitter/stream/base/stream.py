from solariat_bottle.utils.tweet import TwitterApiWrapper
from .listener import BaseListener
from solariat_bottle.daemons.twitter.stream.common import \
    on_test, TestStream, StreamGreenlet, StreamWrapper
from tweepy.streaming import Stream
import tweepy


class BaseStream(object):

    @staticmethod
    def ListenerCls():
        return BaseListener

    def __init__(self, stream_ref, auth_params, stream_manager, db=None, bot_user_agent=None):
        """
        :param username: twitter username
        :param auth: tuple of auth credentials representing twitter user
        :param mstream: multi stream container owning this stream
            `mstream` should implement listener protocol to handle user events
        """
        # self.me = self.username = stream_id
        self.stream_ref = stream_ref
        self.stream_id = stream_ref.id
        self.auth_params = auth_params

        self.auth = TwitterApiWrapper.auth_from_settings(*auth_params)
        self.api = TwitterApiWrapper.make_api(self.auth)

        self.listener = self.ListenerCls()(self, stream_manager, db=db)
        headers = {'X-User-Agent': bot_user_agent} if bot_user_agent else {}
        self.stream = Stream(self.auth, self.listener, headers=headers)
        self.listener.log_event('initialized')

        if on_test():
            self.test_stream = TestStream(self.listener)

    def start_stream(self):
        raise NotImplementedError("start_stream() undefined")

    def run(self):
        """Start polling stream"""
        # threading.current_thread().name = "UserStream(%s)" % self.username
        if on_test():
            self.test_stream.run()
            return 'test run exit'

        self.start_stream()

    def kill(self):
        self.listener.log_event('killing stream')
        self.listener.on_kill()
        self.stream.running = False
        if on_test() and hasattr(self, 'test_stream'):
            self.test_stream.stop()

    def is_alive(self):
        if on_test():
            return not self.test_stream.stopped()
        else:
            return self.stream.running

    def as_greenlet(self):
        if not hasattr(self, '_greenlet'):
            self._greenlet = StreamGreenlet(self)
        return self._greenlet