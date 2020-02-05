# from solariat.db import fields
#
# from solariat_bottle.db.agent_matching.feature_labels.base_profile_label import BaseProfileLabel
#
#
# class LocationBasedMixin():
#
#     locations = fields.ListField(fields.StringField())
#
#     def match(self, profile):
#         if profile.location is None:
#             return False
#         if profile.location.lower() in [l.lower() for l in self.locations]:
#             return True
#         return BaseProfileLabel.match(self, profile)
#
#     def initialize(self, account_id):
#         LocationBasedLabel.objects.get_or_create(account_id=account_id,
#                                                  display_name="US-EAST",
#                                                  locations=["san francisco", "san diego", "san jose", "sacramento",
#                                                             "portland", "seattle"],
#                                                  _feature_index=0)
#         LocationBasedLabel.objects.get_or_create(account_id=account_id,
#                                                  display_name="US-WEST",
#                                                  locations=["new york", "philadelphia", "new jersey", "orlando", "miami"],
#                                                  _feature_index=1)
#         LocationBasedLabel.objects.get_or_create(account_id=account_id,
#                                                  display_name="US-CENTRAL",
#                                                  locations=["denver", "albuquerque", "dallas", "austin", "chicago"],
#                                                  _feature_index=2)
#
#
# class LocationBasedLabel(LocationBasedMixin, BaseProfileLabel):
#     pass
#
