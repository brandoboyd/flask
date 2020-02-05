# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
from datetime import datetime
from solariat_bottle.db.user_profiles.social_profile import SocialProfile
from solariat_bottle.workers import io_pool


logger = io_pool.logger


# --- IO-worker initialization ----

@io_pool.prefork  # IO-workers will run this before forking
def pre_import_twitter():
    """ Master init
        Pre-importing heavy modules with many dependencies here
        to benefit from the Copy-on-Write kernel optimization.
    """
    logger.info('pre-importing twitter dependencies')

    import tweepy

    import solariat_bottle.db.channel.twitter
    import solariat_bottle.db.channel.utils
    import solariat_bottle.db.post.utils
    import solariat_bottle.db.tracking
    import solariat_bottle.utils.oauth
    import solariat_bottle.utils.tweet

    # to disable a pyflakes warnings
    del solariat_bottle, tweepy


def get_twitter_api(channel, parser=None):
    from solariat_bottle.utils.tweet import TwitterApiWrapper

    api = TwitterApiWrapper.init_with_channel(channel, parser=parser)
    return api


# --- Twitter utils ---
def _send_direct_message(consumer_key, consumer_secret, access_token_key,
                         access_token_secret, status, screen_name):
    """
    Send a twitter direct message using the given application authorization keys
    and access tokens.

    :param status: The actual message we are replying with.
    :param post: The SO post object to which we are replying.
    """
    from solariat_bottle.utils.tweet import err_context, TwitterApiWrapper

    api = TwitterApiWrapper.init_with_settings(
        consumer_key, consumer_secret, access_token_key, access_token_secret)
    # Send a direct message. First follow user, then send actual message.
    if screen_name is None:
        raise Exception("Need inbound DM we are answering to so we can get the targeted username.")

    with err_context() as err_ctx:
        err_ctx.screen_name = screen_name
        err_ctx.status = status

        return api.send_direct_message(screen_name=screen_name, text=status)


# --- Twitter tasks ----
@io_pool.task(result='ignore')
def tw_follow_direct_sender(user, post, profile=None):
    if post.message_type in (1, 'direct') and post.channel.is_inbound:
        # This was a direct message, which means we are following the user
        # Only do this for inbound posts, not much to do for outbound posts.

        user_profile     = profile or post.get_user_profile()
        outbound_channel = post.channel.get_outbound_channel(user)

        if outbound_channel and user_profile and not user_profile.is_friend(outbound_channel):
            outbound_channel.follow_user(user_profile, silent_ex=True)


def get_file_from_media(media):
    from werkzeug.datastructures import FileStorage

    if isinstance(media, tuple):
        filename, filepath = media
        return filename, open(filepath, 'rb')
    elif isinstance(media, FileStorage):
        return media.filename, media.stream
    elif isinstance(media, basestring):
        return media, None
    raise TypeError("Unsupported media type %s" % type(media))


@io_pool.task
def tw_update_status(consumer_key, consumer_secret, access_token_key,
                     access_token_secret, status, status_id=None, post=None,
                     media=None):
    """
    Send a twitter direct message using the given application authorization keys
    and access tokens.

    :param status: The actual message we are replying with.
    :param status_id: The twitter post id to which we are replying to
    :param post: The SO post object to which we are replying.
    """
    import os
    from solariat_bottle.utils.tweet import err_context, TwitterApiWrapper

    api = TwitterApiWrapper.init_with_settings(
        consumer_key, consumer_secret, access_token_key, access_token_secret)

    with err_context() as err_ctx:
        err_ctx.status = status
        if post:
            err_ctx.screen_name = post.user_profile.user_name

        if media is not None:
            filename, f = get_file_from_media(media)
            kwargs = dict(status=status, in_reply_to_status_id=status_id)
            upload_result = api.media_upload(filename, file=f)
            logger.info(u"Uploaded media file %s", upload_result)
            media_id = upload_result.get('media_id_string') or upload_result.get('media_id')
            kwargs.update(media_ids=[media_id])
            status = api.update_status(**kwargs)

            if f:
                try:
                    f.close()
                    os.unlink(f.name)
                except IOError:
                    pass
        else:
            status = api.update_status(status=status, in_reply_to_status_id=status_id)
        return status  # OK


@io_pool.task
def tw_retweet_status(consumer_key, consumer_secret, access_token_key,
                      access_token_secret, status_id, screen_name=None):
    """
    Do a retweet on twitter using the given application authorization keys
    and access tokens.

    :param status_id: The twitter id which we are retweeting
    :param screen_name: The user screen_name (optional) used solely for error handling
    """
    from solariat_bottle.utils.tweet import err_context, TwitterApiWrapper
    from solariat_bottle.tasks.exceptions import TwitterCommunicationException

    api = TwitterApiWrapper.init_with_settings(
        consumer_key, consumer_secret, access_token_key, access_token_secret)

    if not status_id:
        raise TwitterCommunicationException("Trying to retweet a post without a status_id.")

    with err_context() as err_ctx:
        err_ctx.screen_name = screen_name
        return api.retweet(id=status_id)


@io_pool.task
def tw_normal_reply(channel, status, status_id=None, post=None, media=None):
    """
    Send a normal twitter reply to the given post.

    :param channel: The channel from which we are replying with a DM
    :param status: The actual message we are replying with.
    :param status_id: The twitter post id to which we are replying to
    :param post: The SO post object to which we are replying.
    """
    from solariat_bottle.utils.oauth import get_twitter_oauth_credentials

    consumer_key, consumer_secret, _, access_token_key, access_token_secret \
        = get_twitter_oauth_credentials(channel)

    return tw_update_status(
        consumer_key,
        consumer_secret,
        access_token_key,
        access_token_secret,
        status,
        status_id,
        post,
        media
    )


@io_pool.task
def tw_direct_reply(channel, status, screen_name):
    """
    Send a twitter direct message as a reply to the given post.

    :param channel: The channel from which we are replying with a DM
    :param status: The actual message we are replying with.
    :param screen_name: The screen name of the creator of the status we are retweeting
    """
    from solariat_bottle.utils.oauth import get_twitter_oauth_credentials

    (consumer_key, consumer_secret, _,
     access_token_key, access_token_secret) = get_twitter_oauth_credentials(channel)

    return _send_direct_message(consumer_key, consumer_secret,
                                access_token_key, access_token_secret,
                                status, screen_name)


@io_pool.task(result='ignore')
def tw_handle_retweet_response(user, resp, dry_run=False):
    """
    Retweet a given response. This means both an accept of the response
    and a retweet of the latest post from the response.

    :param user: The SO user which is doing the retweet.
    :param resp: The response which we are retweeting.
    """
    resp.handle_accept(user,'retweeted')
    resp.post.share(dry_run, user)
    resp.save()


@io_pool.task
def tw_share_post(channel, status_id=None, screen_name=None):
    """
    Share a twitter post from a given channel.

    :param channel: The SO channle from where we are retweeting
    :param status_id: The twitter id which we are retweeting.
    :param screen_name: The screen name of the creator of the status we are retweeting
    """
    from solariat_bottle.utils.oauth import get_twitter_oauth_credentials

    (consumer_key, consumer_secret, _, access_token_key,
             access_token_secret) = get_twitter_oauth_credentials(channel)

    return tw_retweet_status(
        consumer_key,
        consumer_secret,
        access_token_key,
        access_token_secret,
        status_id,
        screen_name
    )


@io_pool.task(result='ignore', timeout=None)
def tw_count(channel, params=('followers_count', 'friends_count')):
    """
    For the given input channel set the number of followers.
    """
    from solariat_bottle.utils.tweet import err_context

    channel.reload()
    api = get_twitter_api(channel)

    with err_context() as err_ctx:
        err_ctx.screen_name = channel.twitter_handle
        err_ctx.channel = channel

        if channel.twitter_handle:
            user = api.get_user(screen_name=channel.twitter_handle)
        else:
            user = api.me()
        update = {"set__%s" % param: getattr(user, param) for param in params}
        update['w'] = 0
        return channel.update(**update)


def expect_follower_tracking(task_fn):
    from functools import wraps

    @wraps(task_fn)
    def decorated(*args, **kwargs):
        channel = args[0]
        from solariat_bottle.db.channel.twitter import \
            FollowerTrackingChannel, FollowerTrackingStatus

        assert isinstance(channel, (
            FollowerTrackingChannel, FollowerTrackingStatus)), \
            u"Expected follower tracking, got %s" % channel
        return task_fn(*args, **kwargs)

    return decorated


@io_pool.task
@expect_follower_tracking
def tw_scan_followers(channel, status_update, cursor=-1):
    """
    On any switch of a channel to active, syncronize all the followers
    stored on the channel with actual twitter handles.
    """
    from solariat_bottle.utils.tweet import err_context
    from . import _is_channel_active

    channel.reload()
    if not _is_channel_active(channel, status_update):
        channel.update(set__sync_status='idle')
        return

    if cursor == -1:
        channel.update(set__followers_synced=0,
                       set__sync_status_followers='sync')

    api = get_twitter_api(channel)

    with err_context() as err_ctx:
        err_ctx.screen_name = channel.twitter_handle

        kwargs = {'cursor': cursor}
        if channel.twitter_handle:
            kwargs['screen_name'] = channel.twitter_handle
        data, cursors = api.followers_ids(**kwargs)

        if data:
            save_followers(channel, data)
            res = channel.update(inc__followers_synced=len(data))
            (_, cursor) = cursors

            timer = io_pool.tools.Timer(
                10,
                tw_scan_followers,
                args   = (channel, status_update),
                kwargs = {'cursor': cursor}
            )
            timer.start()
            return res
        else:
            return channel.update(set__sync_status='idle')


@io_pool.task(result='ignore')
@expect_follower_tracking
def save_followers(channel, data):
    """
    TODO: PostFilterStream still has twitter_handle used, need
    to refactor it to make it more generic to multiple sources
    like fb/email/chat.
    """
    from solariat_bottle.db.tracking        import PostFilterStream
    from solariat_bottle.db.channel.twitter import \
        FollowerTrackingChannel, FollowerTrackingStatus

    data = [ str(i) for i in data ]
    stream = PostFilterStream.get()

    if isinstance(channel, FollowerTrackingStatus):
        main_channel = FollowerTrackingChannel.objects.get(channel.channel)
        if main_channel.tracking_mode == 'Passive':
            stream.track_passive(data, [main_channel],
                twitter_handle=channel.twitter_handle)
        else:
            stream.track('USER_ID', data, [main_channel],
                twitter_handle=channel.twitter_handle)
    else:
        stream.track('USER_ID', data, [channel],
            twitter_handle=channel.twitter_handle)


@io_pool.task(result='ignore')
@expect_follower_tracking
def tw_drop_followers(channel):
    """
    When switching a channel to inactive, drop all the stored
    followers from the channel from actual twitter tracking.
    """
    from solariat_bottle.db.tracking        import PostFilterStream
    from solariat_bottle.db.channel.twitter import \
        FollowerTrackingChannel, FollowerTrackingStatus

    if isinstance(channel, FollowerTrackingChannel):
        for fts in FollowerTrackingStatus.objects.find(channel=channel.id):
            fts.update(set__followers_synced=0,
                       set__sync_status='idle')
    else:
        channel.update(set__followers_synced=0,
                       set__sync_status='idle')

    stream = PostFilterStream.get()

    if isinstance(channel, FollowerTrackingStatus):
        main_channel = FollowerTrackingChannel.objects.get(channel.channel)
        if main_channel.tracking_mode == 'Passive':
            stream.untrack_channel_passive(main_channel, channel.twitter_handle)
        elif main_channel.tracking_mode == 'Active':
            stream.untrack_channel(main_channel, channel.twitter_handle)

    elif isinstance(channel, FollowerTrackingChannel):
        if channel.tracking_mode == 'Passive':
            stream.untrack_channel_passive(channel)
        elif channel.tracking_mode == 'Active':
            stream.untrack_channel(channel)


@io_pool.task
def tw_create_friendship(consumer_key, consumer_secret, access_token_key,
                             access_token_secret, screen_name):
    """
    Do a twitter follow for the given screen name using the given
    application authorization keys and access tokens.

    :param screen_name: The twitter screen name which we want to follow
    """
    from solariat_bottle.utils.tweet import err_context, TwitterApiWrapper

    api = TwitterApiWrapper.init_with_settings(
        consumer_key, consumer_secret, access_token_key, access_token_secret)

    with err_context() as err_ctx:
        err_ctx.screen_name = screen_name

        return api.create_friendship(screen_name=screen_name)


@io_pool.task
def tw_follow(channel, user_profile, silent_ex=False):
    """
    Task for following a twitter screen name.

    :param channel: Used to grab the twitter credentials we are using for the follow action.
    :param screen_name: The twitter screen name we are going to follow
    :param silent_ex: Optional, if true any exceptions will just be silently ignored
    """
    from solariat_bottle.settings import get_var, LOGGER
    from solariat_bottle.db.user_profiles.user_profile import UserProfile, get_brand_profile_id, get_native_user_id_from_channel
    result = {}
    if not get_var('ON_TEST') and get_var('APP_MODE') == 'prod':
        from solariat_bottle.utils.oauth import get_twitter_oauth_credentials
        (consumer_key, consumer_secret, _,
         access_token_key, access_token_secret) = get_twitter_oauth_credentials(channel)
        try:
            result = tw_create_friendship(consumer_key=consumer_key,
                                          consumer_secret=consumer_secret,
                                          access_token_key=access_token_key,
                                          access_token_secret=access_token_secret,
                                          screen_name=user_profile.screen_name)
        except Exception, ex:
            LOGGER.error("tasks.tw_follow: "  + str(ex))
            if silent_ex:
                result = dict(error=str(ex))
            else:
                raise
    user_profile.add_follower(channel)
    try:
        brand_profile = UserProfile.objects.get(get_brand_profile_id(channel))
    except UserProfile.DoesNotExist:
        brand_profile = UserProfile.objects.upsert('Twitter',
                                                   dict(native_id=get_native_user_id_from_channel(channel)))
    brand_profile.add_friend(user_profile)
    _invalidate_friend_follower_cache_bidirectional(channel, user_profile)
    return result


def _invalidate_friend_follower_cache_bidirectional(channel, user_profile):
    from solariat_bottle.db.user_profiles.user_profile import UserProfile, get_brand_profile_id
    from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel
    from solariat_bottle.utils.tweet import tweepy_cache_id
    from solariat_bottle.utils.cache import MongoDBCache

    cache = MongoDBCache()

    # invalidate self cache
    method_name = 'show_friendship'
    args = ()
    kwargs = {'target_id': user_profile.user_id_int}
    cache_id = tweepy_cache_id(channel.access_token_key, channel.access_token_secret, method_name,
                               args, kwargs)
    cache.invalidate(cache_id)

    # invalidate opposite twitter-user cache
    opposite = EnterpriseTwitterChannel.objects.find_one(twitter_handle=user_profile.screen_name)
    if not opposite:
        return

    user_profile = UserProfile.objects.get(get_brand_profile_id(channel))
    kwargs = {'target_id': user_profile.user_id_int}
    cache_id = tweepy_cache_id(opposite.access_token_key, opposite.access_token_secret, method_name,
                               args, kwargs)
    cache.invalidate(cache_id)


@io_pool.task
def tw_destroy_friendship(consumer_key, consumer_secret, access_token_key,
                              access_token_secret, screen_name):
    """
    Do a twitter unfollow for the given screen name using the given
    application authorization keys and access tokens.

    :param screen_name: The twitter screen name which we want to unfollow
    """
    from solariat_bottle.utils.tweet import err_context, TwitterApiWrapper

    api = TwitterApiWrapper.init_with_settings(consumer_key, consumer_secret, access_token_key, access_token_secret)
    with err_context() as err_ctx:
        err_ctx.screen_name = screen_name

        return api.destroy_friendship(screen_name=screen_name)


@io_pool.task
def tw_unfollow(channel, user_profile, silent_ex=False):
    """
    Task for unfollowing a twitter screen name.

    :param channel: Used to grab the twitter credentials we are using for the unfollow action.
    :param screen_name: The twitter screen name we are going to unfollow
    :param silent_ex: Optional, if true any exceptions will just be silently ignored
    """
    from solariat_bottle.settings import get_var, LOGGER
    from solariat_bottle.db.user_profiles.user_profile import UserProfile, get_brand_profile_id, get_native_user_id_from_channel
    result = {}
    if not get_var('ON_TEST') and get_var('APP_MODE') == 'prod':
        from solariat_bottle.utils.oauth import get_twitter_oauth_credentials
        (consumer_key, consumer_secret, _,
         access_token_key, access_token_secret) = get_twitter_oauth_credentials(channel)
        try:
            result = tw_destroy_friendship(consumer_key=consumer_key,
                                           consumer_secret=consumer_secret,
                                           access_token_key=access_token_key,
                                           access_token_secret=access_token_secret,
                                           screen_name=user_profile.screen_name)
        except Exception, ex:
            LOGGER.error("tasks.tw_unfollow: " + str(ex))
            if silent_ex:
                result = dict(error=str(ex))
            else:
                raise
    user_profile.remove_follower(channel)
    try:
        brand_profile = UserProfile.objects.get(get_brand_profile_id(channel))
    except UserProfile.DoesNotExist:
        brand_profile = UserProfile.objects.upsert('Twitter',
                                                   dict(native_id=get_native_user_id_from_channel(channel)))
    brand_profile.remove_friend(user_profile)
    _invalidate_friend_follower_cache_bidirectional(channel, user_profile)
    return result


def _get_following_relations(channel, screen_name_or_id, clear_cache=False):
    from solariat_bottle.settings import LOGGER
    from solariat_bottle.db.user_profiles.user_profile import UserProfile
    from solariat_bottle.utils.tweet import err_context, CachedTwitterProxy

    platform = 'Twitter'

    def _ensure_user_profile(user_name, screen_id):
        try:
            up_id = SocialProfile.make_id(platform, user_name)
            return UserProfile.objects.get(up_id)
        except UserProfile.DoesNotExist:
            return UserProfile.objects.upsert(platform,
                                              dict(screen_name=user_name,
                                                   user_id=screen_id))

    # Query twitter for relations between brand (represented by channel token) and some screen name or id
    api = get_twitter_api(channel)
    api = CachedTwitterProxy(api, clear_cache=clear_cache)

    with err_context() as err_ctx:
        err_ctx.screen_name = screen_name_or_id

        try:
            user_id = int(screen_name_or_id)
        except ValueError:
            screen_name = screen_name_or_id
            brand_relations, queried_user_relations = api.show_friendship(target_screen_name=screen_name)
        else:
            brand_relations, queried_user_relations = api.show_friendship(target_id=user_id)

        # Update the relations on GSA db side aswell
        LOGGER.info("Got relationships information from twitter.")
        _ensure_user_profile(brand_relations.screen_name, brand_relations.id_str)
        # u_p_client = _ensure_user_profile(queried_user_relations.screen_name, queried_user_relations.id_str)
        _ensure_user_profile(queried_user_relations.screen_name, queried_user_relations.id_str)
        LOGGER.info("Upserted new user profiles from twitter data.")
        return brand_relations, queried_user_relations


@io_pool.task
def is_friend(channel, user_profile):
    from solariat_bottle.db.user_profiles.user_profile import UserProfile

    screen_name_or_id = user_profile
    if isinstance(user_profile, UserProfile):
        screen_name_or_id = user_profile.user_id

    brand_friendship, _ = _get_following_relations(channel, screen_name_or_id)
    return brand_friendship.following


@io_pool.task
def is_follower(channel, user_profile):
    from solariat_bottle.db.user_profiles.user_profile import UserProfile

    screen_name_or_id = user_profile
    if isinstance(user_profile, UserProfile):
        screen_name_or_id = user_profile.user_id

    brand_friendship, _ = _get_following_relations(channel, screen_name_or_id)
    return brand_friendship.followed_by


def tw_get_relations(channel, user_id, method='friends_ids'):
    from solariat_bottle.daemons.twitter.parsers import TwitterUserParser
    from solariat_bottle.utils.tweet import CachedTwitterProxy

    result = []

    user_id = int(user_id)
    api = get_twitter_api(channel)
    api = CachedTwitterProxy(api)
    parse = TwitterUserParser()

    next_cursor = -1
    api_params = {'cursor': next_cursor}
    parse_data = lambda d: d
    if method in ('friends', 'followers'):
        # increase default count from 20 to 200 for models, for ids default count 5000
        # https://dev.twitter.com/rest/reference/get/followers/list
        api_params['count'] = 200
        parse_data = lambda d: map(parse, d)

    api_method = getattr(api, method)
    while next_cursor:
        data, cursors = api_method(cursor=next_cursor)
        _, next_cursor = cursors

        if not data:
            break

        result.extend(parse_data(data))
        if len(result) >= 400:
            break

    return result


@io_pool.task(timeout=None)
def tw_get_friends_ids(channel, user_id):
    return tw_get_relations(channel, user_id, method='friends_ids')


@io_pool.task(timeout=None)
def tw_get_friends_list(channel, user_id):
    return tw_get_relations(channel, user_id, method='friends')


@io_pool.task(timeout=None)
def tw_get_followers_ids(channel, user_id):
    return tw_get_relations(channel, user_id, method='followers_ids')


@io_pool.task(timeout=None)
def tw_get_followers_list(channel, user_id):
    return tw_get_relations(channel, user_id, method='followers')


@io_pool.task
def authenticated_media(media_url, channel=None,
                        base64encoded=True, data_uri=False, api=None):
    from solariat_bottle.utils.tweet import TwitterMediaFetcher

    if api is None:
        api = TwitterMediaFetcher(channel=channel)
    return api.fetch_media(media_url,
                           base64encoded=base64encoded,
                           data_uri=data_uri)


@io_pool.task
def user_info(channel, user_id):
    from solariat_bottle.settings import LOGGER
    from solariat_bottle.db.user_profiles.user_profile import UserProfile
    try:
        user_profile = UserProfile.objects.get(native_id=user_id)
        return user_profile.platform_data
    except UserProfile.DoesNotExist:
        pass

    LOGGER.info("Did not find user profile for id=%s in db. Fetching from twitter" % user_id)
    from solariat_bottle.utils.tweet import err_context, tweepy_user_to_user_profile
    api = get_twitter_api(channel)

    with err_context() as err_ctx:
        err_ctx.screen_name = user_id
        user = api.get_user(user_id)
        tweepy_user_to_user_profile(user)
        return user


@io_pool.task
def channel_user(channel):
    # First attempt is to get it directly from GSA
    from solariat_bottle.settings import LOGGER
    from solariat_bottle.db.user_profiles.user_profile import UserProfile, get_brand_profile_id
    profile_id = get_brand_profile_id(channel)
    try:
        u_p = UserProfile.objects.get(profile_id)
        return u_p.platform_data
    except UserProfile.DoesNotExist:
        pass

    # Couldn't find that profile, fetch from twitter
    LOGGER.info("Did not find channel user for channel_id=%s" % channel)
    from solariat_bottle.utils.tweet import tweepy_user_to_user_profile
    api = get_twitter_api(channel)

    # TODO: Think if we want or not to actually store this as a user profile instance at this point
    user = api.get_user(screen_name=channel.twitter_handle)
    tweepy_user_to_user_profile(user)
    return user


from solariat_bottle.jobs.manager import job, terminate_handler

# @io_pool.task(timeout=None)
@job('tw_recovery')
def tw_process_historic_subscription(subscription):
    from solariat_bottle.daemons.twitter.historics.subscriber import TwitterHistoricsSubscriber
    from solariat_bottle.settings import LOGGER
    from datetime import datetime

    start_time = datetime.now()
    subscriber = TwitterHistoricsSubscriber(subscription)

    LOGGER.info("Subscription %s started at %s." % (subscription.id, start_time))
    subscriber.start_historic_load()
    LOGGER.info("Subscription %s finished. Elapsed time %s" %
                (subscription.id, datetime.now() - start_time))

@terminate_handler(tw_process_historic_subscription)
def update_subscription_status(subscription):
    from solariat_bottle.db.historic_data import SUBSCRIPTION_ERROR
    subscription.update(status=SUBSCRIPTION_ERROR)


@io_pool.task(timeout=None)
def tweepy_get_cursored(api, cursor=-1, method='followers_ids',
                        process_data=lambda: None, channel=None,
                        **call_params):
    """The base for cursored twitter api methods.
    :param api: should support `method` call
    :param cursor: cursor returned from previous api call
    :param method: the api method to be executed
    :param process_data: callback which applies to received data from api call
    :return: None
    :raises: exceptions from handle_tweepy_error
    """
    from solariat_bottle.utils.tweet import err_context

    with err_context() as err_ctx:
        err_ctx.screen_name = channel.twitter_handle

        kwargs = {'cursor': cursor}
        kwargs.update(call_params)
        api_method = getattr(api, method)
        data, cursors = api_method(**kwargs)
        process_data(data, method=method)

        if data:
            (_, cursor) = cursors
            if cursor:
                params = {
                    'cursor': cursor,
                    'method': method,
                    'process_data': process_data,
                    'channel': channel
                }
                params.update(call_params)
                timer = io_pool.tools.Timer(
                    10,
                    tweepy_get_cursored,
                    args   = (api,),
                    kwargs = params
                )
                timer.start()
            else:
                process_data(None, method=method)
        return


def _check_stream_data(stream_data):
    def get_channel(channel_id):
        from solariat_bottle.db.channel.base import Channel
        return Channel.objects.find_one(id=channel_id)

    channel = get_channel(stream_data['channel_id'])
    try:
        assert channel, 'Channel not found: %(channel_id)s' % stream_data
        from solariat_bottle.utils.post import normalize_screen_name

        assert normalize_screen_name(channel.twitter_handle) == \
            normalize_screen_name(stream_data['screen_name']), \
            'Twitter handler has been changed during user stream event handling'
    except AssertionError:
        logger.exception('_check_stream_data(%s)', stream_data)


@io_pool.task
def twitter_stream_event_handler(event_json, stream_data=None):
    """The task handles follow/unfollow events from twitter user stream API.

    :param event_json: dict, decoded json event data from Twitter user stream
    :param stream_data: dict
        {'channel_id': 'str enterprise twitter channel id',  # optional
         'screen_name': 'channel twitter handler'}
    :return: None
    """

    def normalize(username):
        if not (username and isinstance(username, basestring)):
            return username
        if username.startswith('@'):
            return username[1:].lower()
        else:
            return username.lower()

    def upsert_user_profile(data):
        from solariat_bottle.daemons.twitter.parsers import parse_user_profile
        from solariat_bottle.db.user_profiles.user_profile import UserProfile

        return UserProfile.objects.upsert('Twitter', parse_user_profile(data))

    event = event_json['event']
    if event not in {'follow', 'unfollow'}:
        return

    if stream_data is None or 'screen_name' not in stream_data:
        return

    source = upsert_user_profile(event_json['source'])
    target = upsert_user_profile(event_json['target'])
    brand_screen_name = stream_data['screen_name']
    if 'channel_id' in stream_data and stream_data['channel_id']:
        _check_stream_data(stream_data)

    if normalize(source.screen_name) == normalize(brand_screen_name):
        # source is brand -
        # brand initiated follow/unfollow event
        if event == 'follow':
            target.add_follower(source)
        elif event == 'unfollow':
            target.remove_follower(source)
    elif normalize(target.screen_name) == normalize(brand_screen_name):
        # target is brand -
        # twitter user stream does not emit 'unfollow' event
        # from unauthenticated users -
        # but 'follow' event occurs when someone follows the brand
        try:
            assert event == 'follow', "Unexpected 'unfollow' event"
        except AssertionError:
            logger.exception('twitter_stream_event_handler()')
        else:
            source.add_friend(target)
    logger.debug(u'%s *%s* %s', source, event, target)


@io_pool.task
def destroy_message(channel, object_id, message_type):
    api = get_twitter_api(channel)
    if message_type in ("DirectMessage", ):
        return api.destroy_direct_message(id=object_id)
    else:
        return api.destroy_status(id=object_id)


@io_pool.task
def create_favourite(channel, object_id):
    api = get_twitter_api(channel)
    return api.create_favorite(id=object_id)


@io_pool.task
def destroy_favorite(channel, object_id):
    api = get_twitter_api(channel)
    return api.destroy_favorite(id=object_id)

