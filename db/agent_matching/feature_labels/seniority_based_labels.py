# from solariat_bottle.db.agent_matching.feature_labels.base_profile_label import BaseProfileLabel
#
#
# class SeniorityMixin():
#
#     def match(self, profile):
#         if profile.seniority == self.display_name:
#             return True
#         return BaseProfileLabel.match(self, profile)
#
#     def initialize(self, account_id):
#         for (idx, value) in enumerate(self.SENIORITY_VALUES):
#             self.objects.get_or_create(account_id=account_id,
#                                        display_name=value,
#                                        _feature_index=idx)
#
#
# class AgentSeniorityLabels(SeniorityMixin, BaseProfileLabel):
#
#     SENIORITY_VALUES = ['JUNIOR', 'EXPERIENCED', 'SENIOR']
#
#
# class CustomerSeniorityLabels(SeniorityMixin, BaseProfileLabel):
#
#     SENIORITY_VALUES = ['NEW', 'REGULAR', 'VIP']