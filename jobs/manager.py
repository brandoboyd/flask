from functools import partial, wraps
from werkzeug.utils import cached_property
from blinker import signal

from solariat_bottle.jobs.config import jobs_config
from solariat_bottle.jobs.creator import Job
from solariat_bottle.settings import LOGGER


JOB_ACTIVITY_DEFAULT_TIMEOUT = 2 * 60


class JobsManager(object):

    def __init__(self, config=None):
        self._configure(config)
        self.job_state_signal = signal('job_state')
        # self.config.add_listener(self._configure)

    def _configure(self, config, drop_registry_cache=True):
        self.config = config

        self.__dict__.pop('transport', None)
        self.__dict__.pop('producer', None)
        if drop_registry_cache:
            self.__dict__.pop('registry', None)

    @cached_property
    def transport(self):
        try:
            transport = self.config.transport
        except AttributeError:
            transport = None
        from .transport.factory import get
        return get(self, transport)

    @cached_property
    def registry(self):
        from solariat_bottle.jobs.registry import JobsRegistry
        return JobsRegistry(self.config)

    @cached_property
    def producer(self):
        try:
            kw = dict(broker=self.config.kafka_broker)
        except AttributeError:
            kw = {}
        return self.create_producer(**kw)

    def create_producer(self, broker=None):
        transport = self.transport
        return transport.create_producer(broker=broker)

    def create_consumer(self, topics=None, group=None, broker=None):
        transport = self.transport
        return transport.create_consumer(topics=topics, group=group, broker=broker)

    def subscribe_state_update(self, func):
        self.job_state_signal.connect(func)

    def produce_state_update(self, state):
        assert isinstance(state, dict)
        self.job_state_signal.send('update', **state)

    def state_producer(self, func):
        def _func(*args, **kwargs):
            state = func(*args, **kwargs)
            if isinstance(state, dict):
                self.produce_state_update(state)
            else:
                LOGGER.warning('produced state must be a dict instance \
                got: %s\nargs:%s\nkwargs:%s', state, args, kwargs)
            return state
        return _func

    def job(self, topic=None, timeout=JOB_ACTIVITY_DEFAULT_TIMEOUT, func=None):
        if func is None:
            return partial(self.job, topic, timeout)

        job_instance = Job(func, topic, manager=self, timeout=timeout)
        job_instance = wraps(func)(job_instance)
        return job_instance


def terminate_handler(job):
    assert isinstance(job, Job)

    def _set_handler(func):
        job.terminate_handler = func
        return func
    return _set_handler


manager = JobsManager(jobs_config)
job = manager.job
state_producer = manager.state_producer
