from .base import MainCase

import requests
from solariat.cipher.random import get_random_bytes

from mock import MagicMock

key = get_random_bytes(32).encode('hex')
keyname = 'secure_key'
REMOTE_KEYS = {'key1': 'val1',
               'key2': 'val2',
                keyname: key}


def keyserver_response(**kwargs):
    return {"ok": True, "keys": REMOTE_KEYS}


def get_stub(*args, **kwargs):
    print "In Mock", args, kwargs
    response = requests.get.return_value
    response.json = lambda: keyserver_response(**kwargs)
    return response


class KeyserverIntegrationTest(MainCase):
    def enable_and_sync(self):
        from solariat_bottle.app import app, sync_with_keyserver
        # Enable call to keyserver, simulate production environment
        app.config['KEYSERVER_CONFIG']['remote_sync_required'] = True
        sync_with_keyserver()

    def test_settings(self):
        """Should merge settings from remote server on startup"""
        requests_get = requests.get
        requests.get = MagicMock(side_effect=get_stub)

        from solariat_bottle.app import app
        ks_config = app.config['KEYSERVER_CONFIG'].copy()
        app.config['KEYSERVER_CONFIG']['host'] = 'test.keyserver.host'

        app.config[keyname] = key + 'not a remote key'
        self.enable_and_sync()

        for k, v in REMOTE_KEYS.items():
            self.assertEqual(app.config.get(k), v)

        requests.get = requests_get
        app.config['KEYSERVER_CONFIG'] = ks_config

    def test_key_sync_failure(self):
        from solariat_bottle.app import app
        from solariat.cipher.keystore import RemoteKeyServerError

        ks_config = app.config['KEYSERVER_CONFIG'].copy()
        app.config['KEYSERVER_CONFIG']['host'] = None
        with self.assertRaises(RemoteKeyServerError):
            self.enable_and_sync()
        app.config['KEYSERVER_CONFIG'] = ks_config