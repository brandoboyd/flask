
from datetime import datetime as dt

from solariat.exc.base import AppException
from solariat.db.abstract import SonDocument
from solariat.db import fields
from solariat.utils.timeslot import datetime_to_timestamp_ms

from solariat_bottle.settings import LOGGER
from solariat_bottle.db.mixins import LocalModelsMixin
from solariat_bottle.db.predictors.models.base import PredictorModel

from solariat_nlp.bandit.features import *
from solariat_nlp.bandit.feature_vector import get_feature_vector_cls
from solariat_nlp.bandit.linucb import ACTION_ID, KEY_DATA


class UnexpectedActionError(AppException):
    pass


class ModelState(SonDocument):

    CYCLE_NEW = 'NEW'
    CYCLE_TRAINED = 'TRAINED'
    CYCLE_LOCKED = 'LOCKED'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'

    state = fields.StringField(db_field='ss', choices=(CYCLE_NEW, CYCLE_TRAINED, CYCLE_LOCKED),
                               default=CYCLE_NEW)
    status = fields.StringField(db_field='st', choices=(STATUS_ACTIVE, STATUS_INACTIVE),
                                default=STATUS_INACTIVE)

    protocol = [
        ((STATUS_INACTIVE, CYCLE_NEW), 'train', (STATUS_INACTIVE, CYCLE_TRAINED)),
        ((STATUS_INACTIVE, CYCLE_TRAINED), 'train', (STATUS_INACTIVE, CYCLE_TRAINED)),

        ((STATUS_INACTIVE, CYCLE_TRAINED), 'activate', (STATUS_ACTIVE, CYCLE_LOCKED)),
        ((STATUS_ACTIVE, CYCLE_LOCKED), 'deactivate', (STATUS_INACTIVE, CYCLE_LOCKED)),
        ((STATUS_INACTIVE, CYCLE_LOCKED), 'activate', (STATUS_ACTIVE, CYCLE_LOCKED)),

        ((STATUS_ACTIVE, CYCLE_LOCKED), 'copy', (STATUS_ACTIVE, CYCLE_LOCKED)),
    ]

    @classmethod
    def initial(cls):
        return cls(status=cls.STATUS_INACTIVE, state=cls.CYCLE_NEW)

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    @property
    def is_locked(self):
        return self.state == self.CYCLE_LOCKED

    @property
    def actions_available(self):
        return {action: to_state
                for (from_state, action, to_state) in self.protocol
                if from_state == (self.status, self.state)}

    def change(self, action):
        actions = self.actions_available
        if action not in actions:
            raise UnexpectedActionError(action)

        next_status, next_state = actions[action]
        return self.__class__(status=next_status, state=next_state)

    def try_change(self, action):
        try:
            return self.change(action)
        except UnexpectedActionError:
            return None


class LinUCBPredictorModel(PredictorModel, LocalModelsMixin):

    TYPE_RANGE = NumericRange.__name__
    TYPE_LABEL = Label.__name__
    TYPE_LOOKUP = Lookup.__name__

    state = fields.EmbeddedDocumentField(ModelState)
    model_type = fields.StringField()
    was_active = fields.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        if 'state' not in kwargs:
            kwargs['state'] = ModelState.initial()
        super(PredictorModel, self).__init__(*args, **kwargs)

    def score(self, filtered_context, filtered_actions):
        return self.clf.score(filtered_context, filtered_actions)

    def reset_performance_stats(self):
        pass

    @property
    def is_active(self):
        return self.state.is_active

    @property
    def is_locked(self):
        return self.state.is_locked

    def vectorize_action(self, action_json):
        # So far we don't have anything except skills in current version.
        # Check for age and sex just in case
        data_vector = {}
        for action_key in self.action_features:
            if action_key in action_json:
                data_vector[action_key] = action_json[action_key]
        return {ACTION_ID: action_json[ACTION_ID],
                KEY_DATA: data_vector}

    def vectorize_context(self, context_json):
        base_vector = {}
        for context_key in self.context_features:
            if context_key in context_json:
                base_vector[context_key] = context_json[context_key]
        return base_vector

    @property
    def reward(self):
        if 'reward' in self.configuration:
            return self.configuration['reward']
        if 'rewards' in self.configuration:
            return self.configuration['rewards'][0]['display_name']
        return 'reward'

    def set_configuration(self, value, model_name, cached_vector_field, feature_key='name'):
        from solariat_nlp.bandit.models import DEFAULT_CONFIGURATION
        configuration = DEFAULT_CONFIGURATION[self.predictor.predictor_type]

        if hasattr(self, cached_vector_field):
            delattr(self, cached_vector_field)
        all_items = configuration[model_name]
        filtered_items = filter(lambda item: item[feature_key] in value, all_items)
        self.configuration[model_name] = filtered_items

    @property
    def context_vector(self):
        model_name = 'context_model'
        if hasattr(self, '_context_vector'):
            return self._context_vector
        else:
            self._context_vector = get_feature_vector_cls(
                '%s__%s' % (self.__class__.__name__, model_name),
                self.configuration[model_name])
            return self._context_vector

    @property
    def action_vector(self):
        model_name = 'action_model'
        if hasattr(self, '_action_vector'):
            return self._action_vector
        else:
            self._action_vector = get_feature_vector_cls(
                '%s__%s' % (self.__class__.__name__, model_name),
                self.configuration[model_name])
            return self._action_vector

    @property
    def classifier_class(self):
        "So we can easily plugin other classifier classes if we want."
        from solariat_bottle.db.predictors.classifiers import ChatDecisionUCB
        return ChatDecisionUCB

    def retrain(self, *args, **kwargs):
        return

    def save_local_models(self):
        if hasattr(self, '_clf'):
            start_ts = dt.now()
            for key, local_model in self.clf._model_cache.items():
                local_model.save() 
                # hack for float keys
                # because keys in model.clf_map should be strings
                # Alex Gogolev
                if isinstance(key, float):
                    key = str(int(key))
                self.clf_map[str(key)] = local_model.id
            LOGGER.info("Saved %s LocalModel-s, timedelta: %s", 
                len(self.clf._model_cache), 
                dt.now()-start_ts)

    def save(self):
        self.save_local_models()
        super(LinUCBPredictorModel, self).save()

    def delete(self, *args, **kwargs):
        LocalModelsMixin.delete(self, *args, **kwargs)
        PredictorModel.delete(self, *args, **kwargs)

    def clone(self):
        return self.__class__(
            parent=self.id,
            predictor=self.predictor,
            # version=(self.version or 0) + 1,
            weight=self.weight,
            display_name=self.display_name,
            configuration=self.configuration,
            state=ModelState.initial(),
            description=self.description,
            context_features=self.context_features,
            action_features=self.action_features,
            model_type=self.model_type)

    def to_json(self, fields_to_show=None):
        json_data = super(LinUCBPredictorModel, self).to_json(fields_to_show=fields_to_show)
        json_data.pop('packed_clf', None)
        json_data['status'] = self.state.status
        json_data['state'] = self.state.state
        json_data['last_run'] = self.last_run and datetime_to_timestamp_ms(self.last_run)
        return json_data


