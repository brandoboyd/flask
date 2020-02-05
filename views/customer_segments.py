# #from flask import request
# #from solariat.db import fields
# from solariat_bottle.app import app
# #from solariat_bottle.settings import LOGGER
# #from solariat_bottle.utils.views import parse_account, get_paging_params
# #from solariat_bottle.utils.request import _get_request_data
# from solariat_bottle.views.journey.journey_tag import JourneyTagView
# from solariat_bottle.db.predictors.customer_segment import CustomerSegment
# from solariat_bottle.api.exceptions import ValidationError
#
#
# class CustomerSegmentView(JourneyTagView):
#     url_rules = [
#             ('/api/customer_segments', ['GET', 'POST']),
#             ('/api/customer_segments/<id_>', ['GET', 'POST', 'PUT', 'DELETE']),
#     ]
#
#     @property
#     def model(self):
#         return CustomerSegment
#
#     @property
#     def valid_parameters(self):
#         return ['id', 'display_name', 'description', 'locations', 'age_range', 'account_balance_range', 'num_calls_range']
#
#     def check_duplicate_display_name(self, **filters):
#         id_ = filters.get('id_', filters.get('id'))
#         duplicate = False
#         if 'display_name' in filters:
#             for obj in self.manager.find_by_user(
#                     self.user,
#                     display_name=filters['display_name']):
#                 if obj.id != id_:
#                     duplicate = True
#         if duplicate:
#             raise ValidationError(u"{m.__name__} with name '{display_name}' already exists".format(m=self.model, **filters))
#
#
# CustomerSegmentView.register(app)
