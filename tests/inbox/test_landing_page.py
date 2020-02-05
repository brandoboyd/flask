import random
import json
import string

from solariat_bottle.tests.base import BaseCase, RestCase

from solariat_bottle.db.lpage import LandingPage

URL = 'http://www.solariat.com'

class LPageDbTest(BaseCase):
    def test_create_delete(self):
        lpage = LandingPage.objects.create_by_user(
            self.user, url=URL)
        self.assertEqual(
            LandingPage.objects.count(), 1)
        lpage.delete_by_user(self.user)
        self.assertEqual(
            LandingPage.objects.count(), 0)


class LPageRestTest(RestCase):

    def create(self, url=None):
        if url is None:
            url = URL
        return self.do_post('landingpages', version='v1.2', url = url)

    def test_create(self):
        " correct creation should return json with ok = True and UUID "
        resp = self.do_post('landingpages', version='v1.2', url = URL)
        self.assertEqual(resp['ok'], True)
        self.assertEqual(resp['item']['url'], URL)
        self.assertEqual(resp['item']['display_field'], None)

    def test_create_duplicate(self):
        """ create more than one landingpage with 
        the same url should return json with ok = False 

        """
        resp1 = self.create(URL)
        resp2 = self.create(URL)
        self.assertTrue(resp1['ok'])
        self.assertFalse(resp2['ok'])


    def test_bad_json(self):
        "raise error on bad formed json filter parameter"
        self.create("foo")
        resp = self.client.get(
            '/api/v1.2/landingpages?token=%s' % self.auth_token,
            data = "{'url':'baz}",
            content_type='application/json')
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])


    def test_get(self):
        "should return 0 or 1 for specific url"
        self.create('foo')
        self.create('bar')

        resp = self.do_get('landingpages', version='v1.2', url='foo')
        self.assertTrue(resp['ok'])
        self.assertEqual(len(resp['list']), 1)

        resp = self.do_get('landingpages', version='v1.2', url='baz')
        self.assertEqual(len(resp['list']), 0)


    def test_get_specific(self):
        " get specific landingpage "

        urls_count = random.randint(5, 10)
        for i in xrange(urls_count):
            self.create(URL + '/' + str(i))

        url = URL + '/' + str(random.randint(0, urls_count - 1))
        resp = self.do_get('landingpages', version='v1.2', url=url)
        self.assertEqual(resp['ok'], True)
        self.assertEqual(len(resp['list']), 1)
        self.assertEqual(resp['list'][0]['url'], url)

    def test_get_all(self):
        " get all landingpages "

        urls_count = random.randint(5, 10)
        for i in xrange(urls_count):
            self.create(URL + '/' + str(i))

        resp  = self.do_get('landingpages', version='v1.2')
        self.assertEqual(resp['ok'], True)
        self.assertEqual(len(resp['list']), urls_count)

    def test_delete_uuid(self):
        " delete specific landingpage using UUID "

        resp = self.create(URL)
        lpage_uuid = resp['item']['id']
        resp = self.do_delete('landingpages/%s' % lpage_uuid, version='v1.2')
        self.assertTrue(resp['ok'])

        resp = self.do_delete('landingpages/%s' % lpage_uuid, version='v1.2')
        self.assertFalse(resp['ok'])

    def test_delete_url(self):
        " delete specific landingpage using url "

        resp = self.create(URL)
        resp = self.do_delete('landingpages', url=URL, version='v1.2')
        self.assertEqual(resp['ok'], True)
        self.assertEqual(resp['message'], '1 docs was deleted, 0 rejected')

        resp = self.do_delete('landingpages', url=URL, version='v1.2')
        self.assertEqual(resp['ok'], True)
        self.assertEqual(resp['message'], '0 docs was deleted, 0 rejected')

    def test_weighted_fields(self):
        """make sure that randomly generated weighted_fields 
        restored back without change 
        """

        weighted_fields = []
        for _ in xrange(random.randint(1,5)):
            name = ''.join((random.choice(
                        string.letters + string.digits) for _ in xrange(
                        random.randint(5,10)) ))
            value = ''.join((random.choice(
                        string.letters + string.digits) for _ in xrange(
                        random.randint(5,10)) ))
            weight = random.random()
            weighted_fields.append({"name": name,
                                    "value": value,
                                   "weight": weight })

        resp = self.do_post(
            'landingpages', version='v1.2', url=URL, weighted_fields=weighted_fields)
        self.assertEqual(resp['ok'], True)
        self.assertEqual(resp['item']['weighted_fields'], weighted_fields)

    def test_missed_weight(self):
        " make sure that missed weight restored back with 1.0 value "

        name = ''.join((
                random.choice(
                    string.letters + string.digits) for _ in xrange(
                    random.randint(5,10)) ))
        value = ''.join((
                random.choice(
                    string.letters + string.digits) for _ in xrange(
                    random.randint(5,10)) ))
        weighted_fields = [ { 'name': name,
                             'value': value } ]
        resp = self.do_post('landingpages', version='v1.2', url=URL, weighted_fields=weighted_fields)
        self.assertEqual(resp['ok'], True)
        self.assertEqual(resp['item']['weighted_fields'][0]['weight'], 1.0)

    def test_archived(self):
        " test archiving capabilities "

        archived = []

        n = random.randint(3, 6)
        for i in xrange(n):
            url = "%s%s" % (URL, i)
            resp = self.create(url)
            archived.append(resp['item']['id'])
            self.do_delete('landingpages', version='v1.2', url=url)

        self.create()

        self.assertEqual(LandingPage.objects.find().count(), 1)
        self.assertEqual(LandingPage.objects.coll.count(), n + 1)

        lp_archived = random.choice(archived)

        stored_id = LandingPage.objects.get(id=lp_archived, 
                                            is_archived=True).id
        self.assertEqual(str(stored_id), lp_archived)

        self.assertRaises(LandingPage.DoesNotExist, 
                          LandingPage.objects.get, 
                          id=lp_archived)

    def test_mass_deletion(self):
        lpage1 = LandingPage.objects.create_by_user(self.user, 
                                                   url='solariat.com')
        lpage2 = LandingPage.objects.create_by_user(self.user, 
                                                   url='solariat1.com')
        LandingPage.objects.remove_by_user(self.user)
        self.assertTrue(LandingPage.objects.find_one(lpage1.id) is None)
        self.assertTrue(LandingPage.objects.find_one(lpage2.id) is None)
