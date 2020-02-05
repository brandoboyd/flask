from solariat_bottle.tests.base import BaseCase
import unittest


class TestColumnTypes(BaseCase):

    @unittest.skip('Test shows we does not respect _id column type')
    def test_id_column_type_idempotent(self):
        from solariat.db.abstract import Document
        from solariat.db import fields
        from datetime import datetime
        from bson.objectid import ObjectId

        cls = type('TestType', (Document, ), {})
        self.assertTrue(isinstance(cls.fields['id'], fields.ObjectIdField),
                        'real_type: %s' % type(cls.fields['id']))
        obj = cls.objects.create(id=datetime.now())
        obj.reload()
        self.assertTrue(isinstance(obj.id, ObjectId), 'real model type: %s' % type(obj.id))
        doc = cls.objects.coll.find_one({'_id': obj.id})
        self.assertTrue(isinstance(doc['_id'], ObjectId), 'real mongo type: %s' % type(doc['_id']))
