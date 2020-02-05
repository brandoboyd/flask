#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
UI for SmartTagChannel

"""
import string
from operator import itemgetter

from flask import jsonify, request, abort

from solariat_bottle.utils.views import parse_bool
from solariat_nlp.sa_labels import SATYPE_NAME_TO_TITLE_MAP
from solariat_bottle.db.group import Group
from ..app              import app
from ..utils.decorators import login_required, timed_event
from solariat.utils.timeslot import datetime_to_timestamp_ms, parse_date_interval, guess_timeslot_level, now
from ..db.account import AccountEvent
from ..db.auth import default_access_groups
from ..db.channel.base import SmartTagChannel
from ..db.channel_stats import aggregate_stats
from ..db.contact_label import ExplcitTwitterContactLabel

ModelCls = SmartTagChannel


def escape_regex(term):
    term = ''.join([c for c in term if c not in string.punctuation])
    return u"%s" % term


def _item_to_dict(t, user=None):
    return {'id': str(t.id),
            'channel': str(t.parent_channel),
            'created_at': datetime_to_timestamp_ms(t.created),
            'title': t.title,
            'direction': t.direction,
            'description': t.description,
            'keywords': t.keywords,
            'skip_keywords': t.skip_keywords,
            'watchwords': t.watchwords,
            'labels': [str(x) for x in t.contact_label],
            'intentions': t.intentions,
            'status': t.status,
            'groups': [str(group) for group in t.acl],
            'adaptive_learning_enabled': t.adaptive_learning_enabled,
            'perm': t.perms(user) if user else 'r',
            'alert': {
                'is_active': t.alert_is_active,
                'posts_limit': t.alert_posts_limit,
                'posts_count': t.alert_posts_count,
                'emails': t.alert_emails
            },
           }

def _params_from_request(request_data, *allowed_params):
    valid_params = {}
    for param in allowed_params:
        valid_params[param] = request_data.get(param)
    return valid_params


def fetch_items(user, offset=None, limit=None, **kw):
    tags = SmartTagChannel.objects.find_by_user(user, **kw).sort(**{'id': -1})
    if offset is not None:
        tags.skip(int(offset))
    if limit is not None:
        tags.limit(int(limit))
    return tags


def _get_items(user, **kw):
    from_, to_ = kw.pop('from', None), kw.pop('to', None)
    if from_ and to_:
        from_, to_ = parse_date_interval(from_, to_)
    else:
        from_ = to_ = now()

    status = kw.pop('status', None)
    if status:
        kw['status'] = status
    if 'groups' in kw and kw['groups']:
        kw['acl'] = kw.pop('groups')

    adaptive_learning = kw.pop('adaptive_learning_enabled', None)
    if adaptive_learning is not None:
        adaptive_learning = parse_bool(adaptive_learning)
        #kw['adaptive_learning_enabled'] = adaptive_learning

    channel = kw.pop('channel', None)
    if channel:
        from ..db.channel.base import Channel
        try:
            channel = Channel.objects.find_by_user(user, id=channel)[0]
        except:
            return {'ok': False,
                    'message': 'Channel not found.'}
        else:
            kw['parent_channel'] = channel.id

    items = [item for item in fetch_items(user, **kw)
             if adaptive_learning is None or adaptive_learning == item.adaptive_learning_enabled]

    level = guess_timeslot_level(from_, to_)
    item_ids = map(itemgetter('id'), items)
    channel_stats_map = aggregate_stats(
        user, item_ids, from_, to_, level, 
        aggregate=(
            'number_of_posts',
            'number_of_false_negative',
            'number_of_true_positive',
            'number_of_false_positive'))

    for k, v in channel_stats_map.items():
        if v:
            denominator = v['number_of_true_positive']+v['number_of_false_positive']
            if denominator:
                v['presicion'] = float(v['number_of_true_positive'])/denominator
            denominator = v['number_of_true_positive']+v['number_of_false_negative']
            if denominator:
                v['recall']    = float(v['number_of_true_positive'])/denominator
            channel_stats_map[k] = v

    def _to_dict(x):
        obj = _item_to_dict(x, user)
        obj.update({"stats": channel_stats_map.get(str(x.id))})
        return obj
    try:
        return dict(ok=True,
            size=len(items),
            list=[_to_dict(x) for x in items])
    except Exception, e:
        app.logger.error(e)



def _get_item_details(user, item_id):
    try:
        item = ModelCls.objects.find_by_user(user, id=item_id)[0]
    except:
        return {'ok': False,
                'message': '%s not found.' % ModelCls.__name__}

    return {'ok': True,
            'item': _item_to_dict(item, user)}


# @app.route('/post/smart_tags/json', methods=['GET', 'POST', 'DELETE'])
# @login_required()
# def smart_tag_post_assignment_handler(user):
#     data = request.json or request.args
#     params = _params_from_request(data, 'ids', 'post_id', 'channel', 'response_id')
#     params['action'] = {
#         'POST': 'add',
#         'DELETE': 'remove',
#         'GET': 'get'}[request.method]
#     try:
#         result = _handle_post_assignment(user, **params)
#     except RuntimeError, e:
#         app.logger.error(str(e))
#         return jsonify(ok=False, error=unicode(e))
#     except Exception, e:
#         app.logger.error("Exception", exc_info=True)
#         return abort(500)
#     else:
#         return jsonify(result)


@app.route('/smart_tags/json', methods=['GET'])
@login_required()
def handle_smart_tags_list(user):
    if request.method == 'GET':
        allowed_params = ('offset', 'limit', 'channel', 'status',
                          'adaptive_learning_enabled', 'id', 'from', 'to', 'groups')
        valid_params = _params_from_request(request.args, *allowed_params)

        item_id = valid_params.pop('id', None)
        try:
            if item_id:
                #return extended message info
                resp = _get_item_details(user, item_id)
            else:
                resp = _get_items(user, **valid_params)
        except Exception, e:
            app.logger.error(e)
            return abort(500)
        else:
            return jsonify(resp)


@app.route('/smart_tags/<action>/json', methods=['POST'])
@login_required()
def handle_smart_tag_actions(user, action):
    if request.method == 'POST':
        try:
            if action in ('update', 'create'):
                if request.json.get('id', False):
                    old_smt_data = SmartTagChannel.objects.get(id=request.json.get('id')).to_dict()
                else:
                    old_smt_data = None
                allowed_params = (
                    'title', 'description', 'groups',
                    'keywords', 'skip_keywords', 'watchwords',
                    'intentions', 'retweet_count',
                    'labels', 'adaptive_learning_enabled',
                    'channel', 'id', 'alert', 'direction')
                result = _create_update(user, **_params_from_request(request.json, *allowed_params))
                if result['ok'] == True:
                    if request.json.get('id'):
                        new_smt_data = SmartTagChannel.objects.get(id=request.json.get('id')).to_dict()
                    else:
                        new_smt_data = None
                    AccountEvent.create_by_user(user=user,
                                                change='SmartTag %s' % action,
                                                old_data=old_smt_data,
                                                new_data=new_smt_data)
            elif action in ('activate', 'deactivate', 'delete'):
                params = _params_from_request(request.json, 'ids')
                params['action'] = action
                result = _handle_smart_tag_status(user, **params)
                AccountEvent.create_by_user(user=user,
                                            change='SmartTag %s' % action)
            else:
                result = {'ok': False, 'error': 'Unknown action.'}
        except Exception, ex:
            app.logger.error(ex)
            return jsonify(ok=False, error=str(ex))

        return jsonify(**result)


def _create_update(user, **params):
    item_id = params.get('id', None)
    direction = params['direction']
    keywords = params['keywords'] or []
    keywords = [t for t in keywords if t and t.strip()]
    skip_keywords = params['skip_keywords'] or []
    skip_keywords = [t for t in skip_keywords if t and t.strip()]
    watchwords = params['watchwords'] or []
    watchwords = [t for t in watchwords if t and t.strip()]
    intentions = params['intentions'] or []
    intentions = [i for i in intentions if i and i.strip()]
    intention_types = [SATYPE_NAME_TO_TITLE_MAP[i] for i in intentions if SATYPE_NAME_TO_TITLE_MAP.get(i)]
    contact_labels = params['labels'] or []
    groups = params.get('groups', None)
    alert = params.get('alert', None)
    if alert is not None:
        alert_is_active = alert.get('is_active', False)
        alert_posts_limit = alert.get('posts_limit', 100)
        alert_emails = alert.get('emails', [])
    else:
        alert_is_active = False
        alert_posts_limit = 100
        alert_emails = []
    if not groups:
        # Nothing was passed, default to all groups current user has access to + default access for this user role
        groups = [str(g) for g in user.groups]

    #else:
        # Specific group filtering set. Use that
        #acl = groups
    acl = groups + default_access_groups(user)

    channel_id = params['channel']

    # STRIP DEFAULTING FROM UI. Hack.
    keywords = [kw for kw in keywords if kw != '_KW_']
    for label in contact_labels:
        try:
            list(ExplcitTwitterContactLabel.objects.find_by_user(user,id=label))[0]
        except Exception,e:
            return {'ok'    : False,
                    'error' : 'Contact Label with id %s does not exist'%label}

    try:
        from ..db.channel.base import Channel

        parent_channel = list(Channel.objects.find_by_user(user, id=channel_id))[0]
    except Exception, e:
        return {'ok': False,
                'error': 'Channel not found'}
    data = {
        'account': parent_channel.account,
        'parent_channel': parent_channel.id,
        'title': params['title'],
        'direction': direction,
        'description': params['description'],
        'keywords': keywords,
        'skip_keywords': skip_keywords,
        'watchwords': watchwords,
        'intention_types': intention_types,
        'influence_score': 0,
        'contact_label': contact_labels,
        'acl': acl,
        'adaptive_learning_enabled': parse_bool(params['adaptive_learning_enabled']),
        'alert_is_active': alert_is_active,
        'alert_posts_limit': alert_posts_limit,
        'alert_emails': alert_emails
    }

    if item_id:
        try:
            item = ModelCls.objects.find_by_user(user, id=item_id)[0]
        except:
            return {'ok': False,
                    'error': '%s not found.' % ModelCls.__name__}
        if item.title != data['title']:
            if SmartTagChannel.objects(parent_channel=data['parent_channel'], title=data['title']).limit(1).count():
                return {'ok': False,
                        'error': 'Title must be unique'}

        set_data = dict(('set__%s' % key, value) for key, value in data.iteritems())
        try:
            item.update(**set_data)
            item.reload()
        except Exception, ex:
            app.logger.error(ex)
            return {'ok'    : False,
                    'error' : 'Could not update SmartTag, check log for more info'}
    else:
        if SmartTagChannel.objects(parent_channel=data['parent_channel'], title=data['title']).limit(1).count():
            return {'ok': False,
                    'error': 'Title must be unique'}
        data['status'] = 'Active'
        groups = data['acl']
        item = ModelCls.objects.create_by_user(user, **data)
        for group in Group.objects(id__in=groups):
            group.smart_tags.append(item)
            group.save()

    return {'ok': True,
            'item': _item_to_dict(item, user)}


def _handle_smart_tag_status(user, **params):
    """Activate / Deactivate / Delete smart tags"""
    action = params.pop('action')
    ids = params['ids']
    if not isinstance(ids, list):
        ids = [ids]

    from solariat_bottle.commands import ActivateChannel, SuspendChannel, DeleteChannel
    Command = {
        'activate'  : ActivateChannel,
        'deactivate': SuspendChannel,
        'delete'    : DeleteChannel
    }[action]

    try:
        items = list(ModelCls.objects.find_by_user(user, id__in=ids))
        Command(channels=items).update_state(user)
    except Exception, e:
        app.logger.error(e)
        return {'ok': False,
                'error': '%s %s failure.' % (ModelCls.__name__, action)}
    return {'ok': True}


@timed_event
def _handle_post_assignment(user, **params):
    """Manages smart tags assigned to post.

    Expected parameters:
    action = get|add|remove
    ids - smart tag ids (not for action = get)
    post_id
    channel - parent channel id
    """
    action = params.pop('action')
    try:
        from ..db.channel.base import Channel
        parent_channel = list(Channel.objects.find_by_user(user, id=params['channel']))[0]

        # If this is a smart tag then it means we are adding a tag that we are faceting on.
        if parent_channel.is_smart_tag:
            parent_channel = Channel.objects.get(id=parent_channel.parent_channel)
    except Exception, e:
        raise RuntimeError('Channels not found')
    
    if not (parent_channel.is_service or parent_channel.is_inbound) and action in ('add', 'remove'):
        raise RuntimeError('You cannot add or remove tags from outbound channels.')
    
    post_id = params['post_id']
    from solariat_bottle.db.post.base import Post

    try:
        post = Post.objects.find_by_user(user, id=post_id).limit(1)[0]
    except Exception, e:
        raise RuntimeError('Post not found')
    if action in ('add', 'remove'):
        if not post.available_smart_tags:
            raise RuntimeError('No smart tags for the channel')

        ids = params['ids']
        if not isinstance(ids, list):
            ids = [ids]

        tags = list(fetch_items(user, id__in=ids, parent_channel=parent_channel.id))
        if not tags:
            raise RuntimeError('Smart tags not found')

        if not all(tag.adaptive_learning_enabled for tag in tags):
            raise RuntimeError('Smart Tag is read only')

        if action == 'add':
            post.handle_add_tag(user, tags)
        else:
            post.handle_remove_tag(user, tags)
            if params['response_id']:
                try:
                    from ..db.response      import Response
                    response = Response.objects.get(params['response_id'])
                    if response.status == 'pending':
                        # If response was in pending state, reset it's assignee
                        response.assignee = None
                        response.save()
                except Response.DoesNotExist:
                    app.logger.warning("Response with id %s does not exist." % params['response_id'])
                

    items = [_item_to_dict(item, user) for item in post.accepted_smart_tags
             if item.parent_channel == parent_channel.id]

    return {"ok": True, "list": items}

