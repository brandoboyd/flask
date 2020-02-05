#!/usr/bin/env python2.7

import facebook
import json

from flask import request, jsonify

from random import randint
from datetime import datetime
from solariat_bottle.app import app
from solariat_bottle.utils import facebook_driver
from solariat_bottle.utils.decorators    import login_required, channel_required
from solariat_bottle.db.channel.facebook import FacebookConfigurationException

solariat_app_id = app.config.get('FACEBOOK_APP_ID')

@app.route('/channels/<channel>/fb/groups', methods=['GET'])
@login_required()
@channel_required()
def get_fb_groups(user, channel):
    return __get_user_data_handler(channel, user, 'groups', 'all_fb_groups',
                                   'tracked_fb_groups', 'No facebook groups found')


@app.route('/channels/<channel>/fb/events', methods=['GET'])
@login_required()
@channel_required()
def get_fb_events(user, channel):
    return __get_user_data_handler(channel, user, 'events', 'all_fb_events',
                                   'tracked_fb_events', 'No facebook events found')


@app.route('/channels/<channel>/fb/pages', methods=['GET'])
@login_required()
@channel_required()
def get_fb_pages(user, channel):
    return __get_user_data_handler(channel, user, 'accounts', 'all_facebook_pages',
                                   'facebook_pages', 'No facebook pages found.')


@app.route('/channels/<channel>/fb/pages', methods=['POST'])
@login_required()
@channel_required()
def post_fb_page(user, channel):
    return __post_del_user_data_handler(channel, user, 'pages', 'add_facebook_page', 'facebook_pages')


@app.route('/channels/<channel>/fb/groups', methods=['POST'])
@login_required()
@channel_required()
def post_fb_group(user, channel):
    return __post_del_user_data_handler(channel, user, 'groups', 'track_fb_group', 'tracked_fb_group')


@app.route('/channels/<channel>/fb/events', methods=['POST'])
@login_required()
@channel_required()
def post_fb_event(user, channel):
    return __post_del_user_data_handler(channel, user, 'events', 'track_fb_event', 'tracked_fb_events')


@app.route('/channels/<channel>/fb/pages', methods=['DELETE'])
@login_required()
@channel_required()
def del_fb_page(user, channel):
    return __post_del_user_data_handler(channel, user, 'pages', 'remove_facebook_page', 'facebook_pages')


@app.route('/channels/<channel>/fb/groups', methods=['DELETE'])
@login_required()
@channel_required()
def del_fb_group(user, channel):
    return __post_del_user_data_handler(channel, user, 'groups', 'untrack_fb_group', 'tracked_fb_groups')


@app.route('/channels/<channel>/fb/events', methods=['DELETE'])
@login_required()
@channel_required()
def del_fb_event(user, channel):
    return __post_del_user_data_handler(channel, user, 'events', 'untrack_fb_event', 'tracked_fb_events')


def get_request_data():
    data = request.json or request.args
    if not data:
        try:
            data = json.loads(request.data)
        except:
            pass
    return data

def __get_channel_events(channel, user):

    tracked_pages = [page for page in channel.all_facebook_pages]
    if not tracked_pages:
        try:
            tracked_pages = facebook_driver.GraphAPI(channel.get_access_token(user), channel=channel).get_object('/me/accounts')['data']
        except facebook.GraphAPIError as e:
            app.logger.error(e)

    events = []
    for page in tracked_pages:
        token = page['access_token']
        api = facebook_driver.GraphAPI(token)
        try:
            res = api.get_object(page['id'] + '/events')
            for itm in res['data']:
                itm['page_id'] = page['id']
                itm['access_token'] = token
                itm['type'] = 'event'
            events.extend(res['data'])
        except facebook.GraphAPIError, e:
            if e.result['error']['code'] == 32:
                from solariat_bottle.settings import LOGGER
                LOGGER.warn("Page has hit rate limit: id=%s name=%s", page.get('id'), page.get('name'))
                continue
            raise e

    return events


def __get_user_data_handler(channel, user, key, field_to_check, current_field, error_message):

    def _get_fb_user_data(channel, user, key, field_to_check):

        if key != 'events':
            """ Return a list of available data by @key for  @user """
            try:
                access_token = channel.get_access_token(user)
            except FacebookConfigurationException, ex:
                return {'ok': False, 'error': ex.message}
            if not access_token:
                return {'ok': False, 'error': 'No access token for channel %s' % channel.title}

            api = facebook_driver.GraphAPI(access_token, channel=channel)
            try:
                res = api.get_object('/me/%s' % key)['data']
            except facebook.GraphAPIError as e:
                app.logger.error(e)

                #password has been changed
                if hasattr(e, 'result') and 'error' in e.result and e.result['error']['code'] == 190 and e.result['error']['error_subcode'] == 460:
                    from solariat_bottle.views.oauth import reset_account_and_sync
                    reset_account_and_sync(channel.dispatch_channel)
                    return {'ok': False, 'error': "Facebook user has changed the password, please relogin"}

                checked_value = getattr(channel, field_to_check, None)
                if checked_value is not None:
                    return {'ok': True, 'data': checked_value}
                return {'ok': False, 'error': str(e)}
        else:

            try:
                res = __get_channel_events(channel, user)
            except Exception, ex:
                from solariat_bottle.settings import LOGGER
                unique_timestamp = str(datetime.now()) + str(randint(0, 10000))
                LOGGER.error(unique_timestamp + " - Facebook communication error: " + str(ex))
                return {'ok': False, 'error': ex.message}

        field_to_update = 'set__%s'%field_to_check
        channel.update(**{field_to_update:res})
        return {'ok': True, 'data': res}

    if request.args.get('all', None):
        res = _get_fb_user_data(channel, user, key, field_to_check)
        if res:
            res['current'] = getattr(channel, current_field, None)
        else:
            res = {'ok': False, 'error' : error_message}
    else:
        res = {'ok': True, 'data': getattr(channel, current_field, None)}

    return jsonify(res)


def __post_del_user_data_handler(channel, user, key, handler, data_field):
    data = get_request_data()
    try:
        item = data[key] if isinstance(data[key], dict) else json.loads(data[key])
        getattr(channel, handler)(item, user)
    except Exception, e:
        res = {'ok': False, 'error': str(e)}
    else:
        res = {'ok': True, 'data': getattr(channel, data_field, None)}

    return jsonify(res)

