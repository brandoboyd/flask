# AGENT MATCHING
from datetime import datetime, timedelta
from solariat_nlp.bandit.linucb import GLOBAL, HYBRID, DISJOINT

from solariat_bottle.db.predictors.base_predictor import BasePredictor, ModelState, LinearPredictor, TYPE_CLASSIFIER, LookupTestPredictor

from solariat_nlp.bandit.models import AGENT_MATCHING_CONFIGURATION
from solariat_nlp.bandit.models import CHAT_OFFER_CONFIGURATION
from solariat_nlp.bandit.models import SUPERVISOR_ALERT_CONFIGURATION
from solariat_nlp.bandit.models import TRANSFER_RATE_CONFIGURATION, TEST_AGENT_MATCHING_CONFIGURATION



AGENT_MATCHING_PREDICTOR = 'Agent Matching Predictor'
AGENT_MATCHING_PREDICTOR_TEST = 'Test Agent Matching Predictor'
CHAT_ENGAGEMENT_PREDICTOR = 'Chat Engagement Predictor'
SUPERVISOR_ALERT_PREDICTOR = 'Supervisor Alert Predictor'
TRANSFER_RATE_PREDICTOR = 'Transfer Rate Predictor'

CONFIG = {
    AGENT_MATCHING_PREDICTOR: AGENT_MATCHING_CONFIGURATION,
    AGENT_MATCHING_PREDICTOR_TEST: TEST_AGENT_MATCHING_CONFIGURATION,
    CHAT_ENGAGEMENT_PREDICTOR: CHAT_OFFER_CONFIGURATION,
    SUPERVISOR_ALERT_PREDICTOR: SUPERVISOR_ALERT_CONFIGURATION,
    TRANSFER_RATE_PREDICTOR: TRANSFER_RATE_CONFIGURATION
}


def get(predictor_type, account_id):
    if predictor_type == TRANSFER_RATE_PREDICTOR:
        return LinearPredictor.objects.get(account_id=account_id,
                                           name=predictor_type)
    return BasePredictor.objects.get(account_id=account_id,
                                     name=predictor_type)


def create(predictor_type, account_id, state=None):
    config = CONFIG[predictor_type]
    if predictor_type == TRANSFER_RATE_PREDICTOR:
        predictor = BasePredictor.objects.create(account_id=account_id,
                                                 name=predictor_type,
                                                 metric=config['rewards'][0]['display_name'],
                                                 action_features_schema=config['action_model'],
                                                 context_features_schema=config['context_model'],
                                                 action_id_expression='native_id',
                                                 reward_type=TYPE_CLASSIFIER)
    else:
        predictor = BasePredictor.objects.create(
            account_id=account_id,
            name=predictor_type,
            metric=config['rewards'][0]['display_name'],
            action_features_schema=config['action_model'],
            context_features_schema=config['context_model'],
            action_id_expression='native_id',
            from_dt=datetime(year=2015, month=5, day=1),
            to_dt=datetime(year=2015, month=6, day=1),
        )
    if state is not None and isinstance(state, ModelState):
        for model in predictor.models:
            model.update(state=state)

    return predictor


def get_or_create(predictor_type, account_id, state=None):
    try:
        return get(predictor_type, account_id)
    except BasePredictor.DoesNotExist:
        return create(predictor_type, account_id, state)


def delete(predictor_type, account_id):
    BasePredictor.objects.remove(account_id=account_id,
                                 name=predictor_type)


# shortcuts for compatibility
# AGENT MATCHING
def create_agent_matching_predictor(account_id, state=None, is_test=False):
    if is_test:
        predictor = create(AGENT_MATCHING_PREDICTOR_TEST, account_id, state)
    else:
        predictor = create(AGENT_MATCHING_PREDICTOR, account_id, state)
    # activating all models for AgentMatching predictor
    for mdl in predictor.models:
        mdl.state.status = mdl.state.STATUS_ACTIVE
        mdl.save()
    return predictor


def create_agent_matching_predictor_for_testing(account_id, predictor_id):
    predictor = LookupTestPredictor(account_id=account_id)
    predictor.predictor_id = predictor_id
    predictor.save()
    return predictor


def get_agent_matching_predictor(account_id):
    return get(AGENT_MATCHING_PREDICTOR, account_id)


def delete_agent_matching_predictor(account_id):
    return delete(AGENT_MATCHING_PREDICTOR, account_id)


# CHAT ENGAGEMENT
def create_chat_engagement_predictor(account_id, state=None):
    return create(CHAT_ENGAGEMENT_PREDICTOR, account_id, state)


def get_chat_engagement_predictor(account_id):
    return get(CHAT_ENGAGEMENT_PREDICTOR, account_id)


def delete_chat_engagement_predictor(account_id):
    delete(CHAT_ENGAGEMENT_PREDICTOR, account_id)


# ALERT SUPERVISOR
def create_supervisor_alert_predictor(account_id):
    return create(SUPERVISOR_ALERT_PREDICTOR, account_id)


def get_supervisor_alert_predictor(account_id):
    return get(SUPERVISOR_ALERT_PREDICTOR, account_id)


def delete_supervisor_alert_predictor(account_id):
    return delete(SUPERVISOR_ALERT_PREDICTOR, account_id)
