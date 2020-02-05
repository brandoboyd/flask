"Login/Logout handlers"

import re
import urllib

from solariat.mail import Message

from flask import (session, redirect, request, flash, render_template,
                   abort, jsonify, get_flashed_messages)

from solariat.utils.http import safe_url as http_safe_url

from ..app import app, MAIL_SENDER
from solariat_bottle.settings import LOGGER
from ..utils.decorators import superuser_required
from ..db.api_auth import AuthToken
from ..db.user import User
from ..db.account import AccountEvent
from ..db.event_log import log_event


PASSWORD_RE = {'lower':re.compile("[a-z]"),
               'upper':re.compile("[A-Z]"),
               'numeric':re.compile("[0-9]"),
               'special':re.compile("[\W_]")}


def safe_url(url):
    host_url = app.config['HOST_DOMAIN']
    return http_safe_url(url, host_url)


def redirect_safe(url):
    return redirect(safe_url(url))


@app.route('/simulate/<user_email>', methods=['GET'])
@superuser_required
def simulate(user, user_email):
    """ This lets a superuser to become any registered user
    """
    try:
        user = User.objects.get(email=user_email)
        session['user'] = str(user.id)
        if request.form.get('next'):
            return redirect_safe(urllib.unquote_plus(request.form['next']))
        else:
            return redirect('/')
    except User.DoesNotExist:
        flash("User with email %s is not registered." % user_email)

    return render_template(
        'login.html',
        name='login',
        next=safe_url(request.args.get('next', '/'))
    )


def password_is_strong(pwd):
    strength = sum(map(lambda x:1 if x.search(pwd) else 0, PASSWORD_RE.values()))
    return strength >= 3

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    "Perform logout"
    session.pop('user', None)
    session.pop('sf_oauthToken', None)
    return redirect('/login')


@app.route('/login', methods=['POST', 'GET'])
def login():
    "Try to auth user on POST, show form on GET"
    status_code = 200
    if request.method == 'POST':
        try:
            user = User.objects.get(email = request.form['email'].lower())
            if not user.check_password(request.form['password']):
                status_code = 401
                log_event('LoginFailedEvent',
                          user=user.email,
                          note="Password doesn't match")
                flash("Password doesn't match.")
            elif not len(user.available_accounts) and not app.config['ON_TEST'] and not user.is_superuser:
                status_code = 401
                flash("You are not associated with any accounts.")
            elif not user.is_staff and user.account and len(user.accounts) == 1 and not user.account.is_active:
                # Inactive single account
                status_code = 401
                flash("Your account is no longer active. \
                    Please contact your customer success manager if you have questions.")
            else:
                log_event('LoginEvent', user=user.email, note='success')
                # Check the password is strong
                if not password_is_strong(request.form['password']):
                    flash(render_template('partials/password_weak_flash.html',
                                          u=user), category='user_flash')
                session['user'] = str(user.id)
                AccountEvent.create_by_user(user=user,
                                            change='Logged in')

                if request.form.get('next'):
                    next_url = urllib.unquote_plus(request.form['next']) + request.form.get('hash_url', '')
                    return redirect_safe(next_url)
                else:
                    return redirect_safe(user.landing_page)
        except User.DoesNotExist:
            status_code = 401
            log_event('LoginFailedEvent',
                      user=request.form['email'],
                      note="User doesn't exist")
            flash("User with email %s is not registered." % (
                    request.form['email']))

    return render_template('login.html',
                            status_code=status_code,
                            name='login',
                            next=safe_url(request.args.get('next', '/'))), status_code

@app.route('/genesys_login', methods=['POST', 'GET'])
def genesys_login():
    "Try to auth user on POST, show form on GET"
    status_code = 200
    if request.method == 'POST':
        try:
            user = User.objects.get(
                email = request.form['email'].lower())
            if not user.check_password(request.form['password']):
                status_code = 401
                log_event('LoginFailedEvent',
                          user=user.email,
                          note="Password doesn't match")
                flash("Password doesn't match.")
            elif not len(user.available_accounts) and not app.config['ON_TEST'] and not user.is_superuser:
                status_code = 401
                flash("You are not associated with any accounts.")
            else:
                log_event('LoginEvent', user=user.email, note='success')
                # Check the password is strong
                if not password_is_strong(request.form['password']):
                    flash(render_template('partials/password_weak_flash.html',
                                          u=user), category='user_flash')
                session['user'] = str(user.id)
                if request.form.get('next'):
                    return redirect_safe(urllib.unquote_plus(request.form['next']))
                else:
                    return redirect('/inbound')
        except User.DoesNotExist:
            status_code = 401
            log_event('LoginFailedEvent',
                      user=request.form['email'],
                      note="User doesn't exist")
            flash("User with email %s is not registered." % (
                    request.form['email']))

    if status_code == 200:
        template = 'genesys_login.html'
    else:
        template = 'login.html'

    return render_template(template,
                           status_code=status_code,
                           name='login',
                           next=safe_url(request.args.get('next', '/'))), status_code


@app.route("/passrestore", methods=['GET', 'POST'])
def restore_password():
    "Send email with link for pasword reset"
    def get_signed_link(auth_token, email):
        """Return link to password restore form
        with auth_token parameter

        """
        return "%susers/%s/password?auth_token=%s" % (
            request.host_url, email, auth_token.digest)

    def send_restore_link(email):
        "Create AuthToken and send restore link"
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            flash("%s is not registered" % email)
            app.logger.warning(
                "request password restore for non registered %s",
                email)
            return False
        auth_token = AuthToken.objects.create_for_restore(
            user=user)
        message = Message(
            subject="Password restore link for Genesys Social Engagement",
            body="Please use the following link %s to reset your password"
                 " for Genesys Social Engagement/Social Analytics" % get_signed_link(auth_token, email),
            recipients=[email])
        app.logger.debug("sent restore link to %s", email)
        app.logger.debug(MAIL_SENDER.send(message))
        return True


    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash("No email provided")
        else:
            try:
                if send_restore_link(email):
                    flash("Please, check your mail box.")
                    return redirect('/login')
            except Exception, ex:
                LOGGER.error(ex)
                flash("Failed to sent restore email. Email communication problems.")
                return redirect('/login')

    return render_template('passrestore.html')


def get_current_user():
    "Get current user from session or auth_token"
    if session.get('user'):# check is user logged in
        return User.objects.get_current()

    auth_digest = request.args.get('auth_token')
    try:
        auth_token = AuthToken.objects.get(
            digest=auth_digest)
    except AuthToken.DoesNotExist:
        flash("Restore link is expired or wrong formatted")
    else:
        try:
            if auth_token.is_valid:
                session['user'] = str(auth_token.user.id)
                return auth_token.user
            else:
                flash("Your password restore link in expired")
                return
        finally:
            auth_token.delete()


@app.route("/users/<email>/password", methods=['POST', "GET"])
def user_password(email):
    """Change user passwod, user could be logged in
    or use auth_token in GET (from password reminder)

    """

    def update_password(user):
        "Update password with data from request"
        new_password = request.form.get('password')
        if not new_password:
            flash("No new password is provided")
            return False
        if len(new_password) < 8 or len(new_password) > 18:
            flash("New password has a wrong size")
            return False
        if not password_is_strong(new_password):
            flash("New password is weak")
            return False
        user.set_password(new_password)
        #Don't push this message so the user does not get notified in login paga
        #flash("New password was set.")
        return True

    app.logger.debug("in password restoring")
    current_user = get_current_user()
    app.logger.debug("current user is %s", current_user)
    "Only redirect if this is the same user that is changing password"
    same_user = False
    if not current_user:
        return redirect('/login')
        same_user = True

    try:
        email = email.lower()
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        flash("User '%s' does not exist.")
        abort(404) # TODO: this is UI, not API ! respect human beings, plz

    if request.method == 'POST':
        ok = False
        if current_user.can_edit(user):
            ok = update_password(user)
            if ok:
                if not request.is_xhr:
                    # from an email with shared item
                    if request.args.get('next'):
                        return redirect_safe(request.args.get('next'))
                    if same_user:
                        return redirect('/login')
                    else:
                        return jsonify(ok=True, messages=["Changed password correctly."])
        else:
            return jsonify(ok=False, messages=["You do not have edit permissions on that account."])

        messages = get_flashed_messages()
        return jsonify(ok=ok, messages=messages)
#    return render_template("password.html",
#                           user = user,
#                           name = 'users')

    return redirect("/configure#/password/%s" % email)
