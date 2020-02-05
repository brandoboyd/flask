from solariat.db.abstract import Document, Manager
from solariat.db import fields


class TwitterRateLimitManager(Manager):
    pass


class TwitterRateLimit(Document):
    manager = TwitterRateLimitManager

    id = fields.StringField(db_field='_id')
    remaining = fields.NumField()
    limit = fields.NumField()
    reset = fields.NumField()
    delay = fields.NumField()

    def is_manual(self):
        if self.delay is not None:
            return True
        return False
