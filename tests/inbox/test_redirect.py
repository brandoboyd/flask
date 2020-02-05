""" Test construction for post/matchable response
"""

from solariat_bottle.utils.redirect import gen_creative, fetch_url
from solariat_bottle.utils.bitly    import generate_shortened_url
import unittest

from solariat_bottle.tests.base import MainCase


class RedirectTest(MainCase):

    def setUp(self):
        MainCase.setUp(self)


    @unittest.skip("No connection")
    def test_url_extraction(self):
        'Make sure to not include the exclamation mark.'

        creative = gen_creative(self.matchable, self.response)
        self.assertEqual(creative.find('!'), len(creative) - 1)
        self.assertTrue(creative.find('www') == -1)

    @unittest.skip("No connection")
    def test_shorten_bug(self):
        landing_page = fetch_url("Check out http://www.laptops.com?utm_source=solariat")
        self.assertEqual(landing_page, "http://www.laptops.com?utm_source=solariat")
        shortened = generate_shortened_url("http://www.laptops.com?utm_source=solariat")
        self.assertEqual(shortened.find("http"), 0)

    """
    def test_wells_fargo_bug(self):
        m = Matchable(
            creative="Check Out foo at https://www.wellsfargocommunity.com/thread/2082?tstart=120")
        m.save()
        post = self._create_db_post("I need foo")
        postmatch = PostMatch(
            post=post, channels=[self.channel_id])
        postmatch.save()

        # We can generate the creative for outbound...
        with app.test_request_context('/'):
            creative = gen_creative(m, postmatch)

        # We can properly do the response redirect
        resp = self.client.get('/redirect/%s/%s' % (
                   str(postmatch.id),
                   str(m.id)))

        self.assertEqual(resp.location, 'https://www.wellsfargocommunity.com/thread/2082?tstart=120&utm_source=solariat')

    def test_click_update(self):
        with app.test_request_context('/'):
            do_redirect(self.postmatch.id, self.matchable.id)
        self.assertEqual(PostClick.objects.count(), 1)
        self.assertEqual(ChannelStats.objects()[0].number_of_clicks, 1)

    def test_redirect(self):
        resp = self.client.get('/redirect/%s/%s' % (
                   str(self.postmatch.id),
                   str(self.matchable.id))
        )
        self.assertEqual(resp.location, 'http://www.foo.com/bar?utm_source=solariat')
    """

    def test_fetch_url(self):
        data = [
            ('Check Out http://www.foo.com/bar! ', 'http://www.foo.com/bar'),
            ('Check Out http://foo.com/bar!a', 'http://foo.com/bar!a'),
            ('Check Out www.foo.com/bar? next', 'www.foo.com/bar'),
            ('Check Out https://www.foo.com/bar? next', 'https://www.foo.com/bar'),
        ]
        for (creative, url) in data:
            self.assertEqual(fetch_url(creative), url)
