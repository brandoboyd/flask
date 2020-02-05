from datetime import datetime
from flask import jsonify, render_template, request
from urllib import unquote

from solariat_bottle.db.dynamic_channel import ChannelType
from solariat_bottle.db.schema_based import (get_query_by_dates,
                                             NameDuplicatedError,
                                             apply_shema_type)
from solariat.utils import timeslot
from solariat_bottle.views.base import BaseMultiActionView, HttpResponse
from solariat_bottle.utils.views import required_fields
from solariat_bottle.settings import LOGGER
from solariat_bottle.app import app


KEY_NAME = 'name'
SCHEMA = 'schema'


class ChannelTypeView(BaseMultiActionView):

    url_rules = [
        ('/channel_type/create', ['POST'], 'create'),
        ('/channel_type/get/<path:name>', ['GET'], 'get'),
        ('/channel_type/update/<path:name>', ['POST'], 'update'),
        ('/channel_type/apply_sync/<path:name>', ['POST'], 'apply_sync'),
        ('/channel_type/delete/<path:name>', ['POST'], 'delete'),
        ('/channel_type/list', ['GET'], 'list'),
    ]

    def get_parameters(self):
        params = super(ChannelTypeView, self).get_parameters()
        if KEY_NAME in params:
            params[KEY_NAME] = unquote(params[KEY_NAME])
        return params

    def _get(self, name):
        return ChannelType.objects.find_one_by_user(self.user,
                                                    account=self.user.account,
                                                    name=name)

    @required_fields(KEY_NAME)
    def create(self, *args, **kwargs):
        kwargs['account'] = self.user.account
        channel_type = ChannelType.objects.create_by_user(self.user, **kwargs)
        return channel_type.to_dict()

    @required_fields(KEY_NAME)
    def update(self, *args, **kwargs):
        channel_type = self._get(kwargs[KEY_NAME])
        if not channel_type:
            return

        if kwargs.get(SCHEMA) != channel_type.schema:
            kwargs.update({'sync_status': ChannelType.OUT_OF_SYNC})
        channel_type.update(**kwargs)
        return channel_type.to_dict()

    @required_fields(KEY_NAME)
    def apply_sync(self, *args, **kwargs):
        channel_type = self._get(kwargs[KEY_NAME])
        sync_errors = channel_type.apply_sync(self.user)
        if sync_errors:
            return HttpResponse({'sync_errors': sync_errors}, ok=False, status=400)
        return {}

    @required_fields(KEY_NAME)
    def get(self, *args, **kwargs):
        channel_type = self._get(kwargs[KEY_NAME])
        return channel_type.to_dict()

    def list(self, *args, **kwargs):
        from_dt = to_dt = None
        if 'from' in kwargs:
            from_dt = timeslot.parse_datetime(kwargs['from'])
            to_dt = timeslot.parse_datetime(kwargs['to'])

        date_query = get_query_by_dates(from_dt, to_dt)
        channel_types = ChannelType.objects.find_by_user(self.user,
                                                         account=self.user.account,
                                                         **date_query)

        return [s.to_dict() for s in channel_types]

    @required_fields(KEY_NAME)
    def delete(self, *args, **kwargs):
        channel_type = self._get(kwargs[KEY_NAME])
        if not channel_type:
            return

        channel_type.delete_by_user(self.user, account=self.user.account, name=kwargs[KEY_NAME])
        return {}


ChannelTypeView.register(app)
