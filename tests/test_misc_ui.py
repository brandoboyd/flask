# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import json
from .base import UICase


class TestMiscCase(UICase):

    def setUp(self):
        UICase.setUp(self)
        self.login()

    def _fetch(self, data):
        resp = self.client.post('/channels/json',
                                data=data,
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))
        return resp

    def test_get_channels(self):
        resp = self._fetch(json.dumps({}))
        self.assertEqual([c['title'] for c in resp['list']], ['TestChannel_Old'])
