from solariat.db import fields

from solariat_bottle.db.events.event import Event, EventManager
from solariat_bottle.db.user_profiles.user_profile import UserProfile
# from solariat_bottle.db.user_profiles.base_platform_profile import BasePlatformProfile


class BranchManager(EventManager):

    def create_by_user(self, user, **kw):
        for field in kw.keys():
            if field not in BranchEvent.fields:
                del kw[field]

        event = BranchManager.create(self, **kw)
        return event


class BranchEvent(Event):

    manager = BranchManager

    PROFILE_CLASS = UserProfile

    @classmethod
    def patch_post_kw(cls, kw):
        pass

    @property
    def platform(self):
        return 'Branch'
