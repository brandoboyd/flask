'''
This module contains facebook specific functionality.
'''
import json
from solariat_bottle.db.user_profiles.social_profile import FacebookProfile

from solariat_bottle.settings import AppException, get_var, LOGGER

from solariat.db           import fields
from solariat_bottle.db.post.base import Post, PostManager, UntrackedPost
from solariat_bottle.db.channel.base import FACEBOOK_INDEX

from solariat_bottle.utils.post     import make_id
from solariat.utils.timeslot import utc, parse_datetime, timedelta, now

from solariat_bottle.tasks import postprocess_new_post


def get_page_ids(facebook_data):
    page_id = facebook_data.get('page_id')
    if not page_id:
        page_id = facebook_data.get('_wrapped_data', {}).get('page_id')
        if not page_id:
            return None
    if '_' in page_id:
        page_ids = page_id.split('_')
    else:
        page_ids = [page_id]
    return page_ids


def lookup_facebook_channels(facebook_data):
    from solariat_bottle.db.facebook_tracking import FacebookTracking
    page_ids = get_page_ids(facebook_data)
    if page_ids:
        return FacebookTracking.objects.find_channels(page_ids)
    else:
        return None


def get_facebook_suffix():
    return ':' + str(FACEBOOK_INDEX)


class FacebookPostManager(PostManager):

    def _requires_moderation(self, user, post):
        return False

    @staticmethod
    def gen_id(padding=0, **kw):
        facebook_data = kw.pop('facebook_data', None)
        p_id = FacebookPost.gen_id(
            is_inbound=kw['is_inbound'],
            actor_id=kw['actor_id'],
            in_reply_to_native_id=facebook_data.get('in_reply_to_status_id') if facebook_data else None,
            _created=kw['_created'] + timedelta(milliseconds=padding))
        return p_id

    def create_by_user(self, user, **kw):
        '''
        This method does the lions share of the processing for a new post.

        The keyword arguments we accomodate are:
        * user_profile - the platform specific user profile
        * url - the url of the post in original location
        * facebook - a packet of extra data

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

        # specific twitter additions
        url           = kw.pop('url',      None)
        facebook_data = kw.pop('facebook', None)
        extra_fields  = kw.pop('extra_fields', {})

        if facebook_data:
            extra_fields.update({'facebook': facebook_data})

        kw['extra_fields'] = extra_fields
        kw['force_create'] = True
        kw = FacebookPost.patch_post_kw(kw, native_data=facebook_data)

        native_id = None
        if facebook_data and facebook_data.get('facebook_post_id', False):
            native_id = facebook_data.get('facebook_post_id')
        post_data = self._prepare_post_checking_duplicates(PostManager, native_id=native_id, **kw)
        post, should_skip = post_data
        if should_skip:
            return post

        post.set_engage_stats(to_save=False)
        post.set_url(url)  # also saves the post
        post.set_root_target()
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

    @staticmethod
    def find_by_fb_id(fb_id):
        return FacebookPost.objects.find_one(_native_id=fb_id)


class UntrackedFacebookPost(UntrackedPost):  #{
    """
    Dummy object that represents the post that is not stored in db yet,
    though there is a reference to this post (i.e. in in_reply_to_status_id)
    in another stored post
    """
    id = None

    @property
    def native_id(self):
        return self.id


class FacebookPost(Post):

    manager = FacebookPostManager

    root_target = fields.DictField()

    platform = 'Facebook'
    PROFILE_CLASS = FacebookProfile

    @property
    def parent(self):
        if self._parent_post == None:
            post = self._get_parent_post()
            if isinstance(post, UntrackedFacebookPost):
                return post
            self._parent_post = post
        return self._parent_post

    @property
    def is_second_level_reply(self):
        """ Return true if this is a second level reply to which we can
        only answer with another second level reply. """
        facebook_data = self.native_data
        return facebook_data.get('second_level_reply', False)

    def like_status(self, username):
        """ Check if the username liked the post or not """
        return username in self.likes

    def like(self, username):
        if username not in self.likes:
            self.likes.append(username)
            self.save()

    def unlike(self, username):
        if username in self.likes:
            self.likes.remove(username)
            self.save()

    def platform_specific_data(self, outbound_channel=None):
        """ Any post info that is specific only per platform goes here """
        if outbound_channel:
            like_status = self.like_status(outbound_channel.facebook_screen_name)
        else:
            like_status = False
        return {'liked': like_status, 'has_attachments': self.has_attachments, 'has_location': self.has_location}

    def set_root_target(self):

        data = self.wrapped_data
        source_id = data.get("source_id", None)
        if source_id:
            if data['source_type'] == 'PM':
                self.root_target = {"type": data['source_type'], "target": source_id}
            else:
                target = data["source_id"] if '_' not in data["source_id"] else data["source_id"].split("_")[0]
                self.root_target = {"type": data['source_type'], "target": target}
            self.save()

    def _get_parent_post(self):
        try:
            return FacebookPost.objects.get(_native_id=self.wrapped_data.get('parent_id', None))
        except Post.DoesNotExist:
            pass

        if self.parent_status_id:
            try:
                return FacebookPost.objects.get(_native_id=self.parent_status_id)
            except Post.DoesNotExist:
                return UntrackedFacebookPost(id=self.parent_status_id)

        return None

    @property
    def view_url_link(self):
        return 'View Post'

    @property
    def is_amplifier(self):
        return False

    @property
    def has_attachments(self):
        facebook_data = self.native_data
        return facebook_data.get('attachments', False)

    @property
    def has_location(self):
        facebook_data = self.native_data
        return facebook_data.get('location', False)

    @property
    def parent_status_id(self):
        facebook_data = self.native_data
        parent_status_id = facebook_data.get('in_reply_to_status_id', None)
        return parent_status_id

    @property
    def wrapped_data(self):
        # TODO: We should be consistent here and either only store JSON dumps or only store dicts.
        # For now, quick workaround to work for both bots.
        if not self.native_data:
            return {}
        __wrapped = self.native_data.get('_wrapped_data', '{}')
        if isinstance(__wrapped, dict):
            return __wrapped
        return json.loads(__wrapped)

    @property
    def native_data(self):
        return self.extra_fields.get('facebook', {})

    @property
    def can_comment(self):
        if 'can_comment' in self.wrapped_data:
            return self.wrapped_data['can_comment']
        if self.is_second_level_reply:
            return False
        return True

    def is_root_post(self):
        return not self.parent

    @staticmethod
    def platform_created_at(platform_data):
        return platform_data.get('created_at', None)

    def parse_created_at(self):
        _created_at = self.platform_created_at(self.native_data)
        return parse_datetime(_created_at, default=utc(now()))

    @property
    def is_pm(self):
        return 'conversation_id' in self.native_data

    @property
    def facebook_id(self):
        if self.native_data and 'facebook_post_id' in self.native_data:
            return self.native_data['facebook_post_id']
        if self.wrapped_data and 'id' in self.wrapped_data:
            return self.wrapped_data['id']
        return None

    def _set_url(self, url=None):
        '''Utility to set the external url
        TODO: Adapt for facebook'''
        fb_id = self.facebook_id
        if fb_id:
            # Facebook is smart enough to do this for us, so if we have a valid id we can use that
            self.url = "http://www.facebook.com/%s" % fb_id
            return
        if url is not None:
            self.url = url
            return
        try:
            self.url = "https://www.facebook.com/%s/posts/%s" % (
                self.native_data.get('page_id'), self.native_data.get('facebook_post_id'))
        except Exception, exc:
            err_msg = "Error decoding url for id: %s. %s" % (self.id, str(exc))
            LOGGER.error(err_msg)
            raise Exception(err_msg)

    def set_url(self, url=None):
        self._set_url(url)
        self.save()

    def get_conversation_root_id(self):
        self_id = self.facebook_id

        post_type = self.wrapped_data.get('type') or self.wrapped_data.get('source_type')
        if not post_type:
            LOGGER.error("Could not infer post type for post " + str(self))
            return None
        post_type = post_type.lower()

        target = self.wrapped_data['source_id']

        if post_type == 'pm':
            result = self.native_data['conversation_id']
        elif post_type in ('status', 'post', 'link', 'photo', 'event', 'video'):
            result = self_id
        else:
            result = target

        return result
