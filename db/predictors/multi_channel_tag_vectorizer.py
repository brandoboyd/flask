import re

from solariat.db import fields
from solariat_bottle.db.predictors.multi_channel_base_vectorizer import BaseEventVectorizer
from solariat_bottle.db.post.web_clicks import WebClick
from solariat_bottle.db.post.chat import ChatPost
from solariat_bottle.db.post.faq_query import FAQQueryEvent


class BaseMetadataValidator(object):

    CHANNEL_NAME = 'base'
    valid_fields = []

    @classmethod
    def validate(cls, features_metadata):
        if cls.CHANNEL_NAME in features_metadata:
            for meta_key in features_metadata[cls.CHANNEL_NAME].keys():
                if meta_key not in cls.valid_fields:
                    raise fields.ValidationError("Unknown key '%s' in %s. Accepted fields are '%s'" %
                                                 (meta_key,
                                                  features_metadata[cls.CHANNEL_NAME].keys(),
                                                  cls.valid_fields))
        return True     # No click specific data


class WebClickValidator(BaseMetadataValidator):

    CHANNEL_NAME = 'web'
    KEY_URL_REGEX = 'urls_regex'
    KEY_ELEMENT_REGEX = 'elements_regex'

    valid_fields = (KEY_URL_REGEX, KEY_ELEMENT_REGEX)

    @staticmethod
    def regex_list(features_metadata):
        web_metadata = features_metadata.get(WebClickValidator.CHANNEL_NAME)
        if web_metadata:
            # Check for any url matches
            url_regexes = web_metadata.get(WebClickValidator.KEY_URL_REGEX)
            return url_regexes
        return []

    @staticmethod
    def get_url_matches(event, features_metadata):
        url_matches = []
        url_regexes = WebClickValidator.regex_list(features_metadata)
        if url_regexes:
            for url_regex in url_regexes:
                url_matches.extend(re.findall(url_regex, event.url))
        return url_matches

    @staticmethod
    def compute_features(click_event, features_metadata):
        feature_dict = {'content': click_event.url,
                        WebClickValidator.KEY_URL_REGEX: WebClickValidator.get_url_matches(click_event,
                                                                                           features_metadata),
                        WebClickValidator.KEY_ELEMENT_REGEX: []}
        return feature_dict

    @staticmethod
    def check_preconditions(event, features_metadata=None):
        if not isinstance(event, WebClick):
            return True
        url_regexes = WebClickValidator.regex_list(features_metadata)
        if url_regexes and not WebClickValidator.get_url_matches(event, features_metadata):
            return False
        return True


class ChatMessageValidator(BaseMetadataValidator):

    KEY_WATCHWORDS = 'watchwords'
    KEY_KEYWORDS = 'keywords'
    KEY_MATCHING_REGEX = 'matching_regex'
    CHANNEL_NAME = 'chat'

    valid_fields = (KEY_WATCHWORDS, KEY_KEYWORDS, KEY_MATCHING_REGEX)

    @staticmethod
    def keywords_list(features_metadata):
        chat_metadata = features_metadata.get(ChatMessageValidator.CHANNEL_NAME)
        if chat_metadata:
            # Check for any keyword matches
            keywords = chat_metadata.get(ChatMessageValidator.KEY_KEYWORDS, [])
            return keywords
        return []

    @staticmethod
    def get_keyword_matches(chat_event, features_metadata):
        matched_keywords = []
        keywords = ChatMessageValidator.keywords_list(features_metadata)
        if keywords:
            for keyword in keywords:
                if keyword in chat_event.plaintext_content:
                    matched_keywords.append(keyword)
        return matched_keywords

    @staticmethod
    def regex_list(features_metadata):
        chat_metadata = features_metadata.get(ChatMessageValidator.CHANNEL_NAME)
        if chat_metadata:
            # Check for any keyword matches
            regex = chat_metadata.get(ChatMessageValidator.KEY_MATCHING_REGEX, [])
            return regex
        return []

    @staticmethod
    def get_regex_matches(chat_event, features_metadata):
        regex_matches = []
        regexes = ChatMessageValidator.regex_list(features_metadata)
        if regexes:
            for regex in regexes:
                regex_matches.extend(re.findall(regex, chat_event.plaintext_content))
        return regex_matches

    @staticmethod
    def check_preconditions(event, features_metadata=None):
        if not isinstance(event, ChatPost):
            return True
        keywords = ChatMessageValidator.keywords_list(features_metadata)
        if keywords and not ChatMessageValidator.get_keyword_matches(event, features_metadata):
            return False
        matches = ChatMessageValidator.regex_list(features_metadata)
        if matches and not ChatMessageValidator.get_regex_matches(event, features_metadata):
            return False
        return True

    @staticmethod
    def compute_features(chat_event, features_metadata):
        feature_dict = {'content': chat_event.plaintext_content,
                        ChatMessageValidator.KEY_KEYWORDS: ChatMessageValidator.get_keyword_matches(chat_event,
                                                                                                    features_metadata),
                        ChatMessageValidator.KEY_WATCHWORDS: []}
        return feature_dict


class FAQQueryValidator(BaseMetadataValidator):

    KEY_MATCHING_REGEX = 'matching_regex'
    CHANNEL_NAME = 'faq'

    valid_fields = (KEY_MATCHING_REGEX, )

    @staticmethod
    def regex_list(features_metadata):
        faq_metadata = features_metadata.get(FAQQueryValidator.CHANNEL_NAME)
        if faq_metadata:
            # Check for any url matches
            faq_regexes = faq_metadata.get(FAQQueryValidator.KEY_MATCHING_REGEX)
            return faq_regexes
        return []

    @staticmethod
    def get_regex_matches(faq_query, features_metadata):
        matches = []
        regexes = FAQQueryValidator.regex_list(features_metadata)
        if regexes:
            for regex in regexes:
                match = re.search(regex, faq_query.query)
                if match:
                    matches.append(match.group())
        return matches

    @staticmethod
    def compute_features(faq_query, features_metadata):
        feature_dict = {'content': faq_query.query,
                        FAQQueryValidator.KEY_MATCHING_REGEX: FAQQueryValidator.get_regex_matches(faq_query,
                                                                                                  features_metadata)}
        return feature_dict

    @staticmethod
    def check_preconditions(event, features_metadata=None):
        if not isinstance(event, FAQQueryEvent):
            return True
        regexes = FAQQueryValidator.regex_list(features_metadata)
        if regexes and not FAQQueryValidator.get_regex_matches(event, features_metadata):
            return False
        return True


class FeatureMetadataBasedVectorizer(BaseEventVectorizer):
    """
    This vectorizer has specific platform specific metadata which it uses as guidance for constructing
    the feature space for each individual event.
    """
    def validate_metadata(self, features_metadata):
        WebClickValidator.validate(features_metadata)
        ChatMessageValidator.validate(features_metadata)

    def vectorize_web_click(self, event, features_metadata=None):
        return WebClickValidator.compute_features(event, features_metadata)

    def vectorize_chat_event(self, event, features_metadata=None):
        return ChatMessageValidator.compute_features(event, features_metadata)

    def vectorize_faq_query(self, event, features_metadata=None):
        return FAQQueryValidator.compute_features(event, features_metadata)

    def vectorize_base_event(self, event, features_metadata=None):
        return None

    def check_preconditions(self, event, features_metadata=None):
        return (FAQQueryValidator.check_preconditions(event, features_metadata) and
                WebClickValidator.check_preconditions(event, features_metadata) and
                ChatMessageValidator.check_preconditions(event, features_metadata))


class MultiChannelTagVectorizer(FeatureMetadataBasedVectorizer):
    """
    Overwrite default behaviour so in case we have some single event tags computed for any event in the
    sequence, we consider that as the feature for the multi-event tag.
    """

    def vectorize_web_click(self, event, features_metadata=None):
        base_vector = super(MultiChannelTagVectorizer, self).vectorize_web_click(event, features_metadata)
        if event.computed_single_tags:
            base_vector['tags'] = event.computed_single_tags
        return base_vector

    def vectorize_chat_event(self, event, features_metadata=None):
        base_vector = super(MultiChannelTagVectorizer, self).vectorize_chat_event(event, features_metadata)
        if event.computed_single_tags:
            base_vector['tags'] = event.computed_single_tags
        return base_vector

    def vectorize_faq_query(self, event, features_metadata=None):
        base_vector = super(MultiChannelTagVectorizer, self).vectorize_faq_query(event, features_metadata)
        if event.computed_single_tags:
            base_vector['tags'] = event.computed_single_tags
        return base_vector

    def merge_event_sequence_vectors(self, vector_sequence, horizon_size=None):
        full_sequence = []
        if horizon_size:
            sequence = vector_sequence[-horizon_size:]
        else:
            sequence = vector_sequence

        import itertools
        previous_event = []
        for event in sequence:
            current_event = []
            content = event.get('content')
            if content:
                current_event.append(content)
            current_event.extend(event.get('tags', []))
            current_event.extend(event.get(ChatMessageValidator.KEY_KEYWORDS, []))
            current_event.extend(event.get(ChatMessageValidator.KEY_WATCHWORDS, []))
            current_event.extend(event.get(WebClickValidator.KEY_URL_REGEX, []))
            current_event.extend(event.get(WebClickValidator.KEY_ELEMENT_REGEX, []))
            current_event.extend(event.get(WebClickValidator.KEY_URL_REGEX, []))
            current_event.extend(event.get(WebClickValidator.KEY_ELEMENT_REGEX, []))
            current_event.extend(event.get(FAQQueryValidator.KEY_MATCHING_REGEX, []))
            #full_sequence.extend(current_event)
            full_sequence.extend(list([str(a) + "__" + str(b) for (a, b) in itertools.product(previous_event,
                                                                                              current_event)]))
            previous_event = current_event
        return list(set(full_sequence))


class SingleEventTagVectorizer(FeatureMetadataBasedVectorizer):
    """
    Just a specific that is always restricted to one event.
    """
    def construct_feature_space(self, event, features_metadata=None):
        # Just overwrite base method to only handle one event at a time and not full event sequence
        vector_space = self.vectorize(event, features_metadata)
        return vector_space

