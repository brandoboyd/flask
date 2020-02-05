
from solariat_bottle.tests.base import UICase
from solariat_bottle.db.roles import AGENT


HTTP_OK       = 200
HTTP_REDIRECT = 302
HTTP_UNAUTH   = 401


class BasePlaygroundCase(UICase):

    def setUp(self):
        super(BasePlaygroundCase, self).setUp()
        # create users
        new_user = self._create_db_user
        self.normaluser = new_user(email='normaluser@yahoo.com',   password='12345', roles=[AGENT])
        self.superuser  = new_user(email='superuser@gmail.com',    password='12345', is_superuser=True)
        self.staffuser  = new_user(email='staffuser@solariat.com', password='12345', roles=[AGENT])

    def _get(self, url, follow_redirects=False):
        return self.client.get(url, follow_redirects=follow_redirects)

    def _post(self, url, data={}, follow_redirects=False):
        return self.client.post(url, data=data, follow_redirects=follow_redirects)


class TestPlaygroundAccessCase(BasePlaygroundCase):

    def test_default_redirect(self):
        GET  = self._get
        resp = GET('/test/playground')
        self.assertEqual(resp.status_code, HTTP_REDIRECT)
        self.assertTrue(resp.location.endswith('/login?next=%2Ftest%2Fplayground'))

    def test_login_required(self):
        GET  = self._get
        POST = self._post

        # -- no user -- 

        resp = GET('/test/playground/chunker')
        self.assertEqual(resp.status_code, HTTP_REDIRECT)
        self.assertTrue(resp.location.endswith('/login?next=%2Ftest%2Fplayground%2Fchunker'))

        resp = POST('/test/playground/chunker')
        self.assertEqual(resp.status_code, HTTP_REDIRECT)
        self.assertTrue(resp.location.endswith('/login?next=%2Ftest%2Fplayground%2Fchunker'))

        resp = GET('/test/playground/tagger')
        self.assertEqual(resp.status_code, HTTP_REDIRECT)
        self.assertTrue(resp.location.endswith('/login?next=%2Ftest%2Fplayground%2Ftagger'))

        resp = POST('/test/playground/tagger')
        self.assertEqual(resp.status_code, HTTP_REDIRECT)
        self.assertTrue(resp.location.endswith('/login?next=%2Ftest%2Fplayground%2Ftagger'))

        # -- normal user --

        self.login(user=self.normaluser)

        resp = GET('/test/playground')
        self.assertFalse(resp.status_code == HTTP_OK)

        resp = GET('/test/playground/chunker')
        self.assertFalse(resp.status_code == HTTP_OK)

        resp = POST('/test/playground/chunker')
        self.assertFalse(resp.status_code == HTTP_OK)

        resp = GET('/test/playground/tagger')
        self.assertFalse(resp.status_code == HTTP_OK)

        resp = POST('/test/playground/tagger')
        self.assertFalse(resp.status_code == HTTP_OK)

        self.logout()

        # -- super user --

        self.login(user=self.superuser)

        resp = GET('/test/playground')
        self.assertEqual(resp.status_code, HTTP_REDIRECT)

        resp = GET('/test/playground/chunker')
        self.assertEqual(resp.status_code, HTTP_OK)

        resp = POST('/test/playground/chunker')
        self.assertEqual(resp.status_code, HTTP_OK)

        resp = GET('/test/playground/tagger')
        self.assertEqual(resp.status_code, HTTP_OK)

        resp = POST('/test/playground/tagger')
        self.assertEqual(resp.status_code, HTTP_OK)

        self.logout()

        # -- staff or admin user --

        self.login(user=self.staffuser)

        resp = GET('/test/playground/chunker')
        self.assertFalse(resp.status_code == HTTP_OK)

        resp = POST('/test/playground/chunker')
        self.assertFalse(resp.status_code == HTTP_OK)

        resp = GET('/test/playground/tagger')
        self.assertFalse(resp.status_code == HTTP_OK)

        resp = POST('/test/playground/tagger')
        self.assertFalse(resp.status_code == HTTP_OK)

        self.logout()


class TestPlaygroundCase(BasePlaygroundCase):
    ''' Test the endpoints. No need to retest for accuracy of algorithms.'''

    def test_chunker(self):
        self.login(user=self.superuser)
        POST = self._post

        data = dict(content='Who is on duty today? Will it rain?')
        resp = POST('/test/playground/chunker', data)
        self.assertEqual(resp.status_code, HTTP_OK)
        #self.assertTrue('(NOUNS rain/NN_rain)' in resp.data, resp.data)

    def test_tagger(self):
        self.login(user=self.superuser)
        POST = self._post

        data = dict(content='Who is on duty today? Will it rain?')
        resp = POST('/test/playground/tagger', data)
        self.assertEqual(resp.status_code, HTTP_OK)
        #self.assertTrue('duty/NN' in resp.data, resp.data)

