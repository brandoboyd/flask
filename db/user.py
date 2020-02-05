"""
Classes and utils for Permission System

"""
import copy
import datetime
import hashlib
import os
import re

from flask import session
from pymongo.errors import DuplicateKeyError
from solariat_bottle.db.user_profiles.user_profile_field import \
    UserProfileIdField

from solariat_bottle.settings import get_var, LOGGER, AppException
from solariat_bottle.configurable_apps import APP_GSE
from solariat.db import fields
from solariat.db.abstract import Manager, Document
from solariat_bottle.db.auth import ArchivingAuthManager, ArchivingAuthDocument, AuthError
from solariat_bottle.db.roles import USER_ROLES, compute_main_role, AGENT, ADMIN, ANALYST, STAFF, REVIEWER, SYSTEM
from solariat_bottle.db.sequences import NumberSequences

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")


import threading

_thread_local = threading.local()

def set_user(user):
    global _thread_local
    _thread_local.user = user

def get_user():
    global _thread_local
    return _thread_local.user

def get_hexdigest(salt, raw_password):
    "Return SHA1 hexdigest"
    return hashlib.sha1(salt + raw_password).hexdigest()

def make_password(raw_password):
    "Return SHA hexdigest"
    from random import random
    salt = get_hexdigest(str(random()), str(random()))[:5]
    hash = get_hexdigest(salt, raw_password)
    return 'sha1$%s$%s' % (salt, hash)

def get_random_digest():
    "True random id"
    sha = hashlib.sha1()
    sha.update(os.urandom(128))
    return sha.hexdigest()


class DuplicateSignatureError(AppException):
    pass


class UserManager(ArchivingAuthManager):
    "Implement user creation and get logged in"
    def create(self, email, password=None, is_superuser=False,
               group=None, account=None, external_id=None, first_name=None,
               last_name=None, user_roles=None, groups=None, signature=None):
        """
        Create (and save) a new user with the given password and
        email address. Generate a random password if not provided

        If external_id is not specified it is set to:
        "na:email"
        """
        from solariat_bottle.db.group import Group
        # Map to lower case
        email = email.lower()

        if not EMAIL_REGEX.match(email):
            raise AppException('Email is not valid')
        raw_password = password

        if raw_password is None:
            raw_password = os.urandom(16).encode('base64')[:-3]
        password = make_password(raw_password)

        try:
            email_name, domain_part = email.strip().split('@', 1)
        except ValueError:
            pass
        else:
            email = '@'.join([email_name, domain_part.lower()])

        if account:
            from .account import Account
            if isinstance(account, basestring):
                account = Account.objects.get(name=account)

        if external_id is None:
            external_id = "na:"+email
        user_roles = user_roles or []
        groups = groups or []
        # groups to which a user belongs explicitly
        # or implicitly via roles
        extended_groups = copy.deepcopy(groups)
        if user_roles:
            extra_groups = Group.objects.find(roles__in=user_roles)[:]
            extended_groups.extend([g.id for g in extra_groups if g.id not in groups])

        try:
            # if signature is provided and is not unique for account do not create user
            if account and signature:
                if User.objects.find(_signature=signature, account=account.id).count() > 0:
                    raise AppException('This signature is already used with this account')
            accounts = [account.id] if account else []
            new_user = ArchivingAuthManager.create(self,
                                                   email=email,
                                                   password=password,
                                                   is_superuser=is_superuser,
                                                   account=account,
                                                   accounts=accounts,
                                                   external_id=external_id,
                                                   user_roles=user_roles,
                                                   groups=extended_groups,
                                                   first_name=first_name,
                                                   last_name=last_name)
            if signature:
                new_user.signature = signature
                new_user.save()
            for group in Group.objects.find(id__in=groups):
                if new_user not in group.members:
                    group.members.append(new_user)
                    group.save()
            new_user.raw_password = raw_password        # Just store it so we can send it via creation email
            return new_user
        except DuplicateKeyError, ex:
            raise AppException(str(ex))

    def get_current(self):
        "Return current logged user"
        try:
            user_id = session.get('user')
        except (AttributeError, AppException):
            user_id = None
        if user_id:
            try:
                return self.get(id = session.get('user'))
            except User.DoesNotExist:
                pass
        try:
            if 'user' in session:
                del session['user']
        except AttributeError:
            pass
        raise AuthError(
            "No user logged in or provided")

    def find_agent(self, account, **kw):
        from ..db.user_profiles.user_profile import UserProfile
        from ..utils.post import normalize_screen_name

        query = {'account': account}

        agent_id = kw.pop('agent_id', None)
        if agent_id:
            query['agent_lookup'] = User.make_agent_lookup_field('agent_id', agent_id)
        else:
            up = kw.pop('user_profile', None)
            if up is not None:
                if isinstance(up, UserProfile):
                    kw['user_profile'] = normalize_screen_name(up.screen_name)
                elif isinstance(up, basestring):
                    kw['user_profile'] = normalize_screen_name(up)

            lookup = map(lambda (k,v): User.make_agent_lookup_field(k, v),
                kw.items())
            query['agent_lookup'] = {'$in': lookup}

        agents = list(User.objects.find(**query).limit(2))
        if len(agents) == 1:
            return agents[0]
        else:
            for agent in agents:
                if agent.signature.lower() == kw.get('signature', '').lower():
                    return agent
        return None

    def find_agent_by_post(self, account, post):
        from ..utils.post import extract_signature

        post_content = post.plaintext_content
        candidates_with_user_profile = []
        candidates_with_signature    = []
        for user in account.get_users():
            if user.signature and (
                    extract_signature(post_content.lower()) == user.signature.lower().strip()):
                candidates_with_signature.append(user)
            if post.user_profile and user.user_profile and \
                    (post.user_profile == user.user_profile
                        or (hasattr(user.user_profile,'user_name') and post.user_profile.user_name == user.user_profile.user_name)):
                candidates_with_user_profile.append(user)

        candidates = candidates_with_signature if candidates_with_signature else candidates_with_user_profile

        msg = u'Found more than 1 candidate for agent. account=%s post=%s agents=%s.'
        if len(candidates_with_signature) > 1:
            msg += u' Users have equal signatures.'
            LOGGER.error(msg, account, post.id, ", ".join(c.display for c in candidates_with_signature))
        if len(candidates_with_user_profile) > 1:
            msg += u' Users have equal user_profiles.'
            LOGGER.info(msg, account, post.id, ", ".join(c.display for c in candidates_with_user_profile))

        if not candidates:
            # Try to create agent from user_profile
            user_profile = post.user_profile
            if user_profile:
                return User.objects.create_agent(account, user_profile, post_content)
            else:
                LOGGER.error(u'No user profile for post %s. Anonymous agent returned.', post)
                return User.objects.anonymous_agent()

        if len(candidates) == 1:
            return candidates[0]

        return sorted(candidates, key=lambda x:-len(x.signature or ''))[0]

    def create_agent(self, account, user_profile, post_content):
        from ..utils.post import extract_signature
        signature = extract_signature(post_content)
        if signature is None:
            if hasattr(user_profile, 'user_name'):
                signature = user_profile.user_name
            else:
                return

        try:
            new_user = User.objects.get(account=account, _signature=signature)
        except User.DoesNotExist:
            new_user = User(
                account=account,
                password=make_password(os.urandom(10).encode('base64')[:-3]),
                user_roles=[SYSTEM])
            new_user.user_profile = user_profile
            try:
                new_user.signature = signature
            except DuplicateSignatureError:
                new_user = User.objects.get(account=account, _signature=signature)
            else:
                domain = get_var('HOST', 'socialoptimizr.com')
                new_user.email = u'agent+%d@%s' % (new_user.agent_id, domain)
                try:
                    new_user.save()
                except Exception, e: # duplication error
                    LOGGER.error(u"Agent creation error: %s. %s", new_user, e)
                    return None
                account.add_user(new_user)
        return new_user

    def anonymous_agent(self):
        from ..db.channel_stats_base import ANONYMOUS_AGENT_ID

        domain = get_var('HOST', 'socialoptimizr.com')
        email = u'agent+anonymous@%s' % domain
        try:
            return User.objects.get(email=email, agent_id=ANONYMOUS_AGENT_ID)
        except User.DoesNotExist:
            anon_user = User(
                email=email,
                agent_id=ANONYMOUS_AGENT_ID,
                password = make_password(os.urandom(10).encode('base64')[:-3]))
            anon_user.save()
            return anon_user


class User(ArchivingAuthDocument):
    """ Represent a real person in system. An entity with a login """
    manager = UserManager
    # we soft delete users by marking this field as True
    # the field includes _user_ not to interfere with similar field from ArchivingAuthManager
    # is_user_archived = fields.BooleanField(default=False, db_field='iua')

    first_name = fields.StringField(db_field='fn')
    last_name = fields.StringField(db_field='ln')
    email = fields.StringField(unique=True, db_field='el')
    # User id for external service (Salesforce, Hootsuite)
    external_id = fields.StringField(unique=True, db_field='eid')
    password = fields.StringField(db_field='pd')
    is_superuser = fields.BooleanField(default=False, db_field='is')
    last_login = fields.DateTimeField(default=datetime.datetime.now, db_field='ll')
    # The roles that are assigned to this account
    user_roles = fields.ListField(fields.NumField(), db_field='ur')
    # The groups which are assigned to this user
    groups = fields.ListField(fields.ObjectIdField(), db_field='gps')
    # The user may be assigned to an account
    account = fields.ReferenceField('Account', db_field='at')
    # The user may have access to more accounts
    accounts = fields.ListField(fields.ObjectIdField(), db_field='ats')
    # Channels by Platform. Used to select the outbound
    # channel for post responses
    outbound_channels = fields.DictField('os')

    agent_id = fields.NumField('aid', default=0)
    _user_profile = UserProfileIdField(db_field='up')
    _signature = fields.StringField(db_field='sgn')
    agent_lookup = fields.ListField(fields.StringField(), db_field='al')

    selected_strategy = fields.StringField(db_field='ssty')

    # agent_profile_id = fields.ObjectIdField(db_field='ad')

    indexes = [('account', ), ('accounts',), ('first_name',), ('last_name',), ('email',),
               ('first_name', 'last_name')]

    def save(self, **kw):
        if self.email and self.external_id is None:
            self.external_id = "na:" + self.email
        super(User, self).save(**kw)

    def archive(self):
        from ..events import doc_before_delete
        doc_before_delete.send(self)
        super(User, self).archive()

    @staticmethod
    def make_agent_lookup_field(name, value):
        prefix = {'agent_id': 'a',
                  'signature': 's',
                  'user_profile': 'u'}[name]

        return "%s:%s" % (prefix, value)

    @property
    def api_token(self):
        from solariat_bottle.db.api_auth import AuthToken
        candidates = AuthToken.objects.find(user=self)[:]
        for candidate in candidates:
            if candidate.is_valid:
                return candidate.digest
        return AuthToken.objects.create_from_user(self).digest

    @property
    def signature_suffix(self):
        ''' Used to append to a dispathched post'''
        if self._signature:
            return " %s" % self._signature.strip()
        return ''

    @property
    def roles(self):
        return [USER_ROLES[r_id] for r_id in self.user_roles]

    @property
    def main_role(self):
        if self.is_superuser:
            return "SUPERUSER"
        return compute_main_role(self.user_roles)

    @property
    def accessible_roles(self):
        roles = []
        if not (self.is_admin or self.is_staff):
            #Not an admin or staff, just see my own roles
            for role in self.user_roles:
                roles.append({'id': role, 'value': USER_ROLES[role]})
        else:
            if self.account.selected_app == 'GSE':
                if self.is_staff:
                    _roles = [STAFF, ADMIN]
                else:
                    _roles = [ADMIN]
                roles = [{'id': role, 'value': USER_ROLES[role]} for role in _roles]
            else:
                # We keep roles sorted based on level of access
                # admin, staff, super_user all should be able to CRUD roles
                # lower than theirs plus roles as their own level
                if self.is_superuser:
                    max_role = max(USER_ROLES.keys())
                else:
                    max_role = max(self.user_roles)
                for role in USER_ROLES:
                    # No one should be able to add / remove SYSTEM from a given user
                    if role <= max_role and role != SYSTEM:
                        roles.append({'id': role, 'value': USER_ROLES[role]})
        return roles

    def __sync_agent(self):
        if self.agent_id == 0:
            self.agent_id = NumberSequences.advance('agent')

        lookup = [self.make_agent_lookup_field('agent_id', self.agent_id)]
        if self.normalized_screen_name:
            lookup.append(self.make_agent_lookup_field('user_profile', self.normalized_screen_name))
        if self.signature:
            lookup.append(self.make_agent_lookup_field('signature', self.signature))

        self.agent_lookup = lookup

    def _get_user_profile(self):
        if not self._user_profile:
            return None

        from solariat_bottle.db.user_profiles.user_profile import UserProfile
        from solariat_bottle.db.user_profiles.social_profile import SocialProfile

        PROFILE_CLASSES = [SocialProfile, UserProfile]
        profile = None
        for cls in PROFILE_CLASSES:
            try:
                profile = cls.objects.get(self._user_profile)
                break
            except cls.DoesNotExist:
                continue
        return profile

    def _set_user_profile(self, value):
        self._user_profile = value.id if value is not None else value
        self.__sync_agent()

    user_profile = property(_get_user_profile, _set_user_profile)

    def _get_signature(self):
        if self._signature:
            return self._signature.strip().lower()
        return None

    def _set_signature(self, value):
        if self._signature == value:
            return
        # check that such signature is not used
        if self.account:
            if User.objects.find(_signature=value, account=self.account).count() > 0:
                raise DuplicateSignatureError('This signature is already used with this account')
        self._signature = value
        self.__sync_agent()

    signature = property(_get_signature, _set_signature)

    def signed_password_url(self):
        """  Url which can be used to reset password for this user """
        from solariat_bottle.db.api_auth import AuthToken
        auth_token = AuthToken.objects.create_for_restore(user=self)
        return "%s/users/%s/password?auth_token=%s" % (get_var('HOST_DOMAIN'), self.email, auth_token.digest)

    @property
    def screen_name(self):
        if self.user_profile:
            return self.user_profile.screen_name
        return None

    @property
    def normalized_screen_name(self):
        from ..utils.post import normalize_screen_name
        if self.screen_name:
            return normalize_screen_name(self.screen_name)
        return None

    def perms(self, user):
        """ Check what kind of permissions we have to some other user
         Could be either 'r', 'w' or None """
        if user.is_system:
            return None

        if self.is_superuser:
            return 'w'
        elif self.is_staff:
            if user.is_superuser:
                return 'r'
            else:
                return 'w'
        elif self.is_admin:
            if user.is_superuser:
                return None
            elif user.is_staff:
                return 'r'
            elif self.account == user.account:  # admin can edit other admin/normal users in same account
                # We are checking account here but nowhere else for security reason because we are allowing to edit here.
                return 'w'
            else:
                return 'r'
        else:
            if user.is_staff:
                return None
            else:
                return 'r'

    def set_password(self, raw_password):
        "hash and store password"
        self.password = make_password(raw_password)
        self.save()
        return self

    def check_password(self, raw_password):
        "Return True if password is OK"
        algo, salt, hash = self.password.split('$')
        return hash == get_hexdigest(salt, raw_password)

    @property
    def display(self):
        'Display uses the email address'
        return self.email

    @property
    def display_agent(self):
        def is_generic_agent(email):
            try:
                email_parts = email.split('@')[0].split('+')
            except:
                return False
            return len(email_parts) == 2 and email_parts[0] == 'agent' and email_parts[1].isdigit()

        if is_generic_agent(self.email):
            return self.screen_name or self.signature or self.email
        return self.email

    @property
    def team(self):
        return [ u for u in User.objects(account=self.account)
                 if u.id != self.id ]

    @property
    def is_agent(self):
        return self.account and (AGENT in self.user_roles) or self.is_staff

    @property
    def is_only_agent(self):
        """This property is for checking that the user is not more than agent.
        """
        if self.main_role == 'AGENT' or self.main_role == 'REVIEWER':
            return True
        else:
            return False

    @property
    def is_system(self):
        return SYSTEM in self.user_roles

    @property
    def is_analyst(self):
        return self.account and (ANALYST in self.user_roles) or self.is_staff

    @property
    def is_reviewer(self):
        return self.account and (REVIEWER in self.user_roles) or self.is_staff

    @property
    def is_admin(self):
        return self.account and (ADMIN in self.user_roles or self.is_staff)

    @property
    def is_staff(self):
        return self.is_superuser or STAFF in self.user_roles

    # deprecated use of account_type
    @property
    def is_gse_only_customer(self):
        return self.account.account_type == 'GSE'

    @property
    def landing_page(self):
        """ Depending on the roles that this user has, return the proper landing page. """
        if self.current_account and self.current_account.account_type == "Skunkworks":
            return "/voc"
        if self.is_admin or self.is_staff:
            return '/configure'
        if self.is_agent:
            return '/inbox'
        if self.is_analyst or self.is_reviewer:
            return '/inbound'
        return '/configure'

    def can_edit(self, target_user):
        """
        Specifies if the current user can or cannot edit a target user.
        """
        if target_user.is_superuser and not self.is_superuser:
            return False
        if target_user.is_superuser and not self.email == target_user.email:
            return False
        return True

    def set_outbound_channel(self, channel):
        self.outbound_channels[channel.platform] = channel.id
        self.save()

    def get_outbound_channel(self, platform):
        from .channel.base import Channel

        if platform in self.outbound_channels:
            channel_id = self.outbound_channels.get(platform, None)
            if channel_id:
                try:
                    ch = Channel.objects.get(id=channel_id)
                    assert(ch and ch.is_dispatchable)
                    assert(ch.platform == platform)
                    return ch
                except (Channel.DoesNotExist, AssertionError), e:
                    LOGGER.warning("User: %s get_outbound_channel: %s" % (self.email, str(e)))
                    self.outbound_channels.pop(platform)
                    self.save()
        if self.account:
            return self.account.get_outbound_channel(platform)
        return None

    def _get_current_account(self):
        return self.account

    def _set_current_account(self, acct):
        #Can set the account only if it is in the accounts list for this user
        acct_available = self.is_superuser or acct.id in self.accounts
        if acct_available and (not self.account or self.account.id != acct.id):
            self.account = acct
            self.save()

    current_account = property(_get_current_account, _set_current_account)

    @property
    def available_accounts(self):
        from ..db.account import Account
        if self.is_superuser:
            return Account.objects.find()
        else:
            return Account.objects.find(id__in=self.accounts)

    def available_groups(self, **kw):
        from ..db.group import Group
        if self.is_superuser:
            return Group.objects()
        else:
            #return Group.objects(id__in=self.groups, **kw)
            return Group.objects.find_by_user(self, **kw)

    def available_groups_by_id(self, **kw):
        groups = list(self.available_groups(**kw))
        group_ids = [str(g.id) for g in groups]
        return dict(zip(group_ids, groups))

    def to_dict(self, fields2show=None):
        base_dict = super(User, self).to_dict(fields2show)
        agent_social_profile = self.user_profile
        base_dict.pop('_user_profile', None)
        base_dict['user_profile'] = agent_social_profile and str(agent_social_profile.id)
        base_dict['roles'] = self.user_roles
        base_dict['signature'] = self._signature
        base_dict['groups'] = [str(g) for g in self.groups]
        base_dict['accounts'] = [str(acc) for acc in base_dict['accounts']]
        base_dict['is_only_agent'] = self.is_only_agent
        base_dict['is_staff'] = self.is_staff
        base_dict['is_analyst'] = self.is_analyst
        base_dict['is_reviewer'] = self.is_reviewer
        base_dict['is_admin'] = self.is_admin
        base_dict['is_superuser'] = self.is_superuser
        return base_dict


class ValidationTokenManager(Manager):
    """
    Manager for specific validation tokens that are available for signing up a new trial
    """
    def create_by_user(self, user, **kw):
        if 'creator' not in kw:
            kw['creator'] = user
        kw['digest'] = get_random_digest()
        return Manager.create(self, **kw)


class ValidationToken(Document):
    """
    Class of tokens available for signing up trials. These expose a consume method so we can invalidate
    them after they have been successfully used.
    """
    manager = ValidationTokenManager

    creator = fields.ReferenceField(User, db_field='crt')
    target = fields.ReferenceField(User, db_field='tgt')
    digest = fields.StringField(unique=True, db_field='dgt')
    is_valid = fields.BooleanField(default=True, db_field='iv')

    @property
    def signup_url(self):
        """  The signup url validated by this specific validation token """
        return get_var('HOST_DOMAIN') + '/signup?validation_token=' + self.digest

    def consume(self):
        # Make sure we only use one token once
        self.reload()
        if not self.is_valid:
            raise AuthError("Attempt to use same validation token twice.")
        self.is_valid = False
        self.save()
