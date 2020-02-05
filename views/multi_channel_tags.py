#! /usr/bin/python
# -*- coding: utf-8 -*-
from flask import request, jsonify

from solariat_bottle.app import app
from solariat_bottle.utils.decorators import login_required

from solariat_bottle.db.predictors.multi_channel_smart_tag import MultiEventTag, SingleEventTag


TAG_MAPPING = {'single': SingleEventTag,
               'multi': MultiEventTag}


def create_multi_channel_tag(user, _klass, account_id, display_name, channels, features_metadata, description=None,
                             precondition=None, acceptance_rule=None):
    return _klass.objects.create_by_user(user,
                                         account_id=account_id,
                                         display_name=display_name,
                                         channels=channels,
                                         features_metadata=features_metadata,
                                         description=description,
                                         precondition=precondition,
                                         acceptance_rule=acceptance_rule)

@app.route('/multi_channel_tag/<tag_type>', methods=['POST'])
@login_required()
def create_tag_handler(user, tag_type):
    """
    Get the list of channels with their bookmarks, in alphabetical
    order.
    """
    account_id = user.account.id

    tag_data = request.json
    if 'display_name' not in tag_data:
        return jsonify(ok=False, error="Required parameter 'display_name' not present")

    if 'channels' not in tag_data:
        return jsonify(ok=False, error="Required parameter 'channels' not present")

    if tag_type not in TAG_MAPPING:
        return jsonify(ok=False, error="Unknowns type %s. Should be one of %s" % (tag_type, TAG_MAPPING.keys()))
    _tag_klass = TAG_MAPPING[tag_type]

    display_name = tag_data['display_name']
    channels = tag_data['channels']
    features_metadata = tag_data.get('features_metadata', {})
    description = tag_data.get('description', None)
    precondition = tag_data.get('precondition', None)
    acceptance_rule = tag_data.get('acceptance_rule', None)

    if 'id' in tag_data:
        tag = _tag_klass.objects.get(tag_data['id'])
        tag.display_name = display_name
        tag.channels = channels
        tag.features_metadata = features_metadata
        tag.description = description
        tag.precondition = precondition
        tag.acceptance_rule = acceptance_rule
        tag.save()
    else:
        tag = create_multi_channel_tag(user,
                                       _tag_klass,
                                       account_id,
                                       display_name,
                                       channels,
                                       features_metadata,
                                       description,
                                       precondition,
                                       acceptance_rule)
    return jsonify(ok=True, item=tag.to_dict())


@app.route('/multi_channel_tag/<tag_type>', methods=['GET'])
@login_required()
def get_multi_channel_tag(user, tag_type):
    """
    Get the list of channels with their bookmarks, in alphabetical
    order.
    """
    if tag_type not in TAG_MAPPING:
        return jsonify(ok=False, error="Unknowns type %s. Should be one of %s" % (tag_type, TAG_MAPPING.keys()))
    _tag_klass = TAG_MAPPING[tag_type]

    tag_data = request.json or request.args or {}
    tag_id = tag_data.get('id')
    if tag_id:
        try:
            tag = _tag_klass.objects.get(tag_id)
            return jsonify(ok=True, item=tag.to_dict())
        except _tag_klass.DoesNotExist:
            return jsonify(ok=False, error='No tag with id=%s was found.' % tag_id)

    account_id = tag_data.get('account_id') or user.account.id
    if account_id:
        return jsonify(ok=True, list=[tag.to_dict() for tag in _tag_klass.objects(account_id=account_id)])

    return jsonify(ok=False, error="No filter criteria passed in. Either 'id' or 'account_id' must be provided.")