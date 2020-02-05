from solariat_bottle.configurable_apps import APP_JOURNEYS
from solariat.db import fields

from solariat_nlp import extract_intentions
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.events.event import Event, EventManager
from solariat_bottle.db.user_profiles.web_profile import WebProfile
from solariat.utils.lang.detect import detect_prob, DetectorSetupError, LanguageInconclusiveError, Language

ANONYMOUS_FAQ_ID = "faq_anonymous_user"


class FAQEventManager(EventManager):

    def create_by_user(self, user, **kw):
        """
        :param user: GSA user whose credentials were used to create a new WebClick object
        :param kw: Any WebClick specific data
        :return:
        """
        assert 'query' in kw, 'Missing required "query" parameter in kwargs=%s' % kw
        channel = kw['channels'][0]
        channel = channel if isinstance(channel, Channel) else Channel.objects.get(id=channel)
        if 'actor_id' not in kw:
            browser_signature = kw.get('browser_signature')
            browser_cookie = kw.get('browser_cookie')
            user_id = kw.get('user_id')
            session_id = kw.get('session_id')
            if not (session_id or user_id or browser_cookie or browser_signature):
                session_id = ANONYMOUS_FAQ_ID
            profile = WebProfile.objects.create_by_user(user,
                                                        # account=channel.account,
                                                        browser_signature=browser_signature,
                                                        browser_cookie=browser_cookie,
                                                        user_id=user_id,
                                                        session_id=session_id)
            kw['actor_id'] = profile.id
            
            if channel.account and APP_JOURNEYS in channel.account.available_apps:
                CustomerProfile = channel.account.get_customer_profile_class()
                customer_profile = CustomerProfile.objects.create(account_id=channel.account.id)
                customer_profile.add_profile(profile)
                kw['actor_id'] = customer_profile.id

        if 'safe_create' in kw:
            kw.pop('safe_create')
        kw['is_inbound'] = True

        try:
            lang = detect_prob(kw['query'])[0]
        except (DetectorSetupError, LanguageInconclusiveError):
            lang = Language(('en', 1.0))
        kw['speech_acts'] = extract_intentions(kw['query'], lang=lang.lang)
        for field in kw.keys():
            if field not in FAQQueryEvent.fields:
                del kw[field]
        event = FAQEventManager.create(self, **kw)
        return event


class FAQQueryEvent(Event):

    query = fields.StringField()
    speech_acts = fields.ListField(fields.DictField())

    manager = FAQEventManager

    PROFILE_CLASS = WebProfile

    @classmethod
    def patch_post_kw(cls, kw):
        pass

    @property
    def platform(self):
        return 'FAQ'

    def to_dict(self, fields2show=None):
        base_dict = super(FAQQueryEvent, self).to_dict()
        base_dict['actor'] = self.actor.to_dict()
        return base_dict


