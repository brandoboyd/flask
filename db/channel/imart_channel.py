# from .base import ChannelManager, Channel
#
#
# class InfomartManager(ChannelManager):
#
#     def create(self, **kw):
#         kw.update(dict(adaptive_learning_enabled=False))
#         return super(InfomartManager, self).create(**kw)
#
#
# class InfomartChannel(Channel):
#
#     manager = InfomartManager
#
#     @property
#     def type_name(self):
#         return "Infomart Data"
#
#     @property
#     def platform(self):
#         return "Imart"
