# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat.db import fields
from solariat.exc.base import AppException
from solariat_bottle.db.roles import ADMIN, STAFF, USER_ROLES
from solariat.db.abstract import Manager, Document
from solariat_bottle.db.group import (
    Group, default_admin_group, default_agent_group, default_analyst_group,
    default_reviewer_group)

from solariat_bottle.settings import LOGGER, AppException


def default_access_groups(user, ignore_admins=False):
    """ Return the default groups we use in case a object is not restricted
     to some specific groups. These groups are inferred based on the user role
     of the creation: AGENT, ANALYST or REVIEWER.
    """
    groups = []
    if user.is_admin and not ignore_admins:
        groups.append(default_admin_group(user.current_account))
    if user.is_reviewer:
        groups.append(default_reviewer_group(user.current_account))
    if user.is_agent:
        groups.append(default_agent_group(user.current_account))
    if user.is_analyst:
        groups.append(default_analyst_group(user.current_account))
    return groups


def get_user_access_groups(user):
    """ Return the entire access control to which a user should have access
     based on his groups, id and accounts
    """
    group_access = [str(o) for o in user.groups] + [str(user.id)]  # Base access groups is set of group
    if user.current_account:
        # Also add any objects which have perm for this entire account
        group_access.extend(default_access_groups(user))
    return group_access


class AuthError(AppException):
    "Raise on any problem with permissions"
    http_code = 401
    code = 13


class AuthMixin(object):
    """
    Add auth methods to Document.
    This doc must have a list of groups which actually have permissions to it.
    Base class just checks general permissions. Any specific read/write permissions
    will be handled in specific classes based on user roles.
    """
    admin_roles = set([STAFF, ADMIN])   # The set of roles which could edit the given document.
                                        # We can overwrite in specific classes as needed!
    @classmethod
    def create_rights(cls, user):
        """ Check if a user has create rights on a given class based on his role """
        return bool(set(user.user_roles).intersection(cls.admin_roles)) or user.is_superuser or user.is_staff

    @classmethod
    def class_based_access(cls, account):
        """ Based on the AUTH class we are creating, we might offer some default access
        to certain groups from the account. By default, permissions should only be given to
        admin type users. This can be overwritten in specific classes as needed. E.G. messages -> agents ?
        """
        if account is None:
            return []
        return default_admin_group(account)

    @staticmethod
    def _get_group_id(group):
        if isinstance(group, Group):
            return str(group.id)
        return str(group)

    def add_perm(self, user, group=None, to_save=True):
        """ Add permission for a user to a given item.
         If no specific group passed in, then just user the generic group for account. """
        if group:
            self.acl.append(self._get_group_id(group))
        else:
            if str(user.id) not in self.acl:
                self.acl.append(str(user.id))
        if to_save:
            self.save()

    def del_perm(self, user, group=None, to_save=True):
        """ Remove permission for a user to a given item.
         If no specific group passed in, then just user the generic group for account. """
        existing_groups = self.acl
        if group and self._get_group_id(group) in existing_groups:
            existing_groups.remove(self._get_group_id(group))
        else:
            # Remove access from specific user
            if str(user.id) in existing_groups:
                existing_groups.remove(str(user.id))
            # We also need to remove any general access if we want user to no longer have access
            if user.is_admin:
                warning_msg = "User you are removing is an admin. Removing access to all admins from object %s" % self
                LOGGER.warning(warning_msg)
            for default_access in default_access_groups(user):
                if default_access in existing_groups:
                    existing_groups.remove(default_access)
        self.acl = existing_groups
        if to_save:
            self.save()

    def has_perm(self, user_or_group):
        """ Check if either a user or a group has permissions to this current object
        In case of users, this would mean the user is part of ANY group which has
        permissions to the object. In case of a group, simply check if it's in list
        of groups for object.
        """
        from solariat_bottle.db.user import User
        if user_or_group is None:
            return False
        if not isinstance(user_or_group, (User, Group)):
            raise AppException("%s should be User or Group" % user_or_group)
        if isinstance(user_or_group, User):
            if user_or_group.is_superuser:
                return True
            group_access = get_user_access_groups(user_or_group)
            # User sting id since at this point it should be rather cost-less and will allow usage
            # of both objects ids and string ids when you want to add/remove temporary perms (to_save=False)
            user_acl = set([str(o) for o in group_access])
            object_acl = set([str(o) for o in self.acl])
            if user_acl.intersection(object_acl):
                return True
        elif isinstance(user_or_group, Group):
            return str(user_or_group.id) in set([str(o) for o in self.acl])
        return False

    def can_view(self, user_or_group):
        """ Return True if read perm exists. """
        return self.has_perm(user_or_group)

    def can_edit(self, user_or_group, admin_roles=None):
        """ Return True if write perm exists. By default we assume only admins
         and staff have permissions to edit. If any specific roles are passed in,
         user those instead."""
        admin_roles = admin_roles or self.admin_roles
        base_check = self.has_perm(user_or_group)   # Basic check that it has permissions to object
        edit_check = (bool(set(admin_roles).intersection(set(user_or_group.user_roles)))
                      or (hasattr(user_or_group, 'is_superuser') and user_or_group.is_superuser))
        return base_check and edit_check

    def perms(self, user_or_group):
        """ Return a permissions string for given user or group.
         Just assume read/write if groups intersect. Specific classes should
         overwrite as needed based on ROLES."""
        if user_or_group.is_superuser:
            return "s"

        perm = "-"
        if self.can_edit(user_or_group):
            return "rw"
        if self.can_view(user_or_group):
            return "r"
        return perm

    def save_by_user(self, user, **kw):
        """ Check user has perms, then save """
        if self.can_edit(user):
            return Document.save(self, **kw)
        raise AuthError("%s has no write perm on %s" % (user, self))

    def delete_by_user(self, user, **kw):
        """ Check user has w perm then delete """
        if self.has_perm(user):
            return self.objects.remove_by_user(user, self.id)
        raise AuthError("%s has no perms to delete %s" % (user, self))


class AuthManager(Manager):

    @staticmethod
    def get_permission_query(user):
        """ Whenever we query for a AuthObject make sure we check that user
         has permissions. The entire permission id which we should check is:
          - user groups (for group shared objects)
          - user id (for individually shared objects)
          - account specific groups (for now only the account id, as in __ALL USERS FROM ACC__
        """
        if user.is_superuser:
            return {}
        return {'acl': {'$in': get_user_access_groups(user)}}

    def populate_acl(self, user, kw):
        if user.is_superuser:
            # In case a superuser will create some objects, we can't default to their groups
            # Just use default groups based on the created class. E.G. Messages -> Agents + Admins
            if 'acl' not in kw or not kw['acl']:
                kw['acl'] = self.doc_class.class_based_access(user.current_account)
                return

        groups = kw.get('acl', [])
        account = kw.get('account', None) or user.current_account

        admin_perms = default_admin_group(account)
        if not groups:
            groups = default_access_groups(user)
        # No matter what was the case, admins of the account should have access
        if admin_perms not in groups:
            groups.append(admin_perms)
        if str(user.id) not in groups:
            groups.append(str(user.id))
        kw['acl'] = groups

    def create_by_user(self, user, **kw):
        if user.is_superuser:
            self.populate_acl(user, kw)
            return self.create(**kw)
        if not user.current_account:
            # For a non-staff user it doesn't make any sense to create objects w/o having a current account
            raise RuntimeError("Non staff members should always have a current account set in order to create objects")
        if not self.doc_class.create_rights(user):
            # No create rights to the given class
            raise RuntimeError("Only %s roles have create rights on %s class. Current user roles: %s." % (
                tuple([USER_ROLES[role] for role in self.doc_class.admin_roles]), self.doc_class.__name__, user.roles)
            )
        self.populate_acl(user, kw)
        return self.create(**kw)

    def remove_by_user(self, user, *args, **kw):
        kw.update(self.get_permission_query(user))
        if args:
            kw['id'] = args[0]
        Manager.remove(self, **kw)

    def get_by_user(self, user, *args, **kw):
        if kw.get('id') and isinstance(kw['id'], (str, unicode)) and kw['id'].isdigit():
            kw['id'] = long(kw['id'])
        kw.update(self.get_permission_query(user))
        if args:
            kw['id'] = long(args[0]) if str(args[0]).isdigit() else args[0]
        return Manager.get(self, **kw)

    def find_by_user(self, user, perm='r', **kw):
        if kw.get('id') and isinstance(kw['id'], (str, unicode)) and kw['id'].isdigit():
            kw['id'] = long(kw['id'])
        kw.update(self.get_permission_query(user))
        return Manager.find(self, **kw)

    def find_one_by_user(self, user, **kw):
        kw.update(self.get_permission_query(user))
        return Manager.find_one(self, **kw)


class AuthDocument(Document, AuthMixin):
    acl = fields.ListField(fields.StringField(), db_field='acl')

    manager = AuthManager

    def to_dict(self, fields_to_show=None):
        # Switch groups from object ids to string ids so we can json objects
        d = super(AuthDocument, self).to_dict(fields_to_show)
        d['groups'] = [str(group) for group in self.acl]
        return d


class ArchivingAuthManager(AuthManager):
    """ Support archiving instead delete on delete_by_user """
    def get_query(self, **kw):
        ignore_archived = not kw.pop('include_safe_deletes', False)
        query = AuthManager.get_query(self, **kw)
        if ignore_archived:
            query.setdefault('is_archived', False)
        return query

    def archive_update_query(self):
        archive_query =  {'$set': {'is_archived': True}}
        return archive_query

    def remove(self, *args, **kw):
        # If there is an arg then it means we want to delete the specific id. But code
        # will for for deleting all that match anyway.
        if args:
            kw['id'] = args[0]
            
        for doc in self.find(**self.doc_class.get_query(**kw)):
            doc.archive()

    def remove_by_user(self, user, *args, **kw):
        kw.update(self.get_permission_query(user))
        self.remove(*args, **kw)


class ArchivingAuthDocument(AuthDocument):
    """ Support archiving instead delete on delete_by_user """
    manager = ArchivingAuthManager

    is_archived = fields.BooleanField(default=False)

    def archive_value(self, value):
        """
        :param value: Current value from the database before the archiving
        :return: if a translation is possible based on the type of the value, translate into archived form
        """
        if type(value) in (unicode, str):
            return 'old.%s.%s' % (str(self.id), value)
        LOGGER.warning("Archiving unique value %s on object %s. No archiving strategy." % (value, self))
        return value

    def archive(self):
        """
        Archive the current document.
        """
        archive_dict = {}
        for field in self.fields.values():
            if field.unique and field.db_field != '_id':
                archive_dict[field.db_field] = self.archive_value(self.data[field.db_field])
        archive_dict['is_archived'] = True
        self.objects.coll.update(self.get_query(**{'_id': self.id}),
                                 {'$set': archive_dict})
        self.data.update(archive_dict)

    def reload(self):
        #update data
        new_data = self.objects.find_one(
            id=self.id, include_safe_deletes=True).data
        self.data = new_data
        self.clear_ref_cache()
