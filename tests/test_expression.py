import datetime
import mock
from solariat.utils.timeslot import parse_date_interval
from solariat_bottle.tests.base import MainCase
from solariat_bottle.db.predictors.base_predictor import BasePredictor
from solariat_bottle.db.predictors.entities_registry import EntitiesRegistry
from solariat_bottle.db.account import Account
from solariat.utils.parsers.base_parser import BaseParser


class PredictorExpression(MainCase):
    def setUp(self):
        MainCase.setUp(self)
        self.account = Account(name="Solariat Test")
        self.account.save()
        self.user.account = self.account
        self.user.save()
        self.account.add_perm(self.user)

    def test_upsert_feedback(self):
        predictor = mock.create_autospec(BasePredictor)
        predictor.name = "Social Media Predictor"

        entities_registry = EntitiesRegistry()

        try:
            predictor.upsert_feedback()
        except:
            self.assertTrue(False)

        # mockup upsert_feedback method
        expression = 'collect(InfomartEvent)'
        expression_data = entities_registry.generate_expression_context(predictor, expression)
        self.assertEqual(expression_data['expression'], u'collect(predictor, from_dt, to_dt, InfomartEvent)')

        _from_dt = datetime.datetime.fromtimestamp(int(1466964000)).strftime('%m/%d/%Y')
        _to_dt = datetime.datetime.fromtimestamp(int(1467050400)).strftime('%m/%d/%Y')
        expression_data['context']['from_dt'], expression_data['context']['to_dt'] = parse_date_interval(_from_dt, _to_dt)
        parser = BaseParser(expression_data['expression'], entities_registry.get_all_entries())
        parser.evaluate(expression_data['context'])

        expression = 'int(123.3333)'
        expression_data = entities_registry.generate_expression_context(predictor, expression)
        self.assertEqual(expression_data['expression'], u'int(123.3333)')
        parser = BaseParser(expression_data['expression'], entities_registry.get_all_entries())
        result = parser.evaluate(expression_data['context'])
        self.assertEqual(result, 123)

        expression = 'str(10)'
        expression_data = entities_registry.generate_expression_context(predictor, expression)
        parser = BaseParser(expression_data['expression'], entities_registry.get_all_entries())
        result = parser.evaluate(expression_data['context'])
        self.assertTrue(isinstance(result, basestring))
        # cant do union until we know COLUMN keys to union
