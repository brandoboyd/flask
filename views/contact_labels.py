#!/usr/bin/env python
# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
"""
UI for Channels

"""
from flask import jsonify, request, abort

from ..db.contact_label import ExplcitTwitterContactLabel

from solariat.utils.timeslot import datetime_to_timestamp_ms
from ..utils.decorators import login_required

from ..app import app


ModelCls = ExplcitTwitterContactLabel


def _user_to_ui_select(user):
    return {"id": str(user.id),
            "text": user.email}


def _params_from_request(request_data, *allowed_params):
    valid_params = {}
    for param in allowed_params:
        valid_params[param] = request_data.get(param)
    return valid_params


def _handle_label(user, status, **params):
    items = params.get('labels', [])
    if not isinstance(items, list):
        items = [items]
    for item_id in items:
        try:
            item = ModelCls.objects.find_by_user(user, id=item_id)[0]
        except (IndexError, ModelCls.DoesNotExist):
            return {'ok': False,
                    'error': '%s not found.' % ModelCls.__name__}
        item.status = "%s" % status
        if status == "Archived":
            item.title = "%s~" % item.title
        item.save()
    return {'ok': True}


def _create_update(user, **params):
    item_id = params.get('id', None)
    users = params['users'] or []

    data = {
        'title': params['title'],
        'users': users
    }

    if item_id:
        try:
            item = ModelCls.objects.find_by_user(user, id=item_id)[0]
        except (IndexError, ModelCls.DoesNotExist):
            return {'ok': False,
                    'error': '%s not found.' % ModelCls.__name__}
        if item.title != data['title']:
            if ModelCls.objects(title=data['title']).limit(1).count():
                return {'ok': False,
                        'error': 'Title must be unique'}
        set_data = dict(
            ('set__%s' % key, value) for key, value in data.iteritems())
        item.update(**set_data)
        item.reload()
    else:
        if ModelCls.objects(title=data['title']).limit(1).count():
            return {'ok': False,
                    'error': 'Title must be unique'}
        data['status'] = 'Active'
        item = ModelCls.objects.create_by_user(user, **data)

    return {'ok': True,
            'item': _to_ui(item, user)}


@app.route('/contact_label/update/json', methods=['POST'])
@login_required()
def update_label(user):
    data = request.json
    allowed_params = ('title', 'users', 'id')
    result = _create_update(user, **_params_from_request(data, *allowed_params))
    return jsonify(**result)


@app.route('/contact_label/<action>/json', methods=['POST'])
@login_required()
def delete_label(user, action):
    if action not in ('activate', 'deactivate', 'delete'):
        return jsonify({'ok': False,
                        'error': 'unknown operation'})

    allowed_params = ('labels',)
    status = {
        'activate': "Active",
        'deactivate': "Suspended",
        'delete': "Archived"
    }[action]
    resp = _handle_label(user, status,
                         **_params_from_request(request.json, *allowed_params))
    return jsonify(resp)


@app.route('/contact_label/json', methods=['GET'])
@login_required()
def list_label(user):
    id_ = request.args['id']
    try:
        resp = _get_label(user, id_)
    except Exception, e:
        app.logger.error(e)
        return abort(500)
    return jsonify(resp)


@app.route('/contact_labels/json', methods=['GET'])
@login_required()
def list_labels(user):
    allowed_params = (
        'offset', 'limit', 'channel', 'status', 'adaptive_learning_enabled',
        'id', 'from', 'to')
    valid_params = _params_from_request(request.args, *allowed_params)

    item_id = valid_params.pop('id', None)
    if item_id:
        try:
            resp = _get_label(user, item_id)
        except Exception, e:
            app.logger.error(e)
            return abort(500)
    else:
        try:
            resp = _get_labels(user)
        except Exception, e:
            app.logger.error(e)
            return abort(500)
    return jsonify(resp)


def _get_labels(user):
    items = ModelCls.objects.find_by_user(user, status={
        '$in': ['Active', 'Suspended']})
    return dict(ok=True,
                size=len(items),
                list=[_to_ui(x, user) for x in items])


def _get_label(user, id_):
    item = ModelCls.objects.find_by_user(user, id=id_)
    return {'ok': True,
            'item': _to_ui(item[0], user)}


def _to_ui(item, user=None):
    return {
        'id': str(item.id),
        'perm': item.perms(user) if user else 'r',
        'title': item.title,
        'users': item.users,
        'status': str(item.status),
        'platform': 'twitter',
        'created_at': datetime_to_timestamp_ms(item.created),
    }
