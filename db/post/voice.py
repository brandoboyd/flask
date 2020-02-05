from solariat.db import fields
from solariat_bottle.db.post.chat import ChatPost, ChatPostManager
from solariat_bottle.db.user_profiles.base_platform_profile import UserProfile


class VoiceChatManager(ChatPostManager):
    pass


class VoicePost(ChatPost):

    manager = VoiceChatManager
    _parent_post = fields.ReferenceField('VoicePost', db_field='pp')

    PROFILE_CLASS = UserProfile

    @property
    def platform(self):
        return 'Voice'

