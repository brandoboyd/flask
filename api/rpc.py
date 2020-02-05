from solariat_bottle.db.post.base import Post
import solariat_bottle.api.exceptions as exc
from solariat_bottle.api.base import BaseAPIView, authenticate_api_user, api_request, _get_request_data
from solariat_bottle.db.channel.base import Channel, ServiceChannel
from solariat_bottle.db.user import User
from solariat_bottle.db.user_profiles.social_profile import SocialProfile
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.utils.tweet import tweepy_entity_to_dict
from solariat_bottle.tasks.twitter import (
    tw_normal_reply, tw_direct_reply, tw_share_post, tw_follow, tw_unfollow,
    is_follower, is_friend, tw_get_friends_ids, tw_get_followers_ids,
    tw_get_friends_list, tw_get_followers_list,
    authenticated_media, user_info, channel_user,
    create_favourite, destroy_favorite, destroy_message)
from solariat_bottle.tasks.facebook import (
    fb_like_post, fb_share_post, fb_put_comment, fb_put_post, fb_delete_object,
    fb_private_message, fb_edit_publication, fb_change_object_visibility,
    fb_get_comments_for_post, fb_channel_user, fb_get_channel_description, fb_put_comment_by_channel)


def make_temp_file(media):
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False) as f:
        media.save(f.name)

    # Note: filename should be ascii encoded,
    # tweepy.API._pack_image does not handle unicode
    return media.filename.encode('us-ascii', 'ignore'), f.name


# Mapping between task names and actual task on our side
TASK_MAPPING = {
    'twitter': {
        'update_status': tw_normal_reply,
        'update_with_media': tw_normal_reply,
        'direct_message': tw_direct_reply,
        'retweet_status': tw_share_post,
        'follow_user': tw_follow,
        'unfollow_user': tw_unfollow,
        'is_friend': is_friend,
        'is_follower': is_follower,
        'get_friends': tw_get_friends_ids,
        'get_friends_list': tw_get_friends_list,
        'get_followers': tw_get_followers_ids,
        'get_followers_list': tw_get_followers_list,
        'user_info': user_info,
        'auth_media': authenticated_media,
        'channel_user': channel_user,
        'create_favorite': create_favourite,
        'destroy_favorite': destroy_favorite,
        'destroy_message': destroy_message
    },
    'facebook': {
        'like': fb_like_post,
        'share': fb_share_post,
        'comment': fb_put_comment,
        'comment_ch': fb_put_comment_by_channel,
        'edit_publication': fb_edit_publication,
        'wall_post': fb_put_post,
        'delete_object': fb_delete_object,
        'send_private_message': fb_private_message,
        'change_visibility': fb_change_object_visibility,
        'get_comments': fb_get_comments_for_post,
        'get_channel_user': fb_channel_user,
        'get_channel_description': fb_get_channel_description
    }
}


def channel_resolver(channel, platform, logged_in_user):
    """
    Based on input `channel` parameter return an actual Channel entity on our side.

    :param channel: Required, should be a channel id.
    :param platform: For consistency across resolvers. Might be used to infer some platform specific restrictions.
    """
    assert platform in ('twitter', 'facebook')
    if isinstance(channel, Channel):
        result = channel
    try:
        result = Channel.objects.get(channel)
    except Channel.DoesNotExist:
        return None
    if isinstance(result, ServiceChannel):
        dispatch = result.get_outbound_channel(logged_in_user)
        if dispatch is None:
            error = "No dispatch channel could be found for service: %s." % result.title
            error += " Please set it on the GSA configuration page."
            raise exc.InvalidParameterConfiguration(error)
        # This is a ugly hack so we have service channel information on any API calls that actually need it
        # E.G. get_channel_description. We should strongly consider merging Service and Account channels for facebook
        dispatch._current_service_channel = result
        return dispatch
    return result


def user_resolver(user, platform, logged_in_user):
    """
    Based on input `user` parameter return an User entity on our side.

    :param channel: Required, should be a user id or user email
    :param platform: For consistency across resolvers. Might be used to infer some platform specific restrictions.
    """
    assert platform in ('twitter', 'facebook')
    if isinstance(user, User):
        return user
    try:
        return User.objects.get(user)
    except User.DoesNotExist:
        try:
            return User.objects.get(email=user)
        except User.DoesNotExist:
            return None


def user_profile_resolver(user_profile, platform, logged_in_user):
    """
    Based on input `user_name`  and `platform` parameters return an UserProfile entity on our side.

    :param user_profile: Required, should be a user profile id or user screen name or user platform id
    :param platform: Used to construct user profile id.
    """
    try:
        return UserProfile.objects.get(user_profile)
    except UserProfile.DoesNotExist:
        u_p_id = SocialProfile.make_id(platform.title(), user_profile)
        try:
            return UserProfile.objects.get(u_p_id)
        except UserProfile.DoesNotExist:
            try:
                return UserProfile.objects.get(native_id=user_profile)
            except UserProfile.DoesNotExist:
                try:
                    return SocialProfile.objects.get(user_name=user_profile)
                except SocialProfile.DoesNotExist:
                    return user_profile

                
def post_resolver(post, platform):

    assert platform in ('twitter', 'facebook')
    try:
        return Post.objects.get(post)
    except Post.DoesNotExist:
        return None



def default_resolver(data, platform, logged_in_user):
    assert platform
    assert logged_in_user
    return data


# Mapping between resolvers who will resolve task parameter to actual state if needed.
# for example if task need channel object, not channel id, we need to resolve if first,
# and then put to the task. So actually there is the place where attribute and resolvers
# will be mapped.
# I expect that attribute data will be provided in that form
# { 'attribute_key_which_used_to_get_actual_resolve' : ['resolver_param1', 'resolver_param2',...]

ATTR_RESOLVER_MAPPING = {
    'channel': channel_resolver,
    'user': user_resolver,
    'user_profile': user_profile_resolver,
    'post': post_resolver
}


class RPCTaskExecutor(object):

    def __init__(self, task, platform, params):
        self.user = authenticate_api_user(params)
        self.params = params
        self.task = task
        self.platform = platform

    def execute(self):
        result = self.task.sync(**self.__resolve_parameters())
        if self.platform == 'twitter':
            return tweepy_entity_to_dict(result)
        return result

    def __resolve_parameters(self):
        try:
            result = {}
            for key, val in self.params.iteritems():
                resolver = ATTR_RESOLVER_MAPPING.get(key, default_resolver)
                result[key] = resolver(val, self.platform, self.user)
            return result
        except Exception, e:
            raise exc.InvalidParameterConfiguration(e.message)


class RPCAPIView(BaseAPIView):
    endpoint = 'commands/<platform>/<name>'

    @api_request
    def dispatch_request(self, user, platform=None, name=None, **kwargs):
        """ Perform the RPC command by the platform and command name"""
        if not platform:
            raise exc.ResourceDoesNotExist("A 'platform' parameter is required")
        if not name:
            raise exc.ResourceDoesNotExist("A 'name' parameter is required")
        if platform not in TASK_MAPPING:
            raise exc.InvalidParameterConfiguration("Unsupported platform '{}'".format(platform))
        if name not in TASK_MAPPING[platform]:
            raise exc.InvalidParameterConfiguration("Unsupported {} command '{}'".format(platform, name))

        task = TASK_MAPPING[platform][name]
        data = _get_request_data()

        if 'media' in data and name in {'update_status', 'update_with_media', 'wall_post'}:
            data['media'] = make_temp_file(data['media'])

        #data = request.json
        executor = RPCTaskExecutor(task, platform, data)
        return dict(item=executor.execute())

    @classmethod
    def register(cls, app):
        view_func = cls.as_view('rpc')
        app.add_url_rule(cls.get_api_url(), view_func=view_func, methods=["GET", "POST"])
