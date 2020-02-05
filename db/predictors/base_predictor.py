
import sys
import math
import random
import numpy as np
import itertools

from bson import ObjectId
from datetime import datetime as dt

from solariat.db import fields
from solariat.db.abstract import TYPE_STRING, TYPE_INTEGER, TYPE_DICT, TYPE_LIST, TYPE_TIMESTAMP, KEY_NAME, KEY_TYPE, TYPE_BOOLEAN as _TYPE_BOOLEAN
from solariat.db.abstract     import Index
from solariat.exc.base import AppException
from solariat.utils.timeslot import now
from solariat.utils.packing import pack_object, unpack_object
from solariat.utils.parsers.base_parser import BaseParser, register_operator

from solariat_nlp.bandit.feature_vector import get_feature_vector_cls
from solariat_nlp.bandit.linucb import GLOBAL, HYBRID, DISJOINT

from sklearn.metrics import auc, mean_squared_error, roc_curve

from solariat_bottle.settings import LOGGER
from solariat_bottle.api.exceptions import DocumentDeletionError
from solariat_bottle.db.dynamic_profiles import ActionProfileDynamicManager
from solariat_bottle.db.predictors.models.base import PredictorModel, PredictorModelData, TaskData
from solariat_bottle.db.predictors.models.linucb import LinUCBPredictorModel, ACTION_ID, KEY_DATA, ModelState
from solariat_bottle.db.predictors.models.linear_regressor import LinearRegressorModel, LinearClassifierModel
from solariat_bottle.db.auth import AuthManager
from solariat_bottle.db.auth import AuthDocument
from solariat_bottle.db.predictors.operators import OPERATOR_REGISTRY
from solariat_bottle.db.predictors.base_score import BaseScore
from solariat_bottle.db.sequences import NumberSequences
from solariat_bottle.tasks import predictor_model_upsert_feedback_task

from solariat_bottle.db.dataset import Dataset
from solariat_bottle.db.schema_based import apply_shema_type
from solariat_bottle.utils.schema import get_dataset_functions

REWARD_NAME = 'reward_name'
DEFAULT_REWARD = 'reward'

TYPE_RANGE = LinUCBPredictorModel.TYPE_RANGE
TYPE_LABEL = LinUCBPredictorModel.TYPE_LABEL
TYPE_LOOKUP = LinUCBPredictorModel.TYPE_LOOKUP

TYPE_NUMERIC = 'Numeric'
TYPE_CLASSIFIER = 'Label'
TYPE_LINUCB = 'LinUCB'
TYPE_BOOLEAN = 'Boolean'

NAME_BOOLEAN_PREDICTOR = 'Logistic Regression'
NAME_NUMERIC_PREDICTOR = 'Linear Regression'
NAME_COMPOSITE_PREDICTOR = 'Composite Predictor'

TYPE_AGENTS = 'agents'
TYPE_GENERATED = 'dataset_generated'

MAX_CLASS_CARD = 5
ERROR_NO_ACTIVE_MODELS = "Predictor has no active models. Cannont finish score request. Please train and activate at least one model."

# register all operators, and update CUSTOM_OPERATORS dict in base_parser.py
for k, v in OPERATOR_REGISTRY.items():
    register_operator(k, v)


class LocalModel(AuthDocument):

    account = fields.ReferenceField('Account', required=True)
    action_id = fields.StringField(required=True)
    predictor_model = fields.ReferenceField('PredictorModel', required=True)
    packed_clf = fields.BinaryField(required=True)
    n_samples = fields.NumField(required=True)

    manager = AuthManager

    indexes = [
        Index(('predictor_model', 'action_id'), unique=True)
    ]

    def get_clf(self):
        if hasattr(self, '_clf'):
            res = self._clf
        else:
            res = unpack_object(self.packed_clf)
            self._clf = res
        return res

    def set_clf(self, value):
        self._clf = value
        self.packed_clf = pack_object(value)

    def del_clf(self):
        self.packed_clf = None

    def fit_local_model(self, data, rewards):
        clf = self.clf
        start_dt = dt.now()
        self.clf.fit(data, rewards)
        LOGGER.info('Sklearn fit() call took: %s, Size of clf: %s', dt.now()-start_dt, sys.getsizeof(self.clf))
        self.clf = clf

    def predict(self, *args, **kwargs):
        return self.clf.predict(*args, **kwargs)

    def predict_proba(self, *args, **kwargs):
        return self.clf.predict_proba(*args, **kwargs)
    
    clf = property(get_clf, set_clf, del_clf, "Im the clf property.")


class BasePredictorManager(AuthManager):

    def create(self, **kw):
        is_duplicate = False
        try:
            self.get(account_id=kw['account_id'], name=kw['name'])
            is_duplicate = True
        except Exception:
            pass
        if is_duplicate:
            raise AppException("Predictor with name %s already exists in accont %s" % (kw['name'], kw['account_id']))
        from solariat.db.abstract import TYPE_STRING as METRIC_STRING, TYPE_INTEGER as METRIC_INTEGER, \
            TYPE_BOOLEAN as METRIC_BOOLEAN
        kw['predictor_num'] = BasePredictor.make_counter()

        if 'dataset' in kw:
            from solariat_bottle.db.dataset import Dataset
            dset = Dataset.objects.get(kw['dataset'])
            # TODO: Try to evaluate metric on an expression
            metric_type = dset.schema_field_types.get(kw['metric'])
            metric_cardinality = dset.cardinalities[kw['metric']]['count']

            if metric_cardinality <= 1:
                err = "The cardinality for reward needs to be at least 2. Selected %s has cardinality of %s" % (
                    kw['metric'], metric_cardinality
                )
                raise AppException(err)

            if metric_type == METRIC_STRING:
                if metric_cardinality > MAX_CLASS_CARD:
                    err = "Maximum cardinality for string reward is %s. Selected %s has cardinality of %s" % (
                        MAX_CLASS_CARD, kw['metric'], metric_cardinality
                    )
                    raise AppException(err)
                kw['reward_type'] = TYPE_CLASSIFIER
            elif metric_type == METRIC_BOOLEAN:
                kw['reward_type'] = TYPE_BOOLEAN
            elif metric_type == METRIC_INTEGER:
                kw['reward_type'] = TYPE_NUMERIC
                _metric_field = '$' + kw['metric']
                _pipeline = [{
                    '$group': {
                        '_id': {},
                        'min_val': {'$min': _metric_field},
                        'max_val': {'$max': _metric_field}
                    }
                }]
                metric_values_range = dset.data_coll.aggregate(_pipeline)['result'][0]
                kw['metric_values_range'] = [int(metric_values_range['min_val']), int(metric_values_range['max_val'])]
            else:
                raise AppException("Unsupported metric type: %s. Only supported ones are %s" % (
                                   metric_type, [METRIC_BOOLEAN, METRIC_INTEGER, METRIC_STRING]))
        # Ignore any features with no label
        for k in ('context_features_schema', 'action_features_schema'):
            kw[k] = [v for v in kw[k] if v.get(BasePredictor.FEAT_LABEL)]
        instance = super(BasePredictorManager, self).create(**kw)
        instance.create_default_models()
        return instance

    def update(self, data, **kw):
        if not data['predictor_num']:
            data['predictor_num'] = BasePredictor.make_counter()

        should_upsert_feedback = False
        should_recreate_models = False
        existing_instance = None
        try:
            existing_instance = self.get(data.get('_id'))

            # need to drop tzinfo to compare offset-naive and offset-aware datetimes
            if data['from_dt'] is not None and data['to_dt'] is not None:
                data['from_dt'] = data.get('from_dt').replace(tzinfo=None)
                data['to_dt'] = data.get('to_dt').replace(tzinfo=None)

            if (existing_instance.action_id_expression != data.get('action_id_expression')# or
                # existing_instance.from_dt != data.get('from_dt') or
                # existing_instance.to_dt != data.get('to_dt')
                ):
                should_upsert_feedback = True
        except BasePredictor.DoesNotExist:
            pass

        if existing_instance and data.get('reward_type') != existing_instance.reward_type:
            existing_instance.model_class.objects.remove(predictor=existing_instance)
            should_recreate_models = True

        result = super(BasePredictorManager, self).update(data, **kw)

        if existing_instance:
            existing_instance.reload()

            if should_upsert_feedback:
                predictor_model_upsert_feedback_task.async(existing_instance)
                existing_instance.fresh_model_state()

            # temporary condition fix for qaart predictor
            # we should skip this block if we're dealing with
            # qaart predictor
            if should_recreate_models and not str(data.get('_id')).startswith('test'):
                existing_instance.create_default_models()
        return result


class PredictorDataManager(AuthManager):

    def create(self, *args, **kw):
        # if 'reward' in kw:
        #     kw['_reward'] = json.dumps(kw.pop('reward'))
        return super(PredictorDataManager, self).create(*args, **kw)

    def by_time_point(self,
                      predictor_id,
                      limit=50,
                      offset=0,
                      from_date=None,
                      to_date=None,
                      params={}):
        query = dict(predictor_id=predictor_id)
        if from_date and to_date:
            query['$and'] = [{self.doc_class.created_at.db_field: {'$gte': from_date}},
                             {self.doc_class.created_at.db_field: {'$lte': to_date}}]

        # CMG: Adding code to handle absence of keys so test will pass.
        context_facets = params.get('context_vector', None)
        action_facets = params.get('action_vector', None)

        if context_facets:
            for facet_name, facet_values in context_facets.iteritems():
                if facet_values:
                    query[self.doc_class.context.db_field + '.' + facet_name] = {'$in': facet_values}

        if action_facets:
            for facet_name, facet_values in action_facets.iteritems():
                if facet_values:
                    query[self.doc_class.action.db_field + '.' + facet_name] = {'$in': facet_values}

        # Use this form to avoid exception if key not found
        if 'models' in params and params['models']:
            query[self.doc_class.model_id.db_field] = {'$in': [ObjectId(m_id) for m_id in params['models']]}

        sort_query = [(self.doc_class.created_at.db_field, 1)]
        return [self.doc_class(data) for data in self.coll.find(query).sort(
            sort_query)[offset:limit + offset]]


class PredictorTrainingData(AuthDocument):

    allow_inheritance = True
    manager = PredictorDataManager

    MODEL_KEY = 'Model ID'

    collection = 'PredictorTrainingData'

    predictor_id = fields.ObjectIdField()
    # _reward = fields.StringField()      # Used to store JSON representation of reward
    context = fields.DictField(db_field='ctx')
    action = fields.DictField(db_field='act')
    created_at = fields.DateTimeField(db_field='crtd')
    model_id = fields.ObjectIdField(db_field='m_id')
    action_id = fields.StringField(db_field='act_id')
    n_batch = fields.NumField(db_field='nbch', required=True)

    indexes = (('predictor_id', 'n_batch'), ('model_id',), ('created_at',), ('predictor_id', 'action_id'))

    def __init__(self, *args, **kw):
        # if 'reward' in kw:
        #     kw['_reward'] = json.dumps(kw.pop('reward'))
        if 'n_batch' not in kw:
            kw['n_batch'] = -1 # filling out default
        super(PredictorTrainingData, self).__init__(*args, **kw)


class RegressorTrainingData(PredictorTrainingData):
    reward = fields.NumField()

    @classmethod
    def translate_static_key_name(cls, key_name):
        # keep in line with required interface for classification analysis
        return key_name

    @classmethod
    def translate_static_key_value(cls, key_name, key_value):
        # keep in line with required interface for classification analysis
        return key_value


class ClassifierTrainingData(PredictorTrainingData):
    reward = fields.StringField()


class BooleanTrainingData(PredictorTrainingData):
    reward = fields.BooleanField()


class EventActionTrainingData(RegressorTrainingData):
    event = fields.ReferenceField('Event')


class MultipleModelsMixin(object):

    models_data = fields.ListField(fields.EmbeddedDocumentField(PredictorModelData))

    _model = None
    _cached_models = None

    @property
    def models(self):
        if hasattr(self, 'model_class'):
            model_class = self.model_class
        else:
            model_class = LinUCBPredictorModel
        if self._cached_models is None:
            self._cached_models = model_class.objects(id__in=[x.model_id for x in self.models_data])[:]
        return self._cached_models

    def _get_model(self):
        return self._model

    def _set_model(self, model):
        if isinstance(model, PredictorModel) or model is None:
            self._model = model
        elif isinstance(model, basestring):  # assume this is model id
            self._model = PredictorModel.objects.get(model)

        return self

    model = property(_get_model, _set_model)

    def make_model(self, context_features=None, action_features=None, weight=1.0,
                   model_type=GLOBAL, **data):
        create_kw = dict(weight=weight)
        if context_features is not None:
            create_kw.update(context_features=context_features)
        if action_features is not None:
            create_kw.update(action_features=action_features)
        create_kw.update(data)
        create_kw.update(predictor=self)
        create_kw.update(model_type=model_type)
        if self.reward_type == TYPE_NUMERIC:
            create_kw['configuration'] = dict(n_estimators=100,
                                              loss='quantile',
                                              alpha=0.5,
                                              learning_rate=0.1,
                                              max_depth=6,
                                              random_state=42)
        else:
            create_kw['configuration'] = dict(n_estimators=100,
                                              learning_rate=0.1,
                                              max_depth=6,
                                              random_state=42)
        model = self.model_class(**create_kw)
        model.save()
        return model

    def clone_model(self, current_model):
        new_model = current_model.clone()
        new_model.save()
        self.add_model(new_model)
        self.model = new_model
        self.del_model(current_model)
        return new_model

    def as_model_instance(self, model):
        if isinstance(model, PredictorModel):
            return model
        elif isinstance(model, PredictorModelData):
            return PredictorModel.objects.get(model.model_id)
        elif isinstance(model, basestring):
            return PredictorModel.objects.get(model)
        elif isinstance(model, dict):
            if {'id'} & set(model):
                return PredictorModel.objects.get(model['id'])
            elif set(model):
                model['weight'] = float(model.get('weight', 1.0))
                return self.make_model(**model)

    def as_model_and_data(self, model):
        model = self.as_model_instance(model)
        model_data = PredictorModelData.init_with_model(model)
        if model_data in self.models_data:
            model_data = filter(lambda x: x.model_id == model.id, self.models_data)[0]
        return model, model_data

    @staticmethod
    def reward_types():
        return [TYPE_CLASSIFIER, TYPE_NUMERIC, TYPE_LINUCB]

    @staticmethod
    def model_types():
        return [GLOBAL, DISJOINT, HYBRID]

    def get_model(self, model):
        model_instance, model_data = self.as_model_and_data(model)
        return model_instance

    def add_model(self, model):
        model_instance, model_data = self.as_model_and_data(model)
        self._cached_models = None
        self.save()
        if isinstance(model, dict) and 'id' in model:
            return self.update_model(model_instance, model)
        else:
            if model_data not in set(self.models_data):
                self.models_data.append(model_data)
                self.save()
            return model_instance

    def create_update_model(self, model):
        """Returns pair (instance of created/updated model, bool created)"""
        existing_ids = set(x.model_id for x in self.models_data)
        instance = self.add_model(model)
        return instance, instance.id not in existing_ids

    def update_model(self, model_instance, data):
        assert isinstance(data, dict) and {'id'} & set(data)
        # update actual model instance
        data.pop('id', None)
        model_instance.update(**data)

        for model_data in self.models_data:
            if model_data.model_id == model_instance.id:
                break
        else:
            model_data = None

        if not model_instance.is_active and model_data:
            # model was deactivated - remove it from models list
            error = self.del_model(model_instance)
            if error:
                raise DocumentDeletionError(error)
            return model_instance
        elif model_data is None:
            model_data = PredictorModelData.init_with_model(model_instance)
            self.models_data.append(model_data)
            self.save()
            return model_instance

        # now update denormalized model data in predictor
        model_data.sync_with_model_instance(model_instance)
        self._cached_models = None
        self.save()
        return model_instance

    def del_model(self, model, hard=False):
        model_instance, model_data = self.as_model_and_data(model)

        if model_data in set(self.models_data):
            # if len(self.models_data) == 1:
            #     return False, "Predictor should have at least one model"

            for x in self.models_data:
                if x.model_id == model_instance.id:
                    break
            else:
                x = None
            if x:
                self.models_data.remove(x)

        if model_instance in set(self.models):
            self.models.remove(model_instance)
        self._cached_models = None
        self.save()

        if hard:
            model_instance.delete()
            return True, None
        else:
            # model_instance.status = model_instance.STATUS_INACTIVE
            # self.save()
            # model_instance.save()
            return True, None

        return False, "model_data not present in self.models_data"

    def __select_model(self, model=None):
        if model is not None:
            return self.as_model_instance(model)

        def weighted_choice(choices):
            total = sum(w for c, w in choices)
            r = random.uniform(0, total)
            upto = 0
            for c, w in choices:
                if upto + w > r:
                    return c
                upto += w

        if not self.models_data:
            return None

        model_choices = [(x, x.weight) for x in self.models if x.is_active]
        model = weighted_choice(model_choices)
        return model

    def features_space_size(self, model):
        context_sizes = [len(self.cardinalities[self.CTX_PREFIX + val[self.FEAT_LABEL]]) + 1
                         if self.CTX_PREFIX + val[self.FEAT_LABEL] in self.cardinalities else 1
                         for val in model.context_features]
        action_sizes = [len(self.cardinalities[self.ACT_PREFIX + val[self.FEAT_LABEL]]) + 1
                        if self.ACT_PREFIX + val[self.FEAT_LABEL] in self.cardinalities else 1
                        for val in model.context_features]
        return sum(context_sizes) + sum(action_sizes)

    def select_model(self, model=None):
        model = self.__select_model(model=model)
        if model is None:
            return model
        # Now cache the context_model / action_model for this train/score so we don't recompute every time
        context_keys = [v[self.FEAT_LABEL] for v in model.context_features]
        context_features = [val for val in self.context_features_schema if val[self.FEAT_LABEL] in context_keys]
        self.context_model = get_feature_vector_cls(self, context_features, prefix=self.CTX_PREFIX)

        action_keys = [v[self.FEAT_LABEL] for v in model.action_features]
        action_features = [val for val in self.action_features_schema if val[self.FEAT_LABEL] in action_keys]
        self.action_model = get_feature_vector_cls(self, action_features, prefix=self.ACT_PREFIX)
        return model


FEAT_TYPE = 'type'
FEAT_LABEL = 'label'
FEAT_EXPR = 'field_expr'

TYPE_LABEL = 'label'
TYPE_EXPR = 'expression'


class BasePredictor(AuthDocument, MultipleModelsMixin):

    STATUS_NO_DATA = 'NO DATA'
    STATUS_GENERATING = 'GENERATING DATA'
    STATUS_IN_SYNC = 'IN SYNC'
    STATUS_ERROR_OCCURED = 'IN ERROR'

    FEAT_TYPE = FEAT_TYPE
    FEAT_LABEL = FEAT_LABEL
    FEAT_EXPR = FEAT_EXPR

    TYPE_LABEL = TYPE_LABEL
    TYPE_EXPR = TYPE_EXPR

    CTX_PREFIX = 'ctx-'
    ACT_PREFIX = 'act-'

    manager = BasePredictorManager

    collection = "Predictors"
    allow_inheritance = True

    # model_class = LinUCBPredictorModel
    # training_data_class = PredictorTrainingData

    account_id = fields.ObjectIdField()
    dataset = fields.ObjectIdField()
    predictor_num = fields.NumField(unique=True, default=0)
    name = fields.StringField(unique=True)
    description = fields.StringField()
    feedback_gen_expression = fields.StringField()
    predictor_type = fields.StringField()
    metric = fields.StringField()
    action_id_expression = fields.StringField()
    # TODO[sabr]: rename to metric_type
    reward_type = fields.StringField(choices=(TYPE_CLASSIFIER, TYPE_NUMERIC, TYPE_LINUCB, TYPE_BOOLEAN),
                                     default=TYPE_NUMERIC)
    metric_values_range = fields.ListField(fields.NumField(), db_field='mvr')
    action_type = fields.StringField(choices=(TYPE_AGENTS, TYPE_GENERATED),
                                     default=TYPE_GENERATED)
    # model_type = fields.StringField(choices=(DISJOINT, GLOBAL, HYBRID), default=GLOBAL)

    # date range for certain operators like collect and union
    from_dt = fields.DateTimeField()
    to_dt = fields.DateTimeField()
    created_at = fields.DateTimeField(default=now)

    context_features_schema = fields.ListField(fields.DictField())
    action_features_schema = fields.ListField(fields.DictField())

    score_expression = fields.StringField(default="")
    is_locked = fields.BooleanField(default=False)
    status = fields.StringField(default=STATUS_NO_DATA)
    info_message = fields.StringField()
    train_set_length = fields.NumField(default=0)
    n_training_data_batches = fields.NumField(default=1000)
    action_profile = ActionProfileDynamicManager()

    cardinalities = fields.DictField()

    TYPE_COMPOSITE = 'Composite Predictor'

    context_model = None
    action_model = None
    min_integer_values = dict()

    def log_collection_name(self):
        return 'scorelog_' + str(id) + self.name.replace(' ', '').replace('\t', '')[:63]

    def mark_error(self, message):
        self.info_message = message
        self.status = self.STATUS_ERROR_OCCURED
        self.save()

    def clear_error(self):
        self.info_message = ''
        self.save()

    def full_data_reset(self):
        self.training_data_class.objects.remove(predictor_id=self.id)
        self.model_class.objects.remove(predictor=self)
        self.models_data = []
        self._cached_models = None
        self.save()

    @staticmethod
    def construct_filter_query(filter_str, context=[]):
        from solariat_bottle.db.filters import FilterTranslator
        # TODO: Move this somewhere in utils
        from solariat_bottle.api.agents import DOT_REPLACEMENT_STR
        filter_str = filter_str.replace('.', DOT_REPLACEMENT_STR)
        query = FilterTranslator(filter_str, context=context).get_mongo_query()
        return query, query

    def schema_equals(self, existing_schema, new_schema):
        if not existing_schema and new_schema:
            return False
        sorted_schema = sorted(existing_schema, key=lambda x: x.get(FEAT_LABEL, None))
        sorted_new_schema = sorted(new_schema, key=lambda x: x.get(FEAT_LABEL, None))
        return sorted_schema == sorted_new_schema

    @property
    def account(self):
        from solariat_bottle.db.account import Account
        return Account.objects.get(self.account_id)

    @property
    def model_class(self):
        class_map = {TYPE_NUMERIC: LinearRegressorModel,
                     TYPE_CLASSIFIER: LinearClassifierModel,
                     TYPE_LINUCB: LinUCBPredictorModel,
                     TYPE_BOOLEAN: LinearClassifierModel}
        return class_map[self.reward_type]

    @property
    def training_data_class(self):
        training_class_map = {TYPE_NUMERIC: RegressorTrainingData,
                              TYPE_LINUCB: RegressorTrainingData,
                              TYPE_CLASSIFIER: ClassifierTrainingData,
                              TYPE_BOOLEAN: BooleanTrainingData}
        return training_class_map[self.reward_type]

    def __init__(self, *args, **kwargs):
        super(BasePredictor, self).__init__(*args, **kwargs)
        self.model = None

    @property
    def action_class_candidates(self):
        return [TYPE_AGENTS, TYPE_GENERATED]

    def get_action_class(self):
        # TODO: In the future we're going to need to allow any other class to be configured here
        if self.action_type == TYPE_AGENTS:
            agent_profile_schema = self.account.agent_profile._get()
            return agent_profile_schema.get_data_class()
        elif self.action_type == TYPE_GENERATED:
            # TODO: Need to generate a dynamic profile
            action_profile_schema = self.action_profile._get()
            return action_profile_schema.get_data_class()

    @classmethod
    def make_counter(cls):
        return NumberSequences.advance('PredictorCounter')

    def get_cardinalities(self, f_name):
        return self.cardinalities.get(f_name, [])

    @property
    def context_feature_names(self):
        return [entry[FEAT_LABEL] for entry in self.context_features_schema]

    @property
    def action_feature_names(self):
        return [entry[FEAT_LABEL] for entry in self.action_features_schema]

    def refresh_cardinalities(self):
        cardinalities = dict()
        max_considered_entries = 1000000
        for ctx_entry in self.context_features_schema:
            f_name = ctx_entry[FEAT_LABEL]
            match_no_limit = [{'$match': {'predictor_id': self.id}},
                              {'$limit': max_considered_entries},
                              {'$group': {'_id': '$ctx.' + f_name}}]
            agg_results = self.training_data_class.objects.coll.aggregate(match_no_limit)
            full_values = []
            for d_t in agg_results['result']:
                full_values.append(d_t['_id'] if not type(d_t['_id']) in [list, dict] else str(d_t['_id']))
            cardinalities[self.CTX_PREFIX + f_name] = full_values
        for ctx_entry in self.action_features_schema:
            f_name = ctx_entry[FEAT_LABEL]
            match_limited = [{'$match': {'predictor_id': self.id}},
                             {'$limit': max_considered_entries},
                             {'$group': {'_id': '$act.' + f_name}}]
            agg_results = self.training_data_class.objects.coll.aggregate(match_limited)
            batched_values = []
            for d_t in agg_results['result']:
                batched_values.append(d_t['_id'] if not type(d_t['_id']) in [list, dict] else str(d_t['_id']))
            cardinalities[self.ACT_PREFIX + f_name] = batched_values
        f_name = self.action_id_expression
        match_limited = [{'$match': {'predictor_id': self.id}},
                         {'$limit': max_considered_entries},
                         {'$group': {'_id': '$act_id'}}]
        agg_results = self.training_data_class.objects.coll.aggregate(match_limited)
        batched_values = []
        for d_t in agg_results['result']:
            batched_values.append(d_t['_id'] if not type(d_t['_id']) in [list, dict] else str(d_t['_id']))
        cardinalities[self.ACT_PREFIX + str(f_name)] = batched_values
        self.cardinalities = cardinalities
        self.min_integer_values = dict()
        self.save()

    def create_default_models(self):
        # add default model
        initial_state = ModelState.initial()
        model = self.make_model(context_features=self.context_features_schema,
                                action_features=self.action_features_schema,
                                display_name='Full feature set',
                                state=initial_state)
        self.add_model(model)

    @staticmethod
    def save_model(model):
        model.save()
        return model

    def score(self, actions, context, model=None):
        if not any(self.cardinalities.values()):
            # TODO: Think how to handle defaults / no trained model
            return [(action[ACTION_ID], 0.5, 0.5) for action in actions]
        self.model = self.select_model(model=model)
        if not self.model:
            raise AppException(ERROR_NO_ACTIVE_MODELS)
        prefixed_context = dict()
        for key, val in context.iteritems():
            feat_key = self.CTX_PREFIX + key
            if feat_key not in self.cardinalities or not self.cardinalities[feat_key]:
                # No data for it anyway, we can't use it for anything.
                continue
            if not type(val) in (int, long, float):
                prefixed_context[feat_key] = val
            else:
                if feat_key not in self.min_integer_values:
                    self.min_integer_values[feat_key] = min(self.cardinalities.get(feat_key, [None]))
                min_value = self.min_integer_values[feat_key]
                if min_value is not None and min_value <= 0:
                    val += abs(min_value) + 1
                prefixed_context[feat_key] = int(np.log(val))
        vectorized_context = self.context_model(prefixed_context).vec

        vectorized_actions = []
        for action in actions:
            prefixed_action = dict()
            for key, val in action.iteritems():
                feat_key = self.ACT_PREFIX + key
                if feat_key not in self.cardinalities or not self.cardinalities[feat_key]:
                    # No data for it anyway, we can't use it for anything.
                    continue
                if not type(val) in (int, long, float):
                    prefixed_action[feat_key] = val
                else:
                    if feat_key not in self.min_integer_values:
                        self.min_integer_values[feat_key] = min(self.cardinalities.get(feat_key, [None]))
                    min_value = self.min_integer_values[feat_key]
                    if min_value is not None and min_value <= 0:
                        val += abs(min_value) + 1
                    prefixed_action[feat_key] = int(np.log(val))

            vectorized_action = {ACTION_ID: action[ACTION_ID],
                                 KEY_DATA: self.action_model(prefixed_action).vec}
            vectorized_actions.append(vectorized_action)

        score = self._score(vectorized_context, vectorized_actions)
        # print score
        return score

    def _score(self, context, actions):
        t0 = dt.utcnow()
        score = self.model.score(context, actions)
        latency = (dt.utcnow() - t0).total_seconds()
        self.track_score(self.model, latency=latency)
        return score

    def track_score(self, model, latency):
        F = BaseScore.F
        BaseScore.objects.coll.update(
            {F.matching_engine: self.id, F.model_id: model.id},
            {"$inc": {F.cumulative_latency: latency, F.counter: 1}},
            upsert=True)

    def feedback(self, context, action, reward=None, **kwargs):
        # Just generate training data instance, actual training is done async in batches
        model_key = self.training_data_class.MODEL_KEY
        model_id = None if model_key not in kwargs else str(kwargs[model_key])

        created_at = dt.utcnow()
        if 'created_at' in kwargs:
            created_at = kwargs['created_at']

        processed_context = {}
        processed_action = {}
        if ACTION_ID in action:
            processed_action[ACTION_ID] = action[ACTION_ID]
        else:
            action_id = self.apply_schema([{FEAT_TYPE: self.TYPE_LABEL,
                                            FEAT_LABEL: self.action_id_expression,
                                            FEAT_EXPR: self.action_id_expression}],
                                          action)
            processed_action[ACTION_ID] = action_id.get(self.action_id_expression)

        for key in context.keys():
            for entry in self.context_features_schema:
                if entry[FEAT_LABEL].lower() == key.lower():
                    processed_context[entry[FEAT_LABEL]] = context[key]

        for key in action.keys():
            for entry in self.action_features_schema:
                if entry[FEAT_LABEL].lower() == key.lower():
                    processed_action[entry[FEAT_LABEL]] = action[key]
        training_data = self.training_data_class(predictor_id=self.id,
                                                 context=processed_context,
                                                 action=processed_action,
                                                 action_id=str(processed_action[ACTION_ID]),
                                                 reward=reward,
                                                 model_id=model_id,
                                                 created_at=created_at,
                                                 n_batch=self.get_n_batch_value())
        training_data.save()
        self.train_set_length = self.train_set_length + 1
        self.save()
        return dict(ok=True, message="Feedback recorded successfully")

    def get_n_batch_value(self):
        return random.randint(0, self.n_training_data_batches)

    def insert_training_data_batch(self, context_generator):
        bulk = self.training_data_class.objects.coll.initialize_ordered_bulk_op()

        for context in context_generator:
            action = {'action_id': self.get_action_id(context)}
            reward = self.metric

            training_data = self.training_data_class(predictor_id=self.id,
                                                     context=context,
                                                     action=action,
                                                     reward=reward)
            bulk.insert(training_data.data)
            self.train_set_length = self.train_set_length + 1
        bulk.execute()
        self.save()

    def train_models(self, model=None):
        models = [model] if model else self.models
        # calculate metrics
        for model in models:
            LOGGER.info("Training actual model")
            model.clf.retrain(self)
            self.save_model(model)

    def train_on_feedback_batch(self, context_list, action_list, reward_list, model=None, insert_feedback=True):
        if insert_feedback:
            bulk = self.training_data_class.objects.coll.initialize_ordered_bulk_op()

            for context, action, reward in itertools.izip(context_list, action_list, reward_list):
                training_data = self.training_data_class(predictor_id=self.id,
                                                         context=context,
                                                         action=action,
                                                         action_id=str(action['action_id']),
                                                         reward=reward,
                                                         n_batch=self.get_n_batch_value())
                bulk.insert(training_data.data)
            bulk.execute()
        models = [model] if model else self.models
        for model in models:
            self.refresh_cardinalities()
            self.train_models(model=model)
            # model.version += 1
            self.save_model(model)

    def reset_training_data(self):
        removed = self.training_data_class.objects.remove(predictor_id=self.id,
                                                          created_at__lte=self.to_dt,
                                                          created_at__gte=self.from_dt)['n']
        self.status = self.STATUS_NO_DATA
        self.save()
        return removed

    @staticmethod
    def get_type_mapping(value):
        import datetime
        if type(value) in (int, float, long):
            return TYPE_INTEGER
        if type(value) in (str, unicode):
            return TYPE_STRING
        if type(value) in (bool, ):
            return _TYPE_BOOLEAN
        if type(value) in (dict, ):
            return TYPE_DICT
        if type(value) in (list, tuple):
            return TYPE_LIST
        if type(value) in (datetime.datetime, ):
            return TYPE_TIMESTAMP

    def upsert_feedback(self):
        from collections import defaultdict
        LOGGER.debug("Removing training data for predictor %s", self.name)
        self.training_data_class.objects.remove(predictor_id=self.id)
        # expression = self.feedback_gen_expression
        # entities_registry = EntitiesRegistry()
        # if expression:
        #     expression_data = entities_registry.generate_expression_context(self, expression)
        #     parser = BaseParser(expression_data['expression'], entities_registry.get_all_entries())
        #     parser.evaluate(expression_data['context'])
        # Generate new data based on dataset and predictor data.
        from solariat_bottle.db.dataset import Dataset
        dset = Dataset.objects.get(self.dataset)
        query = {}
        if dset.created_at_field and self.from_dt:
            query[dset.created_at_field] = {'$gte': self.from_dt}
        if dset.created_at_field and self.to_dt:
            query = {'$and': [query, {dset.created_at_field: {'$lte': self.to_dt}}]}
        BATCH_SIZE = 20000
        LOGGER.info("Executing query: " + str(query))
        N_ITEMS = dset.get_data(**query).count()
        LOGGER.info("Records number: " + str(N_ITEMS))
        N_BATCHES = N_ITEMS / BATCH_SIZE + 1
        self.status = self.STATUS_GENERATING
        self.save()
        action_profile_schema = self.action_profile._get()
        schema_generated = False

        ActionProfile = action_profile_schema.get_data_class()
        ActionProfile.objects.remove(id__ne=1)

        # Make sure to load up all non volatile keys in local storage so we avoid lookups on
        # abstract fields for each individual item that we're processing from the dataset.
        _t = self.training_data_class.get_hierarchy()
        F = self.training_data_class.F
        key_predictor_id = F.predictor_id
        key_context = F.context
        key_action = F.action
        key_action_id = F.action_id
        key_reward = F.reward
        key_created_at = F.created_at
        key_model_id = F.model_id
        key_n_batch = F.n_batch
        dataset_model_key = self.training_data_class.MODEL_KEY
        dataset_created_at = dset.created_at_field
        context_features_schema = self.context_features_schema
        action_features_schema = self.action_features_schema
        action_id_expression = self.action_id_expression
        metric = self.metric
        item_id = self.id
        action_type = self.action_type
        training_data_class = self.training_data_class
        dset_class = dset.get_data_class().objects.coll
        models = self.models
        action_profiles = defaultdict(dict)

        for batch_idx in xrange(N_BATCHES):
            bulk = training_data_class.objects.coll.initialize_ordered_bulk_op()
            LOGGER.info('dset query for upsert_feedback: %s' % str(query))
            for dset_entry in dset_class.find(**query)[batch_idx * BATCH_SIZE:(batch_idx + 1) * BATCH_SIZE]:
                context = self.apply_schema(context_features_schema, dset_entry)
                action = self.apply_schema(action_features_schema, dset_entry)
                # TODO: Hacked for now since UI passes it like this. This needs to be an expression too

                action_id = self.apply_schema([{FEAT_TYPE: TYPE_LABEL,
                                                FEAT_LABEL: action_id_expression,
                                                FEAT_EXPR: action_id_expression}],
                                              dset_entry)
                if action_id:
                    action[ACTION_ID] = action_id.get(action_id_expression)
                else:
                    action[ACTION_ID] = None
                # TODO: Hacked for now since UI passes it like this. This needs to be an expression too
                reward = self.apply_schema([{FEAT_TYPE: TYPE_LABEL,
                                             FEAT_LABEL: metric,
                                             FEAT_EXPR: metric}],
                                           dset_entry)
                #print 'Computed reward was ' + str(reward)
                if not reward:
                    LOGGER.debug("!! NO REWARD, won't insert any feedback records")
                    continue
                reward = reward[self.metric]
                created_at = dset_entry[dataset_created_at] if dataset_created_at in dset_entry else dt.now()

                model_id = None
                if dataset_model_key in dset_entry:
                    model_id = str(dset_entry[dataset_model_key])

                # TODO: This needs to get 'hacked' in the dataset at load time
                # if random.random() > 0.5 and models:
                #     model_id = random.choice([m.id for m in models])

                # it's a hack to avoid strings like "129461290.0" with traling ".0" substr
                # it should be handled via schema, but I already upserted 4.7 mil of records to mongo
                if isinstance(action[ACTION_ID], float):
                    action_id_value = str(int(action[ACTION_ID]))
                else:
                    action_id_value = str(action[ACTION_ID])

                action_profiles[action[ACTION_ID]] = action
                data = {key_predictor_id: item_id,
                        key_context: context,
                        key_action: action,
                        key_action_id: action_id_value,
                        key_reward: reward,
                        key_created_at: created_at,
                        key_model_id: model_id,
                        key_n_batch: self.get_n_batch_value(),
                        '_t': _t}
                bulk.insert(data)
            try:
                res = bulk.execute()
            except Exception, ex:
                LOGGER.info("Failed to insert bulk nr: " + str(batch_idx))
                LOGGER.error("Failed with ex: %s" % ex)
                res = None
            LOGGER.info("Result of bulk insert: " + str(res) + " for bulk number " + str(batch_idx))

        if action_type == TYPE_GENERATED:
            first_action = action_profiles.values()[0]
            schema = []
            for key, val in first_action.iteritems():
                # if key not in self.get_action_class().fields:
                inferred_type = self.get_type_mapping(val)
                if inferred_type:
                    schema.append({KEY_NAME: key, KEY_TYPE: inferred_type})
            action_profile_schema.discovered_schema = schema
            action_profile_schema._raw_data_cls = None
            action_profile_schema.save()

            ActionProfile = action_profile_schema.get_data_class()
            try:
                ActionProfile.objects.coll.create_index('action_id')
            except Exception:
                pass
            bulk_actions = ActionProfile.objects.coll.initialize_ordered_bulk_op()
            for action_id, action in action_profiles.iteritems():
                bulk_actions.find({'action_id': action_id}).upsert().update({'$set': action})
            bulk_actions.execute()

        self.status = self.STATUS_IN_SYNC
        total_count = self.training_data_class.objects.count(predictor_id=self.id)
        self.info_message = "Finished inserting a total of %s entries" % total_count
        self.train_set_length = total_count
        self.save()
        self.refresh_cardinalities()

    def apply_schema(self, features_schema, dataset_object):
        result = dict()
        for feature in features_schema:
            f_type = feature[FEAT_TYPE]
            expression = feature[FEAT_EXPR]
            f_name = feature[FEAT_LABEL]

            # this is just a label or this is feature set for metric & action
            # TODO: unify data format!
            is_label = (
                (
                    f_type != TYPE_EXPR  # for gforce demo data
                    and not feature.get('is_expression', False)  # this is how we expression from UI
                ) and (
                    f_type == TYPE_LABEL   # for action & metric calculations
                    or expression == f_name     # this is how we emulate "label" behavior
                )
            )

            if f_type == TYPE_EXPR:
                f_type = TYPE_STRING    # for old EXP format, set default return type to string

            if is_label:
                if isinstance(dataset_object, dict):
                    value = dataset_object.get(expression)
                else:
                    value = getattr(dataset_object, expression)
                # do not cast value, pass as it is
                # if value is not None:
                #     if not type(value) in (str, unicode, float, int, long, bool):
                #         value = str(value)
            else:
                if isinstance(dataset_object, dict):
                    context = dataset_object.keys()
                else:
                    context = dataset_object.data.keys()
                context.append('interaction_context')
                parser = BaseParser(expression, context)
                try:
                    if isinstance(dataset_object, dict):
                        eval_context = dataset_object
                    else:
                        eval_context = dataset_object.data
                    eval_context['interaction_context'] = dataset_object
                    value = parser.evaluate(eval_context)
                except TypeError:
                    value = None

                if value is not None:
                    value_type = self.get_type_mapping(value)
                    if value_type is None:
                        raise AppException("Unknown feature type: %s in %s for predictor %s" %
                            (f_type, feature, self))
                    elif value_type != f_type:
                        value = apply_shema_type(value, f_type)

            if value is not None:
                result[f_name] = value
        return result

    def get_action_id(self, input_data):
        parser = BaseParser(self.action_id_expression, input_data.keys())
        return parser.evaluate(input_data)

    def context_action_ids(self, data):
        # action_id = data.action.id
        # same as above but without de-referencing
        F = data.__class__.F
        context_id = data.data[F('customer')].id
        action_id = data.data[F('action')].id
        # context_id = data.customer.id
        return context_id, action_id

    def _retrain(self, models):
        # For easy testing of async stuff while dev mode
        from solariat_bottle.tasks.predictors import retrain_classifier
        # retrain_classifier.ignore(self, models=models)
        feedback_count = self.train_set_length      # self.training_data_class.objects(predictor_id=self.id).count()
        for model in models:
            self.save_progress(model, 0, feedback_count)
        retrain_classifier(self, models=models)     # jobs

    def retrain(self, create_new_model_version=True, model=None):
        models = [model] if model else self.models

        cloned_models = []
        if create_new_model_version:
            for model in models:
                new_model = self.clone_model(model)
                next_state = model.state.try_change('deactivate')
                if next_state:
                    model.update(state=next_state)
                cloned_models.append(new_model)
        else:
            cloned_models = models
        self._retrain(cloned_models)
        for model in cloned_models:
            model.reload()
            model._clf = None
        return cloned_models

    def save_progress(self, current_model, progress, total):
        model_instance, model_data = self.as_model_and_data(current_model)
        task = model_instance.task_data or TaskData()
        task.total = total
        task.done = progress
        task.updated_at = now()
        model_instance.task_data = task
        model_instance.last_run = now()
        # LOGGER.info("Size of new task_data: %s", sys.getsizeof(model_instance.task_data))
        # LOGGER.info("Size of new model_instance: %s", sys.getsizeof(model_instance))
        # LOGGER.info("Size of model.clf: %s", sys.getsizeof(model_instance.clf.packed_model))
        # LOGGER.info("New model_instance: %s", model_instance.to_dict())
        model_instance.save()
        model_data.sync_with_model_instance(model_instance)
        self.save()

    def get_last_run(self):
        last_run = filter(None, [model.last_run for model in self.models])
        if last_run:
            last_run = max(last_run)
        return last_run

    def fresh_model_state(self):
        for model in self.model_class.objects(predictor=self):
            model.packed_clf = None
            model.state = ModelState(state=ModelState.CYCLE_NEW, status=ModelState.STATUS_INACTIVE)
            model.save()
            self.save_progress(model, progress=100, total=100)

    def reset(self, create_new_model_version=True, model=None):
        models = [model] if model else self.models
        result = []
        for model in models:
            if create_new_model_version:
                next_state = model.state.try_change('deactivate')
                if next_state:
                    model.update(state=next_state)
                new_model = self.clone_model(model)
                result.append(new_model)
            else:
                model.packed_clf = None
                model.update(state=ModelState(state=ModelState.CYCLE_NEW, status=ModelState.STATUS_INACTIVE))
                self.save_progress(model, progress=0, total=0)
                result.append(model)
        return result

    def suspend_model(self, model=None):
        models = [model] if model else self.models
        for model in models:
            model.update(state=model.state.change('deactivate'))

    def reset_model(self, model):
        return self.reset(model=model)

    def retrain_model(self, model, async=True):
        if async:
            from solariat_bottle.tasks import predictor_model_retrain_task
            return predictor_model_retrain_task(self, model)
            return predictor_model_retrain_task.async(self, model)
        else:
            return self.retrain(model=model)

    def load(self):
        current_model = self.model or self.select_model()
        self.del_model(current_model)

    def to_dict(self, fields2show=None):
        data = super(BasePredictor, self).to_dict()
        data['models_count'] = len(self.models_data)
        data['is_reward_editable'] = False
        data['is_composite'] = False
        data['expression_context'] = self.get_expression_context()
        data = PredictorConfigurationConversion.python_to_json(data)
        return data

    def get_expression_context(self):
        if self.dataset:
            try:
                dataset = Dataset.objects.get(self.dataset)
            except Dataset.DoesNotExist:
                dataset = None
        else:
            dataset = None
        return {
            'context': dataset.get_expression_context() if dataset else [],
            'functions': get_dataset_functions()
        }


class CompositePredictorManager(AuthManager):

    def create(self, **kw):
        kw['predictor_num'] = BasePredictor.make_counter()
        instance = super(CompositePredictorManager, self).create(**kw)
        # Make sure to evaluate expression
        instance.expression
        return instance

    def update(self, data, **kw):
        if not data['predictor_num']:
            data['predictor_num'] = BasePredictor.make_counter()
        super(CompositePredictorManager, self).update(data, **kw)
        instance = self.get(data['_id'])
        # Make sure to evaluate expression
        instance.expression
        return instance


class CompositePredictor(BasePredictor):

    model_class = None
    training_data_class = None

    manager = CompositePredictorManager

    predictors_list = fields.ListField(fields.StringField(), required=True)
    raw_expression = fields.StringField(required=True)
    compiled_expression = fields.StringField()
    last_run = fields.DateTimeField(null=True)

    __predictors = []
    __expression = None

    def to_dict(self, fields2show=None):
        d = AuthDocument.to_dict(self)
        d['models_count'] = len(self.predictors_list)
        d['is_reward_editable'] = False
        d['predictor_names'] = [p.name for p in self.predictors]
        d['predictors'] = [p.to_dict() for p in self.predictors]
        d['is_composite'] = True
        d['expression_context'] = self.get_expression_context()
        return d

    def get_last_run(self):
        return self.last_run

    def get_score(self, score, scale):
        if scale == self.SCALE_LINEAR:
            return score
        if scale == self.SCALE_LOG:
            return math.log(score)
        if scale == self.SCALE_QUAD:
            return score * score

    @property
    def predictors(self):
        if not self.__predictors:
            self.__predictors = BasePredictor.objects.find(id__in=self.predictors_list)[:]
        return self.__predictors

    @property
    def predictor_names(self):
        return [p.name.replace(' ', '') for p in self.predictors]

    @property
    def expression(self):
        if not self.__expression:
            if not self.compiled_expression:
                self.compiled_expression = BaseParser(self.raw_expression, self.predictor_names).to_pickle()
                self.save()
            self.__expression = BaseParser.from_pickle(self.compiled_expression)
        return self.__expression

    @property
    def context_feature_names(self):
        feat_names = []
        for predictor in self.predictors:
            feat_names += predictor.context_feature_names
        return feat_names

    @property
    def action_feature_names(self):
        feat_names = []
        for predictor in self.predictors:
            feat_names += predictor.action_feature_names
        return feat_names

    def score(self, actions, context, model=None):
        agg_scores = {}
        """
        Aim to compute a nested dictionary like follows that can be evaluated at the end:
        {<action_id1>: {'score': {<p_name1>: <score1>, <p_name2>: <score2>, ...},
                        'ucb': {<p_name1>: <ucb1>, <p_name2>: <ucb2>, ...}}
         <action_id2>: {'score': {<p_name1>: <score1>, <p_name2>: <score2>, ...},
                        'ucb': {<p_name1>: <ucb1>, <p_name2>: <ucb2>, ...}}
         ..... }
        """
        for predictor in self.predictors:
            p_scores = predictor.score(actions=actions, context=context, model=model)
            for (action_id, score, ucb_score) in p_scores:
                if action_id not in agg_scores:
                    agg_scores[action_id] = dict(score=dict(), ucb=dict())
                agg_scores[action_id]['score'][predictor.name] = score
                agg_scores[action_id]['ucb'][predictor.name] = ucb_score

        """
        Given a nested dictionary structure as above, translate back into 3 tuple list with the evaluated
        composite expressions.
        """
        results = []
        for action_id, score_data in agg_scores.iteritems():
            composite_score = self.expression.evaluate(score_data['score'])
            composite_ucb = self.expression.evaluate(score_data['ucb'])
            results.append((action_id, composite_score, composite_ucb))
        self.last_run = dt.now()
        self.save()
        return sorted(results, key=lambda x: -x[1])

    def feedback(self, context, action, reward=None, feedback_id=None, save_model=True, **kwargs):
        raise AppException("Feedback score is not supported for composite predictors.")

    def retrain_model(self, model, async=True):
        raise AppException("Retrain is not supported for composite predictors.")


class LinearPredictor(BasePredictor):
    model_class = LinearClassifierModel


class LinearClassifier(BasePredictor):
    model_class = LinearClassifierModel


class LookupTestPredictor(BasePredictor):

    lookup_map = fields.DictField(db_field='lp')

    context_feature_names = fields.ListField(fields.StringField())

    def score(self, actions, context, model=None):

        final_results = []
        context = context.items()
        context = sorted(context)

        agent_profile_schema = self.account.agent_profile._get()
        AgentProfile = agent_profile_schema.get_data_class()
        for action in actions:
            agent = AgentProfile.objects.get(action['action_id'])
            lookup_key = str([agent.data.get('native_id'), context])
            LOGGER.info('LookupTestPredictor::')
            LOGGER.info('LookupTestPredictor::lookup_key %s' % lookup_key)
            LOGGER.info('LookupTestPredictor::lookup_map %s' % self.lookup_map)
            score = self.lookup_map.get(lookup_key, 0)
            final_results.append((
                str(agent.id), score, score
            ))
        LOGGER.info('results: %s' % final_results)

        return final_results



import copy
import collections
inf = float('inf')

def change_values_in_dict(obj, from_to_dict):
    for k, v in obj.iteritems():
        if isinstance(v, collections.Mapping):
            change_values_in_dict(v, from_to_dict)
        elif isinstance(v, collections.Sequence) and not isinstance(v, basestring):
            [change_values_in_dict(each, from_to_dict) for each in v if isinstance(each, collections.Mapping)]
        elif v in from_to_dict:
            obj[k] = from_to_dict[v]


class PredictorConfigurationConversion(object):
    @staticmethod
    def json_to_python(configuration):
        """Call this method when configuration from UI needs to be used in python
        """
        configuration = copy.deepcopy(configuration)
        change_values_in_dict(configuration, {'inf': inf, '-inf': -inf})
        return configuration

    @staticmethod
    def python_to_json(configuration):
        """Call this method when configuration from python needs to be passed to UI
        """
        configuration = copy.deepcopy(configuration)
        change_values_in_dict(configuration, {inf: 'inf', -inf: '-inf'})
        return configuration
