import re
import uuid

from solariat.exc.base import AppException
from solariat_bottle.settings import LOGGER

OPERATOR_EQUIVALENTS = {'=': None,
                        '>=': '$gte',
                        '>': '$gt',
                        '<': '$lt',
                        '<=': '$lte'}
OPERATORS = sorted(OPERATOR_EQUIVALENTS.keys(), key=lambda x: -len(x))

OR_OPERATOR = '|'
AND_OPERATOR = '&'
EXPRESSION_START = '('
EXPRESSION_END = ')'


class BaseParseException(AppException):
    pass


class FilterTranslator(object):

    parsed_expressions = dict()

    def __init__(self, filter_string, prefix=None, context=[]):
        self.prefix = prefix
        # self.filter_string = re.sub('[\s+]', '', filter_string)
        self.filter_string = filter_string
        self.validate_expression()
        self.context = context
        self.context_lower = [key.lower() for key in context]

    @staticmethod
    def parse_value(value_str):
        # TODO: just in case we want to extend to accept different types of values
        try:
            return float(value_str)
        except ValueError:
            return value_str

    def parse_node(self, node):
        node = node.strip()
        operator = None
        for candidate in OPERATORS:
            if candidate in node:
                operator = candidate
                break
        if operator is None:
            raise BaseParseException("No valid operator found in node %s from filter %s. Valid operators are %s" %
                                     (node, self.filter_string, OPERATORS))

        left_operand, right_operand = node.split(operator)
        if left_operand.lower() in self.context_lower:
            left_operand = self.context[self.context_lower.index(left_operand.lower())]
        if self.prefix:
            left_operand = '%s.%s' % (self.prefix, left_operand)
        # TODO: Assumption for now is that left side is always field, right side is always value
        # If this doesn't apply, need to check and reverse the operands
        mongo_operator = OPERATOR_EQUIVALENTS[operator]
        if mongo_operator:
            return {left_operand: {mongo_operator: self.parse_value(right_operand)}}
        else:
            return {left_operand: self.parse_value(right_operand)}

    def parse_simple_expression(self, expression):
        if expression.strip() in self.parsed_expressions:
            # We parsed it before while traversing structure,
            parsed_expression = self.parsed_expressions.pop(expression.strip())
            return parsed_expression
        
        if OR_OPERATOR in expression:
            # One chain of smaller expressions grouped in an OR
            return {'$or': [self.parse_simple_expression(sub_expr) for sub_expr in expression.split(OR_OPERATOR)]}

        if AND_OPERATOR in expression:
            return {'$and': [self.parse_simple_expression(sub_expr) for sub_expr in expression.split(AND_OPERATOR)]}

        return self.parse_node(expression)

    def parse_expression(self, expression):
        if EXPRESSION_START not in expression:
            # We're down to simple expressions, no more groups by ()
            if EXPRESSION_END in expression:
                raise BaseParseException("Invalid expression %s found in filter %s" % (expression, self.filter_string))
            return self.parse_simple_expression(expression)
        else:
            if EXPRESSION_END not in expression:
                raise BaseParseException("Invalid expression %s found in filter %s" % (expression, self.filter_string))
            stack = []
            # We have an expression that has () groups, need to recursively recompute it
            for idx, char_value in enumerate(expression):
                if char_value == EXPRESSION_START:
                    stack.append(idx)
                if char_value == EXPRESSION_END:
                    start_idx = stack.pop()
                    parsed_expression = self.parse_simple_expression(expression[start_idx + 1:idx])
                    expression_id = str(uuid.uuid4()).replace('-', '')
                    self.parsed_expressions[expression_id] = parsed_expression
                    new_expression = expression[:start_idx] + expression_id + expression[idx + 1:]
                    return self.parse_expression(new_expression)

    def validate_expression(self):
        stack = []
        for char in self.filter_string:
            if char == EXPRESSION_START:
                stack.append(char)
            if char == EXPRESSION_END:
                stack.pop()
        assert len(stack) == 0

    def get_mongo_query(self):
        return self.parse_expression(self.filter_string)