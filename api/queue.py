from datetime import datetime, timedelta
import json
import requests
import traceback

from solariat.db.fields               import EventIdField
from solariat_bottle.settings         import LOGGER, get_var
from solariat_bottle.api.base         import ModelAPIView, api_request, deprecate
from solariat_bottle.api.posts        import PostAPIView
import solariat_bottle.api.exceptions as exc
from solariat_bottle.db.queue_message import QueueMessage, DEFAULT_LIMIT, DEFAULT_RESERVE_TIME, BrokenQueueMessage
from solariat_bottle.db.channel.base  import Channel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel, GroupingConfig
from solariat_bottle.db.conversation  import Conversation
from solariat_bottle.utils.post       import get_service_channel
from solariat_bottle.db.post.twitter  import TwitterPost
from solariat_bottle.db.post.facebook import FacebookPost
from solariat_bottle.utils.posts_tracking import get_logger
from solariat_bottle.utils.views import parse_bool
from solariat_bottle.wrappers.abc_wrapper import ABCWrapper
from solariat_bottle.wrappers.gse_twitter_wrapper import GSETwitterWrapper
from solariat_bottle.wrappers.gse_facebook_wrapper import GSEFacebookWrapper
from solariat.utils.timeslot import datetime_to_timestamp

WRAPPERS_MAP = {
    TwitterPost: GSETwitterWrapper,
    FacebookPost: GSEFacebookWrapper
}

to_python = EventIdField().to_python


MAX_LIMIT = 10000
MAX_RESERVE_TIME = 1000
PUBLIC_TWEET, DIRECT_MESSAGE, RETWEET, IN_REPLY_TO = 0, 1, 2, 3
DEFAULT_GROUPING_TIMEOUT = GroupingConfig.DEFAULT_GRP_TIMEOUT


def ensure_list(values):
    if type(values) in (unicode, str):
        # Just so we process GET request with query string arguments
        # We're going to deprecate this
        try:
            values = json.loads(values)
        except Exception:
            values = values.split(',')
    return values


def wrap_post(post):
    wrapper = WRAPPERS_MAP.get(post.__class__, ABCWrapper)
    return wrapper(post).data


def is_valid_numb(val, top_bound):
    """ Check that :param val: is a number lower than top_bound
    """
    return isinstance(val, (int, long)) and (0 < val < top_bound)


def safe_parent(post):
    try:
        parent = post.parent
        assert isinstance(parent, PostAPIView.model)
    except (PostAPIView.model.DoesNotExist, AssertionError):
        parent = None
    return parent


def recover_parents_for_2nd_level_comments(comments):
    parent_ids = set()
    from solariat.utils.timeslot import now, datetime_to_timestamp_ms
    from solariat_bottle.utils.cache import MongoDBCache
    from solariat_bottle.settings import FB_COMMENT_PARENT_RECOVERY_THROTTLE

    cache = MongoDBCache(default_timeout=FB_COMMENT_PARENT_RECOVERY_THROTTLE)

    for comment in comments:
        try:
            page_id = comment.native_data['page_id']
            wrapped_data = comment.wrapped_data
            parent_native_id = wrapped_data['parent_id']
            source_id = wrapped_data['source_id']
            source_type = wrapped_data['source_type']
        except (AttributeError, KeyError):
            LOGGER.warning("comment's parent will not be recovered %s" % comment, exc_info=True)
            continue
        entry = (page_id, parent_native_id, source_id, source_type)
        cached_entry = cache.get_entry(str(entry))
        if cached_entry is None or cached_entry.expired():
            if cached_entry and cached_entry.expired():
                LOGGER.info("comment's parent recovery expired %s" % str(cached_entry))
            cache.set(str(entry), datetime_to_timestamp_ms(now()), timeout=FB_COMMENT_PARENT_RECOVERY_THROTTLE)
            parent_ids.add(entry)
        else:
            LOGGER.warning("comment's parent is being recovered  cached_entry: %s" % str(cached_entry))
            continue

    request_data = []
    for page_id, comment_id, source_id, source_type in parent_ids:
        request_data.append({
            'page_id': page_id,
            'comment_id': comment_id,
            'source_id': source_id,
            'source_type': source_type
        })

    if not request_data:
        return

    from solariat_bottle.tasks import async_requests
    from solariat_bottle.app import settings
    from solariat.utils.timeslot import datetime_to_timestamp_ms
    from solariat.cipher.random import get_random_bytes

    request_id = "CR.%s.%s" % (datetime_to_timestamp_ms(datetime.utcnow()), get_random_bytes(2).encode('hex'))
    url = "%s?token=%s&request_id=%s" % (settings.FBOT_URL + '/json/restore-comments', settings.FB_DEFAULT_TOKEN, request_id)

    LOGGER.info("Before request %s", repr(request_data))
    try:
        response = async_requests.ignore('post', url, json={'data': request_data,
                                                            'request_id': request_id},
                                         verify=False, timeout=None, raise_for_status=True)
    except requests.exceptions.HTTPError:
        LOGGER.exception("Can't connect to FBot")
        return False
    else:
        LOGGER.info("Sent request url=%s with data=%s", url, repr(request_data))
        return response


def get_tweet_type(post):
    if post.is_pm:
        return DIRECT_MESSAGE
    if post.is_retweet:
        return RETWEET
    if post.is_reply:
        return IN_REPLY_TO
    return PUBLIC_TWEET


class PostGroup(object):
    __slots__ = ['conversation', 'root_post', 'annotation']

    def __init__(self, conversation, root_post, annotation=None):
        self.conversation = conversation
        self.root_post = root_post
        self.annotation = annotation

    @property
    def timestamp(self):
        return datetime_to_timestamp(self.root_post.created_at)

    @property
    def id(self):
        return "%s:%s" % (self.conversation.id, self.root_post.id)

    def __eq__(self, other):
        return other and isinstance(other, self.__class__) and self.id == other.id

    def __str__(self):
        return "<%s %s [%s]>" % (self.__class__.__name__, id(self), self.id)

    def to_dict(self):
        return dict(
            id=self.id,
            conv_id=str(self.conversation.id),
            post_id=str(self.root_post.id),
            ts=str(self.timestamp),
            annotation=self.annotation)


def get_previous_conversation_posts(current_post, conversation, lookup_limit=10):
    """Returns posts from conversation with created_at date < conversation_posts[0].created_at.
    :param current_post: initial post to compare with
    :param conversation:
    :param lookup_limit:
    :return: sorted list of posts in reversed order
    """
    from solariat_bottle.utils.id_encoder import unpack_event_id
    conv_posts = sorted(map(to_python, conversation.posts + conversation.amplifiers), key=lambda event: unpack_event_id(event)[1])
    prev_conversation_post_ids = []
    post_index = conv_posts.index(to_python(current_post.id))
    if post_index > 0:
        slice_start = post_index - lookup_limit
        if slice_start < 0:
            slice_start = 0
        prev_conversation_post_ids = conv_posts[slice_start: post_index]

    if not prev_conversation_post_ids:
        return []

    sorted_posts = sorted(PostAPIView.model.objects.find(id__in=prev_conversation_post_ids),
                          key=lambda x: x.created_at, reverse=True)
    return sorted_posts


def maybe_group(post, prev_post, conversation, grouping_timeout, group_by_type):
    """Return new PostGroup instance should post be in a separate group, otherwise returns None"""
    group = None
    if (post.created_at - prev_post.created_at).total_seconds() >= grouping_timeout:
        group = PostGroup(conversation, post, 'timeout')
    elif group_by_type and get_tweet_type(post) != get_tweet_type(prev_post):
        group = PostGroup(conversation, post, 'type')
    return group


def find_last_group_in_conversation(current_post, conversation, lookup_limit=10,
                                    grouping_timeout=DEFAULT_GROUPING_TIMEOUT, group_by_type=True):
    sorted_posts = get_previous_conversation_posts(current_post, conversation, lookup_limit)
    prev_group = None

    for post in sorted_posts:
        if conversation.route_post(post) != conversation.route_post(current_post):
            continue
        group = maybe_group(current_post, post, conversation, grouping_timeout, group_by_type)
        if group:
            prev_group = group
            break
        current_post = post

    return prev_group or PostGroup(conversation, current_post, 'initial')


def assign_groups(posts, conversation, grouping_timeout=DEFAULT_GROUPING_TIMEOUT, group_by_type=True, lookup_limit=10):
    current_group = {}

    for post in posts:
        direction = conversation.route_post(post)
        if current_group.get(direction, None) is None:
            current_group[direction] = find_last_group_in_conversation(post, conversation, lookup_limit, grouping_timeout, group_by_type)
        group = maybe_group(post, current_group[direction].root_post, conversation, grouping_timeout, group_by_type)
        if group:
            current_group[direction] = group
        yield post, current_group[direction]


class BaseQueueEntryProcessor(object):

    def process_batch(self, *args, **kwargs):
        raise NotImplementedError("Should be implemented in subclasses.")

    def batch_confirmation(self, batch_token):
        removed = QueueMessage.objects.remove_reserved(batch_token)['n']
        return removed

    def id_based_confirmation(self, post_ids):
        post_ids = ensure_list(post_ids)
        removed = QueueMessage.objects.clear_reserved_id_based(post_ids)['n']
        return removed

    @staticmethod
    def confirm_error_posts(post_ids):
        post_ids = ensure_list(post_ids)
        messages = QueueMessage.objects.find(id__in=post_ids)
        BrokenQueueMessage.objects.save_from_messages(messages)
        removed = QueueMessage.objects.clear_reserved_id_based(post_ids)['n']
        return removed

    def confirm_batch(self, post_ids, batch_token, *args, **kwargs):
        if post_ids:
            removed = self.id_based_confirmation(post_ids)
        elif batch_token:
            removed = self.batch_confirmation(batch_token)
        else:
            removed = 0
        return removed

    def _get_conversations_for_messages(self, messages, channel, lookup_by_amplifiers=False):
        to_mongo = EventIdField().to_mongo
        post_ids = [to_python(message.post_data.get('_id', None)) for message in messages]
        F = Conversation.F
        if lookup_by_amplifiers:
            mongo_post_ids = map(to_mongo, post_ids)
            posts_query = {"$or": [
                {F.posts: {"$in": mongo_post_ids}},
                {F.amplifiers: {"$in": mongo_post_ids}}]}
            posts_query.update({F.channel: channel.id})
            conversations = map(Conversation, Conversation.objects.coll.find(posts_query))
        else:
            conversations = Conversation.objects(posts__in=post_ids, channel=channel.id)
        return conversations

    @staticmethod
    def add_missing_parents(conversation):
        if conversation.add_missing_parents():
            conversation = Conversation.objects.get(conversation.id)
        return conversation


class SinglePostModeProcessor(BaseQueueEntryProcessor):
    DEFAULT_GROUP_LOOKUP_DEPTH = 10

    def process_batch_with_groups(self, messages, channel, lookup_size=DEFAULT_GROUP_LOOKUP_DEPTH, *args, **kwargs):
        log = get_logger(channel)
        conversations = self._get_conversations_for_messages(messages, channel,
                                                             lookup_by_amplifiers=True)
        log.info("[TW GRP] Conversations for messages %s %s %s", conversations, messages, channel)
        queue_post_ids_map = {to_python(message.post_data.get('_id', None)): message for message in messages}
        queue_post_ids = list(queue_post_ids_map.keys())
        lookup_size = int(lookup_size)
        result = []
        grouping_timeout = kwargs.get('grouping_timeout', DEFAULT_GROUPING_TIMEOUT)
        group_by_type = kwargs.get('group_by_type', True)

        for conversation in conversations:
            conv_posts = conversation.posts + conversation.amplifiers
            post_ids = list(set(map(to_python, conv_posts)).intersection(set(queue_post_ids)))
            conversation_posts = PostAPIView.model.objects.find(id__in=[int(p) for p in post_ids])[:]
            conversation_posts = sorted(conversation_posts, key=lambda p: p.created_at)

            log.info('[TW GRP] QMD: post_ids after intersection: %s', post_ids)
            log.info("[TW GRP] QMD: After intersect with conversation left with queue messages: " + str(
                [(p.id, p.plaintext_content) for p in conversation_posts]))

            errors = []
            conversation_posts_with_groups = assign_groups(conversation_posts, conversation,
                                                           grouping_timeout, group_by_type,
                                                           lookup_size)

            for post, group in conversation_posts_with_groups:
                try:
                    base_dict = PostAPIView._format_doc(post, channel)
                    base_dict['source_data'] = wrap_post(post)
                    message = queue_post_ids_map[post.id]
                    base_dict['created_at'] = str(message.created_at)
                    base_dict['id'] = str(message.id)

                    grouping_info = {'timeout': grouping_timeout, 'group_by_type': group_by_type}
                    grouping_info.update(group.to_dict())
                    base_dict.update(
                        group_id=group.id,
                        grouping_info=grouping_info)
                    result.append(base_dict)
                except Exception, ex:
                    LOGGER.error(u"[TW GRP] Can't process message=%s post_data=%s" % (repr(message), unicode(message.post_data)), exc_info=True)
                    message.delete()
                    errors.append(ex)

            log.info("[TW GRP] QMD: After parent included and post_data wrapped: " + str(result))

            if errors:
                LOGGER.error("[TW GRP] Preparing queue posts from conversation %s generated errors: %s" % (conversation, errors))

        return result

    def process_batch_simple(self, messages, channel, *args, **kwargs):
        """
        In single mode we just return each instance as an individual entry without
        caring about conversations at all. The output will be in the form:

        [post_1, post_2, post_3, ... , post_n]
        """
        result = []
        errors = []
        for message in messages:
            try:
                post = PostAPIView.model(message.post_data)
                base_dict = PostAPIView._format_doc(post, channel)
                base_dict['source_data'] = wrap_post(post)
                base_dict['created_at'] = str(message.created_at)
                base_dict['id'] = str(message.id)
                result.append(base_dict)
            except Exception, ex:
                # Delete invalid message and log error
                LOGGER.error(u"Can't process message=%s post_data=%s" % (repr(message), unicode(message.post_data)), exc_info=True)
                message.delete()
                errors.append(ex)
        if errors:
            LOGGER.error("Queue processing for channel %s generated errors %s" % (channel, errors))
        return result

    def process_batch(self, messages, channel, *args, **kwargs):
        if kwargs.get('grouping_timeout', 0) != 0:
            return self.process_batch_with_groups(messages, channel, *args, **kwargs)
        else:
            return self.process_batch_simple(messages, channel, *args, **kwargs)


class ConversationModeProcessor(BaseQueueEntryProcessor):

    DEFAULT_CONVERSATION_SIZE = 5

    def process_post(self, post, channel, conversation_json):
        try:
            base_dict = PostAPIView._format_doc(post, channel)
            post_data = wrap_post(post)
            base_dict['source_data'] = post_data
            base_dict['created_at'] = str(post.created_at)
        except Exception, exc:
            msg_id = QueueMessage.objects.make_id(channel.id, post.id)
            LOGGER.debug("%s in list %s" % (msg_id, conversation_json['post_ids']))
            if msg_id in conversation_json['post_ids']:
                conversation_json['post_ids'] = [m_id for m_id in conversation_json['post_ids'] if m_id != msg_id]
                LOGGER.warning(u"QMD: Removed message id: %s due to processing error. content=%s" % (msg_id, post.plaintext_content))
            else:
                LOGGER.debug("%s not in list %s" % (msg_id, conversation_json['post_ids']))
            raise exc

        return base_dict

    def process_batch(self, messages, channel, lookup_size=DEFAULT_CONVERSATION_SIZE, *args, **kwargs):
        """
        In conversation mode we use conversation information to gather and aggregate posts from
        similar conversations into single entries. The `lookup_size` will tell us the maximum number
        of posts from a conversation (latest ones based on creation time) we should return.

        The output will look like:

        [(root_1, post_1_n-lookup_size, post_1_n-lookup_size + 1, ..., post_1_n), (root_2, post_2_n-lookup_size, ...]
        """
        log = get_logger(channel)
        conversations = self._get_conversations_for_messages(messages, channel)[:]
        log.info("Conversations for messages %s %s %s", conversations, messages, channel)
        queue_post_ids = [to_python(message.post_data.get('_id', None)) for message in messages]
        lookup_size = int(lookup_size)
        result = []

        def check_conversation(conversation):
            """Should conversation be processed.
            Also adds missing parents if there are in system and calls for recover if necessary.
            :returns
            True for inbound PM and non-corrupted conversations.
            False for corrupted public conversations
            """
            conversation = self.add_missing_parents(conversation)
            has_root_post = conversation.has_initial_root_post()
            if has_root_post:
                return True
            else:
                conversation.mark_corrupted()
            # Only skip entirely conversations for public posts. For PMs we don't NEED (although we'd want)
            # to have 'root' post
            log.info("QMD: conversation data %s" % conversation.data)
            return conversation.root_pm_fb_post

        for conversation in conversations:
            if check_conversation(conversation):
                skipped_posts = []
                root_post = conversation.root_post
                root_post_id = root_post and root_post.id
                if not root_post_id:
                    LOGGER.warning("QMD: %s has no root post. channel=%s" % (
                        conversation, conversation.service_channel))

                post_ids = list(set([to_python(p_id) for p_id in conversation.posts]).intersection(set(queue_post_ids)))[-lookup_size:]
                if root_post_id:
                    post_ids.insert(0, root_post_id)
                conversation_posts = PostAPIView.model.objects.find(id__in=[int(p) for p in post_ids])[:]
                conversation_posts = sorted(conversation_posts, key=lambda p: p.created_at)
                log.info('QMD: post_ids after intersection: %s', post_ids)
                log.info("QMD: After intersect with conversation left with queue messages: " + str([(p.id, p.plaintext_content) for p in conversation_posts]))

                parent_included_posts = []
                is_pm = False
                for post in conversation_posts:
                    is_pm = post.is_pm
                    if is_pm:
                        if post.id in queue_post_ids:
                            # don't include parent for PMs
                            # return only pms from set(queue_post_ids & conversation_ids)
                            parent_included_posts.append(post)
                    else:
                        parent = safe_parent(post)
                        if parent is None and isinstance(post, FacebookPost) and post.is_second_level_reply:
                            log.info("QMD: skipping post %s %s because no parent found" % (post, post.native_id))
                            skipped_posts.append(post)
                            continue
                        if parent and parent.id not in post_ids:
                            parent_included_posts.extend([parent, post])
                        else:
                            parent_included_posts.append(post)

                conversation_posts = parent_included_posts

                if is_pm and root_post_id in post_ids:
                    post_ids.remove(root_post_id)

                if skipped_posts:
                    log.info("QMD: skipped posts %s" % skipped_posts)
                    # do not return the root post if it's the only one left after skipping other posts
                    if len(conversation_posts) == 1 and conversation_posts[0] == root_post and root_post_id not in queue_post_ids:
                        post_ids.remove(root_post_id)
                        conversation_posts = []
                    # recover conversation posts
                    recover_parents_for_2nd_level_comments(skipped_posts)
                    # remove skipped post ids from post_ids list, so that
                    # they would not be cleared from queue upon confirmation by ids
                    skipped_post_ids = set(p.id for p in skipped_posts)
                    for post_id in skipped_post_ids:
                        post_ids.remove(post_id)
                    # reset batch token to not remove skipped messages on confirmation by batch_token
                    skipped_messages = [message for message in messages
                                        if to_python(message.post_data.get('_id', None)) in skipped_post_ids]
                    QueueMessage.objects.reset_reservation(skipped_messages)

                log.info("QMD: After checking parent left with queue messages: " + str([(p.id, p.plaintext_content) for p in conversation_posts]))
                # We add the list of ALL post ids from this conversation up to this point so that
                # when we receive a confirmation for this batch, we will remove ALL posts from this conversation
                # that we already processed. This will make it easier to safeguard against situations like following:
                #
                # There are 10 posts from same conversation in queue, you fetch with lookup_size=5
                # We return you the LATEST posts always, so your initial fetch will get you posts [5:10]
                # If you just confirm those and there is still be data in queue from same conversation
                # you will get them twice
                if not conversation_posts:
                    continue
                conversation_json = {'post_data': [],
                                     'id': str(conversation.id),
                                     'post_ids': [QueueMessage.objects.make_id(channel.id, p_id)
                                                  for p_id in post_ids]}
                errors = []
                created_all_by_admin = True
                for post in conversation_posts:
                    try:
                        base_dict = self.process_post(post, channel, conversation_json)
                        post_data = base_dict['source_data']
                        if post.id in queue_post_ids:
                            created_all_by_admin = created_all_by_admin and post_data.get('created_by_admin')
                        conversation_json['post_data'].append(base_dict)
                    except Exception, ex:
                        errors.append(ex)

                for base_dict in conversation_json['post_data']:
                    base_dict['source_data']['created_by_admin'] = created_all_by_admin
                log.info("QMD: After parent included and post_data wrapped: " + str(conversation_json['post_data']))

                if errors:
                    LOGGER.error("Preparing queue posts from conversation %s generated errors: %s" % (conversation, errors))
                result.append(conversation_json)

        return result

    def batch_confirmation(self, batch_token):
        # This is not safe to do. Unless we do a bunch of extra calls while fetching. Basically we fet a set of posts
        # from the queue, then from that set of posts, we just 'fill in' the last N posts from conversation. If we
        # want to confirm safely based on token, we need to check for those entries in queue and set batch token.
        # Not a big deal but extra db calls that are not really needed since we support id based confirmation.
        raise exc.InvalidParameterConfiguration("Batch confirmation in conversation mode is not supported.")


class RootIncludedModeProcessor(BaseQueueEntryProcessor):

    def process_batch(self, messages, channel, *args, **kwargs):
        """
        Root included mode is kind of a hybrid between conversation and single mode. We return each
        post as an individual entry BUT in addition use conversation data to add the root post for
        the conversation to each individual post.

        The output will look like:

        [(root_1, post_1), (root_2, post_2), ....]
        """
        log = get_logger(channel)
        PostCls = PostAPIView.model
        conversations = self._get_conversations_for_messages(messages, channel)
        queue_post_ids = [to_python(message.post_data.get('_id', None)) for message in messages]
        log.info("QMD root_included: queue_post_ids %s" % queue_post_ids)
        post_root_mapping = {}
        # Just for ease of fetching a root post for a given entry
        for conversation in conversations:
            conversation = self.add_missing_parents(conversation)
            root_post = conversation.root_post
            if root_post is None:
                LOGGER.warning("QMD root_included: %s has no root post. channel=%s" % (
                    conversation, conversation.service_channel))
                conversation.mark_corrupted()
            else:
                for post_id in set(queue_post_ids).intersection(set([to_python(p_id) for p_id in conversation.posts])):
                    post_root_mapping[post_id] = root_post

        result = []
        posts_without_parent = []
        skipped_messages = []
        for message in messages:
            post_dict = {'created_at': str(message.created_at),
                         'id': str(message.id),
                         'post_data': []}

            post_id = to_python(message.post_data.get('_id', None))
            root_post = post_root_mapping.get(post_id, None)

            if root_post is None:
                # Something went wrong. Log what we can and move on
                LOGGER.warning("We could not infer a root post for post %s and channel %s" % (post_id, channel.id))
                skipped_messages.append(message)
                continue

            if str(root_post.id) == str(post_id):
                # Only post in the conversation, let's not return it twice
                post_list = [root_post]
                log.info("QMD root_included: post_id=%s root_post.id=%s" % (post_id, root_post.id))
            else:
                post_object = PostCls(message.post_data)
                is_pm = post_object.is_pm
                if is_pm:
                    post_list = [post_object]
                else:
                    parent = safe_parent(post_object)
                    if parent is None and post_object.is_second_level_reply:
                        LOGGER.warning("We did not find any parent for: %s native_id=%s" % (post_object, post_object.native_id))
                        posts_without_parent.append(post_object)
                        skipped_messages.append(message)
                        continue

                    if parent and parent.id != root_post.id:
                        # Second level comment, add it's first level comment too
                        post_list = [root_post, parent, post_object]
                    else:
                        post_list = [root_post, post_object]
                    log.info("QMD root_included: post_id=%s root_post.id=%s is_pm=%s parent=%s" % (post_id, root_post.id, is_pm, parent))
            log.info("QMD root_included: post_list %s" % post_list)
            errors = []
            created_all_by_admin = True
            for post in post_list:
                try:
                    base_dict = PostAPIView._format_doc(post, channel)
                    post_data = wrap_post(post)
                    if post.id in queue_post_ids:
                        created_all_by_admin = created_all_by_admin and post_data.get('created_by_admin')
                    base_dict['source_data'] = post_data
                    base_dict['created_at'] = str(message.created_at)
                    post_dict['post_data'].append(base_dict)
                except Exception, ex:
                    log.warning("QMD root_included: error wrapping post %s" % post, exc_info=True)
                    errors.append(ex)
            for base_dict in post_dict['post_data']:
                base_dict['source_data']['created_by_admin'] = created_all_by_admin
            if errors:
                LOGGER.error("Preparing posts for queue for channel %s with root included generated errors %s" % (
                    channel, errors))
            result.append(post_dict)

        if skipped_messages:
            # remove batch token from skipped messages so they would remain in queue after batch confirmation
            QueueMessage.objects.reset_reservation(skipped_messages)
        if posts_without_parent:
            LOGGER.warning("Recovering parents for %s", posts_without_parent)
            recover_parents_for_2nd_level_comments(posts_without_parent)

        return result


class PostProcessorFactory(object):

    SINGLE_POST_MODE = "single"
    CONVERSATION_MODE = "conversation"
    ROOT_INCLUDED = "root_included"

    PROCESSORS_MAPPING = {SINGLE_POST_MODE: SinglePostModeProcessor(),
                          CONVERSATION_MODE: ConversationModeProcessor(),
                          ROOT_INCLUDED: RootIncludedModeProcessor()}

    @staticmethod
    def get_processor_instance(mode):
        if mode not in PostProcessorFactory.PROCESSORS_MAPPING:
            raise exc.InvalidParameterConfiguration("Unrecognized fetch mode: %s" % mode)
        return PostProcessorFactory.PROCESSORS_MAPPING[mode]

    @staticmethod
    def process_message_batch(mode, messages, channel, **kwargs):
        processor = PostProcessorFactory.get_processor_instance(mode)
        return processor.process_batch(messages, channel, **kwargs)

    @staticmethod
    def confirm_message_batch(mode, *args, **kwargs):
        processor = PostProcessorFactory.get_processor_instance(mode)
        return processor.confirm_batch(*args, **kwargs)


class QueueAPIView(ModelAPIView):

    model = QueueMessage
    endpoint = 'queue'
    commands = ['fetch', 'confirm', 'count', 'confirm_error']

    @classmethod
    def register(cls, app):
        """ Queue API allows for extra commands, like 'fetch' and 'confirm' """
        view_func = cls.as_view(cls.endpoint)

        url = cls.get_api_url('<command>')
        app.add_url_rule(url, view_func=view_func, methods=["GET", "POST", "PUT", "DELETE"])

    def get(self, command=None, *args, **kwargs):
        """ Allowed commands are routed to the _<command> method on this class """
        return deprecate(self.post(command, *args, **kwargs),
                         deprecation_message="GET requests on /queue endpoints should be replaced with POST requests.")

    def post(self, command=None, *args, **kwargs):
        if command in self.commands:
            meth = getattr(self, '_' + command)
            return meth(*args, **kwargs)
        return super(QueueAPIView, self).post(*args, **kwargs)

    def __fetch_batch(self, channel, limit, reserve_time, unsafe):
        if not unsafe:
            messages, duplicate_count = QueueMessage.objects.select_and_reserve(channel.id,
                                                                                limit,
                                                                                reserve_time)
        else:
            messages, duplicate_count = QueueMessage.objects.get_unsafe(channel.id, limit)

        log = get_logger(channel)
        log.info('QMD: messages to fetch: %s, duplicated: %s', [(msg.id, PostAPIView.model(msg.post_data).plaintext_content) for msg in messages], duplicate_count)

        if not messages:
            return messages, duplicate_count

        queue_purge_horizon = get_service_channel(channel).queue_purge_horizon
        if queue_purge_horizon is not None and queue_purge_horizon > 0:
            horizon_date = datetime.utcnow() - timedelta(seconds=queue_purge_horizon)
            purgeable_ids = []
            valid_messages = []
            for q_m in messages:
                if q_m.created_at < horizon_date:
                    purgeable_ids.append(q_m.id)
                else:
                    valid_messages.append(q_m)

            if purgeable_ids:
                # Some queue messages were too old, we're gonna purge them and recursively search for newer entries
                purged = QueueMessage.objects.clear_reserved_id_based(purgeable_ids)['n']
                if not purged:
                    LOGGER.warning("Tried to remove queue ids: %s but did not purge anything" % purgeable_ids)
                    return messages, duplicate_count

                new_limit = limit - len(valid_messages)
                new_messages, new_duplicate_count = self.__fetch_batch(channel, new_limit, reserve_time, unsafe)
                valid_messages.extend(new_messages)
                duplicate_count += new_duplicate_count
                log.info('QMD: purgable_ids: %s, new_messages: %s', purgeable_ids, [(msg.id, PostAPIView.model(msg.post_data).plaintext_content) for msg in new_messages])
                return valid_messages, duplicate_count
            else:
                return valid_messages, duplicate_count
        else:
            return messages, duplicate_count

    @api_request
    def _fetch(self, user, *args, **kwargs):
        """
        Fetch a batch of posts from a channel queue

        Parameters:
            :param token: <Required> - A valid user access token
            :param channel: <Required> - The channel id for which we are pulling data
            :param limit: <optional> - The number of posts we fetch. Defaults to 1000000
            :param reserve_time: <optional> - For how long we reserve the batch waiting for confirmation
                                              until we start fetching it again in further requests. Defaults to 10000s
            :param unsafe: <optional> - Defaults to False, if passed as True we won't wait for confirmation
            :param mode: <options> - One of the ['single', 'conversation', 'root_included'] 'single' - default

        Output:
            A list of JSON containing post data

        Sample request:
            curl http://staging.socialoptimizr.com/api/v2.0/queue/fetch?token={{your-token}}&?channel={{channel_id}}

        Sample response:

            {
              "status": "ok",
              "warnings": [],
              "data": [
                    {
                        "id": "some_post_id",
                        "content": "@screen_name I need a laptop",
                        "source_data": {},
                        "smart_tags": [],
                        "actionability": 0.5,
                        "utterances": [
                          {
                            "topic_confidence": 0.9170699697250467,
                            "topic": [
                              "laptop"
                            ],
                            "content": "@screen_name I need a laptop",
                            "type": "States a Need / Want",
                            "type_confidence": 1.0
                          },
                        "created_at": "2014-09-11 17:40:23.331000"
                    },
                    {
                        "id": "some_post_id",
                        "content": "@screen_name I need a laptop",
                        "source_data": {},
                        "smart_tags": [],
                        "actionability": 0.5,
                        "utterances": [
                          {
                            "topic_confidence": 0.9170699697250467,
                            "topic": [
                              "laptop"
                            ],
                            "content": "@screen_name I need a laptop",
                            "type": "States a Need / Want",
                            "type_confidence": 1.0
                          }
                        ],
                        "created_at": "2014-09-11 17:40:23.332000"
                    },
                    {
                        "id": "some_post_id",
                        "content": "@screen_name I need a laptop",
                        "source_data": {},
                        "smart_tags": [],
                        "actionability": 0.5,
                        "utterances": [
                          {
                            "topic_confidence": 0.9170699697250467,
                            "topic": [
                              "laptop"
                            ],
                            "content": "@screen_name I need a laptop",
                            "type": "States a Need / Want",
                            "type_confidence": 1.0
                          }
                        ],
                        "created_at": "2014-09-11 17:40:23.333000"
                    },
                    {
                        "id": "some_post_id",
                        "content": "@screen_name I need a laptop",
                        "source_data": {},
                        "smart_tags": [],
                        "actionability": 0.5,
                        "utterances": [
                          {
                            "topic_confidence": 0.9170699697250467,
                            "topic": [
                              "laptop"
                            ],
                            "content": "@screen_name I need a laptop",
                            "type": "States a Need / Want",
                            "type_confidence": 1.0
                          }
                        ],
                        "created_at": "2014-09-11 17:40:23.333000"
                    }
              ],
              "metadata": {
                "count": 4,
                "reserved_until": "2014-09-11 17:40:53.341963",
                "duplicate_count": 0,
                "batch_token": "16603460875411de8731eddd37ebfc3a9722"
              }
            }
        """
        started_batch = datetime.now()
        limit = int(kwargs.get('limit', DEFAULT_LIMIT))
        reserve_time = int(kwargs.get('reserve_time', DEFAULT_RESERVE_TIME))
        unsafe = kwargs.pop('unsafe', None)
        fetch_mode = kwargs.pop('mode', PostProcessorFactory.SINGLE_POST_MODE)

        if 'channel' not in kwargs:
            raise exc.InvalidParameterConfiguration('Required parameter "channel" is missing from request')

        response = {
            'data': None,
            'metadata': {}
        }
        channel_id = kwargs.pop('channel', None)
        try:
            channel = Channel.objects.find_one_by_user(user, id=channel_id)
        except Channel.DoesNotExist:
            return dict(ok=False, error="No channel found with id=%s" % channel_id)

        if channel is None:
            return dict(ok=False, error="No channel found with id=%s" % channel_id)
        # Just so we accept both service channels directly or inbound / outbounds
        channel = get_service_channel(channel) or channel
        if not channel.can_edit(user):
            raise exc.AuthorizationError("You do not have access to channel %s" % channel)

        # Check for auto refresh timeouts
        # if isinstance(channel, TwitterServiceChannel):
        #     outbound_chn = channel.get_outbound_channel(user)
        #     if outbound_chn and outbound_chn.sync_status_followers == 'idle':
        #         if channel.auto_refresh_followers and channel.auto_refresh_followers > 0:
        #             if datetime.utcnow() - timedelta(minutes=channel.auto_refresh_followers) > outbound_chn.last_followers_update:
        #                 # Should start refreshing followers here
        #                 if get_var('ON_TEST'):
        #                     outbound_chn.refresh_followers()
        #                 else:
        #                     url = get_var('HOST_DOMAIN') + '/api/v2.0/refresh_followers'
        #                     data = dict(token=user.api_token,
        #                                 channel=str(channel.id))
        #                     req_data = requests.post(url, data=data)
        #                     LOGGER.info("Refresh followers started. " + str(req_data.content))
        #
        #     if outbound_chn and outbound_chn.sync_status_friends == 'idle':
        #         if channel.auto_refresh_friends and channel.auto_refresh_friends > 0:
        #             outbound_chn = channel.get_outbound_channel(user)
        #             if datetime.utcnow() - timedelta(minutes=channel.auto_refresh_friends) > outbound_chn.last_friends_update:
        #                 # Should start refreshing friends here
        #                 if get_var('ON_TEST'):
        #                     outbound_chn.refresh_followers()
        #                 else:
        #                     url = get_var('HOST_DOMAIN') + '/api/v2.0/refresh_friends'
        #                     data = dict(token=user.api_token,
        #                                 channel=str(channel.id))
        #                     req_data = requests.post(url, data=data)
        #                     LOGGER.info("Refresh friends started. " + str(req_data.content))
        #     else:
        #         LOGGER.warning("Should refresh friends but previous refresh is still running.")

        if not is_valid_numb(limit, MAX_LIMIT):
            raise exc.InvalidParameterConfiguration('Limit should be an integer between 1 and %d' % MAX_LIMIT)
            #response['warnings'].append('Limit should be an integer between 1 and %d' % MAX_LIMIT)

        if not is_valid_numb(reserve_time, MAX_RESERVE_TIME):
            raise exc.InvalidParameterConfiguration('Reserve time should be amount in seconds between 1 and %d' %
                                                    MAX_RESERVE_TIME)
            #response['warnings'].append('Reserve time should be amount in seconds between 1 and %d' % MAX_RESERVE_TIME)

        if isinstance(channel, TwitterServiceChannel):
            if 'group_by_type' in kwargs:
                group_by_type = parse_bool(kwargs.pop('group_by_type', True))
                kwargs['group_by_type'] = group_by_type
            else:
                kwargs['group_by_type'] = channel.grouping_config.group_by_type
            if 'grouping_timeout' in kwargs:
                try:
                    grouping_timeout = int(float(kwargs.pop('grouping_timeout', DEFAULT_GROUPING_TIMEOUT)))
                    GroupingConfig.validate_grouping_timeout(grouping_timeout)
                except ValueError as e:
                    raise exc.InvalidParameterConfiguration(u'Invalid grouping_timeout value: %s' % unicode(e))
                kwargs['grouping_timeout'] = grouping_timeout
            else:
                # grp_conf = channel.grouping_config
                # kwargs['grouping_timeout'] = grp_conf.is_enabled and grp_conf.grouping_timeout or 0
                kwargs['grouping_timeout'] = 0

        try:
            messages, duplicate_count = self.__fetch_batch(channel, limit, reserve_time, unsafe)
            if messages and len(messages) >= 2: # Just in case we needed to recursively split a batch, uniform the token
                for msg in messages[1:]:
                    msg.batch_token = messages[0].batch_token
                    msg.save()
            response['data'] = PostProcessorFactory.process_message_batch(fetch_mode, messages, channel, **kwargs)
            meta = response['metadata']
            meta['count'] = len(messages)
            meta['duplicate_count'] = duplicate_count
            if messages:
                meta['batch_token'] = messages[0].batch_token
                meta['reserved_until'] = str(messages[0].reserved_until) if not unsafe else None
            else:
                meta['batch_token'] = None
                meta['reserved_until'] = None
        except Exception, e:
            err_msg = "Error occurred when pulling queue with params:"
            err_msg += "User: %s, channel: %s, limit: %s, reserve_time: %s" % (user, channel, limit,
                                                                               reserve_time)
            traceback.print_exc()
            LOGGER.error(err_msg)
            raise e
        LOGGER.debug("API.Queue.fetch: Returned a batch of %s entries in %s for channel %s" %
                     (len(messages), datetime.now() - started_batch, channel))
        return response

    @api_request
    def _confirm(self, user, *args, **kwargs):
        """
        A simple acknowledge endpoint to confirm you actually received the batch successfully

        Parameters:
            :param token: <Required> - A valid user access token
            :param batch_token: <Optional> - A batch token received on a previous call to 'queue/fetch'
            :param ids: <Optional> - A list of post ids we want to confirm from items returned by 'queue/fetch'

        Output:
            A simple confirmation dictionary {'ok': true, cleared_count: 4}

        Sample request:
            curl http://staging.socialoptimizr.com/api/v2.0/queue/confirm?token={{your-token}}&?batch_token={{batch}}

        Sample response:
            {
              "cleared_count": 6,
              "ok": true
            }
        """
        batch_token = kwargs.get('batch_token', None)
        post_ids = ensure_list(kwargs.get('ids'))
        fetch_mode = kwargs.pop('mode', PostProcessorFactory.SINGLE_POST_MODE)

        start_confirmation = datetime.now()
        removed = PostProcessorFactory.confirm_message_batch(mode=fetch_mode,
                                                             post_ids=post_ids,
                                                             batch_token=batch_token)
        channel_id = '<in post_ids>'
        if batch_token:
            try:
                sep_pos = batch_token.index(':')
            except (ValueError, AttributeError):
                channel_id = "<%s>" % batch_token
                LOGGER.warning("Invalid batch token %s" % channel_id)
            else:
                channel_id = batch_token[sep_pos - 24: sep_pos]

        LOGGER.info("API.Queue.confirm: Confirmed a batch of %s entries in %s batch_token=%s post_ids=%s fetch_mode=%s channel=%s" %
                    (removed, datetime.now() - start_confirmation, batch_token, post_ids, fetch_mode, channel_id))

        return dict(cleared_count=removed)

    @api_request
    def _confirm_error(self, user, *args, **kwargs):
        """
        A simple acknowledge endpoint to confirm posts which was processed with errors

        Parameters:
            :param token: <Required> - A valid user access token
            :param ids: <Optional> - A list of post ids we want to confirm from items returned by 'queue/fetch'

        Output:
            A simple confirmation dictionary {'ok': true, cleared_count: 4}

        Sample request:
            curl http://staging.socialoptimizr.com/api/v2.0/queue/confirm?token={{your-token}}&?batch_token={{batch}}

        Sample response:
            {
              "cleared_count": 6,
              "ok": true
            }
        """
        post_ids = ensure_list(kwargs.get('ids'))
        start_confirmation = datetime.now()
        removed = BaseQueueEntryProcessor.confirm_error_posts(post_ids)

        LOGGER.info("API.Queue.confirm: Confirmed a batch of %s entries in %s post_ids=%s" % (
            removed, datetime.now() - start_confirmation, post_ids))

        return dict(cleared_count=removed)

    @api_request
    def _count(self, user, *args, **kwargs):
        if 'channel' not in kwargs:
            raise exc.InvalidParameterConfiguration('Required parameter "channel" is missing from request')

        channel = Channel.objects.find_one_by_user(user, id=kwargs['channel'])
        if not channel.can_edit(user):
            raise exc.AuthorizationError("You do not have access to channel %s" % channel)
        if channel is None:
            raise exc.InvalidParameterConfiguration('Channel with id %s not found' % kwargs['channel'])

        return dict(count=QueueMessage.objects.count_non_reserved_entries(channel.id))
