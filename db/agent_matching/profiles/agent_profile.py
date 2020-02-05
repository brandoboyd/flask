# from solariat import elasticsearch as es
# from solariat.db import fields
#
# from solariat_bottle.db.auth import AuthManager
# from solariat_bottle.db.agent_matching.profiles.base_profile import BaseProfile
# from solariat_bottle.db.filters import FilterTranslator
#
#
# class AgentCollection(es.ElasticCollection):
#     """ ES collection for storing agents """
#     def __init__(self):
#         es.ElasticCollection.__init__(self, 'matching', 'agent')
#         self.set_mapping()
#
#     def set_mapping(self):
#         """ Will insert or update a document. """
#         import json
#
#         body = {
#         "mappings": {
#             "agent": {
#                 "properties": {
#                     "skillset": {
#                         "type":       "string",
#                         "similarity": "BM25"
#                         },
#                     "age": {
#                         "type":       "string",
#                         "similarity": "BM25"
#                         },
#                     "location": {
#                         "type":       "string",
#                         "similarity": "BM25"
#                         },
#                     "occupancy": {
#                         "type":       "integer",
#                         "similarity": "BM25"
#                         }
#                     }
#                 }
#             }
#         }
#
#         response = self.index.request(url=self.index.base_url,
#                                       method='POST',
#                                       body=json.dumps(body))
#
#         return response
#
#
# class AgentProfileManager(AuthManager):
#
#     def create(self, **kw):
#         """ Automatically deploy for matching once created """
#         agent = AuthManager.create(self, **kw)
#         agent.deploy()
#         return agent
#
#     def create_by_user(self, user, **kw):
#         agent = AuthManager.create_by_user(self, user, **kw)
#         agent.deploy()
#         return agent
#
#     def remove_by_user(self, user, *args, **kw):
#         if args:
#             kw = {'id': args[0]}
#         for agent in AuthManager.find_by_user(self, user, 'w', **kw):
#             agent.withdraw()
#             agent.delete()
#
#     def withdraw(self, *args, **kw):
#         """ Remove agent from active deployment. Will extract from ES."""
#         for agent in self.find(*args, **kw):
#             agent.withdraw()
#         self.model.es_collection.index.refresh()
#
#
# class AgentProfile(BaseProfile):
#
#     collection = 'AgentProfile'
#
#     es_collection = AgentCollection()
#     manager = AgentProfileManager
#
#     skillset = fields.DictField()
#     occupancy = fields.NumField()
#     english_fluency = fields.StringField()
#     date_of_hire = fields.StringField()
#     native_id = fields.StringField()
#     on_call = fields.BooleanField()
#
#     cached_profile_labels = {}
#
#     @staticmethod
#     def translated_filter_query(filter_string):
#         query = FilterTranslator(filter_string, prefix=AgentProfile.attached_data.db_field).get_mongo_query()
#         limit = 1000
#         return list(AgentProfile.objects.coll.find(query).limit(limit)) #[:]
#
#     @staticmethod
#     def construct_filter_query(filter_str):
#         from solariat_bottle.api.agents import DOT_REPLACEMENT_STR
#         filter_str = filter_str.replace('.', DOT_REPLACEMENT_STR)
#         query = FilterTranslator(filter_str, prefix=AgentProfile.attached_data.db_field).get_mongo_query()
#         return query, query
#
#     def to_dict(self, fields_to_show=None):
#         # from solariat_bottle.db.journeys.customer_journey import CustomerJourney
#         base_dict = super(AgentProfile, self).to_dict(fields_to_show=fields_to_show)
#         if self.skillset:
#             base_dict['skillset'] = self.skillset.keys()
#         if self.products:
#             base_dict['products'] = self.products
#         # journeys = list(CustomerJourney.objects.find(agents=self.id))
#         # base_dict['journeys'] = [each.to_dict() for each in journeys]
#         # base_dict['customer_industries'] = [] # Does not make sense to link agents ot industries?
#         return base_dict
#
#     def make_index_entry(self):
#         base_entry = dict(id=str(self.id),
#                           skillset=[str(s_id) for s_id in self.skillset.keys()],  # equivalent of customer intent
#                           account_id=str(self.account_id),
#                           occupancy=self.occupancy)
#         if self.products:
#             base_entry['products'] = self.products
#         if self.age:
#             base_entry['age'] = [str(self.age)]
#         if self.location:
#             base_entry['location'] = [str(self.location)]
#         if self.assigned_labels:
#             base_entry['assigned_labels'] = [str(l_id) for l_id in self.assigned_labels]
#         if self.english_fluency:
#             base_entry['english_fluency'] = str(self.english_fluency)
#         if self.seniority:
#             base_entry['seniority'] = str(self.seniority)
#         return base_entry
#
#     def __put_to_es(self, refresh=True):
#         """Put an encoded form of the document to elastic search"""
#         doc = self.make_index_entry()
#         self.es_collection.put(str(self.id), doc)
#         if refresh:
#             self.es_collection.index.refresh()
#
#     def withdraw(self, refresh=False):
#         self.es_collection.delete(str(self.id))
#         if refresh:
#             self.es_collection.index.refresh()
#
#     def deploy(self, refresh=True):
#         self.__put_to_es(refresh)
#
#     def save(self, update_es=False):
#         super(AgentProfile, self).save()
#         if update_es:
#             self.__put_to_es(refresh=True)
#
#     def delete(self):
#         super(AgentProfile, self).delete()
#         self.es_collection.delete(str(self.id))
#         self.es_collection.index.refresh()
#
