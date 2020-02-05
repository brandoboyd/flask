from solariat.db import fields
from solariat_bottle.db.auth import ArchivingAuthDocument, ArchivingAuthManager


class BaseEventTypeManager(ArchivingAuthManager):

    def get_by_display_name(self, account_id, display_name):
        platform, name = BaseEventType.parse_display_name(display_name)
        return self.get(account_id=account_id, platform=platform, name=name)

    def find_one_by_display_name(self, account_id, display_name):
        platform, name = BaseEventType.parse_display_name(display_name)
        return self.find_one(account_id=account_id, platform=platform, name=name)


class BaseEventType(ArchivingAuthDocument):  # or still Document?

    collection = 'EventType'
    manager = BaseEventTypeManager
    allow_inheritance = True

    SEP = ' -> '

    platform = fields.StringField(required=True)
    # TODO: check uniqueness
    name = fields.StringField(required=True)  # unique=True
    account_id = fields.ObjectIdField(required=True)

    @property
    def display_name(self):
        return self.SEP.join((self.platform, self.name))

    @staticmethod
    def parse_display_name(display_name):
        platform, name = display_name.split(BaseEventType.SEP)
        return platform, name

    def to_dict(self, fields2show=None):
        data = super(BaseEventType, self).to_dict(fields2show)
        data['display_name'] = self.display_name
        return data


class StaticEventType(BaseEventType):

    attributes = fields.ListField(fields.StringField())

    is_static = True

    EVENT_TYPES = {
        'Facebook': ['Comment'],
        'Twitter': ['Tweet'],
        'Chat': ['Message'],
        'Voice': ['Call'],
        'Email': ['Message'],
        'Web': ['Click'],
        'FAQ': ['Search'],
        'Branch': ['Visit'],
        'VOC': ['Score'],
    }

    @staticmethod
    def generate_static_event_types(user, event_types=EVENT_TYPES):
        types = []
        for platform, names in event_types.iteritems():
            for name in names:
                types.append(StaticEventType.objects.create_by_user(
                    user,
                    account_id=user.account.id,
                    platform=platform,
                    name=name,
                    attributes=['stage_metadata']
                ))
        return types
