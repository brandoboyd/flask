from flask import request

from solariat.utils.timeslot import now
from solariat_bottle.app import app
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.views import parse_account, get_paging_params
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.views.base import BaseView
from solariat_bottle.api.exceptions import ResourceDoesNotExist, \
    DocumentDeletionError, ValidationError
from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType


class JourneyTypeView(BaseView):
    """Journey type management for account admin"""

    url_rules = [
        ('/journey_types/<id_>', ['GET', 'POST', 'PUT', 'DELETE']),
        ('/journey_types', ['GET', 'POST'])
    ]

    def get_parameters(self):
        data = _get_request_data()
        params = {}
        user = self.user
        account = parse_account(user, data)
        if account:
            params['account_id'] = account.id

        valid_parameters = ['display_name', 'description', 'journey_attributes_schema', 'mcp_settings']
        for param_name, param_value in data.iteritems():
            if hasattr(self.model, param_name) and param_name in valid_parameters:
                params[param_name] = param_value

        if request.method == 'GET':
            params.update(get_paging_params(data))

        return params

    @property
    def model(self):
        return JourneyType

    @property
    def manager(self):
        return JourneyType.objects

    def check_duplicate_display_name(self, **filters):
        id_ = filters.get('id_', filters.get('id'))
        duplicate = False
        if 'display_name' in filters:
            for journey_type in self.manager.find_by_user(
                    self.user,
                    display_name=filters['display_name']):
                if str(journey_type.id) != id_:
                    duplicate = True
        if duplicate:
            raise ValidationError(u"Journey Type with name '%(display_name)s' already exists" % filters)

    def get(self, id_=None, **filters):
        query = {}
        if id_:
            query['id'] = id_
        if filters.get('account_id'):
            query['account_id'] = filters['account_id']

        if id_:
            try:
                return self.manager.get_by_user(self.user, **query)
            except self.model.DoesNotExist:
                LOGGER.exception(__name__)
                raise ResourceDoesNotExist("Not found")
        else:
            return self.manager.find_by_user(self.user, **query).limit(filters['limit']).skip(filters['offset'])[:]

    def put(self, id_, **filters):
        from solariat_bottle.db.dynamic_event import run_or_restart_postprocessing

        try:
            item = self.manager.get_by_user(self.user, id=id_)
        except self.model.DoesNotExist:
            LOGGER.exception(__name__)
            raise ResourceDoesNotExist("Not found")
        self.check_duplicate_display_name(id=id_, **filters)
        filters.update({'updated_at': now()})
        item.update(**filters)

        msg = 'Journey updated, resync flag is set on account: %s.' % self.user.account
        run_or_restart_postprocessing(self.user, msg)

        return item

    def post(self, **filters):
        if 'id_' in filters:
            return self.put(**filters)
        self.check_duplicate_display_name(**filters)
        item = self.manager.create_by_user(self.user, **filters)

        if item and item.available_stages:
            from solariat_bottle.db.dynamic_event import run_or_restart_postprocessing
            msg = ('Journey created with stages: %s \n'
                   'resync flag is set on account: %s.' % (item.available_stages,
                                                           self.user.account))
            run_or_restart_postprocessing(self.user, msg)

        return item

    def delete(self, id_, **filters):
        from solariat_bottle.db.dynamic_event import run_or_restart_postprocessing

        try:
            res = self.manager.remove_by_user(self.user, id=id_)
            msg = 'Journey removed, resync flag is set on account: %s.' % self.user.account
            run_or_restart_postprocessing(self.user, msg)
            return res
        except:
            raise DocumentDeletionError(id_)


class JourneyStageTypeView(BaseView):
    url_rules = [
        ('/journey_types/<jt_id>/stages/<id_>', ['GET', 'POST', 'PUT', 'DELETE']),
        ('/journey_types/<jt_id>/stages', ['GET', 'POST'])
    ]

    def dispatch_request(self, *args, **kwargs):
        self.user = kwargs.get('user', None)
        try:
            self.journey_type = JourneyType.objects.get_by_user(self.user, kwargs.pop('jt_id'))
        except JourneyType.DoesNotExist:
            raise ResourceDoesNotExist("JourneyType not found")

        kwargs.update(self.get_parameters())
        return super(JourneyStageTypeView, self).dispatch_request(*args, **kwargs)

    def get_parameters(self):
        params = super(JourneyStageTypeView, self).get_parameters()

        params['strategy'] = None

        return {name: value for name, value in params.iteritems() if name in self.model.fields}

    @property
    def model(self):
        return JourneyStageType

    def post(self, **data):
        if 'id_' in data:
            data['id'] = data.pop('id_')
        stage, error = self.journey_type.create_update_stage(self.model(**data))
        if not error:
            return stage
        raise ValidationError(error)

    def get(self, id_=None, **data):
        if id_:
            stage = self.journey_type.find_stage(id_)
            if stage:
                return stage
            else:
                raise ResourceDoesNotExist('Not found')
        else:
            return self.journey_type.available_stages

    def put(self, id_, **data):
        data['id'] = id_
        return self.post(**data)

    def delete(self, id_, **kwargs):
        error = self.journey_type.remove_stage(id_)
        if not error:
            return None
        raise DocumentDeletionError(error)


JourneyTypeView.register(app)
JourneyStageTypeView.register(app)
