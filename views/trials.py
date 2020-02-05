from flask import request, jsonify

from solariat_bottle.db.user import User, ValidationToken
#from solariat_bottle.db.trials import Trial
from solariat_bottle.db.roles import ADMIN, AGENT, ANALYST
from solariat_bottle.app import app, logger, AppException
from solariat_bottle.db.account import Account

from solariat_bottle.utils.decorators import login_required
from solariat_bottle.utils.mailer import send_invitation_email
from solariat.utils.timeslot import datetime_to_timestamp_ms, parse_datetime, now, Timeslot, UNIX_EPOCH

from solariat_bottle.db.account import account_stats
from solariat_bottle.views.account import _create_trial

js_ts = lambda dt: dt and datetime_to_timestamp_ms(dt) or None

ERROR_DUP_USER = "Looks like you've already registered for a trial. Sorry, you're only allowed register for one trial. If you have further questions, please contact your customer success manager."
ERROR_DATE_RANGE = "End date should be greater than start date"


def account_name_from_email(email):
    account_name = email.replace('@', '_at_')
    account_name = account_name.replace('.', '_dot_')
    return account_name


def split_full_name(full_name):
    names = full_name.split(' ')
    if len(names) == 2:
        first_name = names[0]
        last_name = names[1]
    else:
        first_name = full_name
        last_name = ""
    return first_name, last_name


def date_is_empty(date):
    return not date or date == UNIX_EPOCH


def validate_date_range(data):
    start_date = parse_datetime(data.get('start_date'), default=now())
    end_date = parse_datetime(data.get('end_date'), default=UNIX_EPOCH)
    if not date_is_empty(end_date) and end_date <= start_date:
        return {"ok": False, "error": ERROR_DATE_RANGE}
    else:
        data['start_date'] = start_date
        data['end_date'] = end_date
    return {"ok": True}


def query_trials(user, params):
    trials = Account.objects.find_by_user(user, package="Trial", **params)
    return trials


def get_trial(user, item_id):
    try:
        return True, Account.objects.get_by_user(user, package="Trial", id=item_id)
    except Account.DoesNotExist:
        return False, "Trial does not exist"


def _create_trial_json(user, data):
    objects_created = []

    def clear_created_objects():
        for obj in objects_created:
            obj.delete()

    if not user.is_staff:
        return dict(ok=False,
                    error="Only staff members are allowed to create trials.")
    email = data['email']
    if data.get('full_name'):
        first_name, last_name = split_full_name(data['full_name'])
    else:
        first_name, last_name = data['first_name'], data['last_name']
    account_name = data.get('account_name', None)
    account_name = account_name or account_name_from_email(email)

    resp, trial = _create_trial(user, 
                                {'name': account_name,
                                 'start_date':data['start_date'], 
                                 'end_date':data['end_date']})
    if not resp:
        clear_created_objects()
        return dict(ok=False, error='Error creating Trial: {}'.format(trial))
    else:
        objects_created.append(trial)

    try:
        new_user = User.objects.create(
            email=email, account=trial,
            user_roles=[ADMIN, AGENT, ANALYST],
            first_name=first_name, last_name=last_name)
    except AppException, e:
        clear_created_objects()
        if 'dup key' in str(e):
            return dict(
                ok=False,
                error=ERROR_DUP_USER)
        return dict(ok=False, error='Cannot create user')
    else:
        objects_created.append(new_user)
    
    token = ValidationToken.objects.create_by_user(user, target=new_user)
    objects_created.append(token)

    full_name = ' '.join([new_user.first_name, new_user.last_name])
    try:
        send_invitation_email(new_user, token, full_name)
    except:  # SMTP error
        logger.exception('Invitation was not sent')
        clear_created_objects()
        return dict(ok=False, error='Invitation was not sent')
    return dict(ok=True, item=_json_trial(user, trial))


def _json_trial(user, item, stats_by_account=None, with_stats=False):
    result = {
        "account_name": item.name or "Unnamed Trial",
        "account_id": str(item.id),
        "start_date": js_ts(item.start_date),
        "end_date": js_ts(item.end_date),
        "created_at": js_ts(item.created),
        "status": item.status
    }
    if stats_by_account:
        result["stats"] = stats_by_account[item]
    elif with_stats:
        month_start, month_end = Timeslot(level='month').interval

        result["stats"] = account_stats(
            item, user, start_date=month_start, end_date=month_end)
    return result


def _update_trial_json(user, item_id, data):
    ok, trial_or_err = get_trial(user, item_id)
    if ok:
        trial_or_err.start_date = data['start_date']
        trial_or_err.end_date = data['end_date']
        #trial_or_err.updated_at = now()
        trial_or_err.save()
        return {"ok": True, "item": _json_trial(user, trial_or_err)}
    else:
        return {"ok": ok, "error": trial_or_err}


def _query_trials_json(user, params):
    items = query_trials(user, params)
    return {
        "ok": True,
        "items": [_json_trial(user, item, None, True) for item in items]
    }


def _get_trial_json(user, item_id):
    ok, trial_or_error = get_trial(user, item_id)
    if ok:
        return {"ok": True, "item": _json_trial(user, trial_or_error)}
    else:
        return {"ok": False, "error": trial_or_error}


@app.route('/trials/<item_id>/json', methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/trials/json', methods=['GET', 'POST'])
@login_required()
def trial_crud(user, item_id=None):
    def dispatch():
        if request.method == "POST":
            data = dict(request.json)
            #LOGGER.debug("Create Trial Endpoint: {}".format(data))
            valid = validate_date_range(data)
            if not valid['ok']:
                return res

            if not item_id:
                return _create_trial_json(user, data)
            else:
                return _update_trial_json(user, item_id, data)

        elif request.method == "GET":
            if not item_id:
                params = request.args
                return _query_trials_json(user, params)
            else:
                return _get_trial_json(user, item_id)

    try:
        res = dispatch()
    except Exception, e:
        return jsonify(ok=False, error=unicode(e))
    else:
        return jsonify(res)
