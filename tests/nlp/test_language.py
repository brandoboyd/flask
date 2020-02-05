from solariat.db.abstract import Document
from solariat_bottle.db.language import AllLanguageChannelMixin
from solariat_bottle.tests.base import BaseCase, UICaseSimple


class FakeDoc(Document, AllLanguageChannelMixin):
        pass

class TestLangMixin(BaseCase):

    def test_all_lang_mixin(self):

        mixin = FakeDoc()
        self.assertEqual(len(mixin.langs), 3)
        self.assertTrue('en' in mixin.langs and 'es' in mixin.langs and 'fr' in mixin.langs)


class TestViews(UICaseSimple):
    TWITTER_LANGUAGES_RESPONSE = [
        {u'status': u'production', u'code': u'fr', u'name': u'French'},
        {u'status': u'production', u'code': u'en', u'name': u'English'},
        {u'status': u'production', u'code': u'ar', u'name': u'Arabic'},
        {u'status': u'production', u'code': u'ja', u'name': u'Japanese'},
        {u'status': u'production', u'code': u'es', u'name': u'Spanish'},
        {u'status': u'production', u'code': u'de', u'name': u'German'},
        {u'status': u'production', u'code': u'it', u'name': u'Italian'},
        {u'status': u'production', u'code': u'id', u'name': u'Indonesian'},
        {u'status': u'production', u'code': u'pt', u'name': u'Portuguese'},
        {u'status': u'production', u'code': u'ko', u'name': u'Korean'},
        {u'status': u'production', u'code': u'tr', u'name': u'Turkish'},
        {u'status': u'production', u'code': u'ru', u'name': u'Russian'},
        {u'status': u'production', u'code': u'nl', u'name': u'Dutch'},
        {u'status': u'production', u'code': u'fil', u'name': u'Filipino'},
        {u'status': u'production', u'code': u'msa', u'name': u'Malay'},
        {u'status': u'production', u'code': u'zh-tw', u'name': u'Traditional Chinese'},
        {u'status': u'production', u'code': u'zh-cn', u'name': u'Simplified Chinese'},
        {u'status': u'production', u'code': u'hi', u'name': u'Hindi'},
        {u'status': u'production', u'code': u'no', u'name': u'Norwegian'},
        {u'status': u'production', u'code': u'sv', u'name': u'Swedish'},
        {u'status': u'production', u'code': u'fi', u'name': u'Finnish'},
        {u'status': u'production', u'code': u'da', u'name': u'Danish'},
        {u'status': u'production', u'code': u'pl', u'name': u'Polish'},
        {u'status': u'production', u'code': u'hu', u'name': u'Hungarian'},
        {u'status': u'production', u'code': u'fa', u'name': u'Persian'},
        {u'status': u'production', u'code': u'he', u'name': u'Hebrew'},
        {u'status': u'production', u'code': u'th', u'name': u'Thai'},
        {u'status': u'production', u'code': u'uk', u'name': u'Ukrainian'},
        {u'status': u'production', u'code': u'cs', u'name': u'Czech'},
        {u'status': u'production', u'code': u'ro', u'name': u'Romanian'},
        {u'status': u'production', u'code': u'en-gb', u'name': u'British English'},
        {u'status': u'production', u'code': u'vi', u'name': u'Vietnamese'},
        {u'status': u'production', u'code': u'bn', u'name': u'Bengali'}]
    METHOD_NAME = 'supported_languages'

    def test_support(self):
        from solariat.tests.base import LoggerInterceptor
        with LoggerInterceptor() as logs:
            from solariat.utils.lang.helper import build_lang_map
            lang_map = build_lang_map([lang['code'] for lang in self.TWITTER_LANGUAGES_RESPONSE])
            self.assertFalse(logs)

    def test_languages_all_json(self):
        self.login()

        from mock import patch, PropertyMock, MagicMock
        with patch('tweepy.API.%s' % self.METHOD_NAME, new_callable=MagicMock) as get_languages:
            get_languages.return_value = self.TWITTER_LANGUAGES_RESPONSE

            twitter_langs = self._get('/languages/all/json', {'languageSet': 'twitter'})

        all_langs = self._get('/languages/all/json', {'languageSet': 'all'})
        all_langs_no_params = self._get('/languages/all/json', {})
        self.assertEqual(all_langs, all_langs_no_params)

        def get_lang_codes(resp):
            return set([lang_dict['code'] for lang_dict in resp['list']])

        self.assertTrue(get_lang_codes(twitter_langs) <= get_lang_codes(all_langs) | {'fil'},  # Note: we don't detect Filipino
                        "%s is not a subset of %s" % (get_lang_codes(twitter_langs), get_lang_codes(all_langs)))
