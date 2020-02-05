from solariat.db import fields
from solariat.decorators import class_property
from solariat.exc.base import AppException
from solariat_bottle.app import app
from solariat_bottle.db.dashboard import Dashboard, DashboardType, DashboardWidget
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.views.base import BaseView


class DashboardView(BaseView):
    url_rules = [
            ('/dashboards', ['GET', 'POST']),
            ('/dashboards/<dashboard_id>', ['GET', 'PUT', 'DELETE']),
    ]

    @class_property
    def view_decorator(cls):
        return login_required

    @property
    def valid_parameters(self):
        col_keys = set(Dashboard.fields.keys())
        read_only_keys = {'owner', 'created'}
        return col_keys - read_only_keys

    def get_parameters(self):
        data = _get_request_data()

        params = {
                'owner': self.user, # for storing
        }

        for key, value in data.iteritems():
            if hasattr(Dashboard, key) and key in self.valid_parameters:

                field = getattr(Dashboard, key)
                if isinstance(field, fields.ObjectIdField):
                    value = fields.ObjectId(value)
                elif isinstance(field, fields.ListField) and isinstance(field.field, fields.ObjectIdField):
                    value = map(fields.ObjectId, value)

                params[key] = value

        return params

    def get(self, dashboard_id=None, **filters):
        if dashboard_id is None:
            # fetch list of dashboards
            dashboards = list(Dashboard.objects.find_by_user_on_current_app(self.user, **filters))
            if not dashboards:
                if not set(filters) - {'owner'}:
                    # there should be always empty 'default' dashboard for every user
                    dashboard = Dashboard.objects.get_or_create_blank_dashboard(self.user)
                    dashboards.append(dashboard)
            return [d.to_dict() for d in dashboards]
        else:
            # fetch specific dashboards
            dashboard = Dashboard.objects.get_by_user(self.user, id=dashboard_id, **filters)
            rv = dashboard.to_dict()
            rv['widgets'] = [DashboardWidget.objects.get(w_id).to_dict() for w_id in dashboard.widgets]
            return rv

    def post(self, **data):
        """Creates dashboard
        """
        if 'id' in data:
            return self.put(data['id'], **data)

        if data.get('author') is None:
            data['author'] = self.user
        else:
            data['author'] = fields.ObjectId(data['author'])
        dashboard = Dashboard.objects.create_by_user(self.user, **data)
        return dashboard

    def put(self, dashboard_id, **data):
        dashboard = Dashboard.objects.get_by_user(self.user, id=dashboard_id)

        for k, v in data.iteritems():
            setattr(dashboard, k, v)

        dashboard.save()
        return dashboard

    def delete(self, dashboard_id, **filters):
        dashboard = Dashboard.objects.get_by_user(self.user, id=dashboard_id, **filters)
        dashboard.delete()


class DashboardCopyView(BaseView):
    url_rules = [
            ('/dashboards/<dashboard_id>/copy', ['POST']),
    ]

    def post(self, dashboard_id, title, description=None):
        dashboard = Dashboard.objects.get_by_user(self.user, id=dashboard_id)
        new_dashboard = dashboard.copy_to(self.user, title, description)
        return new_dashboard


class DashboardSharedByMe(BaseView):
    url_rules = [('/dashboards/shared_by_me', ['GET'])]

    def get(self):
        dashboards = Dashboard.objects.find_by_user(self.user, owner=self.user, shared_to__gt=[])
        return [d.to_dict() for d in dashboards]


class DashboardSharedToMe(BaseView):
    url_rules = [('/dashboards/shared_to_me', ['GET'])]

    def get(self):
        dashboards = Dashboard.objects.find_by_user(self.user, shared_to=self.user.id)
        return [d.to_dict() for d in dashboards]


class DashboardTypeView(BaseView):
    url_rules = [
            ('/dashboards/type', ['GET']),
    ]

    def get(self):
        return [dt.to_dict() for dt in DashboardType.objects.find_on_current_app(self.user)]


DashboardView.register(app)
DashboardCopyView.register(app)

DashboardSharedByMe.register(app)
DashboardSharedToMe.register(app)

DashboardTypeView.register(app)
