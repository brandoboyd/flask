"""Twitter and Facebook specific user profiles
"""

from solariat_bottle.db.channel.base import Channel
from solariat.db import fields
from solariat_bottle.db.user_profiles.base_platform_profile import UserProfile, UserProfileManager
from solariat.utils.timeslot import now


DELIMITER = ":"

# relation to brand from user's prospective
RELATION_FOLLOWER = 'follower'
RELATION_FRIEND = 'friend'


def get_native_user_id_from_channel(channel):
    from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel
    from solariat_bottle.db.channel.facebook import EnterpriseFacebookChannel

    if isinstance(channel, EnterpriseTwitterChannel):
        return channel.twitter_handle_id
    if isinstance(channel, EnterpriseFacebookChannel):
        return channel.facebook_handle_id
    return None


def get_brand_profile_id(source):
    """Deprecated. Used in TwitterRelationsMixin"""
    if isinstance(source, Channel):
        native_user_id = get_native_user_id_from_channel(source)
        return SocialProfile.make_id(source.platform, native_user_id)
    elif isinstance(source, UserProfile):
        return source.id
    # raw user id
    return source


class TwitterRelationsMixin(object):
    """Deprecated. We are using general short-term cache for determining
    a relationship status and do not sync followers/friends lists anymore
    """
    # All profile ids from EnterpriseTwitterChannel which are following the user
    # so this user is friend of users in followed_by_brands list
    followed_by_brands = fields.ListField(fields.StringField(), db_field='fc')
    # All profile ids from EnterpriseTwitterChannel which are followed by user,
    # so this user is follower of users in follows_brands list
    follows_brands = fields.ListField(fields.StringField(), db_field='fb')
    relations_history = fields.ListField(fields.DictField(), db_field='rh')

    @staticmethod
    def in_set_ignore_case(items, source):
        lower = lambda x: x.lower()
        return lower(get_brand_profile_id(source)) in set(map(lower, items))

    def is_followed(self, source):
        return self.in_set_ignore_case(self.followed_by_brands, source)

    is_friend = is_followed

    def log_relation(self, action, source):
        doc = {'a': action,
               'u': get_brand_profile_id(source),
               't': now()}
        if isinstance(source, Channel) and hasattr(source, 'status_update'):
            doc['t'] = source.status_update
        self.update(push__relations_history=doc)

    def add_follower(self, source):
        self.log_relation('add_follower', source)
        self.update(addToSet__followed_by_brands=get_brand_profile_id(source))

    def remove_follower(self, source):
        self.log_relation('remove_follower', source)
        self.update(pull__followed_by_brands=get_brand_profile_id(source))

    def is_follower(self, source):
        return self.in_set_ignore_case(self.follows_brands, source)

    def add_friend(self, source):
        self.log_relation('add_friend', source)
        self.update(addToSet__follows_brands=get_brand_profile_id(source))

    def remove_friend(self, source):
        self.log_relation('remove_friend', source)
        self.update(pull__follows_brands=get_brand_profile_id(source))

    def update_relations(self, platform, relation, data, channel):
        manager = self.objects

        def get_params(up_data):
            if platform == 'Twitter':
                from solariat_bottle.daemons.twitter.parsers import parse_user_profile

                return parse_user_profile(up_data)
            return {}

        for user_profile_data in data:
            if isinstance(user_profile_data, (basestring, int)):
                user_p = manager.find_one(user_id=str(user_profile_data))
                if not user_p:
                    continue
            else:
                user_p = manager.upsert(platform, get_params(user_profile_data))

            if relation == RELATION_FRIEND:
                user_p.add_follower(channel)
            elif relation == RELATION_FOLLOWER:
                user_p.add_friend(channel)


class SocialProfileManager(UserProfileManager):
    '''Wraps access with encoded key'''

    def get_by_platform(self, platform, native_id):
        ''' Enforce id encoding.'''
        u_id = SocialProfile.make_id(platform, native_id)
        from solariat_bottle.settings import LOGGER
        LOGGER.debug("SEARCHING BY ID " + str(u_id))
        return self.get(u_id)

    def extract_upsert_data(self, ProfileCls, profile_data):
        native_id = profile_data.get('user_id', profile_data.get('native_id', profile_data.get('id', None)))
        user_name = profile_data.get('user_name', None)
        screen_name = profile_data.get('screen_name', None)

        native_id = native_id or user_name or screen_name or 'anonymous'
        up_id = ProfileCls.make_id(ProfileCls.platform, native_id)

        query = dict(id=up_id)
        data = query.copy()
        if user_name is not None:
            data['name'] = user_name

        data['native_id'] = str(native_id)

        screen_name = screen_name or user_name
        if screen_name:
            data['user_name'] = screen_name

        location = profile_data.get('location', None)
        if location is not None:
            data['location'] = location

        profile_image_url = profile_data.get('profile_image_url', None)
        if profile_image_url is not None:
            data['profile_image_url'] = profile_image_url

        platform_data = profile_data.get('platform_data', None)
        if platform_data is not None:
            data['platform_data'] = platform_data

        klout_score = profile_data.get('klout_score', None)
        if klout_score is not None:
            data['klout_score'] = klout_score

        data['updated_at'] = now()
        return query, data


class SocialProfile(UserProfile):

    manager = SocialProfileManager

    id = fields.CustomIdField()
    # user_id = fields.StringField(db_field='ui')  # replaced with native_id
    user_name = fields.StringField(db_field='un', default='')
    name = fields.StringField(db_field='ne', default='')
    location = fields.StringField(db_field='ln', default='')
    profile_image_url = fields.StringField(db_field='pl')
    klout_score = fields.NumField(db_field='ks')

    indexes = UserProfile.indexes + ['user_name']

    @property
    def platform_id(self):
        index = 0
        if self.id:
            pos = str(self.id).rfind(DELIMITER) + 1
            index = int(self.id[pos:])
        return index

    @property
    def user_id_int(self):
        try:
            return long(self.user_id)
        except:
            return None

    @property
    def user_id(self):
        return self.native_id

    @property
    def screen_name(self):
        return self.user_name

    @property
    def platform(self):
        from solariat_bottle.db.channel.base import get_platform_by_index
        return get_platform_by_index(self.platform_id)

    @property
    def normalized_screen_name(self):
        from solariat_bottle.utils.post import normalize_screen_name
        if self.screen_name:
            return normalize_screen_name(self.screen_name)
        return None

    @property
    def profile_url(self):
        if self.screen_name in ('Anon-y-mous', '', None):
            return None
        return "%s/%s" % (self.base_url, self.screen_name)

    @property
    def base_url(self):
        from solariat_bottle.db.channel.base import PLATFORM_MAP
        return PLATFORM_MAP[self.platform]['base_url']

    @classmethod
    def make_id(cls, platform, native_id):
        from solariat_bottle.db.channel.base import PLATFORM_MAP
        return ("%s%s%d" % (
            native_id,
            DELIMITER,
            PLATFORM_MAP[platform]['index'])).lower()

    @classmethod
    def anonymous_profile(cls, platform=None):
        anonymous_native_id = 'anonymous'
        platform = getattr(cls, 'platform', None)
        if not isinstance(platform, str) or not platform:
            platform = 'Solariat'
        data = {'id': cls.make_id(platform, anonymous_native_id)}
        return cls.objects.get_or_create(**data)

    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user_name,
            'screen_name': self.screen_name,
            'user_id': self.user_id,
            'location': self.location,
            'profile_url': self.profile_url,
            'profile_image_url': self.profile_image_url,
            # 'actor_counter': self.customer_profile.actor_counter,
            'actor_counter': self.actor_num,
            'klout_score': self.klout_score }


class TwitterProfile(SocialProfile, TwitterRelationsMixin):
    platform = 'Twitter'


class FacebookProfile(SocialProfile):
    platform = 'Facebook'


