from abc import abstractmethod

from solariat.db import fields
from solariat_bottle.db.auth import AuthDocument
from solariat_bottle.db.channel_filter import ClassifierMixin

from solariat_bottle.db.predictors.abc_feature_extractor import BaseFeatureExtractor


class ABCPredictor(AuthDocument, ClassifierMixin):

    allow_inheritance = True
    collection = 'ABCPredictor'
    precondition = fields.StringField()     # Hold the precondition as string in a grammar
    acceptance_rule = fields.StringField()  # Hold any acceptance rule
    is_dirty = fields.BooleanField()
    features_metadata = fields.DictField()  # Any hints the classifier can use will be stored as a JSON here

    feature_extractor = BaseFeatureExtractor()

    def get_features(self, object):
        return self.feature_extractor.construct_feature_space(object, self.features_metadata)

    def save(self):
        self.packed_clf = self.clf.packed_model
        super(ABCPredictor, self).save()

    def match(self, object):
        if self.score(object) > self.inclusion_threshold:
            return True
        return False

    def score(self, object):
        if not self.check_preconditions(object):
            return 0
        if self.rule_based_match(object):
            return 1
        return self.clf.score(self.get_features(object))

    def accept(self, object):
        features = self.get_features(object)
        self.clf.train([features], [1])
        self.is_dirty = True
        self.save()

    def reject(self, object):
        self.clf.train([self.get_features(object)], [0])
        self.is_dirty = True
        self.save()

    @abstractmethod
    def check_preconditions(self, object):
        return self.feature_extractor.check_preconditions(object, self.features_metadata)

    @abstractmethod
    def rule_based_match(self, object):
        pass


class ABCMultiClassPredictor(AuthDocument):

    collection = 'ABCMultiPreditor'

    abc_predictors = fields.ListField(fields.ObjectIdField())   # Just a grouping of binary predictors
    inclusion_threshold = fields.NumField(default=0.25)
    is_dirty = fields.BooleanField()

    __classes = None

    @property
    def classes(self):
        if not self.__classes:
            options = [ABCPredictor.objects.get(o_id) for o_id in self.abc_predictors]
            self.__classes = options
        return self.__classes

    def to_dict(self, fields_to_show=None):
        base_dict = super(ABCMultiClassPredictor, self).to_dict(fields_to_show=fields_to_show)
        base_dict['classes'] = [seg.to_dict() for seg in self.classes]
        return base_dict

    def score(self, customer_profile):
        scores = []
        for option in self.classes:
            scores.append((option.display_name, option.score(customer_profile)))
        return scores

    def match(self, customer_profile):
        max_score = 0
        best_option = None
        for option in self.classes:
            option_score = option.score(customer_profile)
            if option_score > max_score:
                best_option = option
                max_score = option_score
        if max_score > self.inclusion_threshold:
            return True, best_option
        return False, None

    def accept(self, customer_profile, accepted_option):
        for option in self.classes:
            if option.id == accepted_option.id:
                option.accept(customer_profile)
            else:
                option.reject(customer_profile)
        self.is_dirty = True
        self.save()

    def reject(self, customer_profile, rejected_option):
        rejected_option.reject(customer_profile)
        self.is_dirty = True
        self.save()
