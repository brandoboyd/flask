from solariat.db import fields
from solariat_bottle.db.user_profiles.base_platform_profile import UserProfile, UserProfileManager


class NPSProfileManager(UserProfileManager):
    pass


class NPSProfile(UserProfile):

    first_name = fields.StringField(db_field='fe')
    last_name = fields.StringField(db_field='le')

    phone = fields.StringField(db_field='pe')
    company_name = fields.StringField(db_field='cm')
    industry = fields.StringField(db_field='iy')
    department = fields.StringField(db_field='de')
    region = fields.StringField(db_field='rn')
    country = fields.StringField(db_field='cy')
    genesys_account = fields.StringField(db_field='gt')
    nps_user_id = fields.StringField(db_field='nuid')

    manager = NPSProfileManager

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_name': '%s %s' % (self.first_name, self.last_name),
            'screen_name': '%s %s' % (self.first_name, self.last_name),
            'user_id': None,
            'location': self.country,
            'profile_url': None,
            'profile_image_url': '',
            # 'actor_counter': self.customer_profile.actor_counter,
            'klout_score': None}
