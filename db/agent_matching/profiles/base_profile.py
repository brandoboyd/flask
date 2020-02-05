from datetime import datetime
from dateutil.relativedelta import relativedelta
from solariat.db import fields
from solariat.utils.timeslot import now

from solariat_bottle.settings import LOGGER
from solariat_bottle.db.auth import AuthDocument, AuthManager
from solariat_bottle.db.sequences import AutoIncrementField

AGE_FORMAT = '%m/%d/%Y'


class UntrackedProfile(object):

    actor_num = 0


class ProfileManager(AuthManager):

    def create_by_user(self, user, *args, **kwargs):
        if 'account_id' not in kwargs:
            kwargs['account_id'] = user.account.id
        return super(ProfileManager, self).create_by_user(user, *args, **kwargs)


class BaseProfile(AuthDocument):
    manager = ProfileManager

    allow_inheritance = True
    collection = "BaseProfiles"

    account_id = fields.ObjectIdField()
    first_name = fields.StringField()
    last_name = fields.StringField()
    age = fields.NumField()
    sex = fields.StringField()
    location = fields.StringField()
    seniority = fields.StringField()
    assigned_labels = fields.ListField(fields.ObjectIdField())
    date_of_birth = fields.StringField()
    attached_data = fields.DictField()
    products = fields.ListField(fields.StringField())
    actor_num = AutoIncrementField(counter_name='ActorCounter', db_field='ar')
    created_at = fields.DateTimeField(default=now)

    linked_profile_ids = fields.ListField(fields.StringField())

    indexes = ['actor_num', 'linked_profile_ids']

    @property
    def linked_profiles(self):
        from solariat_bottle.db.user_profiles.user_profile import UserProfile
        return UserProfile.objects(id__in=self.linked_profile_ids)[:]

    def get_profile_of_type(self, typename):
        if not isinstance(typename, basestring):
            typename = typename.__name__

        for profile in self.linked_profiles:
            if profile.__class__.__name__ == typename:
                return profile

    def add_profile(self, profile):
        new_id = str(profile.id)
        if new_id not in self.linked_profile_ids:
            self.linked_profile_ids.append(new_id)
        self.update(addToSet__linked_profile_ids=new_id)

    def get_age(self):
        # Best guess we can make is by date of birth if present and properly formatted
        if self.date_of_birth:
            try:
                dob = datetime.strptime(self.date_of_birth, AGE_FORMAT)
                return relativedelta(datetime.now(), dob).years
            except Exception, ex:
                LOGGER.error(ex)
        # Next, if actual age is present, use that but also store updated dob
        if self.age:
            dob = datetime.now() - relativedelta(years=self.age)
            self.date_of_birth = dob.strftime(AGE_FORMAT)
            self.save()
            return self.age
        return None

    def to_dict(self, fields_to_show=None):
        base_dict = super(BaseProfile, self).to_dict(fields_to_show=fields_to_show)
        return base_dict

    @property
    def full_name(self):
        name = u" ".join(filter(None, [self.first_name, self.last_name]))
        return name or "Unknown"