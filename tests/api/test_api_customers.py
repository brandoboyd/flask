import json
from solariat_bottle.tests.base import RestCase, setup_customer_schema

class APICustomersCase(RestCase):

    def setUp(self):
        super(APICustomersCase, self).setUp()
        setup_customer_schema(self.user)
        
        self.phone = '16509674312'
        CustomerProfile = self.account.get_customer_profile_class()
        self.customer = CustomerProfile.objects.create_by_user(
            user=self.user, phone=str(int(self.phone)))
        self.token = self.get_token()

    def test_get(self):
        data = {'phone': '16509674312',
                'token': self.token}
        resp = self.client.get('/api/v2.0/customers',
            data=json.dumps(data),
            content_type='application/json',
            base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertNotEqual(data['item'], None)
        #self.assertEqual(data['item']['id'], str(self.customer.id))

        data = {'phone': '111111111111', 'token': self.token}
        resp = self.client.get('/api/v2.0/customers',
            data=json.dumps(data),
            content_type='application/json',
            base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], "No customer found with info {u'phone': u'111111111111'}")
