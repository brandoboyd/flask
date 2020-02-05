'''
This module contains facebook specific functionality.
'''
from datetime  import datetime
from hashlib   import md5

from solariat.db import fields
from solariat.utils.lang.detect import Language
from solariat_bottle.db.post.base import Post, PostManager, UntrackedPost
from solariat.utils.timeslot import utc, parse_datetime
from solariat_bottle.settings import AppException
from solariat_bottle.tasks import postprocess_new_post
from solariat_bottle.db.user_profiles.chat_profile import ChatProfile
from solariat_bottle.utils.post import get_service_channel
from solariat_bottle.db.agent_matching.profiles.base_profile import UntrackedProfile
from solariat_bottle.utils.id_encoder import unpack_event_id, pack_event_id


class ChatPostManager(PostManager):

    def gen_session_id(self):
        return "chat:%s" % md5(str(datetime.now())).hexdigest()

    def create_by_user(self, user, **kw):
        safe_create = kw.pop('safe_create', False)
        if not safe_create:
            raise AppException("Use db.post.utils.factory_by_user instead")
        add_to_queue = kw.pop('add_to_queue', False)
        sync = kw.pop('sync', False) # We might consider dropping this entirely
        self.doc_class.patch_post_kw(kw)
        # handling extra_fields
        chat_data = kw.pop('chat_data', None)
        kw.setdefault("extra_fields", {})
        if chat_data:
            kw["extra_fields"].update({"chat": chat_data})
        kw["extra_fields"].setdefault("chat", {})

        session_id = kw.get("session_id", None) or kw["extra_fields"]["chat"].get("session_id")
        if not session_id:
            session_id = self.gen_session_id()
        kw["session_id"] = session_id
        chat_created_at = chat_data.get('created_at', None) if chat_data else dict()
        if chat_created_at:
            kw['_created'] = utc(parse_datetime(chat_created_at))

        assert 'actor_id' in kw, "No 'actor_id' provided with chat message, could not infer it based on " + str(kw)
        assert 'is_inbound' in kw, "No 'is_inbound' provided with chat message, could not infer it based on " + str(kw)

        CustomerProfile = user.account.get_customer_profile_class()
        AgentProfile = user.account.get_agent_profile_class()
        if 'user_profile' not in kw:    # If we have customer id but no specific profile, try to find it in our system
            if kw['is_inbound']:
                customer_or_agent = CustomerProfile.objects.get(kw['actor_id'])
            else:
                customer_or_agent = AgentProfile.objects.get(kw['actor_id'])
            profile = customer_or_agent.get_profile_of_type(ChatProfile)
            if not profile:
                profile = ChatProfile.anonymous_profile(platform='Chat')
            kw['user_profile'] = profile

        if not kw['is_inbound']:
            # We know it's outbound post, we need to figure out actor id based on parent from chat session
            try:
                parent = self.doc_class.objects.find(session_id=session_id, is_inbound=True).sort(_created=-1).limit(1)[:][0]
            # if we can't figure it out, let's put untracked post as a parent
            except IndexError:
                parent = UntrackedChatPost()
            kw['_id'] = pack_event_id(parent.actor.actor_num, kw['_created'])
        else:
            actor_num = self.doc_class.get_actor(True, kw['actor_id']).actor_num
            kw['_id'] = pack_event_id(actor_num, kw['_created'])
            # We know that it's inbound post, but may be the first post in conversation was outbound.
            # If that's the case, then this outbound post was fired by UntrackedProfile
            # Now we can encode id using current CustomerProfile instead of UntrackedProfile
            outbount_events = self.doc_class.objects.find(session_id=session_id, is_inbound=False)[:]
            for e in outbount_events:
                parent_actor_num, dt = unpack_event_id(e.id)
                if parent_actor_num == 0:
                    e.delete()
                    e.id = pack_event_id(actor_num, dt)
                    e.save()
        kw['force_create'] = True

        lang_data = kw.pop('lang', Language(('en', 1)))
        # creation
        post = self.create(**kw)
        # postprocess_new_post(user, post) - failing for now, something with tag assignments
        assert post.session_id, "ChatPost should have chat session_id"
        self._set_post_lang(post, lang_data)
        postprocess_new_post(user, post, add_to_queue)
        get_service_channel(post.channel).post_received(post)
        return post


class UntrackedChatPost(UntrackedPost):
    """
    Dummy object that represents the post that is not stored in db yet,
    though there is a reference to this post (i.e. in in_reply_to_status_id)
    in another stored post
    """
    id = None
    actor = UntrackedProfile()

    @property
    def native_id(self):
        return self.id


class ChatPost(Post):

    manager    = ChatPostManager

    _parent_post = fields.ReferenceField('ChatPost', db_field='pp')
    session_id = fields.StringField()

    PROFILE_CLASS = ChatProfile

    @property
    def platform(self):
        return 'Chat'

    @property
    def parent(self):
        if self._parent_post == None:
            post = self._get_parent_post()
            if isinstance(post, UntrackedChatPost):
                return post
            self._parent_post = post
        return self._parent_post

    @property
    def conversation(self):
        from solariat_bottle.db.conversation import SessionBasedConversation
        try:
            res = SessionBasedConversation.objects.get(session_id=self.session_id)
        except SessionBasedConversation.DoesNotExist:
            res = None
        return res

    def _get_parent_post(self):
        """ Find the parent chat post of the current post """
        conversation = self.conversation
        if not conversation:
            return None
        # We have no direct way to get a parent from a chat session. Just need to
        # iterate the posts in the conversation and return the previous post to this one
        candidates = sorted(conversation.query_posts()[:], key=lambda x: x.created_at)
        for candidate in reversed(candidates):
            if candidate.created_at < self.created_at:
                return candidate
        return None

    @property
    def view_url_link(self):
        return 'View Chat Message'

    @property
    def is_amplifier(self):
        return False

    def platform_specific_data(self, outbound_channel=None):
        """ Any post info that is specific only per platform goes here """
        return {'has_location': self.has_location}

    @property
    def has_attachments(self):
        return False

    @property
    def has_location(self):
        chat_data = self._chat_data
        return chat_data.get('location', False)

    @property
    def parent_post_id(self):
        chat_data = self._chat_data
        parent_status_id = chat_data.get('in_reply_to_status_id', None)
        return parent_status_id

    @property
    def _chat_data(self):
        return self.extra_fields.get('chat', {})

    def is_root_post(self):
        return not self.parent

    @property
    def _chat_created_at(self):
        return self._chat_data.get('created_at', None)

    def parse_created_at(self):
        return utc(parse_datetime(self._chat_created_at)) if self._chat_created_at else None

    def _set_url(self, url=None):
        if url is not None:
            self.url = url
            return

    def set_url(self, url=None):
        self._set_url(url)
        self.save()

    # @classmethod
    # def gen_id(cls, is_inbound, actor_id, _created, in_reply_to_native_id, parent_event=None):
    #     actor_num = cls.get_actor(is_inbound, actor_id).actor_num
    #     return pack_event_id(actor_num, _created)

    def to_dict(self, fields2show=None, include_summary=True):
        from solariat_bottle.db.predictors.multi_channel_smart_tag import EventTag
        base_dict = super(ChatPost, self).to_dict(fields2show=fields2show)
        if include_summary:
            conversation = self.conversation
            base_dict['summary'] = self.conversation.get_summary()
        return base_dict
