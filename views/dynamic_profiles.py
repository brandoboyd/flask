from datetime import datetime

from solariat_bottle.views.base import BaseMultiActionView
from solariat_bottle.settings import LOGGER
from solariat_bottle.app import app
from solariat_bottle.schema_data_loaders.csv import CsvDataLoader
from solariat_bottle.schema_data_loaders.base import WrongFileExtension

from urllib import unquote


KEY_NAME = 'name'


class DynamicProfileView(BaseMultiActionView):

    ENDPOINT = None
    ACC_DYN_MANAGER_NAME = None

    url_rules = [
        ('/create', ['POST'], 'create'),
        ('/update', ['POST'], 'update'),
        ('/get', ['GET'], 'get'),
        ('/delete', ['POST'], 'delete'),
        ('/view/<field_name>', ['GET'], 'view_data'),

        ('/update_schema', ['POST'], 'update_schema'),
        ('/sync/apply', ['POST'], 'apply_sync'),
        ('/sync/accept', ['POST'], 'accept_sync'),
        ('/sync/cancel', ['POST'], 'cancel_sync'),
    ]

    def view_data(self, field_name, skip=0, limit=20):
        acc = self.user.account
        skip = int(skip)
        limit = min(int(limit), 100)

        manager = getattr(self.user.account, self.ACC_DYN_MANAGER_NAME)
        profile = manager.get(self.user)
        if not profile:
            return {}

        data_coll = profile.data_coll
        total_items = data_coll.count()
        result = (data_coll.find({}, {field_name: 1, '_id': 0})
                           .sort('_id', 1)
                           .skip(skip)
                           .limit(limit))
        values = [d[field_name] for d in result]

        if values and isinstance(values[0], datetime):
            for i in xrange(len(values)):
                values[i] = values[i].ctime()

        return {
                'list': values,
                'skip': skip,
                'limit': limit,
                'total_items': total_items,
        }

    def get_parameters(self):
        params = super(DynamicProfileView, self).get_parameters()
        if KEY_NAME in params:
            params[KEY_NAME] = unquote(params[KEY_NAME])
        return params

    @classmethod
    def patch_urls(cls):
        cls.url_rules = [(cls.ENDPOINT + url, meth, act) for url, meth, act in cls.url_rules]

    def create(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        if not csv_file.filename.endswith('.csv'):
            raise WrongFileExtension('Wrong file extension, only .csv is supported.')

        sep = kwargs['sep']
        data_loader = CsvDataLoader(csv_file.stream, sep=sep)

        manager = getattr(self.user.account, self.ACC_DYN_MANAGER_NAME)
        profile = manager.create(self.user, data_loader)
        return profile.to_dict()

    def update(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        if not csv_file.filename.endswith('.csv'):
            raise WrongFileExtension('Wrong file extension, only .csv is supported.')

        sep = kwargs['sep']
        data_loader = CsvDataLoader(csv_file.stream, sep=sep)

        manager = getattr(self.user.account, self.ACC_DYN_MANAGER_NAME)
        profile = manager.update(self.user, data_loader)
        if not profile:
            return

        return profile.to_dict()

    def get(self, *args, **kwargs):
        manager = getattr(self.user.account, self.ACC_DYN_MANAGER_NAME)
        profile = manager.get(self.user)
        if not profile:
            return {}

        return profile.to_dict(include_cardinalities=True)

    def delete(self, *args, **kwargs):
        manager = getattr(self.user.account, self.ACC_DYN_MANAGER_NAME)
        if not manager.delete(self.user):
            return

        return {}
    
    def update_schema(self, *args, **kwargs):
        manager = getattr(self.user.account, self.ACC_DYN_MANAGER_NAME)
        profile = manager.get(self.user)
        if not profile:
            return

        profile.update_schema(kwargs['schema'])
        return {}

    def apply_sync(self, *args, **kwargs):
        manager = getattr(self.user.account, self.ACC_DYN_MANAGER_NAME)
        profile = manager.get(self.user)
        if not profile:
            return

        manager.apply_sync(profile)
        return profile.to_dict()

    def accept_sync(self, *args, **kwargs):
        '''Accept last sync, move :sync_status from SYNCED to IN_SYNC'''

        manager = getattr(self.user.account, self.ACC_DYN_MANAGER_NAME)
        profile = manager.get(self.user)
        if not profile:
            return

        profile.accept_sync()
        return profile.to_dict()

    def cancel_sync(self, *args, **kwargs):
        '''Cancel last sync, move :sync_status from SYNCED to OUT_OF_SYNC'''

        manager = getattr(self.user.account, self.ACC_DYN_MANAGER_NAME)
        profile = manager.get(self.user)
        if not profile:
            return

        profile.cancel_sync()
        return profile.to_dict()


class CustomerProfileView(DynamicProfileView):
    ENDPOINT = '/customer_profile'
    ACC_DYN_MANAGER_NAME = 'customer_profile'


class AgentProfileView(DynamicProfileView):
    ENDPOINT = '/agent_profile'
    ACC_DYN_MANAGER_NAME = 'agent_profile'


CustomerProfileView.patch_urls()
CustomerProfileView.register(app)
AgentProfileView.patch_urls()
AgentProfileView.register(app)
