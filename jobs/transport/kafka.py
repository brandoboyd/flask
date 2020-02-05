from __future__ import absolute_import
import logging
from solariat_bottle.daemons.twitter.stream.base import kafka_serializer
from .database import _DBProducer
from kafka import KafkaConsumer, KafkaProducer
from kafka.common import ConsumerTimeout
from solariat_bottle.jobs.transport.base import AbstractConsumer, AbstractTransport, \
    ProducerResult
from solariat_bottle.jobs.creator import JobStatus


class _KafkaProducer(_DBProducer):
    def __init__(self, broker, serializer=kafka_serializer):
        self.serializer = serializer
        self.producer = KafkaProducer(bootstrap_servers=broker)

    def send(self, topic, name, args, kwargs, metadata=None):
        res = super(_KafkaProducer, self).send(topic, name, args, kwargs, metadata)
        return ProducerResult(self.send_message(topic, res.job_instance), res.job_instance)

    def send_message(self, topic, job, block=True):
        message = {'job': {'id': job.id}}
        record = self.producer.send(topic, self.serializer.serialize(message))
        # block async producer by default, otherwise
        # underground sender thread could be terminated
        if block:
            return record.get(timeout=30)
        return record


class _KafkaConsumer(AbstractConsumer):
    def __init__(self, topics, group=None, broker=None, serializer=kafka_serializer):
        self.serializer = serializer
        self.consumer = KafkaConsumer(*topics, group_id=group, bootstrap_servers=broker)

    def get_job(self, message):
        if 'job' in message and 'id' in message['job']:
            return JobStatus.objects.find_one(message['job']['id'])

    def iterator(self):
        while 1:
            try:
                message = next(self.consumer)
            except ConsumerTimeout:
                logging.getLogger('jobs.timeout').info('*')
            except Exception:
                logging.exception("_KafkaConsumer.iterator exception")
            else:
                logging.debug(u'Message consumed {}'.format(message))
                try:
                    msg = self.serializer.deserialize(message.value)
                except:  # json.loads exception
                    logging.exception(u'Failed to deserialize {}'.format(message.value))
                else:
                    job = self.get_job(msg)
                    if job:
                        yield job
                    else:
                        logging.exception(u'Cannot instantiate job from message {}'.format(msg))

    def commit(self):
        self.consumer.commit()


class KafkaTransport(AbstractTransport):
    def create_producer(self, broker=None):
        return _KafkaProducer(broker=broker)

    def create_consumer(self, topics, group, broker, serializer=kafka_serializer):
        return _KafkaConsumer(
            topics=topics,
            group=group,
            broker=broker,
            serializer=serializer)

