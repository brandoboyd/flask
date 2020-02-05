def gen_twitter_user(screen_name):
    id_ = hash(screen_name) & 0xFFFFFFFF

    return {
        "lang": "en",
        "created_at": "Thu Aug 09 16:52:43 +0000 2012",
        "screen_name": screen_name,
        "profile_image_url_https": "https://abs.twimg.com/sticky/default_profile_images/default_profile_2_normal.png",
        "profile_image_url": "http://abs.twimg.com/sticky/default_profile_images/default_profile_2_normal.png",
        "time_zone": None,
        "utc_offset": None,
        "description": None,
        "location": None,
        "followers_count": id_ & 0xFF,
        "friends_count": id_ << 2 & 0xFF,
        "statuses_count": id_ << 4 & 0xFF,
        "id_str": str(id_),
        "id": id_,
        "name": screen_name.title()}


def get_user_profile(tw_json):
    from solariat_bottle.daemons.twitter.parsers import parse_user_profile
    from solariat_bottle.db.user_profiles.user_profile import UserProfile
    try:
        return UserProfile.objects.get_by_platform('Twitter', tw_json['screen_name'])
    except UserProfile.DoesNotExist:
        return UserProfile.objects.upsert('Twitter', profile_data=parse_user_profile(tw_json))


class AttrDict(dict):
    __getattr__ = dict.__getitem__

    # for pickling
    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.update(state)
    

class FakeTwitterAPI(object):
    _relations = []

    def get_user(self, screen_name):
        return AttrDict(gen_twitter_user(screen_name))

    def me(self):
        screen_name = hasattr(self, 'screen_name') and self.screen_name or 'me'
        return AttrDict(gen_twitter_user(screen_name))

    def _setup(self, screen_name, followers_count, friends_count):
        user = self.get_user(screen_name)

        for n in range(0, followers_count):
            self._relations.append(
                (user, 'is_friend', self.get_user('usr%s' % n))
            )

        for n in range(0, friends_count):
            self._relations.append(
                (user, 'is_follower', self.get_user('usr%s' % n))
            )

    def _lookup(self, relation):
        def find(item):
            return (item[0].screen_name == self.screen_name
                    and item[1] == relation)

        return map(lambda rel: rel[2], filter(find, self._relations))

    def followers(self, *args, **kwargs):
        cursors = (None, None)
        return self._lookup('is_friend'), cursors

    def friends(self, *args, **kwargs):
        cursors = (None, None)
        return self._lookup('is_follower'), cursors
