from bson.objectid import ObjectId
import logging as LOGGER
from solariat.db.abstract import fields, Document, Manager
from solariat_bottle.db.roles import USER_ROLES, ADMIN, REVIEWER, AGENT, ANALYST
from solariat_bottle.settings import AppException
from solariat_bottle.utils.post import get_service_channel


def __ensure_acc_id(account):
    # commented out by Sasha on 2014.10.13 -- seems to be useless here
    #from solariat_bottle.db.account import Account  # To avoid circular deps

    if type(account) in (str, unicode, ObjectId):
        return str(account)
    return str(account.id)


def default_admin_group(account):
    """ Each account will have a default admin group which contains all admins
     which have the given account set as the current one. """
    return '%s:%s' % (__ensure_acc_id(account), ADMIN)


def default_agent_group(account):
    """ Each account will have a default agent group which will contain all
     AGENT users of the current account """
    return '%s:%s' % (__ensure_acc_id(account), AGENT)


def default_analyst_group(account):
    """ Each account will have a default agent group which will contain all
     ANALYST and REVIEWER users of the current account """
    return '%s:%s' % (__ensure_acc_id(account), ANALYST)


def default_reviewer_group(account):
    """ Each account will have a default agent group which will contain all
     ANALYST and REVIEWER users of the current account """
    return '%s:%s' % (__ensure_acc_id(account), REVIEWER)


class GroupManager(Manager):

    def create(self, **kw):
        # check that group with the same name does not exist for this account
        if Group.objects.find(
                name=kw.get('name', ''),
                account=kw.get('account', '')).count():
            raise AppException('A group with same name exists for this account')
        return super(GroupManager, self).create(**kw)

    def create_by_user(self, user, name, description, members, roles, channels, smart_tags=None,
                        journey_types=None, journey_tags=None, funnels=None, predictors=None):
        from solariat_bottle.db.channel.base import Channel
        from solariat_bottle.db.journeys.journey_type import JourneyType
        from solariat_bottle.db.journeys.journey_tag import JourneyTag
        from solariat_bottle.db.funnel import Funnel
        from solariat_bottle.db.predictors.base_predictor import BasePredictor

        if not (user.is_staff or user.is_admin):
            raise RuntimeError("Only admin and staff users are allowed to create groups.")
        roles = [int(role) for role in roles] if roles is not None else []
        if not user.current_account:
            LOGGER.error(
                "No account could be found for user {}. Aborting group creation.".format(
                    user.email
                ))
            raise AppException("Error accessing database, we could not load your account." +
                               "Please try later. If this keeps reproducing please contact a Staff member.")

        if smart_tags is None:
            smart_tags = []
        if journey_types is None:
            journey_types = []
        if journey_tags is None:
            journey_tags = []
        if funnels is None:
            funnels = []
        if predictors is None:
            predictors = []

        group = super(GroupManager, self).create(name=name,
                                                 description=description,
                                                 members=list(set(members)),
                                                 channels=channels,
                                                 account=user.current_account,
                                                 smart_tags=smart_tags,
                                                 roles=roles,
                                                 journey_types=journey_types,
                                                 journey_tags=journey_tags,
                                                 funnels=funnels,
                                                 predictors=predictors)
        # Update acl for objects which this group was given access to
        for channel in Channel.objects.find(id__in=[ObjectId(c_id) for c_id in channels]):
            if channel.is_inbound:
                channel = get_service_channel(channel) or channel
            channel.add_perm(user, group=group, to_save=True)

        for tag in Channel.objects.find(id__in=[ObjectId(c_id) for c_id in smart_tags]):
            tag.add_perm(user, group=group, to_save=True)

        for jty in JourneyType.objects.find(id__in=journey_types):
            jty.add_perm(user, group=group, to_save=True)

        for jtg in JourneyTag.objects.find(id__in=journey_tags):
            jtg.add_perm(user, group=group, to_save=True)

        for fnl in Funnel.objects.find(id__in=funnels):
            fnl.add_perm(user, group=group, to_save=True)

        for prd in BasePredictor.objects.find(id__in=predictors):
            prd.add_perm(user, group=group, to_save=True)

        # Update members which are part of this group
        user_ids = [user.objects.get(u_id).id for u_id in members]
        if roles:
            # There are roles added to this group, we need to add all users which
            # have any of those associated roles to the group
            valid_users = user.objects.find(account=user.current_account, user_roles__in=roles)[:]
            user_ids.extend([u.id for u in valid_users])
        user.objects.coll.update({'_id': {'$in': user_ids}},
                                 {'$addToSet': {user.__class__.groups.db_field: group.id}},
                                 multi=True)
        return group

    def remove_by_user(self, user, *args, **kw):
        from solariat_bottle.db.channel.base import Channel
        if args:
            kw['id'] = args[0]
        kw.update({'account': user.current_account})
        Channel.objects.remove_groups_by_user(user, kw['id__in'])
        Manager.remove(self, **kw)

    def find_by_user(self, user, **kw):
        kw.update({'account': user.current_account})
        full_list = Manager.find(self, **kw)
        if not (user.is_admin or user.is_staff):
            full_list = [group for group in full_list if group.id in user.groups]
        return full_list


class Group(Document):
    name = fields.StringField(required=True)
    account = fields.ReferenceField('Account', db_field='acnt')
    description = fields.StringField()
    members = fields.ListField(fields.ReferenceField('User'))
    roles = fields.ListField(fields.NumField(choices=USER_ROLES.keys()), db_field='ur')

    channels = fields.ListField(fields.ReferenceField('Channel'), db_field='chs')
    smart_tags = fields.ListField(fields.ReferenceField('Channel'), db_field='sts')
    journey_types = fields.ListField(fields.ReferenceField('JourneyType'), db_field='jty')
    journey_tags = fields.ListField(fields.ReferenceField('JourneyTag'), db_field='jtg')
    funnels = fields.ListField(fields.ReferenceField('Funnel'), db_field='fnl')
    predictors = fields.ListField(fields.ReferenceField('BasePredictor'), db_field='prd')

    manager = GroupManager

    def save(self, **kw):
        # check that no other groups exist with the same combination of
        # name and account
        name = kw.get('name', self.name)
        account = kw.get('account', self.account)
        for g in Group.objects.find(
                name=name,
                account=account):
            if not self.id == g.id:
                raise AppException('A group with same name exists for this account')
        super(Group, self).save(**kw)

    def to_dict(self):
        from solariat.utils.timeslot import datetime_to_timestamp_ms
        return {'id': str(self.id),
                'created_at': datetime_to_timestamp_ms(self.created),
                'members': [str(_.id) for _ in self.members],
                'smart_tags': [str(_.id) for _ in self.smart_tags],
                'channels': [str(_.id) for _ in self.channels],
                'journey_types': [str(_.id) for _ in self.journey_types],
                'journey_tags': [str(_.id) for _ in self.journey_tags],
                'funnels': [str(_.id) for _ in self.funnels],
                'predictors': [str(_.id) for _ in self.predictors],
                'roles': self.roles,
                'name': self.name,
                'description': self.description,
                'members_total': self.members_total}

    @staticmethod
    def analysts(account):
        """ Return a dict representation of a default group for all analysts of an account """
        from solariat.utils.timeslot import datetime_to_timestamp_ms, now
        return {'id': default_analyst_group(account),
                'created_at': datetime_to_timestamp_ms(now()),
                'members': [],
                'smart_tags': [],
                'channels': [],
                'journey_types': [],
                'journey_tags': [],
                'funnels': [],
                'predictors': [],
                'roles': [ANALYST],
                'name': 'All Analysts of account %s' % account.name,
                'description': 'All Analysts of account %s' % account.name,
                'members_total': 'N/A'}

    @staticmethod
    def agents(account):
        """ Return a dict representation of a default group for all agents of an account """
        from solariat.utils.timeslot import datetime_to_timestamp_ms, now
        return {'id': default_agent_group(account),
                'created_at': datetime_to_timestamp_ms(now()),
                'members': [],
                'smart_tags': [],
                'channels': [],
                'journey_types': [],
                'journey_tags': [],
                'funnels': [],
                'predictors': [],
                'roles': [AGENT],
                'name': 'All Agents of account %s' % account.name,
                'description': 'All Agents of account %s' % account.name,
                'members_total': 'N/A'}

    def _role_check(self, member, removed_roles):
        remaining_group_roles = set([role for role in self.roles if role not in removed_roles])
        remaining_user_roles = set([role for role in member.user_roles if role not in removed_roles])
        if not remaining_user_roles.intersection(remaining_group_roles):
            return False
        return True

    def update(self, user, name, description, members, roles, channels, smart_tags=None,
                journey_types=None, journey_tags=None, funnels=None, predictors=None):
        # First, handle any changes in roles. If new ones were added, we automatically need
        # to add extra members. If any were removed, we need to remove batch of members
        from solariat_bottle.db.user import User
        from solariat_bottle.db.channel.base import Channel
        from solariat_bottle.db.journeys.journey_type import JourneyType
        from solariat_bottle.db.journeys.journey_tag import JourneyTag
        from solariat_bottle.db.funnel import Funnel
        from solariat_bottle.db.predictors.base_predictor import BasePredictor

        o_roles = [int(role) for role in roles]
        new_roles = [role for role in o_roles if role not in self.roles]
        removed_roles = [role for role in self.roles if role not in o_roles]
        # Some users have implicit access due to their role. Check if we need to remove this
        # based on the role we just set
        full_user_access = User.objects.find(groups__in=[self.id])
        removed_members = [member for member in full_user_access if not self._role_check(member, removed_roles)]
        # For member that were a part only because of a role on this group, remove them now
        for member in removed_members:
            if self.id in member.groups:
                member.groups.remove(self.id)
                member.save()
        # For new members that would have access because of the role of the group, add group
        for new_member in User.objects.find(account=self.account, user_roles__in=new_roles):
            if self.id not in new_member.groups:
                new_member.groups.append(self.id)
                new_member.save()
        # Now for actual hard specified members, also add group
        user_ids = [User.objects.get(u_id).id for u_id in members]
        User.objects.coll.update({'_id': {'$in': user_ids}},
                                 {'$addToSet': {User.groups.db_field: self.id}},
                                 multi=True)

        new_channels = [channel for channel in channels if channel not in self.channels]
        removed_channels = []
        for channel in self.channels:
            if str(channel.id) not in channels:
                removed_channels.append(channel.id)
        # Remove acl permissions for removed channels
        for channel in Channel.objects.find(id__in=[ObjectId(c_id) for c_id in removed_channels]):
            if channel.is_inbound:
                channel = get_service_channel(channel) or channel
            channel.del_perm(user, group=self, to_save=True)
        # Update acl for objects which this group was given access to
        for channel in Channel.objects.find(id__in=[ObjectId(c_id) for c_id in new_channels]):
            if channel.is_inbound:
                channel = get_service_channel(channel) or channel
            channel.add_perm(user, group=self, to_save=True)

        if smart_tags:
            new_tags = [tag for tag in smart_tags if tag not in self.smart_tags]
            removed_tags = []
            for tag in self.smart_tags:
                if str(tag.id) not in smart_tags:
                    removed_tags.append(tag.id)
            # Remove acl permissions for removed smart_tags
            for tag in Channel.objects.find(id__in=[ObjectId(c_id) for c_id in removed_tags]):
                tag.del_perm(user, group=self, to_save=True)
            # Update acl for objects which this group was given access to
            for tag in Channel.objects.find(id__in=[ObjectId(c_id) for c_id in new_tags]):
                tag.add_perm(user, group=self, to_save=True)

        if journey_types:
            saved_journey_types = set(str(_.id) for _ in self.journey_types)
            new_journey_types = set(journey_types) - saved_journey_types
            removed_journey_types = saved_journey_types - set(journey_types)
            for jty in JourneyType.objects.find(id__in=new_journey_types):
                jty.add_perm(user, group=self, to_save=True)
            for jty in JourneyType.objects.find(id__in=removed_journey_types):
                jty.del_perm(user, group=self, to_save=True)

        if journey_tags:
            saved_journey_tags = set(str(_.id) for _ in self.journey_tags)
            new_journey_tags = set(journey_tags) - saved_journey_tags
            removed_journey_tags = saved_journey_tags - set(journey_tags)
            for jtg in JourneyTag.objects.find(id__in=new_journey_tags):
                jtg.add_perm(user, group=self, to_save=True)
            for jtg in JourneyTag.objects.find(id__in=removed_journey_tags):
                jtg.del_perm(user, group=self, to_save=True)

        if funnels:
            saved_funnels = set(str(_.id) for _ in self.funnels)
            new_funnels = set(funnels) - saved_funnels
            removed_funnels = saved_funnels - set(funnels)
            for fnl in Funnel.objects.find(id__in=new_funnels):
                fnl.add_perm(user, group=self, to_save=True)
            for fnl in Funnel.objects.find(id__in=removed_funnels):
                fnl.del_perm(user, group=self, to_save=True)

        if predictors:
            saved_predictors = set(str(_.id) for _ in self.predictors)
            new_predictors = set(predictors) - saved_predictors
            removed_predictors = saved_predictors - set(predictors)
            for prd in BasePredictor.objects.find(id__in=new_predictors):
                prd.add_perm(user, group=self, to_save=True)
            for prd in BasePredictor.objects.find(id__in=removed_predictors):
                prd.del_perm(user, group=self, to_save=True)

        # Update members which are part of this group
        '''user_ids = [user.objects.get(u_id).id for u_id in members]
        user.objects.coll.update({'_id': {'$in': user_ids}},
                                 {'$addToSet': {user.__class__.groups.db_field: self.id}},
                                 multi=True)'''

        self.name = name
        self.description = description
        self.members = members
        self.roles = [int(r) for r in roles]
        self.channels = channels
        if smart_tags:
            self.smart_tags = smart_tags
        if journey_types:
            self.journey_types = journey_types
        if journey_tags:
            self.journey_tags = journey_tags
        if funnels:
            self.funnels = funnels
        if predictors:
            self.predictors = predictors
        self.save()


    def add_user(self, user, perms='r'):
        """
        Wrapper for add_perms that accepts `user` parameter
        either as email string or object.
        """
        from ..db.account import _get_user
        user = _get_user(user)
        if user:
            user.update(addToSet__groups=self.id)
            if not user in self.members:
                self.members.append(user)
                self.save()
            return True
        else:
            return False

    def can_edit(self, user):
        return user.is_admin or user.is_staff

    def del_user(self, user, perms='rw'):
        from ..db.account import _get_user
        user = _get_user(user)
        if user:
            user.update(pull__groups=str(self.id))
            if user in self.members:
                #self.members.remove(user)  # fails in ListBridge
                self.members = filter(lambda x:x.id!=user.id, list(self.members))
                self.save()
            return True
        else:
            return False

    def clear_users(self):
        from solariat_bottle.db.user import User
        u_ids = [u.id for u in User.objects.find(groups__in=[self.id])]
        User.objects.coll.update({'_id': {'$in': u_ids}},
                                 {'$pull': {User.groups.db_field: self.id}},
                                 multi=True)

    def get_all_users(self):
        """
        Return list of users that have access to account.
        """
        from solariat_bottle.db.user import User
        return User.objects.find(groups__in=[self.id])[:]

    def get_users(self, current_user):
        return [u for u in self.get_all_users() if u != current_user]

    @property
    def members_total(self):
        from solariat_bottle.db.user import User
        return User.objects(groups__in=[self.id]).count()

    def __unicode__(self):
        return self.name
