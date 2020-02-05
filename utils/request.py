# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from flask import request

from solariat_bottle.settings import LOGGER


def _get_request_data():
    """Convert request data to dict
    Data could come with url encoded or as plain html form,
    or with JSON send with curl -d '{"var": "value"}

    """
    import json
    form = {}
    if request.method in ['PUT', 'POST']:
        form = request.form
        if not [x for x in form.values() if x] and len(form.keys()):
            # no values - there is json from -d {...} coming
            try:
                form = json.loads("".join(form.keys()))
            except ValueError:
                msg = "Could not parse JSON from %s" % "".join(form.keys())
                LOGGER.error(msg)
                raise RuntimeError(msg)

    body_data = {}
    if request.data:
        try:
            body_data = json.loads(request.data)
            if not isinstance(body_data, dict):
                raise ValueError
        except ValueError:
            raise RuntimeError(
                "Could not load JSON from %s" % request.data)

    return dict(form.items() + request.args.items() + body_data.items() + request.files.items())


