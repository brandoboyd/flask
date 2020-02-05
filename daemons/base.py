from abc import ABCMeta, abstractmethod
import os
import sys

from Queue import Queue

from solariat_bottle.settings        import get_var, LOGGER
from solariat_bottle.daemons.helpers import (
    ProcessLock, SanityChecker, PostCreator, StoppableThread
)
from solariat_bottle.db.user         import User


MSG_QUIT = 'QUIT'
MSG_IS_BUSY = 'BUSY'
MSG_STATUS = 'STATUS'
MSG_SKIP = 'SKIP'


def post_creator_process(pipe, idx, PostCreator, concurrency, user, **options):
    """Worker process"""
    queue = Queue()

    class Checker(object):
        def inc_skipped(self):
            pipe.put((MSG_SKIP, idx))

    checker = Checker()
    # spawn workers
    workers = ThreadGroup([PostCreator(
        user, queue, checker, **options)
        for _ in range(concurrency)])
    workers.start()

    while True:
        # read pipe and put received data to post creators queue
        data = pipe.get()
        if data == MSG_STATUS:
            pipe.put((MSG_STATUS, (idx, workers.get_status())))
        elif data == MSG_IS_BUSY:
            pipe.put((MSG_IS_BUSY, (idx, workers.is_busy())))
        else:
            # probably post json data
            queue.put(data)


class ProcessGroup(object):

    def __init__(self, num_workers=4, post_queue=None, checker=None, args=(), kwargs={}):
        import gevent
        self.num_workers = num_workers
        self.checker = checker
        self.args = args
        self.kwargs = kwargs

        self.queue = post_queue
        self.pool = gevent.pool.Group()  # group of spawned helper greenlets

        self.workers = []   # child post creator processes
        self.parent_pipes = []  # list of (pipe, index) for communication with child processes

        self._child_message = None  # child processes will send status messages
        self._child_message_received = gevent.event.Event()
        self._child_message_lock = gevent.lock.RLock()

    def __len__(self):
        return self.num_workers

    def start(self):
        import gipc

        workers = self.workers
        parent_pipes = self.parent_pipes

        for idx in range(self.num_workers):
            child, parent = gipc.pipe(duplex=True)
            with child:
                worker = gipc.start_process(target=post_creator_process,
                                            args=(child, idx) + self.args,
                                            kwargs=self.kwargs)
            workers.append(worker)
            parent_pipes.append((parent, idx))
            self.pool.spawn(self.child_listener, idx, parent)

        self.pool.spawn(self.dispatch)

    def join(self):
        workers = self.workers
        parent_pipes = self.parent_pipes

        for p in workers:
            p.join(timeout=1)

        self.pool.kill(block=True)
        for p in workers:
            p.terminate()

        for pipe, idx in parent_pipes:
            pipe.close()

    def child_listener(self, idx, pipe):
        import gevent

        while True:
            TIME_SECONDS = 1
            with gevent.Timeout(TIME_SECONDS, False) as t:
                data = pipe.get(timeout=t)
                if isinstance(data, (tuple, list)) and len(data) == 2:
                    message, context = data
                    if message == MSG_SKIP:
                        self.inc_skipped(context)
                    elif message == MSG_IS_BUSY or message == MSG_STATUS:
                        self._child_message = data
                        self._child_message_received.set()

    def inc_skipped(self, idx):
        if self.checker:
            self.checker.inc_skipped()

    def dispatch(self):
        """Pops message from queue and sends to
        one of child processes through pipe"""
        import gevent

        pipes = self.parent_pipes
        pipes_map = {idx: pipe for (pipe, idx) in pipes}

        def read_queue():
            while True:
                data = self.queue.get()
                if data is None:
                    gevent.sleep(0.1)
                    continue
                return data

        while True:
            # round robin pipes
            for idx, pipe in pipes_map.iteritems():
                data = read_queue()
                pipe.put(data)

            gevent.sleep(0)

    def receive(self, event_json):
        self.queue.put(event_json)

    def stop(self):
        for pipe, idx in self.parent_pipes:
            pipe.put(MSG_QUIT)  # ! do not send PostCreator.QUIT object
        self.join()

    def send_and_receive(self, pipe, message):
        event = self._child_message_received
        NO_MESSAGE = object()

        with self._child_message_lock:
            event.clear()
            self._child_message = NO_MESSAGE
            pipe.put(message)
            event.wait(timeout=1)
            if self._child_message is NO_MESSAGE:
                print("No answer from child %s" % pipe)
            return self._child_message

    def all_busy(self):
        busy_list = []
        for pipe, idx in self.parent_pipes:
            msg, (idx, is_busy) = self.send_and_receive(pipe, MSG_IS_BUSY)
            busy_list.append(is_busy)
        return all(busy_list)

    def is_busy(self):
        for pipe, idx in self.parent_pipes:
            msg, (idx, is_busy) = self.send_and_receive(pipe, MSG_IS_BUSY)
            if is_busy:
                return True
        return False

    def is_alive(self):
        return [worker.is_alive() for worker in self.workers]

    def get_status(self):
        all_statuses = []
        for pipe, idx in self.parent_pipes:
            msg, (idx, status) = self.send_and_receive(pipe, MSG_STATUS)
            all_statuses.append({"process_idx": idx, "workers": status})
        return all_statuses


class ThreadGroup(list):
    def __init__(self, iterable=(), queue=None):
        super(ThreadGroup, self).__init__(iterable)
        self.queue = queue

    def receive(self, event_json):
        """With disabled multiprocessing just put received post to creators
        queue for further processing"""
        if event_json == MSG_QUIT:
            self.stop()
        else:
            self.queue.put(event_json)

    def start(self):
        for thread in self:
            thread.start()

    def stop(self):
        for thread in self:
            thread.stop()
            if self.queue:
                self.queue.put(PostCreator.QUIT)

    def all_busy(self):
        return all(thread.is_busy() for thread in self)

    def is_busy(self):
        for thread in self:
            if thread.is_busy():
                return True
        return False

    def is_alive(self):
        return [thread.is_alive() for thread in self]

    def get_status(self):
        return [x.get_status() for x in self]


class BaseExternalBot(StoppableThread):
    """ The base class for external bots. They should expose at a minimum a post_received method
    that we can use to independently. Also setup basic structure of all bost with PostCreator objects
    that handle actual flow of posts into our own app using ZMQ tasks.

    :param username: The superuser email we're going to user on GSA side to create inbound posts
    :param lockfile: A unique lockfile user to make sure we are not running two instances at once
    :param concurrency: The number of parallel PostCreators we want to process inbound posts
    """

    def __init__(self, username, lockfile, concurrency=4, multiprocess_concurrency=0, max_queue_size=50000, *args, **kwargs):
        PostCreatorThread = kwargs.pop('post_creator', PostCreator) or PostCreator
        post_creator_opts = {arg: kwargs.pop(arg, None)
                             for arg in ('url', 'password', 'user_agent', 'post_creator_senders') if arg in kwargs}

        super(BaseExternalBot, self).__init__(*args, **kwargs)

        if get_var('ON_TEST'):
            lockfile = lockfile + '.test'

        self.process = ProcessLock(lockfile)

        if not self.process.lock():
            LOGGER.error("daemon already running, exiting...")
            if get_var('ON_TEST'):
                os.unlink(lockfile)
                self.process.lock()
            else:
                sys.exit(1)
        LOGGER.info("daemon started with pid %d", os.getpid())

        user = User.objects.get(email=username)

        self.post_queue = Queue(maxsize=max_queue_size)

        if not get_var('ON_TEST'):
            self.checker = SanityChecker(queue=self.post_queue)
        else:
            self.checker = SanityChecker(queue=self.post_queue, check_interval=1)
        self.checker.start()

        if not multiprocess_concurrency:
            self.creators = ThreadGroup([PostCreatorThread(
                user, self.post_queue, self.checker, **post_creator_opts)
                for _ in xrange(concurrency)],
                                        self.post_queue)

        else:
            assert isinstance(multiprocess_concurrency, int) and 32 >= multiprocess_concurrency >= 1
            self.creators = ProcessGroup(num_workers=multiprocess_concurrency,
                                         post_queue=self.post_queue,
                                         checker=self.checker,
                                         args=(PostCreatorThread, concurrency, user),
                                         kwargs=post_creator_opts)
        self.creators.start()
        self._running = False   # Bot is not actually running until connected to external source

    def run(self):
        raise NotImplementedError("Specific run functions should be implemented by speficic bots.")

    def stop(self):
        """ Attempt to gracefully stop the bot and all other threads running for it """
        # we run __del__ method on self.process explicitly
        # since we really want it to be executed here
        # del self.process may be postponed
        # see e.g. http://eli.thegreenplace.net/2009/06/12/safely-using-destructors-in-python/
        self.process.__del__()
        super(BaseExternalBot, self).stop()
        self.checker.stop()
        self.creators.stop()

    def q_size(self):
        """ Return the queue size which is currently waiting to be processed by the bot. """
        return self.post_queue.qsize()

    def is_running(self):
        return self._running

    def is_busy(self):
        """ Bot is busy if any of the post creator objects are busy """
        return self.creators.is_busy()

    def is_blocked(self):
        """ If the queue is not empty, but none of the post creators are working, bot is blocked """
        if self.q_size() > 0 and not self.is_busy():
            return True
        return False

    def post_received(self, post_field):
        """ Should be implemented by specific bots """
        raise NotImplementedError("Each bot should implement it's own post_received function.")

    def isAlive(self):
        bot_alive = super(BaseExternalBot, self).isAlive()
        checked_alive = self.checker.isAlive()
        creators_alive = self.creators.is_alive()
        return bot_alive or checked_alive or any(creators_alive)


class BaseHistoricSubscriber(object):

    __metaclass__ = ABCMeta

    @abstractmethod
    def start_historic_load(self):
        '''Start loading historic data for this kind of subscription'''

    @abstractmethod
    def get_status(self):
        '''return current status of the subscriber'''

    def is_alive(self):
        from solariat_bottle.db.historic_data import SUBSCRIPTION_FINISHED, SUBSCRIPTION_ERROR, SUBSCRIPTION_STOPPED

        return self.get_status() not in {SUBSCRIPTION_FINISHED, SUBSCRIPTION_ERROR, SUBSCRIPTION_STOPPED}
