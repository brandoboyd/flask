from solariat_bottle.db.api_base_command import BaseAPICommand
from solariat.db.abstract import fields


class FeedbackAPICommand(BaseAPICommand):
    """
    This is a base class for the db model REST commands
    """
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ACCEPT_POST = "accept"
    REJECT_POST = "reject"

    AVAILABLE_COMMANDS = (ADD_TAG, REMOVE_TAG, ACCEPT_POST, REJECT_POST)

    channel_id = fields.StringField(db_field="sti",
                                    default=None)
    post_id = fields.StringField(db_field="pi",
                                 default=None)
    command = fields.StringField(db_field="cs",
                                 choices=AVAILABLE_COMMANDS)


