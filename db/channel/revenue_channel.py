# from .base import ChannelManager, Channel
#
#
# class RevenueManager(ChannelManager):
#
#     def create(self, **kw):
#         kw.update(dict(adaptive_learning_enabled=False))
#         return super(RevenueManager, self).create(**kw)
#
#
# class RevenueChannel(Channel):
#
#     manager = RevenueManager
#
#     @property
#     def type_name(self):
#         return "Revenue"
#
#     @property
#     def platform(self):
#         return "Revenue"
