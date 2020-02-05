"""
Contains any Genesys Chat specific functionality related to channels.
"""

# create_by_user method creates an instance of service channel
# user of type admin
from werkzeug.utils import cached_property

from solariat.db import fields
from solariat_bottle.db.channel.base import Channel, ServiceChannel
from solariat_bottle.db.group import Group
from solariat_bottle.settings import AppException, LOGGER

CHAT_TYPE_ID = 16


class ChatConfigurationException(AppException):
    pass


class ChatChannel(Channel):

    review_outbound = fields.BooleanField(default=False, db_field='ro')
    review_team     = fields.ReferenceField(Group, db_field='rg')

    @property
    def is_dispatchable(self):
        return True

    @property
    def platform(self):
        return 'Chat'


class InboundChatChannel(ChatChannel):

    def on_suspend(self):
        " run this handler when channel suspended "
        self.status = 'Suspended'
        self.update(set__status=self.status)

    def on_active(self):
        " run this handler when channel activated "
        self.status = 'Active'
        self.update(set__status=self.status)

    def get_service_channel(self):
        return ChatServiceChannel.objects.get(self.parent_channel)


class OutboundChatChannel(ChatChannel):

    def on_suspend(self):
        " run this handler when channel suspended "
        self.status = 'Suspended'
        self.update(set__status=self.status)

    def on_active(self):
        " run this handler when channel activated "
        self.status = 'Active'
        self.update(set__status=self.status)

    def get_service_channel(self):
        return ChatServiceChannel.objects.get(self.parent_channel)


class ChatServiceChannel(ChatChannel, ServiceChannel):

    @property
    def platform(self):
        return 'Chat'

    @property
    def type_id(self):
        return CHAT_TYPE_ID

    @property
    def base_url(self):
        """return URL of Genesys Web Services """
        return self.base_url

    def find_direction(self, post):
        # For Chat channel all posts are actionable
        return 'direct'

    def post_received(self, post):
        """
        Adds post to conversations.
        """
        from solariat_bottle.db.conversation import SessionBasedConversation
        assert set(post.channels).intersection([self.inbound, self.outbound])
        # We identify the conversation based on the session id.
        conversation = post.conversation
        if conversation:
            conversation.add_posts([post])
        else:
            conversation = SessionBasedConversation.objects.create_conversation(self, [post],
                                                                                session_id=post.session_id)

    def send_message(self, dry_run, creative, post, user):
        """
        TODO: implement
        """
        #check for the current supervisor's mode on the conversation
        # to which the post belongs
        # if mode == 'coach' send creative message to all agents on the chat session
        # if mode == 'bargein' send message to all parties
        # if mode == 'silent' don't send the message
        pass

    def on_active(self):
        """
        TODO:
        1 get list of users (Contact Center agents from GWS API)
        2 for the agents who have chat channel enabled and have status LoggedIn/Ready on chat channel
        add agent to the list of users
        3 for  each agent on the list start monitoring of chat sessions
        """
        self.status = 'Active'
        self.update(set__status='Active')

        self.inbound_channel.on_active()
        self.outbound_channel.on_active()

    def on_suspend(self):
        """
        TODO:
        for all currently monitored users send request stop monitoring to GWS API
        """
        self.status = 'Suspended'
        self.update(set__status='Suspended')
        #TODO: provide list of users as a parameter
        self.inbound_channel.on_suspend()
        self.outbound_channel.on_suspend()

    @property
    def InboundChannelClass(self):
        return InboundChatChannel

    @property
    def OutboundChannelClass(self):
        return OutboundChatChannel

    def list_outbound_channels(self, user):
        return OutboundChatChannel.objects.find_by_user(user, account=self.account)
