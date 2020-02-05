# from solariat_bottle.db.agent_matching.feature_labels.base_profile_label import BaseProfileLabel
#
#
# class FluencyMixin():
#
#     def match(self, profile):
#         if not hasattr(profile, 'english_fluency'):
#             return False
#         if profile.english_fluency == self.display_name:
#             return True
#         return BaseProfileLabel.match(self, profile)
#
#     def initialize(self, account_id):
#         for (idx, value) in enumerate(self.FLUENCY_VALUES):
#             self.objects.get_or_create(account_id=account_id,
#                                        display_name=value,
#                                        _feature_index=idx)
#
#
# class EnglishFluencyLabels(FluencyMixin, BaseProfileLabel):
#
#     FLUENCY_VALUES = ['BAD', 'GOOD', 'NATIVE']
#
