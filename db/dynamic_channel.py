from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.schema_based import (SchemaBased,
                                             NameDuplicatedError,
                                             ImproperStateError,
                                             apply_shema_type,
                                             KEY_EXPRESSION,
                                             KEY_TYPE, KEY_NAME)
from solariat_bottle.schema_data_loaders.list import ListDataLoader
from solariat_bottle.db.auth import ArchivingAuthDocument, ArchivingAuthManager
from solariat_bottle.db.account import Account
from solariat_bottle.workers import io_pool
from solariat_bottle.settings import LOGGER
from solariat.db import fields
from solariat.utils.timeslot import now, utc

from collections import defaultdict
from bson.json_util import dumps


class ChannelTypeManager(ArchivingAuthManager):

    def create_by_user(self, user, **kw):
        name = kw['name']
        if self.find_one_by_user(user, account=user.account, name=name):
            raise NameDuplicatedError('Channel Type with name: %s already exists.' % name)

        kw['mongo_collection'] = Channel.collection
        return super(ChannelTypeManager, self).create_by_user(user, **kw)


class ChannelType(ArchivingAuthDocument):

    STATUSES = IN_SYNC, SYNCING, OUT_OF_SYNC = 'IN_SYNC', 'SYNCING', 'OUT_OF_SYNC'

    manager = ChannelTypeManager

    # from base.Channel
    account = fields.ReferenceField(Account, db_field='at', required=True)
    name = fields.StringField(required=True)
    description = fields.StringField()

    schema = fields.ListField(fields.DictField())
    sync_status = fields.StringField(choices=STATUSES, default=IN_SYNC)
    is_locked = fields.BooleanField(default=False)
    mongo_collection = fields.StringField()
    created_at = fields.DateTimeField(default=now)
    updated_at = fields.DateTimeField(default=now)

    _channel_class = None

    @property
    def data_class_name(self):
        # keep classname unique system wide, to exclude collisions in MetaDocument.Registry[name]
        # when creating instance of Channel for different accounts
        return '%s%s' % (self.name.encode('utf8'), self.account.id)

    def get_channel_class(self):
        if self._channel_class is None:
            newclass = SchemaBased.create_data_class(self.data_class_name,
                                                     self.schema,
                                                     self.mongo_collection,
                                                     inherit_from=DynamicEventsImporterChannel,
                                                     _platform=self.name)
            self._channel_class = newclass
        return self._channel_class

    def update(self, *args, **kwargs):
        if 'schema' in kwargs and kwargs['schema'] != self.schema:
            self._channel_class = None

            from solariat.db.abstract import MetaDocument
            try:
                del MetaDocument.Registry[self.data_class_name]
            except:
                pass

        return super(ChannelType, self).update(*args, **kwargs)

    def apply_sync(self, user):
        if self.sync_status != self.OUT_OF_SYNC:
            raise ImproperStateError(self)

        self.update(sync_status=self.SYNCING)

        sync_errors = defaultdict(list)
        sync_coll = self.mongo_collection + 'Sync' + str(user.account.id)
        ChClass = self.get_channel_class()
        SyncClass = SchemaBased.create_data_class(self.data_class_name,
                                                  self.schema,
                                                  sync_coll,
                                                  inherit_from=DynamicEventsImporterChannel,
                                                  _platform=self.name)
        temp_coll = SyncClass.objects.coll

        bulk_insert = temp_coll.initialize_unordered_bulk_op()
        for doc in ChClass.objects.coll.find({'channel_type_id': self.id}):
            synced_data = {}
            for fname, field in ChClass.fields.iteritems():
                val = doc.get(field.db_field)
                if val is None:
                    continue
                synced_data[fname] = field.to_python(val)

            try:
                for col in self.schema:
                    if KEY_EXPRESSION in col:
                        continue

                    col_name = col[KEY_NAME]
                    val = doc.get(col_name)
                    synced_data[col_name] = apply_shema_type(val, col[KEY_TYPE])

                bulk_insert.insert(SyncClass(**synced_data).data)
            except Exception as ex:
                LOGGER.info('Sync error:\n\n %s', ex, exc_info=True)
                SchemaBased._put_sync_error(sync_errors, col_name, val, ex)

        if not sync_errors:
            try:
                bulk_insert.execute()
            except Exception as ex:
                LOGGER.info('Error inserting synced data %s', ex, exc_info=True)
                self.update(sync_status=self.OUT_OF_SYNC)
                temp_coll.drop()
                raise
            else:
                bulk_update = ChClass.objects.coll.initialize_unordered_bulk_op()
                for doc in temp_coll.find():
                    bulk_update.find({'_id': doc['_id']}).replace_one(doc)
                bulk_update.execute()

                temp_coll.drop()
                self.update(sync_status=self.IN_SYNC,
                            updated_at=utc(now()))
                return {}

        self.update(sync_status=self.OUT_OF_SYNC)
        temp_coll.drop()
        return sync_errors


class DynamicEventsImporterChannel(Channel):

    channel_type_id = fields.ObjectIdField(required=True)
    # sync_status = fields.StringField(choices=SchemaBased.STA)

    @classmethod
    def set_dynamic_class(cls, channel, class_name):
        from solariat.db.abstract import MetaDocument

        channel_type_id = channel.data[cls.channel_type_id.db_field]
        # TODO: add account to query?
        channel_type = ChannelType.objects.find_one(id=channel_type_id)
        if channel_type:
            assert channel_type.data_class_name == class_name
            dyn_cls = channel_type.get_channel_class()
            MetaDocument.Registry[dyn_cls.__name__] = dyn_cls
            channel.__class__ = dyn_cls

    def get_outbound_channel(self, user):
        return None

    def import_data(self, user, data_loader, only_event_type=None):
        from solariat_bottle.db.dynamic_event import EventType

        event_types = EventType.objects.find_by_user(user, platform=self.platform)
        EVENT_TYPE_MAP = {et.name: et for et in event_types
                          if et.schema or et.discovered_schema}

        # total = data_loader.total()

        # TODO: we can improve load a much if use QueueDataLoader
        # Thread.run: mail_event_type.import_data( QueueDataLoader(mail_event_Q) )
        # at same time iterate over real data_loader and push to one of the Queues
        # depends on data_type. It makes sense only on stream json load

        imported_data_by_type = defaultdict(list)
        for data_type, json_data in data_loader.load_data():
            if data_type not in EVENT_TYPE_MAP:
                continue
            imported_data_by_type[data_type].append(json_data)

        # TODO: control fails
        exc = None
        for data_type, all_data in imported_data_by_type.iteritems():
            if only_event_type and only_event_type.name != data_type:
                continue

            event_data_loader = ListDataLoader(all_data)
            event_type = EVENT_TYPE_MAP.get(data_type)
            event_type.channel_id = self.id
            try:
                event_type.import_data(user, event_data_loader)
            except Exception as ex:
                exc = ex
                LOGGER.error('Failed to import to event_type: %s, error: %s',
                             event_type,
                             ex,
                             exc_info=True)

        # raise last exception
        if exc:
            raise exc
