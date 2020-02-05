class FeedAPIError(Exception):
    "Base class for all FeedAPI exceptions."


class InfrastructureError(FeedAPIError):
    """Raised when pycurl/requests fails
    or HTTP server returns non 200 status."""


class ApplicationError(FeedAPIError):
    """Raised when HTTP server returns 200
    but json output non ok."""


class UnauthorizedRequestError(FeedAPIError):
    """Raised when server returns http status 401"""
