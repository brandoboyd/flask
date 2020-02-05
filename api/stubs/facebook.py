import time
from solariat_bottle.api.base import ModelAPIView, api_request
from solariat_bottle.db.api_auth import AuthToken
from solariat_bottle.db.post.utils import factory_by_user


TEMPLATE = {"facebook": {"page_id": "696931697082350_1428443117474284",
                          "facebook_post_id": "1428443117474284_1428447340807195",
                          "_wrapped_data": {"can_hide": 1,
                                            "can_remove": 1,
                                            "like_count": 0,
                                            "user_likes": 0,
                                            "visibility": "Normal",
                                            "created_at": "2015-05-11T20:49:39 +0000",
                                            "source_type": "PM",
                                            "message": "comment 10",
                                            "type": "Comment",
                                            "can_comment": 1,
                                            "can_like": 1,
                                            "parent_id": "1428443117474284",
                                            "from": {"name": "Tester Kultanen",
                                                     "id": "1550633285198664"},
                                            "id": "1428443117474284_1428447340807195",
                                            "source_id": "696931697082350_1428443117474284"},
                          "in_reply_to_status_id": "696931697082350_1428443117474284",
                          "created_at": "2015-05-11T20:49:39 +0000",
                          "root_post": "696931697082350_1428443117474284",
                          "second_level_reply": False},
             "channel": "5551148df68e4a4abf297b33",
             "user_profile": {"user_name": "Tester Kultanen",
                              "profile_image_url": "https://fbcdn-profile-a.akamaihd.net/hprofile-ak-xpf1/v/t1.0-1/c8.0.50.50/p50x50/10665693_1475432259385434_7021820318442317987_n.jpg?oh\\u003d76caa891b5b143b79ba40096ae205350\\u0026oe\\u003d560B9399\\u0026__gda__\\u003d1443722344_fc7b8a244868461b23f5006b0f0a6140", \
                              "id": "1550633285198664"},
             "url": "www.facebook.com/permalink.php?id\\u003d696931697082350_1428443117474284\\u0026story_fbid\\u003d1428447340807195\\u0026comment_id\\u003d1428443117474284", \
             "content": "comment 10"}

R_POST_OBJECTDATA = {u'channel': u'5551148df68e4a4abf297b33',
                     u'content': u'Hi Solariat UI devs page!',
                     u'facebook': {u'_wrapped_data': {u'actions': [{u'name': u'Comment'},
                                                                   {u'name': u'Like'},
                                                                   {u'name': u'See Friendship'}],
                                                      u'attachment_count': 1,
                                                      u'can_be_hidden': 1,
                                                      u'can_change_visibility': 0,
                                                      u'can_comment': 1,
                                                      u'can_like': 1,
                                                      u'can_remove': 1,
                                                      u'comment_count': 0,
                                                      u'comments': [{u'created_at': u'2015-05-11T20:48:36 +0000',
                                                                     u'from': {u'id': u'1428443544140908',
                                                                               u'name': u'Anna Apina'},
                                                                     u'likes': 0,
                                                                     u'message': u'comment 1'}],
                                                      u'created_at': u'2015-05-11T20:48:30 +0000',
                                                      u'created_by_admin': 0,
                                                      u'from': {u'id': u'1428443544140908',
                                                                u'name': u'Anna Apina'},
                                                      u'icon': u'https://www.facebook.com/images/icons/photo.gif',
                                                      u'id': u'696931697082350_1428443117474284',
                                                      u'is_liked': 0,
                                                      u'is_popular': False,
                                                      u'is_published': False,
                                                      u'link': u'https://www.facebook.com/photo.php?fbid=1428443117474284&set=o.696931697082350&type=1',
                                                      u'message': u'Hi Solariat UI devs page!',
                                                      u'picture': u'https://scontent.xx.fbcdn.net/hphotos-xta1/v/t1.0-9/s130x130/11231147_1428443117474284_4502150248783341930_n.jpg?oh=6fb83429097b07a248688932d3e4a233&oe=560B92F8',
                                                      u'place': u'{"zip":"<<not-applicable>>","latitude":43.7166,"longitude":-79.3407}',
                                                      u'privacy': u'',
                                                      u'properties': [],
                                                      u'share_count': 0,
                                                      u'source_id': u'696931697082350',
                                                      u'source_type': u'PM',
                                                      u'story': u"Anna Apina added a new photo to Solariat UI devs Page's timeline \u2014 in Toronto, Ontario.",
                                                      u'to': [{u'id': u'696931697082350',
                                                               u'name': u'Solariat UI devs Page'}],
                                                      u'type': u'photo',
                                                      u'updated_time': u'2015-05-11T20:48:30 +0000'},
                                   u'attachments': True,
                                   u'created_at': u'2015-05-11T20:48:30 +0000',
                                   u'facebook_post_id': u'696931697082350_1428443117474284',
                                   u'page_id': u'696931697082350'},
                     u'url': u'https://www.facebook.com/photo.php?fbid=1428443117474284&set=o.696931697082350&type=1',
                     u'user_profile': {u'id': u'1428443544140908',
                                       u'profile_image_url': u'https://fbcdn-profile-a.akamaihd.net/hprofile-ak-xfp1/v/t1.0-1/c0.0.50.50/p50x50/11174794_1413801515605111_1239918768931071226_n.jpg?oh=e8ba88bc784f5f6e1665993c1fd51f17&oe=55D34EE2&__gda__=1443725515_3660bd65808278e101cfb7a58a5b417b',
                                       u'user_name': u'Anna Apina'}}

POST_TEMPLATE = {'post_object_data': '',
                 'channel': '',
                 'serialized_to_json': True,
                 'content': ''}


class FacebookStub(ModelAPIView):

    commands = ['create_post', 'create_comment']
    endpoint = 'stubs/facebook'
    required_fields = ['channel']

    @classmethod
    def register(cls, app):
        """ Queue API allows for extra commands, like 'fetch' and 'confirm' """
        url = cls.get_api_url()
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(url, view_func=view_func, methods=['GET', "POST", "PUT", "DELETE"])
        url = cls.get_api_url('<command>')
        app.add_url_rule(url, view_func=view_func, methods=["GET", "POST", "PUT", "DELETE"])

    def get(self, *args, **kwargs):
        return self._get(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._delete(*args, **kwargs)

    def post(self, command=None, *args, **kwargs):
        """ Allowed commands are routed to the _<command> method on this class """
        if command in self.commands:
            meth = getattr(self, '_' + command)
            return meth(*args, **kwargs)
        return self._post(*args, **kwargs)

    def __get_token(self, user):
        all_candidates = AuthToken.objects.find(user=user)[:]
        for token in all_candidates:
            if token.is_valid:
                return token.digest
        return None

    @api_request
    def _create_post(self, user, *args, **kwargs):
        base_id = '696931697082350_'
        generated_id = base_id + str(int(time.time() * 1000))

        content = kwargs['content']
        channel = kwargs['channel']

        # Fill in custom content
        R_POST_OBJECTDATA['content'] = content
        R_POST_OBJECTDATA['facebook']['_wrapped_data']['message'] = content
        R_POST_OBJECTDATA['facebook']['_wrapped_data']['id'] = generated_id
        R_POST_OBJECTDATA['facebook']['facebook_post_id'] = generated_id
        R_POST_OBJECTDATA['channel'] = channel

        factory_by_user(user, **R_POST_OBJECTDATA)
        return dict(ok=True)

    @api_request
    def _create_comment(self, user, *args, **kwargs):
        base_id = '696931697082350_'
        generated_id = base_id + str(int(time.time() * 1000))

        content = kwargs['content']
        channel = kwargs['channel']
        parent_id = kwargs.get('parent', None)

        # Fill in custom content
        R_POST_OBJECTDATA['content'] = content
        R_POST_OBJECTDATA['facebook']['_wrapped_data']['message'] = content
        R_POST_OBJECTDATA['facebook']['_wrapped_data']['id'] = generated_id
        R_POST_OBJECTDATA['facebook']['facebook_post_id'] = generated_id
        R_POST_OBJECTDATA['channel'] = channel

        if parent_id:
            R_POST_OBJECTDATA['facebook']['in_reply_to_status_id'] = parent_id

        factory_by_user(user, **R_POST_OBJECTDATA)
        return dict(ok=True)