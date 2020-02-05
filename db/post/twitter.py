'''
This module contains twitter specific functionality
'''
import re
import json
from datetime import datetime, timedelta
from solariat_bottle.db.user_profiles.social_profile import TwitterProfile, \
    SocialProfile
from solariat_bottle.settings import get_var, AppException
from solariat.db import fields
from solariat_bottle.db.post.base import Post, PostManager, UntrackedPost, POST_PUBLIC
from solariat_bottle.db.channel.base import TWITTER_INDEX
from solariat.utils.timeslot import utc, now, parse_datetime
from solariat_bottle.tasks import postprocess_new_post
from solariat_bottle.tasks.twitter import tw_follow_direct_sender


DATE_FORMAT       = '%a, %d %b %Y %H:%M:%S'
TWITTER_STATUS_RE = re.compile(r'^https?://twitter.com/\S+/statuses/(\S+)$', re.IGNORECASE)


class TweetSource(object):
    DATASIFT_STREAM = 0  # NOTE: old posts don't have native_data['_source']
    TWITTER_PUBLIC_STREAM = 1
    TWITTER_USER_STREAM = 2



def get_twitter_suffix():
    return ':' + str(TWITTER_INDEX)


def datetime_to_string(d):
    """
    Return a string with a datetime object formatted as it would
    come from an original twitter source.
    """
    date_string = d.strftime(DATE_FORMAT)
    return date_string + " +0000"


def get_status_from_url(twitter_url):
    """ From a twitter post URL return the status id """
    match = TWITTER_STATUS_RE.match(twitter_url)
    if match:
        return match.group(1)
    return twitter_url


def get_status_id_by_post_id(post_id):
    """Extracts tweet status id from Post.id"""
    id_part = post_id.split(':', 1)[1]

    if id_part.startswith('http'):  #old ids case
        return get_status_from_url(id_part)
    else:
        return id_part.split(':')[0]


class UntrackedTwitterPost(UntrackedPost):
    """
    Dummy object that represents the post that is not stored in db yet,
    though there is a reference to this post (i.e. in in_reply_to_status_id)
    in another stored post
    """
    id = None
    created_at = datetime.now()


class TwitterPostManager(PostManager):

    @staticmethod
    def gen_id(padding=0, **kw):
        twitter_data = kw.pop('twitter_data', None)
        p_id = TwitterPost.gen_id(
            is_inbound = kw['is_inbound'],
            actor_id=kw['actor_id'],
            in_reply_to_native_id=twitter_data.get('in_reply_to_status_id') if twitter_data else None,
            parent_event=kw.get('_parent_post'),
            _created=kw['_created'] + timedelta(milliseconds=padding))
        return p_id

    def create_by_user(self, user, **kw):
        '''
        This method does the lions share of the processing for a new post.

        The keyword arguments we accomodate for twitter are:
        * user_profile - the platform specific user profile
        * url - the url of the post in original location
        * twitter - a packet of extra data for tweets

        The main elements are:
        1. Extract Intentions
        2. Extract Paramaters for creation
        3. Allocate the Post object
        4. Link to Conversation
        5. Compute Tag and Channel Relations (filtering)
        6. Update Statistics
        7. Optionally generate a Response Object for Inbox
        '''
        safe_create = kw.pop('safe_create', False)

        if not safe_create:
            raise AppException("Use db.post.utils.factory_by_user instead")
        add_to_queue = kw.pop('add_to_queue', True)
        sync = kw.pop('sync', False)

        profile = kw.get('user_profile', None)

        # specific twitter additions
        url           = kw.pop('url',     None)
        twitter_data  = kw.pop('twitter', None)
        extra_fields  = kw.pop('extra_fields', {})

        if not twitter_data and url and '//twitter' in url:
            twitter_data = {'id': get_status_from_url(url)}

        if twitter_data:
            extra_fields.update({'twitter': twitter_data})
        kw['extra_fields'] = extra_fields
        kw['force_create'] = True

        kw = TwitterPost.patch_post_kw(kw, native_data=twitter_data)
        native_id = None
        if twitter_data and twitter_data.get('id', False):
            native_id = twitter_data.get('id')
        post_data = self._prepare_post_checking_duplicates(TwitterPostManager,
                                                           native_id=native_id, **kw)
        post, should_skip = post_data
        if should_skip:
            return post

        post.set_engage_stats(to_save=False)
        post.set_url(profile, twitter_data)  # also saves the post

        # postprocess the post
        if get_var('DEBUG_SKIP_POSTPROCESSING'):
            return post

        if sync or get_var('PROFILING'):
            # running synchronously when profiling
            postprocess_new_post    .sync(user, post, add_to_queue)
            post.reload()  # make sure the post has updated stats

        elif get_var('ON_TEST'): # We still have use-cases where we need to force a sync run
            # running asynchronously even when testing
            # (to maximally model the production environment)

            pp_task = postprocess_new_post    .async(user, post, add_to_queue)
            # when testing it is important to check for any exceptions
            pp_task.result()
            post.reload()  # make sure the post has updated stats
        else:
            # running asynchronously not waiting for results
            postprocess_new_post    .ignore(user, post, add_to_queue)

        return post


class TwitterPost(Post):

    manager = TwitterPostManager

    platform = 'Twitter'
    PROFILE_CLASS = TwitterProfile

    def post_type(self):
        return self.MESSAGE_TYPE_MAP[self.message_type]

    @property
    def is_pm(self):
        return self.message_type == 'direct'

    @property
    def computed_tags(self):
        return list(set(self._computed_tags + [str(smt.id) for smt in self.accepted_smart_tags] + self.assigned_tags))

    @property
    def view_url_link(self):
        if self.message_type == 'direct':
            return 'View DM on Twitter'
        else:
            return 'View Tweet'

    def _get_message_type(self):
        return self.MESSAGE_TYPE_MAP[self._message_type]

    def _set_message_type(self, val):
        """
        Accept either a string as a value from MESSAGE_TYPE_MAP or
        an integer as the direct value that will be stored in database.
        """
        if isinstance(val, str):
            for key, value in self.MESSAGE_TYPE_MAP.iteritems():
                if val == value:
                    self._message_type = key
        else:
            self._message_type = val

    message_type = property(_get_message_type, _set_message_type)

    @property
    def is_tweet(self):
        return 'twitter' in self.extra_fields

    @property
    def is_share(self):
        return False

    @property
    def is_amplifier(self):
        return self.is_retweet or self.is_share

    def platform_specific_data(self, outbound_channel):
        """ Any post info that is specific only per platform goes here """
        return {"message_type" : self.message_type,
                "url" : self.url if self.message_type != 'direct' else "http://twitter.com",}

    def _get_parent_tweet(self):
        """ Find the parent twitter post of the current post """
        parent_status_id = self.parent_post_id
        if parent_status_id:
            try:
                parent_post = self.objects.get(_native_id=str(parent_status_id))
            except Post.DoesNotExist:
                parent_post = UntrackedTwitterPost(created_at=self.created_at - timedelta(minutes=1))
        else:
            parent_post = UntrackedTwitterPost(created_at=self.created_at - timedelta(minutes=1))
        return parent_post

    @property
    def parent(self):
        if self._parent_post == None:
            post = self._get_parent_tweet()
            if isinstance(post, UntrackedTwitterPost):
                return post
            self._parent_post = post
        return self._parent_post

    @property
    def parent_post_id(self):
        twitter_data = self.native_data
        parent_status_id = twitter_data.get('in_reply_to_status_id') if twitter_data else None
        if not parent_status_id:
            if 'retweeted' in twitter_data and isinstance(twitter_data['retweeted'], dict):
                # datasift sends retweets as separate objects,
                # but they are same as usual tweets in twitter public stream
                parent_status_id = twitter_data['retweeted']['id']
        if not parent_status_id:
            twitter_data = self.wrapped_data
            if 'retweeted_status' in twitter_data and isinstance(twitter_data['retweeted_status'], dict):
                # retweet from twitter REST/Stream API should have retweeted_status object
                parent_status_id = twitter_data['retweeted_status']['id']
        if parent_status_id:
            return str(parent_status_id)
        else:
            return parent_status_id

    def parent_in_conversation(self, conversation, existing_posts=[]):
        if self._message_type == 0:
            # For public posts we go back in conversation
            # and return the earliest inbound post before conversation switches to outbound
            # or self.parent if no first inbound public post is found
            parent = self.parent
            for ex_post in reversed(existing_posts):
                if ex_post._message_type == 0 and ex_post.id != self.id and conversation.route_post(ex_post) == 'outbound':
                    break
                else:
                    parent = ex_post
            return parent
        else:
            # For direct messages we need to figure it out from the conversation.
            parent = None
            for ex_post in reversed(existing_posts):
                if ex_post._message_type == 1 and ex_post.id != self.id and conversation.route_post(ex_post) == 'inbound':
                    parent = ex_post
                    break
        return parent

    @property
    def wrapped_data(self):
        return json.loads(self.native_data.get('_wrapped_data', '{}'))

    @property
    def native_data(self):
        res = self.extra_fields.get('twitter', {})
        if res is None:
            res = {}
        return res

    @property
    def is_retweet(self):
        return bool(self.native_data.get('retweet') or self.native_data.get('_is_retweet'))

    @property
    def is_reply(self):
        return bool(self.native_data.get('in_reply_to_status_id'))

    def is_reply_or_retweet(self):
        from itertools import imap

        fields = ('in_reply_to_status_id', 'retweet')
        return any(imap(self.native_data.get, fields))

    def is_root_post(self):
        return not self.is_reply_or_retweet()

    @staticmethod
    def platform_created_at(platform_data):
        if 'retweet' in platform_data:
            return platform_data['retweet']['created_at']

        return platform_data.get('created_at', None)

    def parse_created_at(self):
        _created_at = self.platform_created_at(self.native_data)
        return parse_datetime(_created_at, default=utc(now()))

    def get_contacts_for_channel(self, service_channel):
        contacts = [self.get_user_profile().id] if service_channel.route_post(self) == 'inbound' else []

        # Augment contact ids with addressee information for outbound posts.
        addressees = []
        if service_channel.route_post(self) == 'outbound':
            addressee = self.addressee
            if addressee:
                if self._message_type == 1:
                    addressees.append(addressee[1:] if (addressee and addressee[0] == '@') else addressee)
                else:
                    addressees.append(addressee)
        if addressees:
            addressees = [u.id for u in SocialProfile.objects(user_name__in=addressees)]
            contacts.extend(addressees)
        return contacts

    # def _set_url(self, user_profile=None):
    #     '''Utility to set the external url'''
    #     try:
    #         id_ = self.id.split(':',1)[1]
    #         unpacked = id_.split(':')

    #         # Handle case when itis not the expected platform formatted id
    #         if id_.startswith('http') or len(unpacked) != 2:
    #             self.url = id_
    #         else:
    #             original_id, channel_type = tuple(unpacked)
    #             if channel_type == '0':  # Twitter
    #                 profile  = user_profile or self.get_user_profile()
    #                 self.url = 'https://twitter.com/%s/statuses/%s' % (profile.screen_name, original_id)

    #     except Exception, exc:
    #         err_msg = "Error decoding url for id: %s. %s" % (self.id, str(exc))
    #         LOGGER.error(err_msg)
    #         raise Exception(err_msg)


    def _set_url(self, user_profile, twitter_data):
        '''Utility to set the external url'''
        profile  = user_profile or self.get_user_profile()
        self.url = 'https://twitter.com/%s/statuses/%s' % (
            profile.screen_name, twitter_data['id'] if twitter_data else self.id)


    def set_url(self, user_profile, twitter_data):
        self._set_url(user_profile=user_profile, twitter_data=twitter_data)
        self.save()



