from solariat.db import fields
from solariat_bottle.db.auth import AuthDocument, AuthError
from solariat_bottle.db.channel.base import Channel, ChannelAuthDocument
from solariat_bottle.db.roles import AGENT
from solariat_bottle.tests.base import BaseCase


class Foo(AuthDocument):
    title = fields.StringField()


class Bar(ChannelAuthDocument):
    title = fields.StringField()

class AuthTest(BaseCase):
    def _test_auth_doc(self):
        user = self._create_db_user('user1@solariat.com', roles=[AGENT])
        foo = Foo.objects.create(title='test')
        foo.title='updated'
        self.assertRaises(AuthError,
                          foo.save_by_user,
                          user)
        foo.reload()
        self.assertEqual(foo.title, 'test')
        foo.add_perm(user)
        foo.title = 'updated'
        foo.save_by_user(user)
        foo.reload()
        self.assertEqual(foo.title, 'updated')
        self.assertEqual(
            Foo.objects.find_by_user(user).count(),
            1)

class ChannelAuthTest(BaseCase):
    def setUp(self):
        BaseCase.setUp(self)
        self.user = self._create_db_user('user1@solariat.com', roles=[AGENT])
        self.channel = Channel.objects.create(title='test')

    def _test_proxy_auth_deletion(self):
        bar = Bar.objects.create(title='bar', 
                                 channel=self.channel.id)
        self.assertEqual(
            Bar.objects.count(), 1)
        self.assertRaises(
            AuthError,
            bar.delete_by_user,
            self.user)
        self.channel.add_perm(self.user)
        bar.delete_by_user(self.user)
        self.assertEqual(
            Bar.objects.count(), 0)
        
    def test_proxy_auth_query(self):
        bar = Bar.objects.create(title='bar', 
                                 channel=self.channel.id)
        self.assertEqual(
            Bar.objects.find_by_user(self.user).count(),
            0)

        self.channel.add_perm(self.user)
        self.assertEqual(
            Bar.objects.find_by_user(self.user).count(),
            1)
