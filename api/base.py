'''
    API Base Utilizing Flask Pluggable Views
'''
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import request
from flask.views import MethodView

from solariat_bottle.app import get_api_url
from solariat.db import fields
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.settings import LOGGER, AppException, get_var
from solariat_bottle.db.api_auth import AuthToken
from solariat_bottle.utils.decorators import optional_arg_decorator, _get_user
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.utils.views import jsonify_response as jsonify
from solariat_bottle.tasks.exceptions import TwitterCommunicationException
from solariat_bottle.tasks.exceptions import FacebookCommunicationException
from solariat_bottle.api import exceptions as api_exc

from solariat_bottle.db.user import set_user

API_VERSION         = 'v2.0'

DEFAULT_LIMIT            = 100
DEFAULT_ERROR_MSG        = "An {} error has occurred"
DEFAULT_HTTP_ERROR_CODE  = 500


def get_adapted_form(doc, form=None):
    """ Return dict with data come from request and adpated to using inside .objects.create() """
    if form is None:
        form = _get_request_data()

    result = {}

    for key, value in form.items():
        if key in ('token', 'fields'):
            continue
        field = getattr(doc, str(key), None)
        if isinstance(value, basestring) and isinstance(field, fields.ListField) and ',' in value:
            value = value.split(',')
        result[str(key)] = value
    return result


def authenticate_api_user(params, token=None):
    debug_parameters = str(params)
    token = token or params.pop('token', None)
    if not token:
        raise api_exc.AuthorizationError("Auth token is not provided. Could not authenticate user. Params: " + str(debug_parameters),
                                         description="Any request will need a token.")
    user = AuthToken.objects.get_user(token)

    if not user:
        LOGGER.warning("Auth token %s is expired" % token)
        raise api_exc.AuthorizationError("Auth token %s is expired" % token)

    if get_var('ENFORCE_API_HTTPS') and not request.url.startswith('https://'):
        # Unsercure request, invalidate token
        LOGGER.warning("Received unsecure request from URL: " + str(request.url))
        AuthToken.objects.remove(digest=token)
        description = "You have made an unsecured request over HTTP. Please use HTTPS for any subsequent calls. "
        description += "Your current token has automatically been removed. You can get a new one from the "
        description += "%s endpoint." % (get_var('HOST_DOMAIN') + get_api_url('authorize')).replace('http', 'https')
        raise api_exc.AuthorizationError(msg="Unsecure request done over HTTP. Your token has automatically removed.",
                                         description=description)
    return user


@optional_arg_decorator
def api_request(func, allow_basic_auth=False):
    """
        Meat and Bones of the REST API.  All implemented API methods should be decorated with this,
        with a couple exceptions. This decorator adds the authenticated user as a parameter
        passed to the decorated method

        1.  Parse parameters from the Request
        2.  Validate Authentication
        3.  Execute API Method
        4.  Filter and format results
        5.  Handle Error's RESTfully
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        #LOGGER.debug("API Request Args: {} | Params: {}".format(args, kwargs))
        assert args
        assert isinstance(args[0], BaseAPIView)
        view = args[0]  # Method decorator
        try:
            args = args[1:]
        except IndexError:
            args = ()

        params = _get_request_data()
        params.update(kwargs)  # Pass URL variables to the view function

        start_execution = datetime.utcnow()
        # Execute API method
        try:
            # Assert authentication
            LOGGER.debug("Started executing API call: %s.%s(%s, %s) " % (
                view.__class__.__name__, func.__name__, args, kwargs))
            if allow_basic_auth is True:
                user = _get_user()
                if user is None:
                    user = authenticate_api_user(params)
                    if user is None:
                        raise api_exc.AuthorizationError("User is not authenticated. Parameters for call: " + str(params))
            else:
                user = authenticate_api_user(params)

            # Set user in thread local storage
            set_user(user)

            resp = func(view, user, *args, **params)
            elapsed = datetime.utcnow() - start_execution
            if elapsed.total_seconds() >= 2:
                log = LOGGER.info
            else:
                log = LOGGER.debug

            log("API call: %s.%s(%s,%s) finished after %s Parameters: %s" % (view.__class__.__name__, func.__name__,
                                                                             str(args)[:500], str(kwargs)[:500],
                                                                             elapsed, str(params)[:500]))

        # auth token expiration and other auth errors
        except api_exc.AuthorizationError, exc:
            LOGGER.info(exc)
            return view.format_api_error_response(exc, msg=str(exc), description=exc.description)
        #
        # A defined API exception occurred
        #
        except api_exc.BaseAPIException, exc:
            LOGGER.exception(exc)
            return view.format_api_error_response(exc, msg=str(exc), description=exc.description)

        #
        # Some error while communicating with twitter happened
        #
        except TwitterCommunicationException, exc:
            LOGGER.exception(exc)
            return view.format_twitter_communication_exception(exc)

        #
        # Some error while communicating with facebook happened
        #
        except FacebookCommunicationException, exc:
            LOGGER.exception(exc)
            return view.format_api_error_response(exc, msg=str(exc))
        #
        #  Something more sinister went wrong
        #
        except AppException, exc:
            import traceback
            LOGGER.error(traceback.format_exc())
            msg = "{}: {} | {}".format(DEFAULT_ERROR_MSG.format('application'), exc.__class__.__name__, str(exc))
            LOGGER.error(msg)
            return view.format_api_error_response(exc, msg=msg, description=exc.description)

        #
        #  Completely unhandled exception, this is bad
        #
        except Exception, exc:
            import traceback
            LOGGER.error(traceback.format_exc())
            msg = "An unhandled exception has occurred: %s" % exc.__repr__()
            return view.format_api_error_response(msg=msg)

        #
        #  Typecheck the function response
        #
        else:
            try:
                assert isinstance(resp, dict)
            except AssertionError:
                return view.format_api_error_response(msg="API Method must return a dict.  Got a {}".format(type(resp)))
            else:
                #  All good in the hood
                start_format = datetime.now()
                result = view.format_api_response(**resp)
                end_format = datetime.now()
                LOGGER.error("FORMATTING RESPONSE TOOK " + str(end_format - start_format))
                return result

    return wrapper


def deprecate(response, deprecation_message=None):
    import json
    json_data = json.loads(response.data)
    if deprecation_message is None:
        deprecation_message = "Warning, this method is deprecated. It could be removed in future versions of the API."
    json_data['deprecation_warning'] = deprecation_message
    response.data = json.dumps(json_data)
    return response


def validate_params(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        view = args[0]
        view._validate_params(kwargs)
        return func(*args, **kwargs)
    return wrapper


class BaseAPIView(MethodView):
    ''' All of our API methods are to be derived from this class.  '''

    endpoint = None
    version  = None

    def format_api_response(self, ok=True, **kwargs):
        ''' Returns the common jsonified structure '''
        return jsonify(ok=ok, **kwargs)

    def format_api_error_response(self, error=None, msg=None, description=None):
        ''' Return this when an error has occured'''
        error = error or api_exc.BaseAPIException
        code = error.code
        msg = msg or DEFAULT_ERROR_MSG.format('unknown')
        response_data = dict(code=code, error=msg)
        if description:
            response_data['description'] = description
        resp = self.format_api_response(ok=False, **response_data)
        resp.status_code = error.http_code
        return resp

    def format_twitter_communication_exception(self, twitter_exception):
        response_data = dict(code=twitter_exception.http_code,
                             error=twitter_exception.message,
                             twitter_error_code=twitter_exception.twitter_error_code)
        resp = self.format_api_response(ok=False, **response_data)
        resp.status_code = twitter_exception.http_code
        return resp

    @classmethod
    def _resource_uri(cls):
        ''' A quick way to get the complete API URI of the resource'''
        return get_var('HOST_DOMAIN') + cls.get_api_url()

    @classmethod
    def get_api_url(cls, *args):
        ''' Binds the api url builder to the class

        :params args:  Further arguments to pass to `get_api_url`
        '''
        return get_api_url(cls.endpoint, *args, version=cls.version or API_VERSION)

    @classmethod
    def register(cls, app):
        ''' Register the API Method View to an Application.  By default, register
        the endpoint with a CRUD like endpoint scheme, i.e.

            /api/v2.0/posts/        GET
            /api/v2.0/posts/        POST
            /api/v2.0/posts/        DELETE
            /api/v2.0/posts/<_id>   GET, PUT, DELETE

        :params app: A Flask application to bind view to'''
        assert cls.endpoint is not None
        url = cls.get_api_url()
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(url, view_func=view_func, methods=['GET',])
        app.add_url_rule(url, view_func=view_func, methods=['POST',])
        app.add_url_rule(url, view_func=view_func, methods=['DELETE',])
        app.add_url_rule(cls.get_api_url('<_id>'),
                         view_func=view_func,
                         methods=['GET', 'PUT', 'DELETE'])


class ModelAPIView(BaseAPIView):
    '''Basic API CRUD for a model'''
    model = None
    user = None
    reserved_fields = ['start', 'limit', 'token', 'fields']  # Required?
    required_fields = None

    @property
    def _model_name(self):
        if self.model is None:
            return ''
        return self.model.__name__

    @classmethod
    def _resource_uri(cls, item):
        url = super(ModelAPIView, cls)._resource_uri()
        return url + '/' + str(item.id)

    @classmethod
    def _fields2show(cls, **params):
        fields = params.pop('fields', None)

        if fields and not isinstance(fields, list):
            try:
                fields.split(',')
            except AttributeError:
                raise api_exc.InvalidParameterConfiguration("Parameter 'fields', when provided,\
                 must be a list or a comma separated string")
        return fields

    def _validate_params(self, params):
        if self.required_fields:
            for field in self.required_fields:
                if field not in params:
                    raise api_exc.InvalidParameterConfiguration("Expected required field: '{}'".format(field))

    @classmethod
    def _format_doc(cls, item, **kwargs):
        ''' Format a single DB object ready to be JSONified'''
        return item.to_dict(cls._fields2show(**kwargs))

    @classmethod
    def _format_single_doc(cls, doc, **kwargs):
        ''' This gets returned by API methods that are intended to fetch a single object'''
        return {'item': cls._format_doc(doc, **kwargs)}

    @classmethod
    def _format_multiple_docs(cls, docs, **kwargs):
        ''' This is returned by API methods that return a collection of objects'''
        return {'list': [cls._format_doc(doc, **kwargs) for doc in docs]}

    def _method_not_supported_error(self, method):
        raise api_exc.MethodNotAllowed(
            "The {} method is not supported on the {} collection".format(method.upper(), self._model_name))

    @api_request
    def get(self, *args, **kwargs):
        """ By default, all API methods are not allowed.  The logic must be implemented downstream """
        return self._method_not_supported_error('get')

    @api_request
    def post(self, *args, **kwargs):
        """ By default, all API methods are not allowed.  The logic must be implemented downstream """
        return self._method_not_supported_error('post')

    @api_request
    def put(self, *args, **kwargs):
        """ By default, all API methods are not allowed.  The logic must be implemented downstream """
        return self._method_not_supported_error('put')

    @api_request
    def delete(self, *args, **kwargs):
        """ By default, all API methods are not allowed.  The logic must be implemented downstream """
        return self._method_not_supported_error('delete')

    @api_request
    def _get(self, user, _id=None, *args, **kwargs):
        """ A sensical generic repsonse to a Model GET request. """
        if _id:
            return self._get_doc_by_id(user, _id, *args, **kwargs)
        else:
            return self._fetch_docs(user, *args, **kwargs)

    @api_request
    def _post(self, user, _id=None, *args, **kwargs):
        """ A sensical generic repsonse to a Model POST request. """
        return self._create_doc(user, *args, **kwargs)

    @api_request
    def _put(self, user, _id=None, *args, **kwargs):
        """ A sensical generic repsonse to a Model PUT request. """
        if _id:
            return self._update_doc_by_id(user, _id, *args, **kwargs)
        else:
            return self._update_docs(user, *args, **kwargs)

    @api_request
    def _delete(self, user, _id=None, *args, **kwargs):
        """ A sensical generic repsonse to a Model DELETE request. """
        if _id:
            return self._delete_doc_by_id(user, *args, **kwargs)
        else:
            return self._delete_docs(user, *args, **kwargs)

    def _construct_query(self, ignored_params=None, *args, **kwargs):
        """ Build the appropriate filter query for the model from the request parameters"""
        result = {}
        if ignored_params is None:
            # By default we want to skip reserved fields which are used for different purposes
            ignored_params = self.reserved_fields
        _fields = self.model.fields.keys()
        # Now just iterate parameters and construct the required query
        for filter_name, filter_value in kwargs.items():
            if filter_name in ignored_params:
                continue
            parts = filter_name.split('__')
            if parts[0] not in _fields:
                LOGGER.warn("%s supposed to be filter but not in fields for %s, got %s" % (filter_name,
                                                                                           self.model,
                                                                                           str(kwargs)))
                continue
            result[str(filter_name)] = filter_value
        return result

    def _get_doc_by_id(self, user, _id, format_docs=True, **kwargs):
        """ Fetch a single document from the collection.
        :param user: The authorized user
        :param _id:  The document id
        :return: Document dict"""
        try:
            doc = self.model.objects.get_by_user(user, _id)
        except self.model.DoesNotExist:
            raise api_exc.ResourceDoesNotExist("The requested resource does not exist in collection '{}'".format(self._model_name))
        else:
            if format_docs:
                return self._format_single_doc(doc)
            return doc

    def _fetch_docs(self, user, slice_data=True, format_docs=True, *args, **kwargs):
        """ Fetch multiple documents from the collection"""
        query = self._construct_query(*args, **kwargs)
        docs = self.model.objects.find_by_user(user, **query)
        if slice_data:
            start = request.args.get('start', 0)
            limit = request.args.get('limit', DEFAULT_LIMIT)
            docs = docs[start:start + limit]
        if format_docs:
            docs = self._format_multiple_docs(docs)
        return docs

    def _create_doc(self, user, format_docs=True, *args, **kwargs):
        """ Create a new document in the collection """
        query = self._construct_query(*args, **kwargs)
        doc = self.model.objects.create_by_user(user, **query)
        if format_docs:
            return self._format_single_doc(doc)
        return doc

    def _update_docs(self, user, *args, **kwargs):
        """ Updates multiple documents in the collection """
        raise NotImplementedError("The collection update must be implemented individually")

    def _update_doc_by_id(self, user, _id, *args, **kwargs):
        """ Update a single document in the collection """
        raise NotImplementedError("The collection update must be implemented individually")

    def _delete_docs(self, user, *args, **kwargs):
        """ Delete a set of documents in the collection"""
        docs = self._fetch_docs(user, format_docs=False, *args, **kwargs)

        deleted = 0
        exceptions = []
        # Delete each instance individually
        for doc in docs:
            try:
                doc.delete()
            except AppException, exc:
                exceptions.append(str(exc))
            else:
                deleted += 1

        result = "%s docs was deleted, %s rejected" % (deleted, len(exceptions))
        if exceptions:
            raise api_exc.DocumentDeletionError(result, description=str(exceptions))
        return {'removed_count': deleted}

    def _delete_doc_by_id(self, user, _id, *args, **kwargs):
        """ Delete a single document by its ID"""
        doc = self._get_doc_by_id(user, _id, format_docs=False, *args, **kwargs)
        try:
            doc.remove()
        except AppException, exc:
            raise api_exc.DocumentDeletionError("Error removing document: {}".format(str(exc)))
        return {}


class BasicCRUDMixin(object):
    ''' Connect the basic CRUD operations for a ModelAPIView'''
    def get(self, *args, **kwargs):
        return self._get(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self._post(*args, **kwargs)

    def put(self, *args, **kwargs):
        return self._put(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._delete(*args, **kwargs)


class ReadOnlyMixin(object):

    def get(self, *args, **kwargs):
        return self._get(*args, **kwargs)
