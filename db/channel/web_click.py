from .base import ChannelManager, Channel
from solariat.db import fields


class VOCWebClickManager(ChannelManager):
    def create(self, **kw):
        kw.update(dict(adaptive_learning_enabled=False))
        return super(VOCWebClickManager, self).create(**kw)


class WebClickChannel(Channel):
    manager = VOCWebClickManager

    @property
    def type_name(self):
        return "Web Clicks"

    @property
    def platform(self):
        return "Web"
