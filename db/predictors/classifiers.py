import random
import numpy as np
from bson import ObjectId

from sklearn import linear_model, metrics
from datetime import datetime as dt

from solariat.utils.packing import pack_object, unpack_object
from solariat_nlp.bandit.linucb import LinUCB, HYBRID, DISJOINT, ACTION_ID, KEY_DATA, GLOBAL
from solariat_nlp.bandit.models import (
        CUSTOMER_VECTOR, AGENT_VECTOR,
        SUPERVISOR_ALERT_CONTEXT_VECTOR, SUPERVISOR_ALERT_ACTION_VECTOR,
        CHAT_OFFER_CONTEXT_VECTOR, CHAT_OFFER_ACTION_VECTOR
)
from solariat_bottle.settings import LOGGER
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from solariat_bottle.db.predictors.base_predictor import LocalModel

class AgentMatchingUCB(LinUCB):
    def __init__(self, alpha=0.4, model_type=HYBRID, actions=None, model=None, **kwargs):
        cv = kwargs.get('configuration', {}).get('context_model') or kwargs.get('context_model', CUSTOMER_VECTOR)
        av = kwargs.get('configuration', {}).get('action_model') or kwargs.get('action_model', AGENT_VECTOR)
        super(AgentMatchingUCB, self).__init__(context_model=cv,
                                               action_model=av,
                                               alpha=alpha,
                                               model_type=model_type,
                                               actions=actions,
                                               model=model)


class AlertSupervisorUCB(LinUCB):
    def __init__(self, alpha=0.4, model_type=HYBRID, actions=None, model=None, **kwargs):
        cv = kwargs.get('context_model', SUPERVISOR_ALERT_CONTEXT_VECTOR)
        av = kwargs.get('action_model', SUPERVISOR_ALERT_ACTION_VECTOR)
        super(AlertSupervisorUCB, self).__init__(context_model=cv,
                                                 action_model=av,
                                                 alpha=alpha,
                                                 model_type=model_type,
                                                 actions=actions,
                                                 model=model)


class ChatDecisionUCB(LinUCB):
    def __init__(self, alpha=0.7, model_type=HYBRID, actions=None, model=None, **kwargs):
        cv = kwargs.get('context_model', CHAT_OFFER_CONTEXT_VECTOR)
        av = kwargs.get('action_model', CHAT_OFFER_ACTION_VECTOR)
        super(ChatDecisionUCB, self).__init__(context_model=cv,
                                              action_model=av,
                                              alpha=alpha,
                                              model_type=model_type,
                                              actions=actions,
                                              model=model)


GLOBAL_KEY = '__%s__' % GLOBAL
BATCH_SIZE = 10000 
MAX_DATA_SIZE = 2 ** 29

from gevent import threading
_in_memory_model_cache = threading.local()


def convert_action_id(action_id):
    if isinstance(action_id, float):
        action_id = str(int(action_id))
    elif isinstance(action_id, int):
        action_id = str(action_id)
    elif action_id is None or isinstance(action_id, ObjectId):
        action_id = str(action_id)
    else:
        pass
    assert isinstance(action_id, (str, unicode)), (type(action_id), action_id)
    assert '.' not in action_id, action_id
    return action_id


def get_models_maps():
    global _in_memory_model_cache
    if not hasattr(_in_memory_model_cache, 'map'):
        _in_memory_model_cache.map = {}
    return _in_memory_model_cache.map


class ScikitBasedClassifier():

    def __init__(self, predictor_model):
        model_type = predictor_model.model_type
        self.predictor_model = predictor_model
        if model_type not in [DISJOINT, HYBRID, GLOBAL]:
            self.model_type = DISJOINT
        else:
            self.model_type = model_type

        if not get_models_maps().get(self.predictor_model.id):
            self.refresh_local_models()
        else:
            self._model_cache = get_models_maps()[self.predictor_model.id]
        # if this model has zero local models, then
        # lets reset it so this model will have at least
        # GLOBAL model
        if 0 == len(self._model_cache):
            self.reset_model()

    def score(self, context_vector, action_vector_list):
        # print "WE'RE USING A MODEL OF TYPE: %s THAT IS ALSO %s" % (self.model, self.model_type)
        result = []
        for action in action_vector_list:
            action_id = action[ACTION_ID]

            score = [action_id, 0.0, 0.0]
            n_predictions = 0
            if self.model_type in (GLOBAL, HYBRID):
                # Use global model for one prediction
                global_score = self.predict_proba(self._model_cache[GLOBAL_KEY], [context_vector + action[KEY_DATA]])
                score[1] += global_score
                score[2] += global_score
                n_predictions += 1

            if self.model_type in (HYBRID, DISJOINT):
                # Add local model prediction if we have a model for this action id
                if action_id in self._model_cache:
                    # try:
                    local_score = self.predict_proba(self._model_cache[action_id], [context_vector + action[KEY_DATA]])
                    score[1] += local_score
                    score[2] += local_score
                    n_predictions += 1
                    # except Exception, ex:
                        # LOGGER.error("Failed scoring with local model. Error: " + str(ex))
                else:
                    global_score = self.predict_proba(self._model_cache[GLOBAL_KEY], [context_vector + action[KEY_DATA]])
                    score[1] += global_score
                    score[2] += global_score
                    n_predictions += 1
            if n_predictions != 0:
                result.append((score[0], score[1] / n_predictions, score[2] / n_predictions))
        return result


    def batched_read(self, predictor, query, sample_rate, batch_size, batch_idx,
                     test_samples=None, test_split_size=1):
        from random import random
        context_list = []
        action_id_list = []
        reward_list = []
        
        # Make sure to load up all non volatile keys in local storage so we avoid lookups on
        # abstract fields for each individual item that we're processing from the dataset.
        F = predictor.training_data_class.F
        context_key = F.context
        action_key = F.action
        reward_key = F.reward
        cardinalities = predictor.cardinalities
        min_integer_values = predictor.min_integer_values
        CTX_PREFIX = predictor.CTX_PREFIX
        ACT_PREFIX = predictor.ACT_PREFIX
        action_model = predictor.action_model
        context_model = predictor.context_model

        if batch_size is None and batch_idx is None:
            data_batch = predictor.training_data_class.objects.coll.find(query)
        else:
            data_batch = predictor.training_data_class.objects.coll.find(query
                )[batch_idx * batch_size:(batch_idx + 1) * batch_size]
        for data in data_batch:
        # for data in predictor.training_data_class.objects.coll.find(query
        #     ).skip(batch_idx * batch_size).limit(batch_size):
                feeling_lucky = random()
                if sample_rate != -1:
                    if feeling_lucky <= sample_rate:
                        # Skip so that we don't overflow memory
                        continue
                context = data[context_key]
                action = data[action_key]
                reward = data[reward_key]
                prefixed_context = dict()
                for key, val in context.iteritems():
                    feat_key = CTX_PREFIX + key
                    if feat_key not in cardinalities or not cardinalities[feat_key]:
                        # No data for it anyway, we can't use it for anything.
                        continue
                    if not type(val) in (int, long, float):
                        prefixed_context[feat_key] = val
                    else:
                        if feat_key not in min_integer_values:
                            min_integer_values[feat_key] = min(cardinalities.get(feat_key, [None]))
                        min_value = min_integer_values[feat_key]
                        if min_value is not None and min_value <= 0:
                            val += abs(min_value) + 1
                        prefixed_context[feat_key] = int(np.log(val))
                prefixed_action = dict()
                for key, val in action.iteritems():
                    feat_key = ACT_PREFIX + key
                    if feat_key not in cardinalities or not cardinalities[feat_key]:
                        # No data for it anyway, we can't use it for anything.
                        continue
                    if not type(val) in (int, long, float):
                        prefixed_action[feat_key] = val
                    else:
                        if feat_key not in min_integer_values:
                            min_integer_values[feat_key] = min(cardinalities.get(feat_key, [None]))
                        min_value = min_integer_values[feat_key]
                        if min_value is not None and min_value <= 0:
                            val += abs(min_value) + 1
                        prefixed_action[feat_key] = int(np.log(val))
                filtered_action = action_model(prefixed_action).vec
                filtered_context = context_model(prefixed_context).vec
                if test_split_size == -1 and test_samples is not None:
                    test_samples.append((filtered_context, filtered_action, action[ACTION_ID], reward))
                    context_list.append(filtered_context + filtered_action)
                    action_id_list.append(convert_action_id(action[ACTION_ID]))
                    reward_list.append(reward)
                else:
                    if feeling_lucky > test_split_size and test_samples is not None:
                        # This will be a test only entry
                        test_samples.append((filtered_context, filtered_action, action[ACTION_ID], reward))
                    else:
                        context_list.append(filtered_context + filtered_action)
                        action_id_list.append(convert_action_id(action[ACTION_ID]))
                        reward_list.append(reward)
        return context_list, action_id_list, reward_list

    def retrain(self, predictor):
        model = self.predictor_model
        predictor.select_model(model)
        feature_size = predictor.features_space_size(model)
        test_size = float(model.train_data_percentage) / 100
        model.reset_performance_stats()
        new_state = model.state.try_change(action='train')
        from solariat_bottle.settings import get_app_mode
        if new_state is None and get_app_mode() != 'test':
            return

        batch_size = BATCH_SIZE

        max_entries = MAX_DATA_SIZE / feature_size
        max_entries -= max_entries % batch_size

        LOGGER.info("Training with a max size of " + str(max_entries))
        query = dict(predictor_id=predictor.id)
        if model.from_dt:
            query[predictor.training_data_class.created_at.db_field] = {'$gte': model.from_dt}
        if model.to_dt:
            query[predictor.training_data_class.created_at.db_field] = {'$lte': model.to_dt}
        total_count = predictor.train_set_length
        if total_count <= 5000:
            test_size = -1

        test_samples = []
        if self.model_type in (GLOBAL, HYBRID, DISJOINT):
            LOGGER.info("RETRAIN:: Training global model.")
            # Train the global model
            sample_rate = -1
            if total_count > max_entries:
                sample_rate = float(max_entries) / total_count
            context_list = []
            reward_list = []
            n_batches = total_count / batch_size + 1
            start_dt_loop = dt.now()
            n_batch_disctinct_values = predictor.training_data_class.objects.coll.distinct('nbch')
            n_batches = len(n_batch_disctinct_values)
            LOGGER.info("RETRAIN:: global model batches size: %s; total batches: %s" % (batch_size, n_batches))
            for i in xrange(len(n_batch_disctinct_values)):
                LOGGER.info("RETRAIN: Global model. Reading batch %s of size %s; total distinct n_batches vals: %s" % (i, 'UNKNOWN', len(n_batch_disctinct_values)))
                start_dt = dt.now()
                n_batch_value = random.choice(n_batch_disctinct_values)
                n_batch_disctinct_values.remove(n_batch_value)
                n_batch_disctinct_values_len = len(n_batch_disctinct_values)
                query[predictor.training_data_class.n_batch.db_field] = n_batch_value
                batch_contexts, batch_actions, batch_rewards = self.batched_read(
                    predictor, query, sample_rate,
                    batch_size=None,
                    batch_idx=None,
                    test_samples=test_samples,
                    test_split_size=test_size)
                LOGGER.info("RETRAIN: Global model. read n_batch: %s (%s), batch size: %s, timedelta: %s, accumulative timedelta: %s",
                    n_batch_value, n_batch_disctinct_values_len, len(batch_contexts), dt.now()-start_dt, dt.now()-start_dt_loop)
                context_list.extend(batch_contexts)
                reward_list.extend(batch_rewards)

                context_list_len = len(context_list)
                if context_list_len / (1.0 if self.model_type != HYBRID else 2.0) >= total_count:
                    if new_state:
                        model.update(state=new_state,
                                     version=(model.version or 0) + 1)
                    model.n_rows = total_count
                predictor.save_progress(model, context_list_len / (1.0 if self.model_type != HYBRID else 2.0),
                                        total_count)

                LOGGER.info("RETRAIN: context_list len: %s", len(context_list))
                # if we reached max_entries limit lets cut the tail and break the loop
                if len(context_list) >= max_entries:
                    context_list = context_list[:max_entries]
                    reward_list = reward_list[:max_entries]
                    break
            LOGGER.info("RETRAIN:: Done with reading, Timedelta: %s.", dt.now()-start_dt_loop)

            start_dt = dt.now()
            LOGGER.info("RETRAIN:: context_list len: %s, reward_list len: %s", len(context_list), len(reward_list))
            LOGGER.info("Training global model now...")
            # sorted() calls is an overhead, but let do it
            # so we can be sure that two global models trained on the same data 
            # will be identical
            self.fit_local_model(GLOBAL_KEY, sorted(context_list), sorted(reward_list))
            LOGGER.info("RETRAIN:: Trained global model; Timedelta: %s", dt.now()-start_dt)
            
        del query[predictor.training_data_class.n_batch.db_field]
        if self.model_type in (HYBRID, DISJOINT):
            LOGGER.info("RETRAIN:: Training local models.")
            from collections import defaultdict
            actions = predictor.cardinalities.get(predictor.ACT_PREFIX + predictor.action_id_expression, [])
            local_test_samples = None if test_samples else []
            if total_count >= max_entries:
                ag_batch_size = 100    # 100 agents at a time as a mix between memory and performance
                ag_n_batches = len(actions) / ag_batch_size + 1
            else:
                ag_batch_size = total_count + 1
                ag_n_batches = 1
            start_dt_local_models = dt.now()
            for ag_batch_idx in xrange(ag_n_batches):
                start_dt_batch = dt.now()
                LOGGER.info("RETRAIN:: Training agents numbers %s of size %s (ag_n_batches: %s)",  str(ag_batch_idx), str(ag_batch_size), ag_n_batches)
                action_batch = actions[ag_batch_idx * ag_batch_size: (ag_batch_idx + 1) * ag_batch_size]
                query['act_id'] = {'$in': [str(action_id) for action_id in action_batch]}
                total_count = predictor.train_set_length
                sample_rate = -1
                if total_count > max_entries:
                    sample_rate = float(max_entries) / total_count
                batch_size = BATCH_SIZE
                n_batches = total_count / batch_size + 1
                action_mappings = defaultdict(list)
                reward_mappings = defaultdict(list)

                start_dt_loop = dt.now()
                for batch_idx in xrange(n_batches):
                    start_dt_batch_iter = dt.now()
                    LOGGER.info("RETRAIN: Reading data batch nr %s (%s) of size %s", batch_idx, n_batches, batch_size)
                    batch_contexts, batch_actions, batch_rewards = self.batched_read(predictor, query, sample_rate,
                                                                                     batch_size, batch_idx,
                                                                                     local_test_samples, test_size)
                    for idx in xrange(len(batch_actions)):
                        action_mappings[batch_actions[idx]].append(batch_contexts[idx])
                        reward_mappings[batch_actions[idx]].append(batch_rewards[idx])
                    LOGGER.info("RETRAIN: timedelta: %s", dt.now()-start_dt_batch_iter)
                    LOGGER.info("RETRAIN: accumulative timedelta: %s", dt.now()-start_dt_batch)
                LOGGER.info("RETRAIN:: Done reading batches for ag_batch_idx %s / %s batch size: %s; timedelta: %s", 
                    ag_batch_idx, ag_n_batches, ag_batch_size, dt.now()-start_dt_loop
                )

                action_mapping_len = len(action_mappings)
                start_dt_loop = dt.now()
                for i, action_id in enumerate(action_mappings.keys()):
                    if (action_id not in self._model_cache and
                        model.class_validity_check(reward_mappings[action_id], model.min_samples_thresould)
                    ):
                        self.add_local_model(action_id, self.get_model_instance(**self.predictor_model.configuration))
                        LOGGER.info("RETRAIN: Fitting model for action: %s; %s out of %s", str(action_id), i, action_mapping_len)
                        start_dt = dt.now()
                        self.fit_local_model(action_id, action_mappings[action_id], reward_mappings[action_id])
                        LOGGER.info("RETRAIN: Action fit_local_model() call: %s; loop timedelta: %s", dt.now() -start_dt, dt.now()-start_dt_batch)
                        LOGGER.info("RETRAIN: Training set size used: %s", self._model_cache[action_id].n_samples)
                    else:
                        LOGGER.warning("RETRAIN: Skipping training for individual model %s since no data is available for classes" %
                        action_id)
                LOGGER.info("RETRAIN:: Trained all models for crnt agent batch (%s of %s). Timedelta %s; Len: %s", 
                    ag_batch_idx, ag_n_batches, dt.now()-start_dt_loop, start_dt_loop)
                LOGGER.info("RETRAIN:: predictor_model configuration: %s", self.predictor_model.configuration)
                if self.model_type == HYBRID:
                    if total_count / 2.0 + batch_size * (batch_idx + 1) / 2.0 >= total_count:
                        if new_state:
                            model.update(state=new_state,
                                         version=(model.version or 0) + 1)
                        model.n_rows = total_count
                    predictor.save_progress(model, total_count / 2.0 + batch_size * (batch_idx + 1) / 2.0, total_count)
                else:
                    if batch_size * (batch_idx + 1) >= total_count:
                        if new_state:
                            model.update(state=new_state,
                                         version=(model.version or 0) + 1)
                        model.n_rows = total_count
                    predictor.save_progress(model, batch_size * (batch_idx + 1), total_count)
                LOGGER.info("RETRAIN:: Done handling agent batch %s / %s (batch_size %s); Timedelta: %s",
                        ag_batch_idx, ag_n_batches, batch_size, dt.now() - start_dt_batch
                    )
            LOGGER.info("RETRAIN:: Done with local models: %s", dt.now() - start_dt_local_models)
        test_samples = test_samples or local_test_samples

        import math
        from solariat_bottle.db.predictors.base_predictor import TYPE_NUMERIC, TYPE_BOOLEAN,\
            mean_squared_error, auc, roc_curve 

        LOGGER.info("Computing performance metrics")
        y = []
        y_pred = []

        start_dt_metrics = dt.now()
        LOGGER.info("RETRAIN:: starting to compute metrics, len: %s", len(test_samples))
        for context, action, action_id, reward in test_samples:
            predicted_score = self.score(context, [{KEY_DATA: action, ACTION_ID: action_id}])
            y_pred.append(predicted_score[0][1])
            # print str(predicted_score) + " WAS PREDICTED"
            if predictor.reward_type == TYPE_NUMERIC:
                y.append(reward)
                predicted_score = predicted_score[0][1]
                reward_diff = abs(reward - float(predicted_score))
                model.avg_error = (model.avg_error * float(model.nr_scores) + reward_diff) / (model.nr_scores + 1)
                model.nr_scores += 1
            elif predictor.reward_type == TYPE_BOOLEAN:
                y.append(1.0 if reward is True else 0.0)
                predicted_score = predicted_score[0][1]
                if reward and float(predicted_score) > 0.5:
                    model.true_positives += 1
                elif reward and float(predicted_score) < 0.5:
                    model.false_negatives += 1
                elif not reward and float(predicted_score) > 0.5:
                    model.false_positives += 1
                else:
                    model.true_negatives += 1
        LOGGER.info("RETRAIN:: iterated over test_samples, Timedelta: %s", dt.now()-start_dt_metrics)
        start_dt_metrics = dt.now()
        if predictor.reward_type == TYPE_BOOLEAN:
            fpr, tpr, thresholds = roc_curve(y, y_pred)
            _score = "%.2f" % auc(fpr, tpr)
            model.auc = float(_score)
            LOGGER.info("RETRAIN:: auc: %s", model.auc)
        elif predictor.reward_type == TYPE_NUMERIC:
            model.mse = mean_squared_error(y, y_pred)
            model.mae = metrics.mean_absolute_error(y, y_pred)
            model.r2_score = metrics.r2_score(y, y_pred)
            _score = "%.2f" % math.sqrt(model.mse)
            model.rmse = float(_score)
            model.fraction_below_quantile = (np.array(y) < np.array(y_pred)).mean()
            LOGGER.info("RETRAIN:: rmse: %s", model.rmse)
            LOGGER.info("RETRAIN:: mse: %s", model.mse)
            LOGGER.info("RETRAIN:: fraction_below_quantile: %s", model.fraction_below_quantile)

        model.save()
        LOGGER.debug("RETRAIN:: Done computing performance metrics, Timedelta: %s", dt.now()-start_dt_metrics)

        # reseting in memory predictor model cache
        get_models_maps()[model.id] = self._model_cache

    def feedback(self, context_vectors, action_vectors, rewards):
        assert len(context_vectors) == len(action_vectors) == len(rewards)
        individual_model_data = {GLOBAL_KEY: dict(contexts=[], values=[])}
        for fdback_idx in xrange(len(context_vectors)):
            action_id = action_vectors[fdback_idx][ACTION_ID]
            if action_id not in individual_model_data:
                individual_model_data[action_id] = dict(contexts=[], values=[])
            current_context = context_vectors[fdback_idx]
            current_context.extend(action_vectors[fdback_idx][KEY_DATA])
            current_reward = rewards[fdback_idx]
            individual_model_data[action_id]['contexts'].append(current_context)
            individual_model_data[action_id]['values'].append(current_reward)

            if self.model_type in (GLOBAL, HYBRID):
                individual_model_data[GLOBAL_KEY]['contexts'].append(current_context)
                individual_model_data[GLOBAL_KEY]['values'].append(current_reward)

        if self.model_type in (GLOBAL, HYBRID):
            self.fit_local_model(GLOBAL_KEY, individual_model_data[GLOBAL_KEY]['contexts'],
                                       individual_model_data[GLOBAL_KEY]['values'])
        if self.model_type in (HYBRID, DISJOINT):
            for action_id in individual_model_data.keys():
                if (action_id not in self.model and
                    self.class_validity_check(individual_model_data[action_id]['values'], model.min_samples_thresould)
                ):
                    self.add_local_model(action_id, self.get_model_instance(**self.kwargs))
                    self.fit_local_model(action_id, individual_model_data[action_id]['contexts'],
                                              individual_model_data[action_id]['values'])
                else:
                    print "Skipping training for individual model since no data is available for classes"

    def get_model_instance(self, **kwargs):
        return self._get_model_instance(**kwargs)

    def add_local_model(self, action_id, model_instance):
        assert '.' not in action_id, action_id
        local_model = LocalModel(
            account=self.predictor_model.predictor.account,
            action_id=str(action_id),
            predictor_model=self.predictor_model,
            packed_clf=pack_object(model_instance),
            n_samples=-1)
        self._model_cache[action_id] = local_model

    def fit_local_model(self, action_id, data, rewards):
        self._model_cache[action_id].fit_local_model(data, rewards)
        self._model_cache[action_id].n_samples = len(data)

    def refresh_local_models(self):
        local_models = LocalModel.objects(predictor_model=self.predictor_model)[:]
        self._model_cache = {}
        for lm in local_models:
            self._model_cache[lm.action_id] = lm
        get_models_maps()[self.predictor_model.id] = self._model_cache

    def reset_model(self):
        LocalModel.objects.remove(predictor_model=self.predictor_model)
        model_instance = self.get_model_instance(**self.predictor_model.configuration)
        local_model = LocalModel(
            account=self.predictor_model.predictor.account,
            action_id=GLOBAL_KEY,
            predictor_model=self.predictor_model,
            packed_clf=pack_object(model_instance),
            n_samples=-1
        )
        self._model_cache = {GLOBAL_KEY: local_model}
        get_models_maps()[self.predictor_model.id] = self._model_cache

    def get_local_model(self, action_id, force_refresh=False):
        if force_refresh or action_id not in self._model_cache:
            return LocalModel.objects.get(predictor_model=self.predictor_model, action_id=action_id)
        else:
            return self._model_cache[action_id]


class PassiveAggresiveRegressor(ScikitBasedClassifier):

    model_class = linear_model.LinearRegression

    def _get_model_instance(self, **kwargs):
        return self.model_class(**kwargs)

    def predict_proba(self, model, context_vector):
        return model.predict(context_vector)


class PassiveAggresiveClassifier(ScikitBasedClassifier):

    model_class = linear_model.LogisticRegression

    def _get_model_instance(self):
        return self.model_class(C=0.1, fit_intercept=False)

    def class_validity_check(self, values, min_samples_thresould):
        return len(set(values)) > 1

    def predict_proba(self, model, context_vector):
        predicted_probs = list(model.predict_proba(context_vector))
        predicted_class = model.predict(context_vector)[0]
        if predicted_class:
            # Highest probability was for class 'True'
            return max(predicted_probs[0])
        else:
            # Highest probability was for class 'False'
            return min(predicted_probs[0])


class QuantileGradentBoostingRegressor(ScikitBasedClassifier):

    model_class = GradientBoostingRegressor

    def _get_model_instance(self, **kwargs):
        return self.model_class(**kwargs)
        # return self.model_class(n_estimators=100, loss='quantile',
        #                         alpha=0.5, learning_rate=0.1,
        #                         max_depth=6, random_state=42)

    def predict_proba(self, model, context_vector):
        return model.predict(context_vector)[0]


class QuantileGradientBoostingClassifier(ScikitBasedClassifier):

    model_class = GradientBoostingClassifier

    def _get_model_instance(self, **kwargs):
        # return self.model_class(n_estimators=100, learning_rate=0.1, max_depth=6)
        return self.model_class(**kwargs)

    def predict_proba(self, model, context_vector):
        predicted_probs = list(model.predict_proba(context_vector))
        if True not in list(model.clf.classes_):
            raise Exception("Non boolean classes for a boolean predictor " + str(model.clf.classes_))
        class_idx = list(model.clf.classes_).index(True)
        return predicted_probs[0][class_idx]

