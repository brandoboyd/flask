from abc import abstractmethod


class ABCFeatureExtractor(object):

    @abstractmethod
    def construct_feature_space(self, object, features_metadata=None):
        return {}

    @abstractmethod
    def check_preconditions(self, objects, features_metadata=None):
        return True


class BaseFeatureExtractor(ABCFeatureExtractor):

    def construct_feature_space(self, object, features_metadata=None):
        return str(object)

    def check_preconditions(self, object, features_metadata=None):
        return True
