from solariat_bottle.workers import io_pool
from solariat.db import fields
from solariat.db.abstract import MetaDocument
from solariat.utils.app_mode import is_test_mode
from solariat_bottle.db.auth import AuthDocument
from solariat_bottle.db.events.event_type import BaseEventType
from solariat_bottle.db.schema_based import (GetSchemaBased,
                                             InstanceManagerFactory,
                                             InstanceManager,
                                             finish_data_load,
                                             SchemaValidationError,
                                             sync_data,
                                             ImproperStateError,
                                             KEY_NAME)
# from solariat_bottle.schema_data_loaders.base import SchemaBasedDataLoader, WrongFileExtension
from solariat_bottle.settings import LOGGER, AppException
from solariat.utils.timeslot import utc, now, datetime_to_timestamp_ms

KEY_CREATED_AT = 'created_time'
import time
import pymongo
from bson.objectid import ObjectId

KEY_ACTOR_ID = 'actor_id'
KEY_NATIVE_ID = 'native_id'
KEY_IS_NATIVE_ID = 'is_native_id'
KEY_EVENT_TYPE = 'event_type'


def run_or_restart_postprocessing(user, msg):
    account = user.account
    account.reload()

    if account.event_processing_lock:
        account.update(event_processing_needs_restart=True)
        LOGGER.info(msg)
    else:
        account.update(event_processing_lock=True)
        postprocess_events.async(user)

@io_pool.task
def postprocess_events(user):
    from solariat_bottle.db.user import set_user

    set_user(user)
    account = user.account

    start = time.time()
    try:
        _postprocess_events(account)

        # TODO: to remove
        # [11/11/16, 5:11:01 PM] Bogdan Neacsa: Hey Vlad, the way the architecture is going to work this is a scheduled task
        # [11/11/16, 5:11:10 PM] Bogdan Neacsa: So it will just restart automatically on next iteration
        # stop = False
        # while not stop:
        #     _postprocess_events(account)
        #     account.reload()
        #     if account.event_processing_needs_restart:
        #         account.update(event_processing_needs_restart=False)
        #         continue
        #     stop = True
    except:
        LOGGER.critical('[DynamicEvents Postprocessing] Cannot process events:', exc_info=True)
    finally:
        account.update(event_processing_lock=False, event_processing_needs_restart=False)

    LOGGER.info('[DynamicEvents Postprocessing] took: %s sec', time.time() - start)


def _postprocess_events(account):
    assert account.event_processing_lock
    from solariat_bottle.db.events.event import Event
    from solariat_bottle.db.journeys.customer_journey import CustomerJourney

    LOGGER.info('[DynamicEvents Postprocessing] Start re-processing '
                'ALL dynamic events because some of schemas were changed.')

    # Reset customer journey data
    CustomerJourney.objects.remove(account_id=account.id)
    # TODO: After account specific collection is done this should work just fine / uncomment
    # Event.objects.coll.update({'_id': {'$ne': 1}}, {'$set': {'_wp': False}}, multi=True)
    channels = account.get_current_channels()
    Event.objects.coll.update(
        {'_id': {'$ne': 1}, 'cs': {'$in': [c.id for c in channels]}},
        {'$set': {'_wp': False}},
        multi=True)

    from solariat_bottle.tasks.journeys import process_event_batch
    batch_size = 2000
    total_count = Event.objects.count()
    n_batches = total_count / batch_size + 1
    progress = 0
    for batch_nr in xrange(n_batches):
        process_event_batch(account.id, batch_size)
        progress += 100.0 / n_batches
        account.update(resync_progress=progress)


class ChannelTypeIsLocked(AppException):
    http_code = 400


class DuplicateIdOrNativeIdError(AppException):
    pass


# create another SchemaBased, inherited from BaseEventType
SchemaBasedEventType = GetSchemaBased(base=BaseEventType)

class EventType(SchemaBasedEventType):

    allow_inheritance = True

    channel_type_id = fields.ObjectIdField()    # TODO: field temprorary returned for UI
    channel_type_name = fields.StringField()

    channel_id = None
    import_id = None
    before_import_status = None
    user = None
    _native_id_field = None

    is_static = False

    # @property
    # def platform(self):
    #     # for compatibility with customer_journey.LabelingStrategy.compute_label
    #     # return self.name
    #     return self.channel_type_name

    @property
    def data_class_name(self):
        return '%s%s' % (self.name.encode('utf8'), self.parent_id)

    @classmethod
    def create_data_class(cls, name, schema_json, collection):
        from solariat_bottle.db.events.event import DynamicEvent

        data_class = super(EventType, cls).create_data_class(name,
                                                             schema_json,
                                                             collection,
                                                             inherit_from=DynamicEvent)
        return data_class

    def get_data_class(self):
        data_class = super(EventType, self).get_data_class()

        def platform(_self):
            return self.name
        data_class.platform = property(platform)

        if self.data_class_name not in MetaDocument.Registry:
            MetaDocument.Registry[data_class.__name__] = data_class
        return data_class

    def update(self, *args, **kwargs):
        if 'schema' in kwargs and kwargs['schema'] != self.schema:
            from solariat.db.abstract import MetaDocument
            try:
                del MetaDocument.Registry[self.data_class_name]
            except:
                pass
            self._native_id_field = None
        return super(EventType, self).update(*args, **kwargs)

    def enforce_schema(self, raw_data, status):
        mongo_data = super(EventType, self).enforce_schema(raw_data, status)
        if KEY_ACTOR_ID in raw_data:
            mongo_data[KEY_ACTOR_ID] = raw_data[KEY_ACTOR_ID]
        # if self.native_id_field in raw_data:
        #     mongo_data[KEY_NATIVE_ID] = raw_data[self.native_id_field]

        return mongo_data

    @property
    def created_at_field(self):
        created_name = None
        for schema_entry in self.schema:
            if KEY_CREATED_AT in schema_entry:
                created_name = schema_entry[KEY_NAME]
                break
        return created_name

    @property
    def native_id_field(self):
        if not self._native_id_field:
            for col in self.schema:
                if col.get(KEY_IS_NATIVE_ID):
                    self._native_id_field = col[KEY_NAME]
                    break
        return self._native_id_field

    def preprocess_imported_data(self, mongo_data):
        from solariat_bottle.db.events.event import DynamicEvent
        from solariat_bottle.db.events.event import EventManager

        mongo_data['channels'] = [self.channel_id]
        mongo_data['event_type'] = self.display_name
        mongo_data['event_type_id'] = self.id
        mongo_data['import_id'] = self.import_id
        mongo_data['_created'] = mongo_data.get(self.created_at_field, now())
        mongo_data.setdefault('is_inbound', True)   # TODO: derive from channel
        mongo_data.pop('acl', None)

        native_field = self.native_id_field
        native_id = None
        if native_field and mongo_data.get(native_field):
            native_id = mongo_data.get(native_field)
            mongo_data['_native_id'] = native_id
        data_cls = self.get_data_class()

        if data_cls.objects.find_one(_native_id=native_id):
            raise DuplicateIdOrNativeIdError(mongo_data)

        data_cls.objects._handle_create_parameters(None, mongo_data)

    def import_data(self, user, data_loader, *args, **kwargs):
        if not self.channel_id:
            raise ImproperStateError('event_type.channel_id must be set before importing data')

        self.import_id = datetime_to_timestamp_ms(now())
        self.before_import_status = self.sync_status
        self.user = user
        return super(EventType, self).import_data(user, data_loader)

    def after_import_hook(self):
        assert self.import_id
        assert self.before_import_status
        assert self.user

        super(EventType, self).after_import_hook()
        EventManager = self.get_data_class().objects

        # we don't need to run events processing for raw data
        # it will be run after sync apply
        if self.before_import_status == self.OUT_OF_SYNC:
            self.import_id = None
            self.before_import_status = None
            self.user = None
            return

        # TODO: split into batches
        # let's save same behaviour as for api, put in queue if event_processing_lock
        for event in EventManager.find(import_id=self.import_id):
            EventManager.postprocess_event(event)

        self.import_id = None
        self.before_import_status = None
        self.user = None

    @property
    def is_locked(self):
        if self.schema and self.sync_status in (self.SYNCING, self.IMPORTING, self.SYNCED):
            return True
        return False

    def _validate_schema(self, schema_json):
        if not schema_json:
            raise SchemaValidationError('Schema could not be empty')

    def accept_sync(self):
        from solariat_bottle.db.user import get_user
        user = get_user()
        account = user.account

        if self.sync_status != self.SYNCED:
            raise ImproperStateError(self)

        coll = self.data_sync_coll
        count = coll.count()
        if not count:
            raise ImproperStateError('Cannot accept sync on 0 items.')

        account.reload()
        if account.event_processing_lock:
            raise ImproperStateError('Cannot accept sync now, global '
                                     'events re-processing is in progress.')

        account.update(event_processing_lock=True)
        bulk_insert = self.all_data_coll.initialize_unordered_bulk_op()
        for doc in self.data_sync_coll.find():
            bulk_insert.insert(doc)
        self.data_coll.remove()
        bulk_insert.execute()
        self.data_sync_coll.drop()
        postprocess_events.async(user)
        self.update(sync_status=self.IN_SYNC,
                    updated_at=utc(now()),
                    rows=count,
                    sync_errors={})

    @property
    def data_query(self):
        return {'event_type': self.display_name}

    @property
    def all_data_coll(self):
        return super(EventType, self).data_coll

    @property
    def data_coll(self):
        return CollectionPart(self.all_data_coll, self.data_query)

    def get_data(self, **filter_):
        filter_.update(self.data_query)
        return super(EventType, self).get_data(**filter_)

    def drop_data(self):
        self.all_data_coll.remove(self.data_query)
        self.data_sync_coll.drop()


class CollectionPart(object):
    def __init__(self, shared_coll, data_query):
        self.shared_coll = shared_coll
        self.data_query = data_query

    def find(self, spec=None, **kwargs):
        if spec is None:
            spec = {}
        spec.update(self.data_query)
        return self.shared_coll.find(spec, **kwargs)

    def find_one(self, spec_or_id=None, **kwargs):
        if spec_or_id is None:
            spec_or_id = {}
        if not isinstance(spec_or_id, dict):
            spec_or_id = {'_id': spec_or_id}
        spec_or_id.update(self.data_query)
        return self.shared_coll.find_one(spec_or_id, **kwargs)

    def count(self):
        return self.shared_coll.find(self.data_query).count()

    def remove(self):
        self.shared_coll.remove(self.data_query)


class EventTypeInstanceManager(InstanceManager):

    def create(self, user, channel_type, name):
        if channel_type.is_locked:
            raise ChannelTypeIsLocked('ChannelType:%s is locked' % channel_type.name)

        defaults = {
            'mongo_collection': 'Post',
            'sync_collection': 'EventType%s_sync' % fields.ObjectId(),
            'channel_type_id': channel_type.id,  # TODO: unify usage of platform/channel_type
            'channel_type_name': channel_type.name,
            'platform': channel_type.name,
            'account_id': self.instance.id,
        }
        event_type = EventType.create_by_user(user, self.instance.id, name, **defaults)
        return event_type

    def discover_schema(self, event_type, data_loader):
        start = time.time()
        discovered_schema = data_loader.read_schema()
        event_type.update(discovered_schema=discovered_schema)
        LOGGER.info('Discovering schema took: %s', time.time() - start)

    def import_data(self, user, channel, event_type, data_loader):
        # TODO: check if channel is active
        event_type.channel_id = channel.id
        finish_data_load.async(user, event_type, data_loader)
        return event_type

    def apply_sync(self, event_type):
        sync_data.async(event_type)

    # TODO: remove user, probably remove this method at all
    def get(self, user, display_name):
        from solariat_bottle.db.events.event_type import BaseEventType
        return BaseEventType.objects.get_by_display_name(self.instance.id, display_name)

    # TODO: remove
    def get_all(self):
        return EventType.objects.find(account_id=self.instance.id)

    def reset_data_classes(self):
        for event_type in self.get_all():
            from solariat.db.abstract import MetaDocument
            try:
                del MetaDocument.Registry[event_type.data_class_name]
            except:
                pass

    def delete(self, user, name):
        # TODO: should we check if parent ChannelType is locked?
        event_type = self.get(user, name)
        if not event_type:
            return False

        event_type.drop_data()
        event_type.delete_by_user(user)
        return True


class EventTypeManagerFactory(InstanceManagerFactory):
    __manager_cls__ = EventTypeInstanceManager


