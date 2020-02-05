from .base import ChannelManager, Channel
from solariat.db import fields


class BranchChannelManager(ChannelManager):

    def create(self, **kw):
        return super(BranchChannelManager, self).create(**kw)


class BranchChannel(Channel):
    manager = BranchChannelManager

    @property
    def type_name(self):
        return "Branch"

    @property
    def platform(self):
        return "Branch"
