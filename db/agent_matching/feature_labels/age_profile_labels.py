# from solariat.db import fields
#
# from solariat_bottle.db.agent_matching.feature_labels.base_profile_label import BaseProfileLabel
#
#
# class AgeBasedMixin():
#
#     min_age = fields.NumField(default=0)
#     max_age = fields.NumField(default=0)
#
#     def match(self, profile):
#         if profile.get_age() and profile.get_age() > self.min_age and profile.get_age() <= self.max_age:
#             return True
#         return BaseProfileLabel.match(self, profile)
#
#     def initialize(self, account_id):
#         AgeBaseLabel.objects.get_or_create(account_id=account_id,
#                                            display_name="UNDERAGED",
#                                            min_age=0,
#                                            max_age=18)
#         AgeBaseLabel.objects.get_or_create(account_id=account_id,
#                                            display_name="YOUNG",
#                                            min_age=18,
#                                            max_age=30)
#         AgeBaseLabel.objects.get_or_create(account_id=account_id,
#                                            display_name="MIDAGE",
#                                            min_age=30,
#                                            max_age=50)
#         AgeBaseLabel.objects.get_or_create(account_id=account_id,
#                                            display_name="OLD",
#                                            min_age=50,
#                                            max_age=200)
#
#
# class AgeBaseLabel(AgeBasedMixin, BaseProfileLabel):
#     pass
#
#
