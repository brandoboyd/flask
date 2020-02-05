'''
Defines a set of classes around the concept of an account. Accounts vary. But they are related.

'''
from datetime import datetime
import requests
from collections import defaultdict
from functools import partial
from solariat_bottle.configurable_apps import CONFIGURABLE_APPS, APP_GSA, \
    APP_GSE
from solariat_nlp.bandit.models import DEFAULT_CONFIGURATION

from ..settings import get_var, LOGGER, AppException
from solariat.utils.timeslot import guess_timeslot_level, UNIX_EPOCH, now, utc, parse_date, \
    Timeslot
from .auth import ArchivingAuthDocument, ArchivingAuthManager, AuthDocument

from solariat.db.abstract import fields, SonDocument
from solariat_bottle.db.dataset import DatasetsManager
from solariat_bottle.db.dynamic_profiles import (CustomerProfileDynamicManager,
                                                 AgentProfileDynamicManager)
from solariat_bottle.db.dynamic_event import EventTypeManagerFactory
from .api_auth import ApplicationToken
from .user import User
from .group import Group
from .work_time import WorkTimeMixin


THRESHOLD_WARNING = 1
THRESHOLD_SURPASSED_WARNING = 10
VOLUME_NOTIFICATION_THRESHOLD = {"Warning":           75,
                                 "Surpassed":         95}
ACCOUNT_POSTS_LIMIT_DAILY = 10000

# define default recovery days for channels like Twitter and Facebook
DEFAULT_RECOVERY_DAYS = 9


def integrate_stats(keys, data, default=0):
    """Sums up the account stats by channels"""
    result = defaultdict(dict)
    for key in keys:
        result.setdefault(key, default)
    for _, stats in data.iteritems():
        for key in keys:
            result[key] += stats.get(key, 0)
    return result


def account_stats(acct, user, start_date=None, end_date=None,
                  aggregate=('number_of_posts',), channels_filter=None):
    """Returns account stats calculated over live (unarchived) channels"""
    if channels_filter is None:
        channels_filter = {"status__ne": "Archived"}
    stats = acct.aggregate_stats(user, start_date, end_date, stats=aggregate,
                                 channels_filter=channels_filter)
    return integrate_stats(aggregate, stats)

# `all_account_stats` includes archived channels stats
all_account_stats = partial(account_stats,
                            channels_filter={"include_safe_deletes": True})


def _get_user(user):
    if isinstance(user, User):
        return user
    elif isinstance(user, basestring):
        try:
            user = User.objects.get(email=user)
        except User.DoesNotExist:
            return False
        else:
            return user
    else:
        raise ValueError(u"Unsupported parameter type %s" % (user.__class__.__name__))


class ReservedNameException(AppException):
    """ Raise if any reserved names are used for account name. """
    pass


class AccessTokenExpired(AppException):
    pass


class ChannelConfigurationError(AppException):
    """ Raise when the channels are screwed up somehow """
    pass


class Package(ArchivingAuthDocument):
    '''
        Document holding the various pricing volume options for a billable account.
    '''
    name = fields.StringField()
    cost = fields.NumField(default=0)  # Cost / month
    volume = fields.NumField(default=-1)  # Number of posts / month
    storage_time = fields.NumField(default=-1)  # Number of months to store data


def create_application_token(creator):
    return ApplicationToken.objects.create(
        creator=creator,
        status=ApplicationToken.STATUS_VALID,
        type=ApplicationToken.TYPE_ACCOUNT)


class AccountManager(ArchivingAuthManager):

    @staticmethod
    def get_permission_query(user):
        #return {'id__in': user.accounts}
        return {}

    def __ensure_start_end_date(self, kwargs):
        """
        Make sure both start and end date are either None or a valid datetime and not strings
        :param kwargs: The arguments to create the account
        :return: same arguments, only with proper start and end date
        """
        kwargs['start_date'] = kwargs.get('start_date', now())
        if type(kwargs['start_date']) in (str, unicode):
            kwargs['start_date'] = parse_date(kwargs['start_date'])
        end_date = kwargs.get('end_date', False)
        if not end_date:
            # Safe-guard for things like empty string or None
            kwargs.pop('end_date', None)
            return
        if type(kwargs['end_date']) in (str, unicode):
            kwargs['end_date'] = parse_date(kwargs['end_date'])

    def create(self, **kwargs):
        """Checks account name limitations.
        """
        name = kwargs.get('name', None)
        if name is None or not name.strip():
            raise AppException('Account names should not be empty')

        self.__ensure_start_end_date(kwargs)

        package = kwargs.pop('package', "Internal")
        try:
            package = Package.objects.get(name=package)
        except Package.DoesNotExist:
            from solariat_bottle.utils.pricing_packages import PACKAGE_TYPES, ensure_pricing_packages
            #  This is a check for whether an unsupported account type was given,
            #   or if no pricing packages exist in the DB, in which case populate it
            LOGGER.debug(PACKAGE_TYPES)
            LOGGER.debug(package)
            if package in PACKAGE_TYPES:
                ensure_pricing_packages()
                package = Package.objects.get(name=package)
            else:
                raise AppException("Unsupported pricing package: {}".format(package))
        finally:
            kwargs['package'] = package

        account = super(AccountManager, self).create(**kwargs)
        account_metadata = AccountMetadata(
            account=account,
            predictors_configuration=DEFAULT_CONFIGURATION)
        account_metadata.save()
        return account

    def create_by_user(self, user, *args, **kwargs):
        if user.is_staff and not user.is_superuser:
            kwargs['customer_success_manager'] = user

        # If 'end_date' was passed in as empty string or None just remove it from args
        self.__ensure_start_end_date(kwargs)
        if '_gse_api_key' not in kwargs:
            kwargs['_gse_api_key'] = create_application_token(user)
        account = super(AccountManager, self).create_by_user(user, *args, **kwargs)
        account.add_perm(user)
        return account

    def get_by_user(self, user, *args, **kw):
        if len(args) > 0:
            kw['id'] = args[0]
        account = self.get(**kw)
        if not account.has_perm(user) and not user.is_superuser:
            raise AppException("User does not have access to this account")
        return account

    def find_by_user(self, user, **kw):
        if not user.is_superuser:
            kw['id__in'] = user.accounts
        return self.find(**kw)

    def find(self, **kw):
        package = kw.get('package', None)
        if package:
            package = Package.objects.get(name=package)
            kw['package'] = package.id
        return super(AccountManager, self).find(**kw)

    def remove_by_user(self, user, *args, **kw):

        account = self.get_by_user(user, *args, **kw)

        account.pre_removal()

        if user.is_superuser or account.has_perm(user, perm='w'):
            self.remove(*args, **kw)
        else:
            raise AppException("User does not have permissions to delete this account")

    def get_or_create(self, **kw):
        if 'is_archived' not in kw:
            kw['is_archived'] = False
        return super(AccountManager, self).get_or_create(**kw)


class Notification(SonDocument):
    INTERVAL = 24*60*60  # 24 hours
    SENDING = 1
    IDLE = 0

    status = fields.NumField(db_field='ss', default=IDLE, choices=[IDLE, SENDING])
    posts_limit = fields.NumField(db_field='pl', default=ACCOUNT_POSTS_LIMIT_DAILY)

    # posts_count = fields.NumField(db_field='pc', default=0)
    alert_emails = fields.ListField(fields.StringField(), db_field='ae')
    last_sent_at = fields.DateTimeField(db_field='ls')

    def posts_count(self, user, account):
        day_start, day_end = Timeslot(level='day').interval
        posts = account_stats(
            account,
            user,
            start_date=day_start,
            end_date=day_end
        )
        return posts.get('number_of_posts')

    def should_send_notification(self, user, account):
        if self.status == self.SENDING:
            return False
        date_now = now()

        can_send = not self.last_sent_at or (date_now - utc(self.last_sent_at)).total_seconds() > self.INTERVAL
        if can_send:
            limit_reached = self.posts_count(user, account) >= self.posts_limit
            return limit_reached
        return False


class DailyPostsVolumeNotification(Notification):
    def send_notification(self, user, account):
        from solariat_bottle.utils.mailer import send_account_posts_daily_limit_warning

        recipient_emails = list(set(self.alert_emails) | set(get_var('DAILY_VOLUME_ALERT_RECIPIENTS', [])))
        users_email_to_name = {user.email: user.first_name for user in User.objects(email__in=recipient_emails)}
        recipients = [(email, users_email_to_name.get(email)) for email in recipient_emails]

        return send_account_posts_daily_limit_warning(recipients, account.name, self.posts_limit)

    def change_status_atomic(self, account, status):
        notification_status = "%s.%s" % (account.F._daily_post_volume_notification, self.F.status)
        result = account.objects.coll.update(
            {"_id": account.id, notification_status: {"$eq": Notification.IDLE}},
            {"$set": {notification_status: status}},
            upsert=False,
            multi=False)
        return result['n'] == 1

    def save(self, account):
        account.update(_daily_post_volume_notification=self)

    def _check_daily_volume(self, user, account):
        if self.should_send_notification(user, account):
            if self.change_status_atomic(account, Notification.SENDING):
                self.send_notification(user, account)
                self.last_sent_at = now()
                self.status = Notification.IDLE
                self.save(account)
                return True
        return False


class Account(ArchivingAuthDocument, WorkTimeMixin):
    """ Our customer account details. This is a billable entity.
    Not trying to replicate a customer database.
    """
    ACCOUNT_TYPES = ("Native", "Salesforce", "HootSuite",
                     "Skunkworks", "Angel", "GSE")
    ACCOUNT_TYPE_SYSTEM = '__system'
    DEFAULT_APP_KEYS = [APP_GSE]
    DEFAULT_APPS = {app_key: CONFIGURABLE_APPS.get(app_key) for app_key in DEFAULT_APP_KEYS}

    # Name of the account (e.g. Wells Fargo - Social Team)
    name = fields.StringField(unique=True,
                              required=True,
                              db_field='ne')
    account_type = fields.StringField(db_field='ty', default='Native',
                                      choices=ACCOUNT_TYPES)
    package = fields.ReferenceField(Package, db_field="pn")
    # Refresh oAuth token if it was configured so
    oauth_token = fields.StringField(db_field='oauth')
    sf_instance_url = fields.StringField(db_field='sfurl')  # The instance url for our application.
    # GSE API key
    _gse_api_key = fields.ReferenceField(ApplicationToken, db_field='gskey')

    customer_success_manager = fields.ReferenceField(User, db_field="csm", default=None)
    # Start and End Dates for the account
    start_date = fields.DateTimeField(db_field='se', default=UNIX_EPOCH)
    end_date = fields.DateTimeField(db_field='ee', default=UNIX_EPOCH)

    # This is the authorization token which can be used
    # to actually access data but has short lifespan
    _access_token = None

    _posts_limit = None  # The number of posts this account can have before triggering the threshold surpassed TODO: This should be set and reset at a wider scope than here

    # Channels by Platform. Used to select the outbound
    # channel for post responses. These will provide defaults
    # For users
    outbound_channels = fields.DictField('os')

    # Staff notes
    notes = fields.StringField(db_field="ns", default=None)

    # Created / Updated at
    created_at = fields.DateTimeField(default=now)
    updated_at = fields.DateTimeField()

    threshold_warning = fields.NumField('tw', default=0)
    _daily_post_volume_notification = fields.EmbeddedDocumentField(DailyPostsVolumeNotification, db_field='dpvn')
    is_locked = fields.BooleanField(default=False, db_field="isd")
    _recovery_days = fields.NumField(db_field='rcvry')

    available_apps = fields.DictField(db_field='aa', default=DEFAULT_APPS)
    selected_app = fields.StringField(db_field='sa', default=DEFAULT_APP_KEYS[0])

    event_processing_lock = fields.BooleanField(default=False, db_field='ev_plock')
    event_processing_needs_restart = fields.BooleanField(default=False, db_field='ev_resync')
    resync_progress = fields.NumField(default=0, db_field='rsync_progress')

    manager = AccountManager

    NO_ACCOUNT = 'NO_ACCOUNT'
    reserved_names = [NO_ACCOUNT]  # Reserved name for users w/o any accounts

    ReservedNameException = ReservedNameException
    AccessTokenExpired = AccessTokenExpired

    datasets = DatasetsManager()
    customer_profile = CustomerProfileDynamicManager()
    agent_profile = AgentProfileDynamicManager()
    event_types = EventTypeManagerFactory()

    # Just for demo most likely
    # packed_routing_clf = fields.BinaryField()  # WARNING: 2MB limit!

    def get_customer_profile_class(self):
        customer_profile_schema = self.customer_profile._get()
        return customer_profile_schema.get_data_class()

    def get_agent_profile_class(self):
        agent_profile_schema = self.agent_profile._get()
        return agent_profile_schema.get_data_class()

    def save(self, *args, **kwargs):
        if self.name in Account.reserved_names:
            raise ReservedNameException(
                "You cannot name your account %s, that name is reserved" % self.name)
        self.updated_at = now()
        return super(Account, self).save(*args, **kwargs)

    def pre_removal(self):
        # Need to clean up users, groups from this account
        LOGGER.debug("Removing account: {}".format(self))
        for u in self.get_all_users():
            user_accounts = [
                a for a in u.available_accounts if a.id != self.id]
            if user_accounts or u.is_staff:
                u.accounts.remove(str(self.id))
                # reset account only if user's current account is set to the account being removed
                if u.account.id == self.id:
                    # this may leave staff users without account
                    u.account = user_accounts and user_accounts[0] or None
                u.save()
            else:
                u.delete()
        assert self.get_users().count() == 0

        for group in self.get_groups():
            group.delete()

    @classmethod
    def to_mongo(cls, data, fill_defaults=True):
        if 'name' in data and data['name'] in cls.reserved_names:
            raise cls.ReservedNameException(
                "You cannot name your account %s, that name is reserved" % data['name'])
        return super(Account, cls).to_mongo(data, fill_defaults)

    def _get_access_token(self):
        # if no oauth token is specified we cannot get access token
        if not self.oauth_token:
            return None
        if self._access_token is None:
            self.refresh_access_token()
        return self._access_token

    def _set_access_token(self, access_token):
        self._access_token = access_token

    access_token = property(_get_access_token, _set_access_token)

    @property
    def recovery_days(self):
        if self._recovery_days is None:
            return DEFAULT_RECOVERY_DAYS
        return self._recovery_days

    @property
    def gse_api_key(self):
        if not self._gse_api_key:
            # create api keys for already existing accounts
            self._gse_api_key = create_application_token(None)
            self.save()

        try:
            return self._gse_api_key.app_key
        except (ApplicationToken.DoesNotExist, AttributeError):
            return None

    def refresh_access_token(self):
        """
        Refresh the access token, in case we don't have one or we have one
        that has expired.
        """
        if not self.oauth_token:
            raise ValueError(
                "This account does not have a oAuth refresh token. Please authorize it first.")
        data = {
            'grant_type': 'refresh_token',
            'client_id': get_var('SFDC_CLIENT_ID'),
            'client_secret': get_var('SFDC_CONSUMER_SECRET'),
            'refresh_token': self.oauth_token
        }
        access_request = requests.post(
            'https://login.salesforce.com/services/oauth2/token', data=data)
        received_data = access_request.json()
        if not 'access_token' in received_data:
            error_msg = "The Salesforce login token for this account is invalid or has expired."
            if 'error_description' in received_data:
                error_msg += "Error: %s" % received_data['error_description']
            raise ValueError(error_msg)
        self.sf_instance_url = received_data['instance_url']
        self._access_token = received_data['access_token']

    @property
    def admins(self):
        from solariat_bottle.db.roles import ADMIN
        # faster than user.is_admin since it does not hit user.account
        is_admin = lambda u: (ADMIN in u.user_roles or u.is_staff)

        return [user for user in User.objects(account=self) if is_admin(user)]

    def set_oauth_token(self, token):
        self.oauth_token = token
        self.save()

    def invalidate_oauth(self):
        self.oauth_token = ""
        self.save()

    def has_oauth_token(self):
        return self.oauth_token is not None and len(self.oauth_token)

    def set_outbound_channel(self, channel):
        assert channel.account == self
        self.outbound_channels[channel.platform] = channel.id
        self.save()

    def get_outbound_channel(self, platform):
        from .channel.base import Channel

        if platform in self.outbound_channels:
            channel_id = self.outbound_channels.get(platform, None)
            if channel_id:
                try:
                    ch = Channel.objects.get(id=channel_id)
                    assert ch and ch.is_dispatchable, "Channel is not dispatchable: %s" % ch
                    assert ch.platform == platform, "Channel platform=%s stored as %s" % (
                        ch.platform, platform)
                    return ch
                except (Channel.DoesNotExist, AssertionError), e:
                    LOGGER.warning("Account:%s get_outbound_channel: %s" % (self, str(e)))
                    self.outbound_channels[platform] = None
                    self.save()
        return None

    def get_outbounds_for_handle(self, twitter_handle):
        """
        Return all the EnterpriseTwitterChannel from the current account
        which have the given twitter_handle configured.
        """
        from .channel.twitter import EnterpriseTwitterChannel
        return EnterpriseTwitterChannel.objects(twitter_handle=twitter_handle,
                                                status='Active',
                                                account=self)[:]

    def add_perm(self, user):
        needs_save = False
        if not user.account:
            user.account = self
            needs_save = True
        if self.id not in user.accounts:
            user.accounts.append(self.id)
            needs_save = True
        if needs_save:
            user.save()

    def del_perm(self, user):
        existing_accounts = user.accounts
        if self.id in user.accounts:
            existing_accounts.remove(self.id)
            user.accounts = existing_accounts
            if user.account == self:
                user.account = None
            user.save()

    def has_perm(self, user, perm=None):
        return user.account == self or self.id in user.accounts or user.is_superuser

    def add_user(self, user, perms='r'):
        """Wrapper for add_perms that accepts `user` parameter
        either as email string or object."""
        user = _get_user(user)
        if user:
            self.add_perm(user)
            return True
        else:
            return False

    def del_user(self, user, perms='rw'):
        user = _get_user(user)
        if user:
            self.del_perm(user)
            return True
        else:
            return False

    def get_current_users(self, **query):
        """
        Return all users whose current account is this account.
        """
        query.update({"account": self})
        return User.objects(**query)

    def get_current_channels(self, **kwargs):
        from .channel.base import Channel

        kwargs.update({"account": self})
        return Channel.objects(**kwargs)

    def aggregate_stats(self, user, start_date=None, end_date=None, stats=(
            'number_of_posts',), channels_filter=None):
        from .channel_stats import aggregate_stats

        if start_date and end_date:
            level = guess_timeslot_level(start_date, end_date)
        else:
            level = 'month'
        channels = self.get_current_channels(**(channels_filter or {}))
        channel_ids = [c.id for c in channels if not c.is_smart_tag]
        return aggregate_stats(user, channel_ids, start_date, end_date, level,
                               aggregate=stats)

    def get_users(self, **query):
        return self.get_current_users(**query)

    def get_all_users(self):
        """
        Return list of users that have access to account.
        """
        return User.objects.find(accounts__in=[self.id])[:]

    def get_contact_channel(self, platform="Twitter"):
        from .channel.base import ContactChannel, PLATFORM_MAP

        channel = ContactChannel.objects.get_or_create(
            account=self,
            title='Contacts',
            platform_id=PLATFORM_MAP[platform]['index'])
        return channel

    def get_groups(self):
        return Group.objects.find(account=self)[:]

    def get_agents(self):
        return self.get_current_users(agent_id__ne=0, is_superuser=False)

    @property
    def status(self):
        time_now = now()
        if utc(self.start_date) <= time_now <= utc(self.end_date) \
                or utc(self.end_date) == UNIX_EPOCH:
            return 'Active'
        return 'Inactive'

    @property
    def is_active(self):
        return self.status == "Active"

    @property
    def volume_warning_limit(self):
        if self.package is not None and self.package.volume != 0:
            return int((VOLUME_NOTIFICATION_THRESHOLD["Warning"]  * self.package.volume) / 100)
        else:
            return -1

    @property
    def volume_surpassed_limit(self):
        if self.package is not None and self.package.volume != 0:
            return int((VOLUME_NOTIFICATION_THRESHOLD["Surpassed"]  * self.package.volume) / 100)
        else:
            return -1

    def clear_threshold_warnings(self):
        ''' Reset the threshold warning '''
        self.threshold_warning = 0
        self.save()

    def set_threshold_warning(self, warning):
        if warning in [THRESHOLD_WARNING, THRESHOLD_SURPASSED_WARNING]:
            if not self.threshold_warning / warning:
                self.threshold_warning += warning
                self.save()

    @property
    def is_threshold_warning_sent(self):
        return bool(self.threshold_warning / THRESHOLD_WARNING)

    @property
    def is_threshold_surpassed_sent(self):
        return bool(self.threshold_warning / THRESHOLD_SURPASSED_WARNING)

    @property
    def daily_post_volume_notification(self):
        if self._daily_post_volume_notification is None:
            self._daily_post_volume_notification = DailyPostsVolumeNotification()
            self._daily_post_volume_notification.save(account=self)
        return self._daily_post_volume_notification

    def check_daily_volume(self, user):
        notification = self.daily_post_volume_notification
        notification_sent = notification._check_daily_volume(user, account=self)
        return notification_sent

    def __unicode__(self):
        return self.name

    def to_dict(self, fields2show=()):
        d = super(Account, self).to_dict(fields2show)
        if self.customer_success_manager:
            d['customer_success_manager'] = self.customer_success_manager.email
        d.pop('packed_routing_clf', None)     # No one cares about this in UI
        return d

    def lock(self):
        self.is_locked = True
        self.save()

    def unlock(self):
        self.is_locked = False
        self.save()

    @property
    def account_metadata(self):
        account_metadata = AccountMetadata.objects.get(account=self)
        return account_metadata

    def get_journey_types(self):
        from solariat_bottle.db.journeys.journey_type import JourneyType
        return JourneyType.objects(account_id=self.id)[:]


class AccountType(ArchivingAuthDocument):
    '''
    Meta Data for different Account Types that we use for app
    integration
    '''
    EF = lambda field: fields.EncryptedField(field, allow_db_plain_text=True)

    name = fields.StringField(db_field='ne', required=True, unique=True)
    twitter_consumer_key = EF(fields.StringField(db_field='tcy'))
    twitter_consumer_secret = EF(fields.StringField(db_field='tct'))
    twitter_access_token_key = EF(fields.StringField(db_field='tay'))
    twitter_access_token_secret = EF(fields.StringField(db_field='tat'))
    twitter_callback_url = EF(fields.StringField(db_field='tcl'))


class AccountEvent(AuthDocument):

    account = fields.ReferenceField(Account, db_field="at", required=True)
    created_at = fields.DateTimeField(db_field='ct', required=True)
    user = fields.ReferenceField(User, db_field='ur', required=True)
    change = fields.StringField(db_field='ce', required=True)
    event_data = fields.DictField(db_field='da', required=True)

    KEY_OLD_DATA = "old_data"
    KEY_NEW_DATA = "new_data"

    indexes = [('account'), ]

    @classmethod
    def __ensure_event_data(cls, event_data):
        if event_data is None:
            event_data = {}
        if event_data:
            for key in (cls.KEY_NEW_DATA, cls.KEY_OLD_DATA):
                if key not in event_data:
                    event_data[key] = {}
                if not isinstance(event_data[key], dict):
                    event_data[key] = {"state": event_data[key]}
        return event_data

    def get_old_data(self):
        return self.event_data.get(self.KEY_OLD_DATA, {})

    def get_new_data(self):
        return self.event_data.get(self.KEY_NEW_DATA, {})

    @classmethod
    def create_by_user(cls, user, change, old_data=None, new_data=None, event_data=None):
        # import ipdb; ipdb.set_trace()
        event_data = event_data or {}
        event_data.update({cls.KEY_OLD_DATA: old_data,
                           cls.KEY_NEW_DATA: new_data})
        account_event = AccountEvent(
            account=user.account,
            user=user,
            change=change,
            event_data=cls.__ensure_event_data(event_data),
            created_at=datetime.now()
        )
        account_event.save()

        if change in ['activate_channel', 'suspend_channel', 'delete_channel', 'Languages modifications',
                      'Channel edit', 'Channel create']:
            # update "Last Updated" column in "Accounts" page
            user.current_account.save()

    def to_dict(self):
        res = super(AccountEvent, self).to_dict()
        res['old_changed_fields'] = {}
        res['new_changed_fields'] = {}
        res['user_email'] = User.objects.get(id=res['user']).email
        message = ''
        new_data = self.get_new_data()
        old_data = self.get_old_data()
        if new_data and old_data:
            for key in set(old_data.keys() + new_data.keys()):
                if old_data.get(key) != new_data.get(key):
                    message += '"%s" field has changed; old value: "%s"; new value: "%s"; \n' % (
                        key, old_data.get(key), new_data.get(key))
                    res['old_changed_fields'][key] = old_data.get(key)
                    res['new_changed_fields'][key] = new_data.get(key)
        res['message'] = message
        del res['event_data']
        return res


class AccountMetadata(AuthDocument):

    account = fields.ReferenceField(Account, db_field="at", required=True)
    predictors_configuration = fields.DictField(db_field='pn', required=True)

