__author__ = 'bogdan'

import ast
import pickle
import math

from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.parsers.base_visitor_node import BaseVisitorNode
from solariat_bottle.utils.parsers.exceptions import ExpressionCompilationError, ExpressionEvaluationError

BASIC_FUNCS = {"log": math.log,
               "pow": math.pow,
               "int": int,
               "str": str}
CUSTOM_OPERATORS = BASIC_FUNCS.copy()


def register_operator(operator_name, operator_function):
    if operator_name in CUSTOM_OPERATORS:
        return ExpressionCompilationError("There is already a custom operator set for name %s. Aborting." % operator_name)
    CUSTOM_OPERATORS[operator_name] = operator_function


class BaseParser(object):

    raw_expression = ""
    compiled_expression = None
    _visitor_class = BaseVisitorNode

    def __init__(self, raw_expression, variable_list=None, _visitor_class=None):
        if _visitor_class:
            # In case we want to overwrite with more specific checks
            self._visitor_class = _visitor_class
        self.raw_expression = raw_expression
        self.variable_list = variable_list or []
        self.compile()

    def compile(self):
        visitor = self._visitor_class(self.variable_list)
        try:
            parsed_tree = ast.parse(self.raw_expression)
        except SyntaxError, ex:
            error_message = "Failed to compile expression <<%s>>. Invalid syntax around sub-expression <<%s>>." % (
                self.raw_expression, ex.text[:ex.offset])
            raise ExpressionCompilationError(error_message)
        except Exception:
            raise ExpressionCompilationError("Expression %s failed to compile. Please double check syntax." %
                                             self.raw_expression)
        visitor.visit(parsed_tree)
        if visitor.ok:
            self.compiled_expression = parsed_tree
        else:
            LOGGER.error("Failed to compile expression. Details: %s" % visitor.error_message)
            raise ExpressionCompilationError("Expression %s failed to compile. Please double check syntax." %
                                             self.raw_expression)

    def _get_nested_attribute(self, node, context_dict):
        sub_keys = []
        value = node
        while isinstance(value, ast.Attribute):
            sub_keys.append(value)
            value = value.value
        key_list = [str(value.id), ] + list(reversed([key.attr for key in sub_keys]))
        full_field = '.'.join(key_list)
        try:
            context = context_dict[value.id]
            for key in reversed(sub_keys):
                if isinstance(context, dict):
                    context = context[key.attr]
                else:
                    context = getattr(context, key.attr)
            return context
        except KeyError:
            raise ExpressionEvaluationError("%s was not found in context %s" % (full_field, context_dict))

    def _convert(self, node, context_dict):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.List) or isinstance(node, ast.Tuple):
            return [self._convert(val, context_dict) for val in node.elts]
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Attribute):
            # context[node.value.id][node.attr]
            return self._get_nested_attribute(node, context_dict)
        elif isinstance(node, ast.Name):
            if node.id in context_dict:
                return context_dict[node.id]
            else:
                LOGGER.error("Missing parameter %s from context dict %s" % (node.id, context_dict))
                raise ExpressionEvaluationError("Missing parameter %s from expression context." % node.id)
        elif isinstance(node, ast.Dict):
            result = dict()
            for key_idx, key_val in enumerate(node.keys):
                result[self._convert(key_val, context_dict)] = self._convert(node.values[key_idx], context_dict)
            return result
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return - self._convert(node.operand, context_dict)
            else:
                return self._convert(node.operand, context_dict)
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all([self._convert(val, context_dict) for val in node.values])
            if isinstance(node.op, ast.Or):
                return any([self._convert(val, context_dict) for val in node.values])
        elif isinstance(node, ast.Call):
            op_id = node.func.id
            if op_id not in CUSTOM_OPERATORS:
                raise ExpressionCompilationError("Unknown operator %s, only supported ones are %s" % (
                    op_id, CUSTOM_OPERATORS.keys()))
            return CUSTOM_OPERATORS[op_id](*[self.__convert(param, context_dict) for param in node.args])
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult,
                                                                  ast.Div, ast.Mod, ast.Pow)):
            left = self._convert(node.left, context_dict)
            right = self._convert(node.right, context_dict)
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                return left / right
            elif isinstance(node.op, ast.Mod):
                return left % right
            elif isinstance(node.op, ast.LtE):
                return left <= right
            else:
                return left ** right
        elif isinstance(node, ast.Compare):
            left = self._convert(node.left, context_dict)
            # TODO: This only allows 1 comparator, so no x < y < z, needs to be extended for that
            right = self._convert(node.comparators[0], context_dict)
            if isinstance(node.ops[0], ast.Gt):
                return left > right
            if isinstance(node.ops[0], ast.GtE):
                return left >= right
            if isinstance(node.ops[0], ast.Lt):
                return left < right
            if isinstance(node.ops[0], ast.LtE):
                return left <= right
            if isinstance(node.ops[0], ast.Not):
                return not right
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.In):
                return left in right

    def evaluate(self, context_dict):
        """ Evaluate a parse tree.

        This function is motivated by the ast.literal_eval() method and in part a copy of it.
        The function takes a parse tree as prepared by ast.parse() and returns the evaluation
        with respect to the context_dict dictionary, i.e., a call might look like this:

        compiled_expression = ast.parse("2+x")
        evaluate(compiled_expression, { "x": 5 })
        -> 10

        The parse tree once created, can be evaluated multiple time with different dictionaries.
        As a goodie are also vectors allowed for the context_dict, i.e., using NumPy one can do:

        v= numpy.array([2,3,4])
        evaluate(compiled_expression, { "x": v })
        -> array([2, 5, 6])
        """
        return self._convert(self.compiled_expression.body[0].value, context_dict)

    def to_pickle(self):
        return pickle.dumps(self)

    @staticmethod
    def from_pickle(string_pkl):
        return pickle.loads(string_pkl)
