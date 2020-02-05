#!/usr/bin/env python2.7

import os
import json
import unittest
from solariat_bottle.tests.base import BaseCase

class PostsTestCase(BaseCase):

    def setUp(self):

        BaseCase.setUp(self)
        self.number_of_exceptions = 0
        _dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(_dir, 'datasift_invalid_chunkstring.json')) as fp:
            self.posts = [ json.loads(line)['content'] for line in fp ]

    def test_invalid_chunkstring(self):

        for post in self.posts:
            try:
                self._create_db_post(post)
            except ValueError:
                self.number_of_exceptions += 1
                print "POST:", post

        self.assertEqual(self.number_of_exceptions, 0)

if __name__ == '__main__':
    unittest.main()
