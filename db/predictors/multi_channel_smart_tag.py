import re

from solariat_nlp.filter_cls.classifier import MultiEventFilterClassifier
from solariat.db import fields
from solariat.db.abstract import Manager
from solariat.utils.timeslot import now

from solariat_bottle.settings import LOGGER
from solariat_bottle.db.events.event import Event
from solariat_bottle.db.predictors.abc_predictor import ABCPredictor
from solariat_bottle.db.predictors.multi_channel_tag_vectorizer import MultiChannelTagVectorizer
from solariat_bottle.db.predictors.multi_channel_tag_vectorizer import SingleEventTagVectorizer, ChatMessageValidator
from solariat_bottle.db.post.base import Post
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.post.web_clicks import WebClick
from solariat_bottle.db.post.chat import ChatPost


class EventTagManager(Manager):

    def create_by_user(self, user, **kw):
        assert str(kw.get('account_id')) in [str(x) for x in user.accounts], '%s not creator user account %s.' % (
            str(kw.get('account_id')), str(user.accounts)
        )
        # assert str(kw.get('account_id')) == str(user.account.id), '%s not creator user account %s.' % (
        #     str(kw.get('account_id')), str(user.account.id)
        # )
        if 'created' not in kw:
            kw['created'] = now()
        self.doc_class.feature_extractor.validate_metadata(kw.get('features_metadata', {}))
        intention_tag = super(EventTagManager, self).create(**kw)
        return intention_tag


class EventTag(ABCPredictor):

    indexes = [('account_id', 'is_multi', ), ]

    display_name = fields.StringField()
    account_id = fields.ObjectIdField()
    status = fields.StringField(default="Active")
    description = fields.StringField()
    created = fields.DateTimeField()
    channels = fields.ListField(fields.ObjectIdField())

    manager = EventTagManager

    default_threshold = 0.49

    @property
    def inclusion_threshold(self):
        return self.default_threshold

    def save(self):
        self.packed_clf = self.clf.packed_model
        super(EventTag, self).save()

    def match(self, event):
        assert isinstance(event, Event), "EventTag expects Event objects"
        if self.score(event) > self.inclusion_threshold:
            return True
        return False

    def score(self, event):
        assert isinstance(event, Event), "EventTag expects Event objects"
        return super(EventTag, self).score(event)

    def accept(self, event):
        assert isinstance(event, Event), "EventTag expects Event objects"
        return super(EventTag, self).accept(event)

    def reject(self, event):
        assert isinstance(event, Event), "EventTag expects Event objects"
        return super(EventTag, self).reject(event)

    def check_preconditions(self, event):
        if self.precondition:
            return eval(self.precondition)
        return self.feature_extractor.check_preconditions(event, self.features_metadata)

    def rule_based_match(self, event):
        if self.acceptance_rule:
            return eval(self.acceptance_rule)
        return False

    def to_dict(self, fields_to_show=None):
        result_dict = super(EventTag, self).to_dict()
        result_dict.pop('counter')
        result_dict.pop('packed_clf')
        result_dict['channels'] = [str(c) for c in result_dict['channels']]
        return result_dict


class MultiEventTag(EventTag):

    feature_extractor = MultiChannelTagVectorizer()

    event_lookup_horizon = fields.NumField(default=5)

    @property
    def classifier_class(self):
        "So we can easily plugin other classifier classes if we want."
        return MultiEventFilterClassifier

    def get_features(self, last_event):
        full_vector = self.feature_extractor.construct_feature_space(last_event, self.features_metadata)
        return self.feature_extractor.merge_event_sequence_vectors(full_vector, self.event_lookup_horizon)


class SingleEventTag(EventTag):

    feature_extractor = SingleEventTagVectorizer()

    def get_platform(self):
        # This is only for UI side to default at which platform we're gonna default
        platforms = []
        for channel in self.channels:
            platforms.append(Channel.objects.get(channel).platform)
        return platforms[0]

    def to_dict(self, fields_to_show=None):
        base_dict = super(SingleEventTag, self).to_dict(fields_to_show)
        base_dict['platform'] = self.get_platform()
        return base_dict


class RegexBasedAlerts(SingleEventTag):

    @property
    def inclusion_threshold(self):
        return 0.49    # Match as default if regex pass

    def score(self, object):
        if not self.check_preconditions(object):
            return 0
        if self.rule_based_match(object):
            return 1
        return self.clf.score(self.get_features(object))

    def get_regex_matches(self):
        if ChatMessageValidator.CHANNEL_NAME in self.features_metadata:
            metadata = self.features_metadata.get(ChatMessageValidator.CHANNEL_NAME, {})
            if ChatMessageValidator.KEY_MATCHING_REGEX in metadata:
                return metadata[ChatMessageValidator.KEY_MATCHING_REGEX]
        return []

    def check_preconditions(self, event):
        if isinstance(event, Post) or hasattr(event, 'plaintext_content'):
            for regex in self.get_regex_matches():
                if re.search(regex, event.plaintext_content):
                    return True
        return False
