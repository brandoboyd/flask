from solariat_bottle.db.next_best_action.actions import Action
from solariat_bottle.tests.base import BaseCase
from solariat_bottle.db.events.event import Event
from solariat_bottle.db.predictors.factory import create_chat_engagement_predictor, create_supervisor_alert_predictor
from solariat_bottle.db.agent_matching import create_customer, create_agent

from solariat_bottle.tests.advisors import setup_customer_schema, setup_agent_schema

class NBACase(BaseCase):
    def setUp(self):
        super(NBACase, self).setUp()
        setup_customer_schema(self.user)
        setup_agent_schema(self.user)
        
        self.customer_data = dict(
                first_name = 'Sujan',
                last_name = 'Shakya',
                age = 30,
                account_id = str(self.account.id),
                location = 'Nepal',
                sex = 'M',
                account_balance = 1000,
                last_call_intent = ['buy a house'],
                num_calls = 10,
                seniority = 'mediocre',
        )
        self.customer = create_customer(**self.customer_data)

        agent_data = dict(
                first_name = 'Dipa',
                last_name = 'Shakya',
                age = 29,
                location = 'Banepa',
                sex = 'F',
                account_id = str(self.account.id),
                skillset = {
                    'ethics': .9,
                    'temper': .5,
                    'memory': .5,
                },
                occupancy = .9,
                products = ['sell a house'],
                english_fluency = 'advanced',
                seniority = 'expert',
        )
        self.agent = create_agent(**agent_data)
        self.action = Action.objects.create(
            account_id=self.account.id,
            name="Got a question? Chat Now!",
            tags=[],
            channels=[])
        self.event = Event(
            actor_id=self.customer.id,
            is_inbound=True,
            assigned_tags=[],
            _native_id='1')
        self.event.save()


class ChatEngagementDecisionTest(NBACase):

    def test_basic_feedback(self):
        advisor = create_chat_engagement_predictor(self.user.account.id)
        advisor.feedback(self.customer_data, dict(action_id=self.action.id), reward=.9)
        model = advisor.select_model()
        advisor.feedback(self.customer_data, dict(action_id=self.action.id), reward=.9, model=model)


class AlertSupervisorDecisionTest(NBACase):

    def test_basic_feedback(self):
        advisor = create_supervisor_alert_predictor(self.user.account.id)
        advisor.feedback(self.customer_data, dict(action_id=self.action.id), reward=.9)
        model = advisor.select_model()
        advisor.feedback(self.customer_data, dict(action_id=self.action.id), reward=.9, model=model)



