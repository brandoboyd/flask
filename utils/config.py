from solariat_bottle import settings


class SettingsProxy(object):
    """ Simple proxy to combine solariat_bottle.settings with Flask.config
    """
    def __init__(self, config):
        self._config = config

    def __getitem__(self, name):
        null = object()
        item = settings.get_var(name, null)
        if item is null:
            item = self._config[name]
        return item

    def __setitem__(self, name, item):
        setattr(settings, name, item)
        self._config[name] = item

    def get(self, name, default=None):
        null = object()
        item = settings.get_var(name, null)
        if item is null:
            item = self._config.get(name, default)
        return item

    def iteritems(self):
        keys = set(vars(settings)) | set(vars(self._config))
        return ((key, self.get(key)) for key in keys)

    def iterkeys(self):
        return (key for key,_ in self.iteritems())

    def itervalues(self):
        return (val for _,val in self.itervalues())


def sync_with_keyserver():
    from solariat.cipher.keystore import secure_storage, RemoteKeyServerError
    get_var = settings.get_var

    secure_storage.configure(
        storage_proxy=SettingsProxy({}),
        key_field='AES_KEY_256',
        keyserver_config=get_var('KEYSERVER_CONFIG'))

    try:
        secure_storage.keyserver_sync()
    except RemoteKeyServerError as e:
        settings.LOGGER.critical(unicode(e), exc_info=True)
        raise

    if get_var('APP_MODE') == 'prod' \
            and get_var('KEYSERVER_CONFIG', {}).get('remote_sync_required', True):
        assert get_var('AES_KEY_256') != get_var('TEST_AES_KEY_256'), \
            "The key was not updated"