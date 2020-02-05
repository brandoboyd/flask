# from solariat.db import fields
#
# from solariat_bottle.db.agent_matching.feature_labels.base_profile_label import BaseProfileLabel
#
#
# class SubscriptionCountMixin():
#
#     min_subscriptions = fields.NumField(default=0)
#     max_subscriptions = fields.NumField(default=0)
#
#     def match(self, profile):
#         if hasattr(profile, 'num_calls'):
#             if profile.num_calls and (self.min_subscriptions < profile.num_calls <= self.max_subscriptions):
#                 return True
#         return BaseProfileLabel.match(self, profile)
#
#     def initialize(self, account_id):
#         self.objects.get_or_create(account_id=account_id,
#                                    display_name="ONE",
#                                    min_subscriptions=0,
#                                    max_subscriptions=1,
#                                    _feature_index=0)
#         self.objects.get_or_create(account_id=account_id,
#                                    display_name="SOME",
#                                    min_subscriptions=1,
#                                    max_subscriptions=5,
#                                    _feature_index=1)
#         self.objects.get_or_create(account_id=account_id,
#                                    display_name="MANY",
#                                    min_subscriptions=5,
#                                    max_subscriptions=50000,
#                                    _feature_index=2)
#
#
# class SubscriptionCountLabel(SubscriptionCountMixin, BaseProfileLabel):
#     pass
#
#
