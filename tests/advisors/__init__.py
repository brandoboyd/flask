
from solariat_bottle.db.schema_based import (
    KEY_IS_ID, KEY_NAME, KEY_TYPE, KEY_EXPRESSION, TYPE_INTEGER,
    TYPE_STRING, TYPE_BOOLEAN, TYPE_LIST, TYPE_DICT)
from solariat_bottle.schema_data_loaders.base import SchemaProvidedDataLoader

def setup_customer_schema(user):
    schema = list()
    schema.append({KEY_NAME: 'first_name',KEY_TYPE: TYPE_STRING, KEY_IS_ID: True})
    schema.append({KEY_NAME: 'last_name',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'age',KEY_TYPE: TYPE_INTEGER})
    schema.append({KEY_NAME: 'account_id',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'location',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'sex',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'account_balance',KEY_TYPE: TYPE_INTEGER})
    schema.append({KEY_NAME: 'last_call_intent',KEY_TYPE: TYPE_LIST})
    schema.append({KEY_NAME: 'num_calls',KEY_TYPE: TYPE_INTEGER})
    schema.append({KEY_NAME: 'seniority',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'assigned_labels',KEY_TYPE: TYPE_LIST})
    try:
        schema_entity = user.account.customer_profile.create(user, SchemaProvidedDataLoader(schema))
        schema_entity.update_schema(schema_entity.discovered_schema)
    except:
        schema_entity = user.account.customer_profile._get()
        schema_entity.update_schema(schema)
    schema_entity.apply_sync()
    schema_entity.accept_sync()

def setup_agent_schema(user):
    schema = list()
    schema.append({KEY_NAME: 'first_name',KEY_TYPE: TYPE_STRING, KEY_IS_ID: True})
    schema.append({KEY_NAME: 'last_name',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'age',KEY_TYPE: TYPE_INTEGER})
    schema.append({KEY_NAME: 'account_id',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'location',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'sex',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'skillset',KEY_TYPE: TYPE_LIST})
    schema.append({KEY_NAME: 'occupancy',KEY_TYPE: TYPE_INTEGER})
    schema.append({KEY_NAME: 'seniority',KEY_TYPE: TYPE_STRING})
    schema.append({KEY_NAME: 'products',KEY_TYPE: TYPE_LIST})
    schema.append({KEY_NAME: 'english_fluency',KEY_TYPE: TYPE_STRING})
    try:
        schema_entity = user.account.agent_profile.create(user, SchemaProvidedDataLoader(schema))
        schema_entity.update_schema(schema_entity.discovered_schema)
    except:
        schema_entity = user.account.agent_profile._get()
        schema_entity.update_schema(schema)
    schema_entity.apply_sync()
    schema_entity.accept_sync()
