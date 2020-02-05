"""
A bunch of useful decorators

"""
from functools import wraps
from datetime import datetime
import urllib

from flask import url_for, request, redirect, make_response, jsonify
from pprint import pformat

from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.db.user import set_user


def inject_tz_offset():
    try:
        tz_offset = int(request.headers.get('SOTZOFFSET'))
    except:
        tz_offset = 0
    request.tz_offset = tz_offset


def map_request_to_arguments(view_func):
    @wraps(view_func)
    def _wrapper(*args, **kw):
        data = _get_request_data()
        data.update(kw)
        return view_func(*args, **data)

    return _wrapper


def channel_required(ch_key='channel'):

    def _decorator(view_func):

        "Decorator who resolve channel by id or return error response"
        from solariat_bottle.db.channel.facebook import Channel
        from solariat_bottle.utils.views import get_doc_or_error

        @wraps(view_func)
        def wrapper(*args, **kw):
            data = dict()
            data.update(request.view_args)
            data.update(request.args)
            channel_id = data.get(ch_key)
            try:
                channel = get_doc_or_error(Channel, channel_id)
                kw['channel'] = channel
                return view_func(*args, **kw)
            except Exception, e:
                from solariat_bottle.settings import LOGGER

                LOGGER.error(e)
                return jsonify(ok=False, error="No channel exists for id=%s"%channel_id)

        return  wrapper

    return _decorator


def optional_arg_decorator(decorator):
    @wraps(decorator)
    def wrapped_decorator(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return decorator(args[0])
        else:
            def decorator_with_args(view_func):
                return decorator(view_func, *args, **kwargs)
            return decorator_with_args

    return wrapped_decorator


def _get_user():
    from ..db.api_auth import AuthToken
    from ..db.user import User, AuthError

    user = None
    # If this accepts token based auth, try for that first
    data = _get_request_data()
    if 'token' in data:
        try:
            token = data.get('token')
            user = AuthToken.objects.get_user(token)
        except User.DoesNotExist:
            pass

    # Still default to user based auth
    if not user:
        try:
            user = User.objects.get_current()
        except AuthError:
            pass

    return user


def log_staff_request(user):
    if user and (user.is_superuser or user.is_staff) \
            and request.path.startswith('/configure'):
        from solariat.utils.logger import format_request
        from solariat_bottle.settings import LOGGER

        LOGGER.info("\n" + format_request(request, user))


@optional_arg_decorator
def login_required(view_func, allow_app_access=False):
    "Decorator that redirects to login any anonymous user"
    @wraps(view_func)
    def _wrapped(*args, **kw):
        inject_tz_offset()
        user = _get_user()
        log_staff_request(user)
        if user:
            set_user(user)
            kw['user'] = user
            return view_func(*args, **kw)
        else:
            return redirect(url_for('login', next=urllib.quote_plus(request.path)))
    return _wrapped


def add_response_headers(headers={}):
    """This decorator adds the headers passed in to the response"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            resp = make_response(f(*args, **kwargs))
            h = resp.headers
            for header, value in headers.items():
                h[header] = value
            return resp
        return decorated_function
    return decorator


def p3pheader(f):
    """This decorator passes custom HTTP header.

    It is necessary for allowing iframes to set cookies in most browsers.
    See for example https://gist.github.com/daaku/586182
    """
    @wraps(f)
    @add_response_headers({'P3P': 'CP="CAO PSA OUR HONK"'})
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def user_passes_test(test_func):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(*args, **kw):
            from ..db.user import User, AuthError
            inject_tz_offset()
            try:
                user = User.objects.get_current()
            except AuthError:
                return redirect(url_for('login', next=request.path))

            if not test_func(user):
                #abort(401)
                return redirect(url_for('login', next='/'))

            kw['user'] = user
            log_staff_request(user)
            return view_func(*args, **kw)

        return _wrapped_view
    return decorator


def timed_event(func):
    "Decorator to generate timing information"
    @wraps(func)
    def _wrapped_func(*args, **kw):
        from ..db.event_log import log_event
        s = datetime.utcnow()
        res = func(*args, **kw)
        t = datetime.utcnow() - s

        account = None
        email = None

        if 'user' in kw:
            user = kw['user']
            email = user.email
            if user.account:
                account = user.account.name

        note = "Elapsed time for %s was %d ms" % (func.__name__, int(t.total_seconds()))
        log_event('TimedEvent', user=email, account=account,
                  note=note, func_name=func.__name__)
        return res

    return _wrapped_func

superuser_required = user_passes_test(lambda u: u.is_superuser)
staff_required = user_passes_test(lambda u: u.is_staff)
admin_required = user_passes_test(lambda u: u.is_admin)
staff_or_admin_required = user_passes_test(lambda u: u.is_staff or u.is_admin)


def log_response(logger, log_level='DEBUG'):

    def _fn_wrap(func):

        def _wrapper(*args, **kw):
            data = func(*args, **kw)
            from solariat_bottle.settings import LOG_LEVEL

            if LOG_LEVEL == log_level:
                logger.debug(pformat(data))
            return data

        return _wrapper

    return _fn_wrap
