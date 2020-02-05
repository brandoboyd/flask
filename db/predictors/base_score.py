from solariat.utils.timeslot import now
from solariat.db import fields
from solariat_bottle.db.auth import AuthDocument


class BaseScore(AuthDocument):

    created = fields.DateTimeField(default=now)
    matching_engine = fields.ObjectIdField()
    model_id = fields.ObjectIdField(null=True)
    counter = fields.NumField(default=1)
    cumulative_latency = fields.NumField(required=True)

    indexes = [('matching_engine', 'created'), ]

    @property
    def latency(self):
        return 1.0 * self.cumulative_latency / (self.counter or 1)
