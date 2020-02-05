""" Super users must see any object in thy system """

from .base import BaseCase
from ..db.user import User
from ..db.channel.base import Channel


class RootPermCase(BaseCase):

    def test_superuser_perms(self):
        root = User.objects.create(email='root@solariat.com',
                                   password='1',
                                   is_superuser=True)
        self.assertTrue(root.is_superuser)
        self.assertTrue(self.channel.can_view(root))
        self.assertTrue(self.channel.can_edit(root))
        self.assertEqual(Channel.objects.find_by_user(root).count(), 1)

