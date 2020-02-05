import os
from flask import request

from solariat_bottle.settings import get_var
from solariat_bottle.api.base import ModelAPIView
from solariat_bottle.api.exceptions import AppException, InvalidParameterConfiguration, AuthorizationError
from solariat_bottle.db.user import User
from solariat_bottle.db.api_auth import AuthToken, ApplicationToken
from solariat_bottle.utils.request import _get_request_data


class AuthTokenAPIView(ModelAPIView):
    model = AuthToken
    endpoint = 'authenticate'

    def post(self, *args, **kwargs):
        """
        Create a user token entity. Returns a token object in case authentication is successful

        Sample request:
            curl http://staging.socialoptimizr.com/api/v2.0/authenticate

            POST Parameters:
                :param api_key: <Required> - A valid api key
                :param username: <Required> - The username of the GSA user
                :param password: <Required> - The password of the GSA user

        Output:
            A dictionary in the form {'ok': true, 'token': <auth token>}

        Sample valid response
            {
              "token": "dc879e52b70b16c3935b8db99f666fdf8eebaa05",
              "ok": true
            }

        Missing app_key parameter:
            {
              "code": 13,
              "error": "An extra parameter 'api_key' is required for users in order to get a user token."
            }

        Wrong user email
            {
              "code": 13,
              "error": "User with given email or username does not exist"
            }

        Wrong user password
            {
              "code": 13,
              "error": "Provided password wrong is not a match for user test_api@test.com"
            }

        """
        required_post_params = ['username', 'password']
        params = _get_request_data()
        for req_param in required_post_params:
            if req_param not in params:
                exc = InvalidParameterConfiguration
                return self.format_api_error_response(exc, msg="Required parameter missing: {}".format(req_param))
        try:
            if get_var('ENFORCE_API_HTTPS') and not request.url.startswith('https://'):
                # Unsercure request, invalidate token
                # This is not recoverable by user alone, so remove for now until we have a better way
                # where we offer user possibility to recover by some other means
                # try:
                #     user = User.objects.get(email=params['username'])
                #     user.set_password(os.urandom(10).encode('base64')[:-3])
                #     user.save()
                # except User.DoesNotExist:
                #     raise AuthorizationError("No user with email=%s found in the system." % params['username'])
                # if not user.is_superuser:
                #     app_key = ApplicationToken.objects.verify_application_key(params['api_key'])
                #     app_key.invalidate()
                description = "You have made an unsecured request over HTTP. Please use HTTPS for any subsequent calls."
                description += " Your current api token has automatically been invalidated and your password reset. "
                description += "Please contact GSA administrator to get fresh credentials."
                raise AuthorizationError(msg="Unsecure request done over HTTP. Your credentials have been invalidated.",
                                         description=description)

            token = self.model.objects.create(**params)
        except AppException, exc:
            return self.format_api_error_response(exc, msg=str(exc), description=exc.description)
        return self.format_api_response(**dict(token=token.digest))
