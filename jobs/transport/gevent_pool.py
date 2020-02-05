from solariat_bottle.workers import io_pool
from solariat_pool.io import Task
from .base import AbstractTransport, AbstractConsumer, AbstractProducer, \
    ProducerResult


class _GeventPoolProducer(AbstractProducer):
    def __init__(self, manager):
        self.manager = manager

    def send(self, topic, name, args, kwargs, metadata=None):
        job = self.manager.registry.get(name)
        func = job.func
        task = Task(io_pool, func, name=name)
        result = task.ignore(*(args or ()), **(kwargs or {}))
        # result = io_pool.spawn(func, *(args or ()), **(kwargs or {}))
        io_pool.logger.debug("Spawned a task {}".format(result))
        return ProducerResult(True, result)


class GeventPoolTransport(AbstractTransport):

    def create_producer(self, *args, **kwargs):
        return _GeventPoolProducer(self.jobs_manager)

    def create_consumer(self, topics, *args, **kwargs):
        return None
