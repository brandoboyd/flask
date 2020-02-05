from solariat_bottle.tests.base import BaseCase

from solariat.utils.parsers.base_parser import BaseParser, ExpressionCompilationError, ExpressionEvaluationError


class BaseParserTestCase(BaseCase):

    def test_base_parser_expression(self):
        parser = BaseParser("RevenueActivity*NetDelta*0.2 + Resolution")
        self.assertEqual(705.9, parser.evaluate({"RevenueActivity": 31.5,
                                                 "NetDelta": 112,
                                                 "Resolution": 0.3}))

        self.assertEqual(10.5, parser.evaluate({"RevenueActivity": 0.5,
                                                "NetDelta": 100,
                                                "Resolution": 0.5}))

        parser = BaseParser("Pred1 - 0.5 * Pred2 + Pred3 * Pred1")
        self.assertEqual(0.45, parser.evaluate(({"Pred1": 0.5,
                                                 "Pred2": 0.2,
                                                 "Pred3": 0.1,
                                                 "Pred4": 1})))

        parser = BaseParser("(Pred1 + Pred2) * 2 - Pred3")
        self.assertEqual(1.2, parser.evaluate(({"Pred1": 0.5,
                                                "Pred2": 0.2,
                                                "Pred3": 0.2})))

    def test_parser_math_operations(self):
        parser = BaseParser("log(x)")
        self.assertEqual(1, parser.evaluate({"x": 2.718281828459045}))

        parser = BaseParser("pow(x, y)")
        self.assertEqual(9, parser.evaluate({"x": 3, "y": 2}))

    def test_base_parser_expression_with_context(self):
        # Expression is in line with context, all is fine
        parser = BaseParser("RevenueActivity*NetDelta*0.2 + Resolution",
                            ["RevenueActivity", "NetDelta", "Resolution"])
        self.assertEqual(10.87, parser.evaluate({"RevenueActivity": 0.5,
                                                 "NetDelta": 100,
                                                 "Resolution": 0.87}))
        # Missing value from context, expect evaluation error
        try:
            parser.evaluate({"RevenueActivity": 0.5,
                             "NettDelta": 100,
                             "Resolution": 0.89})
            self.fail("Expected evaluation to fail because of missing parameter NetDelta <<misstyped to NettDelta>>")
        except ExpressionEvaluationError, ex:
            self.assertTrue("Missing parameter" in str(ex))
        # Expression has parameter outside context, expect compilation error
        try:
            parser = BaseParser("RevenueActivity*NetDelta*0.2 + Resolution",
                                ["RevenueActivity", "NetDelta2", "Resolution"])
            self.fail("Expected compilation to fail because of wrong parameter NetDelta != NetDelta2")
        except ExpressionCompilationError, ex:
            self.assertTrue("Failed to compile expression. Details:" in str(ex))

    def test_base_parser_invalid_expressions(self):
        try:
            BaseParser("expr1 c + 5 - 1")  # Misstype, missing an operator
            self.fail("Expected compilation to fail because of misstype <<expr1 c>>")
        except ExpressionCompilationError, ex:
            self.assertTrue("Invalid syntax around sub-expression" in str(ex))

        try:
            BaseParser("expr1 - c ) + 2")
        except ExpressionCompilationError, ex:
            self.assertTrue("Invalid syntax around sub-expression" in str(ex))

    def test_pickle_save_load(self):
        parser = BaseParser("RevenueActivity*NetDelta*0.2 + Resolution")
        self.assertEqual(705.9, parser.evaluate({"RevenueActivity": 31.5,
                                                 "NetDelta": 112,
                                                 "Resolution": 0.3}))

        pickle_repr = parser.to_pickle()
        parser2 = BaseParser.from_pickle(pickle_repr)
        self.assertEqual(705.9, parser2.evaluate({"RevenueActivity": 31.5,
                                                  "NetDelta": 112,
                                                  "Resolution": 0.3}))