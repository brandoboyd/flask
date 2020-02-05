# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from ..db.account       import Account
from ..db.user_profiles.user_profile import UserProfile
from ..db.channel.email import EmailServiceChannel as ESC
from ..db.post.chat     import parse_datetime
from ..db.post.utils    import factory_by_user
from ..db.conversation  import Conversation

from .base import MainCase


class EmailCase(MainCase):
    
    def setUp(self):
        super(EmailCase, self).setUp()
        account = Account.objects.get_or_create(name='Test')
        self.user.account = account
        self.user.save()
        self.sc = ESC.objects.create_by_user(
            self.user,
            account = account,
            title = 'test email service channel')
        
        self.inbound = self.sc.inbound_channel
        self.outbound = self.sc.outbound_channel
        self.sc.save()
        self.outbound.usernames = ['test']
        self.outbound.save()
        self.channel = self.inbound
        self.contact = UserProfile.objects.upsert('Email', dict(screen_name='John Doe'))
        self.support = UserProfile.objects.upsert('Email', dict(screen_name='support@enterprise.com'))
        self.client_email_data = {
            "subject":    "new laptop",
            "sender":     "client@acer.com",
            "cc":         "client_brother@acer.com",
            "recipients": "brand1@acer.com, brand2@acer.com",
            "body":       "Hey Acer, my laptop is broken. I need new one as soon as possible!",
            "created_at": "somedate",
        }
        self.brand_email_data = {
            "subject":    "RE: new laptop",
            "sender":     "brand1@acer.com",
            "cc":         "client_brother@acer.com",
            "recipients": "client@acer.com",
            "body":       "Hey Client, we'll ship you new laptop as soon as possible",
            "created_at": "somedate_later",
        }
    
    def test_email_creation(self):
        content    = 'Hi, I need a laptop battery'
        post = factory_by_user(
            self.user,
            channel = self.inbound,
            content = content,
            _created = parse_datetime( "2007-03-04T21:08:12" ),
            email_data = self.client_email_data,
            user_profile = self.contact,
        )
        self.assertEqual(post.content, content)
        self.assertTrue(post._email_data)

    def test_email_conversation(self):
        client_post = factory_by_user(
            self.user,
            channel = self.inbound,
            content = 'Hi, I need a laptop battery',
            _created = parse_datetime( "2007-03-04T21:08:12" ),
            user_profile = self.contact,
            email_data = self.client_email_data,
        )
        self.assertEqual(client_post.get_assignment(self.sc), "highlighted")
        self.assertTrue(client_post._email_data)
        self.brand_email_data.update({"in_reply_to_status_id": client_post.id})
        brand_post = factory_by_user(
            self.user,
            channel = self.inbound,
            content = "Hi, we'll ship you new battery as soon as possible",
            _created = parse_datetime( "2007-03-04T21:08:12" ),
            user_profile = self.support,
            email_data = self.brand_email_data,
        )
        self.assertEqual(brand_post.get_assignment(self.sc), "highlighted")
        client_post.handle_reply(brand_post, [self.sc.inbound_channel])
        client_post.reload()
        self.assertEqual(client_post.get_assignment(self.sc), "replied")
        self.assertEqual(brand_post.parent_post_id, client_post.id)

        conversations = Conversation.objects.lookup_by_posts(self.sc, [client_post])
        # import ipdb; ipdb.set_trace()
        self.assertEqual(len(conversations), 1)
        conversation = conversations[0]
        self.assertEqual(len(conversation.posts), 2)
        self.assertTrue(client_post.id in conversation.posts)
        self.assertTrue(brand_post.id in conversation.posts)
        

