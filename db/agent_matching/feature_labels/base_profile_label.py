from solariat.db import fields

from solariat_bottle.settings import LOGGER
from solariat_bottle.db.auth import AuthDocument
from solariat_bottle.db.channel_filter import ClassifierMixin
from solariat_bottle.db.sequences import NumberSequences


class BaseProfileLabel(AuthDocument, ClassifierMixin):
    allow_inheritance = True
    collection = 'ProfileLabel'

    account_id = fields.ObjectIdField()
    display_name = fields.StringField()
    _feature_index = fields.NumField()

    @property
    def feature_index(self):
        if self._feature_index is None:
            self._feature_index = NumberSequences.advance(str(self.account_id) + '__' + self.__class__.__name__)
            self.save()
        return self._feature_index

    @classmethod
    def get_match(cls, profile):
        matches = []
        for label in cls.objects(account_id=profile.account_id):
            if label.match(profile):
                matches.append(label)
        if not matches:
            LOGGER.warning("Found no match for profile %s and class %s" % (profile, cls))
            return None
        if len(matches) > 1:
            LOGGER.warning("Found more than one match for profile %s and class %s" % (profile, cls))
        return matches[0]

    def save(self):
        self.packed_clf = self.clf.packed_model
        super(BaseProfileLabel, self).save()

    def make_profile_vector(self, profile):
        return { "content": profile.assigned_labels + [profile.location] + [str(profile.age)]}

    def match(self, profile):
        if self.id in profile.assigned_labels:
            return True
        if self.clf.score(self.make_profile_vector(profile)) > self.inclusion_threshold:
            return True
        return False

    def accept(self, profile):
        self.clf.train([self.make_profile_vector(profile)], [1])

    def reject(self, profile):
        self.clf.train([self.make_profile_vector(profile)], [0])

