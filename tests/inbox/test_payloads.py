#!/usr/bin/env python2.7

import random
import unittest

from solariat_bottle.tests.base import MainCase

@unittest.skip("Matchables are depricated now")
class MatchableTestCase(MainCase):

    def create(self, intention_topics = None):
        " create matchable "
        
        post_doc = {
            'url': self.url,
            'creative': 'Your text here',
            'intention_types': ['Asks for Something',
                                'States a Need / Want'],
            'channels': [self.channel_id]
        }

        if intention_topics:
            post_doc['intention_topics'] = intention_topics

        return self.do_post('matchables', version='v1.2', **post_doc)

    def test_create(self):
        " correct creation should return json with ok = True and UUID "

        responseObj = self.create()
        responseObj = self.create(intention_topics=['laptop', 'stickers'])
        self.assertEqual(responseObj['ok'], True)
        self.assertTrue(self.channel_id in responseObj['item']['channels'])
        self.assertEqual(set(responseObj['item']['intention_topics']), 
                         set([u'laptop', u'sticker', u'stickers']))
        self.assertTrue(responseObj['item']['is_dispatchable'])
        
    def test_dispatchable(self):
        pl = Payload.objects.create(
            intention_topics=['laptop', 'stickers'])
        self.assertTrue(pl['is_dispatchable'])
        
    def test_get_specific(self):
        " get specific matchable "

        pl_count = 10
        for i in xrange(pl_count):
            responseObj = self.create()

        pl_id = responseObj['item']['id']
        responseObj = self.do_get('matchables/%s' % pl_id, version='v1.2')
        self.assertEqual(responseObj['ok'], True)
        self.assertTrue(responseObj.has_key('item'))

    def test_get_all(self):
        " get all matchable "

        pl_count = 10
        for i in xrange(pl_count):
            responseObj = self.create()

        responseObj = self.do_get('matchables', version='v1.2')
        self.assertEqual(responseObj['ok'], True)
        self.assertTrue(responseObj.has_key('list'))
        self.assertEqual(len(responseObj['list']), pl_count)

    def test_delete(self):
        " delete specific matchable "

        pl_count = 10
        for i in xrange(pl_count):
            responseObj = self.create()

        pl_id = responseObj['item']['id']
        
        responseObj = self.do_delete('matchables/%s' % pl_id, version='v1.2')
        self.assertEqual(responseObj['ok'], True)

    def test_delete_nonuser(self):
        " delete matchable without user "

        matchableObj = self.create()
        m = Matchable.objects.find_one(id=matchableObj['item']['id'])
        m.delete()
        self.assertEqual(
            Matchable.objects.get(id=m.id, is_archived=True).id, m.id)

    def test_archived(self):
        " test archiving capabilities "

        archived = []

        n = random.randint(3, 6)
        for i in xrange(n):
            responseObj = self.create()
            archived.append(responseObj['item']['id'])
            self.do_delete('matchables/%s' % responseObj['item']['id'], version='v1.2')

        self.create()
        self.assertEqual(Matchable.objects.count(), 1)
        self.assertEqual(Matchable.objects.coll.count(), n + 1)

        pl_archived = random.choice(archived)
        self.assertEqual(
                    str(Matchable.objects.get(id=pl_archived, is_archived=True).id),
                    pl_archived)
        self.assertRaises(Matchable.DoesNotExist, 
                          Matchable.objects.get, 
                          id=pl_archived)

if __name__ == '__main__':
    unittest.main()
