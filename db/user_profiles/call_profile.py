from .user_profile import UserProfile


class CallProfile(UserProfile):

    @property
    def platform(self):
        return 'Call'
