import json
from bson import json_util
from solariat.utils.text import force_bytes, force_unicode

try:
    from six import string_types
except ImportError:
    string_types = basestring,


def _serializer_hook(obj):
    from solariat_bottle.daemons.helpers import PostCreator

    if issubclass(obj, PostCreator):
        return obj.__name__
    return obj


def _json_convert(obj, convert=_serializer_hook):
    if hasattr(obj, 'iteritems') or hasattr(obj, 'items'):
        return {k: _json_convert(v) for k, v in obj.iteritems()}
    elif hasattr(obj, '__iter__') and not isinstance(obj, string_types):
        return list((_json_convert(v) for v in obj))

    try:
        return convert(obj)
    except TypeError:
        return obj


def serialize(obj):
    return force_bytes(json.dumps(_json_convert(obj), default=json_util.default))


def deserialize(text):
    return json.loads(force_unicode(text),
                      object_hook=json_util.object_hook)
