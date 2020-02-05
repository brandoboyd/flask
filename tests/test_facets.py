from datetime import datetime
from nose.tools import eq_

from solariat.db import fields
from solariat.db.abstract import Document
from solariat_bottle import facets
from solariat.utils.timeslot import utc


class FooBar(Document):
    name = fields.StringField(db_field='nm')
    status = fields.StringField(db_field='stts', choices=['active', 'deactivated', 'suspended'])
    counter = fields.NumField(db_field='cntr')
    created_at = fields.DateTimeField(db_field='crtd')
    updated_at = fields.DateTimeField(db_field='updtd')
    active = fields.BooleanField(db_field='actv')
    stages = fields.ListField(fields.StringField(), db_field='stgs')


Query = {
        'name': ['Purchasing', 'Booking'],
        'status': ['deactivated', 'suspended'],
        'counter': {'$gte': 10, '$lt': 20},
        'created_at': ['2016-08-10', '2016-08-11'],
        'updated_at': ['2016-08-11', '2016-08-12'],
        'active': [True],
        'stages': ['stage1', 'stage2'],
}


class TestFacetUI:
    def test_create_facet(self):
        facet = facets.FacetUI.create_facet(FooBar.fields['created_at'])
        facet.validate(Query['created_at'])

    def test_create_facets(self):
        facet_dict = facets.FacetUI.create_facets(FooBar.fields)
        assert isinstance(facet_dict['name'], facets.StringFacet)
        assert isinstance(facet_dict['status'], facets.ChoiceFacet)
        assert isinstance(facet_dict['counter'], facets.NumFacet)
        assert isinstance(facet_dict['created_at'], facets.DateTimeFacet)
        assert isinstance(facet_dict['updated_at'], facets.DateTimeFacet)
        assert isinstance(facet_dict['active'], facets.CheckboxFacet)
        assert isinstance(facet_dict['stages'], facets.ListFacet)

    def test_validate_all(self):
        facets.FacetUI.validate_all(FooBar.fields, Query)

    def test_get_query(self):
        mongo_query = facets.FacetUI.get_query(FooBar.fields, Query)
        expected = {
                'nm': {'$in': ['Purchasing', 'Booking']},
                'stts': {'$in': ['deactivated', 'suspended']},
                'cntr': {'$gte': 10, '$lt': 20},
                'crtd': {'$gte': utc(datetime(2016, 8, 10)), '$lt': utc(datetime(2016, 8, 11))},
                'updtd': {'$gte': utc(datetime(2016, 8, 11)), '$lt': utc(datetime(2016, 8, 12))},
                'actv': {'$in': [True]},
                'stgs': {'$all': ['stage1', 'stage2']},
        }
        eq_(mongo_query, expected)


class TestStringFacet:
    def test_to_mongo(self):
        facet = facets.StringFacet(FooBar.fields['name'])
        eq_(facet.to_mongo(Query['name']), {'nm': {'$in': ['Purchasing', 'Booking']}})


class TestChoiceFacet:
    def test_to_mongo(self):
        facet = facets.ChoiceFacet(FooBar.fields['status'])
        eq_(facet.to_mongo(Query['status']), {'stts': {'$in': ['deactivated', 'suspended']}})
        eq_(facet.to_json(), {'name': 'status', 'type': 'string', 'values': ['active', 'deactivated', 'suspended']})


class TestNumFacet:
    def test_to_mongo(self):
        facet = facets.NumFacet(FooBar.fields['counter'])
        eq_(facet.to_mongo(Query['counter']), {'cntr': {'$gte': 10, '$lt': 20}})


class TestBoundedNumFacet:
    pass


class TestDateTimeFacet:
    def test_to_mongo(self):
        facet = facets.DateTimeFacet(FooBar.fields['created_at'])
        q = facet.to_mongo(Query['created_at'])
        expected = {'crtd': {
            '$gte': utc(datetime(2016, 8, 10)),
            '$lt': utc(datetime(2016, 8, 11))
        }}
        eq_(q, expected)


class TestDateRangeFacet:
    def test_to_mongo(self):
        query = {
                'from': '2016-08-15',
                'to': '2016-08-16',
        }
        facet = facets.DateRangeFacet(FooBar.fields['created_at'])
        eq_(facet.to_mongo(query), {'crtd': {'$gte': utc(datetime(2016, 8, 15)), '$lt': utc(datetime(2016, 8, 16))}})


class TestCheckboxFacet:
    def test_to_mongo(self):
        facet = facets.CheckboxFacet(FooBar.fields['active'])
        eq_(facet.to_mongo(Query['active']), {'actv': {'$in': [True]}})


class TestListFacet:
    def test_to_mongo(self):
        facet = facets.ListFacet(FooBar.fields['stages'])
        eq_(facet.to_mongo(Query['stages']), {'stgs': {'$all': ['stage1', 'stage2']}})
