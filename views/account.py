# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import glob
import logging
import urllib
import datetime as dt

from flask import request, session, jsonify, redirect

from solariat.mail import Message
from solariat.utils.timeslot import parse_date_interval, datetime_to_timestamp_ms, parse_datetime, UNIX_EPOCH, Timeslot
from solariat_bottle.app import app, AppException
from solariat_bottle.configurable_apps import CONFIGURABLE_APPS
from solariat_bottle.db.predictors.base_predictor import PredictorConfigurationConversion
from solariat_bottle.db.account import Account, Package, account_stats, AccountEvent
from solariat_bottle.db.user import User
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.utils.mailer import send_mail
from solariat_bottle.views.gse_signup import _get_sender

js_ts = lambda dt: dt and datetime_to_timestamp_ms(dt) or None

DATE_FMT = '%m/%d/%Y'

def validate_dates(data):

    date_ = data.get('end_date', UNIX_EPOCH.strftime(DATE_FMT))
    if isinstance(date_, dt.datetime):
        date_ = date_.strftime(DATE_FMT)
    #LOGGER.debug("Validating {} type".format(type(date_)))
    data['end_date'] = parse_datetime(date_, default=UNIX_EPOCH)
    return data

@app.route('/account/json', methods=['GET'])
@login_required()
def account_details_handler(user):
    """
    Return current account info.
    For superuser accepts `account_id` parameter and returns any account by id.
    """
    account = user.account
    if user.is_staff:
        acct_id = request.args.get('account_id', '')
        try:
            account = Account.objects.get(id=acct_id)
        except Account.DoesNotExist:
            pass
            #return jsonify(ok=False, error="Account '%s' not found." % acct_name)

    if not account:
        return jsonify(ok=False, error="User is not under account.")

    return jsonify(ok=True, account=_json_account(account, user, with_stats=request.args.get('stats', False)))


@app.route('/accounts/salesforce/<account_id>', methods=['GET'])
@login_required()
def salesforce_handler(user, account_id):
    """
    This method does the initial authorization GET, which should redirect the user
    to salesforce and ask him to grant authorization to our application.
    """
    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        return jsonify(ok=False, error="No account with id=%s found in database." % account_id)

    client_id = app.config['SFDC_CLIENT_ID']
    secret_key = app.config['SFDC_CONSUMER_SECRET']
    redirect_uri = app.config['SFDC_REDIRECT_URI']
    base_url = 'https://login.salesforce.com/services/oauth2/authorize?'
    base_url += urllib.urlencode({"redirect_uri" : redirect_uri,
                                  "response_type" : 'code',
                                  "display" : "popup",
                                  "client_id" : client_id,
                                  "client_secret" : secret_key,
                                  "state" : str(account.id)})
    try:
        return redirect(base_url)
    except Exception, e:
        err_msg = "Couldn't get the response containing access_token! Exception : %s"%str(e)
        app.logger.error(err_msg)
        return jsonify(ok=False)


@app.route('/accounts/salesforcerevoke/<account_id>', methods=['GET', 'POST'])
@login_required()
def salesforce_invalidate(user, account_id):
    """
    Should invaliadate the auth token for a given account id.
    """
    import requests

    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        return jsonify(ok=False, error="Account id=%s does not exist in database." % account_id)
    if (not account.has_oauth_token()):
        return jsonify(ok=False, error="Account does not have oAuth enabled to salesforce")
    data = {'token' : account.oauth_token}
    revoke_post = requests.post("https://login.salesforce.com/services/oauth2/revoke", data=data)
    if revoke_post.status_code == 200:
        # All is well. Token revoked
        account.invalidate_oauth()
        return jsonify(ok=True)
    return jsonify(ok=False)

@app.route('/accounts/salesforcelogin', methods=['POST', 'GET', 'PUT', 'DELETE'])
def salesforce_recieved(*args, **kwargs):
    """
    The callback from our side to which salesforce will make a GET with the following
    parameters:
        {'code' : .... , 'state' : <the state passed in the initial request> (account_id in our case
        {'error' : .... , 'error_description' : ...} in case of failure
    Note that the 'code' retrived here is just a temporary one which can be used to access
    the refresh token and the 'session'-like authorization code.
    """
    import requests

    recieved_data = request.args
    if 'error' in recieved_data:
        error_code = recieved_data['error']
        error_msg = recieved_data['error_description']
        app.logger.error("Error (%s) : %s" % (error_code, error_msg))
    elif 'code' in recieved_data:
        temporary_token = recieved_data['code']
        account_id = recieved_data.get('state', None)

        data = {'code' : temporary_token,
                'grant_type' : 'authorization_code',
                'client_id' : app.config['SFDC_CLIENT_ID'],
                'client_secret' : app.config['SFDC_CONSUMER_SECRET'],
                'redirect_uri' : app.config['SFDC_REDIRECT_URI']}
        access_grant_request = requests.post('https://login.salesforce.com/services/oauth2/token', data=data)
        access_grant_response = access_grant_request.json()
        # Response at this point should look like this:
        # {u'access_token': u'00Di0000000fHia!ARIAQLLNYSeaq0rSxcEAb4qsMxE3pmSjKOv4lXm.b9wnKXRlEdhLeiB_bWZEs5lyi4NYTYJPpnYxzmxJv7L0vkUTtt0pCXlo',
        # u'signature': u'BcLQZqgQLyiaQYkXYBFdRCWjph49UpOBZF4NAvbBOLY=',
        # u'issued_at': u'1380526420859',
        # u'scope': u'id full api visualforce web refresh_token chatter_api',
        # u'instance_url': u'https://na15.salesforce.com',
        # u'id': u'https://login.salesforce.com/id/00Di0000000fHiaEAE/005i0000001A4JvAAK',
        # u'refresh_token': u'5Aep861z80Xevi74eXdr3INE2CN67lG0hCnbPX4kJhwEGwBhwRB_TNLL34Rg73LXDT5wh4Xw5PFTYH7b6y7rPAs'}
        # Or again an error / error_description

        refresh_token = access_grant_response.get('refresh_token', None)
        access_token = access_grant_response.get('access_token', None)
        if refresh_token is None or access_token is None:
            if 'error_description' in access_grant_response:
                return "An error occured: " + access_grant_response['error_description']
            return "Did not recieve a proper response from salesforce."
        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return "Account id=%s does not exist in database." % account_id
        account.sf_instance_url = access_grant_response['instance_url']
        account.set_oauth_token(refresh_token)
        account.access_token = access_token
        try:
            account.refresh_access_token()
        except ValueError, e:
            return str(e)
        return "Account %s now has access to Salesforce using oAuth2." % account.name
    return jsonify(ok=True)


@app.route('/accounts/json', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required()
def accounts_handler(user):
    """
    Accounts CRUD for superuser.
    """
    if not (user.is_staff or user.is_admin):
        if request.method != 'GET':
            params = request.json

            account = user.account
            existing_selected_app = account.selected_app
            new_selected_app = params.get('selected_app')
            if new_selected_app and new_selected_app != existing_selected_app:
                # Update just to be safe we're up to date with any changes in CONFIGURABLE_APPS
                available_apps = account.available_apps
                for key in available_apps.keys():
                    if key in CONFIGURABLE_APPS:
                        available_apps[key] = CONFIGURABLE_APPS[key]
                    else:
                        available_apps.pop(key)
                account.available_apps = available_apps
                account.selected_app = new_selected_app
                account.save()
                return jsonify(ok=True)
            else:
                return jsonify(ok=False, error='No access to editing accounts.')
        else:
            #return all accounts accessible by non-privileged user
            return jsonify(
                ok=True,
                data=[
                    _json_account(acct, user, with_stats=request.args.get('stats', False))
                    for acct in user.available_accounts
                ]
            )

    if request.method == 'GET':
        from_, to_ = None, None
        if request.args.get('account_id'):
            return account_details_handler()
        with_stats = request.args.get('stats', False)
        if with_stats:
            try:
                from_, to_ = parse_date_interval(request.args.get('from', None), request.args.get('to', None))
            except:
                pass
        return jsonify(
            ok=True,
            data=_query_accounts(
                user,
                with_stats=with_stats,
                start_date=from_,
                end_date=to_
            )
        )

    elif request.method == 'POST':
        params = request.json
        # Need to check whether the account exists
        name = params.get('name')
        if not name:
            return jsonify(ok=False, error="Name is required.")
        exists = Account.objects.find(name=name).count()
        if exists:
            ok = False
            result = "Account name '{}' already exists.".format(name)
            #ok, result = _update_account(user, **params)
        else:
            ok, result = _create_account(user, params)
        if ok:
            return jsonify(ok=ok, account=_json_account(result, user))
        else:
            return jsonify(ok=ok, error=result)

    elif request.method == 'DELETE':
        data = request.args
        if not data:
            return jsonify(
                ok=False, error='no parameters provided')

        acct_id = data.get('id')
        if acct_id:
            try:
                account = Account.objects.get_by_user(user, acct_id)
                res, msg = _delete_account(user, account)
                if not res:
                    raise AppException(msg)
            except AppException, ex:
                return jsonify(
                    ok=False,
                    error=str(ex))
            else:
                return jsonify(ok=True, data={})
        else:
            return jsonify(
                ok=False,
                error="No account id")

    elif request.method == 'PUT':
        data = request.json
        data = validate_dates(data)
        ok, result = _update_account(user, **data)
        if ok:
            return jsonify(ok=ok, account=_json_account(result))
        else:
            return jsonify(ok=ok, error=result)


@app.route('/accounts/no_account/json', methods=['GET'])
@login_required()
def no_account(user):
    # Just return NO_ACCOUNT instance in case needed in UI.
    if not user.is_superuser:
        return jsonify(ok=True, error='Only superuser has access to NO ACCOUNT.')
    return jsonify(ok=True, account=_no_account())


def _json_account(acct, user=None, with_stats=False, start_date=None, end_date=None, cache=None):
    if cache is None:
        cache = {}

    if acct:
        if (
            session.get('sf_oauthToken', False) and
            acct.access_token is not None and
                acct.account_type == 'Salesforce'):
            is_sf_auth = True
        else:
            is_sf_auth = False

        package = "Internal"
        if acct.package is not None:
            package = acct.package.name

        csm = acct.customer_success_manager
        if csm is not None:
            csm = csm.email

        adm = {'first': None,
               'last': None,
               'email': None}
        try:
            #  Note: Taking the first element might not be best
            if 'admins' in cache:
                admins = cache['admins']
            else:
                admins = [admin_user for admin_user in acct.admins if not admin_user.is_staff]
            admin = admins[0]
        except IndexError:  # only staff are admins
            pass
        else:
            adm['first'] = admin.first_name
            adm['last'] = admin.last_name
            adm['email'] = admin.email

        a_dict = {
            'id'              : str(acct.id),
            'name'            : acct.name,
            'channels_count'  : acct.get_current_channels(status__ne='Archived').count(),
            'account_type'    : acct.account_type,
            'package'         : package,
            'created_at'      : datetime_to_timestamp_ms(acct.created),
            'is_current'      : user and user.current_account and user.current_account.id == acct.id,
            'is_admin'        : user and (acct.can_edit(user) or user.is_superuser),
            'is_super'        : user and user.is_superuser,
            'is_staff'        : user and user.is_staff,
            'is_analyst'      : user and user.is_analyst,
            'is_only_agent'   : user and user.is_only_agent,
            'signature'       : user and user.signature_suffix,
            'is_sf_auth'      : is_sf_auth,
            'end_date'        : acct.end_date and datetime_to_timestamp_ms(acct.end_date),
            'configured_apps' : acct.available_apps.keys(),
            'available_apps'  : CONFIGURABLE_APPS.keys(),
            'selected_app'    : acct.selected_app,
            'customer_success_manager': csm,
            'notes'           : acct.notes,
            'admin'           : adm,
            'is_active'       : acct.is_active,
            'status'          : acct.status,
            'monthly_volume'  : 0,
            'is_locked'       : acct.is_locked,
            'updated_at'      : datetime_to_timestamp_ms(acct.updated_at) if acct.updated_at else None,
            'recovery_days'   : acct.recovery_days,
            'event_processing_lock': acct.event_processing_lock,
        }

        if 'users_count' in cache:
            a_dict['users_count'] = cache['users_count']
        else:
            a_dict['users_count'] = len([u for u in acct.get_users() if not u.is_system])

        if 'all_users_count' in cache:
            a_dict['all_users_count'] = cache['all_users_count']
        else:
            a_dict['all_users_count'] = len([u for u in acct.get_all_users() if not u.is_system])

        if user and user.is_admin:
            a_dict['gse_api_key'] = acct.gse_api_key

        if with_stats and user:
            a_dict['stats'] = account_stats(acct, user, start_date, end_date)
            today = dt.datetime.now()
            start_of_month = dt.datetime(today.year, today.month, 1)
            a_dict['monthly_volume'] = account_stats(acct, user, start_of_month, today)
            today_start, today_end = Timeslot(level='day').interval
            a_dict['daily_volume'] = account_stats(acct, user, today_start, today_end)
            a_dict['daily_volume_notification_emails'] = acct.daily_post_volume_notification.alert_emails
        return a_dict
    return None


def _no_account(orphans_count=1):
    """
    Returns a dictionary that can be used for users with no active account ('orphans')

    :param orphans_count: the number of orphans from the system (-1 if now known)

    :returns: a dictionary that mimics the one for a normal account from a view perspective
    """
    return {
            'id'                : -1,
            'name'              : Account.NO_ACCOUNT,
            'users_count'       : orphans_count,
            'all_users_count'   : orphans_count,
            'package'           : 'Internal',
            'created_at'        : 0,
            'is_current'        : True,
            'is_admin'          : True,
            'is_super'          : False,
            'signature'         : '',
            'end_date'           : 0,
            'customer_success_manager': None,
            'notes'             : None,
            'admin'             : None,
            'monthly_volume'    : 0
            }


def _create_account(user, params):
    try:
        #check uniqueness
        params = validate_dates(params)
        name = params.get('name')
        if not name:
            return False, "Name is required."
        exists = Account.objects.find(name=name).count()
        if exists:
            return False, "Account with name '%s' already exists. Please provide another name." % name

        LOGGER.debug("Creating new account: {}".format(params))
        acct = Account.objects.create_by_user(user, **params)
        #if user had no account - attach created
        if not user.account:
            user.account = acct
            user.save()

        return True, acct
    except Exception, e:
        return False, str(e)

def _create_trial(user, params):
    params['package'] = "Trial"
    return _create_account(user, params)

def _query_accounts(user, with_stats=False, start_date=None, end_date=None):
    if user.is_superuser:
        accounts_list = Account.objects.find()
    else:
        accounts_list = user.available_accounts
    return [_json_account(acct, user,
        with_stats=with_stats,
        start_date=start_date,
        end_date=end_date) for acct in accounts_list]


def _update_account(user, **data):
    LOGGER.debug("Updating account: {}".format(data))
    name = data.get('name')
    if not name:
        return False, "Name is required."

    allow_update_when_locked = False

    try:
        account = Account.objects.get_by_user(user, id=data['id'])
        if name != account.name:
            exists = Account.objects.find(name=name).count()
            if exists:
                return False, "Account with name '%s' already exists. Please provide another name." % name

        # when clicking on widget title in non-blank dashboard, these keys are restored from widget settings
        # it should be possible even when account is locked
        if set(data.keys()).issubset(('available_apps', 'configured_apps', 'id', 'name', 'selected_app', 'end_date')):
            # resetting name and end_date to prevent them from changing
            name = data['name'] = account.name
            data['end_date'] = account.end_date
            allow_update_when_locked = True

        if account.is_locked and not allow_update_when_locked:
            return False, "Account is locked, nobody can update the account."

        old_account_data = account.to_dict()
        account.name = name

        account_type = data.get('account_type', None)
        if account_type is not None:
            account.account_type = account_type

        package = data.get('package', None)
        if package is not None:
            try:
                package = Package.objects.get(name=package)
            except Package.DoesNotExist:
                raise AppException("Unsupported package type: {}".format(package))
            account.package = package

        csm = data.get('customer_success_manager', None)
        if csm is not None:
            if 'email' in csm:
                csm = csm['email']
            try:
                user = User.objects.get(email=csm)
            except User.DoesNotExist:
                raise AppException("Unknown user: {}".format(csm))
            account.customer_success_manager = user

        notes = data.get('notes', None)
        if notes is not None:
            account.notes = notes

        end_date = data.get('end_date', None)
        if end_date:
            account.end_date = end_date

        if 'daily_volume_notification_emails' in data:
            daily_volume_notification_emails = data.get('daily_volume_notification_emails', [])
            account.daily_post_volume_notification.alert_emails = daily_volume_notification_emails

        selected_app = data.get('selected_app')
        configured_apps = data.get('configured_apps', [])

        #if selected_app not in configured_apps:
        #    raise Exception("Account %s's selected app %r cannot be removed from 'Configurable Apps'" %
        #        tuple([each.encode('utf8') for each in (account.name, selected_app.encode('utf8'))])
        #    )

        available_apps = {}
        for app_name in configured_apps:
            available_apps[app_name] = CONFIGURABLE_APPS[app_name]

        if selected_app:
            if selected_app in available_apps:
                account.selected_app = selected_app
            else:

                pass
                # selected_app has been removed from available_apps
                #raise Exception("Invalid app: " + selected_app)

        account.available_apps = available_apps

        if 'recovery_days' in data:
            account._recovery_days = int(data['recovery_days'])

        account.save()
        new_account_data = account.to_dict()
        AccountEvent.create_by_user(user=user,
                                    change='Account edit',
                                    old_data=old_account_data,
                                    new_data=new_account_data)
    except Exception, e:
        return False, str(e)
    else:
        return True, account


def _delete_account(user, account):
    try:
        if account.is_locked:
            return False, "Account is locked, nobody can delete the account."

        if user.account == account:
            return False, "Can't delete current account."

        LOGGER.debug("Deleting Account: {}".format(account.name.encode('utf-8')))
        from ..db.channel.base import Channel

        acct_channels = Channel.objects(account=account, status__ne='Archived')
        if acct_channels.count() > 0:
            LOGGER.debug("Channels remaining: {}".format(acct_channels.count()))
            return False, ''.join([
                "You can not delete an account that contains channels. ",
                "Please delete the channels first."])

        account.delete_by_user(user)
        '''
        for u in account.get_users():
            user_accounts = [
                a for a in u.available_accounts if a.id != account.id]
            if user_accounts or u.is_staff:
                # this may leave staff users without account
                u.account = user_accounts and user_accounts[0] or None
                u.save()
            else:
                u.delete()
        assert account.get_users().count() == 0
        account.delete_by_user(user)
        '''
    except Exception, ex:
        app.logger.error("Error deleting Account", exc_info=True)
        return False, 'Could not delete account: {}'.format(str(ex))
    else:
        return True, ""


@app.route('/account/lock', methods=['Post'])
@login_required()
def lock_account(user):
    account_id = request.json.get('id')
    if not account_id:
        return jsonify(ok=False, error='no parameters provided')

    try:
        account = Account.objects.get(id=account_id)
        account.lock()
        AccountEvent.create_by_user(user=user,
                                    change='Account locked',
                                    event_data=dict(account_id=account_id))
        return jsonify(ok=True)
    except Exception, e:
        return jsonify(ok=False, error=str(e))


@app.route('/account/unlock', methods=['Post'])
@login_required()
def unlock_account(user):
    account_id = request.json.get('id')
    if not account_id:
        return jsonify(ok=False, error='no parameters provided')

    try:
        account = Account.objects.get(id=account_id)
        account.unlock()
        AccountEvent.create_by_user(user=user,
                                    change='Account unlocked',
                                    event_data=dict(account_id=account_id))
        return jsonify(ok=True)
    except Exception, e:
        return jsonify(ok=False, error=str(e))


class CursoredRequest(object):
    def __init__(self, model_class, limit=20, object_transform=lambda x: x.to_dict()):
        self.model_class = model_class
        self.limit = limit
        self.object_transform = object_transform

    def query(self, **params):
        from solariat.db.abstract import ObjectId
        last_id = params.pop('cursor', None)
        if last_id:
            try:
                last_id = ObjectId(last_id)
            except:
                raise AppException("Bad cursor")
            params["id__lt"] = last_id
        query_set = self.model_class.objects(**params).sort(id=-1).limit(self.limit + 1)
        result = [self.object_transform(item) for item in query_set]
        if result and len(result) == self.limit + 1:
            cursor = result[-2]['id']
        else:
            cursor = None
        return result[:self.limit], cursor


@app.route('/account/events', methods=['post'])
@login_required
def account_events(user):
    request_data = request.json
    account_id = request_data.get('id')
    if not account_id:
        return jsonify(ok=False, error='no parameters provided')

    try:
        limit = int(request_data.get('limit', 20))
    except:
        return jsonify(ok=False, error="Bad limit value")

    try:
        account = Account.objects.get_by_user(user, id=account_id)
    except Exception, e:
        logging.exception('')
        return jsonify(ok=False, error=str(e))
    else:
        try:
            data, cursor = CursoredRequest(AccountEvent, limit=limit).query(
                account=account,
                cursor=request_data.get('cursor', request_data.get('last_id')))
        except Exception, e:
            return jsonify(ok=False, error=str(e))
        else:
            return jsonify(ok=True, data=data, cursor=cursor)


@app.route('/account/predictor-configuration/<account_id>', methods=['GET', 'POST'])
@login_required
def predictor_configuration(user, account_id):
    account = Account.objects.get(account_id)
    metadata = account.account_metadata

    if request.method == 'GET':
        configuration = metadata.predictors_configuration
        return jsonify(ok=True, data=PredictorConfigurationConversion.python_to_json(configuration))
    elif request.method == 'POST':
        configuration = request.json
        try:
            metadata.predictors_configuration = PredictorConfigurationConversion.json_to_python(configuration)
            metadata.save()
            return jsonify(ok=True)
        except Exception, err:
            app.logger.exception('Exception while saving predictor configuration:')
            return jsonify(ok=False, error=str(err))


EMAIL_TEMPLATES = []
for _file in glob.glob('templates/partials/accounts/email_templates/*.txt'):
    with open(_file) as f:
        contents = f.readlines()
        subject = contents[0].strip()
        body = ''.join(contents[1:])
        EMAIL_TEMPLATES.append(dict(subject=subject, body=body))

@app.route('/account/email-data')
@login_required
def account_email_data(user):
    sender = _get_sender()
    data = {
            'from_address': '%s <%s>' % (sender[0], sender[1]),
            'accounts': [{'id': str(ac.id), 'value': ac.name} for ac in Account.objects()],
            'roles': user.accessible_roles,
            'templates': EMAIL_TEMPLATES,
    }
    return jsonify(ok=True, data=data)

@app.route('/account/send-mail', methods=['POST'])
@login_required
def account_send_mail(user):
    data = request.json
    accounts = [each['id'] for each in data['accounts']]
    roles = [each['id'] for each in data['roles']]
    subject = data['subject']
    body = data['body']

    account_names = [each['value'].encode('utf8') for each in data['accounts']]
    role_names = [each['value'].encode('utf8') for each in data['roles']]

    if not subject or not body:
        return jsonify(ok=False, error="Please enter subject and body")

    users = User.objects.find(account__in=accounts, user_roles__in=roles)
    recipients = [user.email for user in users]

    if not recipients:
        return jsonify(ok=False, error="No users found in accounts %s with roles %s." % (account_names, role_names))

    msg = Message(subject=subject,
                  sender=_get_sender(),
                  recipients=recipients)
    msg.body = body

    try:
        send_mail(msg, email_description="Account notification by staff user")
        return jsonify(ok=True, recipients=recipients)
    except Exception, err:
        error = "Sorry, we failed to send email to %s. %s" % (recipients, str(err))
        return jsonify(ok=False, recipients=recipients, error=error)
