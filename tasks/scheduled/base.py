from abc import ABCMeta, abstractmethod
import hashlib
from datetime import timedelta, datetime

from solariat_bottle.settings import LOGGER
from solariat.db import fields
from solariat.db.abstract import Document
from solariat.utils.helpers import enum, init_with_default

TaskStateEnum = enum(WAIT_NEXT=0, IN_PROGRESS=1, FAILED=2)


class _ScheduledTaskDoc(Document):

    collection = 'ScheduledTask'
    started_time = fields.DateTimeField()
    last_run = fields.DateTimeField()
    next_run = fields.DateTimeField()
    _interval = fields.NumField()
    state = fields.NumField()

    def get_interval(self):
        return timedelta(milliseconds=int(self._interval) * 1000)

    def __init__(self, data=None, **kwargs):

        interval = kwargs.get('interval', None)
        kwargs.pop('interval', None)
        super(_ScheduledTaskDoc, self).__init__(data, **kwargs)

        if data is None:
            if not isinstance(interval, timedelta):
                raise Exception("Interval should be an instance of 'timedelta'")
            self._interval = interval.total_seconds()
            self.started_time = init_with_default(kwargs, 'started_time', datetime.utcnow())
            self.last_run = init_with_default(kwargs, 'last_run', self.started_time)
            self.state = init_with_default(kwargs, 'state', TaskStateEnum.WAIT_NEXT)
            self.set_next_run()


    def set_next_run(self):
        self.last_run =  datetime.utcnow()
        self.next_run = self.last_run + self.get_interval()
        self.save()


class BaseScheduledTask(object):

    __metaclass__ = ABCMeta
    __logger = LOGGER
    _db_task = None

    @classmethod
    def _get_db_task(cls):

        return cls._db_task


    @classmethod
    def _resolve(cls, **kw):

        id = cls.__get_id()
        cls._db_task = _ScheduledTaskDoc.objects.find_one(id)
        if cls._db_task is None:
            kw['id'] = id
            cls._db_task = _ScheduledTaskDoc(**kw)
            cls._db_task.save()

        return cls

    @abstractmethod
    def instance(cls):
        '''
        There should be the code, which initialize task with basic
        !!! _resolve method of the base class should be called
        '''

    @abstractmethod
    def should_do(cls, user):
        '''
        Task's computation logic should be defined in this method
        '''

    @classmethod
    def execute(cls, user):

        try:
            cls.__change_state(TaskStateEnum.IN_PROGRESS)
            cls.should_do(user)
            cls.__change_state(TaskStateEnum.WAIT_NEXT)
        except Exception, e:
            cls.__change_state(TaskStateEnum.FAILED)
            cls.__logger.exception(e)
        finally:
            cls._db_task.set_next_run()


    @classmethod
    def get_state(cls):

        return cls._db_task.state


    @classmethod
    def __get_id(cls):

        return hashlib.md5(cls.__name__).hexdigest()


    @classmethod
    def __change_state(cls, state):
        cls._db_task.state = state
        cls._db_task.save()


    @classmethod
    def _log_ex(cls, message, ex):
        cls.__logger.exception(message)
        cls.__logger.exception(ex)

    @classmethod
    def _log_warn(cls, message):
        cls.__logger.warning(message)