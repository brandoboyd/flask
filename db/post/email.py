'''
This module contains facebook specific functionality.
'''
from datetime import datetime, timedelta

from solariat.db import fields
from solariat_bottle.db.post.base import Post, PostManager, UntrackedPost
from solariat_bottle.utils.post import make_id
from solariat.utils.timeslot import utc, parse_datetime
from solariat_bottle.settings import AppException

EMAIL_DATA_KEYS  = ["sender", "subject", "recipients", "cc", "created_at"]

class EmailPostManager(PostManager):

    @property
    def platform(self):
        return 'Email'

    def create_by_user(self, user, **kw):
        safe_create = kw.pop('safe_create', False)
        if not safe_create:
            raise AppException("Use db.post.utils.factory_by_user instead")
        sync = kw.pop('sync', False)
        # allocate a Post object
        email_data = kw.pop('email_data', {})
        assert isinstance(email_data, dict), type(email_data)
        # assert email_data, "you should pass 'email_data' arg to factory_by_user() call"
        kw.setdefault("extra_fields", {})
        if email_data:
            assert set(EMAIL_DATA_KEYS) <= set(email_data.keys()), "%s !<= %s" % (set(EMAIL_DATA_KEYS), set(email_data.keys()))
        kw["extra_fields"].update({"email": email_data})
        post = super(EmailPostManager, self).create_by_user(user=user, safe_create=True, **kw)
        return post


class UntrackedEmailPost(UntrackedPost):  #{
    """
    Dummy object that represents the post that is not stored in db yet,
    though there is a reference to this post (i.e. in in_reply_to_status_id)
    in another stored post
    """
    id = None

    @property
    def native_id(self):
        return self.id


class EmailPost(Post):

    manager = EmailPostManager

    _parent_post = fields.ReferenceField('EmailPost', db_field='pp')

    @property
    def platform(self):
        return 'Email'

    @property
    def parent(self):
        if self._parent_post == None:
            post = self._get_parent_post()
            # import ipdb; ipdb.set_trace()
            if isinstance(post, UntrackedEmailPost):
                return post
            self._parent_post = post
        return self._parent_post

    def _get_parent_post(self):
        parent_status_id = self.parent_post_id
        parent_post = None
        if parent_status_id:
            parent_post_id = make_id(parent_status_id)
            parent_post_id = parent_status_id
            try:
                #should be at most only one Post unless we search against user mentions
                parent_post = EmailPost.objects.get(id=parent_post_id)
            except Post.DoesNotExist:
                untracked_post = UntrackedEmailPost(id=parent_post_id, created_at=self.created_at - timedelta(minutes=1))
                parent_post = untracked_post
        return parent_post

    @property
    def parent_post_id(self):
        email_data = self._email_data
        parent_status_id = email_data.get('in_reply_to_status_id', None)
        return parent_status_id

    @property
    def session_id(self):
        return self._email_data.get('session_id', None)

    @property
    def view_url_link(self):
        return 'View Email'

    @property
    def is_amplifier(self):
        return False

    @property
    def has_attachments(self):
        return False

    def platform_specific_data(self, outbound_channel=None):
        """ Any post info that is specific only per platform goes here """
        return {'has_attachments': self.has_attachments}

    @property
    def _email_data(self):
        return self.extra_fields['email']

    def is_root_post(self):
        return not self.parent

    @property
    def _email_created_at(self):
        return parse_datetime(self._email_data.get('created_at', None))

    def parse_created_at(self):
        return self._email_created_at or None

    def _set_url(self, url=None):
        '''Utility to set the external url
        TODO: Adapt for chat'''
        if url is not None:
            self.url = url
            return

    def set_url(self, url=None):
        self._set_url(url)
        self.save()
