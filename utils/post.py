# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import re
from datetime import timedelta
from string import ascii_letters, digits

from solariat_bottle.settings import get_var, LOGGER, AppException

from bson.dbref    import DBRef
from bson.objectid import ObjectId
from solariat.utils.lang.support import get_lang_code, LANG_MAP
from solariat.utils.lang.detect import Language, detect_lang, LanguageDetectorError


def normalize_screen_name(screen_name):
    if screen_name.startswith('@'):
        return screen_name.lower()
    else:
        return '@%s' % screen_name.lower()


def make_shard_prefix(key, prefix_len=6):
    """key is Twitter/Facebook post id
    Returns last `prefix_len` chars of key in reversed order.
    """

    # In order to shard effectively, we want to avoid any patterns
    # with a regularized increment or decrement
    assert prefix_len < len(key), key

    prefix = ''
    for i in range(-prefix_len, 0):
        if i % 2 == 0:
            prefix = prefix + key[i]
        else:
            prefix = key[i] + prefix

    return prefix #key.zfill(prefix_len)[:-prefix_len-1:-1]


def make_id(base_id, suffix=""):
    '''
    Returns an id suitable for sharding.
    '''
    if not base_id:
        base_id = '%s/posts/%s' % (
            get_var('HOST_DOMAIN'),
            str(ObjectId()))

    base_id = str(base_id)
    key = filter(
        lambda s:s in ascii_letters or s in digits,
        base_id)

    return "%s:%s%s" % (make_shard_prefix(key), base_id, suffix)


def replace_special_chars(s):
    #dots in dict keys not accepted by pymongo
    return s.replace('.', '')


def more_like_post(post, channel):
    """
    Returns a queryset of similar posts in a given channels.
    Similarity determined by list of topics and intentions of the initial post.
    Note that we are looking for posts that are similar, but with opposite
    status, since we want to re-lable
    """
    from solariat_bottle.db.post.base    import Post
    from solariat_bottle.db.speech_act   import SpeechActMap
    from solariat_bottle.db.channel.base import Channel
    from solariat_bottle.db.conversation import Conversation

    from solariat.utils.timeslot import Timeslot, DURATION_DAY

    topics        = []
    intention_ids = []
    channel = Channel.objects.ensure_channels([channel])[0]
    assignment = post.get_assignment(channel)
    if channel.is_smart_tag:
        # for smart tags lookup similar posts in parent channel
        parent_channel = Channel.objects.get(channel.parent_channel)
        status = [SpeechActMap.POTENTIAL, SpeechActMap.ACTIONABLE, SpeechActMap.ACTUAL, SpeechActMap.REJECTED]
    else:
        parent_channel = channel
        status = [SpeechActMap.POTENTIAL]
        if assignment in SpeechActMap.ASSIGNED:
            ''' Postitive assignment could cause a more precise classification
            of a Potential post and could revert the assignment for Rejected
            posts
            '''
            status.append(SpeechActMap.REJECTED)
        elif assignment in {'rejected', 'discarded'}:
            ''' Conversely, may reject potential posts and may cause a reversion
            of prior allocation for Actionable
            '''
            status.append(SpeechActMap.ACTIONABLE)
        else:
            raise AppException("An internal state is not expected: %s. Please contact support for assistance." % assignment)

    for sa in post.speech_acts:
        topics.extend(sa['intention_topics'])
        intention_ids.append(sa['intention_type_id'])

    # The basic post lookup that just searches for the latest objects
    res, more_posts_available = Post.objects.by_time_point(
                                    parent_channel,
                                    ['__ALL__'],
                                    from_ts   = Timeslot(post.created_at-DURATION_DAY),
                                    to_ts     = Timeslot(post.created_at+timedelta(hours=1)),
                                    status    = status,
                                    intention = intention_ids,
                                    languages = [post.language],
                                    limit     = 10)
    res = set(res)

    if (channel.is_smart_tag):
        # Part of new re-labeling. If tag for a post is rejected, we should
        # go through all posts from the post conversation and through first
        # RESPONSE_DEPTH_FACTOR responses containing the tag
        service_channel = get_service_channel(channel)
        if service_channel:
            conversations = Conversation.objects.lookup_conversations(service_channel, [post])

            if len(conversations) == 1:
                # First extend with all other posts from this conversation that have that tag
                # assigned to them
                res |= set([p for p in Post.objects(id__in=list(conversations[0].posts))
                              if (str(p.id) != str(post.id) and str(channel.id) in p.tag_assignments)])
        # Now go through the first RESPONSE_DEPTH_FACTOR responses which have that tag assigned

    elif (not channel.is_smart_tag and
            SpeechActMap.STATUS_MAP[post.get_assignment(channel)] in [SpeechActMap.ACTIONABLE, SpeechActMap.REJECTED]):
        # In case we reject a post, go through all the posts for the first RESPONSE_DEPTH_FACTOR responses from
        # the same service channel
        channels = [channel]
        if channel.parent_channel is not None:
            service_channel   = Channel.objects.get(id=channel.parent_channel)
            channels.append(service_channel)
        channel_filter = [ c.id for c in channels ]
        channel_filter_refs = [DBRef('Channel', ch) for ch in channel_filter]
        if SpeechActMap.STATUS_MAP[post.get_assignment(channel)] == SpeechActMap.REJECTED:
            target_status = [SpeechActMap.POTENTIAL, SpeechActMap.ACTIONABLE]
        else:
            target_status = [SpeechActMap.POTENTIAL, SpeechActMap.REJECTED]
    return list(res)


def update_channel_fit(channel, post):
    '''
    Will re-evaluate and reset the channel/post relationship,
    returning the (has_changed, new_value)
    '''

    # If there is a change, we have to do something about it
    def has_changed(from_status, to_status, channel):

        if from_status == to_status:
            return False

        if channel.is_smart_tag:
            ASSIGNED = {'highlighted', 'starred'}
            REJECTED = {'assigned', 'discarded', 'rejected'}
            if from_status in ASSIGNED and to_status in ASSIGNED:
                return False
            if to_status in REJECTED and from_status in REJECTED:
                return False

        return True

    # Compute the new status
    current_status = post.get_assignment(channel, tags=True)
    new_status, _channel = channel.apply_filter(post)

    if has_changed(current_status, new_status, channel):
        post._handle_filter([channel], new_status, filter_others=False, update_classifier_stats=False)
        return (True, current_status, new_status)

    return (False, current_status, new_status)


def filter_similar_posts(post, channel_id, logger, update_classifier_stats=True):
    '''
    Do the work of filtering the posts and return what has been filtered
    '''
    from solariat_bottle.db.channel.base import Channel
    channel = Channel.objects.get(id=channel_id)

    posts = {'discarded':[],
             'highlighted':[]}

    post_counter = 0

    #debug status
    status = post.get_assignment(channel, tags=True)
    logger.debug("Initial post: Status: %s ID: %s Text: %s Channel: %s", status, post.id, post.plaintext_content, channel.title)  # TODO [encrypt]: logging post content
    for p in more_like_post(post, channel):
        # Screen this post. Edge case because response filtering on outbound does not adjust the status
        # of the post. So it would still be picked up
        if p.id == post.id or not channel.is_mutable(p):
            continue

        has_changed, old_status, new_status = update_channel_fit(channel, p)
        if has_changed:
            posts.setdefault(new_status, [])
            posts[new_status].append(p)
            #logger.debug("Channel filter applied to post %s: %s with result: %s. WAS: %s",
            #             p.id, p.content, new_status, old_status)
        else:
            #logger.debug("Post %s:' %s' remains %s for channel: %s",
            #    p.id, p.content,  old_status, channel.title)
            pass
        post_counter += 1

    logger.debug("%d posts processed. %s" % (post_counter,
                                             [ (item[0], len(item[1])) for item in posts.items() ]))
    return posts


def tag_similar_posts(user, post, tag, action):
    """Add or remove tag to posts similar to given in parent_channel of tag."""

    for p in more_like_post(post, tag):
        if p.id == post.id \
                or action == 'add' and tag in p.accepted_smart_tags \
                or action == 'remove' and tag not in p.accepted_smart_tags:
            continue

        p._handle_tag_assignment(user, [tag], action, tag_similar=False)


def get_service_channel(channel):
    '''
    Cases:
    1. Service Channel
    2. Smart Tag
    3. Inbound
    4. Outbound
    5. Other

    Tail recursive implementation
    '''
    from solariat_bottle.db.channel.base import Channel
    if hasattr(channel, '_current_service_channel'):
        return channel._current_service_channel

    if channel.is_service:
        return channel
    elif channel.is_dispatchable:
        sc_candidate = channel.get_service_channel()
        if sc_candidate:
            return get_service_channel(sc_candidate)
        else:
            return None
    elif channel.parent_channel == None:
        return None

    parent = Channel.objects.get(id=channel.parent_channel)
    return get_service_channel(parent)


def get_service_channel_memoized(channel):
    fn = get_service_channel
    cache_key = channel.id
    cache_attr = '_cache'

    if not hasattr(fn, cache_attr):
        setattr(fn, cache_attr, {})

    cache = getattr(fn, cache_attr)
    if cache_key not in cache:
        cache[cache_key] = get_service_channel(channel)
    return cache[cache_key]


def update_stats(post, channel, status, action, should_increment=True,
                 should_decrement=True, **kw):
    '''
    The main stats update method when a post changes
    its relation to a channel.
    '''
    from solariat_bottle.db import channel_stats_base
    from solariat_bottle.db import channel_stats
    # we use this key value for smart tags special cases
    # when count should not be updated
    tag_assignment = action != 'update'
    if (should_increment or should_decrement):
        inc_value = 1 if action !='remove' else -1
    else:
        inc_value = 0
    channel_stats_base.post_updated(post, status, channels=[channel], action=action, 
                                    should_increment=should_increment, should_decrement=should_decrement, **kw)
    channel_stats.post_updated(post, status, inc_value, channels=[channel], tag_assignment=tag_assignment, 
                               action=action, **kw)




def extract_signature(post_content):
    """
    Returns signature of the post. For example: '^AB'

    Strips white space at the end.
    Takes only last signature if several are present.
    If more text is after the signature `None` is returned.
    """
    re_signature = re.compile(r'.*(\^\w+)\s*$')
    match_object = re_signature.match(post_content)
    if match_object:
        return match_object.groups()[0]
    else:
        return None


def parse_language(language):
    if isinstance(language, Language):
        lang = language
    elif isinstance(language, (basestring, int)):
        # assume confidence=1.0 and lang is language code or int id
        lang = Language([get_lang_code(language), 1.0])
    elif isinstance(language, dict) and \
            'tag' in language and 'confidence' in language:
        # datasift bot format, e.g. {"tag": "en", "confidence": 0.80}
        lang = Language([language['tag'], language['confidence']])
    else:
        raise TypeError(u"create_post: unexpected type %s "
                        u"for lang keyword argument '%s' " % (
                        type(language), language))

    UNDEFINED = 'und'
    assert lang.lang in LANG_MAP or lang.lang == UNDEFINED, u"Unexpected language: %s" % lang.lang
    return lang


def get_language(post_dict, default=Language(('en', 1.0))):

    if 'lang' in post_dict and post_dict['lang'] not in (None, '', 'auto'):
        try:
            lang = parse_language(post_dict['lang'])
        except (TypeError, AssertionError):
            import logging
            import sys

            logging.warning("post=%s\nlanguage set to default because of %s" % (
                post_dict, sys.exc_info()))
            lang = default
    else:
        text = post_dict['content']
        try:
            lang = detect_lang(text)
        except LanguageDetectorError:
            lang = default
    return lang


def is_retweet(post_data):
    assert isinstance(post_data, dict), \
        u"post_data must be json dict, got '%s'" % post_data

    post_is_retweet = False
    if 'twitter' in post_data:
        source_data = post_data['twitter']
        # if _is_retweeted is specified then rely on it
        if '_is_retweet' in source_data:
            post_is_retweet = source_data['_is_retweet']
        else:
            _has_dict = lambda key: key in source_data and isinstance(source_data[key], dict)
            post_is_retweet = (
                _has_dict('retweet') or  # retweet from datasift
                _has_dict('retweeted_status')  # retweet from public twitter stream
            )
    return post_is_retweet