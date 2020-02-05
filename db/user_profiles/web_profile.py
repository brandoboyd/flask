from solariat.db import fields
from solariat.exc.base import AppException

from .base_platform_profile import UserProfile, UserProfileManager


class WebProfileManager(UserProfileManager):
    '''Wraps access with encoded key'''

    def create_by_user(self,
            user,
            session_id,
            browser_signature=None,
            browser_cookie=None,
            user_id=None,
            platform_data=None):

        obj = None
        if obj is None and user_id:
            try:
                obj = WebProfile.objects.get(user_id=user_id)
            except WebProfile.DoesNotExist:
                pass

        if obj is None and session_id:
            try:
                obj = WebProfile.objects.get(sessions__in=[session_id])
            except WebProfile.DoesNotExist:
                pass

        if obj is None and browser_signature:
            try:
                obj = WebProfile.objects.get(browser_signatures__in=[browser_signature])
            except WebProfile.DoesNotExist:
                pass

        if obj is None and browser_cookie:
            try:
                obj = WebProfile.objects.get(browser_cookies__in=[browser_cookie])
            except WebProfile.DoesNotExist:
                pass

        if obj is None:
            if (user_id is None and browser_signature is None
                            and browser_cookie is None and session_id is None):
                raise AppException("No unique way to identify the profile. Either %s, %s or %s needs to be present" %
                                   ("browser_signature", "browser_cookie", "session_id"))
            obj = WebProfile.objects.create(
                user_id=user_id,
                browser_signatures=[browser_signature] if browser_signature else [],
                browser_cookies=[browser_cookie] if browser_cookie else [],
                sessions=[session_id] if session_id else [],
            )

        obj.save()

        if browser_signature and browser_signature not in obj.browser_signatures:
            obj.browser_signatures.append(browser_signature)

        if browser_cookie and browser_cookie not in obj.browser_cookies:
            obj.browser_cookies.append(browser_cookie)

        if platform_data is not None:
            obj.platform_data = platform_data
        obj.save()

        return obj


class WebProfile(UserProfile):
    sessions = fields.ListField(fields.StringField())
    user_id = fields.StringField()
    browser_cookies = fields.ListField(fields.StringField())
    browser_signatures = fields.ListField(fields.StringField())

    manager = WebProfileManager

