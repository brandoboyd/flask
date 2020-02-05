# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

# we later import from solariat_bottle.db instead of mongo
# so NOQA for flake8 to ignore the warning
from solariat.db.mongo import setup_db_connection, get_connection, set_connection, get_shards, get_all_hosts  # NOQA

from solariat_bottle.settings import get_var
_db_settings = ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_POOL_SIZE')
setup_db_connection(dict(zip(_db_settings, map(get_var, _db_settings))))
