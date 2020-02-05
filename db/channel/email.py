"""
Contains any Genesys Chat specific functionality related to channels.
"""

# create_by_user method creates an instance of service channel
# user of type admin
from werkzeug.utils import cached_property

from solariat.db import fields
from solariat_bottle.db.post.email import UntrackedEmailPost
from solariat_bottle.db.channel.base import Channel, ServiceChannel
from solariat_bottle.db.group        import Group

from solariat_bottle.settings import AppException

EMAIL_TYPE_ID = 17

class EmailConfigurationException(AppException):
    pass

class EmailChannel(Channel):

    review_outbound = fields.BooleanField(default=False, db_field='ro')
    review_team     = fields.ReferenceField(Group, db_field='rg')

    @property
    def is_dispatchable(self):
        return True

    @property
    def platform(self):
        return 'Email'

class InboundEmailChannel(EmailChannel):

    def on_suspend(self):
        " run this handler when channel suspended "
        self.status = 'Suspended'
        self.update(set__status=self.status)

    def on_active(self):
        " run this handler when channel activated "
        self.status = 'Active'
        self.update(set__status=self.status)

    def get_service_channel(self):
        return EmailServiceChannel.objects.get(self.parent_channel)

    @property
    def platform(self):
        return 'Email'

class OutboundEmailChannel(EmailChannel):

    def on_suspend(self):
        " run this handler when channel suspended "
        self.status = 'Suspended'
        self.update(set__status=self.status)

    def on_active(self):
        " run this handler when channel activated "
        self.status = 'Active'
        self.update(set__status=self.status)

    def get_service_channel(self):
        return EmailServiceChannel.objects.get(self.parent_channel)

    @property
    def platform(self):
        return 'Email'

class EmailServiceChannel(EmailChannel, ServiceChannel):

    @property
    def platform(self):
        return 'Email'

    @property
    def type_id(self):
        return EMAIL_TYPE_ID

    @property
    def base_url(self):
        """return URL of Genesys Web Services """
        return self.base_url

    def find_direction(self, post):
        # For Chat channel all posts are actionable
        return 'direct'

    @property
    def InboundChannelClass(self):
        return InboundEmailChannel

    @property
    def OutboundChannelClass(self):
        return OutboundEmailChannel

    def list_outbound_channels(self, user):
        return OutboundEmailChannel.objects.find_by_user(user, account=self.account)



