from solariat_bottle.db.schema_based import SchemaBased, ImproperStateError, apply_shema_type
from solariat_bottle.schema_data_loaders.base import SchemaBasedDataLoader
from solariat.exc.base import AppException
from solariat.utils.timeslot import utc, now
from solariat_bottle.settings import LOGGER
from solariat.db.abstract import KEY_NAME, KEY_TYPE, TYPE_STRING

import numpy
import pandas
import tempfile
import time


class CsvDataValidationError(AppException):
    pass


class CsvDataLoader(SchemaBasedDataLoader):

    TAB = '\t'
    COMMA = ','

    def __init__(self, csv_file, sep=None):
        super(CsvDataLoader, self).__init__()
        self.sep = sep
        self.csv_file = csv_file

    COL_SEPARATOR = '\t'
    MAX_ANALYSIS_LINES = 75
    LOAD_CHUNK_SIZE = 5000

    def read_schema(self):
        from solariat_bottle.utils.predictor_events import translate_column, get_type

        analysis_temp_file = tempfile.TemporaryFile('r+')
        headers = self.csv_file.readline()
        if not headers:
            raise CsvDataValidationError('Input file is empty')
        analysis_temp_file.write(headers)

        for idx, line_data in enumerate(self.csv_file.readlines(), start=1):
            analysis_temp_file.write(line_data)
            if idx == self.MAX_ANALYSIS_LINES:
                break

        analysis_temp_file.seek(0)
        schema_json = []
        try:
            dataframe = pandas.read_csv(analysis_temp_file, sep=self.sep)
        except Exception as ex:
            LOGGER.error('Cannot parse file:', exc_info=True)
            raise CsvDataValidationError('Cannot parse file %s' % str(ex))

        for col in dataframe.columns:
            schema_entry = dict(name=translate_column(col),
                                type=get_type(dataframe[col].dtype, dataframe[col].values))
            schema_json.append(schema_entry)

        return schema_json

    def load_data(self):
        from solariat_bottle.utils.predictor_events import translate_column

        self.csv_file.seek(0)
        # TODO: commented to simplify difference between csv & json data processing,
        # and this makes no sense, if someone load ALL data and then apply discovered
        # schema, he can loose some data anyway.
        # dataframe = pandas.read_csv(self.csv_file, dtype=str, sep=self.sep)

        # TODO: add chunksize=self.LOAD_CHUNK_SIZE
        dataframe = pandas.read_csv(self.csv_file, sep=self.sep)

        for idx, (_, row_data) in enumerate(dataframe.iterrows(), start=1):
            mongo_data = {}
            for _col_name, col_value in row_data.iteritems():
                col_name = translate_column(_col_name)
                if type(col_value) in (str, unicode) or not numpy.isnan(col_value):
                    mongo_data[col_name] = col_value
            yield mongo_data

    def total(self):
        rows = -1  # header
        self.csv_file.seek(0)
        for _ in self.csv_file.readlines():
            rows += 1
        return rows

