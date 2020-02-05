from solariat.db.abstract import Manager
from solariat.db import fields

from .user_profile import UserProfile, UserProfileManager


class NPSEntityManager(UserProfileManager):

    def get_by_platform(self, platform, user_name):
        id = NPSEntityProfile.make_id(platform, user_name)
        return Manager.get(self, id=id)

    def sync_customer_profile_data(self, web_profile, customer_profile):
        # TODO: Here might be the point where we also create an anonymous customer profile and link it to this
        pass

    def create_by_user(self, 
            user,
            account,
            phone):

        obj = None
        if obj is None and phone:
            try:
                obj = NPSEntityProfile.objects.get(phone=phone)
            except NPSEntityProfile.DoesNotExist:
                pass

        if obj is None:
            obj = NPSEntityProfile.objects.create(
                phone=phone,
            )
        CustomerProfile = account.get_customer_profile_class()
        obj._customer_profile = CustomerProfile()
        obj._customer_profile.save()
        obj.save()
        customer = obj.customer_profile

        self.sync_customer_profile_data(obj, customer)

        return obj


class NPSEntityProfile(UserProfile):

    collection = 'RevenueProfile'

    phone = fields.NumField()

    manager = NPSEntityManager

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

