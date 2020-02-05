"""
Language related mixins.
"""

from solariat.db import fields
from solariat.utils.lang.support import get_lang_id, LangCode, get_supported_languages, FULL_SUPPORT


class LanguageMixin(object):
    _lang_code = fields.StringField(db_field='lnc', default=LangCode.EN)

    @property
    def language(self):
        return self._lang_code

    @property
    def lang_id(self):
        return get_lang_id(self.language)


class MultilanguageChannelMixin(object):

    langs = fields.ListField(fields.StringField(), default=[LangCode.EN])
    post_langs = fields.ListField(fields.StringField(), default=[])

    def add_post_lang(self, post):
        code = post.language
        if code not in self.post_langs:
            self.post_langs.append(code)
            self.save()


class AllLanguageChannelMixin(MultilanguageChannelMixin):

    langs = fields.ListField(fields.StringField(), default=get_supported_languages(FULL_SUPPORT))
