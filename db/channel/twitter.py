"""
Contains any twitter specific functionality related to channels.
"""
from datetime import datetime
from collections import defaultdict
from solariat.utils.lang.helper import LingualToken, is_token_lang_adopted
from solariat_bottle.db.language import MultilanguageChannelMixin

from solariat_bottle.settings import get_var, LOGGER, AppException

from solariat.db              import fields
from solariat_bottle.db.auth         import Document
from solariat_bottle.db.group        import Group
from solariat.db.abstract     import Index, SonDocument
from solariat_bottle.db.channel.base import (
    needs_postfilter_sync,
    Channel, ChannelManager, ServiceChannel,
    create_outbound_post, CHANNEL_ID_URL_MAP
)


class TwitterConfigurationException(AppException):
    pass


def get_sync_usernames_list(username_list):
    """
    For a list of twitter usernames, make sure that we have both pairs of
    @handle / handle even if for some reason user added only one or another.
    """
    full_usernames = username_list[:]
    for handle in username_list:
        if handle.startswith('@'):
            if handle[1:] not in full_usernames:
                full_usernames.append(handle[1:])
        elif '@' + handle not in full_usernames:
            full_usernames.append('@' + handle)
    return full_usernames


def get_twitter_outbound_channel(user, channel):
    '''
    Get the outbound channel based on user access, channel configuration, and as
    a last resort, channel configurations
    '''
    from solariat_bottle.utils.post import get_service_channel

    # If for any reason we try to get the dispatch channel for
    # a dispatch channel, and user has edit perms, we can just use same channel.
    if isinstance(channel, EnterpriseTwitterChannel) and channel.can_edit(user):
        return channel
    # The configured channel is only necessary, or correct, if this is no service
    # channel, or if there is a service channel with multiple candidates
    configured_channel = user.get_outbound_channel(channel.platform)

    sc = get_service_channel(channel)
    if sc:
        if sc.dispatch_channel:
            return sc.dispatch_channel

        candidates = EnterpriseTwitterChannel.objects.find_by_user(user, account=channel.account, status='Active')[:]
        # Case insensitive filter for match with user names
        usernames_lowercase = [n.lower() if not n.startswith('@') else n[1:] for n in sc.usernames]
        candidates = [c for c in candidates if c.is_authenticated and (c.twitter_handle.lower() in usernames_lowercase or
                                                                       not usernames_lowercase)]
        # If there are no candidates for the service channel, then do not return anything.
        if candidates == []:
            return None

        # If exactly 1, return it
        if len(candidates) == 1:
            return candidates[0]

        # If more than one, we bring in the configured channel if we have one to disambiguate
        if configured_channel and configured_channel in candidates:
            return configured_channel

        # Otherwise, return nothing. We have no solid way to disambiguate
        raise TwitterConfigurationException(
            "Sorry! There is a configuration error. "
            "You have 2 or more reply channels configured."
            "Please set up a default reply channel in Settings on the Default Channels page."
        )

    # We only have the configured channel, no candidates based on sc, it could be None, which is OK
    return configured_channel


class EnterpriseTwitterChannelManager(ChannelManager):
    """
    Specific manager for a ETC. Makes sure we track the twitter handle
    on channel creation.
    """
    def create_by_user(self, user, **kw):
        from solariat_bottle.db.tracking import PostFilterStream
        channel = super(EnterpriseTwitterChannelManager, self).create_by_user(user, **kw)
        twitter_handle = kw.get('twitter_handle')
        if twitter_handle:
            stream = PostFilterStream.get()
            stream.track('USER_NAME', [twitter_handle], [channel])

        return channel


class TwitterChannel(Channel):
    "Channel with twitter specific information for crawler"

    # monitored twitter users.
    # THIS SHOULD BE DEPRECATED. WILL NOT SCALE
    twitter_usernames = fields.ListField(fields.StringField())

    # twitter credentials for replying
    access_token_key = fields.EncryptedField(
        fields.StringField(),
        allow_db_plain_text=True)
    access_token_secret = fields.EncryptedField(
        fields.StringField(),
        allow_db_plain_text=True)

    review_outbound = fields.BooleanField(default=False, db_field='ro')
    review_team = fields.ReferenceField(Group, db_field='rg')

    @property
    def is_authenticated(self):
        ''' Over-ride in derived classes. '''
        return self.access_token_key and self.access_token_secret

    @property
    def type_id(self):
        return 8

    @property
    def type_name(self):
        return "Twitter"

    @property
    def platform(self):
        return "Twitter"

    @property
    def is_dispatchable(self):
        return True

    def get_outbound_channel(self, user):
        return get_twitter_outbound_channel(user, self)

    def has_direct_messages(self, conversation, contact = None):
        """
        If any post from this conversation that is not replied is a direct message,
        that this conversation still has open direct messages, and any reply will be
        as a direct message.

        :param conversation: the conversation we are checking for direct messages
        :param contact: if provided, will only check for open direct messages from this contact.
        """
        posts = conversation.query_posts()
        for post in posts:
            if (post.get_post_status(self) == 'actual' and post.message_type == 'direct'
                                and (contact is None or post.user_profile.user_name == contact)):
                return True
        return False

    def send_message(self, dry_run, creative, post, user, direct_message=None):
        # self.sync_contacts(post.user_profile)
        from solariat_bottle.tasks.twitter import tw_normal_reply, tw_direct_reply

        is_dm = False   # Assume this is not a DM
        if direct_message is not None:
            # If we specifically passed the fact that we want a direct message, use DM
            # Otherwise decide based on post type
            is_dm = direct_message
        else:
            if post.message_type == 'direct':
                is_dm = True
        if not is_dm:
            status = "@%s %s" % (post.user_profile.user_name, creative)
        else:
            status = creative

        if len(status) > 140:
            msg = (
                'Sorry, you have exceeded your 140 character limit by %d characters. '
                'Please correct your reply and try again.'
            ) % (len(status) - 140)
            raise AppException(msg)

        status_id = post.native_id

        # Update the engagement history
        post.user_profile.update_history(self)

        LOGGER.debug("For current message, direct message flag is %s", is_dm)
        if not dry_run and not get_var('ON_TEST'):
            if is_dm:
                tw_direct_reply.ignore(
                    self,
                    status=status,
                    screen_name=post.user_profile.user_name
                )
            else:
                tw_normal_reply.ignore(
                    self,
                    status    = status,
                    status_id = status_id,
                    post      = post
                )
        else:
            create_outbound_post(user, self, creative, post)

        LOGGER.debug(
            "Sent '%s' to %s using %s", creative, post.user_profile.user_name, self.title
        )

    def share_post(self, post, user, dry_run=False):
        # self.sync_contacts(post.user_profile)

        from solariat_bottle.tasks.twitter import tw_share_post

        post_content = post.plaintext_content
        status_id = post.native_id

        if dry_run is False and not get_var('ON_TEST') and get_var('APP_MODE') == 'prod':
            tw_share_post.ignore(self,
                                 status_id=status_id,
                                 screen_name=post.user_profile.user_name)
        else:
            create_outbound_post(user, self, "RT: %s" % post_content, post)

        LOGGER.debug("Retweet '%s' using %s", post_content, self)

    def has_private_access(self, sender_handle, recipient_handle):
        return self._dm_access_check(recipient_handle)

    def _dm_access_check(self, twitter_handle):
        """
        Check if a channels should actually have permissions to a direct message.

        :param sender_handle: the twitter handle for the sender of a message.
        :param recipient_handle: the twitter handle for the recipient of a message.
        """

        if not self.account:
            LOGGER.info("Channel %s rejected because no account.", self.title)
            return False

        outbounds = self.account.get_outbounds_for_handle(twitter_handle)
        if not outbounds:
            LOGGER.info("Channel %s rejected because no outbound channel is set for the handle %s." % (self.title,
                                                                                                       twitter_handle))
            return False

        # Go through all the outbounds and see if there is any valid for this inbound channel
        for outbound_channel in outbounds:
            LOGGER.info("Validating %s against outbound %s.", self.title, outbound_channel.title)
            checks_passed = True

            if not outbound_channel:
                # There is no outbound channel configured for twitter.
                # At this point no channel from the account should have access.
                LOGGER.info("Channel %s rejected because no outbound channel is set.", self.title)
                checks_passed = False

            if outbound_channel.status != 'Active' or outbound_channel.twitter_handle != twitter_handle:
                # Another reason why a channel might not have acces is if twitter
                # outbound channel is no longer active or if it's active for another
                # handle.
                LOGGER.info(
                    "Expected active outbound: %s with handle %s but got: (%s, %s)",
                    outbound_channel.title,
                    twitter_handle,
                    outbound_channel.status,
                    outbound_channel.twitter_handle
                )
                checks_passed = False

            if not set(self.acl).intersection(set(outbound_channel.acl)):
                LOGGER.info("Channel %s rejected due to acl conflicts.", self.title)
                LOGGER.info(
                    "ACL for %s: %s, while ACL for %s: %s",
                    self.title,             set(self.acl),
                    outbound_channel.title, set(outbound_channel.acl)
                )
                checks_passed = False
            if checks_passed: return True
        return False

    def get_service_channel(self):
        return None

    def list_outbound_channels(self, user):
        return EnterpriseTwitterChannel.objects.find_by_user(user,
                                                             account=self.account,
                                                             twitter_handle__in=self.usernames)

    def patch_user(self, user):
        from solariat_bottle.db.user_profiles.social_profile import TwitterProfile
        # TODO: [gsejop] Why do we need to create dummy Agent/UserProfiles
        # when User instance has no user_profile?
        up = TwitterProfile()
        up.save()
        AgentProfile = user.account.get_agent_profile_class()
        ap = AgentProfile(account_id=self.account.id)
        ap.save()
        #ap.add_profile(up)
        user.user_profile = up
        user.save()


class EnterpriseTwitterChannel(TwitterChannel):
    "Channel with twitter specific information for tracking"
    manager = EnterpriseTwitterChannelManager

    twitter_handle = fields.StringField(default='')
    twitter_handle_data = fields.DictField()
    status_update = fields.DateTimeField(db_field='st',
                                         default=datetime.utcnow())

    followers_count = fields.NumField(default=0, db_field='fc')
    friends_count = fields.NumField(default=0, db_field='frc')

    is_inbound = fields.BooleanField(db_field='in', default=False)

    def get_twitter_profile(self):
        if not self.is_authenticated:
            return None

        def fetch_api_me():
            from solariat_bottle.utils.tweet import TwitterApiWrapper, JSONParser

            api = TwitterApiWrapper.init_with_channel(self, parser=JSONParser())
            return api.me()

        token_hash = hash("%s%s" % (
            self.access_token_key,
            self.access_token_secret)) & (1 << 8)
        data = dict(self.twitter_handle_data or {})
        if data and 'hash' in data and 'profile' in data and data['hash'] == token_hash:
            res = data['profile']
        else:
            api_me_json = fetch_api_me()
            data = {'hash': token_hash, 'profile': api_me_json}
            self.update(twitter_handle_data=data,
                        twitter_handle=api_me_json['screen_name'])
            res = api_me_json
        return res

    @property
    def twitter_handle_id(self):
        if get_var('ON_TEST') and not self.twitter_handle_data:
            return self.twitter_handle

        profile_data = self.get_twitter_profile()
        if profile_data:
            return profile_data['id_str']

    @property
    def type_name(self):
        return "Enterprise Twitter"

    @property
    def type_id(self):
        return 1

    @property
    def is_dispatch_channel(self):
        return True

    @property
    def initial_status(self):
        return 'Active'

    def on_suspend(self):
        self.update(status='Suspended',
                    status_update=datetime.utcnow().replace(microsecond=0))

    def tracked_entities(self):
        if self.status not in {'Active', 'Interim'}:
            return []
        return [('USER_NAME', [self.twitter_handle], self, ['en'])]

    def pre_save(self):
        "Track/untrack twitter_handle"
        from solariat_bottle.db.tracking import PostFilterStream

        stream = PostFilterStream.get()
        stream.untrack_channel(self)
        if self.twitter_handle and self.status != 'Archived':
            stream.track('USER_NAME', [self.twitter_handle], [self])

    def save(self, pre_save=True):
        if pre_save:
            self.pre_save()
        super(EnterpriseTwitterChannel, self).save()

    def save_by_user(self, user, **kw):
        if self.can_edit(user):
            self.pre_save()
        super(EnterpriseTwitterChannel, self).save_by_user(user, **kw)

    def follow_user(self, user_profile, silent_ex=False):
        """
        For the given user profile, first do the actual twitter follow
        then also update the user profile object locally so we can quickly
        get the required status.

        If :param silent_ex: is set to true, any exception from twitter call
        is ignored. (e.g. autofollow on DM creation).
        """
        from solariat_bottle.tasks.twitter import tw_follow
        tw_follow(channel=self,
                  user_profile=user_profile,
                  silent_ex=silent_ex)

        self.update(inc__friends_count=1)

    def unfollow_user(self, user_profile, silent_ex=False):
        """
        For the given user profile, first do the actual twitter unfollow
        then also update the user profile object locally so we can quickly
        get the required status.

        If :param silent_ex: is set to true, any exception from twitter call
        is ignored. (e.g. autofollow on DM creation).
        """
        from solariat_bottle.tasks.twitter import tw_unfollow
        tw_unfollow(channel=self,
                    user_profile=user_profile,
                    silent_ex=silent_ex)

        self.update(inc__friends_count=-1)

    def get_attached_service_channels(self):
        service_channel = self.get_service_channel()
        return service_channel and [service_channel] or []

    def get_service_channel(self):
        channel = self.get_user_tracking_channel()
        if channel:
            channel = TwitterServiceChannel.objects.find_one(outbound=channel.id)
        return channel

    def get_user_tracking_channel(self):

        if self.twitter_handle is None:
            return None

        # candidates = UserTrackingChannel.objects.find(usernames__in=get_sync_usernames_list([self.twitter_handle]),
        #                                               account=self.account)[:]

        # case-insensitive lookup for service channel
        from solariat_bottle.db.tracking import PostFilterEntry, TrackingNLP

        usernames_list = get_sync_usernames_list([self.twitter_handle])
        usernames_list = map(TrackingNLP.normalize_kwd, usernames_list)
        candidate_channel_ids = set()
        for pfe in PostFilterEntry.objects.coll.find(
                {PostFilterEntry.F.entry: {'$in': usernames_list}},
                fields=[PostFilterEntry.F.channels]):
            chs = pfe[PostFilterEntry.F.channels]
            if not isinstance(chs, (list, tuple)):
                chs = [chs]
            for ch in chs:
                if hasattr(ch, 'id'):
                    candidate_channel_ids.add(ch.id)
                else:
                    candidate_channel_ids.add(ch)

        candidates = UserTrackingChannel.objects(id__in=candidate_channel_ids,
                                                 account=self.account)[:]
        if candidates:
            if len(candidates) == 1:
                return candidates[0]
            else:
                LOGGER.warning(
                    "We have multiple candidates for service channel matching for enterprise channel %s" % self)
                return None
        LOGGER.warning(
            "No service channel candidates were found for outbound channel %s. "
            "Some outbound channel filtering might not work.",
            self.title
        )
        return None

    def get_outbound_channel(self, user):
        return self


class TwitterTestDispatchChannel(EnterpriseTwitterChannel):
    '''Used for testing purposes, and defined here so the class is available'''
    _auth_flag = fields.BooleanField(default=True)

    @property
    def is_authenticated(self):
        return self._auth_flag


class FollowerTrackingChannel(Channel):
    """
    A channel that follows a list of twitter usernames.
    """
    twitter_handles = fields.ListField(fields.StringField())
    status_update = fields.DateTimeField(db_field='st',
                                         default=datetime.utcnow())

    tracking_mode = fields.StringField(
        default='Passive', choices=('Active', 'Passive'))

    @property
    def is_dispatchable(self):
        return False

    @property
    def type_name(self):
        return "Follower Tracking"

    @property
    def type_id(self):
        return 1

    def get_outbound_channel(self, user):
        return get_twitter_outbound_channel(user, self)

    def get_status(self):
        statuses = FollowerTrackingStatus.objects(channel=self.id)
        return [st.to_dict() for st in statuses]

    def on_active(self):

        self.status = 'Active'
        self.status_update = datetime.utcnow().replace(microsecond=0)
        self.update(set__status=self.status,
            set__status_update=self.status_update)

        from solariat_bottle.tasks.twitter import tw_count, tw_scan_followers

        for fts in FollowerTrackingStatus.objects.find(channel=self.id):
            tw_count.ignore(fts, params=('followers_count',))
            tw_scan_followers.ignore(fts, self.status_update)

    def on_suspend(self):

        self.status = 'Suspended'
        self.status_update = datetime.utcnow().replace(microsecond=0)
        self.update(set__status=self.status,
            set__status_update=self.status_update)

        from solariat_bottle.tasks.twitter import tw_drop_followers

        tw_drop_followers.ignore(self)

    @property
    def usernames(self):
        return get_sync_usernames_list(self.twitter_handles)

    def add_username(self, username):

        if not username in self.twitter_handles:

            self.update(addToSet__twitter_handles=username)

            fts = FollowerTrackingStatus.objects.get_or_create(
                channel=self.id,
                twitter_handle=username)

            from solariat_bottle.tasks.twitter import tw_count, tw_scan_followers

            tw_count.ignore(fts, params=('followers_count',))
            tw_scan_followers.ignore(fts, self.status_update)

    def del_username(self, username):

        if username in self.twitter_handles:

            self.update(pull__twitter_handles=username)

            fts = FollowerTrackingStatus.objects.get(
                channel=self.id,
                twitter_handle=username)

            from solariat_bottle.tasks.twitter import tw_drop_followers

            tw_drop_followers.ignore(fts)

    def has_private_access(self, sender_handle, recipient_handle):
        if not (self.is_service or self.is_inbound):
            twitter_handle = sender_handle
        else:
            twitter_handle = recipient_handle
        return (self.parent_channel and
                TwitterServiceChannel.objects.get(self.parent_channel)._dm_access_check(twitter_handle))


class FollowerTrackingStatus(Document):
    channel = fields.ObjectIdField(db_field='cl')
    twitter_handle = fields.StringField(db_field='th')
    followers_count = fields.NumField(default=0, db_field='fc')
    followers_synced = fields.NumField(default=0, db_field='fs')
    sync_status = fields.StringField(default='idle', db_field='sy',
                                     choices=('idle', 'sync'))

    indexes = [Index(('channel', 'twitter_handle'), unique=True)]


class UserTrackingChannel(Channel, MultilanguageChannelMixin):
    " Tracks a list of datasift usernames "

    usernames = fields.ListField(fields.StringField())

    @property
    def requires_interim_status(self):
        return True

    def mentions(self, post):
        ''' Get all the mentions based on user name configuration'''
        from solariat_bottle.utils.post import normalize_screen_name
        from solariat_bottle.utils.tracking import TrackingNLP
        usernames = map(normalize_screen_name, self.usernames)
        return list(set(TrackingNLP.extract_mentions(post)) & set(usernames))

    def addressees(self, post):
        '''Get all the mentions in the beginning.'''
        mentions = self.mentions(post)
        results = set()
        for term in post.plaintext_content.lower().split():
            if term in mentions:
                results.add(term)
            else:
                break
        return list(results)

    def on_suspend(self):
        super(UserTrackingChannel, self).on_suspend()

        from solariat_bottle.db.tracking import PostFilterStream
        stream = PostFilterStream.get()
        stream.untrack_channel(self)

    def on_active(self):
        super(UserTrackingChannel, self).on_active()

        from solariat_bottle.db.tracking import PostFilterStream
        stream = PostFilterStream.get()
        stream.track('USER_NAME', self.usernames, [self], langs=self.langs)

    def get_outbound_channel(self, user):
        return get_twitter_outbound_channel(user, self)

    def add_username(self, username):
        " add username "
        # self.sync_contacts(user=username, platform='Twitter')

        from solariat_bottle.db.tracking import PostFilterStream

        _usernames = set(self.usernames)
        _usernames.add(username)
        self.usernames = list(_usernames)

        self.update(addToSet__usernames=username)

        if self.status in {'Active', 'Interim'}:
            stream = PostFilterStream.get()
            stream.track('USER_NAME', [username], [self], langs=self.langs)

    def del_username(self, username):
        " del username "

        from solariat_bottle.db.tracking import PostFilterStream

        _usernames = set(self.usernames)
        _usernames.discard(username)
        self.usernames = list(_usernames)

        self.update(pull__usernames=username)
        stream = PostFilterStream.get()
        stream.untrack('USER_NAME', [username], [self], langs=self.langs)

    @property
    def platform(self):

        return "Twitter"

    def has_private_access(self, sender_handle, recipient_handle):
        if not (self.is_service or self.is_inbound):
            twitter_handle = sender_handle
        else:
            twitter_handle = recipient_handle
        return (self.parent_channel and
                TwitterServiceChannel.objects.get(self.parent_channel)._dm_access_check(twitter_handle))


    def set_allowed_langs(self, langs, clear_previous=False):

        dif_langs = set(langs) - set(self.langs)
        if not dif_langs:
            return

        if clear_previous:
            self.langs = langs
        else:
            self.langs = list(set(self.langs)|dif_langs)
        self.save()


    def get_allowed_langs(self):

        return self.langs


    def remove_langs(self, langs):

        for lang in langs:
            if lang in self.langs:
                self.langs.remove(lang)
        self.save()


class KeywordTrackingChannel(Channel, MultilanguageChannelMixin):
    " for datasift keywords "

    keywords   = fields.ListField(fields.StringField())
    skipwords  = fields.ListField(fields.StringField())
    watchwords = fields.ListField(fields.StringField())

    @property
    def requires_interim_status(self):
        return True

    def make_post_vector(self, post):
        'Use configuration information to boost features'
        post_vector = Channel.make_post_vector(self, post)
        post_vector.update(mentions=self.mentions(post),
                           keywords=self.keywords,
                           watchwords=self.watchwords,
                           direction=self.find_direction(post))
        return post_vector

    @property
    def platform(self):
        return "Twitter"

    def get_outbound_channel(self, user):
        return get_twitter_outbound_channel(user, self)

    def is_individual(self, post):
        if post.addressee and  post.addressee not in set([kw.lower() for kw in self.keywords]):
            return True
        else:
            return False

    def on_suspend(self):
        super(KeywordTrackingChannel, self).on_suspend()

        from solariat_bottle.db.tracking import PostFilterStream
        stream = PostFilterStream.get()
        stream.untrack_channel(self)

    def on_active(self):
        " run this handler when channel activated "

        # It's a temporary status which will be overwritten
        # by datasift_sync2 script in 1.5 mins (at max)
        super(KeywordTrackingChannel, self).on_active()

        from solariat_bottle.db.tracking import PostFilterStream
        stream = PostFilterStream.get()
        for keyword in self.keywords:
            stream.track('KEYWORD', [LingualToken.unlangify(keyword)], [self], langs=self.__get_token_langs(keyword))
        for skipword in self.skipwords:
            stream.track('SKIPWORD', [LingualToken.unlangify(skipword)], [self], langs=self.__get_token_langs(skipword))

    def add_keyword(self, keyword):
        " add keyword "
        if not self.__is_token_valid(keyword, self.keywords):
            return False

        from solariat_bottle.db.tracking import PostFilterStream

        _keywords = set(self.keywords)
        _keywords.add(keyword)
        self.keywords = list(_keywords)

        self.update(addToSet__keywords=keyword)

        if self.status in ('Active', 'Interim'):
            stream = PostFilterStream.get()
            stream.track('KEYWORD', [LingualToken.unlangify(keyword)], [self], langs=self.__get_token_langs(keyword))
        return True

    def del_keyword(self, keyword):
        " del keyword "
        from solariat_bottle.db.tracking import PostFilterStream

        _keywords = set(self.keywords)
        _keywords.discard(keyword)
        self.keywords = list(_keywords)
        self.update(pull__keywords=keyword)
        stream = PostFilterStream.get()
        stream.untrack('KEYWORD', [LingualToken.unlangify(keyword)], [self], langs=self.__get_token_langs(keyword))

    def add_watchword(self, watchword):
        " add watchword "

        if not self.__is_token_valid(watchword, self.watchwords):
            return False

        _watchwords = set(self.watchwords)
        _watchwords.add(watchword)
        self.watchwords = list(_watchwords)
        self.update(addToSet__watchwords=watchword)
        return True

    def del_watchword(self, watchword):
        " del watchword "
        _watchwords = set(self.watchwords)
        _watchwords.discard(watchword)
        self.watchwords = list(_watchwords)
        self.update(pull__watchwords=watchword)

    def add_skipword(self, skipword):
        " add skipword "
        if not self.__is_token_valid(skipword, self.skipwords):
            return False

        from solariat_bottle.db.tracking import PostFilterStream

        _skipwords = set(self.skipwords)
        _skipwords.add(skipword)
        self.skipwords = list(_skipwords)
        self.update(addToSet__skipwords=skipword)

        if self.status in ('Active', 'Interim'):
            stream = PostFilterStream.get()
            stream.track('SKIPWORD', [LingualToken.unlangify(skipword)], [self], langs=self.__get_token_langs(skipword))
        return True

    def del_skipword(self, skipword):
        " del skipword "
        from solariat_bottle.db.tracking import PostFilterStream

        _skipwords = set(self.skipwords)
        _skipwords.discard(skipword)
        self.skipwords = list(_skipwords)
        self.update(pull__skipwords=skipword)
        stream = PostFilterStream.get()
        stream.untrack('SKIPWORD', [LingualToken.unlangify(skipword)], [self], langs=self.__get_token_langs(skipword))


    def has_private_access(self, sender_handle, recipient_handle):

        if not (self.is_service or self.is_inbound):
            twitter_handle = sender_handle
        else:
            twitter_handle = recipient_handle
        return (self.parent_channel and
                TwitterServiceChannel.objects.get(self.parent_channel)._dm_access_check(twitter_handle))


    def set_allowed_langs(self, langs, clear_previous=False):

        dif_langs = set(langs) - set(self.langs)
        if not dif_langs:
            return

        if clear_previous:
            self.langs = langs
        else:
            self.langs = list(set(self.langs)|dif_langs)
        self.save()

        self.__fix_tokens_langs(dif_langs, 'track')


    def get_allowed_langs(self):

        return self.langs


    def remove_langs(self, langs):

        for lang in langs:
            for keyword in self.keywords:
                if LingualToken.is_adopted_to_lang(keyword, lang):
                    self.del_keyword(keyword)

            for skipword in self.skipwords:
                if LingualToken.is_adopted_to_lang(skipword, lang):
                    self.del_skipword(skipword)

        for lang in langs:
            if lang in self.langs:
                self.langs.remove(lang)
        self.save()

        self.__fix_tokens_langs(langs, 'untrack')


    def __fix_tokens_langs(self, langs, action):

        keywords = [key for key in self.keywords if not is_token_lang_adopted(key)]
        skipwords = [skip for skip in self.skipwords if not is_token_lang_adopted(skip)]


        from solariat_bottle.db.tracking import PostFilterStream
        stream = PostFilterStream.get()

        if hasattr(stream, action):
            getattr(stream, action)('KEYWORD', keywords, [self], langs=langs)
            getattr(stream, action)('SKIPWORD', skipwords, [self], langs=langs)

    def __is_token_valid(self, token, values):

        result = False
        if token not in values:
            if is_token_lang_adopted(token):
                if LingualToken.unlangify(token) not in values:
                    result = True
            else:
                if token not in LingualToken.unlangify(values):
                    result = True
        return result


    def __get_token_langs(self, token):

        if is_token_lang_adopted(token):
            result = [token[0:2]]
        else:
            result = self.langs
        return result


    @property
    def lang_keywords(self):
        return [LingualToken(key, self.__get_token_langs(key)) for key in self.keywords]


    @property
    def lang_skipwords(self):
        return [LingualToken(key) for key in self.skipwords]


class GroupingConfig(SonDocument):
    MIN_GRP_TIMEOUT, MAX_GRP_TIMEOUT = 0, 7 * 24 * 60 * 60  # from 0 seconds to 7 days
    DEFAULT_GRP_TIMEOUT = 120  # seconds
    is_enabled = fields.BooleanField(default=False)
    group_by_type = fields.BooleanField(default=True)
    grouping_timeout = fields.NumField(default=DEFAULT_GRP_TIMEOUT)  # seconds

    @classmethod
    def validate_grouping_timeout(cls, timeout):
        allowed_types = (int, float)
        if not isinstance(timeout, allowed_types):
            raise ValueError("%s is not instance of %s" % (timeout, allowed_types))
        if not (timeout == 0 or cls.MIN_GRP_TIMEOUT <= timeout <= cls.MAX_GRP_TIMEOUT):
            raise ValueError("%s is not in range of [%s, %s]" % (timeout, cls.MIN_GRP_TIMEOUT, cls.MAX_GRP_TIMEOUT))
        return timeout


class TwitterServiceChannel(ServiceChannel, TwitterChannel):

    auto_refresh_followers = fields.NumField(default=20)
    auto_refresh_friends = fields.NumField(default=20)
    skip_retweets = fields.BooleanField(default=False)
    # grouping configuration for api/queue
    _grouping_config = fields.EmbeddedDocumentField(GroupingConfig)

    @property
    def grouping_config(self):
        if self._grouping_config is None:
            self._grouping_config = GroupingConfig()
        return self._grouping_config

    @property
    def grouping_enabled(self):
        return self.grouping_config.is_enabled

    @grouping_enabled.setter
    def grouping_enabled(self, value):
        from solariat_bottle.utils.views import parse_bool
        self.grouping_config.is_enabled = parse_bool(value)

    @property
    def grouping_timeout(self):
        return self.grouping_config.grouping_timeout

    @grouping_timeout.setter
    def grouping_timeout(self, value):
        if isinstance(value, basestring):
            value = float(value)
        self.grouping_config.grouping_timeout = GroupingConfig.validate_grouping_timeout(value)

    @property
    def InboundChannelClass(self):
        return KeywordTrackingChannel

    @property
    def OutboundChannelClass(self):
        return UserTrackingChannel

    @property
    def DispatchChannelClass(self):
        return EnterpriseTwitterChannel

    @property
    def usernames(self):
        return get_sync_usernames_list(self.outbound_channel.usernames)

    @property
    def keywords(self):
        return self.inbound_channel.keywords if hasattr(self.inbound_channel, "keywords") else []

    @needs_postfilter_sync
    def add_username(self, username):
        usernames = get_sync_usernames_list([username])
        if self.status in {'Active', 'Interim'}:
            self._track_usernames(usernames)
        for username in usernames:
            self.outbound_channel.add_username(username)

    @needs_postfilter_sync
    def del_username(self, username):
        usernames = get_sync_usernames_list([username])
        if self.status in {'Active', 'Interim'}:
            self._untrack_usernames(usernames)
        for username in usernames:
            self.outbound_channel.del_username(username)

    @needs_postfilter_sync
    def add_keyword(self, keyword):
        return self.inbound_channel.add_keyword(keyword)

    @needs_postfilter_sync
    def del_keyword(self, keyword):
        return self.inbound_channel.del_keyword(keyword)

    def _track_usernames(self, usernames=None):
        # Implicitly track usernames as keywords
        usernames = usernames or self.usernames
        from solariat_bottle.db.tracking import PostFilterStream
        from solariat_bottle.utils.post import normalize_screen_name

        stream = PostFilterStream.get()
        stream.track('KEYWORD', map(normalize_screen_name, usernames), [self.inbound_channel], langs=self.langs)

    def _untrack_usernames(self, usernames=None):
        usernames = usernames or self.usernames
        from solariat_bottle.db.tracking import PostFilterStream
        from solariat_bottle.utils.post import normalize_screen_name

        stream = PostFilterStream.get()
        stream.untrack('KEYWORD', map(normalize_screen_name, usernames), [self.inbound_channel], langs=self.langs)

    def on_active(self):
        super(TwitterServiceChannel, self).on_active()
        self._track_usernames()

    def on_suspend(self):
        super(TwitterServiceChannel, self).on_suspend()
        self._untrack_usernames()

    def tracked_entities(self):
        from solariat_bottle.utils.post import normalize_screen_name

        if self.status not in {'Active', 'Interim'}:
            return []

        ic = self.inbound_channel
        oc = self.outbound_channel

        def gen_lang_keywords(kwds, all_langs=None):
            by_lang = defaultdict(list)
            for kwd in kwds:
                lang, kwd = LingualToken.parse(kwd)
                by_lang[lang or 'all'].append(kwd)

            for lang, words in by_lang.iteritems():
                langs = all_langs if lang == 'all' else [lang]
                yield words, langs

        def inflate_entities(filter_type, kwds, channel, all_langs):
            return [(filter_type, keywords, channel, langs)
                    for keywords, langs in gen_lang_keywords(kwds, all_langs)]

        entities = [
            # (entity_type, entities, channels, langs)
            ('KEYWORD', map(normalize_screen_name, self.usernames), ic, self.langs),
            ('USER_NAME', oc.usernames, oc, self.langs)
        ]
        entities.extend(inflate_entities('KEYWORD', ic.keywords, ic, self.langs))
        entities.extend(inflate_entities('SKIPWORD', ic.skipwords, ic, self.langs))
        return entities

    def check_post_filter_entries(self, log_level=None, track_missing=False):
        from solariat_bottle.db.tracking import PostFilterStream

        if log_level:
            log = getattr(LOGGER, log_level)

        stream = PostFilterStream.get()
        tests_results = []
        for (filter_type, entries, channel, langs) in self.tracked_entities():
            tracked = stream.tracking_state(filter_type, entries, [channel], langs)
            all_tracked = all(is_tracked for (_, _, is_tracked) in tracked)
            tests_results.append(all_tracked)

            if not all_tracked:
                if log_level and log:
                    log("Missing PostFilterEntries ({}) for channel '{}'\n"
                        "Details: {}".format(filter_type, channel, tracked))
                # track missing PostFilterEntries
                if track_missing:
                    stream.track(filter_type, entries, [channel], langs=langs)

        return all(tests_results)

    @needs_postfilter_sync
    def set_allowed_langs(self, langs, clear_previous=False):

        current_langs = set(self.langs)

        super(TwitterServiceChannel, self).set_allowed_langs(langs, clear_previous)
        from solariat_bottle.db.tracking import PostFilterStream
        from solariat_bottle.utils.post import normalize_screen_name

        new_langs = set(langs) - current_langs
        usernames = self.usernames
        stream = PostFilterStream.get()
        stream.track('KEYWORD', map(normalize_screen_name, usernames), [self.inbound_channel], langs=new_langs)
        stream.track('USER_NAME', usernames, [self.outbound_channel], langs=new_langs)

    @needs_postfilter_sync
    def remove_langs(self, langs):

        super(TwitterServiceChannel, self).remove_langs(langs)
        from solariat_bottle.db.tracking import PostFilterStream
        from solariat_bottle.utils.post import normalize_screen_name

        usernames = self.usernames
        stream = PostFilterStream.get()
        stream.untrack('KEYWORD', map(normalize_screen_name, usernames), [self.inbound_channel], langs=langs)
        stream.untrack('USER_NAME', usernames, [self.outbound_channel], langs=langs)

    def to_dict(self, fields2show=None):
        res = super(TwitterServiceChannel, self).to_dict(fields2show)
        res['langs'] = self.langs
        res['keywords'] = self.keywords
        res['watchwords'] = self.watchwords
        # res['skipwords'] = self.skipwords
        return res


CHANNEL_ID_URL_MAP[EnterpriseTwitterChannel(title="").type_id] = EnterpriseTwitterChannel(title="").base_url

