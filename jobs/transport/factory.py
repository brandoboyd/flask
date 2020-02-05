import importlib

KAFKA_TRANSPORT = 'kafka'
IN_MEM_TRANSPORT = 'memory'
DB_TRANSPORT = 'database'
SERIAL_TRANSPORT = 'serial'     # for tests
GEVENT_POOL = 'gevent_pool'

TRANSPORT_OPTS = KAFKA_TRANSPORT, IN_MEM_TRANSPORT, DB_TRANSPORT
DEFAULT_TRANSPORT = KAFKA_TRANSPORT

_mapping = {
    KAFKA_TRANSPORT: '.kafka.KafkaTransport',
    IN_MEM_TRANSPORT: '.memory.InMemoryTransport',
    DB_TRANSPORT: '.database.DatabaseTransport',
    SERIAL_TRANSPORT: '.serial.SerialTransport',
    GEVENT_POOL: '.gevent_pool.GeventPoolTransport'
}


def get(manager, transport=None):
    transport = transport or DEFAULT_TRANSPORT

    module_name, class_name = _mapping[transport].rsplit(".", 1)
    try:
        TransportClass = getattr(importlib.import_module(module_name, package=__package__), class_name)
    except AttributeError:
        import logging
        logging.exception("Failed to import %s" % _mapping[transport])
        raise

    return TransportClass(manager)
