# coding=utf-8

import unittest

from .base import BaseCase

class HashUtilsCase(BaseCase):

    @unittest.skip('we know of some collisions')
    def test_string_hashing(self):
        from solariat_bottle.utils.hash import mhash
        asciis = 'Asdfghjjkl;'
        self.assertTrue(1 < mhash(asciis) < 2 ** 32)
        unicodes = u'Фываолдж'
        self.assertTrue(mhash(unicodes) < 2 ** 32)
        xs = 'Фыва'
        self.assertTrue(1 < mhash(xs) < 2 ** 32)
        xsd = 'Фываd'.decode('utf-8')
        self.assertTrue(1 < mhash(xsd) < 2 ** 32)

        test_phrase = 'jumps over the lazy dog'
        test_phrase_hash = 2515788540
        self.assertEqual(mhash(test_phrase), test_phrase_hash)
