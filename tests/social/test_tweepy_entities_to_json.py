from tweepy import DirectMessage, User, API
import json
import datetime
from solariat_bottle.tests.base import BaseCase
from solariat_bottle.utils.tweet import tweepy_entity_to_dict

api = API()


def _create_sender():
    user_sender = User()
    user_sender_dict = dict(_api=api,
                            follow_request_sent=False,
                            profile_use_background_image=True,
                            _json={'follow_request_sent': False,
                                   'profile_use_background_image': True,
                                   'profile_text_color': '333333',
                                   'default_profile_image': False,
                                   'id': 1411050992,
                                   'profile_background_image_url_https': 'https://abs.twimg.com/images/themes/theme1/bg.png',
                                   'verified': False,
                                   'profile_location': None,
                                   'profile_image_url_https': 'https://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg',
                                   'profile_sidebar_fill_color': 'DDEEF6',
                                   'entities': {'url': {'urls': [{'url': 'http://t.co/zo4nXhS2Fu',
                                                                  'indices': [0, 22],
                                                                  'expanded_url': 'http://www.web.com',
                                                                  'display_url': 'web.com'}]},
                                                'description': {'urls': []}},
                                   'followers_count': 10,
                                   'profile_sidebar_border_color': 'C0DEED',
                                   'id_str': '1411050992',
                                   'profile_background_color': 'C0DEED',
                                   'listed_count': 0,
                                   'is_translation_enabled': False,
                                   'utc_offset': None,
                                   'statuses_count': 3113,
                                   'description': 'Teacher',
                                   'friends_count': 13,
                                   'location': 'San Francisco',
                                   'profile_link_color': '0084B4',
                                   'profile_image_url': 'http://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg',
                                   'following': False,
                                   'geo_enabled': False,
                                   'profile_background_image_url': 'http://abs.twimg.com/images/themes/theme1/bg.png',
                                   'name': 'user1_solariat',
                                   'lang': 'en',
                                   'profile_background_tile': False,
                                   'favourites_count': 1,
                                   'screen_name': 'user1_solariat',
                                   'notifications': False,
                                   'url': 'http://t.co/zo4nXhS2Fu',
                                   'created_at': 'Tue May 07 19:35:50 +0000 2013',
                                   'contributors_enabled': False,
                                   'time_zone': None,
                                   'protected': False,
                                   'default_profile': True,
                                   'is_translator': False},
                            time_zone=None, id=1411050992,
                            verified=False,
                            profile_location=None,
                            profile_image_url_https='https://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg',
                            profile_sidebar_fill_color='DDEEF6', is_translator=False, geo_enabled=False, entities={'url': {
        'urls': [{'url': 'http://t.co/zo4nXhS2Fu', 'indices': [0, 22], 'expanded_url': 'http://www.web.com',
                  'display_url': 'web.com'}]}, 'description': {'urls': []}}, followers_count=10, protected=False,
                            id_str='1411050992', default_profile_image=False, listed_count=0, lang='en', utc_offset=None,
                            statuses_count=3113, description='Teacher', friends_count=13, profile_link_color='0084B4',
                            profile_image_url='http://pbs.twimg.com/profile_images/468781442852339712/69CJihsO_normal.jpeg',
                            notifications=False, favourites_count=1,
                            profile_background_image_url_https='https://abs.twimg.com/images/themes/theme1/bg.png',
                            profile_background_color='C0DEED',
                            profile_background_image_url='http://abs.twimg.com/images/themes/theme1/bg.png',
                            screen_name='user1_solariat', is_translation_enabled=False, profile_background_tile=False,
                            profile_text_color='333333', name='user1_solariat', url='http://t.co/zo4nXhS2Fu',
                            created_at=datetime.datetime(2013, 5, 7, 19, 35, 50), contributors_enabled=False,
                            location='San Francisco', profile_sidebar_border_color='C0DEED', default_profile=True,
                            following=False)
    for key, val in user_sender_dict.iteritems():
        setattr(user_sender, key, val)
    return user_sender


def _create_receiver():
    user_reciever = User()
    user_receiver_dict = dict(_api=api, follow_request_sent=False, profile_use_background_image=True,
                              _json={'follow_request_sent': False, 'profile_use_background_image': True,
                                     'profile_text_color': '634047', 'default_profile_image': False, 'id': 1411081099,
                                     'profile_background_image_url_https': 'https://abs.twimg.com/images/themes/theme3/bg.gif',
                                     'verified': False, 'profile_location': None,
                                     'profile_image_url_https': 'https://pbs.twimg.com/profile_images/378800000614919360/cd40847077aabbaae141ad352af91f5d_normal.jpeg',
                                     'profile_sidebar_fill_color': 'E3E2DE', 'entities': {'url': {'urls': [
                                  {'url': 'http://t.co/5YkGQhfD1C', 'indices': [0, 22],
                                   'expanded_url': 'http://www.testsite.com', 'display_url': 'testsite.com'}]},
                                                                                          'description': {'urls': []}},
                                     'followers_count': 7, 'profile_sidebar_border_color': 'D3D2CF', 'id_str': '1411081099',
                                     'profile_background_color': 'EDECE9', 'listed_count': 0,
                                     'is_translation_enabled': False, 'utc_offset': None, 'statuses_count': 1514,
                                     'description': '', 'friends_count': 5, 'location': 'Bay Area',
                                     'profile_link_color': '088253',
                                     'profile_image_url': 'http://pbs.twimg.com/profile_images/378800000614919360/cd40847077aabbaae141ad352af91f5d_normal.jpeg',
                                     'following': False, 'geo_enabled': False,
                                     'profile_background_image_url': 'http://abs.twimg.com/images/themes/theme3/bg.gif',
                                     'name': 'user2_solariat', 'lang': 'en', 'profile_background_tile': False,
                                     'favourites_count': 0, 'screen_name': 'user2_solariat', 'notifications': False,
                                     'url': 'http://t.co/5YkGQhfD1C', 'created_at': 'Tue May 07 19:45:31 +0000 2013',
                                     'contributors_enabled': False, 'time_zone': None, 'protected': False,
                                     'default_profile': False, 'is_translator': False}, time_zone=None, id=1411081099,
                              verified=False, profile_location=None,
                              profile_image_url_https='https://pbs.twimg.com/profile_images/378800000614919360/cd40847077aabbaae141ad352af91f5d_normal.jpeg',
                              profile_sidebar_fill_color='E3E2DE', is_translator=False, geo_enabled=False, entities={
        'url': {'urls': [{'url': 'http://t.co/5YkGQhfD1C', 'indices': [0, 22], 'expanded_url': 'http://www.testsite.com',
                          'display_url': 'testsite.com'}]}, 'description': {'urls': []}}, followers_count=7,
                              protected=False, id_str='1411081099', default_profile_image=False, listed_count=0, lang='en',
                              utc_offset=None, statuses_count=1514, description='', friends_count=5,
                              profile_link_color='088253',
                              profile_image_url='http://pbs.twimg.com/profile_images/378800000614919360/cd40847077aabbaae141ad352af91f5d_normal.jpeg',
                              notifications=False, favourites_count=0,
                              profile_background_image_url_https='https://abs.twimg.com/images/themes/theme3/bg.gif',
                              profile_background_color='EDECE9',
                              profile_background_image_url='http://abs.twimg.com/images/themes/theme3/bg.gif',
                              screen_name='user2_solariat', is_translation_enabled=False, profile_background_tile=False,
                              profile_text_color='634047', name='user2_solariat', url='http://t.co/5YkGQhfD1C',
                              created_at=datetime.datetime(2013, 5, 7, 19, 45, 31), contributors_enabled=False,
                              location='Bay Area', profile_sidebar_border_color='D3D2CF', default_profile=False,
                              following=False)
    for key, val in user_receiver_dict.iteritems():
        setattr(user_reciever, key, val)
    return user_reciever


def _create_dm():
    dm = DirectMessage()

    dm_dict = dict(_api=api,
                   recipient_id_str='1411081099',
                   sender=_create_sender(),
                   sender_id_str='1411050992',
                   text='Hey, I am having some laptop problems. Can you help? 2014.11.19.10.08.44',
                   created_at=datetime.datetime(2014, 11, 19, 18, 8, 52),
                   sender_id=1411050992,
                   id=535132617017135104,
                   entities={'symbols': [], 'user_mentions': [], 'hashtags': [], 'urls': []},
                   recipient_id=1411081099, id_str='535132617017135104',
                   recipient_screen_name='user2_solariat',
                   recipient=_create_receiver(),
                   sender_screen_name='user1_solariat')
    for key, val in dm_dict.iteritems():
        setattr(dm, key, val)

    return dm


class TweepyJsonTests(BaseCase):

    def test_dm_json(self):
        # Just check that we get an actual JSON'able dictionary from an entity
        dm = _create_dm()
        dm_dict = tweepy_entity_to_dict(dm)
        json.dumps(dm_dict)
        print dm_dict