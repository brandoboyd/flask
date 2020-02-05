from solariat_bottle.api.base import ModelAPIView, api_request
import solariat_bottle.api.exceptions as exc

from solariat_bottle.db.channel.base import Channel, ServiceChannel
from solariat_bottle.db.events.event import Event
from solariat_bottle.db.post.voice import VoicePost
from solariat_bottle.db.post.web_clicks import WebClick
from solariat_bottle.db.post.chat import ChatPost
from solariat_bottle.db.dynamic_classes import InfomartEvent, RevenueEvent, NPSEvent
from solariat_bottle.db.events.call_event import CallEvent
from solariat_bottle.db.predictors.multi_channel_smart_tag import EventTag
from solariat_bottle.db.events.event import JourneyTypeStagePair
from solariat_bottle.db.post.utils import factory_by_user

from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType


class EventAPIView(ModelAPIView):
    model = Event
    endpoint = 'events'
    required_fields = ['channel',]

    EVENT_MODEL_MAP = dict(web=WebClick,
                           chat=ChatPost,
                           call=CallEvent,
                           voice=VoicePost,
                           imart=InfomartEvent,
                           revenue=RevenueEvent,
                           nps=NPSEvent)

    commands = ['accept', 'reject', 'tags']

    @classmethod
    def register(cls, app):
        """ Queue API allows for extra commands, like 'fetch' and 'confirm' """
        url = cls.get_api_url()
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(url, view_func=view_func, methods=['GET',])
        app.add_url_rule(url, view_func=view_func, methods=['POST',])
        app.add_url_rule(cls.get_api_url('<_id>'),
                         view_func=view_func,
                         methods=['GET', 'PUT', 'DELETE', 'POST'])

    @api_request
    def handle_accept(self, user, *args, **kwargs):
        if 'event_id' not in kwargs:
            raise exc.InvalidParameterConfiguration("Expected required field 'event_id'")

        if 'tag_id' not in kwargs:
            raise exc.InvalidParameterConfiguration("Expected required field 'tag_id'")
        event_type = kwargs.pop('type', None)
        model_klass = self.EVENT_MODEL_MAP.get(event_type, Event)

        evt = model_klass.objects.get(kwargs['event_id'])
        tag = EventTag.objects.get(kwargs['tag_id'])
        evt.add_tag(tag)
        return self._format_single_doc(evt)

    @api_request
    def handle_reject(self, user, *args, **kwargs):
        if 'event_id' not in kwargs:
            raise exc.InvalidParameterConfiguration("Expected required field 'event_id'")

        if 'tag_id' not in kwargs:
            raise exc.InvalidParameterConfiguration("Expected required field 'tag_id'")
        event_type = kwargs.pop('type', None)
        model_klass = self.EVENT_MODEL_MAP.get(event_type, Event)

        evt = model_klass.objects.get(kwargs['event_id'])
        tag = EventTag.objects.get(kwargs['tag_id'])
        evt.remove_tag(tag)
        return self._format_single_doc(evt)

    @api_request
    def get_tags(self, user, *args, **kwargs):
        if 'channel_id' not in kwargs:
            raise exc.InvalidParameterConfiguration("Expected required field 'channel_id'")
        try:
            channel = Channel.objects.get(kwargs['channel_id'])
        except Channel.DoesNotExist:
            return dict(ok=False, error="There is no channel with id=%s in the system." % kwargs['channel_id'])
        channels = [channel.id]
        if isinstance(channel, ServiceChannel):
            channels.extend([channel.inbound_channel.id, channel.outbound_channel.id])
        return dict(ok=True, list=[dict(id=str(tag.id),
                                        display_name=str(tag.display_name))
                                   for tag in EventTag.objects.find(channels__in=channels)])

    def post(self, _id=None, *args, **kwargs):
        if _id in self.commands:
            if _id == 'accept':
                return self.handle_accept(*args, **kwargs)
            if _id == 'reject':
                return self.handle_reject(*args, **kwargs)
            if _id == 'tags':
                return self.get_tags(*args, **kwargs)
        return self._post(*args, **kwargs)

    def get(self, _id=None, *args, **kwargs):
        if _id in self.commands:
            if _id == 'accept':
                return self.handle_accept(*args, **kwargs)
            if _id == 'reject':
                return self.handle_reject(*args, **kwargs)
            if _id == 'tags':
                return self.get_tags(*args, **kwargs)
        return self._get(*args, **kwargs)

    def _upsert_journey_stage_pair(self, user, stages_info):
        stages = []
        for stage_entry in stages_info:
            if 'journey_type_id' in stage_entry and 'journey_stage_id' in stage_entry:
                stages.append(JourneyTypeStagePair(journey_type_id=stage_entry['journey_type_id'],
                                                   journey_stage_id=stage_entry['journey_stage_id']))
            elif 'journey_type_name' in stage_entry and 'journey_stage_name' in stage_entry:
                journey_type = JourneyType.objects.get(account_id=user.account.id,
                                                       display_name=stage_entry['journey_type_name'])
                journey_stage = JourneyStageType.objects.get(account_id=user.account.id,
                                                             journey_type_id=journey_type.id,
                                                             display_name=stage_entry['journey_stage_name'])
                stages.append(JourneyTypeStagePair(journey_type_id=journey_type.id,
                                                   journey_stage_id=journey_stage.id))
        return stages
    
    def _create_doc(self, user, format_docs=True, *args, **kwargs):
        """ Create a new document in the collection """
        CustomerProfile = user.account.get_customer_profile_class()
        AgentProfile = user.account.get_agent_profile_class()
        from solariat_bottle.utils.views import parse_bool

        return_response = parse_bool(kwargs.pop('_return_response', format_docs))
        event_type = kwargs.pop('type', None)
        model_klass = self.EVENT_MODEL_MAP.get(event_type, Event)
        assert kwargs.get('native_id') or kwargs.get('actor_id'), (kwargs.get('native_id'), kwargs.get('actor_id'))
        native_id = kwargs.pop('native_id', None)

        if kwargs.get('journey_stages'):
            kwargs['journey_stages'] = self._upsert_journey_stage_pair(user, kwargs['journey_stages'])
        if native_id:
            assert native_id, kwargs
            profile_cls = model_klass.PROFILE_CLASS
            try:
                platform_profile = profile_cls.objects.get(native_id=native_id)
            except profile_cls.DoesNotExist:
                platform_profile = profile_cls.objects.create(native_id=native_id)
                platform_profile.save()

            AccountProfileCls = kwargs['is_inbound'] and CustomerProfile or AgentProfile
            channel = Channel.objects.get(kwargs['channels'][0])
            try:
                actor_profile = AccountProfileCls.objects.get(
                    account_id=channel.account.id,
                    linked_profile_ids__in=[str(platform_profile.id)]
                )
            except AccountProfileCls.DoesNotExist:
                actor_profile = AccountProfileCls.objects.create(
                    account_id=channel.account.id,
                    linked_profile_ids=[str(platform_profile.id)]
                )
            kwargs['actor_id'] = str(actor_profile.id)
        elif kwargs.get('actor_id'):
            if kwargs['is_inbound']:
                kwargs['actor_id'] = CustomerProfile.objects.get(kwargs.get('actor_id')).id
            else:
                kwargs['actor_id'] = AgentProfile.objects.get(kwargs.get('actor_id')).id
        else:
            raise Exception('either "native_id" or "actor_id" should be provided')

        if event_type in ('chat', 'voice', 'twitter', 'facebook'):
            doc = factory_by_user(user, **kwargs)
        else:
            doc = model_klass.objects.create_by_user(user, safe_create=True, **kwargs)

        if return_response and format_docs:
            return self._format_single_doc(doc)
        if not return_response:
            return {"ok": True}
        return doc


