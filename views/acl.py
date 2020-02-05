import json
import re
import string
from bson import ObjectId

from flask import (request, jsonify)
from solariat_bottle.app import app, AppException
from solariat_bottle.db.account import Account, AccountEvent
from solariat_bottle.db.user import User
from solariat_bottle.db.group import Group
from solariat_bottle.db.roles import ADMIN, STAFF, AGENT, ANALYST, SYSTEM, REVIEWER

from solariat_bottle.utils.acl import share_with_groups_by_user
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.utils.acl import share_object_by_user, users_and_groups_by_acl
from solariat_bottle.utils.mailer import send_user_create_notification


def cls_by_name(cls_name):
    from solariat_bottle.db.channel.base import Channel
    from solariat_bottle.db.contact_label import ExplcitTwitterContactLabel

    return {'channel': Channel,
            'smarttag': Channel,
            'account': Account,
            'contactlabel': ExplcitTwitterContactLabel,
            'group': Group}[cls_name.lower()]


def reactivate_user(logged_user, user):
    email = user.email
    user_db = User.objects.coll.find({User.email.db_field: email}).next()
    reactivated_user = User(user_db)
    reactivated_user.is_archived = False
    logged_user.current_account.add_perm(reactivated_user)
    reactivated_user.save()
    return True


def iexact(text):
    escaped = re.compile("([%s])" % string.punctuation).sub(r'\\\1', text)
    return u"^%s$" % escaped


@app.route('/acl/json', methods=['POST'])
@login_required()
def acl_handler(user):
    """
    Expected parameters in json-encoded payload:
    id - list of objects to be shared or which access permissions requested
    a - get|share (get - return users with permissions, share - change or add new permissions)
    ot - object type (bookmark, channel, etc)
    up - list of emails with permissions (received when a=share)
    """
    try:
        payload = json.loads(request.data)
    except:
        return jsonify(ok=False, result="Invalid payload")

    objects_ids = payload.get('id', [])
    if not objects_ids:
        return jsonify(ok=False, result="No objects to share")

    object_type = payload.get('ot', 'bookmark')
    action = payload.get('a', 'get')

    object_cls = cls_by_name(object_type)
    objects = list(object_cls.objects.find_by_user(user=user, id__in=objects_ids))

    #user must have write perm to share objects
    for o in objects:
        if not o.can_edit(user):
            return jsonify(ok=False, result="User has no permission to share")
    if action == 'get':
        users, groups = users_and_groups_by_acl(objects)
        account_admins = user.objects.find(account=user.account, user_roles__in=[ADMIN, STAFF])[:]
        users.update(account_admins)
        users_json = [u.to_dict() for u in users]
        groups_json = [g.to_dict() for g in groups]

        if object_type == 'account' and payload.get('extended'):
            #Populate list of users with accounts
            from ..views.account import _json_account
            user_accounts = {}
            for u in users:
                acct_list = [_json_account(a, u) for a in u.available_accounts]
                user_accounts[str(u.id)] = acct_list
            for u in users_json:
                u['accounts'] = user_accounts.get(u['id'], [])

        resp = {'ok': True,
                'result': {'users': users_json, 'groups': groups_json}}
        return jsonify(**resp)

    elif action == 'share':
        users = payload.get('up')
        groups = payload.get('gp')

        ok, ok1 = True, True
        result, result1 = "", ""

        if users:
            ok, result = share_object_by_user(user, object_type, objects, users, send_email=True)
            if object_type == 'bookmark':
                # share bookmarks only if users have access to correspondent channels?
                # Share bookmarks' channels for now. The channels will have the same access level as bookmarks.
                channels = [b.channel for b in objects]
                share_object_by_user(user, 'channel', channels, users, send_email=False)
            if not groups:
                return jsonify(ok=ok, result=result)

        if groups:
            ok1, result1 = share_with_groups_by_user(user, object_type, objects, groups)
            if not users:
                return jsonify(ok=ok1, result=result1)

        return jsonify(ok=ok and ok1, result=' '.join([r for r in (result, result1) if r != 'OK']))

    return jsonify(ok=False, result="Unknown action")


@app.route('/user_roles/json', methods=['GET'])
@login_required()
def user_roles(user):
    """ Return the list of all available user roles """
    return jsonify(ok=True, list=user.accessible_roles)


@app.route('/users/json', methods=['GET'])
@login_required()
def user_list(user):
    """ Return all the users to which this current user would have access to. """
    if user.is_staff:
        users_list = [u.to_dict() for u in user.objects.find(account=user.current_account, user_roles__in=[STAFF, ADMIN, AGENT, ANALYST, SYSTEM, REVIEWER])]
    else:
        if user.is_admin:
            users_list = [u.to_dict() for u in user.objects.find(account=user.current_account, user_roles__in=[ADMIN, AGENT, ANALYST, SYSTEM, REVIEWER])]
        else:
            users_list = {}

    #users_list = [u.to_dict() for u in user.objects.find(account=user.current_account, user_roles__in=[AGENT])]
    # TODO: We need to check if the user is STAFF or ADMIN, otherwise should not have access to this
    #users_list = [u.to_dict() for u in user.objects.find(account=user.current_account)]
    return jsonify(ok=True, list=users_list)


@app.route("/users/edit/json", methods=['POST', 'GET'])
@login_required()
def crud_user(user):
    authenticated_user = user
    if request.method == 'POST':
        payload = request.json
        if not (user.is_admin or user.is_staff or str(payload.get('id')) == str(user.id)):
            return jsonify(ok=False, error="Only admins can create or edit users.")
        #check user data validity
        first_name = payload.get('first_name')
        last_name = payload.get('last_name')
        if not first_name or not last_name:
            return jsonify(ok=False, error="Both first and last name need to be provided.")
        email = payload.get('email')
        if not email:
            return jsonify(ok=False, error="Email needs to be provided and unique.")
        if user.objects(email=email).count() > 0 and not payload.get('id'):
            return jsonify(ok=False, error="There is already a user with the same email.")
        user_roles = [int(role) for role in payload.get('roles', [])]
        if not user_roles:
            return jsonify(ok=False, error="At least one role needs to be specified.")

        filters = dict(
            account=user.current_account,
            first_name__regex=iexact(first_name),
            first_name__options='i',
            last_name__regex=iexact(last_name),
            last_name__options='i')
        users_exist = list(user.objects.find(**filters).limit(1))
        if users_exist and str(users_exist[0].id) != payload.get('id'):
            return jsonify(ok=False, error="There is already a user with the same name.")

        groups = [ObjectId(g_id) for g_id in payload.get('groups', [])]
        signature = payload.get('signature')
        if payload.get('id'):
            try:
                user = user.objects.get(payload.get('id'))
            except user.DoesNotExist:
                return jsonify(ok=False, error="No user was found with the given id.")
            old_user_data = user.to_dict()
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.user_roles = user_roles
            user.groups = groups
            try:
                user.signature = signature
                user.save()
            except AppException as e:
                return jsonify(ok=False, error=str(e))
            if 'password' in payload and 'passwordConfirm' in payload:
                if payload['password'] == payload['passwordConfirm']:
                    user.set_password(payload['password'])
            user.save()
            new_user_data = user.to_dict()
            AccountEvent.create_by_user(user=authenticated_user,
                                        change='User edit',
                                        old_data=old_user_data,
                                        new_data=new_user_data)
            _filtered_user_dict = user.to_dict()
            _filtered_user_dict.pop('password', None)
            return jsonify(ok=True, user=_filtered_user_dict)
        else:
            try:
                user = user.objects.create(email, password=None, is_superuser=False, groups=groups,
                                           account=user.current_account, external_id=None,
                                           first_name=first_name, last_name=last_name, user_roles=user_roles,
                                           signature=signature)
                try:
                    send_user_create_notification(user)
                except Exception, err:
                    app.logger.exception('Send mail notification to newly created user failed.')
                return jsonify(ok=True, user=user.to_dict())
            except Exception, e:
                return jsonify(ok=False, error=str(e))
    elif request.method == 'GET':
        email = request.args.get('email')
        u_id = request.args.get('id')
        if not email and not u_id:
            return jsonify(ok=False, error="No email or id specified to get user by.")
        try:
            if u_id:
                user = user.objects.get(u_id)
            else:
                user = user.objects.get(email=email)
        except user.DoesNotExist:
            return jsonify(ok=False, error="No user exists for email=%s" % email)
        _filtered_user_dict = user.to_dict()
        _filtered_user_dict.pop('password', None)
        return jsonify(ok=True, user=_filtered_user_dict)

@app.route("/users/check_user_archived/json", methods=['POST'])
@login_required()
def check_user_archived(user):
        logged_user = user
        payload = request.json
        u_payload = payload.get('user')
        email = u_payload.get('email')
        #counting = user.objects(email=email).count()
        counting = User.objects.coll.find({User.email.db_field: email}).count()
        if counting == 0 and not u_payload.get('id'):
            response = jsonify(ok=False, message="No Dialog")
            return response
        else:
            if counting > 0:
                user_db = User.objects.coll.find({User.email.db_field: email}).next()
                user = User(user_db)
                if user.is_archived:
                    if reactivate_user(logged_user, user):
                        response = jsonify(ok=True, message="Dialog")
                        return response
                else:
                    response = jsonify(ok=False, message="No Dialog")
                    return response


@app.route("/users/add_to_account/json", methods=['POST'])
@login_required()
def add_to_account(user):
    if not user.is_staff:
        response = jsonify(ok=False, message="Only staff can add other users to account.")
        return response
    payload = request.json
    u_payload = payload.get('user')
    email = u_payload.get('email')
    try:
        user_to_add = User.objects.get(email=email)
    except user.DoesNotExist:
        response = jsonify(ok=False, message="User with such email does not exist.")
        return response
    if not user_to_add.is_staff:
        response = jsonify(ok=False, message="User with this email is not staff.")
        return response
    account = user.current_account
    if not account.id in user_to_add.accounts:
        user_to_add.accounts.append(account.id)
    user_to_add.current_account = account
    user_to_add.save()
    response = jsonify(ok=True, message="User is added to account")
    return response


@app.route("/users/remove_from_account/json", methods=['POST'])
@login_required()
def remove_from_account(user):
    if not user.is_staff:
        response = jsonify(ok=False, message="Only staff can remove other users from account.")
        return response
    payload = request.json
    user_id = payload.get('user_id')
    try:
        user_to_remove = User.objects.get(id=user_id)
    except user.DoesNotExist:
        response = jsonify(ok=False, message="User with such id does not exist.")
        return response
    if not user_to_remove.is_staff:
        response = jsonify(ok=False, message="This user is not staff.")
        return response
    account = user.current_account
    if account.id in user_to_remove.accounts:
        user_to_remove.accounts.remove(account.id)
    if user_to_remove.accounts:
        user_to_remove.account = Account.objects.get(id=
            user_to_remove.accounts[0])
    else:
        user_to_remove.account = None
    user_to_remove.save()
    response = jsonify(ok=True, message="User is remove from account")
    return response


@app.route("/users/delete/json", methods=['POST'])
@login_required()
def delete_user(user):
    """Deletes user from system. (We archive all deleted users.)

    POST payload:

    id: user id
    """
    payload = request.json
    if not (user.is_admin or user.is_staff or str(payload.get('id')) == str(user.id)):
        return jsonify(ok=False, error="Only admins can delete users.")
    try:
        user_to_delete = User.objects.get(payload.get('id'))
    except User.DoesNotExist:
        return jsonify(ok=False, error="Such user does not exist.")

    if user_to_delete.is_superuser:
        return jsonify(ok=False, error="Nobody can delete super_user.")

    # admin < staff < super_user
    if not user.is_staff and user_to_delete.is_staff:
        return jsonify(ok=False, error="%s can't delete %s" % (user.email, user_to_delete.email))

    user_to_delete.account = None
    for group in user_to_delete.groups:
        try:
            db_group = Group.objects.get(group)
        except Group.DoesNotExist:
            app.logger.warn("Group (%s) of a user (%s) to be deleted doesn't exist.", group, user_to_delete.email)
            continue
        else:
            db_group.del_user(user_to_delete)

    user_to_delete.archive()
    user_to_delete.user_roles = []
    user_to_delete.save()

    #user.objects.remove(id=str(user.id))
    return jsonify(ok=True, error="User is deleted.")


@app.route("/users/staff/json", methods=["GET"])
@login_required(allow_app_access=True)
def staff_users_view(user):
    if not (user.is_staff or user.is_admin):
        return jsonify(ok=False, error="Insufficient user privileges")

    staff_users = []
    if user.is_staff:
        staff_users = [u.email for u in User.objects(
            is_superuser=False, user_roles__in=[STAFF]).sort(email=True)]
    elif user.is_admin:
        account_csm = user.current_account.customer_success_manager
        staff_users = account_csm and [account_csm.email] or []

    return jsonify(ok=True, users=staff_users)
