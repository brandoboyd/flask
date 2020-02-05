from solariat.db import fields
from solariat.db.abstract import (Document,
                                  KEY_NAME, KEY_TYPE,
                                  KEY_EXPRESSION, TYPE_LIST,
                                  TYPE_STRING, TYPE_INTEGER, TYPE_OBJECT,
                                  TYPE_TIMESTAMP, TYPE_BOOLEAN, TYPE_DICT)
from solariat_bottle.db.auth import ArchivingAuthDocument, AuthDocument
from solariat_bottle.db.user import set_user

from solariat.utils.timeslot import utc, now, datetime_to_timestamp
from solariat_bottle.settings import LOGGER, AppException
from solariat_bottle.workers import io_pool
from solariat_bottle.db.message_queue import TaskMessage

from bson.objectid import ObjectId
import ast
import json
import datetime
import time
from collections import defaultdict
import traceback
import pandas
from pymongo.errors import BulkWriteError, OperationFailure


KEY_CREATED_AT = 'created_time'
KEY_IS_ID = 'is_id'
VALUES = 'values'
COUNT = 'count'
MONGO_BULK_WRITE_ERRORS = 'writeErrors'
MONGO_BULK_ERROR_KEY = 'errmsg'
MONGO_BULK_DATA_KEY = 'op'
MONGO_BULK_INSERTED_KEY = 'nInserted'


class NameDuplicatedError(AppException):
    pass

class SchemaValidationError(AppException):
    pass

class OutOfSyncError(AppException):
    pass

class SkipDataWithIdNone(AppException):
    pass

class ImproperStateError(AppException):
    def __init__(self, item):
        if isinstance(item, SchemaBased):
            msg = 'State is: %s' % {
                # 'status': item.status,
                'sync_status': item.sync_status,
                'schema': 'exists' if item.schema else 'not exists',
                'discovered_schema': 'exists' if item.discovered_schema else 'not exists'
            }
        else:
            msg = item
        super(ImproperStateError, self).__init__(msg)


@io_pool.task
def finish_data_load(user, schema_entity, data_loader, skip_cardinalities=False):
    schema_entity.import_data(user, data_loader, skip_cardinalities)


@io_pool.task
def sync_data(schema_entity):
    schema_entity.apply_sync()
    if schema_entity.is_archived:
        schema_entity.drop_data()
        LOGGER.info('Entity has been archived, stop syncing, drop data.')


def apply_shema_type(col_value, schema_type):
    # TODO: Finish adding all types. Bring up to date with get_type by using constants
    if col_value is None:
        return col_value
    if schema_type == TYPE_STRING:
        return str(col_value)
    if schema_type == TYPE_INTEGER:
        try:
            if isinstance(col_value, datetime.datetime):
                return datetime_to_timestamp(col_value)

            return int(col_value)
        except Exception, ex:
            raise SchemaValidationError(ex)
    if schema_type == TYPE_TIMESTAMP:
        if isinstance(col_value, datetime.datetime):
            return col_value
        return datetime.datetime.fromtimestamp(int(float(col_value)))
    if schema_type == TYPE_LIST:
        try:
            col_value = json.loads(col_value)
        except (ValueError, TypeError):
            pass
        if type(col_value) in (int, long, float, str, unicode, bool):
            return [str(col_value)]
        else:
            return [str(v) for v in list(col_value)]
    if schema_type == TYPE_BOOLEAN:
        return True if str(col_value) in ('1', 'true', 'True') else False
    if schema_type == TYPE_DICT:
        if isinstance(col_value, dict):
            return col_value
        if type(col_value) in (unicode, str):
            try:
                return json.loads(col_value)
            except Exception:
                try:
                    return ast.literal_eval(col_value)
                except Exception:
                    raise SchemaValidationError("Invalid dictionary " + col_value)
        raise SchemaValidationError("Invalid value for a dictionary " + str(col_value))
    if schema_type == TYPE_OBJECT:
        if isinstance(col_value, ObjectId):
            return col_value
        return ObjectId(col_value)
    raise SchemaValidationError("Unknown type: " + schema_type)

def GetSchemaBased(base=ArchivingAuthDocument):
    class SchemaBased(base):

        STORE_FIELD_MAX_SYNC_ERRORS = 5
        STORE_MAX_SYNC_ERRORS = 100
        ERROR_MAX_OUTPUT_ITEMS = 5
        MAX_CARDINALITY_TO_STORE = 20

        SYNC_STATUSES = OUT_OF_SYNC, SYNCING, SYNCED, IMPORTING, IN_SYNC = \
            'OUT_OF_SYNC', 'SYNCING', 'SYNCED', 'IMPORTING', 'IN_SYNC'

        parent_id = fields.ObjectIdField(required=True)  # account_id
        name = fields.StringField()
        mongo_collection = fields.StringField()
        created_at = fields.DateTimeField(default=now)
        updated_at = fields.DateTimeField(default=now)
        load_progress = fields.NumField(default=0)
        rows = fields.NumField(default=0)
        sync_status = fields.StringField(choices=SYNC_STATUSES)
        sync_progress = fields.NumField(default=0)
        sync_collection = fields.StringField()
        sync_errors = fields.DictField()
        items_synced = fields.NumField(default=0)
        items_imported = fields.NumField(default=0)
        schema = fields.ListField(fields.DictField())  # TODO: create FieldSpec(SonDocument)?
        cardinalities = fields.DictField()

        discovered_schema = fields.ListField(fields.DictField())

        indexes = [('parent_id', ), ('name', )]

        _data_cls = None
        _raw_data_cls = None

        @property
        def is_locked(self):
            raise NotImplementedError('This must return True if schema editing is allowed.')

        @classmethod
        def create_by_user(cls, user, parent_id, name, **kwargs):
            cls.objects.populate_acl(user, kwargs)
            dataset = cls.create(parent_id, name, **kwargs)
            return dataset

        @classmethod
        def create(cls, parent_id, name, **kwargs):
            # cannot use unique index because there could be a lot of archived data
            duplicate_query = {
                'parent_id': parent_id,
                'name': name,
                'is_archived': False,
            }

            if cls.objects.coll.find(duplicate_query).count():
                raise NameDuplicatedError('Schema with name %s already exists in account.' % name)

            mongo_coll = '%s%s' % (cls.__name__.lower(), ObjectId())
            sync_coll = '%ssync' % mongo_coll
            dataset_data = {
                'parent_id': parent_id,
                'name': name,
                'sync_status': cls.OUT_OF_SYNC,
                'mongo_collection': mongo_coll,
                'sync_collection': sync_coll,
            }
            dataset_data.update(kwargs)
            dataset = cls.objects.create(**dataset_data)
            return dataset

        @classmethod
        def create_data_class(cls, name, schema_json, collection, inherit_from=AuthDocument, _platform=None):
            newclass = type(name.encode('utf8'), (inherit_from, ), {})
            newclass.meta_schema = schema_json
            newclass.collection = collection

            def platform(self):
                return _platform or name
            newclass.platform = property(platform)

            return newclass

        @property
        def data_class_name(self):
            return self.name

        def get_data_class(self):
            if not self.schema:
                if self._raw_data_cls:
                    return self._raw_data_cls

                # TODO: Not a good idea for JSON to cast all to string, should we leave a way for csv?
                # raw_schema = [dict(col) for col in self.discovered_schema]
                # raw_schema = map(lambda col: col.update({KEY_TYPE: TYPE_STRING}) or col, raw_schema)

                self._raw_data_cls = self.create_data_class(
                    self.data_class_name,
                    self.discovered_schema,
                    self.mongo_collection
                )
                return self._raw_data_cls

            if not self._data_cls:
                self._data_cls = self.create_data_class(self.data_class_name,
                                                        self.schema,
                                                        self.mongo_collection)
            return self._data_cls

        def update(self, *args, **kwargs):
            if 'schema' in kwargs and kwargs['schema'] != self.schema:
                self._data_cls = None
            if 'discovered_schema' in kwargs and kwargs['discovered_schema'] != self.discovered_schema:
                self._raw_data_cls = None
            return super(SchemaBased, self).update(*args, **kwargs)

        def _validate_schema(self, schema_json):
            raise NotImplementedError('Validate new schema on schema update or on data appending.')

        def _clean_schema(self, schema_json):
            for col in schema_json:
                [col.pop(k, None) for k in [k for k, v in col.iteritems() if v == '']]

        def update_schema(self, schema_json):
            if self.is_locked:
                raise ImproperStateError(self)

            self._clean_schema(schema_json)
            self._validate_schema(schema_json)

            if self.schema != schema_json:
                self.update(sync_status=self.OUT_OF_SYNC,
                            schema=schema_json,
                            updated_at=utc(now()))
                return True

        @classmethod
        def _put_sync_error(cls, sync_errors, field, val, ex):
            max_sync_errors = cls.STORE_MAX_SYNC_ERRORS
            max_field_errors = cls.STORE_FIELD_MAX_SYNC_ERRORS

            if len(sync_errors) > max_sync_errors:
                return
            field_errors = sync_errors[field]
            if len(field_errors) > max_field_errors:
                return
            # let's store only unique errors for a field
            error = unicode(ex)
            if [True for _, err in field_errors if err == error]:
                return
            field_errors.append([val, error])

        def apply_sync(self):
            if self.sync_status != self.OUT_OF_SYNC:
                raise ImproperStateError(self)

            if not self.schema:
                raise ImproperStateError('Cannot apply sync without a schema!')

            # if not self.rows:
            #     raise ImproperStateError('Cannot apply sync on empty data!')

            self.update(sync_status=self.SYNCING)

            sync_errors = defaultdict(list)
            # sync_errors = {
            #     'field1': [
            #         [origin_value, error],
            #         [origin_value, error],
            #         [origin_value, error]
            #     ],
            #     ...
            # }
            failed = []
            failed_cnt = 0
            origin_coll = self.data_coll
            total = origin_coll.count()
            data_cls = self.create_data_class(self.data_class_name, self.schema, self.sync_collection)
            step = (total / 100) or 1

            batch_size = 2000
            n_batches = total / batch_size + 1

            for batch_idx in xrange(n_batches):
                bulk_insert = data_cls.objects.coll.initialize_unordered_bulk_op()
                inserted = 0
                for idx, doc in enumerate(origin_coll.find()[batch_idx * batch_size:(batch_idx + 1) * batch_size]):
                    synced_data = {}
                    for fname, field in data_cls.fields.iteritems():
                        if fname in self.schema_fields:
                            continue
                        val = doc.get(field.db_field)
                        if val is None:
                            continue
                        synced_data[fname] = field.to_python(val)

                    try:
                        for col in self.schema:
                            if col.get(KEY_EXPRESSION):
                                continue

                            col_name = col[KEY_NAME]
                            val = doc.get(col_name)
                            # in case of ID field, let's keep original column
                            synced_data[col_name] = apply_shema_type(val, col[KEY_TYPE])
                            if col.get(KEY_IS_ID):
                                if synced_data[col_name] is None:
                                    raise SkipDataWithIdNone('id_field: %s is None, skip item' % col_name)
                                synced_data['id'] = synced_data[col_name]

                        bulk_insert.insert(data_cls(**synced_data).data)
                        inserted += 1
                    except Exception as ex:
                        LOGGER.error('Sync error:\n\n %s', ex, exc_info=True)
                        # collect errors to log output
                        failed_cnt += 1
                        failed.append({
                            'field': col_name,
                            'val': val,
                            'apply': col[KEY_TYPE],
                            'ex': ex,
                        })
                        if len(failed) > self.ERROR_MAX_OUTPUT_ITEMS:
                            del failed[self.ERROR_MAX_OUTPUT_ITEMS:]

                        # collect errors to write to schema based entity
                        self._put_sync_error(sync_errors, col_name, val, ex)

                    if idx % step == 0:
                        if total:
                            self.update(sync_progress=round((batch_idx * batch_size) + float(idx) / total, 2) * 100)
                        else:
                            self.update(sync_progress=100)
                        self.reload()
                        if self.is_archived:
                            return

                failed_cnt = self.handle_bulk_insert(None, inserted, failed, total,
                                                     bulk_insert, failed_cnt, sync_errors)

            self.update(sync_status=self.SYNCED,
                        updated_at=utc(now()),
                        sync_progress=100,
                        items_synced=total - failed_cnt,
                        sync_errors=sync_errors)

        def handle_bulk_insert(self, user, inserted, failed, total, bulk,
                               failed_cnt, sync_errors, op_name='sync'):
            if inserted:
                try:
                    result = bulk.execute()
                    LOGGER.info("Succesfully executed a batch insert " + str(result))
                except BulkWriteError as bwe:
                    from pprint import pformat
                    msg = 'Error executing bulk insert: ' + pformat(bwe.details, indent=4)
                    LOGGER.info(msg)
                    for err in bwe.details[MONGO_BULK_WRITE_ERRORS]:
                        failed_cnt += 1
                        self._put_sync_error(sync_errors, 'Db Error', err[MONGO_BULK_DATA_KEY],
                                             err[MONGO_BULK_ERROR_KEY])

                    if user:
                        TaskMessage.objects.create_error(user, msg)

            if failed:
                total_fail = (total - failed_cnt == 0)
                log_method = getattr(LOGGER, 'error') if total_fail else getattr(LOGGER, 'info')
                msg = 'Failed to %s %s from %s items.\nlast %s errors:' % (
                    op_name,
                    failed_cnt,
                    total,
                    len(failed))
                log_method(msg)

                for fail in failed:
                    ex = fail.pop('ex')
                    log_method('%s\n%s', fail, traceback.format_exc(ex))

                if user:
                    TaskMessage.objects.create_error(user, msg)

            return failed_cnt

        def create_indexes(self):
            coll = self.data_coll
            # For bigger collections try and create indexes
            for key, value in self.cardinalities.iteritems():
                if 'count' in value and value['count'] < 12 or key == self.created_at_field:
                    try:
                        coll.create_index(key)
                    except OperationFailure, ex:
                        LOGGER.warning("Mongo operation failed while trying to create index: %s", ex)
            if self.created_at_field:
                coll.create_index(self.created_at_field)

        def accept_sync(self):
            if self.sync_status != self.SYNCED:
                raise ImproperStateError(self)

            coll = self.data_sync_coll
            count = coll.count()
            # if not count:
            #     raise ImproperStateError('Cannot accept sync on 0 items.')

            if count:
                coll.rename(self.mongo_collection, dropTarget=True)
            self.update(sync_status=self.IN_SYNC,
                        updated_at=utc(now()),
                        rows=count,
                        sync_errors={})
            if count > 10000:
                # For bigger collections try and create indexes
                self.create_indexes()

        def cancel_sync(self):
            if self.sync_status != self.SYNCED:
                raise ImproperStateError(self)

            self.data_sync_coll.drop()
            self.update(sync_status=self.OUT_OF_SYNC,
                        updated_at=utc(now()))

        @property
        def schema_field_types(self):
            field_types = dict()
            schema = self.schema or self.discovered_schema
            for schema_entry in schema:
                field_types[schema_entry[KEY_NAME]] = schema_entry[KEY_TYPE]
            return field_types

        @property
        def created_at_field(self):
            created_name = None
            for schema_entry in self.schema:
                if KEY_CREATED_AT in schema_entry:
                    created_name = schema_entry[KEY_NAME]
                    break
            return created_name

        def get_data(self, ignore_status=False, **filter_):
            if not ignore_status and self.sync_status != self.IN_SYNC:
                raise OutOfSyncError('Status: %s' % self.sync_status)
            return self.get_data_class().objects.find(**filter_)

        def get_data_item(self, ignore_status=False, **filter_):
            if not ignore_status and self.sync_status != self.IN_SYNC:
                raise OutOfSyncError('Status: %s' % self.sync_status)
            return self.get_data_class().objects.find_one(**filter_)

        def drop_data(self):
            from solariat.db.mongo import get_connection
            db = get_connection()
            db[str(self.mongo_collection)].drop()
            db[str(self.sync_collection)].drop()

        def to_dict(self, include_cardinalities=False, fields2show=None, **kw):
            res = super(SchemaBased, self).to_dict(fields2show)
            res['is_locked'] = self.is_locked

            if not include_cardinalities:
                res.pop('cardinalities', None)
                return res

            cardinalities = res['cardinalities'] or {}
            for key, val in cardinalities.iteritems():
                if key not in self.schema_field_types:
                    continue
                if self.schema_field_types[key] != TYPE_TIMESTAMP:
                    continue
                if VALUES not in val:
                    continue

                LOGGER.info('Refreshing cardinalities for %s', str(val))
                val[VALUES] = [dt.strftime('%m/%d/%Y %H:%M:%S')
                                 if isinstance(dt, datetime.date) else dt
                                 for dt in val.get(VALUES, [])]

            return res

        @property
        def data_coll(self):
            from solariat.db.mongo import get_connection
            return get_connection()[str(self.mongo_collection)]

        @property
        def data_sync_coll(self):
            from solariat.db.mongo import get_connection
            return get_connection()[str(self.sync_collection)]

        def after_import_hook(self):
            self.compute_cardinalities()

        def compute_cardinalities(self):
            start = time.time()
            LOGGER.info('Start computing %s cardinality data.', self)

            data_coll = self.data_coll
            unique_values = defaultdict(lambda: dict(count=0, display_count=0, values=set()))

            threshold = self.MAX_CARDINALITY_TO_STORE
            possible_columns = set()
            if self.schema:
                possible_columns.update({col[KEY_NAME] for col in self.schema})
            if self.discovered_schema:
                possible_columns.update({col[KEY_NAME] for col in self.discovered_schema})

            total_count = data_coll.count()
            batch_size = 20000
            n_batches = total_count / batch_size + 1

            for batch_idx in xrange(n_batches):
                for doc in data_coll.find()[batch_idx * batch_size:(batch_idx + 1) * batch_size]:
                    for col, value in doc.iteritems():
                        if isinstance(col, list) or isinstance(col, dict):
                            col = str(col)

                        if col not in possible_columns:
                            continue

                        if unique_values[col][COUNT] > threshold:
                            # column's cardinality is over MAX_CARDINALITY_TO_STORE threshold
                            continue

                        # if pandas.isnull(value): # don't count None and pd.NaT
                        if value is None:
                            continue

                        unique_values[col][VALUES].add(value if not (isinstance(value, list) or isinstance(value, dict)) else str(value))
                        count = unique_values[col][COUNT] = len(unique_values[col][VALUES])

                        if count > threshold:
                            del unique_values[col][VALUES]
                            count = '%d +' % threshold

                        unique_values[col]['display_count'] = count

            # convert set to list
            for col, info in unique_values.iteritems():
                if info[COUNT] == 0:
                    del info[VALUES]
                elif VALUES in info:
                    info[VALUES] = list(info[VALUES])

            self.update(cardinalities=unique_values)
            LOGGER.info('Finish computing cardinality data, took: %s', time.time() - start)


        # def before_import_state_check(self):
        #     if self.sync_status != self.IN_SYNC:
        #         raise ImproperStateError(self)

        def update_import_progress(self, progress):
            self.update(load_progress=progress)
            # self.update(sync_progress=progress) # TODO: rename to import_progress
            self.reload()

        def enforce_schema(self, raw_data, status):
            '''If we decide to go with inserting really RAW data
               into mongo collection without casting when OUT_OF_SYNC,
               then use :status field to make such decision
               to get known
            '''
            from solariat_bottle.utils.predictor_events import translate_column, get_type

            field_types = self.schema_field_types
            mongo_data = {}

            # TODO: cache translate_column
            for _col_name, col_value in raw_data.iteritems():
                col_name = translate_column(_col_name)
                if col_name not in field_types:
                    continue
                mongo_data[col_name] = apply_shema_type(col_value, field_types[col_name])

            return mongo_data

        def preprocess_imported_data(self, mongo_data):
            pass

        def import_data(self, user, data_loader, skip_cardinalities=False):
            # TODO: IMPLEMENT IMPORT ERRORS
            set_user(user)
            start = time.time()
            LOGGER.info('Start importing data')

            status = self.sync_status
            if status not in (self.IN_SYNC, self.OUT_OF_SYNC):
                raise ImproperStateError(self)

            if not self.schema and not self.discovered_schema:
                raise ImproperStateError('No schema to import with. You need '
                                         'to have at least discovered_schema')

            self.update(sync_status=self.IMPORTING, load_progress=0)

            sync_errors = defaultdict(list)
            failed = []
            failed_cnt = 0
            total = data_loader.total()
            step = (total / 100) or 1
            log_once = True
            inserted = 0

            data_cls = self.get_data_class()
            auth_doc_fields = {}
            AuthDocument.objects.populate_acl(user, auth_doc_fields)

            # TODO: (speedup)
            # for frame_chunk in dataframe: !
            bulk_insert = data_cls.objects.coll.initialize_unordered_bulk_op()

            failed_cnt = 0
            batch_size = 20000
            _was_inserted = True
            for idx, raw_data in enumerate(data_loader.load_data(), start=1):
                _was_inserted = False
                mongo_data = None
                try:
                    mongo_data = self.enforce_schema(raw_data, status)
                    mongo_data.update(auth_doc_fields)
                    self.preprocess_imported_data(mongo_data)
                    bulk_insert.insert(data_cls(**mongo_data).data)
                    inserted += 1
                except Exception, ex:
                    failed_cnt += 1
                    failed.append({
                        'error': str(ex),
                        'val': mongo_data,
                        'ex': ex,
                    })
                    if len(failed) > self.ERROR_MAX_OUTPUT_ITEMS:
                        del failed[self.ERROR_MAX_OUTPUT_ITEMS:]

                    self._put_sync_error(sync_errors, str(ex), mongo_data, ex)
                    if log_once:
                        LOGGER.debug('Data cannot be imported with current'
                                     ' schema: %s\n\nor discovered_schema: %s. Error is %s',
                                     self.schema, self.discovered_schema, ex)
                        log_once = False

                if idx % step == 0:
                    if total:
                        progress = round(float(idx) / total, 2) * 100
                    else:
                        progress = 100
                    self.update_import_progress(progress)
                    if self.is_archived:
                        return

                if inserted % batch_size == 0:
                    self.handle_bulk_insert(user, inserted, failed, total, bulk_insert,
                                            failed_cnt, sync_errors, op_name='import')
                    failed = []
                    _was_inserted = True
                    bulk_insert = data_cls.objects.coll.initialize_unordered_bulk_op()

            if not _was_inserted:
                # Last batch
                self.handle_bulk_insert(user, inserted, failed, total, bulk_insert,
                                        failed_cnt, sync_errors, op_name='import')


            try:
                if not skip_cardinalities:
                    self.after_import_hook()
            except Exception, ex:
                LOGGER.debug("After import hook failed. Error: " + str(ex))
                TaskMessage.objects.create_error(user, "Computing cardinalities"
                                                 " failed. Error: " + str(ex))
                self.update(updated_at=utc(now()), load_progress=100, sync_status=status)

            self.update(rows=self.data_coll.count(),
                        updated_at=utc(now()),
                        items_imported=total - failed_cnt,
                        sync_status=status,
                        load_progress=100)

            LOGGER.info('Loading data for %s finished, %d rows took: %s' % (
                self.name, self.data_coll.count(), time.time() - start))

    return SchemaBased

SchemaBased = GetSchemaBased()

# move to utils?
def get_query_by_dates(from_dt=None, to_dt=None):
    # if only one of from_dt or to_dt is passed, it is exception, so catch with XOR test
    if bool(from_dt) != bool(to_dt):
        raise Exception("Requires %r also. Only %r given" % (
            ('to_dt', 'from_dt') if from_dt else ('from_dt', 'to_dt')
        ))
    date_query = {}
    if from_dt:
        date_query['updated_at__gte'] = from_dt
        date_query['updated_at__lte'] = to_dt
    return date_query


class InstanceManagerFactory(object):

    __manager_cls__ = None

    def __get__(self, instance, cls):
        if instance is None:
            return None

        cached_attr_name = '_%s' % cls.__name__
        if not hasattr(instance, cached_attr_name):
            setattr(instance, cached_attr_name, self.__manager_cls__(instance))

        return getattr(instance, cached_attr_name)


class InstanceManager(object):
    def __init__(self, instance):
        self.instance = instance
