from solariat.db import fields


class UserProfileIdField(fields.ObjectIdField):
    """Can be either of DBRef, ObjectId, String"""
    def to_mongo(self, value):
        if value is None:
            return None
        if isinstance(value, basestring) and value.rfind(':') > -1:
            return value
        return super(UserProfileIdField, self).to_mongo(value)

    def to_python(self, value):
        if isinstance(value, basestring) and value.rfind(':') > -1:
            return value
        return super(UserProfileIdField, self).to_mongo(value)