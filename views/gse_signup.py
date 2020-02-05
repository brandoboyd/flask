import re
import json
from flask import request, session, render_template, jsonify, url_for, redirect

from solariat.mail import Message

from solariat_bottle.app import app, logger
from solariat_bottle.configurable_apps import CONFIGURABLE_APPS, APP_GSE
from solariat_bottle.db.user import User, ValidationToken, ADMIN
from solariat_bottle.db.account import Account
from solariat_bottle.settings import AppException
from solariat_bottle.utils.mailer import send_mail
from solariat.utils.timeslot import now


def _get_sender():
    host_domain = request.host.split(':')[0]
    if host_domain == "localhost" or re.match(r"(\d+\.){3}\d+$", host_domain):
        host_domain = "genesys.com"
    return ("Genesys Social Engagement", "no-reply@" + host_domain)


@app.route("/gse/signup", methods=["GET", "POST"])
def gse_signup():
    if request.method == "GET":
        return render_template("gse_signup/signup.html")

    elif request.method == "POST":
        data = request.json
        first_name = data["first_name"].strip()
        last_name = data["last_name"].strip()
        email = data["email"].strip()
        company_name = data["company_name"].strip()

        if len(company_name) > 30:
            return jsonify(ok=False, error="Company name must not be greater than 30 chars long "
                                           "(%d chars given)" % len(company_name))

        account_created = False
        user_created = False
        token_created = False

        try:
            account = Account.objects.find_one(name=company_name)
            if account is None:
                account = Account.objects.create(
                        name=company_name,
                        available_apps={APP_GSE: CONFIGURABLE_APPS[APP_GSE]},
                        created_at=now(),
                )
                account.selected_app = APP_GSE
                account_created = True
            else:
                return jsonify(ok=False, error="Company name '%s' cannot be used because account "
                                               "with the same name already exists." % company_name)

            # create user but don't activate it yet
            # by setting random password behind the scene
            try:
                user = User.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        account=account,
                        user_roles=[ADMIN],
                )
                user_created = True
            except AppException:
                raise Exception("Sorry, this email is already registered.")

            token = ValidationToken.objects.create_by_user(user)
            token_created = True
            verification_link = url_for("gse_signup_confirm",
                                        validation_token=token.digest,
                                        _external=True)

            # send verification email
            msg = Message(subject="Confirmation required for Genesys Social Engagement deployment",
                          sender=_get_sender(),
                          recipients=[user.email])
            msg.html = render_template(
                "gse_signup/emails/verification.html",
                user=user,
                verification_link=verification_link,
            )
            try:
                send_mail(msg, email_description="GSE signup verification email")
            except Exception, err:
                app.logger.exception("send_mail failed for GSE signup verification email")
                raise Exception("Sorry, we failed to send email to '%s' (%s). Please contact customer support to complete your account provisioning." % (user.email, err))

            notify_staff_about_signup(user)

        except Exception, err:
            #app.logger.exception('GSE signup failed')
            if account_created:
                account.delete()
            if user_created:
                user.delete()
            if token_created:
                token.delete()

            return jsonify(ok=False, error=str(err))


        return jsonify(ok=True)


def notify_staff_about_signup(user):
    recipients = app.config['NEW_GSE_SIGNUP_EMAIL_LIST']
    if not recipients:
        return

    msg = Message(subject="New customer signs up for GSE",
                  sender=_get_sender(),
                  recipients=recipients)
    msg.html = render_template(
            "gse_signup/emails/staff_notification.html",
            user=user,
            host_url=request.host_url,
    )
    send_mail(msg, email_description="Staff notification about GSE signup")


@app.route("/gse/signup/confirm", methods=["GET", "POST"])
def gse_signup_confirm():
    token = request.args.get("validation_token")
    if not token:
        return jsonify(ok=False, error="Validation token is required.")

    vt = ValidationToken.objects.find_one(digest=token)
    if not (vt and vt.is_valid):
        return jsonify(ok=False, error="Validation token is invalid.")

    user = vt.creator
    user_data = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "company_name": user.account.name,
    }
    session['user'] = user_data

    if request.method == "GET":
        return render_template("gse_signup/signup.html", show_password=True, user_json=json.dumps(user_data))

    elif request.method == "POST":
        data = request.json
        password = data["password"]

        # I guess, changing other fields is not in the spec, so just set password here
        user.set_password(password)

        # send email saying login has been completed
        msg = Message(subject="Your Genesys Social Engagement login has been completed",
                      sender=_get_sender(),
                      recipients=[user.email])
        msg.html = render_template(
            "gse_signup/emails/after_successful_signup.html",
            user=user,
            host_url=request.host_url,
        )
        try:
            send_mail(msg, email_description="GSE signup successful email")
        except Exception, err:
            app.logger.exception("send_mail failed after successful GSE signup")

        # expire validation token
        vt.consume()
        return jsonify(ok=True, redirect_url=url_for("gse_signup_success"))


@app.route("/gse/signup/success", methods=["GET"])
def gse_signup_success():
    if 'user' not in session:
        return redirect("/gse/signup")
    else:
        return render_template("gse_signup/success.html", host_url=request.host_url,
                               user=session['user'])


#@app.route("/gse/signup/validate_customer", methods=["GET"])
#def gse_signup_validate_customer_id():
#    identification_number = request.args.get("identification_number")
#    if not identification_number:
#        return jsonify(ok=False, error="Version number is required.")  # formerly identification_number
#
#    if identification_number.strip() == "8.5.2":
#        return jsonify(ok=True)
#    else:
#        return jsonify(ok=False, error="Incorrect version number.")
