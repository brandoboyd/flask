
from itertools import chain, repeat
from solariat.db import fields
from solariat_nlp.filter_cls.classifier import FilterClassifier


class ModelMixin(object):

    packed_clf = fields.BinaryField()  # WARNING: 2MB limit!
    counter    = fields.NumField(default=0)     # Use to track iterations

    configuration = fields.DictField()

    @property
    def classifier_class(self):
        "So we can easily plugin other classifier classes if we want."
        return None

    @property
    def clf(self):
        if not hasattr(self, '_clf') or not self._clf:
            kwargs = dict()
            if self.packed_clf:
                kwargs['model'] = self.packed_clf

            if self.configuration:
                kwargs.update(self.configuration)

            if hasattr(self, 'model_type'):
                kwargs['model_type'] = self.model_type
            self._clf = self.classifier_class(**kwargs)

        return self._clf

    def pack_model(self):
        # make sure we also save classifier state (pickled and zipped)
        #print 'save(): _clf=%r' % self._clf
        self.packed_clf = self.clf.packed_model
        self.counter += 1


class LocalModelsMixin(object):

    # packed_clf = fields.BinaryField()  # WARNING: 2MB limit!
    clf_map = fields.DictField()  
    counter = fields.NumField(default=0)     # Use to track iterations

    configuration = fields.DictField()

    @property
    def classifier_class(self):
        "So we can easily plugin other classifier classes if we want."
        return None

    @property
    def clf(self):
        if not hasattr(self, '_clf') or not self._clf:
            self._clf = self.classifier_class(predictor_model=self)
        return self._clf

    def delete(self, *args, **kwargs):
        from solariat_bottle.db.predictors.base_predictor import LocalModel
        LocalModel.objects.remove(predictor_model=self)

    def delete_local_models(self):
        from solariat_bottle.db.predictors.base_predictor import LocalModel
        LocalModel.objects.remove(predictor_model=self)


class ClassifierMixin(ModelMixin):

    @property
    def classifier_class(self):
        "So we can easily plugin other classifier classes if we want."
        return FilterClassifier

    @property
    def inclusion_threshold(self):
        return self.clf.HI_THRESHOLD

    @property
    def exclusion_threshold(self):
        return self.clf.LO_THRESHOLD

    def retrain(self, incremental=False):
        '''Force a full retrain'''
        clf = self.classifier_class()

        acc = [p.vector for p in self.accepted_items]
        rej = [p.vector for p in self.rejected_items]
        if not incremental:
            if acc or rej:
                X = tuple(chain(acc, rej))
                y = tuple(chain(repeat(1, len(acc)), repeat(0, len(rej))))
                clf.train(X, y)
        else:
            for entry in acc:
                clf.train([entry], [1])
            for entry in rej:
                clf.train([entry], [0])

        self._clf = clf
        self.pack_model()
        self.save()

    def _predict_fit(self, item):
        content = item['content'] if isinstance(item, dict) else item.content
        if not content:
            # No content at all
            return 0
        vector = self.make_post_vector(item)
        return self.clf.score(vector)

    def extract_features(self, item):
        ''' Return the list of features for the given item'''
        pv = self.make_post_vector(item)
        return self.clf.extract_features(pv)
