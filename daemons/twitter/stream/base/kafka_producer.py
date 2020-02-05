from kafka import KafkaProducer as Producer
from solariat.utils.logger import setup_logger
from solariat_bottle.daemons.twitter.stream.base import kafka_serializer
from solariat_bottle.settings import LOG_LEVEL


class KafkaProducer:

    @staticmethod
    def setup_kafka_producer(bot_options):
        setup_logger('kafka.conn', level=LOG_LEVEL, format='%(asctime)-15s (%(threadName)-9s) %(levelname)s %(message)s', patch_logging=True)
        setup_logger('kafka.client', level=LOG_LEVEL, format='%(asctime)-15s (%(threadName)-9s) %(levelname)s %(message)s', patch_logging=True)

        kafka_opts = {}
        if hasattr(bot_options, 'retries'):
            kafka_opts['retries'] = bot_options.retries
        if hasattr(bot_options, 'retry_backoff_ms'):
            kafka_opts['retry_backoff_ms'] = bot_options.retry_backoff_ms
        if hasattr(bot_options, 'message_max_bytes'):
            kafka_opts['max_request_size'] = bot_options.message_max_bytes

        KafkaProducer.producer = Producer(bootstrap_servers=bot_options.broker, **kafka_opts)
        KafkaProducer.topic = bot_options.kafkatopic

    @staticmethod
    def send(task, username, kwargs):
        if not hasattr(KafkaProducer, 'producer'):
            raise NameError('Cant find kafka producer. Probably setup_kafka_producer(bot_options) wasnt called.')
        message = dict()
        message['task'] = task
        message['username'] = username
        message['kwargs'] = kwargs
        # block async producer by default, otherwise
        # underground sender thread could be terminated
        resp = KafkaProducer.producer.send(KafkaProducer.topic, kafka_serializer.serialize(message))
        resp.get(timeout=30)

    @staticmethod
    def send_event(event, stream_data):
        if not hasattr(KafkaProducer, 'producer'):
            raise NameError('Cant find kafka producer. Probably setup_kafka_producer(bot_options) wasnt called.')
        message = dict()
        message['event'] = event
        message['stream_data'] = stream_data
        KafkaProducer.producer.send(KafkaProducer.topic, kafka_serializer.serialize(message))
