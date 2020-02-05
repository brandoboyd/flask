"""
Contains any facebook specific functionality related to channels.
"""
import re
import json
from datetime import timedelta, datetime
from solariat_bottle.db.language import AllLanguageChannelMixin

from solariat_bottle.settings import AppException, LOGGER

from solariat.db              import fields
from solariat_bottle.db.group        import Group
from solariat_bottle.db.channel.base import (
    Channel, CHANNEL_ID_URL_MAP, ServiceChannel
)

from solariat_bottle.utils import facebook_driver
from solariat_bottle.utils.id_encoder import pack_components
from solariat_bottle.utils.facebook_extra import (
    subscribe_realtime_updates, unsubscribe_realtime_updates,
    update_page_admins)

from solariat_bottle.tasks.facebook import fb_put_comment, fb_answer_pm, \
    fb_comment_by_page, get_facebook_api

from solariat.utils.timeslot import now, utc
from solariat_bottle.db.facebook_tracking import FacebookTracking, PAGE, EVENT


class FacebookConfigurationException(AppException):
    pass


class FacebookUserMixin(object):
    _cached_facebook_me = fields.StringField(db_field='fb_me')
    _cached_facebook_me_ts = fields.DateTimeField(db_field='fb_me_ts')

    # Cache channel description on GSA side and update once per day
    _cached_channel_description = fields.StringField()
    _cached_last_description_update = fields.DateTimeField(default=datetime.now())

    def _set_channel_description(self, channel_info):
        self._cached_channel_description = json.dumps(channel_info)
        self._cached_last_description_update = datetime.now()
        self.save()

    def _get_channel_description(self):
        if self._cached_channel_description:
            if self._cached_last_description_update + timedelta(days=1) < datetime.now():
                # After 1 day just consider this to be too old and basically invalid
                self._cached_channel_description = ""
                self.save()
                return None

            # We're still in 'safe' 1 day range, return cached value
            try:
                return json.loads(self._cached_channel_description)
            except Exception:
                return None
        return None

    channel_description = property(_get_channel_description, _set_channel_description)

    def facebook_me(self, force=False):
        default_timeout = 60 * 60  # 1 hour

        def _graph_me():
            graph = get_facebook_api(self)
            return graph.request('/me')

        def _invalidate(timeout=default_timeout,
                        value_attr='_cached_facebook_me',
                        ts_attr='_cached_facebook_me_ts',
                        value_getter=_graph_me):
            date_now = now()

            if not getattr(self, ts_attr) or (date_now - utc(getattr(self, ts_attr))).total_seconds() > timeout:
                self.update(**{ts_attr: date_now,
                               value_attr: json.dumps(value_getter())})

            return json.loads(getattr(self, value_attr))

        timeout = 0 if force is True else default_timeout
        return _invalidate(timeout)

    def set_facebook_me(self, fb_user):
        self.update(_cached_facebook_me_ts=now(),
                    _cached_facebook_me=json.dumps(fb_user))


class EnterpriseFacebookChannel(FacebookUserMixin, Channel):
    "channel with facebook specific information for daemon"

    # user access_token for EnterpriseFacebookChannel
    facebook_access_token = fields.StringField(db_field = 'fat')
    facebook_handle_id    = fields.StringField(db_field = 'fid')
    facebook_screen_name  = fields.StringField(db_field = 'fsn')
    user_access_token     = fields.StringField(db_field = 'uat')
    # Keep track of all the page accounts this user has access to
    facebook_account_ids  = fields.ListField(fields.StringField())
    # monitored facebook pages
    facebook_page_ids     = fields.ListField(fields.StringField())
    tracked_fb_group_ids = fields.ListField(fields.StringField())
    tracked_fb_event_ids = fields.ListField(fields.StringField())

    review_outbound       = fields.BooleanField(default=False, db_field='ro')
    review_team           = fields.ReferenceField(Group, db_field='rg')

    is_inbound            = fields.BooleanField(db_field='in', default=False)

    @property
    def is_authenticated(self):
        return self.facebook_access_token

    @property
    def type_id(self):
        return 2

    @property
    def type_name(self):
        return "Enterprise Facebook"

    @property
    def base_url(self):
        return "https://facebook.com"

    @property
    def platform(self):
        return "Facebook"

    @property
    def is_dispatchable(self):
        return True

    @property
    def is_dispatch_channel(self):
        return True

    def get_attached_service_channels(self):
        candidates = FacebookServiceChannel.objects(account=self.account, _dispatch_channel=self)[:]
        return candidates

    def get_service_channel(self, lookup_by_page_ids=True):
        candidates = self.get_attached_service_channels()
        if not candidates and lookup_by_page_ids:
            # Fallback to lookup by token/page ids
            if self.facebook_access_token:
                candidates = FacebookServiceChannel.objects.find(
                    account=self.account,
                    facebook_access_token=self.facebook_access_token)[:]
            if not candidates:
                candidates = FacebookServiceChannel.objects.find(
                    account=self.account,
                    facebook_page_ids__in=self.facebook_page_ids)[:]
            if not candidates:
                return None

            if len(candidates) == 1:
                return candidates[0]
            else:
                LOGGER.error(
                    "We have multiple candidates for service channel matching for enterprise channel %s" %
                    self)
                return None

        if len(candidates) > 1:
            LOGGER.warn("We have multiple candidates for service channel matching "
                        "for enterprise channel %s" % self)
        if candidates:
            return candidates[0]

    def send_message(self, dry_run, creative, post, user, direct_message=False):
        """ TODO: for now we always response publicly, will need to extend once we want
            to integrate private messages based on response type.
        """
        if post.can_comment:
            post_id = post.native_data['facebook_post_id']
        else:
            if post.parent:
                # This means we also have picked up the parent for the post. We just need
                # to issue a reply on that comment instead
                post_id = post.parent.native_data['facebook_post_id']
            else:
                G = facebook_driver.GraphAPI(self.facebook_access_token, channel=self)
                comment = G.get_object(post.native_data['facebook_post_id'], fields='object.fields(id)')
                post_id = comment['parent']['id']
        LOGGER.info("Sending '%s' to %s using %s" % (creative, post_id, self))

        if post.is_pm:
            fb_answer_pm.ignore(post, creative)
        else:
            fb_comment_by_page.ignore(post,  post_id, creative)

    def get_outbound_channel(self, user):
        return self


CHANNEL_ID_URL_MAP[EnterpriseFacebookChannel(title="").type_id] = EnterpriseFacebookChannel(title="").base_url


class FacebookChannel(Channel):
    conversation_id_re = re.compile(
        r"(t_mid|t_id)\.([0-9]+)(:[a-f0-9]+)?",
        re.IGNORECASE)

    def get_conversation_id(self, post):
        """
        Compute a unique 50 bits id for a given inbound post.
        """
        try:
            root_post_id = post.get_conversation_root_id()
            # Extract unique id from post to use as root post id.
            match = self.conversation_id_re.search(root_post_id)
            if match:
                conv_id = long(match.group(2))
            elif '_' in root_post_id:
                # Public post, format <page_id>_<unique_post_id>
                conv_id = long(root_post_id.split('_')[1])
            else:
                LOGGER.warning(
                    "Could not infer conversation id from root post {}. Post: {} Channel: {}"
                    "Defaulting to base one.".format(root_post_id, post, self))
                return super(FacebookChannel, self).get_conversation_id(post)
        except:
            LOGGER.exception("Exception while getting conv_id from post: {}".format(post))
            raise

        return conv_id

    @property
    def platform(self):
        return 'Facebook'


class InboundFacebookChannel(FacebookChannel, AllLanguageChannelMixin):
    pass


class OutboundFacebookChannel(FacebookChannel, AllLanguageChannelMixin):
    pass


PULL_MODE_AUTO = 0
PULL_MODE_RARE = 1
PULL_MODE_NORMAL = 2
PULL_MODE_FAST = 3


class FacebookServiceChannel(FacebookUserMixin, FacebookChannel, ServiceChannel):
    # -- pages --
    # monitored facebook pages
    facebook_page_ids = fields.ListField(fields.StringField())  #name should be same as in EnterpriseFacebookChannel
    facebook_pages = fields.ListField(fields.DictField())  # current pages data
    all_facebook_pages = fields.ListField(fields.DictField())  # all accessible pages data
    page_admins = fields.DictField()  # {page_id: [list of facebook users json]...}
    tracked_fb_message_threads_ids = fields.ListField(fields.StringField())
    # -- groups --
    tracked_fb_group_ids = fields.ListField(fields.StringField())  #name should be same as in EnterpriseFacebookChannel
    tracked_fb_groups = fields.ListField(fields.DictField())
    all_fb_groups = fields.ListField(fields.DictField())

    # -- events --
    tracked_fb_event_ids = fields.ListField(fields.StringField())  #name should be same as in EnterpriseFacebookChannel
    tracked_fb_events = fields.ListField(fields.DictField())
    all_fb_events = fields.ListField(fields.DictField())

    #-- user --
    facebook_handle_id = fields.StringField()
    facebook_access_token = fields.StringField()

    pull_activity_md = fields.DictField()   # there stored info about last data pull operations time
    fb_pull_mode = fields.NumField(default=PULL_MODE_RARE)

    last_post_received = fields.StringField()
    last_pull_success = fields.StringField()

    @property
    def InboundChannelClass(self):
        return InboundFacebookChannel

    @property
    def OutboundChannelClass(self):
        return OutboundFacebookChannel

    @property
    def DispatchChannelClass(self):
        return EnterpriseFacebookChannel

    def find_direction(self, post):
        # For now just assume all posts are actionable if posted in one
        # of the users pages.
        return 'direct'

    def set_dispatch_channel(self, value):
        super(FacebookServiceChannel, self).set_dispatch_channel(value)
        self.sync_with_account_channel(value)

    def sync_with_account_channel(self, efc):
        self.update(_cached_channel_description=None)
        if efc.facebook_access_token:
            self.update(
                facebook_handle_id=efc.facebook_handle_id,
                facebook_access_token=efc.facebook_access_token,
            )
            self.set_facebook_me(efc.facebook_me())

        else:
            self.update(
                facebook_page_ids=[],
                facebook_pages=[],
                all_facebook_pages=[],

                tracked_fb_event_ids=[],
                tracked_fb_events=[],
                all_fb_events=[]
            )

    def get_access_token(self, user):
        """
        Try to get the access token for this channel.
        """
        # if self.facebook_handle_id:
        #     return self.facebook_access_token
        # else:
        try:
            efc = self.get_outbound_channel(user)
            if efc:
                if efc.facebook_access_token:
                    self.sync_with_account_channel(efc)  # TODO: do we need sync here?
                    return efc.facebook_access_token
                error_msg = "Channel %s has no access token. Did you login to facebook from configuration page?" % (efc.title)
                raise FacebookConfigurationException(error_msg)
            else:
                error_msg = 'Please create and configure a channel of type "Facebook : Account" first.'
                raise FacebookConfigurationException(error_msg)
        except Exception as ex:
            LOGGER.error(ex)
            raise FacebookConfigurationException(ex.message)

    def get_outbound_channel(self, user):
        '''
        Get the outbound channel based on user access, channel configuration, and as
        a last resort, channel configurations
        '''
        # The configured channel is only necessary, or correct, if this is no service
        # channel, or if there is a service channel with multiple candidates
        if self.dispatch_channel:
            return self.dispatch_channel

        configured_user_channel = user.get_outbound_channel(self.platform)
        configured_account_channel = self.account.get_outbound_channel(self.platform)
        candidates = EnterpriseFacebookChannel.objects.find_by_user(user,
                                                                    account=self.account,
                                                                    status='Active')[:]

        # If there are no candidates for the service channel, then do not return anything.
        if not candidates:
            return None
        else:
            if len(candidates) == 1:
                return candidates[0]
            if configured_user_channel in candidates:
                return configured_user_channel
            if configured_account_channel in candidates:
                return configured_account_channel
            error_msg = "There are multiple Facebook : Account channels on this account: "
            error_msg += "Channels: (%s), Account: %s. You need to set one in user profile or account settings." % (
                [c.title for c in candidates], self.account.name)
            raise FacebookConfigurationException(error_msg)

    def track_fb_group(self, group, user):
        assert isinstance(group, dict) and {'id', 'name'} <= set(group), 'Wrong group object'
        self.__add_to_tracking(user, group, 'tracked_fb_group_ids', 'tracked_fb_groups')

    def untrack_fb_group(self, group, user):
        assert isinstance(group, dict) and {'id', 'name'} <= set(group), 'Wrong group object'
        self.__remove_from_tracking(user, group, 'tracked_fb_group_ids', 'tracked_fb_groups')

    def track_fb_event(self, event, user):
        assert isinstance(event, dict) and {'id', 'name'} <= set(event), 'Wrong event object'
        self._handle_tracking("add", [], [event['id']])
        self.__add_to_tracking(user, event, 'tracked_fb_event_ids', 'tracked_fb_events')

    def untrack_fb_event(self, event, user):
        assert isinstance(event, dict) and {'id', 'name'} <= set(event), 'Wrong event object'
        self._handle_tracking("remove", [], [event['id']])
        self.__remove_from_tracking(user, event, 'tracked_fb_event_ids', 'tracked_fb_events')

    def add_facebook_page(self, page, user):
        assert isinstance(page, dict) and {'id', 'name'} <= set(page), 'Wrong page object'
        self._handle_tracking("add", [page['id']])
        self.__add_to_tracking(user, page, 'facebook_page_ids', 'facebook_pages')
        update_page_admins(self, page)

    def remove_facebook_page(self, page, user):
        assert isinstance(page, dict) and {'id', 'name'} <= set(page), 'Wrong page object'
        self._handle_tracking("remove", [page['id']])
        self.__remove_from_tracking(user, page, 'facebook_page_ids', 'facebook_pages')

    def post_received(self, post):
        """
        Adds post to conversations.
        """
        from solariat_bottle.db.post.base import UntrackedPost
        assert set(post.channels).intersection([self.inbound, self.outbound])
        assert not isinstance(post, UntrackedPost), "It should be tracked if we received it."

        conv = self.upsert_conversation(post, contacts=False)
        if post.is_pm:
            self.last_post_received = datetime.utcnow().strftime("%s")
            self.save()

    def _handle_tracking(self, action, pages=None, events=None):
        LOGGER.info(u"Invoked {}[{}]._handle_tracking action={} pages={} events={}".format(
            self.__class__.__name__, self.id, action, pages, events))

        if pages == 'all':
            pages = self.facebook_page_ids
        if events == 'all':
            events = self.tracked_fb_event_ids
        if pages:
            FacebookTracking.objects.handle_channel_event(action, self, pages, PAGE)
        if events:
            FacebookTracking.objects.handle_channel_event(action, self, events, EVENT)

    def on_active(self):
        self.status = 'Active'
        self.update(set__status='Active')
        self._handle_tracking("add", "all", "all")
        subscribe_realtime_updates(self.facebook_pages)
        self.inbound_channel.on_active()
        self.outbound_channel.on_active()

    def on_suspend(self):
        self.status = 'Suspended'
        self.update(set__status='Suspended')
        self._handle_tracking("remove", "all", "all")
        unsubscribe_realtime_updates(self.facebook_pages)
        self.inbound_channel.on_suspend()
        self.outbound_channel.on_suspend()

    def archive(self):
        self._handle_tracking("remove", "all", "all")
        return super(FacebookServiceChannel, self).archive()

    def list_outbound_channels(self, user):
        return EnterpriseFacebookChannel.objects.find_by_user(user, account=self.account)

    def __invalidate_channel_descriptions(self, user):
        self._cached_channel_description = None     # Make sure we no longer consider same cached channel
        candidates = EnterpriseFacebookChannel.objects.find_by_user(user,
                                                                    account=self.account,
                                                                    status='Active')[:]
        for candidate in candidates:
            candidate._cached_channel_description = None
            candidate.save()

    def __add_to_tracking(self, user, item, id_fields, tracked_field):

        if str(item['id']) in getattr(self, id_fields):
            return

        getattr(self, tracked_field).append(item)
        getattr(self, id_fields).append(item['id'])
        self.__invalidate_channel_descriptions(user)
        self.save()

        if self.status == 'Active' and 'access_token' in item and item.get('type') != "event":
            subscribe_realtime_updates([item])

        efc = self.get_outbound_channel(user)
        if efc:
            getattr(efc, id_fields).append(str(item['id']))
            efc.save()

    def __remove_from_tracking(self, user, item, ids_field, tracked_field):

        tracked = getattr(self, tracked_field)
        setattr(self, tracked_field, filter(lambda p: str(p['id']) != str(item['id']), list(tracked)))

        try:
            getattr(self, ids_field).remove(str(item['id']))
        except ValueError:
            pass
        self.__invalidate_channel_descriptions(user)
        self.save()

        # Now also add page to dispatch so facebook bot will have access
        efc = self.get_outbound_channel(user)
        if efc:
            try:
                getattr(efc, ids_field).remove(str(item['id']))
            except ValueError:
                pass
            efc.save()

        if self.status == 'Active' and 'access_token' in item and item.get('type') != "event":
            unsubscribe_realtime_updates([item])

    def get_outbound_ids(self):
        outbound_ids = set()
        for page_id, users in (self.page_admins or {}).viewitems():
            outbound_ids.add(page_id)
            for user in users:
                if user.get('role') == 'Admin' and user.get('id'):
                    outbound_ids.add(user['id'])

        if self.facebook_handle_id:
            outbound_ids.add(str(self.facebook_handle_id))

        for page_data in list(self.all_facebook_pages):
            if page_data.get('id'):
                outbound_ids.add(page_data['id'])

        return outbound_ids
