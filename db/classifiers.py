from solariat_nlp import extract_intentions

from solariat.db import fields
from solariat.db.abstract import Document
from solariat_bottle.db.auth import AuthDocument, AuthManager
from solariat_bottle.db.channel_filter import ClassifierMixin


TYPE_CONTENT_BASIC = 'content_basic'
TYPE_KEYWORD_AUGMENTED = 'keyword_augmented'


class FilteredOutException(Exception):
    pass


class BaseClassifierHelper(object):
    """ Base class for a vectorizer that transforms a inbound dictionary of the form
    {'content': content, 'speech_acts': []} into something the FIlterClassifier can work with.

    Also exposes a match function that decides if the sample should even go through prediction
    or is rejected right out the bat.
    """

    def make_item_vector(self, item, classifier):
        raise NotImplementedError("Should be implemented in subclasses")

    def match(self, item, classifer):
        raise NotImplementedError("Should be implemented in subclasses")


class BasicContentHelper(BaseClassifierHelper):

    def make_item_vector(self, item, classifier):
        return item

    def match(self, item, classifer):
        return True


class KeywordEnhancedHelper(BaseClassifierHelper):

    def make_item_vector(self, item, classifier):
        relevant_keys = ['keywords', 'watchwords', 'skip_keywords']
        metadata = dict({key: classifier.metadata[key] for key in relevant_keys if key in classifier.metadata})
        item.update(metadata)
        return item

    def match(self, item, classifier):
        """
        Try to match a item to a classifier based on a set of restrictions.
        """
        relevant_keys = ['keywords', 'watchwords', 'skip_keywords']
        metadata = dict({key: classifier.metadata[key] for key in relevant_keys if key in classifier.metadata})

        def _any_keyword_in(content, words):
            for word in words:
                if content.find(word) != -1:
                    return True
            return False

        keywords = [kwd.lower() for kwd in metadata.get('keywords', [])]
        skip_list = [kwd.lower() for kwd in metadata.get('skip_keywords', [])]
        keyword_constraint = not keywords or _any_keyword_in(item.lower(), keywords)
        skip_list_constraint = not skip_list or not _any_keyword_in(item.lower(), skip_list)
        return keyword_constraint and skip_list_constraint


POST_VECTORIZER_MAPPING = {TYPE_CONTENT_BASIC: BasicContentHelper,
                           TYPE_KEYWORD_AUGMENTED: KeywordEnhancedHelper}


class AuthTextChannelFilterManager(AuthManager):

    def create_by_user(self, user, name, type, **kwargs):

        return super(AuthTextChannelFilterManager, self).create_by_user(user,
                                                                        name=name,
                                                                        type=type,
                                                                        metadata=kwargs or {})


class AuthTextClassifier(AuthDocument, ClassifierMixin):

    ACCEPTED_TYPES = (TYPE_CONTENT_BASIC, TYPE_KEYWORD_AUGMENTED)

    acl = fields.ListField(fields.StringField(), db_field='acl')
    name = fields.StringField(db_field='nm', required=True)
    type = fields.StringField(db_field='tp', required=True, choices=ACCEPTED_TYPES)
    _reject_count = fields.NumField(db_field='rc', default=-1)
    _accept_count = fields.NumField(db_field='ac', default=-1)
    metadata = fields.DictField(db_field='md')

    manager = AuthTextChannelFilterManager

    top_rejected = None
    top_starred = None

    @property
    def helper(self):
        _helper_class_ = POST_VECTORIZER_MAPPING.get(self.type, None)
        if _helper_class_ is None:
            raise AuthTextClassifier.DoesNotExist("No helper found for type=%s" % self.type)
        _helper = _helper_class_()
        return _helper

    def reset_counters(self):
        self._reject_count = -1
        self._accept_count = -1
        self.save()

    @property
    def reject_count(self):
        if self._reject_count == -1:
            self._reject_count = len(self.rejected_items)
            self.save()
        return self._reject_count

    @property
    def accept_count(self):
        if self._accept_count == -1:
            self._accept_count = len(self.accepted_items)
            self.save()
        return self._accept_count

    @property
    def accepted_items(self):
        return TextChannelFilterItem.objects(channel_filter=self, filter_type='accepted')

    @property
    def rejected_items(self):
        return TextChannelFilterItem.objects(channel_filter=self, filter_type='rejected')

    def reset(self):
        """ Remove all related items """
        for item in TextChannelFilterItem.objects(channel_filter=self):
            item.delete()
        self.reset_counters()
        self.retrain()

    def predict(self, content):
        if not self.helper.match(content, self):
            return 0
        item = {'content': content,
                'speech_acts': extract_intentions(content)}
        return self._predict_fit(item)

    def batch_predict(self, content_list):
        result = []
        for content in content_list:
            if not self.helper.match(content, self):
                result.append({'text': content, 'score': 0})
            else:
                item = {'content': content,
                        'speech_acts': extract_intentions(content)}
                result.append({'text': content, 'score': self._predict_fit(item)})
        return result

    def handle_accept(self, content):
        # Call super class and get the vector
        item = {'content': content,
                'speech_acts': extract_intentions(content)}
        vec = self.make_post_vector(item)
        self.clf.train([vec], [1])
        TextChannelFilterItem.objects.create(content=content,
                                             channel_filter=self,
                                             filter_type='accepted',
                                             vector=vec)
        self.save()

    def handle_reject(self, content):
        item = {'content': content,
                'speech_acts': extract_intentions(content)}
        vec = self.make_post_vector(item)
        self.clf.train([vec], [0])
        TextChannelFilterItem.objects.create(content=content,
                                             channel_filter=self,
                                             filter_type='rejected',
                                             vector=vec)
        self.save()

    def make_post_vector(self, item):
        """ Convert the post to a useful dictionary of data that will allow
            all sorts of features to be applied. """
        return self.helper.make_item_vector(item, self)

    def save(self):
        self.packed_clf = self.clf.packed_model
        self.counter += 1
        super(AuthTextClassifier, self).save()


class TextChannelFilterItem(Document):
    content = fields.StringField(db_field='ct')
    channel_filter = fields.ReferenceField(AuthTextClassifier, db_field='cr')
    vector = fields.DictField(db_field='vr')
    filter_type = fields.StringField(choices=['rejected', 'accepted'],
                                     default='rejected',
                                     db_field='fe')