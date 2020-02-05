import json
import datetime
from bson.objectid import ObjectId

from solariat_bottle.tests.base import RestCase
from solariat_bottle.settings import LOGGER

from ..db.post.utils    import factory_by_user

from ..db.conversation  import Conversation
from solariat_bottle.db.user_profiles.chat_profile import ChatProfile
from solariat_bottle.db.events.event import Event
from ..db.channel.chat  import ChatServiceChannel as CSC
from ..db.account       import Account
from solariat_bottle.utils.id_encoder import unpack_event_id

now = datetime.datetime.now
ALTERNATE_DATETIME_FORMAT = '%m/%d/%Y'
TEST_SURVEY_DATE = '2014-12-16 12:13:14'

from solariat_bottle.db.schema_based import (
    KEY_IS_ID, KEY_NAME, KEY_TYPE, KEY_EXPRESSION, TYPE_INTEGER,
    TYPE_STRING, TYPE_BOOLEAN, TYPE_LIST, TYPE_DICT)
from solariat_bottle.schema_data_loaders.base import SchemaProvidedDataLoader

class APIChatCase(RestCase):

    def setUp(self, *args, **kwargs):
        super(APIChatCase, self).setUp(*args, **kwargs)

        schema = list()

        account = Account.objects.get_or_create(name='Test')
        schema.append({ KEY_NAME: 'first_name',KEY_TYPE: TYPE_STRING, KEY_IS_ID: True})
        schema_entity = account.customer_profile.create(self.user, SchemaProvidedDataLoader(schema))
        schema_entity.update_schema(schema_entity.discovered_schema)
        schema_entity.apply_sync()
        schema_entity.accept_sync()

        schema_entity = account.agent_profile.create(self.user, SchemaProvidedDataLoader(schema))
        schema_entity.update_schema(schema_entity.discovered_schema)
        schema_entity.apply_sync()
        schema_entity.accept_sync()

        self.token = self.get_token()
        CustomerProfile = account.get_customer_profile_class()
        AgentProfile = account.get_agent_profile_class()
        self.customer_profile = CustomerProfile.objects.create(id=str(ObjectId()),first_name='Alex')
        self.chat_profile = ChatProfile()
        self.chat_profile.save()
        self.customer_profile.add_profile(self.chat_profile)
        self.agent_profile = AgentProfile(id=str(ObjectId()))
        self.agent_profile.save()
        self.agent_profile.first_name = 'Bogdan'
        self.agent_profile.save()

        self.user.account = account
        self.user.save()
        self.sc = CSC.objects.create_by_user(
            self.user,
            account=account,
            title='test chat service channel')

        self.inbound = self.sc.inbound_channel
        self.outbound = self.sc.outbound_channel
        self.sc.save()
        self.customer_profile.update(account_id=account.id)
        self.agent_profile.update(account_id=account.id)

    def test_summary(self):
        token = self.get_token()
        conv = self._create_conversation(session_id='chat_session_id')[0]

        request_data = {
            'conversation_id': str(conv.id),
            'token': token
        }
        resp = self.client.get(
            '/api/v2.0/chat/summary',
            data=json.dumps(request_data),
            content_type='application/json',
            base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['topics'])
        self.assertTrue(resp_data['customers'])
        self.assertTrue(resp_data['agents'])
        self.assertTrue(resp_data['list'])
        self.assertTrue(resp_data['ok'])

    def _create_conversation(self, session_id):
        client_post = factory_by_user(
            self.user,
            channel = self.inbound,
            content = 'I would like to report a problem with my laptop. And I hate you already.', # need two flags here
            url = 'http://fake.com',
            # _created = parse_datetime( "2007-03-04T21:08:12" ),
            actor_id = str(self.customer_profile.id),
            is_inbound=True,
            extra_fields = {"chat": {"session_id": session_id}}
        )
        self.assertEqual(client_post.get_assignment(self.sc), "highlighted")
        brand_post = factory_by_user(
            self.user,
            channel = self.outbound,
            content = 'Sure, do you have a problem with laptop battery?',
            url = 'http://fake2.com',
            # _created = parse_datetime( "2007-03-04T21:08:12" ),
            actor_id = str(self.agent_profile.id),
            is_inbound=False,
            extra_fields = {"chat": {
                "session_id": session_id,
                "in_reply_to_status_id": client_post.id}}
        )
        self.assertEqual(brand_post.get_assignment(self.sc.outbound_channel), "highlighted")
        client_post.handle_reply(brand_post, [self.sc.inbound_channel])
        client_post.reload()
        self.assertEqual(client_post.get_assignment(self.sc), "replied")
        self.assertEqual(brand_post.parent_post_id, client_post.id)

        conversations = Conversation.objects.lookup_by_posts(self.sc, [client_post])
        return conversations

    def _do_request(self, request_data):
        resp = self.client.get(
            '/api/v2.0/chat/sessions',
            data=json.dumps(request_data),
            content_type='application/json',
            base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.data)
        self.assertTrue(resp_data['ok'])
        self.assertTrue(resp_data['list'])

    def test_get_sessions(self):
        self._create_conversation(session_id='chat_session_id')
        request_data={
            'token': self.token,
            'chat_profile_id': str(self.chat_profile.id),
            'service_channel_id': str(self.sc.id)}
        self._do_request(request_data)

        del request_data['chat_profile_id']
        request_data['customer_profile_id'] = str(self.customer_profile.id)
        self._do_request(request_data)

        del request_data['customer_profile_id']
        request_data['agent_profile_id'] = str(self.agent_profile.id)
        self._do_request(request_data)

    def test_agent_post_first(self):
        token = self.get_token()
        session_id = 'agent_fist_session_id'
        chat_data = dict(session_id=session_id,
                         content="agent message",
                         channels=[str(self.sc.id)],
                         token=token,
                         type='chat',
                         is_inbound=False,
                         actor_id=self.agent_profile.id)
        resp = self.client.post(
            '/api/v2.0/events',
            data=json.dumps(chat_data),
            content_type='application/json',
            base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)

        # the first event belog to untracked agent, lets check that
        events = Event.objects()[:]
        self.assertEqual(len(events), 1)
        event = events[0]
        actor_num = unpack_event_id(event.id)[0]
        self.assertEqual(actor_num, 0)
        self.assertEqual(event.actor.first_name, self.agent_profile.first_name)
        self.assertEqual(event.actor.id, self.agent_profile.id)
        self.assertEqual(event.actor.actor_num, self.agent_profile.actor_num)

        chat_data = dict(session_id=session_id,
                         content="customer message",
                         channels=[str(self.sc.id)],
                         token=token,
                         type='chat',
                         is_inbound=True,
                         actor_id=str(self.customer_profile.id))
        resp = self.client.post(
            '/api/v2.0/events',
            data=json.dumps(chat_data),
            content_type='application/json',
            base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        # after customer event was fired, the first event should
        # has right id with particular customer_profile encoded in id value
        events = Event.objects()[:]
        self.assertEqual(len(events), 2)
        event = events[0]
        self.assertEqual(event.is_inbound, False)

        self.assertEqual(event.actor.first_name, self.agent_profile.first_name)
        self.assertEqual(event.actor.id, self.agent_profile.id)
        self.assertEqual(event.actor.actor_num, self.agent_profile.actor_num)
        actor_num = unpack_event_id(event.id)[0]
        self.assertEqual(self.customer_profile.actor_num, actor_num)


