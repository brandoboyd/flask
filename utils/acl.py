
from solariat_bottle.settings import get_var

from solariat_bottle.db.user  import User
from solariat_bottle.db.group import Group


def get_object_link(obj):
    from ..db.channel.base import Channel
    default_url = '/listen'

    obj_type = obj.__class__.__name__

    if obj_type == 'Bookmark':
        return '/listen'
    elif obj_type == 'SmartTagChannel':
        return '/configure#/tags/edit/%s/' % str(obj.id)
    elif isinstance(obj, Channel):
        return '/configure#/channels'
    elif obj_type == 'Matchable':
        return '/configure#/messages/edit/%s' % str(obj.id)
    elif obj_type == 'Group':
        return '/configure#/groups/edit/%s/' % str(obj.id)
    elif obj_type == 'Account':
        return '/configure#/accounts/'
    elif obj_type == 'ExplcitTwitterContactLabel':
        return '/configure#/labels/edit/%s/' % str(obj.id)

    return default_url


def send_shared_object(msg_type, obj, current_user, user,
                       send_mail,
                       auth_token=None):
    """
    Send an email with link to shared object.
    """

    if not send_mail:
        return

    from urlparse            import urljoin
    from flask               import request
    from solariat.mail       import Message
    from solariat_bottle.app import MAIL_SENDER as mail

    _subject = get_var('SHARE_%s_SUBJECT' % msg_type.upper())
    _body    = get_var('SHARE_%s_BODY' % msg_type.upper())

    # gets object type
    obj_type = obj.__class__.__name__
    temp     = obj_type
    if obj_type.endswith('Channel'):
        temp = 'Channel'
    if obj_type.endswith('ContactLabel'):
        temp = 'Contact Label'
    if obj_type == 'SmartTagChannel':
        temp = 'Tag'
    obj_type = temp
    path = get_object_link(obj)

    if auth_token:
        link = "%susers/%s/password?auth_token=%s&next=/%s" % (
            request.host_url, user.email, auth_token.digest, path)
    else:
        #link = "%s%s" % (request.host_url, path)
        link = urljoin(request.host_url, path)

    _template = {'username': current_user.email,
                 'link': link,
                 'title': getattr(obj, 'title', None) or unicode(obj),
                 'object_type': obj_type}

    msg = Message(subject = _subject % _template)
    msg.recipients = [user.email]
    msg.body = _body % _template
    #LOGGER.debug(msg.body)
    mail.send(msg)


def send_shared_objects_bulk(objs, current_user, user, send_mail, auth_token=None):
    """
    Send an email with link to shared object.
    """
    if not send_mail or not objs:
        return

    from urlparse            import urljoin
    from flask               import request, render_template
    from solariat.mail       import Message
    from solariat_bottle.app import MAIL_SENDER as mail

    #_subject = get_var('SHARE_%s_SUBJECT_BULK' % msg_type.upper())
    #_body    = get_var('SHARE_%s_BODY_BULK'    % msg_type.upper())

    # gets object type
    obj_type = objs[0].__class__.__name__
    temp = obj_type
    if obj_type.endswith('Channel'):
        temp = 'Channel'
    if obj_type.endswith('ContactLabel'):
        temp = 'Contact Label'
    if obj_type == 'SmartTagChannel':
        temp = 'Tag'
    obj_type = temp

    objs_for_email = []
    for obj in objs:
        path = get_object_link(obj)
        if auth_token:
            link = "%susers/%s/password?auth_token=%s&next=/%s" % (
                request.host_url, user.email, auth_token.digest, path)
        else:
            link = urljoin(request.host_url, path)
        objs_for_email.append((
            getattr(obj, 'title', None) or unicode(obj),
            link
        ))

    msg = Message(subject="New shared %s" % obj_type)
    msg.recipients = [user.email]
    msg.body = render_template(
        "mail/send_shared_objects_bulk.html",
        objs=objs_for_email,
        username=current_user.email,
        object_type=obj_type
    )
    #LOGGER.debug(msg.body)
    mail.send(msg)


def share_object_by_user(current_user, object_type, objects, users, send_email=True):
    """
    List of objects to be shared within given users.
    An user object is: email:perms:action
    """
    if not objects:
        return (False, "No %ss selected. Choose at least 1 %s to share." % (
            object_type, object_type))

    if not users:
        return False, "No Users found. Add at least 1 email address to share selected %ss." % object_type

    # Current user should have edit access to account
    if not current_user.account:
        return False, "You must have account."

    def _get_data(u):
        if isinstance(u, basestring):
            a = u.split(':')
            return a[0], a[1]
        else:
            return u['email'], u['action']

    for u in users:
        email, action = _get_data(u)
        # do not allow current user to withdraw permissions
        if current_user.email == email:
            continue

        # check if user is already registered
        exist_user = User.objects.find_one(email=email.lower())
        if exist_user and exist_user.is_superuser:
            return False, "User '%s' already has access as superuser."

        auth_token = None
        objs_for_email = []

        if not exist_user:
            return False, "Creating new users should be done through separate endpoint"

        for obj in objects:
            # if user have no write permission on account,
            # we can't create a new user and assign account to them
            if object_type == 'account' and not obj.can_edit(current_user):
                return False, "%s is not registered. Creating new user requires write permission on account." % email
            # add/delete perms for users who have already some perms
            if action == 'add':
                obj.add_perm(exist_user)
                objs_for_email.append(obj)
            elif action == 'del':
                obj.del_perm(exist_user)
                objs_for_email.append(obj)
                if object_type == 'account':
                    # In case we remove a user from an account, automatically
                    # set a new current account, if he has permissions on other accounts.
                    remaining_accounts = exist_user.available_accounts
                    if remaining_accounts:
                        exist_user.current_account = remaining_accounts[0]
        send_shared_objects_bulk(objs_for_email, current_user, exist_user, send_email, auth_token)

    return True, "OK"

def share_with_groups_by_user(user, object_type, objects, group_perms):
    if not group_perms:
        return True, "OK"

    for gp in group_perms:
        if not gp:
            continue

        try:
            group = Group.objects.find_by_user(user, id=gp['id'])[0]
        except (Group.DoesNotExist, IndexError):
            return False, "Group %s does not exist." % gp['id']

        for obj in objects:
            if object_type == 'group' and obj.id == group.id:
                continue
            if not gp['is_new']:
                if gp['action'] == 'add':
                    obj.add_perm(group)
                    obj.add_perm(group)
                elif gp['action'] == 'del':
                    obj.del_perm(group)
                    # add perms for users who do not have any perms yet
    return True, "OK"





def get_users_and_groups_with_perms(objects, skip_su=True):
    """
    Retrieves the set of users and groups with access levels for all objects.

    Example result tuple:
    (
        [{"id": "user_id1",
          "email": "test@test.ts",
          "perm": "r"},
         {"id": "user_id2":
          "email": "userc@user.com",
          "perm": "rw"}
        }],

        [{"id:"group_id1",
         "name": "group_name",
         "perm": "r"}
        }]
    )

    r - can view
    rw - can edit
    s - superuser (not used)

    When there are more than one object, the permissions for each user/group
    are computed as the intersection of their permissions in each object.

    """
    # A dictionary for perms as a set
    user_perms = {}
    group_perms = {}

    empty_perms = {}

    # Initialize sets for all user ids.
    for obj in objects:
        users, groups = users_and_groups_by_acl(obj)
        user_perms.update( dict( (str(u.id), {'email': u.email, 'perm': set(['r', 'w', 'd'])}) for u in users ) )
        group_perms.update( dict( (str(g.id), {'name': g.name, 'perm': set(['r', 'w', 'd'])}) for g in groups ) )
        for u in users:
            empty_perms[str(u.id)] = set()
        for g in groups:
            empty_perms[str(g.id)] = set()

    import copy
    # Now process the objects one by one
    for obj in objects:
        # Set empty set for all users
        this_object_perms = copy.deepcopy(empty_perms)

        # Fill entries as we find them
        for a in obj.acl:
            a = a.split(':')
            if a[0] == 'g':
                a = a[1:]  #skip group mark
            this_object_perms[a[0]].add(a[1])

        # Now process these perms for intersection with global list
        for object_id, value in this_object_perms.items():
            if object_id in user_perms:
                user_perms[object_id]['perm'] = user_perms[object_id]['perm'].intersection(value)
            elif object_id in group_perms:
                group_perms[object_id]['perm'] = group_perms[object_id]['perm'].intersection(value)

    # Add/set entry for all super users. Superuser dominates
    for su in User.objects(is_superuser=True):
        #LOGGER.debug("Setting for super user: %s" % su.email)
        user_perms[str(su.id)] = {"email": su.email, "perm": set(['s'])}

    #LOGGER.debug(user_perms)

    #Remove user entries with empty permissions set
    #or super users
    user_perm_list = []
    for user_id, v in user_perms.iteritems():
        if not v['perm'] or 's' in v['perm'] and skip_su:
            continue
        else:
            user_dict = user_perms[user_id]
            user_dict['id'] = user_id
            user_dict['perm'] = "".join(list(v['perm']))
            user_perm_list.append(user_dict)

    #Remove group entries with empty permissions set
    group_perm_list = []
    for group_id, v in group_perms.iteritems():
        if not v['perm']:
            continue
        else:
            group_dict = group_perms[group_id]
            group_dict['id'] = group_id
            group_dict['perm'] = "".join(list(v['perm']))
            group_perm_list.append(group_dict)

    return user_perm_list, group_perm_list

def user_ids_by_acl(obj):
    if not hasattr(obj, 'acl'):
        raise RuntimeError(u'Object %s has no ACL.' % obj)

    acl = set(obj.acl)
    user_ids = set([a.split(':')[0] for a in acl if not a.startswith('g:')])
    return user_ids


def users_by_acl(obj, clean_acl=True):
    """
    Iterates through acl list, checks all Users exist and pops off the superuser entries.

    Returns list of users instantiated by cleaned acl list.
    """

    if not hasattr(obj, 'acl'):
        raise RuntimeError(u'Object %s has no ACL.' % obj)

    acl = set(obj.acl)
    user_ids = list(set([a.split(':')[0] for a in acl if not a.startswith('g:')]))
    users = [u for u in User.objects.find(id__in=user_ids) if not u.is_superuser]

    if clean_acl:
        accepted_user_ids = set([str(u.id) for u in users])
        def _group_or_accepted_user_id(acl_item):
            return acl_item.startswith('g:') or acl_item.split(':')[0] in accepted_user_ids

        cleaned_acl = set(filter(_group_or_accepted_user_id, acl))

        #if acl changed
        if cleaned_acl != acl:
            obj.acl = list(cleaned_acl)
            obj.save()

    return users

def _get_str_id(o):
    return str(o.id)


def users_and_groups_by_acl(objs, clean_acl=True):
    users = set([])
    groups = set([])
    for obj in objs:
        if not hasattr(obj, 'acl'):
            raise RuntimeError(u'Object %s has no ACL.' % obj)
        acl = set(obj.acl)
        users.update(User.objects.find(id__in=obj.acl)[:])
        groups.update(Group.objects.find(id__in=obj.acl)[:])
    return users, groups
