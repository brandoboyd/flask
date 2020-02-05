""" Landing Pages and related stuff """

from solariat.db.abstract import SonDocument
from .auth     import ArchivingAuthDocument, ArchivingAuthManager
from solariat.db import fields


class WeightedContentField(SonDocument):
    '''For landing pages
    '''
    name = fields.StringField()
    value = fields.StringField()
    weight = fields.NumField(default=1.0)

class LandingPageManager(ArchivingAuthManager):
    def remove(self, *args, **kw):
        if args:
            kw['id'] = args[0]
        query = self.doc_class.get_query(**kw)
        self.coll.update(query, {'$set': {'is_archived': True}},
                         multi=True)
        # rename unique url field
        query['is_archived'] = True
        self.coll.update(query, {'$rename': {'ul': 'r_ul'}},
                         multi=True)

class LandingPage(ArchivingAuthDocument):
    manager = LandingPageManager
    url = fields.StringField(required=True, unique=True, sparse=True, db_field='ul')
    display_field = fields.StringField(db_field='df')
    weighted_fields = fields.ListField(
        fields.EmbeddedDocumentField(WeightedContentField),
        db_field='wf')

    # indexes = [ ('url', ) ]

    def to_dict(self, fields2show=None):
        info = ArchivingAuthDocument.to_dict(self, fields2show)
        if not fields2show or 'weighted_fields' in fields2show:
            info['weighted_fields'] = [
                x.to_dict() for x in self.weighted_fields]
        return info
