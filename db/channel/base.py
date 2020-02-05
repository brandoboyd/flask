"""
Contains the base classes for channels, independent of any platform.

"""
from collections import defaultdict
from datetime import datetime
from functools import wraps
import re

from bson.dbref     import DBRef
from bson.objectid  import ObjectId
from solariat_bottle.configurable_apps import APP_GSA, APP_GSE, APP_NPS
from werkzeug.utils import cached_property
from pymongo.errors import DuplicateKeyError
from solariat.utils.lang.support import get_supported_languages

from solariat_bottle.settings import (
    get_var, LOGGER, AppException)
from solariat.db                import fields
from solariat_bottle.db.account        import Account
from solariat_bottle.db.channel_filter import ChannelFilter
from solariat_bottle.db.contact_label  import ExplcitTwitterContactLabel, ContactLabel
from solariat_bottle.db.sequences      import NumberSequences
from solariat_bottle.db.group          import Group
from solariat_bottle.db.roles          import ADMIN, STAFF, ANALYST
from solariat_bottle.db.user           import User
from solariat_bottle.db.auth           import (
    AuthDocument, AuthError, AuthManager, Manager, Document,
    ArchivingAuthManager, ArchivingAuthDocument)
from solariat_bottle.utils.facebook_extra import reset_fbot_cache

WORD_SPLIT_RE = re.compile('[\t\n .,:;!\?]+')

TWITTER_INDEX  = 0
FACEBOOK_INDEX = 1
LINKEDIN_INDEX = 2
SOLARIAT_INDEX = 3
VOC_INDEX      = 4
CHAT_INDEX     = 5
EMAIL_INDEX    = 6

# Platforms are listed here. It is an expanding list as we integrate
# more broadly. The index is used to reference platfroms efficiently
# (storage of number).
PLATFORM_MAP = {
    'Twitter'  : {'index' : TWITTER_INDEX,  'base_url' : 'https://twitter.com' },
    'Facebook' : {'index' : FACEBOOK_INDEX, 'base_url' : 'https://facebook.com' },
    'LinkedIn' : {'index' : LINKEDIN_INDEX, 'base_url' : 'https://linkedin.com' },
    'Solariat' : {'index' : SOLARIAT_INDEX, 'base_url' : 'https://tango.solariat.com' },
    'VOC'      : {'index' : VOC_INDEX,      'base_url' : 'https://tango.solariat.com' },
    'Chat'     : {'index' : CHAT_INDEX,     'base_url' : 'https://chat-link.com' },
    'Voice'    : {'index' : CHAT_INDEX,     'base_url' : 'https://chat-link.com' },
    'Email'    : {'index' : EMAIL_INDEX,    'base_url' : 'https://email-link.com' },
}
PLATFORM_BY_INDEX = dict((v['index'], k) for k, v in PLATFORM_MAP.iteritems())

# Set Status control
REJECT_STATUSES = ('rejected', 'discarded')
ACCEPT_STATUSES = ('starred', 'highlighted', 'replied', 'accepted')


def get_platform_by_index(index):
    return PLATFORM_BY_INDEX[index]


def filtered_channels(channels, filter_service=False, filter_compound=False):
    return [ch for ch in channels
            if not (ch.is_contact or ch.is_smart_tag
                    or ch.is_service  and filter_service
                    or ch.is_compound and filter_compound
                    or ch.read_only   and filter_service and filter_compound
    )]


def create_outbound_post(user, outbound_channel, content, inbound_post):
    '''
    Used for testing purposes for dispatching when not actually posting
    to an external platform

    :param user: the SO user which posted a reply
    :param outbound_channel: the dispatch channel which is being used
    :param content: the content of the newly issued reply
    :param inbound_post: the post that was replied to
    '''
    from solariat_bottle.db.post.utils import factory_by_user

    channels = [outbound_channel]
    for sc in inbound_post.service_channels:
        channels.append(sc.outbound_channel)
        channels.append(sc.get_outbound_channel(user))

    if not user.user_profile:
        outbound_channel.patch_user(user)

    post = factory_by_user(user,
                           channels=channels,
                           content=content,
                           # actor_id=user.user_profile.agent_profile.id,
                           # is_inbound=False,
                           _parent_post=inbound_post)
    # The entire flow from conversation handling should make sure to call
    # handle_reply on the inbound post, so we should not call this twice.
    #inbound_post.handle_reply(user, inbound_post._get_channels(), handle_channel_filter=True)
    return post


def needs_postfilter_sync(method):
    @wraps(method)
    def _wrapped(this, *args, **kwargs):
        LOGGER.info(u"Invoked %s[%s].%s %s %s" % (
            this.__class__.__name__, this.id, method.__name__, args, kwargs))
        result = method(this, *args, **kwargs)
        this.update(status=this.initial_status)
        if this.is_service:
            this.inbound_channel.update(status=this.inbound_channel.initial_status)
            this.outbound_channel.update(status=this.outbound_channel.initial_status)
        return result
    return _wrapped


class ChannelManager(ArchivingAuthManager):
    "Over-ride create method"

    def create(self, **kw):
        'Force a unique and monotonically increasing counter.'
        kw['counter'] = Channel.make_counter()
        channel = AuthManager.create(self, **kw)

        if 'status' not in kw:
            channel.on_active()
        return channel

    def create_by_user(self, user, **kw):
        if not 'account' in kw and user.account:
            kw['account'] = user.account
        return super(ChannelManager, self).create_by_user(user, **kw)

    def find_by_user(self, user, perm='r', **kw):
        if 'status' not in kw and 'status__in' not in kw:
            kw['status'] = {"$ne": 'Archived'}
        #filter channels by current account
        if not kw.pop('_all_accounts', False) and user.account:
            if not 'account' in kw:
                kw['account'] = user.account
        return AuthManager.find_by_user(self, user, perm, **kw)

    def ensure_channels(self, items):
        channels = [item for item in items if isinstance(item, Channel)]
        channel_ids = [item for item in items if isinstance(item, (basestring, ObjectId))]
        if channel_ids:
            channels.extend(Channel.objects(id__in=channel_ids)[:])
        return channels

    def remove_groups_by_user(self, user, group_ids):
        self.coll.update(
                {
                    'at': DBRef('Account', user.current_account.id),
                    'acl': {'$in': group_ids},
                },
                {'$pullAll': {'acl': group_ids}},
                multi=True)


class SmartTagHolderMixin(object):
    """Channel.smart_tags"""
    _smart_tags = fields.ListField(fields.ObjectIdField(), db_field='sts')

    def _get_smart_tags(self):
        if not hasattr(self, '_cached_smart_tags'):
            tags = SmartTagChannel.objects(parent_channel=self.id, status__ne='Archived')[:]
            self._smart_tags = [t.id for t in tags]
            self._cached_smart_tags = tags
        return self._cached_smart_tags

    def _set_smart_tags(self, val):
        assert isinstance(val, list)
        self._smart_tags = [o.id for o in val]
        self._cached_smart_tags = val

    smart_tags = property(_get_smart_tags, _set_smart_tags)

    def add_tag(self, tag):
        tags = self.smart_tags
        if tag not in tags:
            tags.append(tag)
        self.smart_tags = tags

    def remove_tag(self, tag):
        tag.archive()
        tags = [t for t in self.smart_tags if t.id != tag.id]
        self.smart_tags = tags


class Channel(ArchivingAuthDocument, SmartTagHolderMixin):
    collection = 'Channel'

    manager = ChannelManager
    allow_inheritance = True

    title = fields.StringField(required=True, db_field='te')

    status = fields.StringField(default='Suspended',  db_field='ss',
                                choices=('Active', 'Interim', 'Suspended', 'Archived'))

    posts_tracking_enabled = fields.BooleanField(db_field='pte')
    posts_tracking_disable_at = fields.DateTimeField(db_field='ptd')

    type = fields.StringField(db_field='tpe')
    intention_types = fields.ListField(fields.StringField(),
                                       db_field='it')
    description = fields.StringField(db_field='dn')
    parent_channel = fields.ObjectIdField(db_field='pc')

    is_inbound = fields.BooleanField(db_field='in', default=True)

    is_migrated = fields.BooleanField(db_field='im', default=False)

    '''
    Thresholds constraining channel behavior. Customers
    can be more restrictive, but we impose limits to
    protect the integrity of the end user experience
    '''
    moderated_relevance_threshold = fields.NumField(default=0.0,
                                                    db_field='mrt')
    auto_reply_relevance_threshold = fields.NumField(default=1.0,
                                                     db_field='arrt')
    moderated_intention_threshold = fields.NumField(default=0.0,
                                                    db_field='mit')
    auto_reply_intention_threshold = fields.NumField(default=1.0,
                                                     db_field='arit')

    '''
    0 <= exclusion_threshold <= inclusion_threshold <= 1
    '''
    exclusion_threshold = fields.NumField(default=0.2,
                                          db_field='ed')
    inclusion_threshold = fields.NumField(default=0.8,
                                          db_field='id')

    nof_posts = fields.NumField(default=0, db_field='np')

    # used to encode channel numbers sequentially and uniquely,
    # gets populated automatically on .save()
    counter = fields.NumField(unique=True, default=0, db_field='cr')

    # It has to be moved to customer preferences
    bitly_login = fields.StringField()
    bitly_access_token = fields.StringField()

    # All channels should be attributed to an account
    account = fields.ReferenceField(Account, db_field='at')

    # Deperecate this
    _channel_filter = fields.ReferenceField(ChannelFilter,
                                            db_field='cf')
    adaptive_learning_enabled = fields.BooleanField(db_field='ale', default=True)

    # Use an id in order to allow cache based access
    _channel_filter_id = fields.ObjectIdField(db_field='cd')

    # Track when it was last purged.
    last_purged = fields.DateTimeField(db_field='ld')

    # _response_match_enabled = fields.BooleanField(db_field='rme', default=False)

    indexes = [("counter",), ('parent_channel', 'status'), ("account",)]

    admin_roles = [ADMIN, STAFF, ANALYST]

    remove_personal = fields.BooleanField(db_field='rp', default=False)

    def set_dynamic_class(self, inheritance):
        ''' Support dynamic channels '''
        from solariat_bottle.db.dynamic_channel import DynamicEventsImporterChannel

        if DynamicEventsImporterChannel.__name__ in inheritance:
            DynamicEventsImporterChannel.set_dynamic_class(self, inheritance[0])

    @property
    def account_type(self):
        return self.account and self.account.account_type or None

    @property
    def is_dispatch_channel(self):
        return False

    def patch_user(self, user):
        """
        Allows additional user profile nformation to be added in a channel
        specific way. Called for creating outbound posts.
        """
        pass
    
    def get_conversation_id(self, post):
        """
        Compute a unique 50 bits id for a given inbound post.
        """
        from solariat_bottle.utils.id_encoder import pack_components
        COUNTER_WIDTH = 50
        c_counter = NumberSequences.advance('ConversationId_%s' % self.counter)
        return pack_components((c_counter, COUNTER_WIDTH),)

    def can_view(self, user_or_group):
        """ Return True if read perm exists """
        return (self.has_perm(user_or_group) and
                self.account and self.account.has_perm(user_or_group))

    def can_edit(self, user_or_group, admin_roles=None):
        """ Return True if write perm exists. Allow overwrite or admin right roles """
        admin_roles = admin_roles or self.admin_roles
        return (super(Channel, self).can_edit(user_or_group, admin_roles) and
                self.account and self.account.has_perm(user_or_group))

    def to_dict(self, fields2show=None):
        res = super(Channel, self).to_dict(fields2show)
        if '_smart_tags' in res:
            # This is to get rid of ObjectIds from the smart tags attribute.
            # Not really elegant, should just rewrite whole method and only
            # return what we need
            res['_smart_tags'] = [str(x) for x in res['_smart_tags']]
        return res

    def is_assigned(self, post):
        ''' True if the post is assigned to the channel, otherwise False '''
        from solariat_bottle.db.speech_act import SpeechActMap
        key = str(self.id)
        return key in post.channel_assignments and post.channel_assignments[key] in SpeechActMap.ASSIGNED

    def is_mutable(self, post):
        ''' True if the tag is not user specified '''
        from solariat_bottle.db.speech_act import SpeechActMap
        key = str(self.id)
        return key not in post.channel_assignments or post.channel_assignments[key] in SpeechActMap.PREDICTED

    def get_outbound_channel(self, user):
        # Each specific channel should know how to get it's own dispatch channel
        # depending on specific platform
        return user.get_outbound_channel(self.platform)

    def get_title(self):
        return self.title

    def set_title(self, value):
        title = value
        if self.parent_channel:
            title = u"%s %s" % (value, "Inbound" if self.is_inbound else "Outbound")
        self.title = title

    _title = property(get_title, set_title)

    def __get_channel_filter(self):
        if hasattr(self, '_channel_filter_id') and self._channel_filter_id is not None:
            try:
                return ChannelFilter.objects.get_instance(self._channel_filter_id)
            except:
                pass
        _channel_filter = ChannelFilter.objects.create_instance(channel=self)
        self._channel_filter_id = _channel_filter.id
        self.save()

        return _channel_filter

    def __set_channel_filter(self, cf):
        self._channel_filter_id = cf.id

    channel_filter = property(__get_channel_filter, __set_channel_filter)

    @property
    def is_authenticated(self):
        return False

    def save(self):
        # setup channel counter
        if self.counter == 0:
            self.counter = Channel.make_counter()

        # clean up possible back reference cache (channel -> channel_filter -> channel).
        # we need this because .channel_filter uses LRU cache in ChannelFilterManager
        # and may store an instance that itself has cached a reference to .channel
        if self._channel_filter_id is not None:
            self.channel_filter.clear_ref_cache()

        AuthDocument.save(self)

    def update_stats(self, post, original_channels, status, from_status_parent, context):
        """
        Do any context updates as necessary, then update post assignment for this
        status and delegate updating stats for other models (trends, channel stats etc.)
        """
        from solariat_bottle.utils.post import update_stats
        from_status = post.get_assignment(self, False)
        post.set_assignment(self, status)
        update_stats(post, self, status, action='update', from_status=from_status, **context)

    def mentions(self, post):
        """Stub. Subclasses can resolve"""
        return []

    def find_direction(self, post):
        """Stub. Subclasses can expand on this as appropriate."""
        if self.parent_channel:
            return Channel.objects.get(id=self.parent_channel).find_direction(post)
        elif self.is_individual(post):
            return 'individual'
        else:
            return 'unknown'

    def is_individual(self, post):
        return False

    @classmethod
    def make_counter(cls):
        return NumberSequences.advance('ChannelCounter')

    def get_matchable_relevance(self, matchable):
        "Lookup the relevance score"
        return matchable['relevance']

    def use_matchable_for_relevance(self):
        return True

    @property
    def speech_act_types(self):
        return self.intention_types

    @property
    def relevance_threshold(self):
        return self.moderated_relevance_threshold

    @property
    def type_id(self):
        return 0

    @property
    def type_name(self):
        return "Solariat"

    @property
    def base_url(self):
        return PLATFORM_MAP[self.platform]['base_url']

    @property
    def platform_id(self):
        return PLATFORM_MAP[self.platform]['index']

    @property
    def platform(self):
        return "Twitter"

    @property
    def read_only(self):
        if not self.parent_channel:
            return False

        try:
            channel = Channel.objects.get(id=self.parent_channel)
            assert channel
        except:
            return False
        return True

    @property
    def is_dispatchable(self):
        "Determines whether the channel can send outbound messages."
        return False

    def requires_moderation(self, post):
        if self.parent_channel is not None and not self.is_inbound:
            return False

        if self.account.account_type in ("GSE", "Skunkworks") \
                or self.account.selected_app != APP_GSA:
            return False

        if post.channel_assignments[str(self.id)] in ['rejected', 'filtered'] or \
           post.relevance < self.moderated_relevance_threshold:
            return False

        return (
            post.intention_confidence <= self.auto_reply_intention_threshold or \
            post.relevance <= self.auto_reply_relevance_threshold)

    def send_message(self, dry_run, creative, post, user):
        'Stub for subclasses to implement'
        pass

    @property
    def is_compound(self):
        return False

    @property
    def is_service(self):
        return False

    @property
    def is_contact(self):
        return False

    @property
    def is_smart_tag(self):
        return False

    @property
    def keywords(self):
        return []

    @property
    def requires_interim_status(self):
        return False

    @property
    def initial_status(self):
        if get_var('APP_MODE') != 'dev' and self.requires_interim_status:
            return 'Interim'
        else:
            return 'Active'

    def on_active(self):
        self.status = self.initial_status
        self.update(set__status=self.status)

    def on_suspend(self):
        self.status = 'Suspended'
        self.update(set__status=self.status)
        reset_fbot_cache(self.id)

    def __setattr__(self, key, value):
        # Move smart tags to new account with channel
        if key == 'account':
            new_account = value
            if self.account and self.account.id != new_account.id:
                self.__dict__.pop('_cached_smart_tags', None)   # Make sure we always update ALL tags not only cached
                for tag in self.smart_tags:
                    tag.account = new_account
                    tag.update(set__account=new_account)

        super(Channel, self).__setattr__(key, value)

    def archive(self):
        for tag in self.smart_tags:
            tag.archive()
        self.status = 'Archived'
        self.update(set__status='Archived')
        ArchivingAuthDocument.archive(self)
        assert self.status == 'Archived'
        reset_fbot_cache(self.id)

    def sync_contacts(self, user, platform=None):
        """Appends user to correspondent contacts channel.
        `user` is either screen_name string or UserProfile instance

        """
        return
        """
        if not self.account:
            return

        contact_channel = self.account.get_contact_channel(platform or self.platform)
        contact_channel.add_username(user)
        """

    def get_review_team(self):
        if not self.is_dispatchable:
            return None

        try:
            group = self.review_team
            assert group
        except (AssertionError, Group.DoesNotExist):
            group = Group.objects.create(
                name=u"%s Review Team" % self.title,
                description="Users allowed for outbound messages review prior to dispatch",
                account=self.account
            )
            self.review_team = group
            self.save()
        return group


    # '''
    # Methods for channel classification on inbound and outbound actions
    # '''

    def apply_filter(self, item):
        '''
        Apply filtering algorithm for actionability
        '''

        # Outbound channels are always actionable
        if not self.is_inbound:
            return 'highlighted', self

        matched = self.match(item)
        if self.adaptive_learning_enabled:
            fit = self.channel_filter._predict_fit(item)
            score = (fit + int(matched)) / 2
            # If it is matched and there is no indication it should not be
            if matched and fit and fit >= 0.5:
                return 'highlighted', self
            # If it is above the inclusion threshold
            if score >= self.channel_filter.inclusion_threshold:
                return 'highlighted', self
            # If we have learned to reject it, do so.
            if score < self.channel_filter.exclusion_threshold:
                return 'discarded', self
            return 'discarded', self
        else:
            return ('highlighted', self) if matched else ('discarded', self)

    # def apply_filter(self, item):
    #     '''
    #     Apply filtering algorithm for actionability
    #     If the rule is True, we require a contradiction to reject it.
    #     '''

    #     # Outbound channels are always actionable
    #     if not self.is_inbound:
    #         return 'highlighted', self

    #     matched = self.match(item)
    #     if self.adaptive_learning_enabled:
    #         fit = self.channel_filter._predict_fit(item)
    #     else:
    #         fit = None

    #     # If we have learned to reject it, do so.
    #     print 1111111111112222, matched, fit
    #     # If we have learned to reject it, do so.
    #     if fit and fit < self.channel_filter.exclusion_threshold:
    #         return 'discarded', self

    #     # If it is matched and there is no indication it should not be
    #     if matched and fit and fit >= 0.5:
    #         return 'highlighted', self

    #     # If it is above the inclusion threshold
    #     if fit and fit >= self.channel_filter.inclusion_threshold:
    #         return 'highlighted', self

    #     # Otherwise, get rid of it
    #     return 'discarded', self

    def match(self, post):
        '''Is there an explicit rule match between this post and channel '''

        if self.parent_channel:
            return Channel.objects.get(id=self.parent_channel).match(post)

        return True

    def _handle_filter(self, item, status):
        if self.adaptive_learning_enabled:
            try:
                if status in REJECT_STATUSES:
                    return self.channel_filter.handle_reject(item)
                elif status in ACCEPT_STATUSES:
                    return self.channel_filter.handle_accept(item)
            except Exception, ex:
                LOGGER.warning("Failed to apply filter on item=%s. Error=%s. " % (item, ex))


    def make_post_vector(self, post):
        'Just a stub. Inboked by channel filter'

        # We use tags if there are any as an extension.
        return dict(lang=post.language,
                    extensions=[u"__lang_%s__" % post.language] +
                               [u"__%s__" % t.title.upper()
                                for t in post.accepted_smart_tags])


class MonitoringChannel(Channel):
    """Channel that does not perform
    classification or payload processing,
    instead it gets classified speech acts
    and used only for statistic

    """

    @property
    def type_id(self):
        return 4

    @property
    def type_name(self):
        return "Monitoring Channel"

    @property
    def base_url(self):
        return "https://tango.solariat.com"

    @property
    def platform(self):
        return "Solariat"

    def fetch_payloads_by_post(self, post, size=None):
        "Do not search in ES"
        return []

    def requires_moderation(self, post):
        return False


class CompoundChannel(Channel):
    channels = fields.ListField(fields.ReferenceField(Channel))

    @property
    def is_compound(self):
        return True

    @property
    def platform(self):
        "The platform must be the same for all primitive channels."
        if self.channels:
            try:
                ch = self.channels[0]
                if hasattr(ch, 'platform'):
                    return ch.platform
                return Channel.objects.get(id=ch).platform
            except Channel.DoesNotExist:
                LOGGER.error("Compound channel inconsistent.")
        #Platform is not set or undefined
        return ""


class ContactChannel(Channel):

    platform_id = fields.NumField(db_field='pi', default=0)  #default=twitter

    @property
    def is_contact(self):
        return True

    @property
    def platform(self):
        return get_platform_by_index(self.platform_id)

    def get_contacts(self, **kw):
        from solariat_bottle.db.user_profiles.user_profile import UserProfile
        return UserProfile.objects.find(contact_channels__in=[self.id], **kw)

    @property
    def usernames(self):
        from operator import itemgetter
        return filter(None,
            map(itemgetter('screen_name'), self.get_contacts().fields('id')))

    def add_user_profile(self, user_profile):
        user_profile.update(addToSet__contact_channels=self.id)
        if self.id not in user_profile.contact_channels:
            user_profile.contact_channels.append(self.id)
        user_profile.save()

    def remove_user_profile(self, user_profile):
        user_profile.update(pull__contact_channels=self.id)
        if self.id in user_profile.contact_channels:
            user_profile.contact_channels.remove(self.id)
        user_profile.save()

    def _get_user_profile(self, user):
        """Returns tuple: user_profile, created
        `user` is string or UserProfile instance
        """
        from solariat_bottle.db.user_profiles.social_profile import SocialProfile
        if isinstance(user, SocialProfile):
            return user, False
        elif isinstance(user, basestring):
            #get_or_create user profile by platform
            try:
                return SocialProfile.objects.get_by_platform(self.platform, user), False
            except SocialProfile.DoesNotExist:
                return SocialProfile.objects.upsert(self.platform, dict(user_name=user)), True

    def track_usernames(self, usernames):
        from solariat_bottle.db.tracking import PostFilterStream
        stream = PostFilterStream.get()
        stream.track('USER_NAME', usernames, [self])

    def add_username(self, username):
        user_profile, _ = self._get_user_profile(username)
        self.add_user_profile(user_profile)
        if self.status == 'Active':
            self.track_usernames([user_profile.screen_name])

    def del_username(self, username):
        up, created = self._get_user_profile(username)
        if created:
            return

        self.remove_user_profile(up)

        from solariat_bottle.db.tracking import PostFilterStream
        stream = PostFilterStream.get()
        stream.untrack('USER_NAME', [up.screen_name], [self])

    def on_suspend(self):
        " run this handler when channel suspended "
        super(ContactChannel, self).on_suspend()

        from solariat_bottle.db.tracking import PostFilterStream
        stream = PostFilterStream.get()
        stream.untrack_channel(self)

    def on_active(self):
        " run this handler when channel activated "
        super(ContactChannel, self).on_active()
        self.track_usernames(self.usernames)


class ServiceChannelManager(ChannelManager):

    def find_by_channels(self, channels):
        expr = {'or': [
            {'inbound__in': channels},
            {'outbound__in': channels}
        ]}
        return self.find(**expr)


class ServiceChannel(Channel):
    """Service Channel. Tracks keywords as inbound channel and usernames as outbound channel
    """
    manager = ServiceChannelManager

    inbound = fields.ObjectIdField(db_field='i')
    outbound = fields.ObjectIdField(db_field='o')
    _dispatch_channel = fields.ReferenceField(Channel, null=True, db_field='dispatch_channel')
    agents = fields.ListField(fields.ReferenceField('User'), db_field='as')
    # ignore_images = fields.BooleanField(default=False)
    history_time_period = fields.NumField(default=604800)  # default=one week
    #langs = fields.ListField(fields.StringField(), default=[LangCode.EN])

    indexes = Channel.indexes + [('inbound',), ('outbound',), ('_dispatch_channel',)]

    @property
    def dispatch_channel(self):
        return self._dispatch_channel

    @dispatch_channel.setter
    def dispatch_channel(self, value):
        self.set_dispatch_channel(value)

    def set_dispatch_channel(self, value):
        self._dispatch_channel = value

    def list_dispatch_candidates(self, user, only_not_attached=False):
        all_candidates = self.DispatchChannelClass.objects.find_by_user(user, account=self.account)[:]
        if only_not_attached:
            # return all channels that are not attached to any service channel
            non_attached_channels = [channel for channel in all_candidates
                                     if channel.get_service_channel() is None]
            return non_attached_channels
        else:
            return all_candidates

    @property
    def queue_endpoint_attached(self):
        return self.account_type in {'GSE', 'Skunkworks'} or \
            self.account.selected_app in {APP_GSE, APP_GSA, APP_NPS}

    @property
    def queue_purge_horizon(self):
        if self.history_time_period:
            return int(self.history_time_period)
        else:
            return None

    @property
    def langs(self):
        return self.inbound_channel.langs

    @property
    def requires_interim_status(self):
        return True

    @property
    def InboundChannelClass(self):
        return Channel

    @property
    def OutboundChannelClass(self):
        return Channel

    @property
    def DispatchChannelClass(self):
        return Channel

    @property
    def is_service(self):
        return True

    def archive(self):
        super(ServiceChannel, self).archive()
        self.inbound_channel.archive()
        self.outbound_channel.archive()

    def match(self, post):
        """ The service channel rule is based on actionability """
        ''' This is a hard-wired rule for actionability. It implements the
        following policy for cases where it is actionable:
        1. Directed at one of the service handles of the brand
        2. Mentions the brand, and has an actionable intention
        3. One of the actionable intention topics is a keyword...
        '''
        from solariat_bottle.db.conversation import ACTIONABLE_INTENTIONS
        direction = self.find_direction(post)

        # All direct posts are actionable
        if direction == 'direct':
            return True

        # All mentions with actionable intentions
        post_intentions = set([int(x['intention_type_id']) for x in post.speech_acts])
        if direction == 'mentioned' and post_intentions.intersection(ACTIONABLE_INTENTIONS):
            return True

        if post.head.startswith('@') and post.lang_specific_head.match_any(self.keywords):
            return True

        # All cases where actionable intentions are about the topics of interest
        for item in post.speech_acts:
            topics = item.get("intention_topics")
            attr = 'lang_keywords'
            keywords = getattr(self, attr, getattr(self.inbound_channel, attr, []))
            for keyword in keywords:
                if keyword.match_any(topics, post.language, strict=False):
                    if int(item['intention_type_id']) in ACTIONABLE_INTENTIONS:
                        return True
        return False

    def find_direction(self, post):
        from solariat_bottle.utils.post import normalize_screen_name
        clean_service_handles = map(normalize_screen_name, self.usernames)
        if set(self.addressees(post)).intersection(clean_service_handles):
            return 'direct'
        elif set(self.mentions(post)).intersection(clean_service_handles):
            return 'mentioned'
        elif self.inbound_channel.is_individual(post):
            return 'individual'
        return 'unknown'

    def update_subchannels(self):
        fields_to_sync = ('acl', 'status', 'account')
        update = {}
        inb = self.inbound_channel
        out = self.outbound_channel

        for field in fields_to_sync:
            value = getattr(self, field)
            setattr(inb, field, value)
            setattr(out, field, value)
            update['set__%s' % field] = value

        inb._title = self.title
        update['set__title'] = inb._title
        inb.update(**update)

        out._title = self.title
        update['set__title'] = out._title
        out.update(**update)

    def save_by_user(self, user, **kw):
        if self.can_edit(user):
            self.save()

    def save(self):
        self.update_subchannels()
        super(ServiceChannel, self).save()

    def reload(self):
        self.__dict__.pop('inbound_channel', None)
        self.__dict__.pop('outbound_channel', None)
        return super(ServiceChannel, self).reload()

    #proxy methods for i/o channels
    @cached_property
    def inbound_channel(self):
        try:
            channel = Channel.objects.get(
                id=self.inbound, include_safe_deletes=True)
            if not channel.is_inbound:
                channel.is_inbound = True
                channel.save()
            assert isinstance(channel, self.InboundChannelClass)
        except (IndexError, Channel.DoesNotExist, AssertionError):
            channel = self.InboundChannelClass.objects.create(
                acl            = self.acl,
                account        = self.account,
                title          = u"%s Inbound" % self.title,
                parent_channel = self.id,
                is_inbound     = True
            )
            self.inbound = channel.id
            self.save()
        return channel

    @cached_property
    def outbound_channel(self):
        try:
            channel = Channel.objects.get(
                id=self.outbound, include_safe_deletes=True)
            if channel.is_inbound:
                channel.is_inbound = False
                channel.save()
            assert isinstance(channel, self.OutboundChannelClass)
        except (IndexError, Channel.DoesNotExist, AssertionError):
            channel = self.OutboundChannelClass.objects.create(
                acl            = self.acl,
                account        = self.account,
                title          = u"%s Outbound" % self.title,
                parent_channel = self.id,
                is_inbound     = False
            )
            self.outbound = channel.id
            self.save()
        return channel

    @property
    def skipwords(self):
        return self.inbound_channel.skipwords if hasattr(self.inbound_channel, "skipwords") else []

    @property
    def watchwords(self):
        return self.inbound_channel.watchwords if hasattr(self.inbound_channel, "watchwords") else []

    def mentions(self, post):
        return self.outbound_channel.mentions(post)

    def addressees(self, post):
        return self.outbound_channel.addressees(post)

    @needs_postfilter_sync
    def add_skipword(self, keyword):
        return self.inbound_channel.add_skipword(keyword)

    @needs_postfilter_sync
    def del_skipword(self, keyword):
        return self.inbound_channel.del_skipword(keyword)

    def add_watchword(self, watchword):
        return self.inbound_channel.add_watchword(watchword)

    def del_watchword(self, watchword):
        return self.inbound_channel.del_watchword(watchword)

    def on_suspend(self):
        super(ServiceChannel, self).on_suspend()
        ic = self.inbound_channel
        oc = self.outbound_channel
        ic.on_suspend()
        oc.on_suspend()

    def on_active(self):
        super(ServiceChannel, self).on_active()
        ic = self.inbound_channel
        oc = self.outbound_channel
        ic.on_active()
        oc.on_active()

    #Conversation related methods
    def upsert_conversation(self, post, contacts=False, max_tries=20):
        '''
        Utility to fetch the conversation for a post, or create a new one.
        The given post is always inserted either way
        '''
        from solariat_bottle.db.conversation import Conversation, ConversationManager
        from solariat_bottle.db.post.facebook import FacebookPost
        conv_id = self.get_conversation_id(post)

        if isinstance(post, FacebookPost):
            parent = post.parent
            if isinstance(parent, FacebookPost):
                # Increment cached comment_count
                update_dict = dict(inc__comment_count=1)
                parent.update(**update_dict)
            try:
                conv = Conversation.objects.upsert_conversation(self, [post], conversation_id=conv_id)
            except DuplicateKeyError, e:
                # Conversation was already created!
                conv = Conversation.objects.get(conv_id)
        else:
            conversations = Conversation.objects.lookup_conversations(self, [post], contacts=contacts)

            if len(conversations) > 1:
                LOGGER.warning("Found multiple conversations for post %s, merging them." % post)
                conversations = [ConversationManager.merge_conversations(conversations)]

            if conversations == []:
                conv = Conversation.objects.create_conversation(self, [post], conversation_id=conv_id)
            else:
                conv = conversations[0]

        conv.add_posts([post])

        if conv.is_synced and conv.service_channel.account.account_type == 'Salesforce':
            access_token = conv.service_channel.account.access_token
            instance_url = conv.service_channel.account.sf_instance_url
            #
            # TODO: move this try/except block inside the task itself
            #       so that it can be called asynchronously
            from solariat_bottle.tasks.salesforce import sf_sync_conversation
            try:
                sf_sync_conversation.sync(conv, access_token, instance_url)
            except Account.AccessTokenExpired:
                conv.service_channel.account.refresh_access_token()
                sf_sync_conversation.sync(conv, access_token, instance_url)

        return conv

    def route_post(self, post):
        from solariat_bottle.db.post.base import UntrackedPost
        if isinstance(post, dict):
            post_channels = post.get('cs', [])
        elif isinstance(post, UntrackedPost):
            # For untracked posts we don't have a route and don't care about channels
            post_channels = []
        else:
            post_channels = [str(ch) for ch in post.channels]

        if str(self.inbound) in set(post_channels):
            return 'inbound'
        elif str(self.outbound) in set(post_channels):
            return 'outbound'

        LOGGER.warning(u'Post %s channels=%s is not from service channel %s(%s): inbound=%s, outbound=%s',
                       post, post_channels, self, self.title, self.inbound, self.outbound)
        # if get_var('ON_TEST'):
        #     import traceback
        #     traceback.print_stack()
        return 'unknown'

    def extract_agents(self, post):
        """Extracts agents for outbound post.
        Returns context dict for stats update.
        """
        context = {}
        if self.route_post(post) == 'outbound':
            context = {"agent": post.find_agent_id(self)}
        return context

    def post_received(self, post):
        """Adds post to conversations.
        """
        from solariat_bottle.db.post.base import UntrackedPost
        assert set(post.channels).intersection([self.inbound, self.outbound])
        assert not isinstance(post, UntrackedPost), "It should be tracked if we received it."

        parent = post.parent
        if post.is_amplifier:
            #add as amplifier to original post's conversation
            #We should have parent, though it may be not stored in db
            if isinstance(parent, UntrackedPost):
                #LOGGER.info("Post (status: %s) handler failed: original tweet (status: %s) does not exist",
                #            post.native_id, parent.native_id)
                return

            thread = self.upsert_conversation(parent)
            thread.add_amplifying_post(post)
        else:
            # Update or initialize a conversation.
            # If parent post exists, add post to its conversation,
            # else lookup the latest conversation by current post author.
            if parent and not isinstance(parent, UntrackedPost):
                thread = self.upsert_conversation(parent)
                thread.add_posts([post])
            else:
                self.upsert_conversation(post, contacts=True)

    def add_agent(self, user):
        assert isinstance(user, User)
        if user not in self.agents:
            self.agents.append(user)
        self.update(addToSet__agents=user)

    def __setattr__(self, key, value):
        # Move agents to new account with channel
        if key == 'account':
            new_account = value
            if self.account and self.account.id != new_account.id:
                for agent in self.agents:
                    agent.account.del_user(agent)
                    new_account.add_user(agent)

        super(ServiceChannel, self).__setattr__(key, value)

    def set_allowed_langs(self, langs, clear_previous=False):
        self.inbound_channel.set_allowed_langs(langs, clear_previous=clear_previous)
        self.outbound_channel.set_allowed_langs(langs, clear_previous=clear_previous)

    def get_allowed_langs(self):
        return self.inbound_channel.get_allowed_langs()

    def remove_langs(self, langs):
        self.inbound_channel.remove_langs(langs)
        self.outbound_channel.remove_langs(langs)

    def is_lang_allowed(self, lang_code):
        return lang_code in self.langs and lang_code in get_supported_languages()


CHANNEL_ID_URL_MAP = {
    Channel(title="").type_id: Channel(title="").base_url,
    MonitoringChannel(title="").type_id: MonitoringChannel(title="").base_url,
}


class ChannelAuthManager(Manager):
    '''
    Access controlled by the underlying channel access
    '''

    def _get_channel(self, obj):
        if isinstance(obj, Channel):
            return obj
        if isinstance(obj, (basestring, ObjectId)):
            return Channel.objects.get(obj)

    def _get_channels(self, user, perm):
        "Return list of channels where user has perm"
        return Channel.objects.find_by_user(user, perm=perm)[:]

    def _set_channel_key(self, user, kw, perm):
        if 'channel' in kw:
            channel = self._get_channel(kw['channel'])
            if perm == 'w':
                assert channel.can_edit(user), "The user does not have edit permission to access this channel."
            kw['channel'] = str(channel.id)
        else:
            kw['channel'] = {'$in': [str(c.id) for c in self._get_channels(user, perm)]}

    def create_by_user(self, user, **kw):
        assert kw.get('channel'), "channel parameter must be provided"
        channel = self._get_channel(kw['channel'])
        if not channel.can_edit(user):
            raise AuthError("%s has no perms on %s" % (user, channel))
        return Manager.create(self, **kw)

    def remove_by_user(self, user, *args, **kw):
        self._set_channel_key(user, kw, 'w')
        Manager.remove(self, **kw)

    def get_by_user(self, user, *args, **kw):
        if kw.get('id') and isinstance(kw['id'], (str, unicode)) and kw['id'].isdigit():
            kw['id'] = long(kw['id'])
        self._set_channel_key(user, kw, 'r')
        return Manager.get(self, **kw)

    def find_by_user(self, user, perm='r', **kw):
        if kw.get('id') and isinstance(kw['id'], (str, unicode)) and kw['id'].isdigit():
            kw['id'] = long(kw['id'])
        self._set_channel_key(user, kw, perm)
        return Manager.find(self, **kw)

    def find_one_by_user(self, user, perm='r', **kw):
        self._set_channel_key(user, kw, perm)
        return Manager.find_one(self, **kw)


class ChannelsAuthManager(ChannelAuthManager):

    def _get_channel_ids(self, user, perm, **kw):
        """Return list of channel ids for given kwargs,
        Return list of ids of channels where user has
        read permission if no any channels parameters
        inside kwargs

        """
        ensure_channels = Channel.objects.ensure_channels
        if kw.has_key('channels__in'):
            channels = ensure_channels(kw['channels__in'])
        elif kw.has_key('channels'):
            if not isinstance(kw['channels'], dict) or not '$in' in kw['channels']:
                raise AppException('channels params should be dict with $in key')
            channels = ensure_channels(kw['channels']['$in'])
        else:
            channels = Channel.objects.find_by_user(user, perm=perm)[:]

        for ch in channels:
            if perm == 'w':
                assert ch.can_edit(user), "The %s does not have permission to access %s" % (user, ch)

        return [str(x.id) for x in channels]

    def _set_channel_key(self, user, kw, perm):
        kw['channels'] = {'$in': self._get_channel_ids(user, perm, **kw)}
        kw.pop('channels_in', None)

    def create_by_user(self, user, **kw):
        """ Expect assignment to channels. Must have write perms for all. """
        assert kw.get('channels'), "channels parameter must be provided"
        channels = kw['channels']
        # Translate to objects if needed
        if not isinstance(channels[0], Channel):
            channels = Channel.objects(id__in=kw['channels'])[:]
        for channel in channels:
            if not channel.can_edit(user, admin_roles=self.doc_class.admin_roles):
                raise AuthError("%s has no 'w' perms on %s" % (user.email, channel.title))

        # Set the channels with ids
        kw['channels'] = [str(c.id) for c in channels]
        return self.create(**kw)


class ChannelAuthDocument(Document):
    """In case of channel authenticated objects, just use the group
    permissions of the referenced channel. """
    manager = ChannelAuthManager

    channel = fields.ObjectIdField(required=True, db_field='cl')

    @property
    def acl(self):
        """ Return copy of acl field from channel """
        return list(self.channel.acl)

    def to_dict(self, fields2show=None):
        res = super(ChannelAuthDocument, self).to_dict(fields2show)
        res['channel'] = str(self.channel)
        return res


class ChannelsAuthDocument(Document):
    '''
    For collections where access control is dictated
    by the access to the channels contained.
    '''

    manager = ChannelsAuthManager
    channels = fields.ListField(fields.ObjectIdField(),
                                db_field='cs')

    admin_roles = [ADMIN, STAFF]

    @property
    def channel(self):
        ''' Temporary for backward compatibility.'''
        if not self.channels:
            return None
        for channel in Channel.objects(id__in=self.channels).limit(1):
            return channel

    @property
    def channels_by_account(self):
        channels_by_acct_map = defaultdict(list)
        for channel in Channel.objects.ensure_channels(self.channels):
            channels_by_acct_map[channel.account].append(channel)
        return channels_by_acct_map

    def to_dict(self, fields2show=None):
        res = super(ChannelsAuthDocument, self).to_dict(fields2show)
        res['channels'] = [str(c_id) for c_id in self.channels]
        return res

    def has_perm(self, user):
        for channel in Channel.objects(id__in=self.channels):
            if channel.has_perm(user):
                return True
        return False

    def can_edit(self, user):
        for channel in Channel.objects(id__in=self.channels):
            if channel.can_edit(user, self.admin_roles):
                return True
        return False

    def save_by_user(self, user):
        if self.can_edit(user):
            self.save()
        else:
            raise AuthError("%s has no perms to save %s" % (user, self))

    def delete_by_user(self, user, **kw):
        "Check user has w perm then delete"
        if self.can_edit(user):
            return self.objects.remove(self.id)
        raise AuthError("%s has no perms to delete %s" % (user, self))


class SmartTagChannel(Channel):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    ANY_DIRECTION = "any"

    keywords = fields.ListField(fields.StringField(), db_field='ks')
    usernames = fields.ListField(fields.StringField(), db_field='us')
    influence_score = fields.NumField(db_field='ie', default=0)
    skip_keywords = fields.ListField(fields.StringField(), db_field='sks')
    watchwords = fields.ListField(fields.StringField(), db_field='ws')
    retweet_count_min = fields.NumField(db_field='rcm')
    contact_label = fields.ListField(fields.ObjectIdField(),db_field='cl')
    alert_is_active = fields.BooleanField(db_field='aia')
    alert_posts_limit = fields.NumField(db_field='apl')
    alert_posts_count = fields.NumField(db_field='apc', default=0)
    alert_emails = fields.ListField(fields.StringField(), db_field='ae')
    alert_last_sent_at = fields.DateTimeField(db_field='als')
    alert_last_post_at = fields.DateTimeField(db_field='alp')
    direction = fields.StringField(choices=[INBOUND, OUTBOUND, ANY_DIRECTION], db_field='drn')

    def fits_to_event(self, direction, event_is_inbound):
        """
        :param direction - smart tag direction
        :param event_is_inbound - channel's direction
        Check 4 allowed cases with smart tag direction (d) and channel's event (e):
        1) d - inbound, e - inbound
        2) d - outbound, e - outbound
        3) d - any, e - inbound
        4) d - any, e - outbound
        """
        return direction == self.INBOUND and event_is_inbound \
            or direction == self.OUTBOUND and not event_is_inbound \
            or direction == self.ANY_DIRECTION

    def increment_alert_posts_count(self):
        # start incrementing from zero if now is another date
        if self.alert_last_post_at and self.alert_last_post_at.date() < datetime.now().date():
            self.alert_posts_count = 1
        # simple increment otherwise
        else:
            self.inc(field_name='alert_posts_count', value=1)
            self.alert_last_post_at = datetime.now()
        self.save()

    @property
    def alert_can_be_sent(self):
        # do not send if date of last time alert was sent is the same
        self.reload() # the counter may be was updated by another task, so we need to reload it
        if self.alert_last_sent_at:
            if self.alert_last_sent_at.date() == datetime.now().date():
                return False
        return self.alert_is_active and self.alert_posts_count >= self.alert_posts_limit

    @property
    def platform(self):
        try:
            parent = Channel.objects.get(self.parent_channel)
            return parent.platform
        except Channel.DoesNotExist:
            LOGGER.error("Smart tag %s has no parent channel!" % self.title)
            return None

    def add_perm(self, user, group=None, to_save=True):
        super(SmartTagChannel, self).add_perm(user, group=group, to_save=to_save)
        for label in ContactLabel.objects.find(id__in=self.contact_label):
            label.add_perm(user, group=group, to_save=to_save)

    def is_assigned(self, post):
        ''' True if the post is assigned to the channel, otherwise False '''
        from solariat_bottle.db.speech_act import SpeechActMap
        key = str(self.id)
        return key in post.tag_assignments and post.tag_assignments[key] in SpeechActMap.ASSIGNED

    def is_mutable(self, post):
        ''' True if assignment is mutable'''
        from solariat_bottle.db.speech_act import SpeechActMap
        key = str(self.id)
        return key not in post.tag_assignments or post.tag_assignments[key] in SpeechActMap.PREDICTED

    def update_stats(self, post, original_channels, status, from_status_parent, context):
        """
        Do any context updates as necessary, then update post assignment for this
        status and delegate updating stats for other models (trends, channel stats etc.)
        """
        from_status = post.get_assignment(self, True)
        from solariat_bottle.utils.post import update_stats
        # Set context information. Required for agent related stats on replies
        update_context = post._get_last_update_context(self)
        if update_context and not update_context['outbound_stats']:
            # see reset_outbound so SpeechActMap.reset() works
            context['reset_outbound'] = True
        context.update(update_context)

        if self in original_channels:
            action = {"highlighted": "add",
                      "discarded" : "remove",
                      "assigned": "remove",
                      "starred": "add",
                      "rejected": "remove"}[status]
        else:
            action = "update"

        should_increment = post.should_increment_stats(action, from_status, from_status_parent, status)
        should_decrement = post.should_decrement_stats(action, from_status, from_status_parent, status)

        old_status = post.tag_assignments.get(str(self.id))
        context["old_status"] = old_status

        if action != "update":
            # We are using this to get response tags, need to have state saved.
            post.set_assignment(self, status, context=update_context)
            post.save()
        update_stats(post, self, status=post.get_assignment(self),
                     action=action, from_status=from_status_parent,
                     should_increment=should_increment, should_decrement=should_decrement, **context)

    def apply_filter(self, item):
        '''
        Over-ride channel filtering algorithm to suite tags. The main difference
        is that users have more control over the matching rule so we must give
        it greater considertaion. We treat it as a hard constraint.
        '''
        if 'faq' in self.title.lower():
            # import ipdb; ipdb.set_trace()
            pass

        # If the rule is false, discard it
        if not self.match(item):
            #print "EXCLUDED", self.title
            return 'discarded', self

        # If adaptive learning enabled we use the channel filter. It will dominate
        # if it can make a decision
        if self.adaptive_learning_enabled:
            fit = self.channel_filter._predict_fit(item)
            #print "FIT", fit, self.title
            if fit < 0.5: #self.channel_filter.exclusion_threshold:
                return 'discarded', self

        return 'highlighted', self

    @property
    def is_smart_tag(self):
        return True

    def flatten_list(self,list):
        return set([val for subl in list for val in subl])

    @property
    def normalized_usernames(self):
        from solariat_bottle.utils.post import normalize_screen_name
        contact_labels = [ExplcitTwitterContactLabel.objects.get(id = x) for x in self.contact_label]
        users_lists = [contact_label.users for contact_label in contact_labels if contact_label.status == 'Active']
        return map(normalize_screen_name, self.flatten_list(users_lists))

    @property
    def intentions(self):
        from solariat_nlp.sa_labels import SATYPE_TITLE_TO_NAME_MAP

        return filter(None, map(SATYPE_TITLE_TO_NAME_MAP.get, self.intention_types))

    def make_post_vector(self, post):
        'Call the parent'
        post_vector = Channel.make_post_vector(self, post)
        post_vector.update(Channel.objects.get(id=self.parent_channel).make_post_vector(post))
        post_vector['keywords'] = post_vector.get('keywords', [])
        post_vector['keywords'] = post_vector['keywords'] + self.keywords
        post_vector['skip_keywords'] = self.skip_keywords
        post_vector['watchwords'] = post_vector.get('watchwords', [])
        post_vector['watchwords'] = post_vector['watchwords'] + self.watchwords

        # Add Klout
        post_vector['extensions'] = []
        up = post.get_user_profile()
        if up and self.influence_score > 0 and self.influence_score <= up.klout_score:
            post_vector['extensions'] = post_vector['extensions'] + ['__KLOUT__']

        return post_vector

    def match(self, post):

        """Test if post fits the smart tag by configurable parameters"""
        if self.status != 'Active':
            return False

        up = post.get_user_profile()
        user_profile_constraint = not up or all([
            self.influence_score == 0 or self.influence_score <= up.klout_score,
            not self.contact_label or up.normalized_screen_name in self.normalized_usernames
        ])
        content = " %s " % " ".join(WORD_SPLIT_RE.split(post.plaintext_content.lower()))
        post_intention_types = set([sa['intention_type'] for sa in post.speech_acts])

        def _any_keyword_in(content, words):
            for word in words:
                if content.find(word) != -1:
                    return True
            return False

        keywords = [kwd.lower() for kwd in self.keywords]
        skip_list = [kwd.lower() for kwd in self.skip_keywords]
        keyword_constraint = not keywords or _any_keyword_in(content, keywords)
        skip_list_constraint = not skip_list or not _any_keyword_in(content, skip_list)
        intentions_constraint = not self.intention_types or set(self.intention_types) & post_intention_types
        retweet_count_constraint = True  # TODO: for new post retweet_count will always be 0

        results = [user_profile_constraint,
                   keyword_constraint,
                   skip_list_constraint,
                   intentions_constraint,
                   retweet_count_constraint]
        return all(results)

    @property
    def parent(self):
        try:
            return Channel.objects.get(self.parent_channel)
        except Channel.DoesNotExist:
            raise AppException("Smart tag %s has no parent channel with id=%s" % (self, self.parent_channel))

    def get_outbound_channel(self, user):
        # Each specific channel should know how to get it's own dispatch channel
        # depending on specific platform
        return self.parent.get_outbound_channel(user)


class ClickChannel(Channel):

    @property
    def platform(self):
        return "Click"

class CallChannel(Channel):

    @property
    def platform(self):
        return "Call"

# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
