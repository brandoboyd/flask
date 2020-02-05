from solariat.metacls import Singleton
from solariat_bottle.db.post.twitter import datetime_to_string

identity = lambda x: x


def _parse_date(dt):
    if not isinstance(dt, basestring):
        return datetime_to_string(dt)
    return dt


class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def copy_attrs(data, attrs, map_attrs=None, parsers=None):
    if map_attrs is None:
        map_attrs = {}

    if isinstance(data, dict):
        data = AttributeDict(data)

    if parsers is None:
        parsers = {}

    json_dict = {}
    for attr in attrs:
        if hasattr(data, attr):
            val = getattr(data, attr)
            json_dict[attr] = parsers.get(attr, identity)(val)

    for key, attr in map_attrs.iteritems():
        if isinstance(attr, basestring) and hasattr(data, attr):
            json_dict[key] = parsers.get(attr, identity)(getattr(data, attr))
        if callable(attr):
            json_dict[key] = attr(data)

    return json_dict


class Parser(object):
    __metaclass__ = Singleton

    MIRROR_ATTRIBUTES = []
    MAP_ATTRIBUTES = {}
    PARSERS = {}

    def __call__(self, data=None, mirror_attrs=None, map_attrs=None):
        mirror_attrs = mirror_attrs or self.MIRROR_ATTRIBUTES
        map_attrs = map_attrs or self.MAP_ATTRIBUTES
        json_dict = copy_attrs(
            data, mirror_attrs, map_attrs, parsers=self.PARSERS)
        return json_dict

    #__call__ = to_json


class TwitterUserParser(Parser):
    MIRROR_ATTRIBUTES = (
        'id', 'id_str', 'name', 'screen_name',
        'profile_image_url', 'profile_image_url_https',
        'description', 'created_at', 'lang', 'location',
        'time_zone', 'utc_offset',
        'followers_count', 'friends_count', 'statuses_count')

    PARSERS = {
        'created_at': _parse_date
    }


class TwitterUserToUserProfile(Parser):
    MIRROR_ATTRIBUTES = ('name', 'profile_image_url', 'location')
    MAP_ATTRIBUTES = {'user_id': 'id_str', 'user_name': 'screen_name'}


def _get_full_text(data):
    extended_tweet = data.get('extended_tweet') or {}
    return data.get('full_text') or extended_tweet.get('full_text') or data.get('text')


def _get_full_entities(data):
    extended_tweet = data.get('extended_tweet') or {}
    if extended_tweet:
        return extended_tweet.get('extended_entities') or extended_tweet.get('entities') or []
    else:
        return data.get('extended_entities') or data.get('entities') or []


class TweetParser(Parser):
    MIRROR_ATTRIBUTES = (
        'id',
        'in_reply_to_status_id',
        'in_reply_to_screen_name',
        'in_reply_to_user_id',
        'mentions', 'mention_ids',
        'retweet', 'retweeted',
        'created_at',

        'recipient',
        'recipient_id', 'recipient_id_str', 'recipient_screen_name',
        'sender', 'sender_id', 'sender_id_str', 'sender_screen_name',
    )

    MAP_ATTRIBUTES = {
        'text': _get_full_text,
        'entities': _get_full_entities
    }

    PARSERS = {
        'id': str,  # twitter sends int ids
        'recipient': TwitterUserParser(),  # direct message has
        'sender': TwitterUserParser(),     # sender/recipient pair

        'created_at': _parse_date
    }


class DMTweetParser(TweetParser):

    def __call__(self, data=None, mirror_attrs=None, map_attrs=None):
        """mention* and in_reply_to* params do not come with Direct Message,
        so they are filled from recipient info
        """
        json_dict = super(DMTweetParser, self).__call__(data, mirror_attrs, map_attrs)
        recp = json_dict['recipient']
        json_dict.update(dict(in_reply_to_user_id=recp['id_str'],
                              in_reply_to_screen_name=recp['screen_name'],
                              mentions=[recp['screen_name']],
                              mention_ids=[recp['id_str']]))
        return json_dict


def parse_user_profile(up):
    user_profile = TwitterUserToUserProfile()(up)
    user_profile['platform_data'] = TwitterUserParser()(up)
    return user_profile
