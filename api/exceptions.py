"""Discussion at
https://docs.google.com/a/solariat.com/document/d/1HDBTgIOusUXRXPRCWNUiAnSct652f7d0Ua0EJphwCaI/edit
"""
from solariat_bottle.settings import AppException


class BaseAPIException(AppException):

    code = 0
    http_code = 500

    def __init__(self, msg, e=None, description=None, http_code=None):
        super(BaseAPIException, self).__init__(msg, e, description, http_code)


class AuthorizationError(BaseAPIException):

    code = 12
    http_code = 401

    def __init__(self, msg, e=None, description=None, http_code=None):
        super(AuthorizationError, self).__init__(msg, e, description, http_code)


class ValidationError(BaseAPIException):
    code = 35
    http_code = 400

    def __init__(self, msg, e=None, description=None, http_code=None):
        super(ValidationError, self).__init__(msg, e, description, http_code)


class InvalidParameterConfiguration(BaseAPIException):

    code = 113
    http_code = 400

    def __init__(self, msg, e=None, description=None, http_code=None):
        super(InvalidParameterConfiguration, self).__init__(msg, e, description, http_code)


class DocumentDeletionError(BaseAPIException):

    code = 114
    http_code = 400

    def __init__(self, msg, e=None, description=None, http_code=None):
        super(DocumentDeletionError, self).__init__(msg, e, description, http_code)


class ResourceDoesNotExist(BaseAPIException):

    code = 34
    http_code = 404

    def __init__(self, msg, e=None, description=None, http_code=None):
        super(ResourceDoesNotExist, self).__init__(msg, e, description, http_code)


class ForbiddenOperation(BaseAPIException):

    code = 134
    http_code = 403

    def __init__(self, msg, e=None, description=None, http_code=None):
        super(ForbiddenOperation, self).__init__(msg, e, description, http_code)


class MethodNotAllowed(BaseAPIException):

    code = 135
    http_code = 405
