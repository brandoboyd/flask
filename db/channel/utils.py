'''
Any utility functions related strictly to channels.

'''
from solariat_bottle.db.channel.base     import ServiceChannel
from solariat_bottle.db.channel.twitter  import TwitterServiceChannel
from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.db.channel.chat     import ChatServiceChannel
from solariat_bottle.db.channel.email    import EmailServiceChannel
from solariat_bottle.db.channel.voice    import VoiceServiceChannel


SERVICE_CHANNEL_PLATFORM_MAP = {
    'Twitter':  TwitterServiceChannel,
    'Facebook': FacebookServiceChannel,
    'Chat':  ChatServiceChannel,
    'Email': EmailServiceChannel,
    'Voice': VoiceServiceChannel
    }


def get_platform_class(platform):
    return SERVICE_CHANNEL_PLATFORM_MAP.get(platform, ServiceChannel)

