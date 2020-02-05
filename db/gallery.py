from datetime import datetime
from solariat.db import fields
from solariat.db.abstract import Document
from solariat_bottle.db.auth import AuthDocument
from solariat_bottle.db.user import User
from solariat_bottle.db.dashboard import DashboardType, Dashboard


class WidgetModel(Document):
    """
    A WidgetModel is a abstract widget that can be instantiated to ConcreteWidget
    and used in corresponding typed dashboard
    """
    title = fields.StringField(required=True, unique=True)
    description = fields.StringField()
    settings = fields.DictField()
    created = fields.DateTimeField(default=datetime.now)
    #gallery = fields.ReferenceField(Gallery)


class Gallery(Document):
    """
    A gallery is dashboard_type specific, will contain collection of predifined
    widget models
    """
    dashboard_type = fields.ReferenceField(DashboardType, required=True)
    widget_models = fields.ListField(fields.ReferenceField(WidgetModel))
    created = fields.DateTimeField(default=datetime.now)

    def to_dict(self):
        rv = super(Gallery, self).to_dict()
        rv['display_name'] = self.dashboard_type.display_name
        rv['type'] = self.dashboard_type.type
        return rv


def insert_prebuilt_galleries():
    galleries = []
    for db_type in DashboardType.objects.find():
        if db_type.type == 'blank':
            continue
        gallery = Gallery.objects.get_or_create(dashboard_type=db_type)
        galleries.append(gallery)
    return galleries

insert_prebuilt_galleries()
