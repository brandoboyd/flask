__author__ = 'bogdan'


from solariat.exc.base import AppException


class ParsingException(AppException):
    pass


class ExpressionCompilationError(ParsingException):
    pass


class ExpressionEvaluationError(ParsingException):
    pass


