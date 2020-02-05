# -*- coding: utf-8 -*-
"""
These tests are for solariat_bottle.db.matchable
"""
import unittest

from solariat_bottle.tests.base import UICase

@unittest.skip("Matchables are depricated")
class TestMatchable(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()
        pass

    def test_unicode(self):
        """Tests creative in unicode
        """
        # create matchable in Spanish
        matchable_es = self._create_db_matchable(
            u'Por favor, intente éste', _lang_code='es')
        self.assertEqual(matchable_es.language, 'es')
        pass

    def test_two_languages(self):
        """Tests case when posts and matchables are present in two languages
        """
        # English
        # create matchable in English
        matchable_en = self._create_db_matchable('You should try our new laptop')
        # create a post in English
        matchable_es = self._create_db_matchable(
            'Usted debe tratar de nuestro nuevo ordenador portatil', _lang_code='es')
        print 'matchable language=', matchable_es.language
        post_en = self._create_db_post('I need a laptop bag', demand_matchables=True)
        post_es = self._create_db_post(
            'Necesito una bolsa de ordenador portatil',
            demand_matchables=True, lang='auto')
        # each post has only one matchable
        self.assertEqual(len(post_en.get_matches()), 1)
        self.assertEqual(len(post_es.get_matches()), 1)
        # make sure that two languages match
        response_en = Response.objects.upsert_from_post(post_en)
        self.assertEqual(response_en.matchable.id, matchable_en.id)
        response_es = Response.objects.upsert_from_post(post_es)
        self.assertEqual(response_es.matchable.id, matchable_es.id)
