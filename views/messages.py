#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
UI for Messages

"""
import string
from flask import jsonify, request
from solariat_nlp.sa_labels import SATYPE_NAME_TO_TITLE_MAP, SATYPE_TITLE_TO_NAME_MAP

from ..app              import app
from ..utils.views      import get_paging_params
from ..utils.decorators import login_required
from solariat.utils.timeslot import datetime_to_timestamp_ms

def escape_regex(term):
    term = ''.join([c for c in term if c not in string.punctuation])
    return u"%s" % term

def _matchable_to_dict(matchable, user):
    return  {'id'               : str(matchable.id),
             'created_at'       : datetime_to_timestamp_ms(matchable.created),
             'url'              : matchable.get_url(),
             'creative'         : matchable.creative,
             #'topics'          : matchable.intention_topics,
             'channels'         : [str(x.id) for x in matchable.channels if x],
             'status'           : 'active' if matchable.is_active else 'inactive',
             #'is_dispatchable' : matchable.is_dispatchable,
             'impressions'      : matchable.accepted_count,
             'perm'             : 'rw' if matchable.can_edit(user) else 'r',
             'clicks'           : matchable.clicked_count,
             'language': matchable.language}

def _params_from_request(request_data, *allowed_params):
    valid_params = {}
    for param in allowed_params:
        valid_params[param] = request_data.get(param)
    return valid_params


def fetch_matchables(user, offset, limit, **kw):
    return Matchable.objects.find_by_user(user, **kw).sort(**{'id': -1}).skip(offset).limit(limit)

def _get_messages(user, **kw):
    status = kw.pop('status', None)
    if status is not None and status.strip() and status != 'all':
        kw['is_active'] = status == 'active'

    channel = kw.pop('channel', None)
    from ..db.channel.base import Channel
    try:
        channel = Channel.objects.find_by_user(user, id=channel)[0]
    except:
        return {'ok': False,
                'message': 'Channel not found.'}
    else:
        kw['channels__in'] = [channel]

    search_term = kw.pop('search_term', None)
    if search_term is not None and search_term.strip():
        kw['creative__regex'] = escape_regex(search_term)
        kw['creative__options'] = 'i'

    paging_params = get_paging_params(kw)
    kw.update(paging_params)
    matchables = fetch_matchables(user, **kw)

    return dict(ok=True,
        size=matchables.count(with_limit_and_skip=False),
        list=[_matchable_to_dict(m, user) for m in matchables],
        **paging_params)


def _get_matchable_details(user, id):
    try:
        matchable = Matchable.objects.find_by_user(user, id=id)[0]
    except:
        return {'ok': False,
                'message': 'Message not found.'}
    matchable_dict = matchable.to_dict(skip_ranking_model=True)
    matchable_dict['topics'] = matchable.intention_topics
    matchable_dict['perm'] = matchable.perms(user)
    del matchable_dict['intention_topics']
    matchable_dict['intentions'] = [SATYPE_TITLE_TO_NAME_MAP.get(x)
                                    for x in matchable_dict['intention_types']]
    return {'ok': True,
            'matchable': matchable_dict}


@app.route('/messages/json', methods=['GET'])
@login_required()
def messages(user):
    try:
        allowed_params = ('offset', 'limit', 'channel', 'search_term', 'status', 'id')
        valid_params = _params_from_request(request.args, *allowed_params)

        matchable_id = valid_params.pop('id', None)
        if matchable_id:
            #return extended message info
            resp = _get_matchable_details(user, matchable_id)
            return jsonify(resp)
        
        resp = _get_messages(user, **valid_params)
    except Exception as e:
        resp = {'ok': False, 'message': str(e) }
    return jsonify(resp)


@app.route('/message/<action>/json', methods=['POST'])
@login_required()
def message(user, action):
    try:
        if action == "create" or action == 'update':
            allowed_params = ('creative', 'topics', 'intentions', 'channels', 'id', 'language')
            result = _create_update_message(user, **_params_from_request(request.json, *allowed_params))
        elif action == 'delete':
            result = _delete_message(user, **_params_from_request(request.json, 'ids'))
        elif action == "activate":
            result = _activate_message(user, **_params_from_request(request.json, 'ids'))
        elif action == "deactivate":
            #print "Deactivating"
            result = _deactivate_message(user, **_params_from_request(request.json, 'ids'))
        else:
            result = {'ok': False, 'error': 'Unknown action.'}
    except Exception as e:
        result = {'ok': False, 'error': str(e)}
    return jsonify(**result)


def _create_update_message(user, **params):
    matchable_id = params.get('id', None)
    channels = params['channels']
    creative = params['creative']
    language = params['language']
    language = language if language else 'en'

    # Topics
    topics = [t for t in params['topics'] if t and t.strip()]

    # Intentions
    intentions = [i for i in params['intentions'] if i and i.strip()]
    if intentions:
        intention_types = [SATYPE_NAME_TO_TITLE_MAP[i] for i in intentions]
    else:
        intention_types = [sa for sa in SATYPE_NAME_TO_TITLE_MAP.values() if sa != 'ALL INTENTIONS']

    if not (creative and creative.strip()):
        return {'ok': False,
                'error': 'Creative must not be empty.'}
    
    if not (channels and len(channels)):
        return {'ok': False,
                'error': 'Channel fields must not be empty.'}

    try:
        from ..db.channel.base import Channel
        channels = list(Channel.objects.find_by_user(user, id__in=channels))
    except Exception, e:
        return {'ok': False,
                'error': 'Channels not found.'}

    from ..elasticsearch import MatchableCollection
    from ..db.matchable import Matchable

    if matchable_id:
        try:
            matchable = Matchable.objects.find_by_user(user, id=matchable_id)[0]
        except:
            return {'ok': False,
                    'error': 'Message not found.'}

        matchable.channels = channels
        matchable.creative = creative
        matchable.intention_types = intention_types
        matchable.intention_topics = topics
        matchable._lang_code = language
        matchable.save()

        try:
            matchable.withdraw()
            matchable.deploy(refresh=False)
        except Exception, e:
            return {'ok': False,
                    'error': 'Saved changes. But could not synchronize for matching. Error: %s. Try manual activation, or contact support.' % str(e)}
            
    else:
        from solariat_bottle.db.group import default_admin_group, default_agent_group
        # As a default, try to share with groups that I'm part of. If I'm not part of any specific
        # groups, just share with the default admin and agent groups
        if user.is_agent and user.groups:
            # If an agent creates a new message, share with all his groups
            acl = [str(g) for g in user.groups]
        else:
            # If admin/staff creates message, share with all agents and all admins
            acl = [default_admin_group(user.current_account), default_agent_group(user.current_account)]
        print acl
        matchable = Matchable.objects.create_by_user(user,
                                                     channels=channels,
                                                     creative=creative,
                                                     intention_types=intention_types,
                                                     intention_topics=topics,
                                                     acl=acl,
                                                     _lang_code=language)

    #print "Refreshing"
    try:
        MatchableCollection().index.refresh()
    except Exception, e:
        return {'ok': False,
                    'message': 'Saved changes. But could not refresh matching. Error: %s. Try manual activation, or contact support.' % str(e)}

    return {'ok': True,
            'data':_matchable_to_dict(matchable, user)}


def _delete_message(user, **params):
    ids = params['ids']
    if not isinstance(ids, list):
        ids = [ids]

    try:
        Matchable.objects.remove_by_user(user, id__in=ids)
    except Exception, e:
        return {'ok': False,
                'message': 'Matchables delete failure.'}
    return {'ok': True}


def _activate_message(user, **params):
    ids = params['ids']
    if not isinstance(ids, list):
        ids = [ids]

    try:
        matchables = Matchable.objects.find_by_user(user, id__in=ids)
        for m in matchables:
            m.deploy()
    except Exception, e:
        return {'ok': False,
                'message': 'Matchables deploy failure.'}
    return {'ok': True}


def _deactivate_message(user, **params):
    ids = params['ids']
    if not isinstance(ids, list):
        ids = [ids]

    try:
        matchables = Matchable.objects.find_by_user(user, id__in=ids)
        for m in matchables:
            m.withdraw()
    except Exception, e:
        return {'ok': False,
                'message': 'Matchables withdraw failure.'}
    return {'ok': True}

