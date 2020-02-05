from datetime import datetime
from flask import jsonify, render_template, request
from urllib import unquote
from bson.objectid import ObjectId
from solariat_bottle.db.channel.base import Channel

from solariat_bottle.db.dynamic_channel import ChannelType
from solariat_bottle.db.dynamic_event import EventType
from solariat_bottle.db.events.event_type import BaseEventType, StaticEventType
from solariat_bottle.db.schema_based import get_query_by_dates
from solariat_bottle.schema_data_loaders.base import WrongFileExtension
from solariat_bottle.schema_data_loaders.csv import CsvDataLoader
from solariat_bottle.schema_data_loaders.json import JsonDataLoader

from solariat.utils import timeslot
from solariat_bottle.views.base import BaseMultiActionView
from solariat_bottle.utils.views import required_fields, ParamIsMissing
from solariat_bottle.settings import LOGGER, AppException
from solariat_bottle.app import app

# TODO: Change this to be done via introspection of channel / post subpackages
from solariat_bottle.db.post.branch import BranchEvent
from solariat_bottle.db.post.chat import ChatPost
from solariat_bottle.db.post.email import EmailPost
from solariat_bottle.db.post.facebook import FacebookPost
from solariat_bottle.db.post.faq_query import FAQQueryEvent
from solariat_bottle.db.post.twitter import TwitterPost
from solariat_bottle.db.post.nps import NPSOutcome
from solariat_bottle.db.post.voice import VoicePost
from solariat_bottle.db.post.web_clicks import WebClick

from solariat_bottle.db.channel.branch import BranchChannel
from solariat_bottle.db.channel.chat import ChatServiceChannel
from solariat_bottle.db.channel.email import EmailServiceChannel
from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.db.channel.faq import FAQChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.channel.voc import VOCServiceChannel
from solariat_bottle.db.channel.voice import VoiceServiceChannel
from solariat_bottle.db.channel.web_click import WebClickChannel

# TODO: move to StaticEventType, use post.utils.POST_PLATFORM_MAP
STATIC_EVENT_TYPE_MAPPING = {BranchChannel: BranchEvent,
                             ChatServiceChannel: ChatPost,
                             EmailServiceChannel: EmailPost,
                             FacebookServiceChannel: FacebookPost,
                             FAQChannel: FAQQueryEvent,
                             TwitterServiceChannel: TwitterPost,
                             VOCServiceChannel: NPSOutcome,
                             VoiceServiceChannel: VoicePost,
                             WebClickChannel: WebClick}

STATIC_CHANNEL_EVENT_TYPE_DATA = {'id': 'builtin', 'name': 'builtin', 'sync_status': 'synced'}

KEY_NAME = 'name'
KEY_CHANNEL_TYPE_ID = 'channel_type_id'
KEY_PLATFORM = 'platform'
KEY_FILE = 'file'
KEY_SCHEMA = 'schema'
KEY_CHANNEL_ID = 'channel_id'


class EventTypeView(BaseMultiActionView):

    url_rules = [
        ('/event_type/create', ['POST'], 'create'),
        ('/event_type/get/<path:name>', ['GET'], 'get'),
        ('/event_type/delete/<path:name>', ['POST'], 'delete'),
        ('/event_type/list', ['GET'], 'list'),

        ('/event_type/update_schema/<path:name>', ['POST'], 'update_schema'),
        ('/event_type/discover_schema', ['POST'], 'discover_schema'),
        ('/event_type/import_data', ['POST'], 'import_data'),
        ('/event_type/sync/apply/<path:name>', ['POST'], 'apply_sync'),
        ('/event_type/sync/accept/<path:name>', ['POST'], 'accept_sync'),
        ('/event_type/sync/cancel/<path:name>', ['POST'], 'cancel_sync'),
    ]

    def _get(self, user, name):
        return EventType.objects.find_one_by_user(self.user,
                                                  parent_id=self.user.account.id,
                                                  name=name)

    def get_data_loader_by_ext(self, input_file, params):
        if input_file.filename.lower().endswith('.csv'):
            return CsvDataLoader(input_file.stream, sep=params['sep'])
        if input_file.filename.lower().endswith('.json'):
            def type_getter(data):
                return data.get('event_type')
            return JsonDataLoader(input_file.stream, data_type_getter=type_getter)
        raise WrongFileExtension('Only CSV and JSON are supported.')

    def get_parameters(self):
        params = super(EventTypeView, self).get_parameters()
        if KEY_NAME in params:
            params[KEY_NAME] = unquote(params[KEY_NAME])
        return params

    @required_fields(KEY_NAME, KEY_PLATFORM)
    def create(self, *args, **kwargs):
        # needs to create:
        # 1. channel instance
        # 2. list of existing event types in this ChannelType
        acc = self.user.account
        platform = kwargs[KEY_PLATFORM]
        channel_type = ChannelType.objects.find_one_by_user(self.user, name=platform)
        event_type = acc.event_types.create(self.user, channel_type, kwargs[KEY_NAME])
        return event_type.to_dict()

    @required_fields(KEY_CHANNEL_ID)
    def import_data(self, *args, **kwargs):
        from solariat_bottle.db.channel.base import Channel

        channel_id = ObjectId(kwargs[KEY_CHANNEL_ID])
        channel = Channel.objects.find_one_by_user(self.user, id=channel_id)
        if channel.__class__ in STATIC_EVENT_TYPE_MAPPING:
            event_type = STATIC_EVENT_TYPE_MAPPING[channel.__class__]
        else:
            name = kwargs.get(KEY_NAME)
            event_type = None
            if name:
                event_type = self._get(self.user, kwargs[KEY_NAME])
                if not event_type:
                    return {'error': 'EventType not found %s' % str(kwargs)}

        input_file = kwargs[KEY_FILE]
        data_loader = self.get_data_loader_by_ext(input_file, kwargs)

        if isinstance(event_type, EventType):
            self.user.account.event_types.import_data(self.user,
                                                      channel,
                                                      event_type,
                                                      data_loader)
            return event_type.to_dict()
        else:
            # TODO: currently static event types imported only for 1 event_type/channel
            return event_type.import_data(self.user, channel, data_loader)

    @required_fields(KEY_NAME)
    def get(self, *args, **kwargs):
        event_type = self._get(self.user, kwargs[KEY_NAME])
        d = event_type.to_dict(include_cardinalities=True)
        return d

    def list(self, *args, **kwargs):
        account_id = self.user.account.id
        platform = kwargs.get(KEY_PLATFORM)

        # list event types for choosen channel when importing events
        if platform:
            if platform in StaticEventType.EVENT_TYPES:
                return [STATIC_CHANNEL_EVENT_TYPE_DATA]

            event_types = BaseEventType.objects.find_by_user(
                self.user, account_id=account_id, platform=platform)
            return [et.to_dict(fields2show=('id', 'name', 'sync_status')) for et in event_types]

        # list event_types for journey type stages
        if kwargs.get('show_all'):
            event_types = BaseEventType.objects.find_by_user(self.user, account_id=account_id)
            return [et.to_dict() for et in event_types]

        # list dynamic event types
        from_dt = to_dt = None
        if 'from' in kwargs:
            from_dt = timeslot.parse_datetime(kwargs['from'])
            to_dt = timeslot.parse_datetime(kwargs['to'])

        date_query = get_query_by_dates(from_dt, to_dt)
        event_types = EventType.objects.find_by_user(self.user,
                                                     parent_id=self.user.account.id,
                                                     **date_query)

        return [s.to_dict() for s in event_types]

    @required_fields(KEY_NAME)
    def delete(self, *args, **kwargs):
        event_type = self._get(self.user, kwargs[KEY_NAME])
        if not event_type:
            return

        event_type.delete_by_user(self.user, account=self.user.account, name=kwargs[KEY_NAME])
        return {}

    @required_fields(KEY_FILE)
    def discover_schema(self, *args, **kwargs):
        input_file = kwargs['file']
        data_loader = self.get_data_loader_by_ext(input_file, kwargs)
        schema = data_loader.read_schema()

        name = kwargs.get(KEY_NAME)
        event_type = None
        if name:
            event_type = self._get(self.user, kwargs[KEY_NAME])
            if not event_type:
                return

        if event_type:
            if isinstance(data_loader, JsonDataLoader) and event_type.name in schema:
                event_type.update(discovered_schema=[event_type.name])
            else:
                event_type.update(discovered_schema=schema)
            return event_type.to_dict()

        if isinstance(data_loader, CsvDataLoader):
            raise ParamIsMissing('"name" parameter is required if CSV file is used for discovery')

        res = []
        for ev_name, ev_schema in schema.iteritems():
            event_type = self._get(self.user, ev_name)
            if not event_type:
                continue
            event_type.update(discovered_schema=ev_schema)
            res.append(event_type)

        if not res:
            return

        return [ev.to_dict() for ev in res]

    @required_fields(KEY_NAME, KEY_SCHEMA)
    def update_schema(self, *args, **kwargs):
        event_type = self._get(self.user, kwargs[KEY_NAME])
        event_type.update_schema(kwargs[KEY_SCHEMA])
        return event_type.to_dict()

    @required_fields(KEY_NAME)
    def apply_sync(self, *args, **kwargs):
        event_type = self._get(self.user, kwargs[KEY_NAME])
        event_type.apply_sync()
        return event_type.to_dict()

    @required_fields(KEY_NAME)
    def cancel_sync(self, *args, **kwargs):
        event_type = self._get(self.user, kwargs[KEY_NAME])
        event_type.cancel_sync()
        return event_type.to_dict()

    @required_fields(KEY_NAME)
    def accept_sync(self, *args, **kwargs):
        event_type = self._get(self.user, kwargs[KEY_NAME])
        event_type.accept_sync()
        return event_type.to_dict()


EventTypeView.register(app)
