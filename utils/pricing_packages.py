'''
Utilities file to ensure the proper billing/pricing packages are in the DB
'''

from solariat_bottle.settings import LOGGER
from solariat_bottle.db.account import Package

def get_or_create_pricing_package(name, data):
    query_data = {'name': name}
    try:
        package = Package.objects.get(**query_data)
    except Package.DoesNotExist:
        #LOGGER.debug('Creating pricing package: {}'.format(name))
        data.update(query_data)
        package = Package.objects.create(**data)
    return package

PACKAGE_TYPES = {
                    'Internal': {'cost': 0, 'volume': -1, 'storage_time': -1},
                    'Bronze': {'cost': 500, 'volume': 5000, 'storage_time': 3},
                    'Silver': {'cost': 2000, 'volume': 25000, 'storage_time': 3},
                    'Gold': {'cost': 5000, 'volume': 75000, 'storage_time': 6},
                    'Platinum': {'cost': 10000, 'volume': 200000, 'storage_time': 13},
                    'Trial': {'cost': 0, 'volume': 500, 'storage_time': 1}
                }

#INTERNAL_ACCOUNT_TYPES = ["Native", "Salesforce", "HootSuite", "Skunkworks", "Angel"]

def ensure_pricing_packages():
    LOGGER.debug("Ensuring proper account pricing packages exist in DB")
    for account_name, account_data in PACKAGE_TYPES.iteritems():
        get_or_create_pricing_package(account_name, account_data)
