from solariat_bottle.db.api_base_command import BaseAPICommand
from solariat.db.abstract import fields


class ChannelAPICommand(BaseAPICommand):
    """
    This is a base class for the db model REST commands
    """
    ACTIVATE = "activate"
    SUSPEND = "suspend"
    DELETE = "delete"

    AVAILABLE_COMMANDS = (ACTIVATE, SUSPEND, DELETE)

    channel_id = fields.StringField(db_field="ci",
                                    default=None)
    command = fields.StringField(db_field="cs",
                                 choices=AVAILABLE_COMMANDS)

