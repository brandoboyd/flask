# from datetime import datetime
#
# from solariat.utils.timeslot import datetime_to_timestamp
#
# from solariat_bottle.db.channel.base import Channel
# from solariat_bottle.db.events.event import Event, EventManager
# from solariat_bottle.db.user_profiles.nps_entity_profile import NPSEntityProfile
# from solariat_bottle.utils.predictor_events import read_schema, translate_column
# from solariat_bottle.utils.id_encoder import pack_components
#
#
# class NPSEventManager(EventManager):
#
#     def create_by_user(self, user, **kw):
#         """
#         :param user: GSA user whose credentials were used to create a new WebClick object
#         :param kw: Any WebClick specific data
#         :return:
#         """
#         channel = kw['channels'][0]
#         channel = channel if isinstance(channel, Channel) else Channel.objects.get(id=channel)
#         if 'actor_id' not in kw:
#             phone = kw.get('CUSTOMER_HOME_PHONE')
#             profile = NPSEntityProfile.objects.create_by_user(user,
#                                                               account=channel.account,
#                                                               phone=phone)
#             kw['actor_id'] = profile.customer_profile.id
#
#         if 'safe_create' in kw:
#             kw.pop('safe_create')
#         kw['is_inbound'] = False
#
#         for field in kw.keys():
#             if field not in NPSEvent.fields:
#                 del kw[field]
#
#         e_id = NPSEvent.make_id(kw)
#
#         try:
#             event = self.get(e_id)
#             return event
#         except NPSEvent.DoesNotExist:
#             kw['_id'] = e_id
#             event = NPSEventManager.create(self,  **kw)
#
#             # from solariat_bottle.db.predictors.factory import get_or_create, TRANSFER_RATE_PREDICTOR
#             # i_mart_predictor = get_or_create(TRANSFER_RATE_PREDICTOR, str(channel.account.id))
#             # i_mart_predictor.feedback(event.data,
#             #                           dict(action_id=event.EMPLOYEE_ID),
#             #                           event.was_transfer())
#
#             return event
#
#
# class NPSEvent(Event):
#
#     meta_schema = read_schema('anonymized_nps')
#
#     manager = NPSEventManager
#
#     PROFILE_CLASS = NPSEntityProfile
#
#     @staticmethod
#     def parse_ts(input_ts):
#         '2016-03-16 21:23:06'
#         return datetime.strptime(input_ts, '%d-%m-%y')
#
#     @classmethod
#     def make_id(cls, kw):
#         from_ts = datetime_to_timestamp(NPSEvent.parse_ts(kw['START_TS']))
#         itx_id = long(kw['INTERACTION_ID'])
#         return pack_components((itx_id, 29), (from_ts, 34))
#
#     @classmethod
#     def patch_post_kw(cls, kw):
#         pass
#
#     @property
#     def platform(self):
#         return 'NPS'
#
#     @property
#     def post_type(self):
#         return 'private'
#
#     @property
#     def _message_type(self):
#         return 1
#
#     @property
#     def view_url_link(self):
#         return "View the Comment"
#
#     def nps_score(self):
#         return self.data[translate_column('Likelihood to recommend to friends / family_06c-08c961b30b1a')]
#
#     def to_dict(self, fields2show=None):
#         base_dict = super(NPSEvent, self).to_dict()
#         base_dict['actor'] = self.actor.to_dict()
#         return base_dict
#
