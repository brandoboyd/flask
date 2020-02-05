"Store events logs for future audit"

import time
from flask import request
from solariat_bottle.tasks.eventlog import log_event as log_event_task

from ..settings import get_var, AppException
from .auth import AuthDocument
from solariat.db import fields


def get_remote_ip():
    "Extract remote ip from request, return None if not provided"
    try:
        return request.remote_addr
    except RuntimeError:  # Flask: working outside of request context
        return None

def log_event(event_name, **kw):
    if not get_var('EVENT_LOG_ENABLED', True):
        return

    Klass = globals().get(event_name)
    if not Klass:
        raise AppException("No such event %s" % event_name)

    event = Klass(**kw)

    if get_var('ON_TEST'):
        log_event_task.sync(event)
    else:
        log_event_task.ignore(event)


class EventLog(AuthDocument):
    "Store informmation about variouse events in db"
    type_id    = fields.NumField(required=True, db_field='ti')
    name       = fields.NameField(required=True, db_field='ne')
    timestamp  = fields.NumField(default=time.time)
    ip_address = fields.StringField(db_field='ia', default=get_remote_ip)
    user       = fields.StringField(default='anonymous', db_field='ur')
    account    = fields.StringField(default='solariat', db_field='at')
    note       = fields.StringField(db_field='nte')
    extra_info = fields.DictField(db_field='ei')

class BaseEvent(object):
    "Abstract class for events"
    type_id = 0
    name = 'AbstractEvent'

    def __init__(self, user=None, account=None, ip_address=None, note=None, **kw):
        self.user       = user
        self.account    = account
        self.ip_address = ip_address
        self.note       = note
        self.extra_info = kw

    def log(self):
        "Store log about the event in db"

        from ..utils.logger import get_tango_handler

        event = EventLog.objects.create(
            type_id    = self.type_id,
            name       = self.name,
            ip_address = self.ip_address or "",
            account    = self.account or 'solariat',
            user       = self.user or 'anonymous',
            note       = self.note,
            extra_info = self.extra_info)

        get_tango_handler().emit(event.to_dict())

class LoginEvent(BaseEvent):
    "Represent successful user login"
    type_id = 1
    name = 'UserLoggedIn'

class LoginFailedEvent(BaseEvent):
    "Represent failed login event"
    type_id = 2
    name = 'LoginFailed'

class MessageDispatchedEvent(BaseEvent):
    "Raised on message sent to the author of Post"
    type_id = 3
    name = "MessageDispatched"

class TimedEvent(BaseEvent):
    "For wrapped system calls that we want performance results for."
    type_id = 4
    name = "TimedEvent"

    def __init__(self, user=None, account=None, ip_address=None, note=None, func_name=None, **kw):
        super(TimedEvent, self).__init__( user=user, account=account, ip_address=ip_address, note=note, **kw)
        self.name = "%s:%s" % (self.name, func_name)

