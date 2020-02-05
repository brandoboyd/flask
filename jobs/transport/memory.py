import logging
from Queue import Queue, Empty
from collections import defaultdict
from .base import AbstractTransport, AbstractConsumer, AbstractProducer, \
    ProducerResult
from .database import _DBProducer


class KeyedQueue(object):
    def __init__(self):
        self.q = defaultdict(Queue)

    def put(self, topic, message):
        self.q[topic].put(message)

    def viewkeys(self):
        return self.q.viewkeys()

    def __getitem__(self, item):
        return self.q[item]


class _InMemoryProducer(_DBProducer):
    def __init__(self, queue):
        self.queue = queue

    def send_message(self, topic, message):
        return self.queue.put(topic, message)

    def send(self, topic, name, args, kwargs, metadata=None):
        res = super(_InMemoryProducer, self).send(topic, name, args, kwargs, metadata)
        return ProducerResult(self.send_message(topic, res.job_instance), res.job_instance)


class _InMemoryConsumer(AbstractConsumer):
    def __init__(self, queue, topics=(), forever=False):
        self.queue = queue
        self.topics = topics
        self.forever = forever

    def iterator(self):

        def gen_batch(topics=(), timeout=0.5):
            messages = []
            if not topics:
                logging.warning('Consumer configured with no topics')
                topics = list(self.queue.viewkeys())

            for topic in topics:
                try:
                    messages.append(self.queue[topic].get(timeout=timeout))
                except Empty:
                    pass

            for message in messages:
                yield message

        while True:
            iterator = gen_batch(self.topics)
            try:
                message = next(iterator)
            except StopIteration:
                logging.getLogger('jobs.timeout').info('*')
            else:
                yield message
            if not self.forever:
                break

    def commit(self):
        topics = self.topics or list(self.queue.viewkeys())
        for topic in topics:
            self.queue[topic].task_done()


class InMemoryTransport(AbstractTransport):
    def __init__(self, *args, **kwargs):
        self.queue = KeyedQueue()
        super(InMemoryTransport, self).__init__(*args, **kwargs)

    def create_consumer(self, topics=None, *args, **kwargs):
        return _InMemoryConsumer(self.queue, topics)

    def create_producer(self, *args, **kwargs):
        return _InMemoryProducer(self.queue)
