""" Test limiting fields requested from Mongo """

from .base import BaseCase
from ..db.post.base import Post


class FieldsInQuerySet(BaseCase):

    def test_query(self):
        post = self._create_db_post('I need some foo')
        origin_fields = post.data.keys()
        self.assertTrue(len(origin_fields) > 30)

        _post = Post.objects.find(id=post.id).fields('content')[0]
        self.assertEqual(len(_post.data.keys()), 3) # _t, id and status
        self.assertEqual(_post.content, post.content)
