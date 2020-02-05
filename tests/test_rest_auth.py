"Test that auth via API works"

import json

from .base import RestCase
from ..db.user import User

class RestAuthCase(RestCase):
    def test_auth(self):
        user = User.objects.create(email='testme@solariat.com',
                                   password='12345')
        resp = self.client.post(
            '/api/v1.2/authtokens',
            data=json.dumps({"username":"testme@solariat.com",
                            "password":"12345"}))
        self.assertTrue(resp.status, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'], data.get('error'))
                               
