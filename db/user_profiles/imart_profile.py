from solariat.db.abstract import Manager
from solariat.db import fields
from .user_profile import UserProfile, UserProfileManager


class ImartProfileManager(UserProfileManager):

    def get_by_platform(self, platform, user_name):
        id = ImartProfile.make_id(platform, user_name)
        return Manager.get(self, id=id)

    def sync_customer_profile_data(self, web_profile, customer_profile):
        # TODO: Here might be the point where we also create an anonymous customer profile and link it to this
        pass

    def create_by_user(self, 
            user,
            account,
            ani):

        obj = None
        if obj is None and ani:
            try:
                obj = ImartProfile.objects.get(ani=ani)
            except ImartProfile.DoesNotExist:
                pass

        if obj is None:
            obj = ImartProfile.objects.create(
                ani=ani,
            )
        CustomerProfile = account.get_customer_profile_class()
        obj._customer_profile.save()
        obj.save()
        customer = obj.customer_profile(account)

        self.sync_customer_profile_data(obj, customer)

        return obj


class ImartProfile(UserProfile):

    collection = 'ImartProfile'

    ani = fields.NumField()

    manager = ImartProfileManager

    def customer_profile(self, account):
        if not self._customer_profile:
            CustomerProfile = account.get_customer_profile_class()
            cp = CustomerProfile()
            cp.save()
            self._customer_profile = cp
            self.save()
        return self._customer_profile

    @property
    def agent_profile(self):
        assert False

