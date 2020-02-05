from __future__ import division

from collections import defaultdict
from operator import itemgetter
import pytz
from solariat_bottle.db.channel.facebook import FacebookServiceChannel

from werkzeug.utils import cached_property
from solariat.utils import timeslot
from pymongo.errors import DuplicateKeyError

from solariat.db.abstract import fields
from solariat.utils.timeslot import Timeslot
from solariat_bottle import settings
from solariat_bottle.db.post.facebook import FacebookPost, FacebookPostManager
from solariat_bottle.db.sequences import NumberSequences
from solariat_bottle.utils.posts_tracking import get_logger, is_enabled
from solariat_nlp.languages import LangComponentFactory
from solariat_nlp.sa_labels import SATYPE_ID_TO_OBJ_MAP
from solariat_nlp.utils     import translate_keys, inversed_dict

from ..settings import get_var, LOGGER, AppException
from ..db import channel_stats_base
from ..db.post.base import Post
from ..db.post.base import UntrackedPost
from ..db.post.chat import ChatPost
from ..db.post.email import EmailPost
from ..db.channel.base import Channel, ChannelAuthDocument, ChannelAuthManager
from ..utils.id_encoder import pack_conversation_key, make_channel_ts
from ..utils.views import reorder_posts
from ..utils.facebook_driver import get_page_id
from solariat_nlp.conversations.topics import DEFAULT_STOPWORDS
from solariat_nlp.sentiment import extract_sentiment
from solariat_nlp.conversations.topics import get_topics_simple
from solariat_nlp.sentiment import NEUTRAL

CLASSIFIER = LangComponentFactory.resolve('en').get_intent_classifier()
MAX_REORDER_LIMIT = 10

# -- constants --
logger = LOGGER

CONVERSATION_DIRECTIONS = (
    (0, "unknown"),
    (1, "direct"),
    (2, "indirect"),
    (3, "mentioned")
)

CONVERSATION_DIRECTIONS_LOOKUP     = dict(CONVERSATION_DIRECTIONS)

INV_CONVERSATION_DIRECTIONS_LOOKUP = inversed_dict(CONVERSATION_DIRECTIONS_LOOKUP)

# -- For handling actionability --
LABELS_DICT = CLASSIFIER.bs.config['LABELS_DICT']

LABELS_MAP = dict((typ.name, num) for (num, typ) in LABELS_DICT.items())

ACTIONABLE_INTENTIONS = set(
    dict(filter(lambda (k, v): k in ("asks", "needs", "problem"), LABELS_MAP.items())).values()
)

INACTIONABLE_INTENTIONS = set(
    dict(filter(lambda (k, v): k in ("junk", "discarded"), LABELS_MAP.items())).values()
)


# -- helpers --
channel_id_str = lambda x:str(x.id) if hasattr(x, 'id') else str(x)

speech_acts_mapping = {
    "intention_type_id"    : "i",
    "intention_type_conf"  : "ic",
    "intention_topics"     : "t",
    "intention_topic_conf" : "tc",
    "content"              : "c"
}

def decode_speech_acts(speech_acts):
    ''' Decode encoded version '''

    mapping = inversed_dict(speech_acts_mapping)
    result = []

    for sa in speech_acts:
        speech_act = translate_keys(sa, mapping)
        speech_act["intention_type"] = SATYPE_ID_TO_OBJ_MAP[str(speech_act["intention_type_id"])]
        result.append(speech_act)

    return result


def post_to_dict(post):
    if isinstance(post, dict):
        return post
    return {
        "id" : post.id,
        "s"  : post.native_id,
        "u"  : post.get_user_profile().screen_name,
        "d"  : post.created_at,
        "t"  : post.content,
        "p"  : post.parent_post_id,
        "cs" : map(channel_id_str, post.channels),
        "mtp": post.message_type,
        "sa" : [translate_keys(sa, speech_acts_mapping) for sa in post.speech_acts]
    }

def db_to_ui(tree):
    mapped = {
        'id' : 'id',
        's'  : 'status_id',
        'u'  : 'user_profile',
        'd'  : 'created',
        't'  : 'content',
        'p'  : 'parent',
        'cs' : 'channels',
        'sa' : 'speech_acts'
    }
    result = {}

    for k, v in tree.iteritems():
        if k == 'c' and v:
            result[mapped[k]] = db_to_ui(v)
        elif k == 'sa':
            result[mapped[k]] = decode_speech_acts(v)
        else:
            result[mapped[k]] = v

    return result


class ConversationManager(ChannelAuthManager):

    def build_fb_conversation_data(self, posts):
        update_dict = {}
        post = posts[0]
        if isinstance(post, FacebookPost) and post.wrapped_data:
            from solariat_bottle.db.channel.facebook import FacebookChannel

            update_dict['conv_root_id'] = post.get_conversation_root_id()
            if FacebookChannel.conversation_id_re.match(post.wrapped_data['source_id']):
                # source id is private message id
                target_id = post.native_data['page_id']
            else:
                target_id = get_page_id(post)
            update_dict['target_id'] = target_id
            update_dict['target_type'] = post.wrapped_data['source_type']

            if post.wrapped_data['type'].lower() == 'pm':
                if 'in_reply_to_status_id' not in post.native_data:
                    update_dict['root_pm_fb_post'] = post.facebook_id
                else:
                    update_dict['is_corrupted'] = True
        return update_dict

    def upsert_conversation(self, service_channel, posts, conversation_id):
        conversation_id = pack_conversation_key(service_channel, conversation_id)
        get_logger(service_channel).info("CONV_TRACK: UPSERTING WITH ID: %s", str(conversation_id))
        search_dict = {Conversation.id.db_field: conversation_id,
                       Conversation.version.db_field: 0}

        update_dict = {Conversation.channel.db_field: service_channel.id,
                       Conversation.is_closed.db_field: False,
                       Conversation.is_corrupted.db_field: False,
                       Conversation.created_by_admin.db_field: True}
        if posts:
            conv_data = self.build_fb_conversation_data(posts)
            update_dict.update(conv_data)

        try:
            self.coll.update(search_dict, {'$set': update_dict}, upsert=True, w=1)
        except DuplicateKeyError, ex:
            # Was already created, don't try again
            pass

        conv = self.get(conversation_id)
        return conv

    def create_conversation(self, service_channel, posts, conversation_id):
        conv_id = pack_conversation_key(service_channel, conversation_id)
        if is_enabled(service_channel):
            get_logger(service_channel).info("CONV_TRACK: USING CONVERSATION ID %s %s", conv_id, conv_id > 2 ** 63 - 1)
        create_dict = {
            'id': pack_conversation_key(service_channel, conversation_id),
            'channel': service_channel.id,}

        if posts:
            create_dict.update(self.build_fb_conversation_data(posts))

        conversation = Conversation(**create_dict)
        conversation.save(is_safe=True)

        conversation.add_posts(posts)  #add posts and save to update stats
        return conversation

    @staticmethod
    def merge_conversations(conversations):
        non_corrupted = [c for c in conversations if not c.is_corrupted]
        if non_corrupted:
            chosen_one = non_corrupted[0]
        else:
            chosen_one = sorted(conversations, lambda x: - len(x.posts))[0]
        if conversations and len(conversations) > 1:
            # all_posts = set()
            # for cv in conversations:
            #     for post in cv.posts:
            #         if post not in all_posts:
            #             all_posts.add(post)
            #
            # main_cv = conversations[0]
            # main_cv.posts = list(all_posts)
            # main_cv.save()
            #
            # for cv in conversations[1:]:
            #     cv.delete()
            #
            # LOGGER.error("Final count is:" + str(len(main_cv.posts)))
            for conv in conversations:
                if conv.id != chosen_one.id:
                    chosen_one.add_posts(conv.query_posts()[:])
                    conv.delete()
            return chosen_one
        else:
            return None


    def lookup_by_posts(self, service_channel, posts, include_closed=False):
        '''
        We must use the compound index so even if we need  to fetch closed as
        well as open/
        '''
        assert posts, "post list given to lookup_by_posts() func is empty"
        # making sure that all given posts belong to the same type
        assert 1 == len(set([type(p) for p in posts])), "post list given to lookup_by_posts() contains posts of different types"
        post = posts[0]
        assert post, posts
        if isinstance(post, ChatPost):
            klass = SessionBasedConversation
        elif isinstance(post, (Post, EmailPost)):
            klass = Conversation
        else:
            raise Exception("Unknown type of Post, get a proper conversation class for it: %s" % type(post))

        all_conversations =  set([c for c in klass.objects(posts__in=[p.id for p in posts],
                                                           channel=service_channel.id,
                                                           is_closed=False)])
        if include_closed:
            closed_conversations =  set([c for c in klass.objects(posts__in=[p.id for p in posts],
                                                                  channel=service_channel.id,
                                                                  is_closed=True)])
            all_conversations = all_conversations | closed_conversations

        return list(reversed(sorted(all_conversations, key=lambda c: c.last_modified)))

    def lookup_by_contacts(self, service_channel, posts, include_closed=False):
        # Augment contact ids with addressee information for outbound posts.
        contacts = []
        for post in posts:
            contacts.extend(post.get_contacts_for_channel(service_channel))

        conversations = [c for c in Conversation.objects(channel=service_channel.id,
                                                         contacts__in=contacts,
                                                         is_closed=include_closed)]
        # And run the query
        if include_closed:
            conversations.extend([c for c in Conversation.objects(channel=service_channel.id,
                                                                  contacts__in=contacts,
                                                                  is_closed=True)])

        return list(reversed(sorted(conversations, key=lambda c: c.last_modified)))[0:1]

    def lookup_conversations(self, service_channel, posts, contacts=False, include_closed=False):
        """Lookup Conversations by list of post ids."""

        conversations = list(self.lookup_by_posts(service_channel, posts, include_closed=include_closed))

        if conversations == [] and contacts:
            conversations = list(self.lookup_by_contacts(service_channel, posts, include_closed=include_closed))

        return conversations

    def get_conversation(self, service_channel, post, include_closed=False):
        '''We expect a conversation, and there better be exactly 1'''

        conversations = Conversation.objects.lookup_by_posts(service_channel, [post], include_closed)

        if len(conversations) == 0:
            return None
        if len(conversations) > 1:
            for conv in sorted(conversations, key=lambda x: -len(x.posts))[1:]:
                conv.delete()
                LOGGER.warning("Found multiple conversations for post %s, removing all but one." % post)

        return conversations[0]

    def count_profile_conversations(self, service_channel, user_profile):
        CF = Conversation.F
        active_count_query = {
            CF.contacts: user_profile.id,
            CF.channel: service_channel.id,
            CF.is_closed: False}
        closed_count_query = active_count_query.copy()
        closed_count_query[CF.is_closed] = True

        query = Conversation.objects.coll.find({"$or": [active_count_query, closed_count_query]})
        return query.count()


class Conversation(ChannelAuthDocument):
    id               = fields.CustomIdField()
    last_modified    = fields.DateTimeField(db_field="lm")
    contacts         = fields.ListField(fields.ObjectIdField(), db_field="c")   # list of user profile ids involved
    channels         = fields.ListField(fields.ObjectIdField(), db_field="cs")  # all channels of posts in conversation
    posts            = fields.ListField(fields.EventIdField(), db_field="p")   # list of post ids in conversation
    amplifiers       = fields.ListField(fields.EventIdField(), db_field="a")   # posts that are retweets/shares for posts in this conversation
    is_closed        = fields.BooleanField(db_field="x", default=False)         # conversation is in one of terminal statuses
    external_id      = fields.StringField(required=False, db_field='eid')       # Keeps track of the salesforce CaseId in case the conversation is synced
    last_synced_post = fields.ObjectIdField(db_field="lupid", required=False)   # keeps track of the latest post (date-oredered) from this conversation that was synced with SFDC

    platform         = fields.StringField()
    is_corrupted     = fields.BooleanField(default=False)
    last_recovery_ts = fields.DateTimeField(db_field='r_ts', null=True)
    conv_root_id     = fields.StringField() # !!! currently used for Facebook posts only
    root_pm_fb_post  = fields.StringField() # !!! used for facebook posts only which is from PM
    target_id        = fields.StringField() # !!! currently used for Facebook posts only
    target_type      = fields.StringField() # !!! currently used for Facebook posts only
    version          = fields.NumField(db_field='v', default=0)

    actors           = fields.ListField(fields.ObjectIdField(), db_field="act")   # list of actors cross channel involved
    created_by_admin = fields.BooleanField(default=True)

    # Meta Data
    manager = ConversationManager
    indexes = [('posts', 'is_closed', ),
               ('contacts', 'is_closed', ),
               ('actors', 'is_closed'),
               ('last_modified', ),
               ('channel', ),
               ('is_corrupted', ),
               ('target_id', 'conv_root_id'),
               ('amplifiers', )
               ]

    @classmethod
    def get_query(cls, **kw):
        if kw.pop('raw_query', False):
            return kw
        else:
            return super(ChannelAuthDocument, cls).get_query(**kw)

    @cached_property
    def service_channel(self):
        return Channel.objects.get(id=self.channel)

    @property
    def is_synced(self):
        return self.external_id

    def unsynced_posts(self):
        """
        Return a list with all the posts from this conversation that were not synced
        with Salesforce.

        :returns: a list with all the posts that are not yet synced
        :raises: ValueError in case conversation does not have a Case on salesforce
        """
        if not self.external_id:
            raise ValueError("This conversation is not synced up with Salesforce.")
        if not self.last_synced_post:
            return self.posts
        for idx, post_id in enumerate(self.posts):
            if post_id == self.last_synced_post:
                return self.posts[(idx+1):]
        return []

    def set_external_id(self, ex_id):
        self.external_id = ex_id
        self.save()

    @property
    def POST_CLASS(self):
        from ..db.post.utils import get_platform_class
        return get_platform_class(self.service_channel.platform)

    def delete(self):
        """ Make sure that if we decide to remove a conversation, we also remove corresponding response
        and response tag objects so as not to leave system in a 'broken' state """
        ChannelAuthDocument.delete(self)

    def query_posts(self):
        return self.POST_CLASS.objects(id__in=self.posts).sort(_created=1)

    def route_post(self, post):
        result = self.service_channel.route_post(post)

        # this happens when we have conversation containing posts from deleted channels
        # see https://jira.genesys.com/browse/SMD-3354
        if result == 'unknown':
            if self.add_missing_parents(force=True):
                self.reload()
                if not self.has_initial_root_post():
                    self.mark_corrupted()
        return result

    def db_lock_aquire(self):
        import time
        num = 0
        tries_remaining = 16
        while num != 1 and tries_remaining:
            num = NumberSequences.advance("conv_add_posts_%s" % self.id)
            tries_remaining -= 1
            if num != 1:
                LOGGER.warning("Conversation %s is being modified, num=%s" % (self.id, num))
                time.sleep(num * 0.05)
        if tries_remaining == 0:
            self.db_lock_release()

    def db_lock_release(self):
        NumberSequences.objects.coll.remove({"name": "conv_add_posts_%s" % self.id})

    def add_posts_with_lock(self, posts):
        self.db_lock_aquire()
        try:
            return self.add_posts_safe(posts)
        finally:
            self.db_lock_release()

    def add_posts_safe(self, posts, force_root_post_update=False):
        # logger.error("ADDING POST " + str([p.plaintext_content for p in posts]) + " VERSION IS " + str(self.version) + " AND EXISTING POSTS ARE " + str(len(self.posts)))
        self.reload()
        new_reply = False
        search_dict = {Conversation.id.db_field: self.id,
                       Conversation.version.db_field: self.version}
        update_dict = dict()
        is_fb_conversation = False
        conv_last_modified = timeslot.utc(self.last_modified or timeslot.UNIX_EPOCH)
        for post in posts:
            post_created_at = post.created_at
            if not conv_last_modified:
                conv_last_modified = post_created_at
            elif timeslot.utc(post_created_at) > timeslot.utc(conv_last_modified):
                conv_last_modified = post_created_at

            if isinstance(post, FacebookPost):
                is_fb_conversation = True
        update_dict[Conversation.last_modified.db_field] = conv_last_modified

        if self.is_corrupted or force_root_post_update:
            for post in posts:
                if isinstance(post, FacebookPost):
                    p_type = post.wrapped_data['type'].lower()
                    if p_type == 'pm':
                        if 'in_reply_to_status_id' not in post.native_data:
                            update_dict[Conversation.root_pm_fb_post.db_field] = post.facebook_id
                            update_dict[Conversation.is_corrupted.db_field] = False
                    else:
                        if post.facebook_id == self.conv_root_id:
                            update_dict[Conversation.is_corrupted.db_field] = False

        for post in posts:
            # If the post does not belong to an inbound or outbound channel, skip it
            if not set(post.channels).intersection({self.service_channel.inbound, self.service_channel.outbound}):
                continue
            if post.id not in self.posts:
                self.posts.append(post.id)
            # Update the conversation state history
            # Add contacts only from inbound posts
            if self.route_post(post) == 'inbound':
                # self.contacts = list(set(self.contacts + [post.user_profile.id]))
                update_dict[Conversation.contacts.db_field] = list(set(self.contacts + [post.user_profile.id]))

            if post.actor_id:
                update_dict[Conversation.actors.db_field] = list(set(self.actors).union([post.actor_id]))
            # if self.route_post(post) == 'inbound':
            #     self.contacts = list(set(self.contacts + [post.actor_id]))

            if self.route_post(post) == 'outbound':
                new_reply = True

            for ch in post.channels:
                # self.channels = list(set(self.channels + [ch]))
                update_dict[Conversation.channels.db_field] = list(set(self.channels + [ch]))

        has_replies = False
        if not is_fb_conversation and len(self.posts) > get_var('INBOUND_SPAM_LIMIT'):
            possible_spam = self.POST_CLASS.objects(id__in=self.posts[-1:-get_var('INBOUND_SPAM_LIMIT'):-1])[:]
            for post in possible_spam:
                # Check that we have at least one outbound post in the last `INBOUND_SPAM_LIMIT`
                # posts from the conversation. Otherwise we can delete it
                if self.route_post(post) == 'outbound':
                    has_replies = True
        else:
            has_replies = True

        if not has_replies and not new_reply:
            # Now create a new conversation containing only this new post
            # This should be the equivalent of just setting the posts of this conversation
            # to an empty list.
            self.posts = [p.id for p in posts]

        # posts are reordered so that they come in chronological order
        # but a reply is immediatly after the post its parent post
        latest_posts = self.POST_CLASS.objects(id__in=self.posts[-MAX_REORDER_LIMIT:])[:]
        sorted_latest_posts = reorder_posts(latest_posts)
        # self.posts = [ p.id for p in sorted_posts]
        # self.last_modified = timeslot.UNIX_EPOCH if not sorted_posts else sorted_posts[-1].created_at
        # update_dict[Conversation.posts.db_field] = [p.id for p in sorted_posts]
        if len(sorted_latest_posts) >= MAX_REORDER_LIMIT:
            update_dict[Conversation.posts.db_field] = self.posts[:-MAX_REORDER_LIMIT] + [p.id for p in sorted_latest_posts]
        else:
            update_dict[Conversation.posts.db_field] = [p.id for p in sorted_latest_posts]

        if sorted_latest_posts:
            sorted_latest_created_at = sorted_latest_posts[-1].created_at
            if timeslot.utc(sorted_latest_created_at) > timeslot.utc(conv_last_modified):
                update_dict[Conversation.last_modified.db_field] = sorted_latest_created_at
        update_dict[Conversation.version.db_field] = self.version + 1

        update_dict[Conversation.posts.db_field] = map(fields.EventIdField().to_mongo, update_dict[Conversation.posts.db_field])
        self.objects.coll.update(search_dict, {'$set': update_dict}, upsert=True, w=1)
        return sorted_latest_posts

    def add_posts(self, posts, max_tries=20):

        """Appends posts to list.
        Updates contacts, channels lists and conversation tree.
        """
        # Filter out any untracked posts if they somehow made their way in
        from solariat.utils.iterfu import flatten
        import time
        from random import normalvariate

        channels = list(flatten(getattr(p, 'channels', []) for p in posts))
        rp = self.service_channel.remove_personal
        log = get_logger(channels)
        if is_enabled(channels):
            log.info("CONV_TRACK: Adding posts %s to conversation %s, version is %s and existing posts are %s" % (
                [(p.id, '' if rp else p.plaintext_content) for p in posts], self.id, self.version,
                ['' if rp else p.plaintext_content for p in self.query_posts()]))
        posts = [p for p in posts if not isinstance(p, UntrackedPost)]
        old_posts = set(self.posts)

        nr_of_tries = 0
        sorted_posts = []
        while nr_of_tries < max_tries:
            try:
                sorted_posts = self.add_posts_safe(posts)
                break
            except DuplicateKeyError, e:
                delay_sec = max(0.01, normalvariate(0.5, 0.08))
                time.sleep(delay_sec)
            nr_of_tries += 1
        if nr_of_tries == max_tries:
            LOGGER.error("Failed to add posts %s to conversation %s due to collisions" % (posts, self))

        # we update status not of all sorted posts but only until the last new post
        # so that if we have posts 1, 2, 3 in the conversation and reply to 2
        # we update only 1 and 2
        is_post_in_sorted = False
        for i, p in reversed(list(enumerate(sorted_posts))):
            if p in posts:
                is_post_in_sorted = True
                break
        if is_post_in_sorted:
            sorted_posts_to_change = sorted_posts[:i+1]
            remaining_posts = sorted_posts[i+1:]
        else:
            sorted_posts_to_change = sorted_posts
            remaining_posts = []

        new_posts = [p for p in posts if p.id in self.posts and p.id not in old_posts]
        self.handle_channel_filter(new_posts, sorted_posts_to_change)
        self.reload()
        if is_enabled(channels):
            log.info("CONV_TRACK: Done with adding posts to conversation %s, new post list is %s" % (
                self.id, [(p.id, '' if rp else p.plaintext_content) for p in self.query_posts()]
                                                                                                          ))

        # Inbox is deprecated, no longer need this!
        # when some posts are replies
        # remove remaining posts from response add them to a new one
        # have_parents = False
        # for p in posts:
        #     if p.parent:
        #         have_parents = True
        #         break
        # if have_parents:
        #     # this way we get the latest response for this post and conversation
        #     response = self.get_response_for_post(sorted_posts_to_change[-1]) if sorted_posts_to_change else None
        #     if response:
        #         for post in sorted_posts_to_change[::-1]:
        #             if self.route_post(post) == 'inbound':
        #                 # Only set inbounds as latests posts, we should only see replies in conversation
        #                 response.set_latest_post(post)
        #                 break
        #     if remaining_posts:
        #         for post in remaining_posts:
        #             if (self.route_post(post) == 'inbound' and
        #                 post.get_assignment(self.service_channel.inbound_channel) != 'replied'):
        #                 Response.objects.upsert_from_post(p)

    def add_amplifying_post(self, post):
        self.objects.coll.update({Conversation.id.db_field: self.id},
                                 {'$push': {Conversation.amplifiers.db_field: post.data['_id']}},
                                 w=1)
        self.amplifiers.append(post.id)

    def handle_channel_filter(self, posts, sorted_existing_posts):
        from ..db.post.base import UntrackedPost
        for post in posts:
            # Update user profile either if the length of posts from the conversation
            # is greater than 1 or if there are multiple conversations for this profile
            if len(self.posts) > 1 \
                    or self.objects.count_profile_conversations(self.service_channel, post.user_profile) > 1:
                for sc in post.service_channels:
                    post.user_profile.update_history(sc)

            if self.route_post(post) == 'outbound':
                parent = post.parent_in_conversation(self, sorted_existing_posts)
                if parent and not isinstance(parent, UntrackedPost) and self.route_post(parent) == 'inbound':
                    if parent.get_assignment(self.service_channel.inbound_channel) != 'replied':
                        # If this is another reply to same parent, don't go thorugh handle_reply
                        # again since that will always fail, also the outbound stats should be those
                        # for the first reply. E.G. response_time now is not relevant since it's already
                        # been responded to with a quicker response time
                        context = {
                            'agent'           : post.find_agent_id(self.service_channel),
                            'outbound_stats'  : self.get_outbound_stats(post, parent, account=self.service_channel.account),
                            'reply'           : post,
                        }
                        # we need to break if we run into post, which is already replied
                        parent.set_reply_context(self.service_channel.inbound_channel, context)
                        context['handle_channel_filter'] = True
                        try:
                            parent.handle_reply(None, [self.service_channel.inbound_channel], **context)
                        except Exception as ex:
                            LOGGER.error("Handle post reply failed for post %s with trace: %s" % (parent.id, ex))

                    inbound_channel_id = str(self.service_channel.inbound)
                    # here we itearate over posts of conversation
                    # and apply to posts handle_reply() function
                    for existing_post in reversed(sorted_existing_posts):
                        # print p.content
                        if (existing_post.id == parent.id):
                            continue
                        if not existing_post.channel_assignments.has_key(inbound_channel_id):
                            continue
                        if existing_post.channel_assignments[inbound_channel_id] == "replied":
                            break
                        if self.route_post(existing_post) == "inbound":
                            # context does not include outbound stats
                            # because we count response volume based on number of outbound posts
                            context = {
                                'agent': post.find_agent_id(self.service_channel),
                                'reply': post
                            }
                            # we need to break if we run into post, which is already replied
                            existing_post.set_reply_context(self.service_channel.inbound_channel, context)
                            if existing_post.channel_assignments[inbound_channel_id] == "rejected":
                                # No point to learn anything new from this
                                context['handle_channel_filter'] = False
                            try:
                                existing_post.handle_reply(
                                                            None,
                                                            [self.service_channel.inbound_channel],
                                                            **context)
                            except Exception as ex:
                                LOGGER.error(
                                    "Handle post reply failed for post %s with trace: %s",
                                    existing_post.id, ex
                                )

    def get_outbound_stats(self, post, parent=None, account=None):
        """
        :param post: post for which to get stats
        :param parent: in general can be different from ``post.parent``
            because we consider a parent in conversation the first post in it
            ``post.parent`` is what Twitter returns as parent
        :returns dict stats: with ``response_volume`` and ``response_time``
        """
        if parent is None:
            parent = post.parent

        if account is None:
            # not safe
            account = post.channel.account

        if not parent:
            return {'response_volume': 1}

        return {'response_volume': 1,
                'response_time': account.schedule_aware_dates_diff(
                    post.created_at, parent.created_at)}

    def update_stats(self, posts):
        """
        Deprecated. Stats updated in handle_channel_filter
        """
        from ..db.service_channel_stats import ServiceChannelStats
        channel = self.service_channel

        posts = sorted(posts, key=itemgetter('created_at'))
        for post in posts:
            dest = self.route_post(post)

            if dest == 'outbound':
                agent = post.find_agent_id(self.service_channel)
                agents = set([0, agent])
                stats = self.get_outbound_stats(post, account=self.service_channel.account)
                ServiceChannelStats.objects.outbound_post_received(channel, post, agents, stats=stats)

    @cached_property
    def tree(self):
        return self.rebuild_tree()

    def rebuild_tree(self):
        posts_in_order = sorted(self.query_posts(), key=lambda p: p.created_at)
        return self.add_to_tree(posts_in_order)

    def add_to_tree(self, posts):
        import copy
        t = {}

        def attach_child(post_dict, children):
            for p in children:
                if p.get('c'):
                    attach_child(post_dict, p['c'])

                if p['s'] == post_dict['p']:
                    if 'c' not in p:
                        p['c'] = []
                    p['c'].append(post_dict)
                    return

        for post in posts:
            post_dict = post_to_dict(post)
            if not t:
                t = post_dict
                continue

            #if post in parent for the root post
            if t.get('p') == post_dict['s']:
                tree = copy.deepcopy(t)
                post_dict['c'] = [tree]  # children
                t = post_dict
            else:
                #found parent
                if t.get('s') == post_dict['p']:
                    if 'c' not in t:
                        t['c'] = []
                    t['c'].append(post_dict)
                else:
                    if 'c' not in t:
                        t['c'] = []
                    attach_child(post_dict, t['c'])

        return t

    @property
    def root_post(self):
        try:
            is_fb = self.conv_root_id or self.root_pm_fb_post or self.target_id or self.target_type
            if is_fb:
                if self.root_pm_fb_post:
                    result = FacebookPostManager.find_by_fb_id(self.root_pm_fb_post)
                else:
                    result = FacebookPostManager.find_by_fb_id(self.conv_root_id)
            else:
                result = self.query_posts()[0]
            return result
        except:
            return None

    def has_initial_root_post(self):
        return self.root_post is not None

    def add_missing_parents(self, force=False):
        if not force and (not self.is_corrupted or self.has_initial_root_post()):
            # No need to add parents if conversation already has a root post
            return False

        current_post_ids = set(self.posts)
        posts_to_add = []
        PostCls = self.POST_CLASS
        conversation_channels = set(self.channels)

        def lookup_parents(post, posts_to_add):
            try:
                parent = post.parent
            except PostCls.DoesNotExist:
                parent = None

            if isinstance(parent, PostCls) and parent.id not in current_post_ids:
                logger.info("Found parent post %s for conversation %s", parent, self)
                if parent.get_conversation_root_id() == post.get_conversation_root_id():
                    if not set(parent.channels) & conversation_channels:
                        logger.info(
                            "Parent post %s channels %s do not intersect with conversation %s",
                            parent, parent.channels, self)

                        # re-routing parent post to inbound/outbound channel of current conversation
                        for previous_service_channel in parent.service_channels:
                            direction = previous_service_channel.route_post(parent)
                            if direction == 'outbound':
                                new_channels = [self.service_channel.outbound]
                            else:
                                new_channels = [self.service_channel.inbound]

                            logger.info(
                                "Extending parent post %s channels %s with %s. %s",
                                parent, parent.channels, new_channels, self)
                            parent.channels.extend(new_channels)
                            parent.save()

                    posts_to_add.append(parent)
                    lookup_parents(parent, posts_to_add)
                else:
                    logger.info(
                        "Conversation %s root id mismatch: parent=%s post=%s",
                        self, parent.get_conversation_root_id(),
                        post.get_conversation_root_id())

        for post in PostCls.objects(id__in=self.posts):
            lookup_parents(post, posts_to_add)

        if posts_to_add:
            logger.info("Adding parent posts %s into conversation %s" % (posts_to_add, self))
            conv_data = []
            for conv in Conversation.objects(posts__in=set(post.id for post in posts_to_add)):
                if conv.id != self.id:
                    conv_data.append(str(conv.data))
            if conv_data:
                logger.info("Posts %s also belong to conversations: %s" % (posts_to_add, '\n'.join(conv_data)))
            try:
                return self.add_posts_safe(set(posts_to_add), force_root_post_update=True)
            except DuplicateKeyError:
                return False

    def mark_corrupted(self, throttling_interval=settings.FB_CONVERSATION_RECOVERY_THROTTLE):
        import requests
        from solariat.utils.timeslot import now, timedelta
        recovery_throttling_interval = timedelta(seconds=throttling_interval)

        last_recovered = Conversation.last_recovery_ts.db_field
        update_result = self.objects.coll.update(
            {Conversation.id.db_field: self.id,
             '$or': [
                 {last_recovered: {'$exists': False}},
                 {last_recovered: {'$eq': None}},
                 {last_recovered: {'$lte': now() - recovery_throttling_interval}}
             ]},
            {'$set': {Conversation.is_corrupted.db_field: True,
                      Conversation.last_recovery_ts.db_field: now()}}, w=1)
        if update_result.get('n'):
            LOGGER.warning("Marking conversation %s as corrupted." % self)
            self.is_corrupted = True
        else:
            if self.is_corrupted:
                LOGGER.warning("Conversation recovery for %s has been started less than %s sec ago"
                               ", still corrupted." % (self, throttling_interval))
            return False

        if isinstance(self.service_channel, FacebookServiceChannel):
            # call FBot endpoint to fetch the whole conversation
            from solariat_bottle.tasks import async_requests
            url = "%s?token=%s&conversation=%s" % (settings.FBOT_URL + '/json/restore-conversation', settings.FB_DEFAULT_TOKEN, self.id)
            try:
                response = async_requests.ignore('get', url, verify=False, timeout=None, raise_for_status=True)
            except requests.exceptions.HTTPError:
                logger.exception("Can't connect to FBot")
                return False
            else:
                return response

    @property
    def post_objects(self):
        if hasattr(self, '_posts') and self._posts:
            return self._posts
        try:
            posts = sorted(self.POST_CLASS.objects(id__in=self.posts), key=lambda p: p.created)
            self._posts = posts
            return posts
        except Exception, exc:
            LOGGER.error(exc)
            raise AppException(
                "Sorry! Invalid post keys in conversation '%s' for response '%s'. "
                "Contact support for help." % (self.conversation_id, self.id)
            )
        return []

    @property
    def is_incomplete(self):
        """Returns True if conversation contains untracked posts."""
        return bool(self.tree.get('p'))

    def __iter__(self):
        return self.query_posts()

    def iter_tree(self):
        def _clean(p):
            d = dict(p)
            d.pop('c', None)
            return d

        q = []
        if self.tree:
            q.append(self.tree)

        while q:
            post = q.pop(0)
            if post.get('c'):  # has children
                q.extend(post['c'])
            yield _clean(post)

    def iter_post_reply_pairs(self):
        def _ordered(p):
            if p[0]['s'] == p[1]['p']:
                return p
            else:
                return p[1], p[0]

        pairs = defaultdict(list)

        for post in [post_to_dict(p) for p in self]:
            dest = self.route_post(post)
            if dest == 'inbound':
                pairs[post['s']].append(post)
            else:
                pairs[post['p']].append(post)

        for parent_post_id, pair in pairs.iteritems():
            if parent_post_id and len(pair) >= 2:
                yield _ordered(pair)

    def to_dict(self, fields2show=None):
        return {'id': str(self.id),
                'last_modified': timeslot.datetime_to_timestamp_ms(self.last_modified),
                'is_incomplete': self.is_incomplete}

    def reload(self):
        self.__dict__.pop('tree', None)
        self.__dict__.pop('service_channel', None)
        return super(Conversation, self).reload()

    def close(self, closing_time=None, quality=None):
        from solariat_bottle.db.conversation_trends import ConversationQualityTrends
        self.is_closed = True
        if not quality:
            quality = self.get_quality()
        quality = ConversationQualityTrends.CATEGORY_MAP[quality]
        if closing_time is None:
            closing_time = self.get_closing_datetime()
        self.channel_ts_day = make_channel_ts(
            self.service_channel, Timeslot(closing_time, "day"))
        self.channel_ts_hour = make_channel_ts(
            self.service_channel, Timeslot(closing_time, "hour"))
        self.quality = quality
        self.save(is_safe=True)
        channel_stats_base.conversation_closed(self, closing_time, quality)

    def get_quality(self):
        """it's a stub"""
        if not self.is_closed:
            raise Exception("cannt calculate quality for unclosed conversation!")
        else:
            return ["unknown", "win", "loss"][len(self.posts)%3]

    # def get_agents(self):
    #     outbound_posts = [p for p in self.post_objects if self.route_post(p) == 'outbound']
    #     if not outbound_posts:
    #         return []
    #     userprofile_ids = list(set([p.user_profile_id for p in outbound_posts]))
    #     userprofiles = UserProfile.objects(id__in=userprofile_ids)
    #     agents       = User.objects(id__in=[u.user_id for u in userprofiles])
    #     agents       = [a for a in agents]
    #     return agents

    def get_closing_datetime(self):
        last_post = Post.objects.find_one(id=self.posts[-1])
        return last_post.created

    def reset_create_by_admin_data(self, post):

        if self.created_by_admin:
            self.created_by_admin = bool(post.wrapped_data.get('created_by_admin', False if post.is_inbound else True))
            self.save()

    def save(self, is_safe=False, **kw):
        if not is_safe:
            raise Exception("Not thread safe")
        return super(Conversation, self).save(**kw)

    def get_session_data(self):
        session = {'messages': [], 'actors': [], 'stopwords': []}
        for p in self.query_posts():
            actor_label = 'Customer' if p.is_inbound else 'Agent'
            session['messages'].append(
                [actor_label, p.plaintext_content, p._created])
            try:
                session['actors'].append(p.actor.to_dict())
            except AttributeError:
                pass
        session['stopwords'] = DEFAULT_STOPWORDS
        return session

    def get_duration(self):
        t_start = None
        i = 0
        while t_start is None:
            try:
                t_start = Post.objects.get(self.posts[i]).created
            except Post.DoesNotExist:
                i += 1
        t_end = self.last_modified
        res = pytz.utc.localize(t_end) - t_start
        res = res.total_seconds()*100
        return int(res)

    def get_agents(self):
        posts = self.post_objects
        actor_ids = list(set([p.actor_id for p in posts]))
        AgentProfile = self.service_channel.account.get_agent_profile_class()
        return AgentProfile.objects(id__in=actor_ids)[:]

    def get_customers(self):
        posts = self.post_objects
        actor_ids = list(set([p.actor_id for p in posts]))
        CustomerProfile = self.service_channel.account.get_customer_profile_class()
        return CustomerProfile.objects(id__in=actor_ids)[:]

    def get_summary(self):
        session = self.get_session_data()
        topics = get_topics_simple(session=session['messages'])
        posts = []
        tags = {}
        last_customer_post = None
        p_obj = None
        for p_obj in self.query_posts():
            post = Post.to_dict(p_obj)
            post.pop('_reply_context', None)
            post['actor_info'] = p_obj.actor.to_dict()
            posts.append(post)
            for tag in p_obj.event_tags:
                if str(tag.id) in tags:
                    tags[str(tag.id)]['count'] += 1
                else:
                    tags[str(tag.id)] = {'display_name': tag.display_name,
                                         'count': 1,
                                         'id': str(tag.id)}
            for tag_id in p_obj.rejected_tags:
                tags.pop(str(tag_id), None)
            if p_obj.is_inbound:
                last_customer_post = p_obj
        sorted_tags = sorted([tag for tag in tags.values()], key=lambda x: -x['count'])

        if last_customer_post:
            sentiment_sample = extract_sentiment(last_customer_post.plaintext_content)
            sentiment = sentiment_sample['sentiment'].title,
            sentiment_score = sentiment_sample['score']
        else:
            sentiment = NEUTRAL.title,
            sentiment_score = 0

        agents = [x.to_dict() for x in self.get_agents()]
        customers = [x.to_dict() for x in self.get_customers()]

        summary = {'topics': topics,
                   'duration': self.get_duration(),
                   'tags': sorted_tags,
                   'sentiment': sentiment,
                   'sentiment_score': sentiment_score,
                   'latest_event_id': p_obj and str(p_obj.id),
                   'agents': agents,
                   'customers': customers,
                   'list': posts,
                   'id': str(self.id)
            }
        return summary



class SessionBasedConversationManager(ConversationManager):

    def create_conversation(self, service_channel, posts, session_id):
        session_ids = list(set([p.session_id for p in posts]))
        if None in session_ids:
            session_ids.remove(None)
        assert 1 == len(session_ids), session_ids
        assert session_id, "you should provide a session_id for SessionBasedConversationManager.create_conversation()"
        assert session_ids[0] == session_id, "session_ids: %s; session_id: %s" % (session_ids, session_id)
        create_dict = {
            'id': pack_conversation_key(service_channel, service_channel.get_conversation_id(posts[0])),
            'channel': service_channel.id,
            'session_id': session_id
            }

        conversation = SessionBasedConversation(**create_dict)
        conversation.save(is_safe=True)
        conversation.add_posts(posts)  #add posts and save to update stats

        return conversation


class SessionBasedConversation(Conversation):

    collection = "Conversation"

    session_id = fields.StringField(db_field='s_id', unique=True)

    manager = SessionBasedConversationManager

    indexes = Conversation.indexes + ['session_id']

    def handle_channel_filter(self, posts, sorted_existing_posts):
        for post in posts:
            # Update user profile either if the length of posts from the conversation
            # is greater than 1 or if there are multiple conversations for this profile
            if len(self.posts) > 1 \
                    or self.objects.count_profile_conversations(self.service_channel, post.user_profile) > 1:
                for sc in post.service_channels:
                    post.user_profile.update_history(sc)
            if self.route_post(post) == 'outbound':
                inbound_channel_id = str(self.service_channel.inbound_channel.id)
                # here we itearate over posts of conversation
                # and apply to posts handle_reply() function
                for existing_post in reversed(sorted_existing_posts):
                    if not existing_post.channel_assignments.has_key(inbound_channel_id):
                        continue
                    # As soon as we reached a replied post we should stop
                    if existing_post.channel_assignments[inbound_channel_id] == "replied":
                        break
                    if self.route_post(existing_post) == "inbound":
                        context = {
                            'agent'           : post.find_agent_id(self.service_channel),
                            'outbound_stats'  : self.get_outbound_stats(existing_post, account=self.service_channel.account),
                            'reply'           : post
                        }
                        # we need to break if we run into post, which is already replied
                        existing_post.set_reply_context(self.service_channel.inbound_channel, context)
                        if existing_post.channel_assignments[inbound_channel_id] == "rejected":
                            # No point to learn anything new from this
                            context['handle_channel_filter'] = False
                        try:
                            existing_post.handle_reply(None,
                                                       [self.service_channel.inbound_channel],
                                                       **context)
                        except Exception as ex:
                            LOGGER.error("Handle post reply failed for post %s with trace: %s" % (existing_post.id, ex))

    # def add_posts(self, posts):
    #     """Appends posts to list.
    #     Updates contacts, channels lists and conversation tree.
    #     """
    #     # Filter out any untracked posts if they somehow made their way in
    #     posts = [p for p in posts if not isinstance(p, UntrackedPost)]
    #     self.last_modified = timeslot.utc(self.last_modified or timeslot.UNIX_EPOCH)
    #     for post in posts:
    #         # If the post does not belong to an inbound or outbound channel, skip it
    #         if post.id not in self.posts:
    #             self.posts.append(post.id)
    #             self.contacts = list(set(self.contacts + post.get_contacts_for_channel(self.service_channel)))
    #             self.actors.append(post.actor_id)
    #             self.save()

    def to_dict(self, fields2show=None):
        res = super(SessionBasedConversation, self).to_dict()
        res['session_id'] = self.session_id
        return res


if __name__ == '__main__':
    import doctest
    doctest.testmod()


# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
