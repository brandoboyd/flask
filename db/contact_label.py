from datetime import datetime
from solariat_bottle.db.group    import (default_admin_group, default_analyst_group, default_reviewer_group)
from solariat_bottle.db.roles          import ADMIN, STAFF, ANALYST

from .auth import AuthManager,AuthDocument
from solariat.db import fields


class ContactLabelManager(AuthManager):

    def create_by_user(self, user, **kw):
        if user.current_account:
            # Force class based access
            account = user.current_account
            kw['acl'] = [default_admin_group(account), default_analyst_group(account), default_reviewer_group(account)]
        return AuthManager.create_by_user(self, user, **kw)


class ContactLabel(AuthDocument):

    admin_roles = [ADMIN, STAFF, ANALYST]

    manager = ContactLabelManager

    title     =     fields.StringField(db_field='te')
    created   =     fields.DateTimeField(db_field='cd',
                    default=datetime.utcnow())
    platform  =     fields.StringField(db_field='pm')
    status    =     fields.StringField(db_field='st')
    users     =     fields.ListField(fields.StringField())

    allow_inheritance = True

    @classmethod
    def class_based_access(cls, account):
        """ Based on the AUTH class we are creating, we might offer some default access
        to certain groups from the account. By default, permissions should only be given to
        admin type users. This can be overwritten in specific classes as needed. E.G. messages -> agents ?
        """
        if account is None:
            return []
        return [default_admin_group(account), default_analyst_group(account), default_reviewer_group(account)]

    @property
    def type_id(self):
        return 0


class ExplcitTwitterContactLabel(ContactLabel):

    manager = ContactLabelManager

    @property
    def type_id(self):
        return 1

