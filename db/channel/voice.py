from solariat_bottle.db.channel.chat import ChatServiceChannel, OutboundChatChannel, InboundChatChannel
from .base import ChannelManager, Channel
from solariat.db import fields


# class VoiceChannelManager(ChannelManager):

#     def create(self, **kw):
#         return super(VoiceChannelManager, self).create(**kw)


class InboundVoiceChannel(InboundChatChannel):

    @property
    def platform(self):
        return 'Voice'

    def get_service_channel(self):
        return VoiceServiceChannel.objects.get(self.parent_channel)


class OutboundVoiceChannel(OutboundChatChannel):

    @property
    def platform(self):
        return 'Voice'

    def get_service_channel(self):
        return VoiceServiceChannel.objects.get(self.parent_channel)


class VoiceServiceChannel(ChatServiceChannel):

    @property
    def InboundChannelClass(self):
        return InboundVoiceChannel

    @property
    def OutboundChannelClass(self):
        return OutboundVoiceChannel

    @property
    def platform(self):
        return 'Voice'

    @property
    def is_service(self):
        return True

    @property
    def is_inbound(self):
        return False
