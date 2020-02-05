from threading import RLock
from solariat_bottle.settings import LOGGER
from importlib import import_module


class RegistryError(Exception):
    pass


class JobsRegistry(object):

    def __init__(self, config=None):
        self.lock = RLock()
        self.registry = {}
        self.config = config

    def add(self, job):
        with self.lock:
            if job.topic not in self.config.supported_topics:
                raise RegistryError('Job: %s topic "%s" is not supported' % (job.name, job.topic))
            if job.name in self.registry:
                raise RegistryError('Job: %s already exists in registry' % job.name)
            self.registry[job.name] = job
            LOGGER.info('Job with name "%s" added', job.name)

    def get(self, name):
        with self.lock:
            if name not in self.registry:
                LOGGER.info('No Job registered for: %s, trying to import.', name)
                try:
                    self._import_module(name)
                except ImportError:
                    LOGGER.error('Cannot import job module:', exc_info=True)
                    raise RegistryError('No Job registered for: %s' % name)
            return self.registry[name]

    def _import_module(self, fullname):
        name = fullname
        package = None
        if '.' in fullname:
            module_path = fullname.split('.')
            name = '.'.join(module_path[:-1])
            package = module_path[-1]
        import_module(name, package=package)

    def check_unused_topics(self):
        with self.lock:
            registered_topics = {job.topic for job in self.registry.viewvalues()}

        unused = set(self.config.supported_topics) - registered_topics
        LOGGER.warning('There is unused supported topics: %s', unused)

