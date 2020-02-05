# from solariat.db import fields
#
# from solariat_bottle.db.predictors.abc_predictor import ABCPredictor, ABCMultiClassPredictor
# from solariat_bottle.db.predictors.customer_feature_extractor import CustomerFeatureExtractor
#
#
# class SegmentMixin():
#     display_name = fields.StringField(required=True)
#     description = fields.StringField()
#     account_id = fields.ObjectIdField()     # Specific for an 'omni-channel'
#
#
# class CustomerSegment(ABCPredictor, SegmentMixin):
#     allow_inheritance = True
#     collection = 'CustomerSegment'
#
#     parent_filter = fields.ObjectIdField()
#     is_multi = fields.BooleanField(default=False)
#
#     locations = fields.ListField(fields.StringField())
#     age_range = fields.ListField(fields.NumField())             # [min, max]
#     account_balance_range = fields.ListField(fields.NumField()) # [min, max]
#     num_calls_range = fields.ListField(fields.NumField())       # [min, max]
#
#     indexes = [('account_id', 'is_multi', ), ]
#     feature_extractor = CustomerFeatureExtractor()
#
#     def match(self, customer_profile):
#         assert isinstance(customer_profile, CustomerProfile), "BaseSegments expects CustomerProfile objects"
#         return super(CustomerSegment, self).match(customer_profile)
#
#     def score(self, customer_profile):
#         assert isinstance(customer_profile, CustomerProfile), "BaseSegments expects CustomerProfile objects"
#         return super(CustomerSegment, self).score(customer_profile)
#
#     def accept(self, customer_profile):
#         assert isinstance(customer_profile, CustomerProfile), "BaseSegments expects CustomerProfile objects"
#         customer_profile.add_segment(self.id)
#         return super(CustomerSegment, self).accept(customer_profile)
#
#     def reject(self, customer_profile):
#         assert isinstance(customer_profile, CustomerProfile), "BaseSegments expects CustomerProfile objects"
#         customer_profile.remove_segment(self.id)
#         return super(CustomerSegment, self).reject(customer_profile)
#
#     def check_preconditions(self, customer_profile):
#         if self.locations:
#             if customer_profile.location is None:
#                 return False
#             if not customer_profile.location.lower() in [each.lower() for each in self.locations]:
#                 return False
#
#         if self.age_range and self.age_range != [16, 16]:
#             if customer_profile.age is None:
#                 return False
#             if not (self.age_range[0] <= customer_profile.age <= self.age_range[1]):
#                 return False
#
#         if self.account_balance_range and self.account_balance_range != [1000, 1000]:
#             if customer_profile.account_balance is None:
#                 return False
#             if not (self.account_balance_range[0] <= customer_profile.account_balance <= self.account_balance_range[1]):
#                 return False
#
#         if self.num_calls_range and self.num_calls_range != [0, 0]:
#             if customer_profile.num_calls is None:
#                 return False
#             if not (self.num_calls_range[0] <= customer_profile.num_calls <= self.num_calls_range[1]):
#                 return False
#
#         return True
#
#     def rule_based_match(self, customer_profile):
#         return 1
#
#     def to_dict(self, fields_to_show=None):
#         base_dict = super(CustomerSegment, self).to_dict(fields_to_show)
#         del base_dict['packed_clf']
#         return base_dict
#
#
# class CustomerMultiSegment(ABCMultiClassPredictor, SegmentMixin):
#     collection = 'CustomerMultiSegment'
#     inclusion_threshold = fields.NumField(default=0.25)
