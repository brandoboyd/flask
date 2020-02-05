# from datetime import datetime
#
# from solariat.utils.timeslot import datetime_to_timestamp
#
# from solariat_bottle.db.channel.base import Channel
# from solariat_bottle.db.events.event import Event, EventManager
# from solariat_bottle.db.user_profiles.revenue_profile import RevenueProfile
# from solariat_bottle.utils.predictor_events import read_schema
# from solariat_bottle.utils.id_encoder import pack_components
#
#
# class RevenueEventManager(EventManager):
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
#             rcs_id = kw.get('X_RCIS_ID')
#             profile = RevenueProfile.objects.create_by_user(user,
#                                                             account=channel.account,
#                                                             rcs_id=rcs_id)
#             kw['actor_id'] = profile.customer_profile.id
#
#         if 'safe_create' in kw:
#             kw.pop('safe_create')
#         kw['is_inbound'] = False
#
#         for field in kw.keys():
#             if field not in RevenueEvent.fields:
#                 del kw[field]
#
#         e_id = RevenueEvent.make_id(kw)
#
#         try:
#             event = self.get(e_id)
#             return event
#         except RevenueEvent.DoesNotExist:
#             kw['_id'] = e_id
#             event = RevenueEventManager.create(self,  **kw)
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
# class RevenueEvent(Event):
#
#     meta_schema = read_schema('anonymized_revenue')
#
#     manager = RevenueEventManager
#
#     PROFILE_CLASS = RevenueProfile
#
#     @staticmethod
#     def parse_ts(input_ts):
#         return datetime.strptime(input_ts, "%m/%d/%Y")
#
#     @classmethod
#     def make_id(cls, kw):
#         from_ts = datetime_to_timestamp(RevenueEvent.parse_ts(kw['Interaction_date']))
#         itx_id = long(kw['MAX_of_session_objid'])
#         return pack_components((itx_id, 29), (from_ts, 34))
#
#     @classmethod
#     def patch_post_kw(cls, kw):
#         pass
#
#     @property
#     def platform(self):
#         return 'Revenue'
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
#     def revenue_value(self):
#         return self.NET_DELTA_EOP_INIT
#
#     def to_dict(self, fields2show=None):
#         base_dict = super(RevenueEvent, self).to_dict()
#         base_dict['actor'] = self.actor.to_dict()
#         return base_dict
#
