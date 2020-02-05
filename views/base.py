from flask import request
from flask.views import MethodView

from solariat.decorators import class_property

from solariat.exc.base import AppException
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.utils.views import jsonify_response

from solariat_bottle.settings import LOGGER


class HttpResponse(object):
    __slots__ = ['status', 'data', 'ok']

    def __init__(self, data, status=200, ok=True):
        self.data = data
        self.status = status
        self.ok = ok


class BaseView(MethodView):
    url_rules = []

    @class_property
    def view_decorator(cls):
        return login_required

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        view = super(BaseView, cls).as_view(name, *class_args, **class_kwargs)
        return cls.view_decorator(view)

    @classmethod
    def register(cls, app):
        view_func = cls.as_view(cls.__name__)
        for url, methods in cls.url_rules:
            app.add_url_rule(url, view_func=view_func, methods=methods)

    def get_parameters(self):
        data = _get_request_data()
        return data

    def do_dispatch(self, *args, **kwargs):
        return super(BaseView, self).dispatch_request(*args, **kwargs)

    def dispatch_request(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        http_status = {'GET': 200,
                       'POST': 201,
                       'DELETE': 204}.get(request.method, 200)

        try:
            kwargs.update(self.get_parameters())
            response = self.do_dispatch(*args, **kwargs)
        except AppException as exc:
            LOGGER.exception(__name__)
            resp = exc.to_dict()
            resp['ok'] = False
            http_status = exc.http_code
        except:
            LOGGER.exception(__name__)
            http_status = 423
            resp = {'ok': False, 'error': 'System error'}
        else:
            ok = True
            if isinstance(response, HttpResponse):
                http_status = response.status
                ok = response.ok
                response = response.data

            resp = {"data": response, "ok": ok}
            if response is None and request.method == 'GET':
                http_status = 404

        resp = jsonify_response(resp)
        resp.status_code = http_status
        return resp


class BaseMultiActionView(BaseView):

    # something like
    # url_rules = [
    #     ('/dataset/create', ['POST'], 'create'),
    #     ('/dataset/update/<name>', ['POST'], 'update'),
    #     ('/dataset/get/<name>', ['GET'], 'get'),
    # ]

    @classmethod
    def register(cls, app):
        view_func = cls.as_view(cls.__name__)
        for url, methods, _ in cls.url_rules:
            app.add_url_rule(url, view_func=view_func, methods=methods)

    def do_dispatch(self, *args, **kwargs):
        for url, methods, action in self.url_rules:
            if request.url_rule.rule == url and request.method in methods:
                meth = getattr(self, action, None)
                assert meth is not None, 'Not implemented action: %s' % action
                return meth(*args, **kwargs)
