from solariat.db import fields
from solariat_bottle.db.post.base import Post, PostManager
from solariat_bottle.db.user_profiles.nps_profile import NPSProfile
from solariat_bottle.utils.id_encoder import pack_event_id
from solariat.utils.timeslot import now
from solariat_bottle.utils.post import get_language
from solariat_bottle.db.user import get_user
from solariat_bottle.tasks import _set_channel_and_tag_assignments, normalize_post_params


class NPSPostManager(PostManager):

    def create_by_user(self, user, **kw):
        # assert kw.get('case_number'), kw

        if not kw.get('_created'):
            kw['_created'] = now()

        if not kw.get('actor_id'):
            kw['actor_id'] = kw['case_number']

        try:
            nps_profile = NPSProfile.objects.get(kw['actor_id'])
        except:
            nps_profile = NPSProfile.objects.create(id=kw['actor_id'])
        _id = NPSPost.gen_id(
            actor_id=nps_profile.id,
            _created=kw['_created'],
            in_reply_to_native_id=None
        )

        # from solariat_bottle.db.channel.voc import *
        # chan = VOCChannel.objects.get(kw['channels'][0])
        # if isinstance(chan, VOCServiceChannel):
        #     kw['channels'] = str(chan.inbound_channel.id)
        normalize_post_params(user, kw)
        post = super(NPSPostManager, self).create(_id=_id, force_create=True, **kw)

        for sc in post.service_channels:
            sc.post_received(post)
        _set_channel_and_tag_assignments(post)
        return post


class NPSPost(Post):

    PROFILE_CLASS = NPSProfile
    manager = NPSPostManager

    allow_inheritance = True
    collection = "NPSPost"

    case_number = fields.StringField(db_field='cn', required=True)
    last_modified = fields.DateTimeField(db_field='lm', required=False)
    case_update_id = fields.StringField(db_field='cd', required=False)
    type = fields.StringField(db_field='te', required=False)
    native_id = fields.StringField(db_field='nd', required=True)
    description = fields.StringField(db_field='dsc')
    survey_response_name = fields.StringField(db_field='srn')

    @classmethod
    def gen_id(cls, account, actor_id, _created, in_reply_to_native_id, parent_event=None):
        CustomerProfile = account.get_customer_profile_class()
        actor_num = CustomerProfile.objects.get(id=actor_id).actor_num
        packed = pack_event_id(actor_num, _created)
        return packed

    @property
    def computed_tags(self):
        return list(set(self._computed_tags + [str(smt.id) for smt in self.accepted_smart_tags] + self.assigned_tags))

    # @classmethod
    # def get_actor(cls, actor_id):
    #     CustomerProfile = get_user().account.get_customer_profile_class()
    #     return CustomerProfile.objects.get(case_number=actor_id)


class NPSOutcomeManager(PostManager):

    def create_by_user(self, user, **kw):
        post_lang = get_language(kw)
        kw['lang'] = post_lang

        if 'content' not in kw:
            kw['content'] = 'No verbatim provided'

        assert kw.get('case_number'), kw
        kw['is_inbound'] = True
        kw['safe_create'] = True
        # We need to override posts for NPS,
        # so we need to check if post exist,
        # if post exist let remove it and re-create
        if kw.get('actor_id'):
            CustomerProfile = user.account.get_customer_profile_class()
            actor_num = CustomerProfile.objects.get(kw.get('actor_id')).actor_num
        elif kw.get('user_profile'):
            # TODO: [gsejop] create anonymous CustomerProfile?
            # actor_num = kw['user_profile'].customer_profile.actor_num
            actor_num = kw['user_profile'].actor_num
        else:
            actor_num = 0

        if kw['user_profile']:
            kw['profile_data'] = kw['user_profile'].data
        nps_event_id = pack_event_id(actor_num, kw['_created'])
        try:
            nps_post = self.get(id=nps_event_id)
            raise Exception('NPSOutcome with nps_event_id: %s exists already' % nps_event_id)
        except NPSOutcome.DoesNotExist:
            pass
        try:
            nps_post = NPSOutcome.get_by_native_id(kw['native_id'])
            raise Exception('NPSOutcome with native_id: %s exists already' % kw['native_id'])
        except NPSOutcome.DoesNotExist:
            pass

        normalize_post_params(user, kw)
        post = super(NPSOutcomeManager, self).create_by_user(user, **kw)
        # self._postprocess_new_post(user, post, sync)
        # _set_channel_and_tag_assignments(post)

        # post.compute_journey_information()  # why we needed this? PostManager.create_by_user already did this
        return post


class NPSOutcome(Post):

    manager = NPSOutcomeManager
    PROFILE_CLASS = NPSProfile

    case_number = fields.StringField(db_field='cr', required=True)
    response_type = fields.StringField(db_field='rp', required=True)
    score = fields.NumField(db_field='se', required=True)
    profile_data = fields.DictField(db_field='pd')

    indexes = [('response_type',), ('_created',)]

    @property
    def computed_tags(self):
        return list(set(self._computed_tags + [str(smt.id) for smt in self.accepted_smart_tags] + self.assigned_tags))

    @classmethod
    def gen_id(cls, is_inbound, actor_id, _created, in_reply_to_native_id, parent_event=None):
        actor_num = cls.get_actor(True, actor_id).actor_num
        packed = pack_event_id(actor_num, _created)
        return packed

    def to_dict(self, fields2show=None):
        base_dict = super(NPSOutcome, self).to_dict(fields2show=fields2show)
        base_dict.pop('profile_data')
        return base_dict
