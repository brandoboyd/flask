from solariat.db import fields
from solariat_bottle.db.auth import AuthDocument


class Action(AuthDocument):

    name = fields.StringField()
    tags = fields.ListField(fields.ObjectIdField())
    channels = fields.ListField(fields.ObjectIdField())
    account_id = fields.ObjectIdField()
    type = fields.StringField()

    def to_dict(self, fields_to_show=None):
        return dict(id=str(self.id),
                    account_id=str(self.account_id),
                    name=str(self.name))