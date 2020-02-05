"""
Any specific email interaction utilities should go here.
Using sendmail so we have better control in production environment.
"""
from datetime import datetime
from itsdangerous import URLSafeSerializer
from jinja2 import Environment, PackageLoader

from solariat.mail import Message

from solariat_bottle.settings import get_app_mode, LOGGER, get_var
from solariat.exc.base import AppException
from solariat_bottle.db.user import User

ENV = Environment(loader=PackageLoader('solariat_bottle', 'templates'))


def render_template(template, **context):
    """
    Render a template directly using JINJA so we avoid dependencies on a flask
    request needed in order to do rendering.

    :param template: The name of the template that we want to render
    :param context: The context we are using for rendering
    """
    template = ENV.get_template(template)
    return template.render(**context)


def _get_sender():
    host_domain = get_var('HOST_DOMAIN')
    if '//' in host_domain:
        host_domain = host_domain.split('//')[1]
    return (
        "Genesys Social Analytics Notification",
        "Notification-Only--Do-Not-Reply@" + host_domain)


class EmailSendError(AppException):
    pass


def send_mail(msg, email_description='email'):
    # avoiding a circular module dependency
    from solariat_bottle.app import MAIL_SENDER
    try:
        return MAIL_SENDER.send(msg)
    except Exception, err:
        LOGGER.exception("Sending %r failed because %r." % (email_description, str(err)))
        raise EmailSendError("Sending %r failed because %r." % (email_description, str(err)))


def error_notifier_500(subject, raised_exception, system_info=None):
    if get_app_mode() == 'prod':
        recipients = get_var('DEV_ADMIN_LIST')
        if not recipients:
            return
        msg = Message(subject=subject)
        msg.recipients = recipients
        msg.html = render_template("error_pages/500_email_notification.html",
                                   error_message=raised_exception,
                                   system_info=system_info)
        try:
            send_mail(msg)
        except EmailSendError:
            pass
    else:
        LOGGER.error("Got unhandled exception:")
        LOGGER.error(raised_exception)
        LOGGER.error("System info when it was raised:")
        LOGGER.error(system_info)


def send_invitation_email(user, validation_token, full_name):
    """
    First invitation email once a new trial has been created by staff member.
    """
    msg = Message(subject="Twitter Channel Sign-up - Genesys Social Analytics",
                  sender=_get_sender(),
                  recipients=[user.email])
    msg.html = render_template(
        "mail/invitation_email.html",
        full_name=full_name,
        url=validation_token.signup_url
    )
    # LOGGER.debug(msg.body)
    if get_app_mode() != 'dev':
        send_mail(msg, email_description='invitation email')
    else:
        LOGGER.info(msg.html)


def send_validation_email(user, channel):
    """
    Sends validation email once successfully configured a twitter channel through the signup wizzard.
    """
    msg = Message(subject="Twitter Channel Confirmation - Genesys Social Analytics",
                  sender=_get_sender(),
                  recipients=[user.email])
    msg.html = render_template(
        "mail/validation_email.html",
        channel_name=channel.title,
        url=get_var('HOST_DOMAIN')
    )
    # LOGGER.debug(msg.body)
    if get_app_mode() != 'dev':
        send_mail(msg, email_description='channel confirmation email')
    else:
        LOGGER.info(msg.html)


def send_new_channel_creation(staff_user, admin_user, channel, link):
    """
    Send warning email to a user once a user with a trial account creates a new channel
    """
    msg = Message(subject="A channel has been created for a trial account you created",
                  sender=_get_sender(),
                  recipients=[staff_user.email] + get_var('ONBOARDING_ADMIN_LIST'))
    handles = channel.usernames
    thandle = 'Unknown'
    for handle in handles:
        if handle.startswith('@'):
            thandle = handle

    # Get the sender name
    staff_user_name = 'Unknown'
    admin_user_name = 'Unknown'
    admin_email = 'Unknown'
    ckeywords = 'None defined yet'
    cskipwords = 'None defined yet'

    if staff_user.first_name is not None:
        staff_user_name = staff_user.first_name
    if admin_user.first_name is not None:
        admin_user_name = admin_user.first_name
    if admin_user.email is not None:
        admin_email = admin_user.email
    if channel.keywords:
        ckeywords = ''
        for keyword in channel.keywords:
            ckeywords += keyword + ' '
    if channel.skipwords:
        cskipwords = ''
        for skipword in channel.skipwords:
            cskipwords += skipword + ' '
    msg.html = render_template(
        "mail/new_channel_creation.html",
        staff_user_name=staff_user_name,
        admin_user_name=admin_user_name,
        admin_user_email=admin_email,
        keywords=ckeywords,
        skipwords=cskipwords,
        twitter_handle=thandle,
        channel_link=link
    )
    if get_app_mode() != 'dev':
        send_mail(msg, email_description='new channel confirmation email')
    else:
        LOGGER.info(msg.html)


def send_confimation_email(user, on_boarded_customer, keywods, usernames, skipwords):
    """
    Send confirmation email to a user once signup process is completed
    """
    msg = Message(subject="Customer just signed up! - Genesys Social Analytics",
                  sender=_get_sender(),
                  recipients=[user.email] + get_var('ONBOARDING_ADMIN_LIST'))
    msg.html = render_template(
        "mail/confirmation_email.html",
        user_name=user.first_name,
        customer_email=on_boarded_customer.email,
        keywords=keywods,
        usernames=usernames,
        skipwords=skipwords
    )
    if get_app_mode() != 'dev':
        send_mail(msg, email_description='signup notification email')
    else:
        LOGGER.info(msg.html)


def send_user_create_notification(user):
    """
    Sends a notification to recently created user with a url of the app and a url to reset his password.

    :param user: The recently create user
    """
    url = user.signed_password_url()
    app_url = get_var('HOST_DOMAIN')
    msg = Message(subject="Your Genesys Social Analytics Login Has Been Setup",
                  sender=_get_sender(),
                  recipients=[user.email])
    msg.html = render_template(
        "mail/user_creation_email.html",
        url=url,
        app_url=app_url)
    # LOGGER.debug(msg.body)
    if get_app_mode() != 'dev':
        send_mail(msg, email_description='email notification to the created user')
    else:
        LOGGER.info(msg.html)


def send_account_posts_limit_warning(user, percentage, volume):
    """
    Sends a warning message to the Account admin when the posts limit for that account has reached a percentage
    :param user: The admin user or users
    :param percentage: The percentage surpassed
    :param volume: The volume allowed for this account
    """
    msg = Message(subject="Genesys Social Analytics Notification, " + percentage
                  + " of Permitted Traffic Volume Reached",
                  sender=_get_sender(),
                  recipients=[user.email])
    msg.html = render_template(
        "mail/threshold_warning.html",
        user_name=user.first_name or "Admin",
        percentage=percentage,
        volume=volume)

    if get_app_mode() != 'dev':
        send_mail(msg)
    else:
        LOGGER.info(msg.html)


def send_account_posts_daily_limit_warning(recipients, account_name, limit, template='mail/daily_limit_reached.html'):
    for (email, first_name) in recipients:
        msg = Message(subject="Daily limit of {} posts reached. Genesys Social Analytics Notification.".format(limit),
                      sender=_get_sender(),
                      recipients=[email])
        msg.html = render_template(template,
                                   user_name=first_name or 'Admin',
                                   limit=limit,
                                   account_name=account_name)
        send_mail(msg)


def send_tag_alert_emails(tag):
    """
    Sends emails to every tag.alert_email
    :param tag SmartTagChannel:
    :returns: True if sending process was successful, False otherwise
    """

    if not tag.alert_can_be_sent:
        return False

    # to prevent sending several emails by different processes
    # we sent alert_last_sent_at to current time
    # it is changed back if sending was unsuccesful
    previous_sent_time = tag.alert_last_sent_at
    tag.alert_last_sent_at = datetime.now()
    tag.save()

    # noinspection PyBroadException
    try:
        tag_edit_url = '{}/configure#/tags/edit/{}'.format(
            get_var('HOST_DOMAIN'), str(tag.id))
        for user_email in tag.alert_emails:
            s = URLSafeSerializer(get_var('UNSUBSCRIBE_KEY'), get_var('UNSUBSCRIBE_SALT'))
            email_tag_id = s.dumps((user_email, str(tag.id)))
            tag_unsubscribe_url = '{}/unsubscribe/tag/{}'.format(
                get_var('HOST_DOMAIN'), email_tag_id)
            tag_view_url = '{}/inbound#?tag={}&channel={}'.format(
                get_var('HOST_DOMAIN'), str(tag.id), str(tag.parent_channel)
            )
            msg = Message(
                subject="Geneys Social Analytics Alert - Smart Tag",
                sender=_get_sender(),
                recipients=[user_email])
            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                user = None
            msg.html = render_template(
                "mail/smarttag_alert.html",
                user_name=user.first_name if user else None,
                tag_title=tag.title,
                tag_edit_url=tag_edit_url,
                tag_unsubscribe_url=tag_unsubscribe_url,
                tag_view_url=tag_view_url
            )
            # get_var('ON_TEST') since when running tests
            # get_app_mode() returns 'dev' in pool_worker thread
            try:
                app_mode = get_app_mode()
            except RuntimeError:
                app_mode = 'dev'
            if app_mode != 'dev' or get_var('ON_TEST'):
                send_mail(msg)
            else:
                LOGGER.info(msg.html)
        tag.alert_last_sent_at = datetime.now()
        tag.save()
        return True
    except:
        if previous_sent_time:
            tag.alert_last_sent_at = previous_sent_time
            tag.save()
        return False
