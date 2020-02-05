from solariat.db.abstract import Document
from solariat.db.abstract import fields
from solariat_bottle.db.user import User


class BaseAPICommand(Document):
    """
    This is a base class for the db model REST commands regarding
    administration or feedback.
    """
    allow_inheritance = True
    collection = "RESTCommands"

    user = fields.ReferenceField(User,
                                 unique=True,
                                 required=True,
                                 db_field='ur')
    timestamp = fields.DateTimeField(db_field='ts',
                                     required=True,
                                     default=None)
