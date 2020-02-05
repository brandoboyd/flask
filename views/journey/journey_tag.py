from flask import request, jsonify
from solariat.db import fields
from solariat_bottle.app import app
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.views import parse_account, get_paging_params
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.views.journey.journey_type import BaseView
from solariat_bottle.db.journeys.journey_tag import JourneyTag
from solariat_bottle.api.exceptions import ResourceDoesNotExist, \
        DocumentDeletionError, ValidationError


class JourneyTagView(BaseView):
    url_rules = [
            ('/journey_tags', ['GET', 'POST']),
            ('/journey_tags/<id_>', ['GET', 'POST', 'PUT', 'DELETE']),
    ]

    @property
    def model(self):
        return JourneyTag

    @property
    def valid_parameters(self):
        return [
            'id', 'journey_type_id', 'display_name', 'description', 
            'tracked_stage_sequences', 'tracked_customer_segments', 
            'nps_range', 'csat_score_range', 'key_smart_tags',
            'skip_smart_tags'
        ]

    @property
    def manager(self):
        return self.model.objects

    def get_parameters(self):
        data = _get_request_data()
        params = {}
        account = parse_account(self.user, data)
        if account:
            params['account_id'] = account.id

        for param_name, param_value in data.iteritems():
            if hasattr(self.model, param_name) and param_name in self.valid_parameters:

                field = getattr(self.model, param_name)
                if isinstance(field, fields.ObjectIdField):
                    param_value = fields.ObjectId(param_value)
                elif isinstance(field, fields.ListField) and isinstance(field.field, fields.ObjectIdField):
                    param_value = map(fields.ObjectId, param_value)

                params[param_name] = param_value

        if request.method == 'GET':
            params.update(get_paging_params(data))

        return params

    def check_duplicate_display_name(self, **filters):
        id_ = filters.get('id_', filters.get('id'))
        duplicate = False
        if 'display_name' in filters:
            for obj in self.manager.find_by_user(
                    self.user,
                    display_name=filters['display_name'],
                    journey_type_id=filters['journey_type_id']):
                if obj.id != id_:
                    duplicate = True
        if duplicate:
            raise ValidationError(u"{m.__name__} with name '{display_name}' already exists".format(m=self.model, **filters))

    def get(self, id_=None, **filters):
        limit = filters.pop('limit')
        offset = filters.pop('offset')

        if id_:
            filters['id'] = id_
            try:
                return self.manager.get_by_user(self.user, **filters)
            except self.model.DoesNotExist:
                LOGGER.exception(__name__)
                raise ResourceDoesNotExist("Not found")
        else:
            filters['account_id'] = self.user.account.id
            res = self.manager.find_by_user(self.user, **filters).limit(limit).skip(offset)[:]
            return res

    def post(self, **filters):
        if 'id' in filters:
            filters['id_'] = filters.pop('id')
        if 'id_' in filters:
            return self.put(**filters)
        self.check_duplicate_display_name(**filters)
        return self.manager.create_by_user(self.user, **filters)

    def put(self, id_, **filters):
        try:
            item = self.manager.get_by_user(self.user, id=id_)
        except self.model.DoesNotExist:
            LOGGER.exception(__name__)
            raise ResourceDoesNotExist("Not found")
        self.check_duplicate_display_name(id=id_, **filters)
        item.update(**filters)
        return item

    def delete(self, id_, **filters):
        try:
            return self.manager.remove_by_user(self.user, id=id_)
        except:
            raise DocumentDeletionError(id_)


JourneyTagView.register(app)
