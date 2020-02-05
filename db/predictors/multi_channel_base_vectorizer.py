from abc import abstractmethod
from datetime import timedelta
from solariat_bottle.settings import LOGGER

from solariat.utils.timeslot import utc
from solariat_bottle.utils.id_encoder import unpack_event_id, pack_event_id
from solariat_bottle.db.events.event import Event
from solariat_bottle.db.post.web_clicks import WebClick
from solariat_bottle.db.post.chat import ChatPost
from solariat_bottle.db.post.faq_query import FAQQueryEvent
from solariat_bottle.db.predictors.abc_feature_extractor import BaseFeatureExtractor


class BaseEventVectorizer(BaseFeatureExtractor):

    lookback_window = 120 # Time, in seconds, for which we are looking back in the event sequence

    def vectorize(self, event, features_metadata=None):
        if isinstance(event, WebClick):
            return self.vectorize_web_click(event, features_metadata)
        if isinstance(event, ChatPost):
            return self.vectorize_chat_event(event, features_metadata)
        if isinstance(event, FAQQueryEvent):
            return self.vectorize_faq_query(event, features_metadata)
        if isinstance(event, Event):
            return self.vectorize_base_event(event, features_metadata)
        raise Exception("Cannot vectorize instance " + str(event))

    @abstractmethod
    def vectorize_web_click(self, event, features_metadata=None):
        return None

    @abstractmethod
    def vectorize_base_event(self, event, features_metadata=None):
        return None

    @abstractmethod
    def vectorize_faq_query(self, event, features_metadata=None):
        return None

    def construct_feature_space(self, event, features_metadata=None):
        actor_num, _ = unpack_event_id(event.id)

        id_lower_bound = pack_event_id(actor_num, utc(event._created - timedelta(seconds=self.lookback_window)))
        id_upper_bound = pack_event_id(actor_num, utc(event._created))
        event_sequence = Event.objects(id__lte=id_upper_bound, id__gte=id_lower_bound)[:]

        vector_space = []
        for event in event_sequence:
            event_vector = self.vectorize(event, features_metadata)
            if event_vector is not None:
                vector_space.append(event_vector)

        return vector_space

    def merge_event_sequence_vectors(self, vector_sequence, horizon_size=None):
        if horizon_size:
            return vector_sequence[-horizon_size:]
        else:
            return vector_sequence

