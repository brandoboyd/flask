# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
from solariat.utils.lang.helper import LingualToken
from solariat.utils.lang.support import LangCode, Support
from solariat_bottle.db.user_profiles.base_platform_profile import UserProfile
from solariat_bottle.utils.posts_tracking import get_logger

from solariat_bottle.db.language import MultilanguageChannelMixin

from solariat_bottle.settings import (
    AppException, get_app_mode, get_var, LOGGER, LOG_LEVEL)
from solariat_bottle.workers  import io_pool
from solariat_bottle.utils.mailer import send_tag_alert_emails
from solariat_bottle.utils.logger import setup_logger
from solariat.utils.timeslot import now, Timeslot


# register all tasks
from solariat_bottle.tasks import nlp
from solariat_bottle.tasks import stats
from solariat_bottle.tasks import twitter
from solariat_bottle.tasks import facebook
from solariat_bottle.tasks import commands
from solariat_bottle.tasks import eventlog
from solariat_bottle.tasks import salesforce
from solariat_bottle.tasks import throughput_test
from solariat_bottle.tasks import predictors
from solariat_bottle.tasks.analysis import journeys_analysis
from solariat_bottle.tasks.analysis import predictors_analysis

# to disable pyflakes warnings:
from solariat_bottle.db.queue_message import QueueMessage

nlp, stats, twitter, facebook, salesforce
commands, eventlog, throughput_test

logger = io_pool.logger

MAX_BATCH_SIZE = 10000 # The actual max batch call for one mongo post fetch
# --- IO-worker initialization ----

@io_pool.prefork  # IO-workers will run this before forking
def pre_import_base():
    """ Master init
        Pre-importing heavy modules with many dependencies here
        to benefit from the Copy-on-Write kernel optimization.
    """
    logger.info('pre-importing heavy modules')

    import solariat_bottle.app

    import solariat_bottle.db.user
    import solariat_bottle.db.post.utils
    import solariat_bottle.db.account
    import solariat_bottle.db.speech_act
    import solariat_bottle.db.conversation
    import solariat_bottle.db.channel.utils
    import solariat_bottle.db.channel_topic_trends
    import solariat_bottle.db.tracking

    import solariat_bottle.utils.post
    import solariat_bottle.utils.tracking
    import solariat_bottle.utils.id_encoder

    # to disable a pyflakes warnings
    del solariat_bottle


# --- utils ---

@io_pool.task
def _resolve_channels(post_user_profile, channels, kw):
    """ Accepts an iterable of channels in various forms --
        Channel objects, string ids, ObjectIds.
        Returns a tuple (channels, service_channels)
    """
    from solariat_bottle.db.post.base import (
        find_primitive_channels, resolve_service_channels
    )
    if kw and kw.get('facebook'):
        from solariat_bottle.db.post.facebook import lookup_facebook_channels

        fb_channels = lookup_facebook_channels(kw['facebook'])
        if fb_channels:
            channels = fb_channels
    channels = find_primitive_channels(channels, post_user_profile)
    return resolve_service_channels(channels)


def _obtain_user_profile(user, account, platform,
        actor_id=None, profile=None, is_inbound=True, no_profile=False):
    """ Returns a <UserProfile>
    """
    # LOGGER.debug("_obtain_user_profile(%s, %s,\n\tprofile=%s\n\tactor_id=%s\n)" % (user, platform, profile, actor_id))

    # TODO:
    # change the way we obtaining profile
    # 1. if UserProfile and NOT actor_id: as it is at the moment, find DynProfileClass by linked_profiles
    # 2. if NOT UserProfile and actor_id: get DynProfileClass, find UserProfile in linked_profiles
    # 3. if both present, check they are linked
    # 4. if both absent, create both, link



    from bson.objectid import ObjectId
    from solariat_bottle.db.user_profiles.user_profile import UserProfile

    # TODO: should we check platform profile in customer_profile.linked_profiles first?

    if isinstance(profile, dict):
        get     = profile.get
        profile = UserProfile.objects.upsert(
            platform, profile_data=dict(
            user_name         = get('user_name', 'anonymous'),
            name              = get('name',              None),
            user_id           = get('user_id', get('id', get('native_id', None))),
            location          = get('location',          None),
            klout_score       = get('klout_score',       None),
            profile_image_url = get('profile_image_url', None),
            platform_data     = get('platform_data',     None)
            )
        )

    elif isinstance(profile, (bytes, ObjectId)):
        profile = UserProfile.objects.find_one(profile)

    elif isinstance(profile, UserProfile) or no_profile:
        pass

    # --- no profile ---

    elif get_var('ON_TEST', False):
        profile = user.user_profile
        if not profile:
            # create a user profile in case of a test post
            profile = UserProfile.objects.upsert(
                platform, dict(
                user_name='anonymous',
                user_id = 'anonymous',  # str(user.id),
                id      = 'anonymous',
                name    = user.email
                )
            )
            user.user_profile = profile
            user.save()

    else:
        profile = UserProfile.objects.upsert(platform, dict(
            id='anonymous',
            user_id='anonymous',
            user_name='anonymous'))

    # use UserProfile.native_id to bind it to a customer or agent profile
    # if such a/c profile doesn't exists, then create it
    if is_inbound:
        DynProfileClass = account.get_customer_profile_class()
    else:
        DynProfileClass = account.get_agent_profile_class()

    # we use directly specified actor_id as ID for dynamic profile
    # if no actor_id is specified, use native_id as ID

    need_save = False
    if actor_id is None:
        actor_id = profile.native_id if profile else ObjectId()

    try:
        dyn_profile = DynProfileClass.objects.get(actor_id)
    except DynProfileClass.DoesNotExist:
        dyn_profile = DynProfileClass(id=actor_id)
        need_save = True

    if profile and not dyn_profile.has_linked_profile(profile):
        dyn_profile.add_profile(profile)

    need_save and dyn_profile.save()

    return dyn_profile, profile


def _set_channel_and_tag_assignments(post):  #{
    '''
    Computes and sets the assignment updates for channels and tags on creation of
    a new post. If a post is from an outbound channel, and this post is in reply
    to another, then there is also an implication for that post. The speech act mapping
    must be updated to enable correct searching of posts from a faceted
    analytics view.

    Keep in mind that we have already computed a first pass of channels
    and tags just by looking at the candidate set.
    '''
    from solariat_bottle.db.speech_act import (
        SpeechActMap, reset_speech_act_keys
    )

    channels = list(post._get_channels())  # copy

    # Also check for smart tags. If we find any, then we want to include them in set
    # of channels to reset
    # LOGGER.info("NOTIFICATION DEBUG: %s", [x.title for x in post.active_smart_tags])
    for tag in post.active_smart_tags:
        assignment, _ = tag.apply_filter(post)
        post.set_assignment(tag, assignment)
        if SpeechActMap.STATUS_MAP[assignment] == SpeechActMap.ACTIONABLE:
            tag.increment_alert_posts_count()
            # LOGGER.info("NOTIFICATION DEBUG: %s; %s, %s", tag.alert_can_be_sent, tag.alert_posts_count, tag.title)
            if tag.alert_can_be_sent:
                send_tag_alert_emails(tag)
                tag.alert_posts_count = 0
            tag.save()
            channels.append(tag)

    # Figure out what the assignment should be for channels.
    # For that we use channel filters.
    # pretty simple, but really they are magic little black boxes :-)
    for channel in channels:
        assignment, _ = channel.apply_filter(post)
        post.set_assignment(channel, assignment)


    agent_channel_map = {}
    for channel in channels:
        # get the service channel for this if you have one
        sc = post.channels_map.get(channel.parent_channel if channel.is_smart_tag else channel.id)

        # Get agent data for this channel and process for them
        agent_data = post.get_agent_data(channel)

        # If no agent data, nothing to do. Note that we will only have agent data
        # If it is a service channel. So after this we know it is
        if not agent_data:
            continue

        # Assert thes properties because
        if sc.outbound != channel.id and not (channel.is_smart_tag and sc.outbound == channel.parent_channel):
            raise AppException("Ouch! Something went wrong with the data. Please contact support for details.")

        # Update agent channel_map
        post.set_reply_context(channel, agent_data)
        agent_id = agent_data['agent']
        agent_channel_map.setdefault(agent_id, []).append(channel)

    # Reset outbound keys and remove from update list
    for agent_id, outbound_channels in agent_channel_map.items():
        reset_speech_act_keys(post, channels=outbound_channels, agent=agent_id, reset_outbound=True)
        for ch in outbound_channels:
            channels.remove(ch)

    # reset SAMs for remaining inbound channels and tags
    if channels:
        reset_speech_act_keys(post, channels=channels)

    post.save()

def _is_channel_active(channel, status_update):
    from solariat_bottle.db.channel.twitter import (
        FollowerTrackingChannel, FollowerTrackingStatus
    )

    check_channel = channel
    if isinstance(channel, FollowerTrackingStatus):
        check_channel = FollowerTrackingChannel.objects.get(channel.channel)

    if check_channel.status == 'Active' and \
       check_channel.status_update == status_update:
        return True

    return False

def _check_account_volume(user, account):
    ''' Handles the email warnings for volume thresholding.
        Returns a boolean flag to indicate that the monthly volume threshold
        has been exceeded.
    '''
    if not account.package or account.package.name == "Internal":
        return False
    if account.is_threshold_surpassed_sent:
        return True

    from solariat_bottle.db.account import (
        account_stats, VOLUME_NOTIFICATION_THRESHOLD,
        THRESHOLD_WARNING, THRESHOLD_SURPASSED_WARNING
    )

    volume_limit = account.package.volume
    month_start, month_end = Timeslot(level='month').interval
    posts = account_stats(
        account,
        user,
        start_date = month_start,
        end_date   = month_end
    )
    number_posts    = posts.get('number_of_posts')
    warning_limit   = account.volume_warning_limit
    surpassed_limit = account.volume_surpassed_limit

    send_warning = False

    if number_posts >= warning_limit and number_posts < surpassed_limit:
        if not account.is_threshold_warning_sent:
            # Send warning email
            send_warning = True
            percentage = str(VOLUME_NOTIFICATION_THRESHOLD["Warning"]) + "%"
            warning = THRESHOLD_WARNING

    elif number_posts >= surpassed_limit:
        if not account.is_threshold_surpassed_sent:
            # Send surpassed email
            send_warning = True
            percentage = str(VOLUME_NOTIFICATION_THRESHOLD["Surpassed"]) + "%"
            warning = THRESHOLD_SURPASSED_WARNING

    if send_warning:
        from solariat_bottle.utils.mailer import send_account_posts_limit_warning
        account.set_threshold_warning(warning)
        for admin in account.admins:
            send_account_posts_limit_warning(admin, percentage, volume_limit)

    return False


def _check_account_daily_volume(user, account):
    return account.check_daily_volume(user)


# --- Base I/O tasks ----

@io_pool.task
def create_post(user, sync=False, **kw):
    """ Creates a proper platform Post given a user and post components.
        Special args:
        sync - <bool:default=False> forces synchronous postprocessing
        skip_acl_check - <bool:default=False> creates post w/o checking acl permissions on parent channel (e.g. bots)
    """
    """ Creates a proper platform Post given a user and post components.

        Special args:

        sync - <bool:default=False> forces synchronous postprocessing
    """
    # Set user in thread local storage
    from solariat_bottle.db.user import set_user
    set_user(user)

    from solariat_bottle.db.post.utils   import get_platform_class
    from solariat_bottle.utils.post      import get_language
    from solariat_bottle.db.channel.base import Channel
    from solariat_bottle.utils.posts_tracking import log_state, PostState, get_post_natural_id

    log_state(kw.get('channel', kw.get('channels', None)), get_post_natural_id(kw), PostState.DELIVERED_TO_TANGO)

    post_lang = get_language(kw)
    if post_lang.support_level == Support.NO:
        logger.info("Detect message for unsupported language: %s" % post_lang.lang)
        logger.info("Unsupported message value is: %s" % str(kw))
        return
    else:
        kw['lang'] = post_lang
    kw    = normalize_post_params(user, kw)
    klass = get_platform_class(kw['_platform'], event_type=kw['event_type'])

    # we have channels resolved in normalize_post_params
    channels = kw['channels']
    accounts = set([ch.account for ch in channels])
    for account in accounts:
        if _check_account_volume(user, account):
            msg = u"Account '{} ({})' has reached its monthly volume threshold.".format(account.name, account.id)
            LOGGER.warning(msg)
        if _check_account_daily_volume(user, account):
            msg = u"Account '{} ({})' has reached its daily volume threshold.".format(account.name, account.id)
            LOGGER.warning(msg)

    return klass.objects.create_by_user(user, safe_create=True, sync=sync, **kw)

@io_pool.task
def normalize_post_params(user, kw):
    """ Concurrently prepares parameters for post creation

        Returns a modified keyword <dict> with the following changes:

        - channel       (removed)
        - channels      (set)
        - user_profile  (set)
        - speech_acts   (set)
        - message_type  (removed)
        - _message_type (set)
        - _platform     (set)
        - event_type    (set) NEW
    """
    from solariat_bottle.api.exceptions import ForbiddenOperation
    from solariat.db.fields import ValidationError
    from solariat_bottle.db.events.event_type import BaseEventType
    from solariat_bottle.db.post.utils   import get_platform_class, POST_PLATFORM_MAP

    spawn = io_pool.executor.spawn
    get, pop = kw.get, kw.pop

    channels = set(pop('channels', []))
    _channel = pop('channel', None)
    _channel and channels.add(_channel)

    profile     = get('user_profile', None)
    content     = get('content',      None)
    speech_acts = get('speech_acts',  None)
    user_tag    = pop('user_tag',     None)
    msg_type    = pop('message_type', None)
    lang        = get('lang', None)
    event_type  = pop('event_type', None)

    if not content:
        content = ''
        kw['content'] = ''
        # raise ValidationError("no content")

    if not profile and user_tag:
        # legacy wrapper
        profile = dict(user_name=user_tag)

    if msg_type is not None:
        if isinstance(msg_type, str):
            from solariat_bottle.db.post.base import Post
            for key, val in Post.MESSAGE_TYPE_MAP.iteritems():
                if val == msg_type:
                    msg_type = key
                    break
        if not isinstance(msg_type, (int, long)):
            raise ValidationError('bad message_type %r' % msg_type)
        kw['_message_type'] = msg_type

    profiling = get_var('PROFILING')
    if not profiling:
        # resolve channels and extract intentions concurrently
        channel_task = _resolve_channels.async(profile, channels, kw)
    else:
        channels, _ = _resolve_channels(profile, channels, kw)

    if speech_acts is None:
        # it's fast so we make a direct call here
        kw['speech_acts'] = nlp.extract_intentions(content, lang=lang.lang if lang else None)

    if not profiling:
        channels, _ = channel_task.result()

    if not channels:
        raise ValidationError("Channel(s) must be provided. Only received data %s" % kw)

    platforms = set(c.platform for c in channels)
    if len(platforms) != 1:
        raise ValidationError(
            "All channels must belong to the same platform, "
            "got: %s. Received data: %s" % (platforms, kw)
        )
    platform = platforms.pop()

    # fill event type for static events, until we have 1 event per platform
    if not event_type:
        if platform in POST_PLATFORM_MAP:
            event_type = BaseEventType.objects.get_by_user(user, platform=platform)
        else:
            raise ValidationError("event_type is required for dynamic platform: %s" % platform)
    # check if event type exists, if it is specified
    elif isinstance(event_type, basestring):
        if BaseEventType.SEP in event_type:  # full name of event type
            _p, _et = BaseEventType.parse_display_name(event_type)
            if _p != platform:
                raise ValidationError('event_type:"%s" platform is different from channel:"%s"' % (
                    event_type, platform
                ))
            event_type = _et

        event_type = BaseEventType.objects.find_one_by_user(
            user, platform=platform, name=event_type)

    # normalize channels value (code returned to request proper customer or agent profile in 1 shot)
    is_inbound_vals = list({ch.is_inbound for ch in channels})
    if len(is_inbound_vals) > 1:
        # outbount channel exists after _resolve_channels, so it might be outbound
        is_inbound = False
    else:
        is_inbound = is_inbound_vals[0]

    # if len(is_inbound_vals) > 1:
    #     channels = filter(lambda x: not x.is_inbound, channels)
    #     channels = [channels[0]]
    # # lets create proper is_inbound value
    # is_inbound_vals = [ch.is_inbound for ch in channels]
    # is_inbound_vals = list(set(is_inbound_vals))
    # assert 1 == len(is_inbound_vals), is_inbound_vals
    # is_inbound = is_inbound_vals[0]

    # Can assume channels is a list of objects here because it is accessed as such above in order
    # to construct list of platforms
    if platform != 'VOC':
        dyn_profile, platform_profile = _obtain_user_profile(
            user,
            channels[0].account,
            platform,
            kw.get('actor_id'),
            profile,
            is_inbound=is_inbound,
            no_profile=not event_type.is_static,
        )

    for c in channels:
        if not c.can_view(user):
            raise ForbiddenOperation("User %s does not have permissions on channel %s" % (user.email, c.title))

    kw['channels']     = channels
    kw['_platform']    = platform
    kw['event_type']   = event_type
    if platform != 'VOC': # if it's VOC we have NPSProfile, and hence we don't need to create user_profile
        if platform_profile:    # no platform_profile for dynamic events
            kw['user_profile'] = platform_profile
        kw.setdefault('actor_id', dyn_profile.id)  # bind event to dynamic profile

    return kw

@io_pool.task(result='ignore')
def postprocess_new_post(user, post, add_to_queue):
    """ Basic post processing for any new posts received in the system.
        Create Response for the post, upsert conversation and handle stats processing
    """
    # Link to Conversations per service channel
    for sc in post.service_channels:
        sc.post_received(post)

    old_val = post.accepted_smart_tags
    _set_channel_and_tag_assignments(post)
    if old_val != post.accepted_smart_tags:
        post.apply_smart_tags_to_journeys()

    #update post's channels languages
    for channel in post._get_channels():
        if isinstance(channel, MultilanguageChannelMixin):
            channel.add_post_lang(post)

    # Update Stats
    from solariat_bottle.db import channel_stats, channel_stats_base
    channel_stats.post_created(post)
    channel_stats_base.post_created(post)

    # Submit posts to the queue, is Post's service channel attached to it
    if add_to_queue:
        for channel in post.service_channels:
            if channel.queue_endpoint_attached:
                get_logger(channel).info("Pushed message to queue, qmp:post_id=%s, qmp:channel_id=%s" % (post.id, channel.id))
                QueueMessage.objects.push(post, str(channel.id))

                if channel.remove_personal:
                    remove_personal_data(post)


def remove_personal_data(post):
    # clean direct messages only
    if post.is_pm:
        message = 'The content of this message was deleted'
        post.content = message
        post.speech_acts = [{'content': message,
                             'intention_type_id': '1',
                             'intention_type': 'Junk',
                             'intention_topics': [],
                             'intention_topic_conf': 1.0,
                             'intention_type_conf': 1.0
                             }]
        post.punks = []
        post.actor_id = UserProfile.anonymous_profile().id
        # post.user_profile = UserProfile.anonymous_profile()
        # post.extra_fields = {}
        ef = post.extra_fields
        if 'facebook' in ef and '_wrapped_data' in ef['facebook'] and 'message' in ef['facebook']['_wrapped_data']:
            post.extra_fields['facebook']['_wrapped_data']['message'] = message

        logger.info("Removed personal data from post: " + str(post.id))
        post.save()


@io_pool.task(result='ignore')
def filter_similar_posts(post, channel_id):
    """
    This task starts on post reject/star action,
    applies Channel classifier to posts similar to starred/rejected one.
    """
    from solariat_bottle.utils.post import filter_similar_posts as filter_similar

    filter_similar(post, channel_id, logger)

@io_pool.task(result='ignore')
def clear_expired_assignments(channel_filter_refs):
    """
    Clear the assignments for all `channel_filter_refs` that have expired.
    """
    from solariat_bottle.db.response     import Response

    Response.objects.coll.update(
        {
            Response.channel._db_field               : {'$in' : channel_filter_refs},
            Response.assignee._db_field              : {'$ne' : None},
            Response.assignment_expires_at._db_field : {'$lt' : now()},
        },
        {
            '$set' : {Response.assignee._db_field: None}
        },
        multi = True
    )

@io_pool.task(result='ignore')
def handle_post_response(user, resp, matchable, dry_run=False, posted_matchable='first',
                         prefix='', suffix='', post_id=None, response_type=None):
    # post_id is what came from frontend
    # it is NOT necessary the latest in the conversation
    from solariat_bottle.commands.engage import create_post_match
    from solariat_bottle.utils.redirect  import gen_creative
    # post should be done by the user calling the function
    # otherwise, if we use resp.origin_user, that user may have no permission to post
    postmatch = create_post_match(user, resp, matchable)

    if suffix:
        creative = "%s %s" % (gen_creative(resp.matchable, postmatch), suffix)
    else:
        creative = gen_creative(resp.matchable, postmatch)
    if prefix:
        addressee = "@" + prefix
    else:
        addressee = ''

    # Update response
    # import ipdb; ipdb.set_trace()
    try:
        # we get the post to reply to from arguments
        # if none is specified, from response object
        if post_id is not None:
            if isinstance(post_id, (str, unicode)) and post_id.isdigit():
                post_id = long(post_id)
            post = resp.POST_CLASS.objects.get(id=post_id)
        else:
            post = resp.latest_post or resp.post
        resp.handle_accept(user, 'posted')
        matchable.reload()
        resp.posted_matchable = posted_matchable
        resp.dispatched_text  = "%s %s" % (addressee, creative)
        resp.save_by_user(user)
        post.reply(dry_run, creative, user, resp.channel, response_type)

        # Update the ranking model with feedback
        matchable.update_ranking_model(post)
    except AppException, exc:
        # Things break. Good to know as much as possible
        logger.error(exc)
        resp.restore()
        raise exc
    except Exception, exc:
        logger.error(exc, exc_info=True)
        resp.restore()
        raise AppException("%s. Reverting to pending state." % str(exc))


@io_pool.task(result='ignore')
def handle_post_reply(user, creative, outbound_channel_id, post_id,
                      dry_run=False, prefix='', suffix='', response_type=None):
    """Reply is different from Response that it is arbitrary text posted to arbitrary channel
    in reply to some post.
    """
    from solariat_bottle.db.channel.base import Channel
    from solariat_bottle.db.post.base import Post
    outbound_channel = Channel.objects.get(id=outbound_channel_id)
    post = Post.objects.get(id=post_id)
    if suffix:
        # suffix is added with space
        creative = "%s%s" % (creative, suffix)
    # prefix is added in send_message
    if outbound_channel.is_dispatchable:
        is_direct = None
        if response_type == 'direct':
            is_direct = True
        elif response_type is not None:
            is_direct = False
        outbound_channel.send_message(dry_run, creative, post, user=user,
                                      direct_message=is_direct)
    else:
        LOGGER.debug('Warning. No post has been dispacthed because the channel %s is not dispatchable.' %
                     outbound_channel.title)
    pass


@io_pool.task(result='ignore')
def extend_trends(channel):
    from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
    from solariat_bottle.utils.id_encoder import (
        pack_components, CHANNEL_WIDTH, TIMESLOT_WIDTH,
        BIGGEST_STATUS_VALUE, BIGGEST_TOPIC_VALUE, BIGGEST_TIMESOLT_VALUE
    )

    logger.info("------------------------")
    if channel.is_migrated:
        logger.info("SKIPPING CHANNEL: %s" % channel.title)
        return

    lower_bound = ChannelTopicTrends.make_id(channel, 0, 0, 0)
    upper_bound = ChannelTopicTrends.make_id(channel, BIGGEST_TIMESOLT_VALUE, BIGGEST_TOPIC_VALUE, BIGGEST_STATUS_VALUE)
    count = ChannelTopicTrends.objects(id__gte=lower_bound, id__lte=upper_bound).count()
    logger.info("CHANNEL START: %s (%s)" % (channel.title, count))

    from solariat.db.fields import BytesField
    l      = BytesField().to_mongo
    limit  = 100
    offset = 0

    while offset <= count:
        logger.info("--> channel: %s offset %s of %s" % (channel.title, offset, count))
        query = ChannelTopicTrends.objects(id__gte=lower_bound, id__lte=upper_bound)
        query = query.skip(offset).limit(100)
        for trend in query:
            channel_num, topic_hash, status, time_slot = trend.unpacked
            channel_ts = pack_components(
                (channel_num, CHANNEL_WIDTH),
                (time_slot,   TIMESLOT_WIDTH),
            )
            ChannelTopicTrends.objects.coll.update(
                {"_id": l(trend.id)},
                {"$set": {"ct": l(channel_ts)}},
                upsert=False
            )
        offset += limit

    channel.is_migrated = True
    channel.save()

    logger.info("CHANNEL END: %s (%s)" % (channel.title, count))


    # l = BytesField().to_mongo

    # for trend in ChannelTopicTrends.objects().limit(limit).skip(offset):
    #     # app.logger.error("TR: %s" % trend.channel_ts)
    #     channel_num, topic_hash, status, time_slot = trend.unpacked
    #     channel_ts = pack_components(
    #         (channel_num, CHANNEL_WIDTH),
    #         (time_slot,   TIMESLOT_WIDTH),
    #     )
    #     res = ChannelTopicTrends.objects.coll.update(
    #         {"_id": l(trend.id)},
    #         {"$set": {"ct": l(channel_ts)}},
    #         upsert=False
    #     )
    # app.logger.error("EXTEND TRENDS: handled: offset: %s" % offset)

@io_pool.task
def get_tracked_channels(platform_name, post_data, keywords=None):
    '''
    Called By: Datasift Bot

    Assume:
    1. The post is in canonical dictionary form.
    2. User is only interested in active channels
    '''
    from solariat_bottle.utils.tracking import lookup_tracked_channels

    return lookup_tracked_channels(platform_name, post_data, keywords, logger=logger)


@io_pool.task
def process_export_task(export_task, user, params=None):
    export_task.reload()
    return export_task.process(user, params)


@io_pool.task
def predictor_model_retrain_task(predictor, model=None):
    create_new_model_version = model.state.is_locked
    return predictor.retrain(model=model, create_new_model_version=create_new_model_version)


@io_pool.task
def predictor_model_upsert_feedback_task(predictor, model=None):
    import traceback
    try:
        return predictor.upsert_feedback()
    except Exception, ex:
        traceback.print_exc()
        predictor.mark_error("Upserting feedback failed with exception: %s" % ex)


@io_pool.task
def async_requests(method, url, **kwargs):
    import requests
    raise_for_status = kwargs.pop('raise_for_status', False)
    response = requests.request(method, url, **kwargs)
    if raise_for_status:
        response.raise_for_status()
    return response
