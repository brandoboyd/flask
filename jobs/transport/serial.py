from solariat_bottle.jobs.transport.database import _DBProducer
from solariat_bottle.jobs.transport.base import AbstractTransport, \
    ProducerResult
from solariat_bottle.jobs.executor import JobsSerialConsumer


class SerialProducer(_DBProducer):

    def __init__(self, manager):
        self.jobs_manager = manager

    def send_message(self, topic, job):
        JobsSerialConsumer(job, manager=self.jobs_manager).run()

    def send(self, topic, name, args, kwargs, metadata=None):
        res = super(SerialProducer, self).send(topic, name, args, kwargs, metadata)
        return ProducerResult(self.send_message(topic, res.job_instance), res.job_instance)


class SerialTransport(AbstractTransport):

    def create_producer(self, *args, **kwargs):
        return SerialProducer(self.jobs_manager)

    def create_consumer(self, *args, **kwargs):
        return None
