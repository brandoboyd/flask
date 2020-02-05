from solariat.db.abstract import Manager
from solariat.db import fields

from .user_profile import UserProfile, UserProfileManager


class RevenueProfileManager(UserProfileManager):

    def get_by_platform(self, platform, user_name):
        id = RevenueProfile.make_id(platform, user_name)
        return Manager.get(self, id=id)

    def sync_customer_profile_data(self, web_profile, customer_profile):
        # TODO: Here might be the point where we also create an anonymous customer profile and link it to this
        pass

    def create_by_user(self, 
            user,
            account,
            rcs_id):

        obj = None
        if obj is None and rcs_id:
            try:
                obj = RevenueProfile.objects.get(rcs_id=rcs_id)
            except RevenueProfile.DoesNotExist:
                pass

        if obj is None:
            obj = RevenueProfile.objects.create(
                rcs_id=rcs_id,
            )
        CustomerProfile = account.get_customer_profile_class()
        obj._customer_profile = CustomerProfile()
        obj._customer_profile.save()
        obj.save()
        customer = obj.customer_profile

        self.sync_customer_profile_data(obj, customer)

        return obj


class RevenueProfile(UserProfile):

    collection = 'RevenueProfile'

    rcs_id = fields.NumField()

    manager = RevenueProfileManager

    @property
    def customer_profile(self):
        if not self._customer_profile:
            cp = CustomerProfile()
            cp.save()
            self._customer_profile = cp
            self.save()
        return self._customer_profile

    @property
    def agent_profile(self):
        assert False

