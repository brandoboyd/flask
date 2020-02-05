from itsdangerous import URLSafeSerializer

from solariat_bottle.settings import UNSUBSCRIBE_KEY, UNSUBSCRIBE_SALT
from solariat_bottle.tests.slow.test_smarttags import SmartTagsBaseCase
from solariat_bottle.tests.base import UICase, fake_twitter_url


class UnsubscribeTestCase(SmartTagsBaseCase, UICase):

    def setUp(self):
        super(UnsubscribeTestCase, self).setUp()
        self.i = self.sc.inbound_channel
        self.o = self.sc.outbound_channel
        self.o.usernames = ['solariat']
        self.o.save()

        # Create 2 Smart Tags, for different use keywords
        self.laptop_tag = self._create_smart_tag(self.i, 'Laptops Tag', status='Active', keywords=['laptop'])
        self.laptop_tag_outbound = self._create_smart_tag(self.o, 'Laptops Tag', status='Active', keywords=['laptop'])
        self.other_tag = self._create_smart_tag(self.i, 'Other Tag', status='Active', keywords=['support', 'help'])
        self.other_tag_outbound = self._create_smart_tag(self.o, 'Other Tag', status='Active', keywords=['support', 'help'])

        url = fake_twitter_url(self.customer.user_name)


    def test_unsubscribe(self):
        # unsubscribe view exists
        resp = self.client.get('/unsubscribe/tag/incorrecthash')
        self.assertEqual(resp.status_code, 404)

        # correct parameters unsubscribe
        user_email = self.user.email
        self.laptop_tag.alert_emails = [user_email]
        self.laptop_tag.save()
        self.laptop_tag.reload()
        self.assertEqual(len(self.laptop_tag.alert_emails), 1)
        tag_id = str(self.laptop_tag.id)
        user_id = str(self.user.id)
        s = URLSafeSerializer(UNSUBSCRIBE_KEY, UNSUBSCRIBE_SALT)
        email_tag_id = s.dumps((user_email, tag_id))
        resp = self.client.get('/unsubscribe/tag/{}'.format(email_tag_id))
        self.assertEqual(resp.status_code, 200)
        self.laptop_tag.reload()
        self.assertEqual(len(self.laptop_tag.alert_emails), 0)
