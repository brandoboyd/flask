"Test EvenLogs"

import json
import time
import unittest

from .base import UICaseSimple

from ..db.channel.twitter import EnterpriseTwitterChannel as ETC, TwitterServiceChannel
from ..db.event_log       import EventLog, log_event
from ..db.post.base       import Post
from ..db.user_profiles.user_profile    import UserProfile

from ..utils.logger     import setup_logger, TangoHandler
from ..utils.decorators import timed_event

from solariat_bottle          import settings
from solariat_bottle.settings import get_var, LOGGER


class LoggingCase(UICaseSimple):

    def setUp(self):
        super(LoggingCase, self).setUp()

        self.orig_logger_level    = LOGGER.level
        self.orig_logger_handlers = LOGGER.handlers[:]
        self.orig_ev_log_enabled  = get_var('EVENT_LOG_ENABLED')

        # make sure the logger has the tango handler
        handler = TangoHandler.instance()
        handler._account = None
        handler._channel = None
        handler._user = None
        setup_logger(LOGGER, level='DEBUG', extra_handlers=[handler])

        # make sure EventLog is enabled
        settings.EVENT_LOG_ENABLED = True

    def tearDown(self):
        # restore original logger level & handlers
        LOGGER.setLevel(self.orig_logger_level)
        LOGGER.handlers  = self.orig_logger_handlers
        # restore original EVENT_LOG_ENABLED config parameter
        settings.EVENT_LOG_ENABLED = self.orig_ev_log_enabled

        super(LoggingCase, self).tearDown()


class TangoStreaming(LoggingCase):

    @unittest.skip("Deprecated ??")
    def test_post_count(self):
        '''
        When we enable logging, we get the posts
        '''
        before = Post.objects.count()

        def log(post):
            LOGGER.debug(post)
            time.sleep(0.001)  # delay because posts sent within one millisecond clash

        log("P1")
        log("P2")
        log("P3")
        log("P4")
        log("P5")
        log("P6")

        self.assertEqual(Post.objects.count() - before, 6)

    @timed_event
    def time_this(self):
        Post.objects.count()

    @unittest.skip("Deprecated ??")
    def test_timed_event(self):
        before = Post.objects.count()
        self.time_this()
        self.assertEqual(Post.objects.count() - before, 1)


class EventLogCase(LoggingCase):

    def test_creation(self):
        elog = EventLog.objects.create(
            type_id=0, name='Test')
        self.assertTrue(elog.id)
    @unittest.skip("Deprecated ??")
    def test_log_event(self):
        ''' Make sure expected post structure is there'''

        log_event("LoginEvent",
                  user=self.user.email,
                  account="SOLARIAT",
                  note="This is a login")

        last_post = Post.objects()[:][-1]
        self.assertEqual(set(last_post.speech_acts[0]['intention_topics']),
                         set([ u'userloggedin solariat nobody@solariat.com',
                               u'solariat userloggedin', u'nobody@solariat.com userloggedin',
                               u'solariat nobody@solariat.com userloggedin']))

    def test_login(self):
        self.login()
        elog = EventLog.objects.find_one(name='UserLoggedIn')
        self.assertTrue(elog)
        self.assertEqual(elog.user, self.user.email)

    def test_wrong_username(self):
        self.login('foo', 'bar')
        elog = EventLog.objects.find_one(name='LoginFailed')
        self.assertTrue(elog)
        self.assertEqual(elog.note, "User doesn't exist")
        self.assertEqual(elog.user, 'foo')

    def test_wrong_password(self):
        self.login(self.user.email, 'bar')
        elog = EventLog.objects.find_one(name='LoginFailed')
        self.assertTrue(elog)
        self.assertEqual(elog.note, "Password doesn't match")
        self.assertEqual(elog.user, self.user.email)


class DispatchEventsCase(LoggingCase):

    def setUp(self):
        LoggingCase.setUp(self)
        self.login()
        self.channel = ETC.objects.create_by_user(
            self.user, title='Test Twitter Channel',
            access_token_key='dummy_key',
            access_token_secret='dummy_secret')
        self.user_profile = UserProfile.objects.upsert("Twitter", dict(screen_name="Jack"))
        self.sc = TwitterServiceChannel.objects.create_by_user(
            self.user,
            title='Service Channel')

        matchable = self._create_db_matchable(
            'there is some foo', 
            channels=[self.sc.inbound_channel])

        post = self._create_db_post('I need some foo',
                                    demand_matchables=True,
                                    user_profile=self.user_profile,
                                    channel=self.sc.inbound_channel)

    @unittest.skip("Deprecated ??")
    def test_post_log(self):
        resp = self.client.post('/commands/post_response',
                                data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(self.response.id), str(self.response.matchable.id), str(self.response.post.id)))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.response.reload()
        self.assertEqual(self.response.status, 'posted')
        elog = EventLog.objects.find_one(name='MessageDispatched')
        self.assertTrue(elog)
        self.assertEqual(elog.user, self.user.email)

