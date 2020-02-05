# TODO: All this needs to be deprecated
# from solariat_bottle.db.post.web_clicks import WebClick
# from solariat_bottle.db.post.chat import ChatPost
# from solariat_bottle.db.post.faq_query import FAQQueryEvent
#
# from solariat.db import fields
#
# from solariat_bottle.settings import LOGGER
# from solariat_bottle.db.auth import AuthDocument
# from solariat_bottle.db.channel_filter import ClassifierMixin
# from solariat_nlp.bandit.models import (
#     SUPERVISOR_ALERT_CONFIGURATION, CHAT_OFFER_CONFIGURATION)
#
# INITIALIZATION_CACHE = {}
#
#
# class NextBestActionEngine(AuthDocument, ClassifierMixin):
#
#     account_id = fields.ObjectIdField()
#     #
#     @classmethod
#     def upsert(cls, account_id):
#         from solariat_bottle.db.predictors import ChatEngagementDecision
#         from solariat_bottle.db.predictors import AlertSupervisorDecision
#         try:
#             return cls.objects.get(account_id=account_id)
#         except cls.DoesNotExist:
#             engine = cls.objects.create(account_id=account_id)
#             configuration = CHAT_OFFER_CONFIGURATION
#             ChatEngagementDecision.objects.create(account_id=account_id,
#                                                   name="Chat Engagement",
#                                                   configuration=CHAT_OFFER_CONFIGURATION)
#             AlertSupervisorDecision.objects.create(account_id=account_id,
#                                                    name="Supervisor Alert",
#                                                    configuration=SUPERVISOR_ALERT_CONFIGURATION)
#             return engine
#
#     @property
#     def classifier_class(self):
#         "So we can easily plugin other classifier classes if we want."
#         from solariat_bottle.db.predictors.classifiers import AgentMatchingUCB
#         return AgentMatchingUCB
#
#     def get_decision_engine(self, event):
#         from solariat_bottle.db.predictors import ChatEngagementDecision
#         from solariat_bottle.db.predictors import AlertSupervisorDecision
#         try:
#             if isinstance(event, WebClick) or isinstance(event, FAQQueryEvent):
#                 return ChatEngagementDecision.objects.get(account_id=self.account_id)
#             elif isinstance(event, ChatPost):
#                 return AlertSupervisorDecision.objects.get(account_id=self.account_id)
#         except ChatEngagementDecision.DoesNotExist:
#             pass
#
#     def feedback(self, event, customer, action, reward=None, model=None):
#         from solariat_nlp.bandit.models import (
#                 CUSTOMER_AGE, CUSTOMER_SEX, CUSTOMER_SENIORITY, EVENT_TAGS
#         )
#         from solariat_nlp.bandit.linucb import ACTION_ID
#         decision_engine = self.get_decision_engine(event)
#         if decision_engine:
#             customer_vector = {CUSTOMER_AGE: customer.get_age(),
#                                CUSTOMER_SEX: customer.sex,
#                                CUSTOMER_SENIORITY: customer.seniority,
#                                'id': customer.id}
#             action_vector = {ACTION_ID: str(action.id)}
#             return decision_engine.feedback(event, customer_vector, action_vector, reward, model=model)
#
#         LOGGER.error("No decision engine found for event=%s and customer=%s" % (event, customer))
#         return {'error': "No decision engine found for event=%s and customer=%s" % (event, customer)}
#
#     def search(self, event, customer, model=None):
#         from solariat_nlp.bandit.models import (
#                 CUSTOMER_AGE, CUSTOMER_SEX, CUSTOMER_SENIORITY
#         )
#         decision_engine = self.get_decision_engine(event)
#         if decision_engine:
#             customer_vector = {CUSTOMER_AGE: customer.get_age(),
#                                CUSTOMER_SEX: customer.sex,
#                                CUSTOMER_SENIORITY: customer.seniority,
#                                'id': customer.id}
#             return decision_engine.search(event, customer_vector, model=model)
#         LOGGER.error("No decision engine found for event=%s and customer=%s" % (event, customer))
#         return {'error': "No decision engine found for event=%s and customer=%s" % (event, customer)}
