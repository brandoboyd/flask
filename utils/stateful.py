from solariat.db.abstract import Document
from solariat.db import fields
from solariat_bottle.utils.hash import mhash
from solariat_bottle.settings import LOGGER


class TaskState(Document):
    params = fields.DictField()
    state = fields.DictField()


class Stateful(object):

    def __init__(self, *args, **kwargs):
        reset_state = kwargs.pop('reset_state', False)
        self.__stateful_params_cls = None
        self.__stateless = kwargs.pop('stateless', False)
        if self.__stateless:
            super(Stateful, self).__init__(*args, **kwargs)
            return

        # support decorators
        for name, method in list(self.__class__.__dict__.iteritems()):
            if hasattr(method, '_state_serializer'):
                setattr(self.__class__, 'serialize_state', method)
            elif hasattr(method, '_state_deserializer'):
                setattr(self.__class__, 'deserialize_state', method)
            elif hasattr(method, '_stateful_params'):
                setattr(self.__class__, 'stateful_params', method)
                if hasattr(method, '_stateful_params_cls'):
                    self.__stateful_params_cls = method._stateful_params_cls

        # if 'stateless' not in kwargs:
        self.__stateful_task = None
        self.__stateful_id = None
        self.__stateful_params = None
        self.__restore_state(reset_state=reset_state)
        super(Stateful, self).__init__(*args, **kwargs)

    def stateful_params(self):
        return NotImplementedError('Must return BSON-safe dict of params, unique for related Stateful.')

    def serialize_state(self):
        raise NotImplementedError('Must return BSON-safe dict with state data.')

    def deserialize_state(self, state):
        raise NotImplementedError('Must set self.fields to values from :state dict')

    def __restore_state(self, reset_state=False):
        params = self.stateful_params()
        implicit_cls = getattr(self.stateful_params, '_stateful_params_cls', None)
        self.__check_class_presence(params, implicit_cls=implicit_cls)
        state_doc = TaskState.objects.coll.find_one({TaskState.params.db_field: params})
        task_state = state_doc and TaskState(state_doc) or None

        if not task_state:
            task_state = TaskState(params=params, state={})
            task_state.save()
        elif reset_state:
            task_state.state = {}
        elif task_state.state:
            self.deserialize_state(task_state.state)

        self.__stateful_id = task_state.id
        self.__stateful_task = task_state

    def __update_state(self):
        if self.__stateless:
            return

        task = self.__stateful_task
        state = self.serialize_state()
        if state is None:
            return
        if state != task.state:
            upd_doc = {'$set': {TaskState.state.db_field: state}}
            TaskState.objects.coll.update({'_id': self.__stateful_id}, upd_doc)
            task.state = state
        return

    def __check_class_presence(self, params, implicit_cls=None):
        assert isinstance(params, dict), \
            'stateful_params() must return dict, returned: %s' % params

        if implicit_cls is not None:
            cls = implicit_cls
        elif '_class_' in params:
            cls = params['_class_']
        else:
            cls = self.__class__

        classname = '%s.%s' % (cls.__module__, cls.__name__)
        params['_class_'] = classname
        return params

    @classmethod
    def get_stateful_cls(cls):
        cls = getattr(cls.stateful_params, '_stateful_params_cls', cls)
        classname = '%s.%s' % (cls.__module__, cls.__name__)
        return classname


def stateful_params(method):
    method._stateful_params = True
    return method


def stateful_params_cls(cls):
    def _mark_method(method):
        method._stateful_params = True
        method._stateful_params_cls = cls
        return method
    return _mark_method


def serializer(method):
    method._state_serializer = True
    return method


def deserializer(method):
    method._state_deserializer = True
    return method


def state_updater(method):
    def _method(*args, **kwargs):
        res = method(*args, **kwargs)
        stateful_obj = args[0]
        if isinstance(stateful_obj, Stateful):
            stateful_obj._Stateful__update_state()
        return res
    return _method
