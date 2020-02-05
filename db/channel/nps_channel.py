# from .base import ChannelManager, Channel
#
#
# class NPSEventManager(ChannelManager):
#
#     def create(self, **kw):
#         kw.update(dict(adaptive_learning_enabled=False))
#         return super(NPSEventManager, self).create(**kw)
#
#
# class NPSChannel(Channel):
#
#     manager = NPSEventManager
#
#     @property
#     def type_name(self):
#         return "NPS"
#
#     @property
#     def platform(self):
#         return "NPS"
