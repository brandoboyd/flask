from .test_channel import ChannelCase
from solariat_bottle.db.channel.chat import ChatServiceChannel as CSC
from solariat_bottle.db.channel.base import Channel

class ChatChannelCase(ChannelCase):
    def setUp(self):
        ChannelCase.setUp(self)
        
    def test_chat_channel_creation(self):
        self.user.is_superuser = True
        self.user.account = None
        self.user.save()
        
        channel = CSC.objects.create_by_user(
            self.user, title='test chat service channel')
 
        self.assertEqual(
            Channel.objects.get_by_user(
                self.user, id=channel.id).__class__.__name__,
            'ChatServiceChannel')
 
        self.assertEqual(
            list(Channel.objects.find_by_user(
                    self.user, id=channel.id))[0].__class__.__name__,
            'ChatServiceChannel')

 
