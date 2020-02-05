from solariat.db.mongo import setup_db_connection
from solariat_bottle.settings import get_var

if not get_var('SIGNATURE_SECRET'):
    # disable pickle signature check in test environment
    from solariat.utils import signed_pickle
    signed_pickle.signed_pickle = signed_pickle._PackedPickle()

TEST_DB = get_var('DB_NAME')

assert get_var('APP_MODE') == 'test', \
            "Attempt to run test in '{}' app mode.".format(get_var('APP_MODE'))
setup_db_connection({"DB_NAME": TEST_DB, "TEST_DB_NAME": TEST_DB})

from solariat_nlp.sa_labels import SAType
SA_TYPES = [sa.title for sa in SAType.all()]
SA_NAMES = [sa.name  for sa in SAType.all()]
