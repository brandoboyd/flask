from __future__ import absolute_import
import json
from bson import json_util
from collections import defaultdict, Counter

from .base import SchemaBasedDataLoader
from solariat_bottle.settings import AppException
from solariat.db.abstract import (KEY_NAME, KEY_TYPE,
                                  TYPE_STRING, TYPE_INTEGER,
                                  TYPE_BOOLEAN, TYPE_DICT,
                                  TYPE_LIST, TYPE_TIMESTAMP)


class WrongInputFileFormat(AppException):
    http_code = 400


class JsonDataLoader(SchemaBasedDataLoader):
    '''This kind of data loader support raw data of multiple types and
       returns not only schema or data, but map with data_type as a key
    '''

    MAX_ITEMS_TO_DISCOVER = 100
    UNKNOWN_TYPE = TYPE_STRING
    TYPE_MAP = {
        float: TYPE_INTEGER,
        int: TYPE_INTEGER,
        long: TYPE_INTEGER,
        str: TYPE_STRING,
        unicode: TYPE_STRING,
        dict: TYPE_DICT,
        list: TYPE_LIST,
        bool: TYPE_BOOLEAN,
    }

    def __init__(self, json_file, data_type_getter):
        self.data_type_getter = data_type_getter
        self.json_file = json_file

    def iterator(self):
        def yield_data(data):
            if isinstance(data, dict):
                yield data
            if isinstance(data, list):
                for item in data:
                    yield item

        def read_stream():
            self.json_file.seek(0)
            try:
                data = json.load(self.json_file, object_hook=json_util.object_hook)
            except ValueError:
                self.json_file.seek(0)
                for line in self.json_file:
                    # support comments and newlines for object-per-line mode json input
                    if line in ('\n', '\r\n') or line.startswith('#') or line.startswith('//'):
                        continue
                    item = json.loads(line, object_hook=json_util.object_hook)
                    yield item
            else:
                yield data

        for data in read_stream():
            for item in yield_data(data):
                yield item

    def read_schema(self):
        processed_data = self.iterator()
        TYPE_SCHEMA_MAP = defaultdict(lambda: defaultdict(list))
        type_getter = self.data_type_getter
        for idx, data in enumerate(processed_data, start=1):
            if idx > self.MAX_ITEMS_TO_DISCOVER:
                break
            data_type = type_getter(data)
            schema_data = TYPE_SCHEMA_MAP[data_type]
            for field, val in data.iteritems():
                val_types = schema_data[field]
                if val is not None:
                    val_types.append(type(val))

        res = {}
        for data_type, schema_data in TYPE_SCHEMA_MAP.iteritems():
            schema = []
            res[data_type] = schema
            for field, val_types in schema_data.iteritems():
                if len(val_types):
                    ftype = self._get_field_type(Counter(val_types))
                    schema.append(self._generate_field(field, ftype))
                else:
                    # all values were None
                    schema.append(self._generate_field(field, self.UNKNOWN_TYPE))

        return res

    @staticmethod
    def _generate_field(field, _type):
        return {KEY_NAME: field, KEY_TYPE: _type}

    @classmethod
    def _get_field_type(cls, stat):
        if len(stat) == 1:
            _type, _ = next(stat.iteritems())
            return cls.TYPE_MAP[_type]

        if set(stat.keys()) <= {float, int, long}:
            return TYPE_INTEGER

        return cls.UNKNOWN_TYPE

    def load_data(self):
        processed_data = self.iterator()

        type_getter = self.data_type_getter
        for data in processed_data:
            data_type = type_getter(data)
            yield data_type, data
