from solariat.db.abstract import fields
from solariat_bottle.db.auth import ArchivingAuthDocument, ArchivingAuthManager
from solariat_bottle.db.user import User
from solariat_bottle.db.account import Account
from solariat.utils.timeslot import now, utc, UNIX_EPOCH
from solariat_bottle.settings import LOGGER

class TrialManager(ArchivingAuthManager):
    def create_by_user(self, user, *args, **kwargs):

        LOGGER.debug("Create Trial: {}".format(kwargs))
        item = super(TrialManager, self).create_by_user(user, **kwargs)
        item.add_perm(user)
        return item



class Trial(ArchivingAuthDocument):
    created_at = fields.DateTimeField()
    updated_at = fields.DateTimeField()

    creator = fields.ReferenceField(User)

    account = fields.ReferenceField(Account)  # trial account
    admin_user = fields.ReferenceField(User)  # trial admin

    start_date = fields.DateTimeField(default=UNIX_EPOCH)
    end_date = fields.DateTimeField(default=UNIX_EPOCH)

    manager = TrialManager

    @property
    def status(self):
        time_now = now()
        if utc(self.start_date) <= time_now <= utc(self.end_date) \
                or utc(self.end_date) == UNIX_EPOCH:
            return 'Active'
        return 'Inactive'
