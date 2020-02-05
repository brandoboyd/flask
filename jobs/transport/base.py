from abc import ABCMeta, abstractmethod
from collections import Iterator, namedtuple


class AbstractConsumer(Iterator):

    @abstractmethod
    def iterator(self):
        yield None

    def _get_iterator(self):
        try:
            self._stored_iterator
            assert self._stored_iterator is not None
        except (AttributeError, AssertionError):
            self._stored_iterator = self.iterator()
        return self._stored_iterator

    def next(self):
        return next(self._get_iterator())

    def commit(self):
        pass


class AbstractProducer(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def send(self, topic, name, args, kwargs, metadata=None):
        raise NotImplementedError()


class AbstractTransport(object):
    __metaclass__ = ABCMeta

    def __init__(self, manager):
        self.jobs_manager = manager

    @abstractmethod
    def create_consumer(self, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def create_producer(self, *args, **kwargs):
        raise NotImplementedError()


ProducerResult = namedtuple('ProducerResult', ['submission_result', 'job_instance'])