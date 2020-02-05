from solariat.utils.timeslot import now
from solariat.db import fields
from solariat_bottle.db.auth import AuthDocument


class BaseFeedback(AuthDocument):

    created = fields.DateTimeField(default=now)
    action = fields.DictField()
    context = fields.DictField()
    matching_engine = fields.ObjectIdField()
    model_id = fields.ObjectIdField(null=True)
    reward = fields.NumField()

    # predicted score
    est_reward = fields.NumField()

    context_vector = fields.DictField()
    action_vector = fields.DictField()

    # scoring latency in ms
    score_runtime = fields.NumField()  # time taken in millisecond to compute score

    # scoring error %
    score_diff = fields.NumField()  # (reward - score) / reward

    indexes = [('matching_engine', 'created'), ]

