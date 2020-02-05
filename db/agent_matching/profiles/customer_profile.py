# from solariat.db import fields
#
# from solariat_bottle.settings import LOGGER
# from solariat_bottle.db.agent_matching.profiles.base_profile import BaseProfile
# from solariat_bottle.db.sequences import NumberSequences
#
#
# class CustomerProfile(BaseProfile):
#
#     collection = 'CustomerProfile'
#
#     last_call_intent = fields.ListField(fields.StringField())
#     num_calls = fields.NumField()
#     account_balance = fields.NumField()
#     assigned_segments = fields.ListField(fields.ObjectIdField())
#     frequency = fields.NumField()
#     phone = fields.StringField()
#     status = fields.StringField()
#     industry = fields.StringField()
#     case_number = fields.StringField()  # In case NPS survey was completed
#
#     def refresh_segments(self):
#         from solariat_bottle.db.predictors.customer_segment import CustomerSegment, CustomerMultiSegment
#         self.assigned_segments = []
#         self.save()
#         assigned_segments = []
#         for segment in CustomerMultiSegment.objects(account_id=self.account_id):
#             is_match, option = segment.match(self)
#             if is_match:
#                 assigned_segments.append(option.id)
#         for segment in CustomerSegment.objects(account_id=self.account_id, is_multi=False):
#             if segment.match(self):
#                 assigned_segments.append(segment.id)
#         self.assigned_segments = assigned_segments
#         self.save()
#
#     def remove_segment(self, segment):
#         if segment in self.assigned_segments:
#             self.assigned_labels.remove(segment)
#         self.save()
#
#     def add_segment(self, segment):
#         if segment not in self.assigned_segments:
#             self.assigned_labels.append(segment)
#         self.save()
#
#     def to_dict(self, fields_to_show=None):
#         from solariat_bottle.db.predictors.customer_segment import CustomerSegment
#
#         base_dict = super(BaseProfile, self).to_dict(fields_to_show=fields_to_show)
#         base_dict.pop('assigned_labels', None)
#         base_dict['assigned_segments'] = [segment.display_name for segment in CustomerSegment.objects.cached_find_by_ids(self.assigned_segments)]
#         return base_dict
#
#     def construct_matching_query(self):
#         terms_constraint = [
#                             {'terms': {'skillset': [str(self.last_call_intent)]}},
#                             {'term': {'occupancy': False}}
#         ]
#
#         soft_constraint = [{'terms': {'skillset': [str(self.last_call_intent)]}}]
#         return {'filtered': {'filter': {'and': terms_constraint},
#                                        'query': {'bool': {'should': soft_constraint,
#                                                           'minimum_number_should_match': 1}
#                                        }
#                             }
#                }
#
#     def check_defined_rule(self, rule_string, default=False):
#         func_locals = locals()
#         func_locals.update(self.to_dict()) # pass
#         if rule_string:
#             try:
#                 import numexpr as ne
#
#                 return bool(ne.evaluate(rule_string, local_dict=func_locals))
#             except Exception, ex:
#                 LOGGER.warning("Got exception while parsing rule %s. Error: %s" % (rule_string, ex))
#                 return default
#         return default
#
#     def refresh_intent(self):
#         from solariat_bottle.db.events.event import Event
#         latest_events = Event.objects.customer_history(self)
#         all_tags = []
#         for event in latest_events:
#             all_tags.extend([t.display_name for t in event.event_tags])
#         self.last_call_intent = list(set(all_tags))
#         self.save()
#
#     @classmethod
#     def get_default_profile(cls):
#         profile = CustomerProfile(
#             first_name='John',
#             last_name='Joe',
#             age=35,
#             sex='M',
#             location='san francisco',
#             seniority=None,
#             assigned_labels=[],
#             date_of_birth='01/01/1980',
#             attached_data={},
#             last_call_intent=None,
#             num_calls=0,
#             account_balance=0,
#             assigned_segments=[],
#             frequency=None,
#             phone=None,
#         )
#         return profile
#
#
