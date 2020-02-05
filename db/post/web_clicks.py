from solariat.db import fields

from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.events.event import Event, EventManager
from solariat_bottle.db.user_profiles.web_profile import WebProfile


class WebClickManager(EventManager):

    def create_by_user(self, user, **kw):
        """
        :param user: GSA user whose credentials were used to create a new WebClick object
        :param kw: Any WebClick specific data
        :return:
        """
        channel = kw['channels'][0]
        channel = channel if isinstance(channel, Channel) else Channel.objects.get(id=channel)
        if 'actor_id' not in kw:
            browser_signature = kw.get('browser_signature')
            browser_cookie = kw.get('browser_cookie')
            user_id = kw.get('user_id')
            session_id = kw.get('session_id')
            profile = WebProfile.objects.create_by_user(user,
                                                        account=channel.account,
                                                        browser_signature=browser_signature,
                                                        browser_cookie=browser_cookie,
                                                        user_id=user_id,
                                                        session_id=session_id)
            kw['actor_id'] = profile.customer_profile.id

        if 'safe_create' in kw:
            kw.pop('safe_create')
        if not kw.get('url', False):
            kw['url'] = ''
        if not kw.get('element_html', False):
            kw['element_html'] = ''
        kw['is_inbound'] = True
        
        for field in kw.keys():
            if field not in WebClick.fields:
                del kw[field]

        event = WebClickManager.create(self,  **kw)
        return event


class WebClick(Event):

    url = fields.StringField()
    element_html = fields.StringField()
    session_id = fields.StringField()

    manager = WebClickManager

    PROFILE_CLASS = WebProfile

    @classmethod
    def patch_post_kw(cls, kw):
        pass

    @property
    def platform(self):
        return 'Web'

    @property
    def post_type(self):
        return 'private'

    @property
    def _message_type(self):
        return 1

    @property
    def view_url_link(self):
        return "View the Comment"

    def to_dict(self, fields2show=None):
        base_dict = super(WebClick, self).to_dict()
        base_dict['actor'] = self.actor.to_dict()
        base_dict['content'] = 'URL: ' + self.url
        if self.element_html:
            base_dict['content'] += " HTML: " + self.element_html
        return base_dict


