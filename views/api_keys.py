#! /usr/bin/python
# -*- coding: utf-8 -*-
""" UI for Channels """
from flask import jsonify

from solariat_bottle.app import app, AppException
from solariat_bottle.db.api_auth import ApplicationToken
from solariat_bottle.utils.decorators import login_required


def get_adapted_form(*args, **kw):
    from solariat_bottle.api.base import get_adapted_form
    return get_adapted_form(*args, **kw)


@app.route('/api_key/request_new', methods=['POST'])
@login_required()
def create_api_key(user):
    api_data = get_adapted_form(ApplicationToken)
    token = ApplicationToken.objects.request_by_user(user=user,
                                                     app_type=api_data.get('type', ApplicationToken.TYPE_ACCOUNT))
    return jsonify(ok=True, item=token.to_dict())


@app.route('/api_key/<key_id>/validate', methods=['POST'])
@login_required()
def validate_api_key(user, key_id):
    try:
        token = ApplicationToken.objects.validate_app_request(user, key_id)
    except AppException, ex:
        return jsonify(ok=False, error=str(ex))
    return jsonify(ok=True, item=token.to_dict())


@app.route('/api_key/list', methods=['GET'])
@login_required()
def list_api_keys(user):
    if not user.is_superuser:
        return jsonify(ok=False, error="Only superuser has access to all application keys")
    return jsonify(ok=True, list=[item.to_dict() for item in ApplicationToken.objects()])

