"Suite for testing various security issues"

from solariat_bottle.tests.base import RestCase
from solariat_bottle.db.auth import AuthError
from solariat_bottle.db.api_auth import AuthToken
from solariat_bottle.db.user import User
from solariat_bottle.db.post.base import Post
from solariat_bottle.db.roles import ADMIN


class SecTest(RestCase):

    def test_deletion(self):
        """ User with not staff / admin role cannot delete post """
        post = self._create_db_post("I need some foo")
        trudy = User.objects.create(email='trudy@solarist.com',
                                    password='1',
                                    account=self.user.account)
        self.channel.add_perm(trudy, to_save=True)
        posts = Post.objects.find_by_user(trudy, perm='r')
        self.assertEqual(posts.count(), 1)

        self.assertRaises(AuthError, posts[0].delete_by_user, trudy)

        self.auth_token = AuthToken.objects.create_from_user(trudy).digest
        self.do_delete('posts')
        self.assertEqual(posts.count(), 1)

        # Now set the role of staff to that user and try again
        trudy.user_roles = [ADMIN]
        trudy.save()
        # On version 2.0 still should not be possible
        resp = self.do_delete('posts', version='v2.0')
        self.assertEqual(posts.count(), 1)
        # On version 1.2 this should have been allowed
        self.auth_token = AuthToken.objects.create_from_user(trudy).digest
        self.do_delete('posts', version='v1.2')
        self.assertEqual(posts.count(), 0)