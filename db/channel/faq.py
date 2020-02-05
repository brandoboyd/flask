from .base import ChannelManager, Channel
from solariat.db import fields


class FAQChannelManager(ChannelManager):
    def create(self, **kw):
        kw.update(dict(adaptive_learning_enabled=False))
        return super(FAQChannelManager, self).create(**kw)


class FAQChannel(Channel):
    manager = FAQChannelManager

    @property
    def type_name(self):
        return "FAQ Channel"

    @property
    def platform(self):
        return "FAQ"
