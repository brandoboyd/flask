from solariat.db.abstract import ObjectId
from solariat_bottle.db.sequences import AutoIncrementField
from solariat.db import fields
from solariat.utils.timeslot import now, utc

from solariat_bottle.db.channel.base import Channel, PLATFORM_BY_INDEX
from solariat.db.abstract import Document, Manager
from solariat_bottle.utils.post import get_service_channel
from solariat_bottle.settings import LOGGER as logger

NATIVE_REMOVED_PROFILE = "258419301__UNKNOWN__PROFILE__5OrdCPQiGNLdr"   # Just a unique id for all removed profiles


class UserProfileManager(Manager):

    def create(self, *args, **kwargs):
        if 'platform_data' not in kwargs or kwargs['platform_data'] is None:
            kwargs['platform_data'] = {}
        if '_created' not in kwargs:
            kwargs['_created'] = now()
        return super(UserProfileManager, self).create(**kwargs)

    @staticmethod
    def profile_class(platform):
        from solariat_bottle.db.post.chat import ChatPost
        from solariat_bottle.db.post.voice import VoicePost
        from solariat_bottle.db.post.twitter import TwitterPost
        from solariat_bottle.db.post.facebook import FacebookPost
        from solariat_bottle.db.post.base import Post
        from solariat_bottle.db.post.voc import VOCPost
        from solariat_bottle.db.post.email import EmailPost
        from solariat_bottle.db.post.faq_query import FAQQueryEvent

        PLATFORM_PROFILE_MAP = {
            'Chat': ChatPost.PROFILE_CLASS,
            'Voice': VoicePost.PROFILE_CLASS,
            'Twitter': TwitterPost.PROFILE_CLASS,
            'Facebook': FacebookPost.PROFILE_CLASS,
            'Solariat': Post.PROFILE_CLASS,
            'VOC': VOCPost.PROFILE_CLASS,
            'Email': EmailPost.PROFILE_CLASS,
            'FAQ': FAQQueryEvent.PROFILE_CLASS
        }

        _profile_klass = PLATFORM_PROFILE_MAP.get(platform, UserProfile)
        return _profile_klass

    def extract_upsert_data(self, ProfileCls, data):
        logger.debug('extract_upsert_data(%s, %s)', ProfileCls, data)

        if data.get('id'):
            query = {'id': data.get('id')}
        else:
            query = {'id': str(ObjectId())}
        update = {
            'native_id': ProfileCls.extract_native_id(data),
            'platform_data': data,
            'updated_at': now()
        }
        return query, update

    def upsert_with_retry(self, ProfileCls, query, update, max_tries_count=5):
        up_id = query.get('id')
        assert up_id, "Undefined profile id"

        profile_object = None
        tries_count = 0
        from solariat_bottle.settings import LOGGER as logger

        while tries_count < max_tries_count:
            tries_count += 1
            try:
                profile_object = ProfileCls.objects.get(up_id)
            except ProfileCls.DoesNotExist:
                from pymongo.helpers import DuplicateKeyError

                try:
                    profile_object = ProfileCls.objects.create(**update)
                except DuplicateKeyError:
                    continue
                else:
                    break
            else:
                absent = object()
                for field, value in update.viewitems():
                    current = getattr(profile_object, field, absent)
                    if current is not absent:
                        setattr(profile_object, field, value)
                try:
                    profile_object.save()
                except:
                    logger.warning("Could not save profile", exc_info=True)
                    continue
                break

        if profile_object is None:
            # create a user profile in case of a test post
            logger.warning(
                "Failed to upsert UserProfile, "
                "returning anonymous profile\nupsert_with_retry("
                "{}, {}, {})".format(ProfileCls, query, update))
            profile_object = ProfileCls.anonymous_profile()
        assert profile_object, profile_object
        return profile_object

    def upsert(self, platform, profile_data):
        ProfileCls = self.profile_class(platform)

        if isinstance(profile_data, ProfileCls):
            profile_object = profile_data
        elif isinstance(profile_data, (bytes, ObjectId)):
            profile_object = ProfileCls.objects.find_one(profile_data)
        elif isinstance(profile_data, dict):
            query, update = ProfileCls.objects.extract_upsert_data(ProfileCls, profile_data)
            profile_object = self.upsert_with_retry(ProfileCls, query, update)
        else:
            logger.warning(
                "Failed to upsert UserProfile, "
                "returning anonymous profile\nupsert("
                "{}, {})".format(platform, profile_data))
            profile_object = ProfileCls.anonymous_profile()
        return profile_object


class UserProfile(Document):
    collection = 'UserProfile'
    allow_inheritance = True

    _created = fields.DateTimeField(default=now)
    updated_at = fields.DateTimeField(default=now, db_field='ts')
    native_id = fields.StringField(db_field='ui', required=False)  # Note: ui is a name for UserProfile.user_id field
    # All Channels this user has been engaged through
    engaged_channels = fields.ListField(fields.ReferenceField(Channel))
    platform_data = fields.DictField(db_field='pd')
    actor_num = AutoIncrementField(counter_name="ActorCounter", db_field='ar')

    manager = UserProfileManager

    indexes = [('native_id', ), ('engaged_channels', )]

    def __init__(self, data=None, **kw):
        """For compatibility with untyped UserProfile.
        This constructor can be deleted once all profiles in the UserProfile
        collection have the type information in the _t field
        """
        def _get_class_by_id(profile_id):
            from solariat_bottle.db.user_profiles.social_profile import DELIMITER, TwitterProfile, FacebookProfile
            pos = unicode(profile_id).rfind(DELIMITER) + 1
            if pos == 0:
                return self.__class__
            platform = None
            try:
                index = int(profile_id[pos:])
            except ValueError:
                logger.info(u"Could not obtain platform from profile id: {}".format(profile_id))
            else:
                platform = PLATFORM_BY_INDEX.get(index)
            class_ = {
                TwitterProfile.platform: TwitterProfile,
                FacebookProfile.platform: FacebookProfile
            }.get(platform, self.__class__)
            return class_

        if data:
            profile_id = data.get('_id')
        else:
            profile_id = kw.get('id')
        if isinstance(profile_id, basestring):
            self.__class__ = _get_class_by_id(profile_id)
        super(UserProfile, self).__init__(data, **kw)

    @property
    def screen_name(self):
        return self.native_id

    @staticmethod
    def extract_native_id(data):
        assert isinstance(data, dict), u"%s is not dict" % repr(data)
        native_id = None
        if 'platform_data' in data:
            native_id = data['platform_data'].get('id')
        if not native_id:
            native_id = data.get('id', data.get('native_id'))
        if not native_id:
            native_id = ObjectId()
        return str(native_id)

    @property
    def created(self):
        return utc(self._created)

    @classmethod
    def anonymous_profile(cls, platform=None):
        data = {'id': 'anonymous'}
        return cls.objects.get_or_create(**data)

    @classmethod
    def non_existing_profile(cls):
        try:
            profile = cls.objects.get(native_id=NATIVE_REMOVED_PROFILE)
        except cls.DoesNotExist:
            profile = cls.objects.create(native_id=NATIVE_REMOVED_PROFILE)
        return profile

    def update_history(self, channel):
        if channel not in self.engaged_channels:
            self.engaged_channels.append(channel)
            self.save()

    def has_history(self, channel):
        service_channel = get_service_channel(channel) if channel and not channel.is_dispatch_channel else None
        return (channel and (channel in self.engaged_channels or
                             service_channel in self.engaged_channels))

    def get_conversations(self, user, channel=None):
        '''All conversations for this contact - subject to access controls'''
        from solariat_bottle.db.conversation import Conversation
        conv_list = sorted(Conversation.objects.find_by_user(user, contacts=self.id), key=lambda c: c.last_modified)
        if channel is not None:
            conv_list = [conv for conv in conv_list if str(channel.id) in conv.channels]
        return conv_list

    def to_dict(self, fields2show=None):
        doc = super(UserProfile, self).to_dict(fields2show)
        doc.update(
            _type=self.__class__.__name__,
            screen_name=self.screen_name
        )
        return doc


