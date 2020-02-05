from functools import partial
from flask import request, jsonify

from solariat_bottle.app              import app
from solariat_bottle.db.group         import Group
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.user import User
from solariat_bottle.utils.decorators import login_required


def _to_user_message(s):
    """
    :param s: string with error message from exception
    :return: a message more readable by a user, if no mapping exists returns ``s``
    """
    ERROR_TO_MESSAGE = {
        "'NoneType' object is not iterable":  "Error accessing database, please try later."
    }
    return ERROR_TO_MESSAGE.get(s, s)


@app.route('/alert_user_candidates', methods=['GET'])
@login_required()
def alert_user_candidates(user):
    return jsonify(ok=True, list=[u.to_dict() for u in User.objects(account=user.account) if not u.is_system])


@app.route('/groups/<action>/json', methods=['POST'])
@login_required()
def groups_actions_handler(user, action):
    data = request.json
    group_id = data.get('id')

    if not group_id:
        return jsonify(ok=False, error="Group id required")

    if isinstance(group_id, list):
        q = {"id__in": group_id}
    else:
        q = {"id": group_id}
        group_id = [group_id]

    groups = list(Group.objects.find_by_user(user, **q))
    if not groups:
        Channel.objects.remove_groups_by_user(user, group_id)
        #return jsonify(ok=False, error=u"Group %s not found" % group_id)

    if action == 'get_users':
        users = []

        def _user_dict(u, group):
            return {'id':str(u.id),
                    'email':u.email,
                    'gid':str(group.id)}

        for group in groups:
            users.extend([_user_dict(u, group) for u in group.members])

        return jsonify(ok=True, users=users)

    return jsonify(ok=False, error="unknown action")


@app.route('/groups/json', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required()
def groups_handler(user):
    """
    Groups CRUD for superuser.
    """
    if request.method == 'GET':
        group_id = request.args.get('id')
        if group_id:
            group = list(Group.objects.find_by_user(user, id=group_id))
            if not group:
                return jsonify(ok=False, error=u"Group %s not found" % group_id)
            group_dict = group[0].to_dict()
            if user.is_admin or user.is_staff:
                group_dict['perm'] = 'wr'
            else:
                group_dict['perm'] = 'r'
            return jsonify(ok=True, group=group_dict)
        available_groups = _query_groups(user)
        return jsonify(ok=True, data=available_groups)

    elif request.method == 'POST':
        params = request.json
        ok, result = _create_group(user, **params)
        if ok:
            return jsonify(ok=ok, group=result.to_dict())
        else:
            return jsonify(ok=ok, error=_to_user_message(result))

    elif request.method == 'DELETE':
        if not user.is_admin:
            return jsonify(
                ok=False,
                error="Attempting to remove group can only be done by admin or staff.")
        data = request.args
        if not data:
            return jsonify(ok=False, error='no parameters provided')
        _id = data['id']
        ok, error = _delete_groups(user, _id)
        return jsonify(ok=ok, error=error)

    elif request.method == 'PUT':
        data = request.json
        ok, result = _update_group(user, **data)
        if ok:
            return jsonify(ok=ok, group=result.to_dict())
        else:
            return jsonify(ok=ok, error=result)


def _valid_group_params(params):
    allowed = ['name', 'description', 'members', 'roles', 'channels', 'smart_tags',
            'journey_types', 'journey_tags', 'funnels', 'predictors']
    return dict((k, params.get(k)) for k in allowed)


def _create_group(user, **params):
    if params.get('id'):
        return _update_group(user, **params)

    #check uniqueness
    name = params.get('name')
    if not name:
        return False, "Name is required."
    channels = params['channels']
    if not params['channels']:
        return False, "At least one channel needs to be set."
    exists = Group.objects.find(name=name, account=user.account).count()
    if exists:
        return (
            False,
            "Group with name '%s' already exists for this account. Please provide another name."
                % name)
    group = Group.objects.create_by_user(user, **_valid_group_params(params))
    return True, group


def _query_groups(user):
    return [group.to_dict() for group in Group.objects.find_by_user(user)]


def filter_accessible(old, new, predicate=None):
    old_set = set(old)
    new_set = set(new)
    added_items = new_set - old_set
    removed_items = old_set - new_set

    if predicate is not None:
        added_items = filter(predicate, added_items)
        removed_items = filter(predicate, removed_items)

    new_items = list(set(old).union(set(added_items)) - set(removed_items))
    return new_items


def editable_roles_filter(current_user, role):
    if current_user.is_superuser:
        return True

    if not current_user.roles:
        return False

    return int(role) <= int(max(current_user.user_roles))

def editable_users_filter(current_user, user):
    return current_user.perms(user) == 'w'

def _update_group(user, **data):
    if not (user.is_staff or user.is_admin):
        raise RuntimeError("Only admin and staff users are allowed to create groups.")

    name = data.get('name')
    if not name:
        return False, "Name is required."

    groups = Group.objects.find_by_user(user, id=data['id'])
    group = groups and groups[0]
    if not (group and group.can_edit(user)):
        return False, "The permission required to edit group."

    if name != group.name:
        exists = Group.objects.find(name=name, account=user.account).count()
        if exists:
            return (
                False,
                "Group with name '%s' already exists for this account. Please provide another name."
                    % name)

    data['roles'] = filter_accessible(old=group.roles,
                                      new=data['roles'],
                                      predicate=partial(editable_roles_filter, user))
    _new_members = [User.objects.get(uid) for uid in data['members']]
    data['members'] = filter_accessible(old=group.members,
                                        new=_new_members,
                                        predicate=partial(editable_users_filter, user))
    data['members'] = [u.id for u in data['members']]

    group.update(user, **_valid_group_params(data))
    return True, group


def _delete_groups(user, ids):
    if ',' in ids:
        ids = ids.split(',')
    if not isinstance(ids, list):
        if not ids:
            return False, "Groups not found"
        ids = [ids]

    #Verify groups are empty
    groups = list(Group.objects.find_by_user(user, id__in=ids))
    if not groups:
        return False, "Groups not found"

    for group in groups:
        if not group.can_edit(user):
            return False, "The permission required to delete group."
        group.clear_users()
        if group.get_users(user):
            return False, "Can't delete group with assigned users."

    try:
        Group.objects.remove_by_user(user, id__in=ids)
    except Group.DoesNotExist, e:
        return False, "Trying to remove a group which was already removed."
    return True, ""
