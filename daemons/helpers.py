#!/usr/bin/env python2.7
import threading
import json
from os        import unlink, close
from os.path   import basename, join
from collections import deque
import time
from fcntl     import flock, LOCK_EX, LOCK_NB
from errno     import EAGAIN
from tempfile  import gettempdir, mkstemp
from Queue import Queue
from solariat.utils.lang.detect import Language
from solariat_bottle.db.post.twitter import TweetSource

from solariat_bottle.settings      import LOGGER
from solariat_bottle.utils.tracking import lookup_tracked_channels
from solariat_bottle.utils.posts_tracking import log_state, PostState, get_post_natural_id
# from solariat_bottle.tasks import get_tracked_channels
from solariat_bottle.db            import get_connection
from solariat_bottle.daemons.twitter.parsers import (
    TweetParser, DMTweetParser, parse_user_profile)

from solariat_pool.db_utils import retry, CONNECTION_ERRORS
from solariat_bottle.daemons.feedapi import FeedApiThread
from solariat_bottle.settings import LOGGER, get_var
from solariat_bottle.registered_schemas import register_schemas
from solariat_bottle.daemons.feedapi import RequestsClient


# Make sure all fields are set on post objects
register_schemas()


def lookup_tracked_channels_switchable(*args, **kwargs):
    time.sleep(0)
    return lookup_tracked_channels(*args, **kwargs)


DIRECT_MESSAGE = 0
PUBLIC_TWEET = 1


class DedupQueue(object):
    def __init__(self, maxlen=None):
        self.seen_items = deque(maxlen=maxlen)

    def append(self, item):
        for last_added in reversed(self.seen_items):
            if item == last_added:
                return False
        self.seen_items.append(item)
        return True


class Stoppable(object):
    def __init__(self, *args, **kwargs):
        self._stop = threading.Event()
        super(Stoppable, self).__init__(*args, **kwargs)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def wait(self, seconds):
        seconds_delay = 0.5
        while seconds > 0:
            seconds -= seconds_delay
            time.sleep(seconds_delay)
            if self.stopped():
                break


class StoppableThread(Stoppable, threading.Thread):
    pass


class SanityChecker(StoppableThread):
    """ This thread periodically checks:
        - size of a passed queue to be lower than a defined threshold
        - skipped counter to be higher than a difined threshold
        - received counter to be higher than a defined threshold
    """
    CHECK_INTERVAL       = 30    # check every 30 seconds
    QUEUE_SIZE_THRESHOLD = 50    # allow 50 queued items at max
    SKIPPED_INTERVAL     = 5*60  # check & reset skipped every 5 minutes
    SKIPPED_THRESHOLD    = 8     # allow 8 skipped items per SKIPPED_INTERVAL
    RECEIVED_INTERVAL    = 1*60  # check & reset received every minute
    RECEIVED_THRESHOLD   = 1     # require at least 1 received item per RECEIVED_INTERVAL

    _num = 0

    def __init__(self, queue, check_interval=None):
        """
        """
        num = self._num
        self._num = num + 1
        name = self.__class__.__name__ + ('-%s' % num if num else '')
        super(SanityChecker, self).__init__(name=name)
        self.daemon   = True
        self.queue    = queue
        self.skipped  = 0
        self.received = 0
        self.skipped_rate_per_second = 0
        self.received_rate_per_second = 0
        self.check_interval = check_interval or SanityChecker.CHECK_INTERVAL
        self.last_skipped_check  = time.time()
        self.last_received_check = time.time()
        self.__not_receiving = False
        self.__client        = None

    def run(self):
        while not self.stopped():
            self._check_queue_size()
            self._check_skipped()
            self._check_received()
            time.sleep(self.check_interval)

    def _check_queue_size(self):
        " check queue size "
        queue_size = self.queue.qsize()
        if queue_size > self.QUEUE_SIZE_THRESHOLD:
            LOGGER.warning('queue is too large: %d > %d', queue_size, self.QUEUE_SIZE_THRESHOLD)

    def _check_skipped(self):
        " check skipped counter "

        cur_time = time.time()
        interval = cur_time - self.last_skipped_check
        self.skipped_rate_per_second = self.skipped / (interval or 1.0)

        if interval >= self.SKIPPED_INTERVAL:
            if self.skipped > self.SKIPPED_THRESHOLD:
                LOGGER.warning('too many skipped: %d > %d', self.skipped, self.SKIPPED_THRESHOLD)
            self.skipped            = 0         # reset skipped counter
            self.last_skipped_check = cur_time  # start new skipped period

    def _check_received(self):
        " check received counter "

        cur_time = time.time()
        interval = cur_time - self.last_received_check
        self.received_rate_per_second = self.received / (interval or 1.0)

        if interval >= self.RECEIVED_INTERVAL:
            if self.received < self.RECEIVED_THRESHOLD:
                LOGGER.warning(
                    'not receiving often enough: %d < %d (per %d sec)',
                    self.received,
                    self.RECEIVED_THRESHOLD,
                    self.RECEIVED_INTERVAL
                )
                self.not_receiving = True
                if self.__client is not None:
                    try:
                        self.__client.close()
                    except Exception, err:
                        LOGGER.warning(err)
            else:
                self.not_receiving = False
            self.received            = 0         # reset received counter
            self.last_received_check = cur_time  # start new received period

    def _get_not_receiving(self):
        value = self.__not_receiving
        self.__not_receiving = False  # immediate reset on read
        return value

    def _set_not_receiving(self, value):
        self.__not_receiving = value

    # -- public api --

    def set_client(self, client):
        self.__client = client

    def inc_skipped(self):
        self.skipped += 1

    def inc_received(self):
        self.received += 1

    not_receiving = property(_get_not_receiving, _set_not_receiving)

    def get_status(self):
        cur_time = time.time()
        return {
            "skipped": self.skipped,
            "received": self.received,
            "skipped_rate_per_second": self.skipped_rate_per_second,
            "received_rate_per_second": self.received_rate_per_second,
            "check_interval": self.check_interval,
            "current_time": cur_time,
            "last_skipped_check": self.last_skipped_check,
            "last_received_check": self.last_received_check,
            "skipped_interval": cur_time - self.last_skipped_check,
            "received_interval": cur_time - self.last_received_check,
        }


class PostProcessor(object):
    _preprocessors = {}

    @property
    def preprocessors(self):
        if not self.__class__._preprocessors:
            self.__class__._preprocessors = {
                DIRECT_MESSAGE: twitter_dm_to_post_dict,
                PUBLIC_TWEET: twitter_status_to_post_dict
            }
        return self.__class__._preprocessors

    def get_tracked_channels(self, *args, **kwargs):
        channels = lookup_tracked_channels_switchable(*args, **kwargs)
        return channels

    def preprocess_post(self, event_json):
        if isinstance(event_json, (tuple, list)):
            message_type, data = event_json
            post_data = None
            preprocess = self.preprocessors.get(message_type)
            if preprocess is None:
                LOGGER.warn(u"Unknown message type: %s\nEvent is: %s" % (message_type, event_json))
                return None

            try:
                post_data = preprocess(data)
            except:
                import traceback
                traceback.print_exc()
                LOGGER.warn(u"Error parsing tweet: %s" % unicode(event_json))

            if post_data:
                return post_data
            else:
                LOGGER.info(u"Twitter event: %s" % unicode(event_json))

        elif isinstance(event_json, dict):
            # already processed
            return event_json
        return None

    def assign_channels(self, post_fields):
        if not post_fields.get('channel', False) and not post_fields.get('channels', False):
            if 'twitter' in post_fields:
                LOGGER.debug('resolving tracked channels')
                channels = self.get_tracked_channels(
                    'Twitter',
                    post_fields
                )
                LOGGER.debug(channels)
                post_fields['channels'] = channels

        log_state(post_fields.get('channel', post_fields.get('channels', None)),
                  get_post_natural_id(post_fields),
                  PostState.REMOVED_FROM_WORKER_QUEUE)

        channels_assigned = post_fields.get('channel', False) or post_fields.get('channels', False)
        if channels_assigned:
            # clean up just to be on the safe side
            post_fields.pop('direct_message', None)
            post_fields.pop('sender_handle', None)
            post_fields.pop('recipient_handle', None)
            return channels_assigned
        return False

    @staticmethod
    def _prepare_post_data(**data):
        post_data = data.copy()
        if not isinstance(post_data['channels'][0], str):
            post_data['channels'] = [str(c.id) for c in post_data['channels']]
        if 'lang' in post_data and isinstance(post_data['lang'], Language):
            post_data['lang'] = post_data['lang'].lang

        try:
            return json.dumps(post_data)
        except Exception:
            from pprint import pformat
            LOGGER.exception(pformat(post_data))
            raise


class KafkaPostCreator(PostProcessor):
    def __init__(self, user, kwargs):
        self.user = user

    def create_post(self, **data):
        from solariat_bottle.db.post.utils import factory_by_user
        from solariat_bottle.db.user import User
        user = User.objects.get(email=self.user)
        return factory_by_user(user, **data)

    def run(self, task):
        # make sure we intercept all errors
        try:
            post_fields = self.preprocess_post(task)
            if not post_fields:
                LOGGER.warning('no post_fields in: %s', task)
                return

            if self.assign_channels(post_fields):
                self.create_post(**post_fields)
            else:
                LOGGER.info('skipping post %r' % post_fields.get('content'))

        except Exception, err:
            LOGGER.error(err, exc_info=True)
            pass
        else:
            LOGGER.info(u'done %s %s' % (self, str(task)))

    def __str__(self):
        return "%s[%s]" % (self.__class__.__name__, id(self))


class KafkaFeedApiPostCreator(KafkaPostCreator):
    _client = None

    @property
    def client(self):
        if self._client is None:
            _client = RequestsClient(self.options, self.sleep_timeout, self.user_agent)
            self._client = _client
        return self._client

    def __init__(self, user, kwargs):
        super(KafkaFeedApiPostCreator, self).__init__(user, kwargs)

        class Options(dict):
            __getattr__ = dict.__getitem__

        self.options = Options(username=user,
                               password=kwargs['password'],
                               url=kwargs['url'],
                               retries=kwargs.get('retries', 3))
        if not self.options.password:
            err_msg = "Configuration Error: password and url are required"
            LOGGER.error("%s %s" % (err_msg, self.options))
            raise RuntimeError(err_msg)

        self.user_agent = kwargs.pop('user_agent', 'FeedApi-PostCreator')
        self.sleep_timeout = 30

    def create_post(self, **data):
        return self.send_post(self._prepare_post_data(**data))

    def send_post(self, post_data):
        return self.client.api_posts(post_data, number_of_retries=self.options.retries)


class PostCreator(PostProcessor, StoppableThread):
    """ This thread receives tasks in a form of post-fields dictionaries from an input queue,
        prepares them and creates posts using ZMQ task API (db.post.utils.factory_by_user).
    """
    _num = 1
    QUIT = object()

    def __init__(self, user, inp_queue, checker=None, **kwargs):
        """ user      - a <User> which will create posts in the db
            inp_queue - a shared <Queue> of posts to create
            checker   - a <SanityChecker> thread that is tied to this queue
        """
        num = self._num
        self._num = num + 1
        name = self.__class__.__name__ + ('-%s' % num if num else '')
        super(PostCreator, self).__init__(name=name)
        self.daemon    = True
        self._busy     = False
        self.user      = user
        self.inp_queue = inp_queue
        self.checker   = checker
        self._elapsed_times = deque([], 25)

    def create_post(self, **data):
        from solariat_bottle.db.post.utils import factory_by_user
        return factory_by_user(self.user, **data)

    def inc_skipped(self):
        if self.checker:
            self.checker.inc_skipped()

    def run(self):
        inp_queue = self.inp_queue
        start_time = time.time()

        while not self.stopped():
            # make sure we intercept all errors
            try:
                task = inp_queue.get()
                if task is self.QUIT or task == 'QUIT':
                    LOGGER.debug('received QUIT signal %s' % self)
                    break
                start_time = time.time()
                self._busy = True   # Just started doing our post processing
                post_fields = self.preprocess_post(task)
                if not post_fields:
                    LOGGER.warning('no post_fields in: %s', task)
                    continue

                # LOGGER.debug('creating post %r %s', post_fields.get('content'), inp_queue.qsize())

                if self.assign_channels(post_fields):
                    self.create_post(**post_fields)
                else:
                    LOGGER.info('skipping post %r' % post_fields.get('content'))
                    self.inc_skipped()

                self._busy = False  # Just Finished doing our post processing
            except Exception, err:
                LOGGER.error(err, exc_info=True)
                pass

            finally:
                inp_queue.task_done()
                self._busy = False
                self._elapsed_times.append(time.time() - start_time)
                time.sleep(0)

        LOGGER.info('quit %s' % self)

    def is_busy(self):
        return self._busy

    def quit(self):
        "Passes a QUIT command to the working thread using its cmd_queue"
        self.inp_queue.put(self.QUIT)

    @property
    def average_processing_time(self):
        size = len(self._elapsed_times)
        if size > 0:
            return sum(self._elapsed_times) / (size * 1.0)
        else:
            return -1

    def get_status(self):
        return {
            "alive": self.isAlive(),
            "busy": self.is_busy(),
            "avg_processing_time": self.average_processing_time
        }


class FeedApiPostCreator(PostCreator):
    def __init__(self, *args, **kwargs):
        super(FeedApiPostCreator, self).__init__(*args, **kwargs)

        class Options(dict):
            __getattr__ = dict.__getitem__

        self.options = Options(username=self.user.email,
                               password=kwargs.get('password'),
                               url=kwargs.get('url'))

        if not self.options.password:
            err_msg = "Configuration Error: password and url are required"
            LOGGER.error("%s %s" % (err_msg, self.options))
            raise RuntimeError(err_msg)

        self.user_agent = kwargs.pop('user_agent', 'FeedApi-PostCreator')
        self.max_workers = kwargs.pop('post_creator_senders', 4) or 4
        self.feed_queue = Queue()
        self.feed_api_threads = []

    def _add_feed_thread(self):
        qsize = self.feed_queue.qsize()
        total_threads = len(self.feed_api_threads)
        if (total_threads == 0 or qsize > 1) and total_threads < self.max_workers:
            thread = FeedApiThread(
                args=(self.feed_queue, self.options),
                kwargs={'User-Agent': '%s-%s' % (self.user_agent, self._num)}
            )
            thread.daemon = True
            thread.start()
            self.feed_api_threads.append(thread)
            LOGGER.info("Added FeedApiThread")

    def create_post(self, **data):
        self._busy = True
        self.feed_api_threads = [thread for thread in self.feed_api_threads
                                 if thread.isAlive() and not thread.stopped()]
        self.feed_queue.put(self._prepare_post_data(**data))
        self._add_feed_thread()

    def quit(self):
        self.feed_queue.put(FeedApiThread.QUIT)
        self.feed_queue.join()
        super(FeedApiPostCreator, self).quit()

    def is_busy(self):
        return (self._busy or self.feed_queue.qsize() > 0 or
                any(thread.is_busy() for thread in self.feed_api_threads))

    def get_status(self):
        status = super(FeedApiPostCreator, self).get_status()
        threads_stats = [
            {
                "busy": x.is_busy(),
                "alive": x.isAlive(),
                "average_send_time": x.average_processing_time
            } for x in self.feed_api_threads
        ]

        status.update(feed_sender={
            "qsize": self.feed_queue.qsize(),
            "threads_total": len(self.feed_api_threads),
            "threads_stats": threads_stats
        })
        self.feed_api_threads = [thread for thread in self.feed_api_threads
                                 if thread.isAlive() and not thread.stopped()]
        return status


class ProcessLock(object):

    def __init__(self, lockfile):
        self.is_locked = False
        self.lockfile = lockfile
        self.fp = open(lockfile, 'w')

    def lock(self):
        try:
            flock(self.fp, LOCK_EX|LOCK_NB)
        except IOError as e:
            if e.errno != EAGAIN:
                raise e
            return False

        self.is_locked = True
        return True

    def __del__(self):
        if self.is_locked:
            try:
                unlink(self.lockfile)
            except OSError:
                pass


def get_default_lockfile(suffix='.lock'):
    import __main__

    if hasattr(__main__, '__file__'):
        return join(
            gettempdir(),
            basename(__main__.__file__) + suffix
        )
    else:
        fd, filename = mkstemp(suffix=suffix)
        close(fd)
        return filename


def twitter_status_to_post_dict(data):
    base_url = 'https://twitter.com/%s/statuses/%s'

    if 'text' in data or 'full_text' in data:
        extended_tweet = data.get('extended_tweet') or {}
        is_retweet = 'retweeted_status' in data
        post_fields = {'twitter': {'_wrapped_data': json.dumps(data)}}
        post_fields['twitter'].update(
            _source=TweetSource.TWITTER_PUBLIC_STREAM,
            _is_retweet=is_retweet
        )

        if 'user' in data:
            author = data['user']
            content = data.get('full_text') or extended_tweet.get('full_text') or data.get('text')
        else:
            LOGGER.warn(u"Mis-formatted twitter data %s" % data)
            return

        def _get_tweet_lang(data):
            if 'lang' in data and data['lang']:
                return data['lang']
            elif 'lang' in author:
                return author['lang']

        post_fields['twitter'].update(_is_manual_retweet=not is_retweet and content.startswith('RT'))
        post_fields['lang'] = _get_tweet_lang(data)
        post_fields['user_profile'] = parse_user_profile(author)
        post_fields['content'] = content
        post_fields['url'] = base_url % (
            author['screen_name'],
            data['id_str'])

        #twitter data used to link a post to possible thread
        post_fields['twitter'].update(TweetParser()(data))
        return post_fields


def twitter_dm_to_post_dict(dm):
    """ Converts a Twitter direct message data structure (coming from the Twitter Stream API)
        to a post-fields dict (for passing to a <PostCreator> or db.post.utils.factory_by_user)
    """
    user_profile = parse_user_profile(dm['sender'])

    post_fields = dict(
        twitter      = {
            '_wrapped_data': json.dumps(dm),
            '_source': TweetSource.TWITTER_USER_STREAM,
        },
        user_profile = user_profile,
        content      = dm['text'] + ' @%s' % dm['recipient']['screen_name'],
        message_type = 1,

        # the following is for tasks.get_tracked_channels which is going
        # to be called by PostCreator because we do not provide channels here
        direct_message   = True,
        recipient_handle = dm['recipient']['screen_name'],
        sender_handle    = dm['sender']['screen_name'],
    )
    post_fields['twitter'].update(DMTweetParser()(dm))
    return post_fields


def datasift_to_post_dict(data):
    """ Converts a Datasift data structure (coming from the Datasift Stream API)
        to a post-fields dict (for passing to a <PostCreator> or db.post.utils.factory_by_user)
    """
    base_url = 'https://twitter.com/%s/statuses/%s'

    def _get_user_profile(author, klout):
        result = parse_user_profile(author)
        if klout:
            result['klout_score'] = klout['score']
        return result

    if 'text' in data['twitter'] or 'retweet' in data['twitter']:
        post_fields = {'twitter': {'_wrapped_data': json.dumps(data)}}
        is_retweet = 'retweet' in data['twitter']
        post_fields['twitter'].update(
            _source=TweetSource.DATASIFT_STREAM,
            _is_retweet=is_retweet
        )

        if is_retweet:
            author = data['twitter']['retweet']['user']
            content = data['twitter']['retweet']['text']
        elif 'user' in data['twitter']:
            author = data['twitter']['user']
            content = data['twitter']['text']
        else:
            LOGGER.error(u'format not supported: %s' % data)

        # datasift not always return 'language' object
        if 'language' in data:
            post_fields['lang'] = data['language']
        elif 'lang' in data['twitter']:
            post_fields['lang'] = data['twitter']['lang']
        elif 'lang' in author:
            post_fields['lang'] = author['lang']

        post_fields['user_profile'] = _get_user_profile(
            author, data.get('klout', None))
        post_fields['content'] = content
        post_fields['url'] = base_url % (
            author['screen_name'],
            str(data['twitter']['id']))

        #twitter data used to link a post to possible thread
        post_fields['twitter'].update(TweetParser()(data['twitter']))
        return post_fields


@retry(exc=CONNECTION_ERRORS, max_tries=34)
def get_datasift_hash():
    "Gets a datasift hash from database"
    try:
        db  = get_connection()
        res = db.PostFilterStream.find_one({'_id': 'datasift_stream1'})
        if res and 'dh' in res and res['dh']:
            return res['dh']
    except Exception as e:
        LOGGER.error(e, exc_info=True)

    return None


def systemd_notify():

    try:
        import systemd.daemon
        systemd.daemon.notify("READY=1")
    except ImportError:
        pass
