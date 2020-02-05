import subprocess
from collections import defaultdict
from kafka import KafkaClient
from threading import RLock

from solariat_bottle.settings import get_var, get_app_mode
from solariat.metacls import Singleton
from solariat_bottle.settings import LOGGER


class JobsClusterConfigurationError(Exception):
    pass


class JobsConfig(object):

    __metaclass__ = Singleton

    def __init__(self):
        self._git_commit = None
        self.load()

        if get_var('APP_MODE') == 'prod':
            self.validate()
            self.validate_kafka()

    def load(self):
        try:
            import solariat_bottle.jobs_config as cfg
        except ImportError:
            LOGGER.error('Jobs configuration file "jobs_config.py" is not found.')
            raise

        self.kafka_broker = cfg.KAFKA_BROKER
        self.consumers_group = cfg.CONSUMERS_GROUP
        self.supported_topics = cfg.TOPICS
        self.cluster_config = cfg.CLUSTER_CONFIG
        if get_app_mode() == 'test':
            # default_transport = 'SERIAL'
            self.transport = 'serial'
        else:
            default_transport = 'kafka'
            self.transport = getattr(cfg, 'TRANSPORT', default_transport)

    @property
    def git_commit(self):
        if not self._git_commit:
            commit = subprocess.check_output(['git', 'log', '-1', '--format=%H'])
            self._git_commit = commit.rstrip('\n')
        return self._git_commit

    def validate(self):
        violations = []
        for node in self.cluster_config:
            for consumers in node['processes']:
                unsupported = set(consumers['topics']) - set(self.supported_topics)
                if unsupported:
                    violations.append({node['machine_id']: unsupported})

        if violations:
            msg = 'Consumers configured with unsupported topics: %s' % violations
            raise JobsClusterConfigurationError(msg)

    def validate_kafka(self):
        if self.transport != 'kafka':
            return
        client = KafkaClient(self.kafka_broker)
        lock_client = RLock()
        with lock_client:
            no_topics = set(self.supported_topics) - set(client.topics)
        if no_topics:
            msg = 'Topics in kafka are not created: %s' % no_topics
            raise JobsClusterConfigurationError(msg)
            # LOGGER.error(msg)

        topic_consumers = defaultdict(int)
        for processes in [p for node in self.cluster_config for p in node['processes']]:
            for topics in processes['topics']:
                topic_consumers[topics] += processes['consumers']

        with lock_client:
            topics_info = client.topic_partitions.items()
        for topic, part_info in topics_info:
            if topic not in self.supported_topics:
                if topic != '__consumer_offsets':
                    LOGGER.warning('Topic "%s" exists in kafka, but not in supported topics', topic)
                continue

            partitions = len(part_info)
            if topic_consumers[topic] == 0:
                msg = 'No consumers configured for topic "%s"' % topic
                raise JobsClusterConfigurationError(msg)
                # LOGGER.error(msg)
            elif topic_consumers[topic] < partitions:
                LOGGER.warning('Consumers for topic "%s" will read from multiple partitions', topic)
            elif topic_consumers[topic] > partitions:
                LOGGER.warning('Some consumers for topic "%s" will be idle', topic)

    def get_machine_options(self, machine):
        try:
            machine = [m for m in self.cluster_config if m['machine_id'] == machine][0]
            return machine['processes']
        except (IndexError, KeyError):
            LOGGER.error('No such machine "%s" exists in config', machine)


jobs_config = JobsConfig()
