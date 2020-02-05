from datetime import datetime
from solariat.db import fields
from solariat.db.abstract import Document
from solariat_bottle.db.user import User
from solariat_bottle.db.auth import AuthDocument


class Funnel(AuthDocument):
    """
    """
    name = fields.StringField(required=True, unique=True)
    description = fields.StringField()
    journey_type = fields.ObjectIdField()
    steps = fields.ListField(fields.ObjectIdField(), required=True)
    owner = fields.ReferenceField(User)
    created = fields.DateTimeField(default=datetime.now)

    def to_dict(self, fields_to_show=None):
        rv = super(Funnel, self).to_dict()
        rv['steps'] = map(str, self.steps)
        return rv
