from flask import request
from solariat.db import fields
from solariat.decorators import class_property
from solariat_bottle.app import app
from solariat_bottle.db.funnel import Funnel
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.views.base import BaseView


class FunnelView(BaseView):
    url_rules = [
            ('/funnels', ['GET', 'POST']),
            ('/funnels/<funnel_id>', ['GET', 'PUT', 'DELETE']),
    ]

    @class_property
    def view_decorator(cls):
        return login_required

    @property
    def valid_parameters(self):
        col_keys = set(Funnel.fields.keys())
        read_only_keys = {'owner', 'created'}
        return col_keys - read_only_keys

    def get_parameters(self):
        data = _get_request_data()

        params = {}
        # since funnels are account specific and not user specific
        if request.method == 'POST':
            params['owner'] = self.user

        for key, value in data.iteritems():
            if hasattr(Funnel, key) and key in self.valid_parameters:

                field = getattr(Funnel, key)
                if isinstance(field, fields.ObjectIdField):
                    value = fields.ObjectId(value)
                elif isinstance(field, fields.ListField) and isinstance(field.field, fields.ObjectIdField):
                    value = map(fields.ObjectId, value)

                params[key] = value

        return params

    def get(self, funnel_id=None, **filters):
        if funnel_id is None:
            # fetch list of funnel
            funnels = list(Funnel.objects.find_by_user(self.user, **filters))
            return [f.to_dict() for f in funnels]
        else:
            # fetch specific funnel
            funnel = Funnel.objects.get_by_user(self.user, id=funnel_id, **filters)
            rv = funnel.to_dict()
            return rv

    def post(self, **data):
        """Creates a funnel
        """
        if 'id' in data:
            return self.put(data['id'], **data)

        funnel = Funnel.objects.create_by_user(self.user, **data)
        return funnel

    def put(self, funnel_id, **data):
        funnel = Funnel.objects.get_by_user(self.user, id=funnel_id)

        for k, v in data.iteritems():
            setattr(funnel, k, v)

        funnel.save()
        return funnel

    def delete(self, funnel_id, **filters):
        funnel = Funnel.objects.get_by_user(self.user, id=funnel_id, **filters)
        funnel.delete()


FunnelView.register(app)
