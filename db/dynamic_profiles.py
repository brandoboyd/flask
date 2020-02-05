from datetime import timedelta, datetime
from pymongo.errors import OperationFailure

from solariat.db import fields
from solariat_bottle.settings import LOGGER, AppException
from solariat_bottle.db.user import get_user
from solariat_bottle.db.filters import FilterTranslator
from solariat_bottle.db.sequences import AutoIncrementField
from solariat_bottle.db.schema_based import (SchemaBased, SchemaValidationError,
                                             SkipDataWithIdNone,
                                             AuthDocument,
                                             finish_data_load, sync_data,
                                             ImproperStateError,
                                             KEY_TYPE, KEY_NAME, KEY_IS_ID,
                                             TYPE_STRING)
from solariat_bottle.schema_data_loaders.base import SchemaBasedDataLoader

import time

FIELD_TOO_LONG = 'TOO LONG TO DISPLAY'


class DynamicProfile(SchemaBased):

    _id_field = None

    @classmethod
    def create_data_class(cls, name, schema_json, collection):
        profile_class = super(DynamicProfile, cls).create_data_class(name,
                                                                     schema_json,
                                                                     collection,
                                                                     inherit_from=DynamicImportedProfile)
        profile_class.meta_schema = schema_json
        return profile_class

    @property
    def id_field(self):
        if not self._id_field:
            if self.schema:
                is_id_col = [col for col in self.schema if KEY_IS_ID in col][0]
                self._id_field = is_id_col[KEY_NAME]

        return self._id_field

    @property
    def is_locked(self):
        return self.sync_status not in (self.IN_SYNC, self.OUT_OF_SYNC)

    @classmethod
    def create(cls, parent_id, **kwargs):
        return super(DynamicProfile, cls).create(parent_id, cls.__name__, **kwargs)

    def _validate_schema(self, schema_json):
        '''Agent/Customer Profiles schema could be customized almost in any way.'''
        if not schema_json:
            raise SchemaValidationError('Schema could not be empty')

        if len([1 for col in schema_json if col.get(KEY_IS_ID)]) != 1:
            raise SchemaValidationError('Profile schema or imported data '
                                        'must contain exact one "ID_FIELD".')

    def preprocess_imported_data(self, mongo_data):
        '''Insert the id field to the data.'''
        if not self.id_field:
            return

        _id = mongo_data.get(self.id_field)
        if _id is None:
            raise SkipDataWithIdNone('id_field: %s is None, skip item' % self._id_field)

        mongo_data['id'] = _id

    def accept_sync(self, events_processing=True):
        from solariat_bottle.db.dynamic_event import postprocess_events

        if self.sync_status != self.SYNCED:
            raise ImproperStateError(self)

        if not events_processing:
            super(DynamicProfile, self).accept_sync()
            return

        user = get_user()
        user.account.reload()
        if user.account.event_processing_lock:
            raise ImproperStateError('Cannot accept sync now, global '
                                     'events re-processing is in progress.')

        user.account.update(event_processing_lock=True)
        super(DynamicProfile, self).accept_sync()
        postprocess_events.async(user)


class DynamicImportedProfile(AuthDocument):

    id = fields.CustomIdField()
    actor_num = AutoIncrementField(counter_name='ActorCounter', db_field='ar')
    linked_profile_ids = fields.ListField(fields.StringField())
    account_id = fields.ObjectIdField()

    @property
    def linked_profiles(self):
        from solariat_bottle.db.user_profiles.user_profile import UserProfile
        return UserProfile.objects(id__in=self.linked_profile_ids)[:]

    def get_profile_of_type(self, typename):
        if not isinstance(typename, basestring):
            typename = typename.__name__

        for profile in self.linked_profiles:
            if profile.__class__.__name__ == typename:
                return profile

    def add_profile(self, platform_profile):
        self.linked_profile_ids.append(str(platform_profile.id))
        self.save()

    def has_linked_profile(self, platform_profile):
        return str(platform_profile.id) in self.linked_profile_ids

    def to_dict(self, **kw):
        base_dict = super(DynamicImportedProfile, self).to_dict(**kw)
        for key, val in base_dict.iteritems():
            if len(str(val)) > 100:
                base_dict[key] = FIELD_TOO_LONG
        return base_dict

class ActionProfile(DynamicProfile):
    action_id = fields.StringField(unique=True)

    indexes = ('action_id', )


class CustomerProfile(DynamicProfile):
    pass


class AgentProfile(DynamicProfile):
    pass

    cardinalities_lu = fields.DateTimeField()
    has_indexes = fields.BooleanField(default=False)

    refresh_rate = timedelta(hours=2)

    def compute_cardinalities(self):
        if self.cardinalities_lu:
            if self.cardinalities_lu + self.refresh_rate >= datetime.utcnow():
                return
        super(AgentProfile, self).compute_cardinalities()
        if self.cardinalities:
            self.cardinalities_lu = datetime.utcnow()
            if not self.has_indexes:
                self.create_indexes()
        self.save()

    def create_indexes(self):
        coll = self.data_coll
        # For bigger collections try and create indexes
        if self.id_field:
            coll.create_index(self.id_field)
        for key, value in self.cardinalities.iteritems():
            try:
                coll.create_index(key)
            except OperationFailure, ex:
                LOGGER.warning("Mongo operation failed while trying to create index: %s", ex)
        if self.created_at_field:
            coll.create_index(self.created_at_field)
        self.has_indexes = True

    @staticmethod
    def construct_filter_query(filter_str, context=[]):
        from solariat_bottle.api.agents import DOT_REPLACEMENT_STR
        filter_str = filter_str.replace('.', DOT_REPLACEMENT_STR)
        query = FilterTranslator(filter_str, context=context).get_mongo_query()
        return query, query


class DynamicProfileManagersFactory(object):

    profile_cls = None

    def __init__(self, ):
        self.attr_name = '_%sManager' % self.profile_cls.__name__

    def __get__(self, instance, cls):
        # assert cls == self.profile_cls
        if instance is None:
            return None
        if not hasattr(instance, self.attr_name):
            setattr(instance, self.attr_name, DynamicProfileManager(instance, self.profile_cls))
        return getattr(instance, self.attr_name)


class DynamicProfileManager(object):

    def __init__(self, parent, profile_cls):
        self.parent = parent
        self.profile_cls = profile_cls

    def create(self, user, data_loader):
        discovered_schema = data_loader.read_schema()
        assert isinstance(data_loader, SchemaBasedDataLoader)
        schema_entity = self.profile_cls.create(self.parent.id)
        schema_entity.add_perm(user)
        start = time.time()
        schema_entity.update(discovered_schema=discovered_schema)
        LOGGER.info('Analazing of input data took: %s', time.time() - start)

        finish_data_load.async(user, schema_entity, data_loader)
        # finish_data_load(user, schema_entity, data_loader)
        return schema_entity

    def update(self, user, data_loader):
        schema_entity = self.get(user)
        if not schema_entity:
            return

        finish_data_load.async(user, schema_entity, data_loader)
        return schema_entity

    def apply_sync(self, profile):
        sync_data.async(profile)

    def get(self, user=None):
        return self.profile_cls.objects.find_one(parent_id=self.parent.id)

    # TODO: getting auth instance without user
    def _get(self, upsert=True):
        profile_cls = self.profile_cls.objects.find_one(parent_id=self.parent.id)
        if profile_cls is None and upsert:
            profile_cls = self.profile_cls.create(self.parent.id)
            # profile_cls.create_indexes()
        return profile_cls

    def delete(self, user):
        profile = self.get(user)
        if not profile:
            return False

        profile.drop_data()
        profile.delete_by_user(user)
        return True


class CustomerProfileDynamicManager(DynamicProfileManagersFactory):
    profile_cls = CustomerProfile


class AgentProfileDynamicManager(DynamicProfileManagersFactory):
    profile_cls = AgentProfile


class ActionProfileDynamicManager(DynamicProfileManagersFactory):
    profile_cls = ActionProfile

