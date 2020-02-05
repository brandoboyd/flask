from datetime import datetime

from solariat.db import fields
from solariat_bottle.db.user import User
from solariat.db.abstract import Document, Manager
from solariat_bottle.db.auth import AuthDocument, AuthManager
from solariat_bottle.db.roles import STAFF, ADMIN, REVIEWER, ANALYST

DASHBOARD_TYPES = {
        'blank': {
            'display_name': 'Blank dashboard type',
        },
        'nps': {
            'display_name': 'NPS dashboard type',
        },
        'journeys': {
            'display_name': 'Journeys dashboard type',
        },
        'customers': {
            'display_name': 'Customers dashboard type',
        },
        'agents': {
            'display_name': 'Agents dashboard type',
        },
}

DASHBOARD_TYPES_FOR_APP = {
        'GSA': ['blank'],
        'GSE': ['blank'],
        'Journey Analytics': ['blank', 'journeys', 'customers', 'agents'],
        'NPS': ['blank', 'nps'],
        'Predictive Matching': ['blank'],
}


class DashboardWidgetManager(Manager):

    def create_by_user(self, user, title, dashboard_id, order=None, **settings):
        if order is None:
            # Figure it out from existing obects of the current user
            existing_max = DashboardWidget.objects.find(user=user.id, dashboard_id=dashboard_id).sort(order=-1).limit(1)[:]
            if existing_max:
                order = existing_max[0].order + 1
            else:
                order = 0

        dashboard = Dashboard.objects.get_by_user(user, id=dashboard_id)
        widget = DashboardWidget(user=user.id, title=title, settings=settings, dashboard_id=dashboard.id,
                                 order=int(order), created=datetime.now())
        widget.save()
        dashboard._add_widget(widget)
        return widget

    def clear_for_channels(self, channels_list):
        """ Clear all widgets which were created for any of the channels
        passed in as :param channels_list:"""
        # TODO: If this is a frequent operation we might think of moving the channel if out
        # of object settings and have it as an indexed attribute (so far don't think it's the case)
        DashboardWidget.objects.coll.remove({'s.settings.channel_id' : {'$in' : channels_list}})


class DashboardWidget(Document):
    '''
    Internal Structure representing the integartion
    data structure with a data stream provider.
    '''
    created = fields.DateTimeField(db_field='c', default=datetime.now)
    settings = fields.DictField(db_field='s')
    order = fields.NumField(db_field='o')
    title = fields.StringField(db_field='t', required=True)
    user = fields.ReferenceField(User, db_field='u')
    dashboard_id = fields.ObjectIdField(required=True)

    manager = DashboardWidgetManager

    def to_dict(self):
        base_dict = dict(title=self.title, order=self.order, id=str(self.id), dashboard_id=str(self.dashboard_id))
        base_dict.update(self.settings)
        return base_dict

    def copy_to(self, dashboard):
        new_widget_data = {
                'title': self.title,
                'user': dashboard.owner,
                'dashboard_id': dashboard.id,
        }
        new_widget_data.update(self.settings)
        widget = DashboardWidget.objects.create_by_user(**new_widget_data)
        return widget

    def delete(self):
        dashboard = Dashboard.objects.get_by_user(self.user, id=self.dashboard_id)
        dashboard._remove_widget(self)
        super(DashboardWidget, self).delete()

    def __repr__(self):
        return "<DashboardWidget: %s; id: %s>" % (self.title, self.id)


class DashboardManager(AuthManager):

    def get_or_create_blank_dashboard(self, user, default_title='Blank Dashboard'):
        """Get a dashboad with {title='Blank Dashboard'},
        OR Create a dashboard of {type_id='blank dashboard type id', display_name='Blank Dashboard'}
        """
        db_type = DashboardType.objects.get_or_create_blank_dashboard_type()
        try:
            return Dashboard.objects.get_by_user(user, type_id=db_type.id, owner=user)
        except Dashboard.DoesNotExist:
            dashboard_data = {
                    'type_id': db_type.id,
                    'title': default_title,
                    'owner': user,
                    'author': user,
            }
            return Dashboard.objects.create_by_user(user, **dashboard_data)

    def find_by_user_on_current_app(self, user, **filters):
        supported_dashbaord_types = DASHBOARD_TYPES_FOR_APP.get(user.account.selected_app)
        if supported_dashbaord_types is None:
            return []
        filters['type_id__in'] = [dt.id for dt in DashboardType.objects.find(type__in=supported_dashbaord_types)]
        return self.find_by_user(user, **filters)


class Dashboard(AuthDocument):
    collection = 'Dashboard'
    manager = DashboardManager

    type_id = fields.ObjectIdField(required=True)
    title = fields.StringField(required=True)
    description = fields.StringField()
    owner = fields.ReferenceField(User)
    author = fields.ReferenceField(User)
    widgets = fields.ListField(fields.ObjectIdField())
    shared_to = fields.ListField(fields.ObjectIdField())
    filters = fields.DictField()
    created = fields.DateTimeField(default=datetime.now)

    admin_roles = {STAFF, ADMIN, REVIEWER, ANALYST}

    def to_dict(self, fields_to_show=None):
        rv = super(Dashboard, self).to_dict()
        rv['widgets'] = map(str, self.widgets)
        rv['shared_to'] = map(str, self.shared_to)
        rv['owner_name'] = '%s %s' % (self.owner.first_name or '', self.owner.last_name or '')
        rv['author_name'] = '%s %s' % (self.author.first_name or '', self.author.last_name or '')
        rv['owner_email'] = self.owner.email
        rv['author_email'] = self.author.email
        rv['account_id'] = str(self.owner.account.id)
        rv['type'] = DashboardType.objects.get(self.type_id).type
        return rv

    def __repr__(self):
        return "<Dashboard: %s; id: %s>" % (self.title, self.id)

    def _add_widget(self, widget):
        """
        """
        self.widgets.append(widget.id)
        self.save()

    def _remove_widget(self, widget):
        """
        widget is not automatically deleted. To delete, use `.delete_widget()` instead.
        `widget.dashboard_id` will still point to this dashboard.
        """
        self.widgets.remove(widget.id)
        self.save()

    def delete_widget(self, widget):
        if isinstance(widget, (basestring, fields.ObjectId)):
            widget = DashboardWidget.objects.get(widget)
        widget.delete()

    def delete(self):
        for widget_id in self.widgets:
            self.delete_widget(widget_id)
        super(Dashboard, self).delete_by_user(self.owner)

    def copy_to(self, user, title=None, description=None):
        dashboard_data = {
                'type_id': self.type_id,
                'title': title or self.title,
                'description': description or self.description,
                'author': self.owner,
                'owner': user,
                'widgets': [],
                'shared_to': [],
                'filters': self.filters,
        }
        # FIX: create_by_user is having role error
        dashboard = Dashboard.objects.create_by_user(user, **dashboard_data)
        #dashboard = Dashboard.objects.create(**dashboard_data)
        for widget_id in self.widgets:
            widget = DashboardWidget.objects.get(widget_id)
            widget.copy_to(dashboard)
        return dashboard


class DashboardTypeManager(Manager):
    def get_or_create_blank_dashboard_type(self):
        try:
            return DashboardType.objects.get(type='blank')
        except DashboardType.DoesNotExist:
            dashboard_type_data = {
                'type': 'blank',
                'display_name': DASHBOARD_TYPES['blank']['display_name'],
            }
            return DashboardType.objects.create(**dashboard_type_data)

    def find_on_current_app(self, user, **filters):
        supported_dashbaord_types = DASHBOARD_TYPES_FOR_APP.get(user.account.selected_app)
        if supported_dashbaord_types is None:
            return []
        filters['type__in'] = supported_dashbaord_types
        return DashboardType.objects.find(**filters)


class DashboardType(Document):
    collection = 'DashboardType'
    manager = DashboardTypeManager

    type = fields.StringField(required=True, unique=True)
    display_name = fields.StringField(required=True, unique=True)
    owner = fields.ReferenceField(User)
    created = fields.DateTimeField(default=datetime.now)

    def __repr__(self):
        return "<DashboardType: %s; id: %s>" % (self.display_name, self.id)

    def to_dict(self):
        rv = super(DashboardType, self).to_dict()
        if self.owner:
            rv['owner_name'] = '%s %s' % (self.owner.first_name or '', self.owner.last_name or '')
            rv['email'] = self.owner.email
        else:
            rv['owner_name'] = ''
            rv['email'] = ''
        return rv

def insert_default_dashboard_types():
    # default dashboard types
    # Fixtures for now
    db_types_obj = []
    for db_type, meta in DASHBOARD_TYPES.items():
        db_type_obj = DashboardType.objects.get_or_create(type=db_type,
                                            display_name=meta['display_name'])
        db_types_obj.append(db_type_obj)

    return db_types_obj

insert_default_dashboard_types()
