#!/usr/bin/env python2.7
from solariat_bottle.tasks.twitter import get_twitter_api

import tweepy
import facebook

from solariat_bottle.utils.facebook_extra import reset_fbot_cache
from ..app import app
from solariat_bottle.db.channel.facebook import FacebookConfigurationException
from solariat_bottle.utils import facebook_driver
from ..utils.decorators import login_required
from ..utils.oauth import get_twitter_oauth_handler
from flask import session, redirect, request, abort, jsonify, render_template
from ..utils.views import get_doc_or_error
from ..db.channel.twitter import TwitterChannel
from ..db.channel.facebook import EnterpriseFacebookChannel, FacebookServiceChannel


@app.route('/twitter_profile/<channel_id>', methods=['GET'])
@login_required()
def twitter_get_profile(user, channel_id):
    try:
        channel = get_doc_or_error(TwitterChannel, channel_id)
    except :
        return jsonify(ok=False, error="Channel not found.")
    twitter_profile = get_twitter_profile(channel)
    return jsonify(ok=True, twitter_profile=twitter_profile)


@app.route('/twitter_request_token/<channel_id>', methods = ['GET'])
@login_required()
def twitter_request_token(user, channel_id):
    auth = get_twitter_oauth_handler(channel_id, callback_url='/twitter_callback/' + channel_id)

    try:
        auth.request_token = auth._get_request_token()
        url = auth._get_oauth_url('authorize')
        try:
            req = tweepy.oauth.OAuthRequest.from_token_and_callback(
                token=auth.request_token,
                http_url=url,
                parameters={'force_login': 'true'}
            )
            redirect_url = req.to_url()
        except AttributeError:
            # For tweepy==3.3
            redirect_url = auth.oauth.authorization_url(url, force_login=True)
    except Exception, ex:
        app.logger.exception('twitter_request_token')
        error_message = "Failure during twitter authentication. Possible account credentials miss configuration."
        app.logger.error("%s channel: %s, token: %s" % (error_message, channel_id, auth.access_token))
        return render_template('oauth/auth_callback.html',
                               error=True,
                               error_message=error_message), 401

    if isinstance(auth.request_token, dict):
        # tweepy == 3.3
        session['request_token'] = auth.request_token
    else:
        session['request_token'] = (
            auth.request_token.key,
            auth.request_token.secret
        )
    
    return redirect(redirect_url)

@app.route('/twitter_callback/<channel_id>', methods = ['GET'])
@login_required()
def twitter_callback(user, channel_id):

    verifier = request.args['oauth_verifier']
    request_token = session.pop('request_token', None)
    auth = get_twitter_oauth_handler(channel_id)
    if isinstance(request_token, dict):
        # tweepy==3.3
        auth.request_token = request_token
    else:
        auth.set_request_token(request_token[0], request_token[1])

    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        error_message = "Failure during twitter authentication. Possible account credentials miss configuration."
        app.logger.error("%s channel: %s, app id %s, app secret %s" % (error_message,
                                                                       channel_id,
                                                                       request_token[0],
                                                                       request_token[1]))
        return render_template('oauth/auth_callback.html',
                               error=True,
                               error_message=error_message), 401

    if hasattr(auth.access_token, 'key'):
        auth.set_access_token(auth.access_token.key, auth.access_token.secret)
    else:
        pass

    channel = get_doc_or_error(TwitterChannel, channel_id)
    if hasattr(auth.access_token, 'key'):
        channel.access_token_key = auth.access_token.key
        channel.access_token_secret = auth.access_token.secret
    else:
        channel.access_token_key = auth.access_token
        channel.access_token_secret = auth.access_token_secret

    get_twitter_profile(channel)  # cache profile data, set twitter_handle
    channel.save()  # save() triggers username tracking

    return render_template('oauth/auth_callback.html',
                           error=False,
                           channel_name=channel.title), 200

@app.route('/twitter_logout/<channel_id>', methods = ['GET'])
@login_required()
def twitter_logout(user, channel_id):

    channel = get_doc_or_error(TwitterChannel, channel_id)
    channel.access_token_key = ''
    channel.access_token_secret = ''
    channel.twitter_handle = ''
    channel.twitter_handle_data = {}
    channel.save()

    return render_template('oauth/logout_popup.html',
                           channel_name=channel.title), 200


def get_twitter_profile(channel):
    " get twitter profile "
    try:
        return channel.get_twitter_profile()
    except:
        app.logger.exception('get_twitter_profile')
    return None

@app.route('/facebook_request_token/<channel_id>', methods = ['GET'])
@login_required()
def facebook_auth_url(user, channel_id):
    " gen facebook auth url "

    auth_url = facebook.auth_url(
        app_id=app.config['FACEBOOK_APP_ID'],
        canvas_url=app.config["FACEBOOK_CALLBACK_URL"] + '/' + str(channel_id),
        perms=["manage_pages", "publish_actions", "user_events", "read_page_mailboxes", "publish_pages"]
    )
    return redirect(auth_url + '&auth_type=reauthenticate')


@app.route('/facebook/callback/<channel_id>', methods=['GET'])
@login_required()
def facebook_callback(user, channel_id):

    code = request.args.get('code')

    try:
        access_token = facebook.GraphAPI().get_access_token_from_code(
            code,
            app.config['FACEBOOK_CALLBACK_URL'] + '/' + str(channel_id),
            app.config['FACEBOOK_APP_ID'],
            app.config['FACEBOOK_APP_SECRET'])
    except facebook.GraphAPIError as e:
        app.logger.exception(e)
        return render_template('oauth/auth_callback.html',
                               error=True,
                               error_message=str(e)), 400

    channel = get_doc_or_error(EnterpriseFacebookChannel, channel_id)
    channel.user_access_token = code
    channel.facebook_access_token = access_token['access_token']

    facebook_profile = get_facebook_profile(channel)
    user_id = facebook_profile['id']
    accounts_data = get_facebook_accounts(channel, user_id)
    channel.facebook_account_ids = [acc_data['id'] for acc_data in accounts_data]
    channel.facebook_handle_id = user_id
    channel.set_facebook_me(facebook_profile)
    channel.facebook_screen_name = unicode(facebook_profile.get('name', facebook_profile.get('id')))
    channel.save()
    for service_channel in channel.get_attached_service_channels():
        service_channel.sync_with_account_channel(channel)

    return render_template('oauth/auth_callback.html',
                           error=False,
                           channel_name=channel.title), 200


@app.route('/facebook_logout/<channel_id>', methods = ['GET'])
@login_required()
def facebook_logout(user, channel_id):
    channel = get_doc_or_error(EnterpriseFacebookChannel, channel_id)
    reset_account_and_sync(channel)
    return render_template('oauth/logout_popup.html',
                           channel_name=channel.title), 200


def facebook_profile_to_json(profile):
    if not profile:
        return None
    return {'id': profile.id,
            'screen_name': profile.screen_name,
            'profile_image_url': profile.profile_image_url}

@app.route('/facebook_profile/<channel_id>', methods=['GET'])
@login_required()
def facebook_get_profile(user, channel_id):
    try:
        channel = get_doc_or_error(EnterpriseFacebookChannel, channel_id)
        facebook_profile = get_facebook_profile(channel)
    except facebook.GraphAPIError, e:
        return jsonify(ok=False, error=e.message)
    except:
        return jsonify(ok=False, error="Channel not found.")

    return jsonify(ok=True, facebook_profile=facebook_profile)


def get_facebook_accounts(channel, user_id):
    if channel.facebook_access_token:
        graph = facebook_driver.GraphAPI(channel.facebook_access_token, channel=channel)
        try:
            accounts_path = '/' + user_id + '/accounts'
            account_data = graph.get_object(accounts_path)
            return account_data.get('data', [])
        except facebook.GraphAPIError as e:
            app.logger.error(e)
    return []


def get_facebook_profile(channel):
    " get facebook profile or None "

    if channel.facebook_access_token:
        graph = facebook_driver.GraphAPI(channel.facebook_access_token, channel=channel)
        try:
            profile = graph.get_object('me')
            return profile
        except facebook.GraphAPIError as e:
            app.logger.error(e)
            if hasattr(e, 'result') and 'error' in e.result and e.result['error']['code'] == 190 and e.result['error']['error_subcode'] == 460:
                reset_account_and_sync(channel)
                raise facebook.GraphAPIError("Facebook user has changed the password, please relogin")
    return None


def reset_account_and_sync(channel):
    app.logger.info("Resetting channel" + str(channel.id))
    channel.facebook_access_token = ''
    channel.facebook_handle_id = ''
    channel.facebook_screen_name = ''
    channel.facebook_account_ids = []
    channel.save()
    for service_channel in channel.get_attached_service_channels():
        service_channel.sync_with_account_channel(channel)
        reset_fbot_cache(service_channel.id)
