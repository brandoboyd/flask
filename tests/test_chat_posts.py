# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from ..db.account       import Account
from ..db.user_profiles.chat_profile import ChatProfile
from ..db.channel.chat  import ChatServiceChannel as CSC
from ..db.post.utils    import factory_by_user
from ..db.conversation  import Conversation

from .base import MainCase


class ChatPostCase(MainCase):

    def setUp(self):
        super(ChatPostCase, self).setUp()
        account = Account.objects.get_or_create(name='Test')
        self.user.account = account
        self.user.save()
        self.sc = CSC.objects.create_by_user(
            self.user,
            account = account,
            title = 'test chat service channel')

        self.inbound = self.sc.inbound_channel
        self.outbound = self.sc.outbound_channel
        self.sc.save()
        self.outbound.usernames = ['test']
        self.outbound.save()
        self.channel = self.inbound
        self.contact = ChatProfile.objects.create((), native_id='customer1')
        self.contact.save()
        self.support = ChatProfile.objects.create((), native_id='agent1')
        self.support.save()

    def fake_chat_url(self, id):
        return  "https://hpe-voicevm-77.genesyslab.com:8090/api/v2/chats/" + id

    def test_chat_post_creation(self):
        chat_session_id = '123345'
        url = self.fake_chat_url(chat_session_id)
        content = 'Hi, I need a laptop battery'
        post = factory_by_user(
            self.user,
            channel = self.inbound,
            content = content,
            url = url,
            user_profile = self.contact,
            extra_fields = {"chat": {"session_id": chat_session_id}}
        )
        self.assertEqual(post.content, content)

    def test_chat_conversation(self):
        chat_session_id = '123345'
        url = self.fake_chat_url(chat_session_id)
        client_post = factory_by_user(
            self.user,
            channel = self.inbound,
            content = 'Hi, I need a laptop battery',
            url = url,
            user_profile = self.contact,
            extra_fields = {"chat": {"session_id": chat_session_id}}
        )
        self.assertEqual(client_post.get_assignment(self.sc), "highlighted")
        brand_post = factory_by_user(
            self.user,
            channel = self.inbound,
            content = 'Hi, I need a laptop battery',
            url = url,
            user_profile = self.support,
            extra_fields = {"chat": {
                "session_id": chat_session_id,
                "in_reply_to_status_id": client_post.id}}
        )
        self.assertEqual(brand_post.get_assignment(self.sc), "highlighted")
        client_post.handle_reply(brand_post, [self.sc.inbound_channel])
        client_post.reload()
        self.assertEqual(client_post.get_assignment(self.sc), "replied")
        self.assertEqual(brand_post.parent_post_id, client_post.id)

        conversations = Conversation.objects.lookup_by_posts(self.sc, [client_post])
        self.assertEqual(len(conversations), 1)
        conversation = conversations[0]
        self.assertEqual(len(conversation.posts), 2)
        self.assertTrue(client_post.id in conversation.posts)
        self.assertTrue(brand_post.id in conversation.posts)
        self.assertEqual(chat_session_id, conversation.session_id, conversation)



    def test_post_special_case(self):
        content = """
        Customer: Hi, I need a laptop battery
        Brand: We willsend you new one
        Customer: It's urgent
        Brand: Ok, we'll send it to you today
        Customer: Thank you
        Brand: you're welcome
        Customer: Hi, I need a laptop battery
        Brand: We willsend you new one
        Customer: It's urgent
        Brand: Ok, we'll send it to you today
        Customer: Thank you
        Brand: you're welcome
        """*10
        chat_session_id = '123345'
        url = self.fake_chat_url(chat_session_id)
        post = factory_by_user(
            self.user,
            channel = self.inbound,
            content = content,
            url = url,
            # _created = parse_datetime( "2007-03-04T21:08:12" ),
            user_profile = self.contact,
            extra_fields = {"chat": {"session_id": chat_session_id}}
        )
        self.assertEqual(post.content, content)


