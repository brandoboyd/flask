from solariat_bottle.settings import AppException


class FacebookConfigurationException(AppException):

    code = 364
    http_code = 400

    def __init__(self, msg, e=None, description=None, http_code=None):
        super(FacebookConfigurationException, self).__init__(msg, e, description, http_code)


class FacebookCommunicationException(AppException):

    code = 363
    http_code = 432

    def __init__(self, msg, e=None, description=None, http_code=None):
        super(FacebookCommunicationException, self).__init__(msg, e, description, http_code)


class TwitterCommunicationException(AppException):
    # Default error code. We can use various for different purposes.
    # For now the use case I have in mind is refreshing a page if
    # error occures.
    twitter_error_code = -1
    http_code = 432
    REFRESH_UI = 1
    KEEP_AS_DM = 2

    def __init__(self, msg, e=None, description=None, http_code=None, error_code=-1, *args, **kwargs):
        super(TwitterCommunicationException, self).__init__(msg,
                                                            e=e,
                                                            description=description,
                                                            http_code=http_code,
                                                            *args,
                                                            **kwargs)
        self.twitter_error_code = error_code

    def to_dict(self):
        base_dict = super(TwitterCommunicationException, self).to_dict()
        if self.twitter_error_code > 0:
            base_dict['twitter_error_code'] = self.twitter_error_code
        return base_dict


class DirectMessageUnpermitted(TwitterCommunicationException):

    def __init__(self, msg, e=None, description=None, http_code=None, error_code=-1, internal_code=-1, *args, **kwargs):
        super(DirectMessageUnpermitted, self).__init__(msg,
                                                            e=e,
                                                            description=description,
                                                            http_code=http_code,
                                                            error_code=error_code,
                                                            *args,
                                                            **kwargs)
        self.internal_code = internal_code  # User for internal specific handling (e.g. keep response as DM or not)
