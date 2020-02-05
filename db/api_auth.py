"""
Container for any token/managers related to authentication through the API.
"""
from bson.objectid import ObjectId
from datetime import datetime, timedelta

from solariat.db import fields
from solariat.db.abstract import Manager, Document
from solariat_bottle.db.user import User, get_random_digest, set_user
from solariat_bottle.settings import get_var, AppException, LOGGER
from solariat_bottle.db.auth import AuthError


class AuthTokenManager(Manager):
    """ Provide special create method with truly random digest
    """
    @staticmethod
    def _get_user_obj(**kw):
        """
        Given a set of accepted parameters, get the user object based on a number of possible fields.

        :param kw: A dictionary which should contain one of the following keys: user, email, username, user_id
        :return: A user object that matches one of the keys passed in
        """

        for k, v in kw.iteritems():
            if (k!="password"):
                LOGGER.info("New SMS connection with user params: %s : %s ." % (k,v))

        if 'user' in kw:
            return kw['user']
        elif 'email' in kw:
            return User.objects.get(email=kw['email'])
        elif 'username' in kw:
            return User.objects.get(email=kw['username'])
        elif 'user_id' in kw:
            return User.objects.get(id=kw['user_id'])
        else:
            raise AppException("user, email or user_id should be provided")

    def create(self, **kw):
        """Create AuthToken with password check.
        Delete any existed AuthTokens for this user.
        """
        skip_app_check = kw.pop('skip_app_check', False)
        try:
            user = self._get_user_obj(**kw)
        except User.DoesNotExist:
            raise AuthError("User with given email or username does not exist")
        password = kw.get('password')
        if not password:
            raise AuthError("No password was provided for access token generation.")
        if not user.check_password(password):
            raise AuthError("Provided password %s is not a match for user %s" % (password, user.email))
        api_key = None
        if skip_app_check is False and not user.is_superuser:
            api_key = kw.get('api_key')
            if not api_key:
                raise AuthError("An extra parameter 'api_key' is required for users in order to get a user token.")
            api_key = ApplicationToken.objects.verify_application_key(api_key).id
        return self.create_from_user(user=user, api_key=api_key)

    def create_for_restore(self, **kw):
        """Create AuthToken for password restore form
        Please, note, We don't check password here!
        """
        user = self._get_user_obj(**kw)
        return self.create_from_user(user)

    def _delete_expired(self):
        # Clear out any expired tokens from the database
        threshold = datetime.utcnow() - timedelta(seconds=get_var('TOKEN_VALID_PERIOD')*60*60)
        threshold_id = ObjectId.from_datetime(threshold)
        self.remove(id={'$lt':threshold_id})

    def create_from_user(self, user, api_key=None):
        """ Skips password. Assumes if we have the user object we
        are all set. Delete any expired tokens """
        self._delete_expired()
        return Manager.create(self,
                              digest=get_random_digest(),
                              user=user,
                              app_key=api_key)

    def get_user(self, digest):
        """ Get user by given digest (token)
        Check if existed AuthToken is still valid.
        Delete if not.
        """
        try:
            token = Manager.get(self, digest=digest)
        except AuthToken.DoesNotExist:
            return None
        if not token.is_valid:
            token.delete()
            return None
        return token.user


class AuthToken(Document):
    """ Temporary key for user authentication """

    manager = AuthTokenManager
    collection = 'authtoken'

    VALID_PERIOD = get_var('TOKEN_VALID_PERIOD', 24) # hours

    user = fields.ReferenceField(User)
    digest = fields.StringField(unique=True)
    app_key = fields.ObjectIdField(required=False)

    @property
    def is_valid(self):
        # return True if the token is not expired
        deadline = datetime.utcnow() - timedelta(hours=self.VALID_PERIOD)
        return deadline < self.created

    def to_dict(self):
        # Return dict for HTTP API
        return {'token': self.digest}


class ApplicationTokenManager(Manager):

    def _ensure_application_token(self, app_token):
        """
        Make sure we get an actual ApplicationToken object from the parameter passed in.

        :param app_token: Can be either an ApplicationToken object, a string or an ObjectId
        :return: An ApplicationToken object if it could be inferred, None otherwise
        """
        if isinstance(app_token, ApplicationToken):
            return app_token
        if isinstance(app_token, ObjectId) or type(app_token) in (str, unicode):
            return self.get(app_token)
        return None

    def create(self, **kw):
        if 'app_key' not in kw:
            kw['app_key'] = get_random_digest()
        return super(ApplicationTokenManager, self).create(**kw)

    def request_by_user(self, user, app_type):
        """
        Create a new request for an application on GSA. This will need to be approved by a superuser
        before it gets validated.

        :param user: The user who is requesting an application
        :param app_type: The type of application that is requested. It can be <basic, account, corporate>
        :return: A new ApplicationToken object left in the 'requested' state
        """
        token = self.create(creator=user,
                            status=ApplicationToken.STATUS_REQUESTED,
                            type=app_type)
        return token

    def create_by_user(self, user, creator, app_type):
        """
        Create a new valid application token by GSA. This call must be done by a superuser and receives
        as parameter a 'creator' argument which is the user for which we create the application.

        :param user: The user with superuser privileges who created the new application token
        :param creator: The user for which the application will be created
        :param app_type: The type of application that is created. It can be <basic, account, corporate>
        :return: A new ApplicationToken object left in the 'valid' state
        """
        if not user.is_superuser:
            raise AuthError("Only superusers are allowed to create new application tokens."
                            "User %s does not have permissions." % user.email)
        token = self.create(creator=creator,
                            status=ApplicationToken.STATUS_VALID,
                            type=app_type)
        return token

    def verify_application_key(self, app_key):
        """
        For an input application key, validate that we have a valid application token in place.

        :param app_key: A string representing an application key
        :return: An `ApplicationToken` object is a valid one exists for this key, None otherwise
        """
        try:
            app_token = self.get(app_key=app_key)
            if app_token.status != ApplicationToken.STATUS_VALID:
                LOGGER.warning("App key %s is  no longer valid" % app_key)
                raise AuthError("App key %s is no longer valid" % app_key)
            return app_token
        except ApplicationToken.DoesNotExist:
            LOGGER.warning("Trying to use invalid api key %s" % app_key)
            raise AuthError("Trying to use invalid api key %s" % app_key)

    def validate_app_request(self, user, app_token):
        """
        Validate a previously created application request.

        :param user: The user who is doing the app validation
        :param app_token: The application who is validated
        :return: The same app passed in with a valid state
        """
        if not user.is_superuser:
            raise AuthError("Only superusers are allowed to validate application tokens."
                            "User %s does not have permissions." % user.email)
        app_token = self._ensure_application_token(app_token)
        app_token.validate()
        return app_token


class ApplicationToken(Document):
    """ Non-expiring key which is tied in to a user which was granted an application """
    STATUS_REQUESTED = 'requested'      # State a token will be from the moment it was requested by a user
                                        # to the moment the request was accepted by a superuser
    STATUS_VALID = 'valid'              # State a token will be since it was created/accepted by a superuser
                                        # until the moment it's specifically invalidated
    STATUS_INVALID = 'invalid'          # State once token has been revoked by a superuser

    TYPE_BASIC = 'basic'                # Cannot create account/users, only basic access (nlp endpoints)
    TYPE_ACCOUNT = 'account'            # Can create one account, has admin level access on that account
    TYPE_CORPORATE = 'corporate'        # an create multiple accounts, has staff level access across them

    manager = ApplicationTokenManager

    creator = fields.ReferenceField(User)
    status = fields.StringField(choices=[STATUS_INVALID, STATUS_VALID, STATUS_REQUESTED])
    type = fields.StringField(choices=[TYPE_BASIC, TYPE_CORPORATE, TYPE_ACCOUNT])
    app_key = fields.StringField()

    def validate(self):
        self.status = self.STATUS_VALID
        self.save()

    def invalidate(self):
        self.status = self.STATUS_INVALID
        self.save()

