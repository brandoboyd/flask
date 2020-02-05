from solariat_bottle.db.predictors.base_predictor import LinUCBPredictorModel
from solariat_bottle.db.predictors.models.linucb import ModelState
from solariat_bottle.tests.base import BaseCase
from solariat_bottle.db.predictors.factory import create_agent_matching_predictor, get_agent_matching_predictor
from solariat_bottle.db.agent_matching import create_customer, create_agent
from solariat_nlp.bandit.models import AGENT_MATCHING_CONFIGURATION

from solariat_bottle.tests.advisors import setup_customer_schema, setup_agent_schema

class AgentMatchingPredictorTest(BaseCase):

    def setUp(self):
        super(AgentMatchingPredictorTest, self).setUp()
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

        self.agent_data = dict(
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
        self.agent = create_agent(**self.agent_data)
        self.agent_data['action_id'] = str(self.agent.id)

    def test_basic_feedback(self):
        advisor = create_agent_matching_predictor(self.user.account.id, is_test=True)
        advisor.feedback(self.customer_data, self.agent_data, reward=.9)

    import unittest
    @unittest.skip("Deprecated")
    def test_multi_models(self):
        def feat(features):
            return [f.name for f in features.features()]

        def assert_models_count(cnt=1):
            assert len(advisor.models_data) == cnt
            assert len(LinUCBPredictorModel.objects()) == cnt

        def assert_model_data(model, model_data, context_features, action_features, weight=1.0):
            self.assertEqual(model_data.model_id, model.id)
            self.assertEqual(model_data.weight, weight)
            self.assertEqual(model_data.display_name, model.display_name)
            # default model should have all possible features enabled
            self.assertEqual(model.context_features, context_features)
            self.assertEqual(model.action_features, action_features)
            self.assertEqual(model.weight, weight)

        try:
            advisor = get_agent_matching_predictor(self.user.account)
        except:
            advisor = create_agent_matching_predictor(self.user.account.id, is_test=True)

        # force 'active' state for select_model() to work
        for model in advisor.models:
            model.update(state=ModelState(status=ModelState.STATUS_ACTIVE, state=ModelState.CYCLE_LOCKED))

        assert_models_count(cnt=1)
        model_data = advisor.models_data[0]
        model = LinUCBPredictorModel.objects.get()
        assert_model_data(model, model_data, model.context_features, model.action_features)

        # adding new model
        w = 10.0
        new_model_data = {
            "action_features": [model.action_features[0]],
            "context_features": [model.context_features[0]],
            "weight": w
        }
        advisor.add_model(new_model_data)
        for model in advisor.models:
            model.update(state=ModelState(status=ModelState.STATUS_ACTIVE, state=ModelState.CYCLE_LOCKED))
        advisor.reload()

        assert_models_count(cnt=2)
        model_data = advisor.models_data[1]
        model = LinUCBPredictorModel.objects.get(id=model_data.model_id)
        assert_model_data(model, model_data, new_model_data['context_features'],
                          new_model_data['action_features'], weight=w)

        # check selection algorithm
        from collections import Counter
        n = 100
        most_common = Counter(advisor.select_model() for x in range(n)).most_common()
        self.assertEqual(most_common[0][0], model)
        if len(most_common) == 2:
            self.assertTrue(round(1.0 * most_common[0][1] / most_common[1][1]) >= w / 2, msg=most_common)
