import ast
import json

from solariat_bottle.settings         import LOGGER
from solariat_bottle.api.base         import BaseAPIView, api_request
from ..db.conversation                import Conversation, SessionBasedConversation
from ..db.channel.chat  import ChatServiceChannel as CSC
from solariat_bottle.db.user_profiles.chat_profile import ChatProfile
#from solariat_bottle.db.events.predictor import CSMPredictor


class ChatAPIView(BaseAPIView):

    endpoint = 'chat'
    commands = ['summary', 'sessions', 'join_conversation']

    @classmethod
    def register(cls, app):
        """ Chat API allows for extra commands, like 'summary' and 'session' """
        view_func = cls.as_view(cls.endpoint)

        url = cls.get_api_url('<command>')
        app.add_url_rule(url, view_func=view_func, methods=["GET", "POST", "PUT", "DELETE"])

    def get(self, command=None, *args, **kwargs):
        """ Allowed commands are routed to the _<command> method on this class """
        if command in self.commands:
            meth = getattr(self, '_' + command)
            return meth(*args, **kwargs)
        return super(ChatAPIView, self).post(*args, **kwargs)

    def post(self, command=None, *args, **kwargs):
        """ Allowed commands are routed to the _<command> method on this class """
        if command in self.commands:
            meth = getattr(self, '_' + command)
            return meth(*args, **kwargs)
        return super(ChatAPIView, self).post(*args, **kwargs)

    @api_request
    def _join_conversation(self, user, *args, **kwargs):
        assert kwargs.get('session_id') and kwargs.get('agent_id'), 'Both "session_id" and "agent_id" required'
        conversation = SessionBasedConversation.objects.get(session_id=kwargs['session_id'])
        conversation.actors.append(kwargs.get('agent_id'))
        conversation.save(is_safe=True)
        return dict(ok=True)

    @api_request
    def _summary(self, user, *args, **kwargs):
        assert kwargs.get('conversation_id') or (kwargs.get('agents_ids') and kwargs.get('channel_id')), \
            'Either "conversation_id" or "agents_ids" and "channel_id" are required'
        if 'conversation_id' in kwargs:
            conversation = Conversation.objects.get(long(kwargs.get('conversation_id')))
            return conversation.get_summary()
        else:
            agent_ids = kwargs['agents_ids']
            if isinstance(agent_ids, str) or isinstance(agent_ids, unicode):
                try:
                    agent_ids = json.loads(agent_ids)
                except:
                    agent_ids = ast.literal_eval(agent_ids)

            service_channel = CSC.objects.get(kwargs.get('channel_id'))
            agent_profile_schema = service_channel.account.agent_profile._get()
            AgentProfile = agent_profile_schema.get_data_class()

            agents = AgentProfile.objects(id__in=agent_ids)[:]
            if not agents:
                return dict(ok=False, error="No agent found with ids=%s" % kwargs['agents_ids'])
            all_summaries = []
            for agent in agents:
                contacts = [agent.id]
                conversations = SessionBasedConversation.objects(channel=str(service_channel.id),
                                                                 actors__in=contacts,
                                                                 is_closed=False).sort(last_modified=1)
                agent_summaries = []
                for conversation in conversations:
                    agent_summaries.append(conversation.get_summary())
                all_summaries.append({str(agent.id): agent_summaries})
        return dict(ok=True, list=all_summaries)

    @api_request
    def _sessions(self, user, *args, **kwargs):
        assert (kwargs.get('chat_profile_id') 
            or kwargs.get('customer_profile_id')
            or kwargs.get('agent_profile_id')
            ), "either chat_profile_id or customer_profile_id or agent_profile_id should be provided"
        assert kwargs.get('service_channel_id'), kwargs.get('service_channel_id')
        service_channel = CSC.objects.get(kwargs.get('service_channel_id'))

        CustomerProfile = service_channel.account.get_customer_profile_class()
        AgentProfile = service_channel.account.get_agent_profile_class()

        if kwargs.get('chat_profile_id'):
            chat_profile = ChatProfile.objects.get(kwargs.get('chat_profile_id'))
            try:
                customer_profile = CustomerProfile.objects.get(
                    account_id=service_channel.account.id,
                    linked_profile_ids__in=[str(chat_profile.id)])
            except CustomerProfile.DoesNotExist:
                contacts = [chat_profile.id]
            else:
                contacts = [customer_profile.id]
        elif kwargs.get('customer_profile_id'):
            customer_profile = CustomerProfile.objects.get(kwargs.get('customer_profile_id'))
            # chat_profile = ChatProfile.objects.get(_customer_profile=str(customer_profile.id))
            # contacts = [chat_profile.customer_profile.id]
            contacts = [customer_profile.id]
        elif kwargs.get('agent_profile_id'):
            agent_profile = AgentProfile.objects.get(kwargs.get('agent_profile_id'))
            contacts = [agent_profile.id]
        else:
            raise Exception('Unexpeted combination of params')
        assert contacts

        conversations = SessionBasedConversation.objects(
            channel=str(service_channel.id),
            actors__in=contacts,
            is_closed=False).sort(last_modified=1)
        results = []
        for conversation in conversations:
            base_dict = conversation.get_summary()
            results.append(base_dict)
        return {'list': results}




