from kafka import KafkaConsumer
from solariat.utils.logger import setup_logger
from solariat_bottle.daemons.twitter.stream.argparse import parse_options
from solariat_bottle.daemons.twitter.stream.base import kafka_serializer
from solariat_bottle.daemons.twitter.stream.base.kafka_handler import KafkaHandler
from solariat_bottle.settings import LOGGER, LOG_LEVEL
from solariat_bottle.utils.config import sync_with_keyserver
sync_with_keyserver()
from solariat_bottle.tasks.nlp import warmup_nlp
warmup_nlp()


class KafkaMessagesConsumer(object):

    def __init__(self, bot_options, kafka_handler, kafka_consumer):

        self.setup_logging()
        self.consumer = kafka_consumer
        self.kafka_handler = kafka_handler

    def setup_logging(self):

        LOG_FORMAT = '%(asctime)-15s (%(threadName)-9s) %(levelname)s %(message)s'
        setup_logger(LOGGER, level=LOG_LEVEL, format=LOG_FORMAT, patch_logging=True)

    def run(self):

        for message in self.consumer:
            LOGGER.debug('kafka message consumed: %s', message.value)
            try:
                object = kafka_serializer.deserialize(message.value)
                if 'task' in object:
                    self.kafka_handler.handle_create_post(object['task'], object['username'], object['kwargs'])
                if 'event' in object:
                    self.kafka_handler.on_event_handler(object['event'], object['stream_data'])
            except Exception as e:
                LOGGER.exception(e)


if __name__ == '__main__':
    options = parse_options()
    kafka_opts = {}
    if hasattr(options, 'message_max_bytes'):
        kafka_opts['max_partition_fetch_bytes'] = options.message_max_bytes
    consumer = KafkaConsumer(options.kafkatopic,
                             group_id=options.kafkagroup,
                             bootstrap_servers=options.broker,
                             **kafka_opts)
    KafkaMessagesConsumer(options, KafkaHandler(options), consumer).run()
