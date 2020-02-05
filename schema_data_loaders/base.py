from solariat_bottle.settings import AppException


class SchemaBasedDataLoader(object):

    def read_schema(self):
        raise NotImplementedError()

    def load_data(self):
        raise NotImplementedError()

    def total(self):
        raise NotImplementedError()


class WrongFileExtension(AppException):
    pass


class SchemaProvidedDataLoader(SchemaBasedDataLoader):

    def __init__(self, schema):
        self.schema = schema

    def read_schema(self):
        return self.schema

    def load_data(self):
        return []

    def total(self):
        return 0
