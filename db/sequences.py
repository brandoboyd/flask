# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from .auth   import AuthDocument
from solariat.db.fields import StringField, NumField


class NumberSequences(AuthDocument):
    name  = StringField(required=True, unique=True)
    _next = NumField(required=True)

    indexes = [ ("name", ) ]

    def __repr__(self):
        return '<%s: "%s", %s>' % (self.__class__.__name__, self.name, self._next)

    @classmethod
    def advance(cls, seq_name, first=1):
        """ Returns the next number in the <seq_name> sequence
            advancing it forward

            Example:
            num = NumberSequences.advance('channels')
        """
        doc = cls.objects.coll.find_and_modify(
            {'name':seq_name},
            {'$inc': {'_next': 1}},
            upsert=True,
            new=True)
        return doc['_next']


class AutoIncrementField(NumField):
    def __init__(self, counter_name, *args, **kwargs):
        self.counter_name = counter_name
        kwargs['default'] = self._advance
        super(AutoIncrementField, self).__init__(*args, **kwargs)

    def _advance(self):
        return NumberSequences.advance(self.counter_name)
