"""
Holds post functionality independent of any platform.

"""
import re
from itertools import chain
from datetime import datetime, timedelta

from bson.objectid  import ObjectId
from bson.dbref     import DBRef

from werkzeug.utils import cached_property
from solariat.utils.lang.helper import LingualToken
from solariat.utils.lang.support import get_lang_id
from solariat.utils.hidden_proxy import unwrap_hidden

from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.db.user_profiles.user_profile_field import \
    UserProfileIdField
from solariat_nlp import sa_labels, scoring
from solariat_bottle.settings import get_var, LOGGER, AppException

from solariat.utils.helpers import safe_max
from solariat.utils.timeslot import (
    now, Timeslot, datetime_to_timeslot, timedelta, decode_timeslot
)
from solariat_bottle.utils.id_encoder import get_intention_id
from solariat_bottle.utils.post       import (
    make_id, replace_special_chars
)
from solariat.db              import fields
from solariat.utils.helpers import trim_to_fixed_point
from solariat.db.abstract     import SonDocument, Document
from solariat_bottle.db.event_log    import log_event
from solariat_bottle.db.user         import User
from solariat_bottle.db.language     import LanguageMixin
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.roles        import ADMIN, STAFF, AGENT
from solariat_bottle.db.speech_act   import (
    SpeechActMap, fetch_posts, reset_speech_act_keys
)
from solariat_bottle.db.channel.base import (
    Channel, ServiceChannel, CompoundChannel,
    ChannelsAuthDocument, ChannelsAuthManager
)
from solariat_bottle.tasks import postprocess_new_post, filter_similar_posts
from solariat_bottle.db.events.event import Event, EventManager

PREFIX_LENGTH = 5
SIGNATURE_RE  = re.compile(r'([^\s]+)$', re.I)  #last word in post content

DEBUG_STATS   = get_var('DEBUG_STATS', False)

POST_PUBLIC = 0
POST_DIRECT = 1
POST_OTHER = 2

class DecrementLog(Document):
    id = fields.CustomIdField()
    decrement_log = fields.ListField(fields.DictField())

def _get_channels_for_post(post):
    'A helper method for extracting channel objects'
    if not hasattr(post, '_channel_objects'):
        post._channel_objects = Channel.objects(id__in=post.channels)[:]
    return post._channel_objects

class NoRelevantPost(object):
    """ Return classification result only when the post is not relevant
    and no sense to store it """

    def __init__(self, channel_ids, speech_acts):
        self.channels = channel_ids
        self.speech_acts = speech_acts
        self.created = now()
        self.status = 'rejected'
        self.channel_assignments = {}
        self._tag_assignments = {}

    def _get_channels(self):
        return _get_channels_for_post(self)

    def to_dict(self):
        "Return dict for API"
        return dict(
            id = None,
            matchables = [],
            status = 'rejected',
            speech_acts = self.speech_acts)

    def get_matches(self, user=None):
        return []

    @property
    def id(self):
        return make_id(''.join([sa['content'] for sa in self.speech_acts]))

    @property
    def channel(self):
        # Cover the case where the channel can be filtered
        if self.channels == []:
            return None
        for channel_id in self.channels:
            return Channel.objects.get(id=channel_id)

    def handle_accept(self, user, channels):
        pass

    def handle_reject(self, user, channels):
        pass


def find_primitive_channels(_channels, post_user_profile):
    '''
    Get the channel objects. Input can be a list of ids or objects.
    Output will be a list of objects
    '''
    #instantiate channels
    channels    = []
    channel_ids = []
    for chan in _channels:
        if isinstance(chan, (basestring, ObjectId)):
            channel_ids.append(chan)
        elif isinstance(chan, Channel):
            channels.append(chan)
    if channel_ids:
        channels.extend(
            [c for c in Channel.objects.find(id__in=channel_ids)]
        )

    def select_inbound_or_outbound(channel, post_user_profile):
        result = channel
        if ch.is_service:
            if not post_user_profile:
                # No way to tell, default inbound
                result = channel.inbound_channel
            elif isinstance(channel, FacebookServiceChannel):
                outbounds = channel.get_outbound_ids()
                id = post_user_profile.get("id")
                if id in outbounds:
                    result = channel.outbound_channel
                else:
                    result = channel.inbound_channel
            else:
                result = channel.inbound_channel

        return result

    channels = [select_inbound_or_outbound(ch, post_user_profile) for ch in channels]
    return channels


def find_channels_and_compounds(_channels, user):
    assert False, 'This method is deprecated and should no longer be used'

    #iterate compounds
    all_channels = find_primitive_channels(_channels, user)
    channel_ids = list(set([ch.id for ch in all_channels]))

    compounds = list(CompoundChannel.objects.find_by_user(user, channels__in=channel_ids))

    channels_from_compounds = set()
    for cc in compounds:
        channels_from_compounds = channels_from_compounds.union(cc.channels)

    all_channels = list(channels_from_compounds.union(compounds).union(all_channels))
    return all_channels


def resolve_service_channels(channels):
    '''
    The set of channels will always consist exclusively of primitive channels.
    It is possible that the matching process for figuring out which channel
    to assign will include a post that can be assigned to both an inbound or
    an outbound channel. This is not allowed. So we exclude inbound channels
    if in fact it is related to a service channel.
    '''
    channel_ids = [ch.id for ch in channels]
    channels_set = set(channel_ids)

    service_channels = ServiceChannel.objects.find_by_channels(channel_ids)[:]
    for sc in service_channels:
        #outbound is prioritized, so when both outbound and inbound
        #channels of the same Service channel assigned to post, inbound pulled off
        if sc.outbound in channels_set:
            channels_set.discard(sc.inbound)

    channels = [ch for ch in channels if ch.id in channels_set]
    return channels, service_channels


def channels_with_smart_tags(post, cs):
    """ Get all the channels and smart tags relevant for a 1 pass
    update for this post
    """
    result_channels = Channel.objects.ensure_channels([
            c.parent_channel if c.is_smart_tag else c for c in cs])

    tags = [tag for tag in post.accepted_smart_tags
            if tag.parent_channel in set([c.id for c in result_channels])]

    return result_channels + tags


class PostManager(EventManager):

    def by_time_point(
        self,
        channel,          # <Channel> | <ch_id:ObjectId> | <ch_num:int> | <list|tuple|set>
        topic,            # <topic:str> | <topic_hash:int> | <list|tuple|set>
        from_ts,
        to_ts     = None,
        status    = None, # (opt) <code:int> | <name:str> | <list|tuple|set>
        intention = None, # (opt) <SAType> | <id:int|str> | <name:str> | <list|tuple|set>
        min_conf  = 0.0,  # (opt) <min_confidence:float:0.0..1.0>
        agents    = None, # (opt) list of agent <User>
        languages = None, # (opt) list of languages
        sort_by   = 'time',
        offset = None,
        limit     = None,
        message_type = None,
        last_query_time = None):
        """ Returns a tuple:

            (a sequence of Posts by given
            channel(s), topic(s), status(es) and intention(s)
            within a given time_slot,

            a boolean which is true if more posts are available)

            Notice, channel, topic, status and intention arguments
            all may be a <tuple|list|set> containing several supported
            values of each. In that case the function will issue an OR-query
            covering all combinations of filters.
        """
        from solariat.utils import timeslot

        if offset is None:
            offset = 0

        if limit is None:
            limit = 50

        if to_ts is None:
            to_ts = from_ts

        # -- normalize input --
        seq_types = (list, tuple, set)
        norm_ch   = lambda c: c if isinstance(c, ObjectId) else c.id

        channels = channel if isinstance(channel, seq_types) else [channel]
        channels = map(norm_ch, channels)
        topics   = topic   if isinstance(topic,   seq_types) else [ dict(topic=topic,topic_type="node") ]

        if not status:
            statuses = SpeechActMap.STATUS_NAME_MAP.keys()
        else:
            statuses = status if isinstance(status, seq_types) else [status]

        if not intention:
            intentions = [t.oid for t in sa_labels.ALL_SATYPES if t.name != 'all']
        else:
            intentions = intention if isinstance(intention, seq_types) else [intention]
        intentions = map(get_intention_id,  intentions)

        agent_ids = [a.agent_id for a in (agents or [])]
        lang_ids = map(get_lang_id, languages) if languages else None

        # we assume there is at least one item of each type
        assert channels
        assert statuses
        assert intentions

        # Handle time. The common use cases here are:
        # 1. Search by hour. For this, a single search is good.
        # 2. Search by day. Also, a single search will do.
        # 3. A range query spanning a week or a month. Multiple day quesries required

        # Start with an hourly query and see if it fits in the day. Note, the strategy here
        # Is to ensure the worst case query times are good, at the cost of making average
        # case higher. This is because of the access patterns of large channels. Multiple
        # short queries are still very fast than on much bigger query because we can sample
        # the data systematically in reverse timeslot order

        # So, first compute the slot sequence
        slots = list(timeslot.gen_timeslots(from_ts, to_ts, 'hour', closed_range=False))
        if len(slots) > 25:
            slots = list(timeslot.gen_timeslots(from_ts, to_ts, 'day', closed_range=False))

        slots.reverse()
        # Iterate over slots, and merge (append) result set as you go.
        posts = set([])
        are_more_posts_available = False

        for slot in slots:
            slot_start_dt, slot_end_dt = timeslot.get_timeslot_interval(slot)

            start_ts = Timeslot(slot_start_dt).timeslot
            end_ts   = Timeslot(slot_end_dt).timeslot
            fetch_limit = limit + offset - len(posts)

            if fetch_limit <= 0:
                break

            new_posts = fetch_posts(channels=channels, start_ts=start_ts, end_ts=end_ts, topics=topics,
                                    statuses=statuses, intentions=intentions, min_conf=min_conf,
                                    agents=agent_ids, sort_by=sort_by, limit=fetch_limit, message_type=message_type,
                                    create_date_limit=last_query_time, languages=lang_ids)

            if last_query_time is not None:
                # Just so new posts don't mess with the offset in case of pagination
                # E.G. if 3 new posts arrive in the time between getting page 1 and
                # switching to page2, we don't want those considered in the offset computation
                new_posts = [p for p in new_posts if p.created_at <= last_query_time]

            if offset >= len(new_posts):
                offset = offset - len(new_posts)
            else:
                posts.update(new_posts[offset:])
                offset = 0

            # If we have hit our limit we are done
            if len(posts) >= limit:
                are_more_posts_available = True
                break

        dt_now = now()
        posts = list(posts)
        return sorted(posts, key=lambda x: dt_now - x.created_at)[:limit], are_more_posts_available

    def _requires_moderation(self, user, post):
        channels = set(post._get_channels())
        skipped_channels = set()
        for channel in post._get_channels():
            if channel in skipped_channels:
                continue
            # skip dispatch channels
            skipped_channels.add(channel.get_outbound_channel(user))
            if channel.id in post.channels_map:
                # skip correspondent outbound channels
                skipped_channels.add(post.channels_map[channel.id].outbound_channel)

        for channel in channels - skipped_channels:
            if channel.requires_moderation(post) is True:
                return True
        return False

    def gen_id(self, padding=0, **kw):
        p_id = self.doc_class.gen_id(
            is_inbound=kw['is_inbound'],
            actor_id=kw['actor_id'],
            in_reply_to_native_id=kw.get('in_reply_to_status_id') if kw else None,
            _created=kw['_created'] + timedelta(milliseconds=padding))
        assert p_id
        return p_id

    def create_by_user(self, user, **kw):
        """ Notice: this is called from db.post.utils.factory_by_user(),
                    do not use directly

            Parameters
            ----------
            user     -- <str:objectid> | <objectid> | <User>  (required)
            platform -- <str>                                 (required)
            channels -- [<objectid>, ...]                     (required)
            content  -- <basestring>                          (required)
            ...
        """
        safe_create = kw.pop('safe_create', False)
        if not safe_create:
            raise AppException("Use db.post.utils.factory_by_user instead")
        sync = kw.pop('sync', False)
        add_to_queue = kw.pop('add_to_queue', False)

        kw['force_create'] = True
        # patching kwargs
        kw = Post.patch_post_kw(kw)
        post_data = self._prepare_post_checking_duplicates(PostManager, **kw)
        post, should_skip = post_data

        if should_skip:
            return post

        post.set_engage_stats()  # also saves the post
        self._postprocess_new_post(user, post, sync, add_to_queue)
        return post

    def _postprocess_new_post(self, user, post, sync, add_to_queue=True):
        # postprocess the post
        if get_var('DEBUG_SKIP_POSTPROCESSING'):
            return post

        if sync or get_var('ON_TEST') or get_var('PROFILING'):
            # when testing it is important to check for any exceptions
            postprocess_new_post.sync(user, post, add_to_queue)

            post.reload()  # make sure the post has updated stats
        else:
            # running asynchronously not waiting for results
            postprocess_new_post.ignore(user, post, add_to_queue)

        return post

    def create(self, *args, **kw):
        if 'force_create' not in kw:
            raise AppException("Use db.post.utils.factory_by_user instead")
        else:
            kw.pop('force_create')
            kw.pop('add_to_queue', None)
            return EventManager.create(self, *args, **kw)

    def _set_post_lang(self, post, lang):
       post._lang_code = lang.lang

class UntrackedPost(dict):
    """
    Dummy object that represents the post that is not stored in db yet,
    though there is a reference to this post in another stored post
    """
    id = None
    def __hash__(self):
        return hash(self.id)


class PostExtraFieldsMixin(object):
    """
    Methods and properties to work with original
    twitter/facebook post data stored in post.extra_fields.
    """
    _parent_post = fields.ReferenceField('Post', db_field='pp')

    @cached_property
    def service_channels(self):
        if not hasattr(self, '_cached_service_channels'):
            from solariat_bottle.db.channel.utils import get_platform_class
            self._cached_service_channels = get_platform_class(self.platform).objects.find_by_channels(self.channels)[:]
        return self._cached_service_channels

    @property
    def parent(self):
        return self._parent_post


    def parent_in_conversation(self, conversation, existing_posts=[]):
        """
        Return the parent of this post from an existing conversation.

        :param existing_posts: The rest of the posts from the conversation.
        """
        # In the base case just return the post parent. Specializations of
        # base post might require extra work (e.g. Twitter DMs or chat/email)
        return self.parent

    @property
    def reply_to(self):
        """
        If this post is reply, then this property will
        return list of posts which correspond to this reply
        """
        if not self.service_channels:
            return []
        result = []
        for sc in self.service_channels:
            if "inbound" == sc.route_post(self):
                result = []
                break
            from solariat_bottle.db.conversation import Conversation
            try:
                conv = Conversation.objects.lookup_by_posts(sc, [self])[0]
            except IndexError:
                conv_result = []
            else:
                conv_posts = [long(p) for p in conv.posts]
                post_ids = conv_posts[:conv_posts.index(self.id)]
                post_ids.reverse()
                posts = Post.objects(id__in=conv_posts)
                posts = {p.id: p for p in posts}
                conv_result = []
                for pid in post_ids:
                    post = posts[pid]
                    if sc.route_post(post) == "inbound":
                        conv_result.append(pid)
                    else:
                        break
                conv_result.reverse()
            result += conv_result
        return result


class UpdateContextEmbed(SonDocument):
    """Embed doc, contains stats update context on post reply"""
    agent = fields.NumField(db_field='a')
    outbound_stats = fields.DictField(db_field='os')
    reply = fields.ReferenceField('Post', db_field='r')

    def to_dict(self, fields2show=None):
        return super(UpdateContextEmbed, self).to_dict(fields2show=['agent', 'outbound_stats'])


class TagAssignment(SonDocument):
    """Value part of tag assignments dictionary"""
    status = fields.StringField(db_field='s')
    history = fields.ListField(fields.EmbeddedDocumentField(UpdateContextEmbed), db_field='h')

    @classmethod
    def default(cls):
        return cls(status='assigned', history=[])


class Post(Event, PostExtraFieldsMixin, LanguageMixin):

    MESSAGE_TYPE_MAP = {POST_PUBLIC: 'public',
                        POST_DIRECT: 'direct',
                        POST_OTHER : 'retweet'}

    # collection = 'Post'
    allow_inheritance = True

    manager = PostManager

    @property
    def plaintext_content(self):
        return unwrap_hidden(self.content)

    _user_profile = UserProfileIdField(db_field='up')
    speech_acts = fields.ListField(
        fields.EncryptedHiddenField(fields.DictField(), allow_db_plain_text=True),
        db_field='sa')

    indexes = Event.indexes + ['_user_profile']

    PROFILE_CLASS = UserProfile

    def _get_user_profile(self):
        # user_profile = self.data[self.F('_user_profile')]
        if not self.user_profile_id:
            return None
        try:
            profile_data = self.PROFILE_CLASS.objects.coll.find_one(self.user_profile_id)
            if profile_data:
                return self.PROFILE_CLASS(profile_data)
        except:  #UserProfile.DoesNotExist
            return None

    def _set_user_profile(self, value):
        LOGGER.debug("Setting post.user_profile = {}".format(value))
        self._user_profile = value if (isinstance(value, ObjectId) or value is None)else value.id
        # self.save()

    user_profile = property(_get_user_profile, _set_user_profile)

    def post_type(self):
        return 'public'

    @property
    def parent_post_id(self):
        if self._parent_post:
            return str(self._parent_post.id)
        return None

    @property
    def addressee(self):
        '''
        If the post contains an explict contact indicator, return it.
        This will be platform specific
        '''
        if not self.content:
            return None
        if not self._message_type:
            if self.content[0] == '@':
                possible_contact = self.content.split()[0].lower()
                if len(possible_contact) == 1:
                    return None
                return possible_contact
        elif self._message_type == 1:
            possible_contact = self.content[self.content.rfind('@'):]
            if ' ' in possible_contact or len(possible_contact) == 1:
                # TODO: add extra checks for valid contacts here
                return None
            return possible_contact
        return None

    def platform_specific_data(self, outbound_channel=None):
        return {}

    def get_contacts_for_channel(self, service_channel):
        return [self.get_user_profile().id] if service_channel.route_post(self) == 'inbound' else []

    def set_assignment(self, channel, assignment, context=None):
        """ Handle assignment appropriate for the channel type """
        # and channel.fits_to_event(channel.direction, self.channel.is_inbound):
        if channel.is_smart_tag:
            ta = TagAssignment.default()
            # Note: accumulating contexts, but enough to have very last
            ta = TagAssignment(self._tag_assignments.setdefault(str(channel.id), ta.data))
            ta.status = assignment
            if context:
                ta.history.append(context)
            self._tag_assignments[str(channel.id)] = ta.data
            self.save()
        else:
            self.channel_assignments[str(channel.id)] = assignment
            self.save()

    def get_assignment(self, channel, tags=False):
        """Return channel assignment.
        For the smart tag return assignment of parent channel.
        """
        if channel.is_smart_tag and tags:
            return self.tag_assignments.get(str(channel.id))
        else:
            if channel.is_smart_tag:
                channel_lookup = Channel.objects.get(channel.parent_channel)
            else:
                channel_lookup = channel

            if channel_lookup.is_service == True:
                channel_id = channel_lookup.inbound
            else:
                channel_id = channel_lookup.id

            return self.channel_assignments.get(str(channel_id))

    @property
    def message_type(self):
        return 'direct'

    def get_post_status(self, channel):
        assignment = self.get_assignment(channel)
        return SpeechActMap.STATUS_NAME_MAP[SpeechActMap.STATUS_MAP[assignment]]


    @property
    def tag_assignments(self):
        return {tag_id: TagAssignment(item).status for tag_id, item in self._tag_assignments.items()}

    @property
    def assignment_history(self):
        return {tag_id: TagAssignment(item).history for tag_id, item in self._tag_assignments.items()}

    def has_conversation(self, service_channel):
        '''
        This is slow...
        '''
        from solariat_bottle.db.conversation import Conversation
        if service_channel:
            conversations = Conversation.objects.lookup_by_posts(service_channel, [self],
                                                                 include_closed=True)
            if (conversations):
                if len(conversations[0].posts) > 1:
                    return True
        return False


    def set_reply_context(self, channel, data):
        field_path = "%s.%s" % (self.__class__._reply_context.db_field, channel.id)
        context = UpdateContextEmbed(**data)
        document = {"$addToSet": {field_path: context.data}}
        if context.data[UpdateContextEmbed.reply.db_field]:
            document["$addToSet"][field_path][UpdateContextEmbed.reply.db_field] = \
                DBRef('Post', fields.EventIdField().to_mongo(context.reply.id))
        self.objects.coll.update({'_id': self.__class__.id.to_mongo(self.id)},
            document, multi=False, w=1)

        history = self._reply_context.setdefault(str(channel.id), [])
        history.append(context.data)

    def _get_last_update_context(self, channel):
        assert channel.is_smart_tag
        update_history = self.assignment_history.get(str(channel.id))
        update_context = {}
        if update_history:
            update_context = update_history[-1].to_dict()
        else:
            # try to find data in _reply_context for tag's parent channel
            channel_update_ctx = self._reply_context.get(str(channel.parent_channel))
            if channel_update_ctx:
                update_context = UpdateContextEmbed(channel_update_ctx[-1]).to_dict()
        return update_context

    @property
    def topics(self):
        return list(chain(*[sa['intention_topics'] for sa in self.speech_acts]))

    @property
    def intention_types(self):
        return [ sa['intention_type'] for sa in self.speech_acts]

    @property
    def platform(self):
        if not self._platform:
            channel = self.channel
            if not channel:
                return None
            return channel.platform
        return self._platform

    @property
    def head(self):
        try:
            return self.content.split(' ', 1)[0]
        except (AttributeError, TypeError):
            return ''

    @property
    def lang_specific_head(self):
        try:
            return LingualToken(token=self.content.split(' ', 1)[0], lang_codes=self.language)
        except (AttributeError, TypeError):
            return LingualToken(token='', lang_codes=self.language)

    def _get_channels(self):
        return _get_channels_for_post(self)

    def _get_smart_tags(self):
        """Returns all smart tags for all post channels"""
        from itertools import chain
        return list(chain.from_iterable(ch.smart_tags for ch in self._get_channels() if ch.smart_tags))

    available_smart_tags = property(_get_smart_tags)

    @property
    def active_smart_tags(self):
        return [tag for tag in self.available_smart_tags if tag.status == 'Active']

    @property
    def smart_tags(self):
        from solariat_bottle.db.channel.base import SmartTagChannel
        channel_ids = self.tag_assignments.keys()
        smart_tags = SmartTagChannel.objects(id__in=channel_ids)[:]
        return smart_tags

    @property
    def accepted_smart_tags(self):
        result = []
        for smart_tag in self.smart_tags:
            assignment = self.tag_assignments[str(smart_tag.id)]
            if SpeechActMap.STATUS_MAP[assignment] in [SpeechActMap.ACTIONABLE,
                                                       SpeechActMap.ACTUAL]:
                result.append(smart_tag)
        return result

    @cached_property
    def _accepted_channels(self):
        """
        Returns the list of channel ids the post is not rejected/discarded for.
        """
        from solariat_bottle.db.channel.base import REJECT_STATUSES

        channels = self.channels
        ca = self.channel_assignments or {}

        accepted = []

        for channel in channels:
            if ca.get(str(channel)) not in REJECT_STATUSES:
                accepted.append(channel)

        return accepted

    @cached_property
    def channels_map(self):
        """Dict to lookup Service channel by sub-channel"""
        result = {}
        for channel in self.service_channels:
            result[channel.inbound] = channel
            result[channel.outbound] = channel
        return result

    def extract_signature(self):
        signature = SIGNATURE_RE.search(self.plaintext_content)
        if signature:
            return signature.group()
        return None

    def find_agent_id(self, service_channel):
        """
            :param service_channel: - the service channel for which we try to find the agent

            :returns: the agent id, or 0 (all agents) in case none could be inferred
        """
        agent = self.find_agent(service_channel)
        if agent:
            service_channel.add_agent(agent)
            return agent.agent_id
        return 0

    def find_agent(self, service_channel):
        """
            :param service_channel: - the service channel for which we try to find the agent
            :returns: the User obj or None
        """
        account = service_channel.account
        agent = User.objects.find_agent_by_post(account, self)
        return agent

    @property
    def view_url_link(self):
        return "View Post"

    def get_agent_data(self, channel):
        """If channel is outbound of service channel or
        channel is a smart tag of outbound channel,
        returns {"agent": agent_id}.
        Otherwise (or if agents not found) returns {}
        """
        if not hasattr(self, '_agents_map'):
            self._agents_map = {}
            for ch in self._get_channels():
                sc = self.channels_map.get(ch.id)
                if sc:
                    self._agents_map[ch.id] = sc.extract_agents(self)

        agents_data = self._agents_map.get(channel.parent_channel if channel.is_smart_tag else channel.id)
        return agents_data or {}

    def reply(self, dry_run, msg, user, outbound_channel, response_type=None):
        "Send message to author via channel machinery"
        if outbound_channel.is_dispatchable:
            if response_type is not None:
                is_direct = response_type == 'direct'
            else:
                is_direct = response_type
            outbound_channel.send_message(dry_run, msg, self, user=user, direct_message=is_direct)

            log_event(
                'MessageDispatchedEvent',
                user           = user.email,
                note           = "Message dispatched",
                platform       = self.platform,
                content        = msg,
                recipient_name = self.user_profile.name
            )
        else:
            LOGGER.debug('Warning. No post has been dispacthed because the channel %s is not dispatchable.' % outbound_channel.title)

    def share(self, dry_run, user):
        "share post via channel machinery"

        outbound_channel = self.channel.get_outbound_channel(user)

        if outbound_channel == None:
            outbound_channel = self.channel

        if outbound_channel.is_dispatchable:
            outbound_channel.share_post(self, user, dry_run=dry_run)

    @property
    def user_profile_id(self):
        up = self.data[self.__class__._user_profile.db_field]
        if isinstance(up, DBRef):
            return up.id
        elif isinstance(up, (ObjectId, basestring)):
            return up
        return None

    def set_vote(self, user, vote):
        if vote is False:
            if user.id not in self.disagree:
                self.disagree.append(user.id)
                self.save_by_user(user)

    def _get_votes_path(self, sa_idx, intention=None, topic=None):
        if bool(intention) == bool(topic):
            raise AttributeError('Must define either intention or topic.')

        field = intention or topic
        scope = 'intention' if intention else 'topic'
        field = replace_special_chars(u"%s::%s" % (sa_idx, field))
        return field, scope

    def get_vote_for(self, user, sa_idx, intention=None, topic=None):
        field, scope = self._get_votes_path(sa_idx, intention, topic)

        try:
            value = self.user_feedback['%s' % user.id][scope][field]
        except KeyError:
            #try to find vote among old data with dots
            try:
                value = 0
                values = self.user_feedback['%s' % user.id][scope]
                for k, v in values.items():
                    if replace_special_chars(k) == field:
                        value = v
                        break
            except KeyError:
                value = 0

        return value

    def set_vote_for(self, user, vote, sa_idx, intention=None, topic=None):
        """
        `vote` -1 | 0 | 1
        -1  voted down
         0  not voted
         1  voted up
        """
        field, scope = self._get_votes_path(sa_idx, intention, topic)

        votes = self.user_feedback
        votes.setdefault('%s' % user.id, {})
        votes['%s' % user.id].setdefault(scope, {})
        votes['%s' % user.id][scope][field] = vote
        self.user_feedback = votes

        PostUserFeedback(
            channels      = self.channels,
            post          = self.id,
            user          = user.id,
            speech_act_id = sa_idx,  # note: this is really a speech-act index (0..N)
            vote          = vote,
            vote_kind     = PostUserFeedback.TOPIC if scope == 'topic' else PostUserFeedback.INTENTION,
            content       = intention or topic,
            last_modified = now()
        ).save()

    def get_vote(self, user):
        "Return True if user did not vote at all or voted OK"
        if user.id in self.disagree:
            return False
        return True


    @property
    def intention(self):
        return self.intention_confidence  # WTF?  why not intention_name?

    @property
    def user_tag(self):
        profile = self.user_profile
        if profile:
            return profile.user_name
        return 'anonymous'

    def get_user_profile(self):
        try:
            profile = self.user_profile
            if profile:
                return profile
        except UserProfile.DoesNotExist:
            self.user_profile = None
            field = self.name2db_field('_user_profile')
            LOGGER.error(
                u"Dereference error: post.user_profile. post=%s user_profile=%r",
                self,
                self.data[field]
            )
            self.objects.coll.update(
                {"_id": self.id},
                {"$set": {field: None}}
            )

        return UserProfile.non_existing_profile()

    def customer_profile(self, account):
        CustomerProfile = account.get_customer_profile_class()
        customer_profile = super(Post, self).customer_profile(account)
        if customer_profile:
            return customer_profile

        def get_customer_by_user_profile(up_id):
            return CustomerProfile.objects.find_one(linked_profile_ids=str(up_id))

        if self.actor_id:
            actor = self.actor
            if isinstance(actor, CustomerProfile):
                return actor
            elif isinstance(actor, UserProfile):
                return get_customer_by_user_profile(actor.id)

        customer_by_user_profile = get_customer_by_user_profile(self.user_profile_id)
        if customer_by_user_profile:
            return customer_by_user_profile

    def get_matches(self, user=None, **kw):
        return []

    def get_punks(self):
        "Return a set of PUNKs (topics of speech-acts)"
        topics = set()
        for sa in self.speech_acts:
            topics.update(sa['intention_topics'])
        return list(topics)

    def to_dict(self, fields2show=None):
        result = super(Post, self).to_dict(fields2show)
        if not fields2show or 'speech_acts' in fields2show:
            result['speech_acts'] = map(unwrap_hidden, self.speech_acts)
        if not fields2show or 'intention' in fields2show:
            result['intention'] = str(self.intention)
        if not fields2show or 'platform' in fields2show:
            result['platform'] = self.platform
        if not fields2show or 'channel_assignments' in fields2show:
            result['channel_assignments'] = self.channel_assignments
        if 'content' in result:
            result['content'] = unwrap_hidden(result['content'])
        return result

    def set_engage_stats(self, to_save=True):
        "Set topics, intention type and confidence"

        def _get_max_scored_sa():
            "return name and score of max scored SA label"
            pairs = []

            for sa in self.speech_acts:
                pairs.append((sa['intention_type_conf'], sa['intention_type']))

            return sorted(pairs, reverse=True)[0]

        confidence, title = _get_max_scored_sa()
        sa_type = sa_labels.SAType.by_title(title)

        if not sa_type:
            raise AppException('%r is not a valid SAType title' % title)

        self.intention_name       = sa_type.name
        self.intention_confidence = confidence
        self.punks                = self.get_punks()

        if to_save:
            self.save()

    def adjust_confidence_from_matchables(self, to_save=True):
        """ Once we have computed the matchables, we can set the intention
            and relevance based on the best matchable. This will over-ride
            default values
        """
        matchables = self._get_matchable_dicts()[0]  # caches result

        if not matchables:
            return

        best_match     = matchables[0]
        self.relevance = best_match['relevance']

        best_type_ids  = set(best_match['intention_type_ids'])

        if best_type_ids == set([u'0']):
            intention_conf_values = [
                sa['intention_type_conf'] for sa in self.speech_acts
            ]
        else:
            intention_conf_values = [
                sa['intention_type_conf'] for sa in self.speech_acts
                if sa['intention_type_id'] in best_type_ids
            ]

        self.intention_confidence = safe_max(intention_conf_values)

        if to_save:
            self.save()

    def __status_changed(self, from_status, from_status_parent, to_status):
        """
        Test if the status is in fact changed for a given 3-pair of from_status,
        from_status_parent (in case smart tags) and to_status.
        """
        return not (from_status is not None and
                SpeechActMap.STATUS_MAP[to_status] == SpeechActMap.STATUS_MAP[from_status] and
                SpeechActMap.STATUS_MAP[to_status] == SpeechActMap.STATUS_MAP[from_status_parent])


    def _record_decrement_log(
            self, action, from_status, from_status_parent,
            to_status, remove_rejected=None, status_unchanged=None, ret=False):
        """
        Debug method to save some stats updates.
        """
        decrement_log = {
            'action': action,
            'from_status': from_status,
            'from_status_parent': from_status_parent,
            'to_status': to_status,
            'remove_rejected': remove_rejected,
            'status_unchanged': status_unchanged,
            'return': not (remove_rejected or status_unchanged)
        }
        DecrementLog.objects.coll.update(
            {
                "_id": self.id,
                "content": unwrap_hidden(self.content)
            },
            {
                "$push": {"decrement_log": decrement_log}
            },
            upsert=True
        )


    def should_decrement_stats(self, action, from_status, from_status_parent, to_status):
        # Test if we need in fact to decrement the stats

        # Boolean that represents situation where for some reason, we remove an already rejected status
        remove_rejected = ((from_status == None or SpeechActMap.STATUS_MAP[from_status] == SpeechActMap.REJECTED) and
                           (action == 'remove' or SpeechActMap.STATUS_MAP[to_status] == SpeechActMap.REJECTED))
        # Boolean that repesents situation where status is not actually changed (eg. from one actionable to another)
        status_unchanged = not self.__status_changed(from_status, from_status_parent, to_status)

        if DEBUG_STATS:
            self._record_decrement_log(
                action, from_status, from_status_parent,
                to_status, remove_rejected, status_unchanged, not (remove_rejected or status_unchanged))

        return not (remove_rejected or status_unchanged)

    def should_increment_stats(self, action, from_status, from_status_parent, to_status):
        # Increment if the status has in fact changed.
        return self.__status_changed(from_status, from_status_parent, to_status)

    def _handle_filter(self, channels, status, **kw):
        """ This algorithm is used to handle the update logic
        for a post that has changed its channel status. There are 2 variattions
        to consider: actionability and tag status. Also, have to consider the case
        of actionability where the select channel is a smart tag.
        """

        if not hasattr(channels, '__iter__'):
            channels = [channels]

        original_channels = set(channels)
        all_channels = []
        for channel in channels:
            # If a channel is a smart tag just update it's status, otherwise
            # for any other channel also extend with the list of assigned tags
            if not channel.is_smart_tag:
                all_channels.extend(channels_with_smart_tags(self, [channel]))
            else:
                all_channels.append(channel)
        channels = all_channels
        if not all_channels:
            return
        platforms = set([c.platform for c in all_channels])
        assert len(platforms) <= 1, "A single post should never be part of multiple platforms. Got %s for post %s and channels %s" % (
                                        platforms, self.id, all_channels)

        # some updates require parent channel assignments, some smart tag channel assignment
        # map is in the form: (channel, from_status_parent, from_status)
        channels_current_status_map = []

        from solariat_bottle.db.post.utils import get_platform_class
        refreshed_post = get_platform_class(self.platform).objects.get(self.id)

        # Filter by Smart tags direction and whether post is inbound or outbound
        for c in channels:
            # we refresh post because its state could have changed
            channels_current_status_map.append(
                (
                    c,
                    refreshed_post.get_assignment(c)
                )
            )

        handle_channel_filter = kw.pop('handle_channel_filter', kw.get('filter_others', True))
        safe_channels = []
        for (channel, from_status_parent) in channels_current_status_map:
            # if kw.get('should_update_stats', True):
            try:
                if not channel.is_smart_tag and refreshed_post.get_assignment(channel, channel.is_smart_tag) == 'replied':
                    LOGGER.warning("You are trying to change the status of a replied post.")
                    refreshed_post.save()
                else:
                    if handle_channel_filter and channel in original_channels:
                        channel._handle_filter(refreshed_post, status)

                    channel.reload()

                    channel.update_stats(refreshed_post, original_channels, status, from_status_parent, kw)

                    safe_channels.append(channel)
            except Exception, ex:
                import traceback
                traceback.print_exc()
                LOGGER.error("Error on updating post stats for post %s and channel %s. Traceback: %s" %
                                 (self.id, channel.id, str(ex)))

        refreshed_post.save()

        # Reset the speech act mapping keys because the stats has changed.
        kw['channels'] = safe_channels
        reset_speech_act_keys(refreshed_post, **kw)

        # Since we used the refreshed post for all stats update, do a reload at this
        # point so the current instance is also having all the updates
        self.reload()
        # If we want to filter others, kick that off for each channel
        if kw.get('filter_others', True):
            channel_ids = [c.id for c in channels]

            for channel_id in channel_ids:
                filter_similar_posts.sync(refreshed_post, channel_id)
            # Running things async just increase risk of stats updates collision, skip for now
            #     futures = []
            #     # we run the filteing asynchronously
            #     for channel_id in channel_ids:
            #         future = filter_similar_posts.async(refreshed_post, channel_id)
            #         futures.append(future)
            #     # but we still wait for it to finish,
            #     # because otherwise it causes some issue with stats updates
            #     for future in futures:
            #         future.result()

    def handle_accept(self, user, channels, **kw):
        self._handle_filter(channels, 'starred', **kw)

    def handle_reject(self, user, channels, **kw):
        self._handle_filter(channels, 'rejected', **kw)

    def handle_reply(self, user, channels, **kw):
        kw['filter_others'] = False
        self._handle_filter(channels, 'replied', **kw)

    def handle_add_tag(self, user, channels, **kw):
        self._handle_filter(channels, 'starred', **kw)

    def handle_remove_tag(self, user, channels, **kw):
        self._handle_filter(channels, 'rejected', **kw)


class PostMatchManager(ChannelsAuthManager):
    "Reimplement create method"
    def _get_post_obj(self, user, parameter):
        "Return post obj for given parameter"
        if isinstance(parameter, Post):
            return parameter
        if isinstance(parameter, (int, long, str, unicode, ObjectId)):
            if isinstance(parameter, (str, unicode)):
                parameter = long(parameter)
            return Post.objects.get_by_user(user, parameter)
        raise AppException(
            "%s (type: %s) shoud be post id or post obj itself" % (parameter, type(parameter)))

    def create_by_user(self, user, **kw):
        """ If impressions and rejects empty
        post should get state 'rejected'

        """
        from solariat_bottle.db import channel_stats

        assert kw.get('post'), "Post parameter must be provided"
        kw['post'] = post = self._get_post_obj(user, kw['post'])

        # Use the post channels by default.
        if 'channels' not in kw:
            kw['channels'] = post.channels

        kw['content'] = post.plaintext_content
        #if not kw.get('impressions') and not kw.get(
        #    'rejects'):
        #    post.status = 'rejected'
        #    post.save_by_user(user)
        if kw.get('custom_response'):
            matchable = self.make_matchable_on_demand(
                user,
                post,
                kw['custom_response'],
                kw.get('speech_act_types', []))
            kw['impressions'] = [matchable]

        if not kw.get('speech_act_types'):
            post_dict = post.to_dict()
            kw['speech_act_types'] = [
                    speech_act['intention_type']
                    for speech_act in post.speech_acts]

        if not kw.get('relevance'):
            post_dict = post.to_dict()
            if post_dict['matchables']:
                kw['relevance'] = trim_to_fixed_point(
                    post_dict['matchables'][0]['relevance'],
                    2)

        """https://github.com/solariat/tango/issues/295#issuecomment-2287853
        You can always do .status_str.title() for 'Rejected'
        """

        if not kw.get('impressions') and not kw.get('rejects'):
            kw['status'] = 'rejected'
        elif not kw.get('impressions') and kw.get('rejects'):
            kw['status'] = 'actionable'
        elif kw.get('impressions'):
            kw['status'] = 'approved'
        else:
            kw['status'] = 'unknown'

        if kw.get('impressions') and kw.get('released') is not False:
            kw['released'] = True
        else:
            kw['released'] = False

        item = ChannelsAuthManager.create_by_user(self, user, **kw)
        if item.impressions and item.released:
            channel_stats.impressions_recieved(
                kw['post'].channel,
                item.impressions,
                item.created)

        return item


class PostMatch(ChannelsAuthDocument):
    "Document collects feedback  about Post/Matchables"

    manager = PostMatchManager
    post = fields.ReferenceField('Post', required=True) # , unique=True
    impressions = fields.ListField(
        fields.ReferenceField('Matchable'))
    rejects = fields.ListField(
        fields.ReferenceField('Matchable'))
    speech_act_types = fields.ListField(fields.StringField(), db_field='ss')
    content = fields.StringField(db_field='c')
    intention = fields.NumField(default=0.0, db_field='inn')
    relevance = fields.NumField(default=0.0, db_field='rlc')
    actionable = fields.NumField(default=0.0, db_field='act')
    custom_response = fields.StringField(db_field='crs')
    status = fields.StringField(
        choices=('approved', 'actionable', 'rejected', 'unknown'),
        default='unknown')
    released = fields.BooleanField(default=True, db_field='rl')

    admin_roles = [ADMIN, STAFF, AGENT]

    @property
    def created(self):
        return self.id.generation_time


class PostClickManager(ChannelsAuthManager):

    def _get_post(self, obj_or_id):
        if isinstance(obj_or_id, Post):
            return obj_or_id
        return Post.objects.get(obj_or_id)

    def create_by_user(self, user, **kw):
        from solariat_bottle.db import channel_stats
        assert kw.get('post'), "post should be provided"
        assert kw.get('matchable'), "matchable should be provided"
        kw['post'] = post = self._get_post(kw['post'])
        kw['matchable'] = matchable = self._get_matchable(kw['matchable'])
        channel_stats.post_clicked(post, matchable)
        if not 'channels' in kw:
            kw['channels'] = kw['post'].channels
        return ChannelsAuthManager.create_by_user(self, user, **kw)

    def create(self, *args, **kw):
        raise NotImplementedError


class PostClick(ChannelsAuthDocument):
    "Store info about Post's click"

    manager = PostClickManager
    post = fields.ReferenceField(Post)
    matchable = fields.ReferenceField('Matchable')
    redirect_url = fields.StringField(default="")

    admin_roles = [ADMIN, STAFF, AGENT]


class PostUserFeedback(ChannelsAuthDocument):
    "Collection of user votes on post topic/intention."
    TOPIC = 1
    INTENTION = 2

    post = fields.EventIdField(db_field='p')
    speech_act_id = fields.StringField(db_field='sa')
    user = fields.ObjectIdField(db_field='u')
    vote = fields.NumField(db_field='vt', choices=(-1,0,1))
    vote_kind = fields.NumField(db_field='vk', choices=(TOPIC, INTENTION))
    content = fields.StringField(db_field='ti')  #extracted topic or intention name
    last_modified = fields.DateTimeField(db_field='lm')


# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0



