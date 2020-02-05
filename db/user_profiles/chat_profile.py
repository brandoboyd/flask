from .user_profile import UserProfile


class ChatProfile(UserProfile):
    @property
    def platform(self):
        return 'Chat'

