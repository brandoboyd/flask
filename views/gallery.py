import json
from flask import make_response

from solariat.db import fields
from solariat.decorators import class_property
from solariat.exc.base import AppException
from solariat_bottle.app import app
from solariat_bottle.db.gallery import Gallery, WidgetModel
from solariat_bottle.db.dashboard import Dashboard, DashboardWidget, DashboardType
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.utils.views import jsonify_response as jsonify
from solariat_bottle.views.base import BaseView


class GalleryView(BaseView):
    url_rules = [
            ('/gallery', ['GET', 'POST']),
            ('/gallery/<gallery_id>', ['GET', 'PUT', 'DELETE']),
    ]

    @class_property
    def view_decorator(cls):
        return login_required

    @property
    def valid_parameters(self):
        col_keys = set(Gallery.fields.keys())
        read_only_keys = {'created'}
        return col_keys - read_only_keys

    def get_parameters(self):
        data = _get_request_data()
        params = {}

        for key, value in data.iteritems():
            if hasattr(Gallery, key) and key in self.valid_parameters:

                field = getattr(Gallery, key)
                if isinstance(field, fields.ObjectIdField):
                    value = fields.ObjectId(value)
                elif isinstance(field, fields.ListField) and isinstance(field.field, fields.ObjectIdField):
                    value = map(fields.ObjectId, value)

                params[key] = value

        return params


    def get(self, gallery_id=None, **filters):
        if gallery_id is None:
            # fetch list of gallery
            galleries = list(Gallery.objects.find(**filters))
            return [g.to_dict() for g in galleries]
        else:
            # fetch specific gallery
            gallery = Gallery.objects.get(id=gallery_id, **filters)
            rv = gallery.to_dict()
            rv['widget_models'] = [w_m.to_dict() for w_m in gallery.widget_models]
            return rv

    # deprecated, gallery should not be created from UI
    def post(self, **data):
        """Creates a Gallery
        """
        if 'id' in data:
            raise AppException(http_code=501, msg="'id' shouldn't be passed while creating")

        gallery = Gallery.objects.create(**data)
        return gallery.to_dict()

    # deprecated, gallery should not be updated from UI
    def put(self, gallery_id, **data):
        gallery = Gallery.objects.get(gallery_id)

        for k, v in data.iteritems():
            setattr(gallery, k, v)

        gallery.save()
        return gallery.to_dict()

    # deprecated, gallery should not be deleted from UI
    def delete(self, gallery_id, **filters):
        gallery = Gallery.objects.get(id=gallery_id, **filters)
        gallery.delete()


class WidgetModelView(BaseView):
    url_rules = [
            ('/gallery/<gallery_id>/widget_models', ['GET', 'POST', 'DELETE']),
            ('/gallery/<gallery_id>/widget_models/<widget_model_id>', ['GET', 'PUT', 'DELETE']),
    ]

    @class_property
    def view_decorator(cls):
        return login_required

    @property
    def valid_parameters(self):
        col_keys = set(WidgetModel.fields.keys())
        read_only_keys = {'created'}
        return col_keys - read_only_keys

    def get_parameters(self):
        data = _get_request_data()
        params = {}

        for key, value in data.iteritems():
            if hasattr(WidgetModel, key) and key in self.valid_parameters:

                field = getattr(WidgetModel, key)
                if isinstance(field, fields.ObjectIdField):
                    value = fields.ObjectId(value)
                elif isinstance(field, fields.ListField) and isinstance(field.field, fields.ObjectIdField):
                    value = map(fields.ObjectId, value)

                params[key] = value

        return params


    def get(self, gallery_id, widget_model_id=None):
        # **filters not supported yet
        gallery = Gallery.objects.get(gallery_id)

        if widget_model_id is None:
            # fetch list of widget_models
            widget_models = gallery.widget_models
            return [w.to_dict() for w in widget_models]
        else:
            # fetch specific widget_model
            for widget_model in gallery.widget_models:
                if str(widget_model.id) == widget_model_id:
                    break
            else:
                raise AppException(http_code=404, msg="No such widget_model_id in gallery %s" % gallery_id)
            return widget_model.to_dict()

    def post(self, gallery_id, **data):
        """Creates a widget model and adds it to given gallery
        """
        if 'id' in data:
            raise AppException(http_code=501, msg="'id' shouldn't be passed while creating")

        gallery = Gallery.objects.get(gallery_id)

        widget_model = WidgetModel.objects.create(**data)
        gallery.widget_models.append(widget_model)
        gallery.save()
        return widget_model.to_dict()

    def put(self, gallery_id, widget_model_id, **data):
        gallery = Gallery.objects.get(gallery_id)

        for widget_model in gallery.widget_models:
            if str(widget_model.id) == widget_model_id:
                break
        else:
            raise AppException(http_code=404, msg="No such widget_model_id in gallery %s" % gallery_id)

        for k, v in data.iteritems():
            setattr(widget_model, k, v)

        widget_model.save()
        return widget_model.to_dict()

    def delete(self, gallery_id, widget_model_id=None):
        # **filters not supported yet
        gallery = Gallery.objects.get(id=gallery_id)

        if widget_model_id is None:
            for widget_model in gallery.widget_models:
                # when widget_model is deleted, it is automatically pulled from gallery.widget_models since it is a ReferenceField
                # gallery.widget_models.remove(widget_model)
                widget_model.delete()
        else:
            for widget_model in gallery.widget_models:
                if str(widget_model.id) == widget_model_id:
                    break
            else:
                raise AppException(http_code=404, msg="No such widget_model_id in gallery %s" % gallery_id)

            # when widget_model is deleted, it is automatically pulled from gallery.widget_models since it is a ReferenceField
            # gallery.widget_models.remove(widget_model)
            widget_model.delete()
        # gallery.save()


# deprecated, use old widget endpoints /dashboard/new
class InstantiateWidgetModelView(BaseView):
    url_rules = [
            ('/instantiate_widget_models/<widget_model_id>', ['GET', 'PUT', 'DELETE']),
    ]

    @class_property
    def view_decorator(cls):
        return login_required

    @property
    def valid_parameters(self):
        return {'dashboard_id'}

    def get_parameters(self):
        data = _get_request_data()
        params = {}

        for key, value in data.iteritems():
            if key in self.valid_parameters:

                if key == 'dashboard_id':
                    key = 'dashboard'
                    value = Dashboard.objects.get_by_user(self.user, id=value)

                params[key] = value

        return params

    def get(self, widget_model_id):
        widget_model = WidgetModel.objects.get(widget_model_id)

    def put(self, widget_model_id, dashboard):
        widget_model = WidgetModel.objects.get(widget_model_id)
        widget_data = {
                'user': self.user,
                'title': widget_model.title,
                'dashboard_id': dashboard.id,
        }
        widget_data.update(widget_model.settings)
        widget = DashboardWidget.objects.create_by_user(**widget_data)
        dashboard.reload()
        return dashboard

    def delete(self, widget_model_id, dashboard):
        widget_model = WidgetModel.objects.get(widget_model_id)


@app.route('/gallery/<gallery_id>/export')
@login_required()
def export_gallery(user, gallery_id):
    try:
        gallery = Gallery.objects.get(gallery_id)
    except Exception, err:
        return jsonify(ok=False, error=str(err))

    gallery_dict = gallery.to_dict()

    gallery_dict['widget_models'] = [wm.to_dict() for wm in gallery.widget_models]

    output = make_response(json.dumps(gallery_dict, indent=4))
    output.headers["Content-Disposition"] = 'attachment; filename="Gallery for %s.json"' % gallery.dashboard_type.display_name
    output.headers["Content-type"] = "application/json"
    return output


@app.route('/gallery/import', methods=['POST'])
@login_required()
def import_gallery(user):
    data = _get_request_data()
    try:
        dashboard_type = DashboardType.objects.get(type=data['type'])
        gallery = Gallery.objects.get(dashboard_type=dashboard_type.id)
    except Exception, err:
        return jsonify(ok=False, error=str(err))

    for wm in data['widget_models']:
        model = WidgetModel.objects.create(
                title = wm['title'],
                description = wm['description'],
                settings = wm['settings']
        )
        gallery.widget_models.append(model)
    gallery.save()
    return jsonify(ok=True, data=gallery.to_dict(), number_of_added_widget_models=len(data['widget_models']))


GalleryView.register(app)
WidgetModelView.register(app)
InstantiateWidgetModelView.register(app)
