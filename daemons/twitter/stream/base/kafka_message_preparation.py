from solariat_bottle.daemons.twitter.stream.base.kafka_producer import KafkaProducer


class KafkaDataPreparation:

    @staticmethod
    def on_message(username, task, kwargs):
        KafkaProducer.send(task, username, kwargs)

    @staticmethod
    def on_event(event, stream_data):
        KafkaProducer.send_event(event, stream_data)
