from flask import request, render_template, jsonify, session

from solariat_bottle.app import app
from solariat_bottle.utils.mailer import send_confimation_email, send_new_channel_creation
from solariat_bottle.db.user import ValidationToken, AuthError
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.app import logger


ERROR_VALIDATION_TOKEN = "Token is incorrect or expired"


def get_validation_token(digest):
    try:
        assert digest
        token = ValidationToken.objects.get(digest=digest)
        assert token.is_valid
    except (ValidationToken.DoesNotExist, AssertionError):
        token = None
    return token


@app.route("/signup", methods=['GET', 'POST'])
def signup_wizard():
    if request.method == "POST":
        digest = session.pop('validation_token', None)
        validation = get_validation_token(digest)
        if not validation:
            return jsonify(ok=False, error=ERROR_VALIDATION_TOKEN)

        user = validation.target
        password = request.json['password']
        confirm = request.json['password_confirm']
        if password != confirm:
            return jsonify(ok=False, error="Passwords are not the same.")
        else:
            user.set_password(password)
        account = user.current_account

        title = request.json['channel']['title']
        keywords = request.json['channel']['keywords']
        # skipwords = request.json['channel']['skipwords']
        usernames = request.json['channel']['handles']

        try:
            validation.consume()    # This makes sure we don't create multiple channels using same token
        except AuthError, ex:
            return jsonify(ok=False, error=str(ex))
        channel = TwitterServiceChannel.objects.create_by_user(user, account=account, title=title)

        if isinstance(keywords, str):
            keywords = keywords.split(',')
        for keyword in keywords:
            channel.add_keyword(keyword)

        if isinstance(usernames, str):
            usernames = usernames.split(',')
        for username in usernames:
            channel.add_username(username)

        # if isinstance(skipwords, str):
        #     skipwords = skipwords.split(',')
        # for skipword in skipwords:
        #     channel.inbound_channel.add_skipword(skipword)

        channel.save()
        channel.on_active()
        send_confimation_email(validation.creator, validation.target, keywords, usernames, skipwords="")

        staff_user = validation.creator
        link = (
            u"%s/configure#/channels" % app.config.get('HOST_DOMAIN')
        ).replace('//configure', '/configure')
        try:
            send_new_channel_creation(staff_user, user, channel, link)
        except:  # SMTP error
            logger.exception('Could not send new channel creation for trail account to staff user')

        session['user'] = str(user.id)

        return jsonify(ok=True)

    elif request.method == "GET":
        digest = request.args.get('validation_token', None)
        validation = get_validation_token(digest)
        if not validation:
            return render_template('signup-error.html',
                                   error=ERROR_VALIDATION_TOKEN), 402

        target_mail = validation.target.email
        full_name = ""
        if validation.target.first_name:
            full_name += validation.target.first_name + " "
        if validation.target.last_name:
            full_name += validation.target.last_name
        session['validation_token'] = digest
        return render_template('signup.html', target_email=target_mail, target_name=full_name)
