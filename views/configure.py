#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
UI for Channels

"""
import math
from operator import itemgetter
from collections import defaultdict

import datetime
from bson import DBRef
from pymongo.errors import DuplicateKeyError
import tweepy
from flask import (jsonify, request, abort, redirect, session)

from solariat_bottle.db.account import Account, Package
from ..app import app, AppException
from solariat.db import fields
from ..utils.decorators import login_required
from ..db.channel.base import (Channel, CompoundChannel)
from ..db.account import AccountEvent
from ..db.channel.voc import VOCServiceChannel
from ..db.channel.twitter import (TwitterChannel, EnterpriseTwitterChannel,
                                  UserTrackingChannel, KeywordTrackingChannel,
                                  FollowerTrackingChannel, FollowerTrackingStatus,
                                  TwitterServiceChannel, ServiceChannel)
from ..db.channel.facebook import EnterpriseFacebookChannel, FacebookServiceChannel

# For now import at least so we register to metaregistry
from ..db.channel.chat import ChatServiceChannel
from ..db.channel.email import EmailServiceChannel
from ..db.channel.web_click import WebClickChannel
from ..db.channel.faq import FAQChannel
from ..db.events.event_type import StaticEventType

from ..utils.oauth import get_twitter_oauth_handler

from ..db.user import User
from solariat_bottle.utils.views import parse_account

CHANNEL_TYPE_MAP = {
    'forum': Channel,
    'twitter': TwitterChannel,
    'enterprisetwitter': EnterpriseTwitterChannel,
    'enterprisefacebook': EnterpriseFacebookChannel,
    'usertracking': UserTrackingChannel,
    'keywordtracking': KeywordTrackingChannel,
    'compound': CompoundChannel,
    'followertracking': FollowerTrackingChannel,
    'facebookservice' : FacebookServiceChannel,
    'chatservice' : ChatServiceChannel,
    'service': TwitterServiceChannel,
    'voc': VOCServiceChannel,
    'emailservice': EmailServiceChannel,
    'webclick': WebClickChannel,
    'faq': FAQChannel
}

CHANNEL_TYPES_LIST = [
    { 'key'     : 'enterprisetwitter',
      'title'   : 'Twitter : Account',
      'display' : 'Account'
    },

    { 'key'     : 'service',
      'title'   : 'Twitter : Service',
      'display' : 'Service'
    },

#     { 'key'     : 'usertracking',
#       'title'   : 'Twitter : Users',
#       'display' : 'Users'
#     },
#
#     { 'key'     : 'followertracking',
#       'title'   : 'Twitter : Followers',
#       'display' : 'Followers'},
#
#     { 'key'     : 'keywordtracking',
#       'title'   : 'Twitter : Topics',
#       'display' : 'Topics'
#     },
#     { 'key'     : 'compound',
#       'title'   : 'Twitter : Combination',
#       'display' : 'Combination'},

    { 'key'     : 'enterprisefacebook',
      'title'   : 'Facebook : Account',
      'display' : 'Account'
    },


    { 'key'     : 'facebookservice',
      'title'   : 'Facebook : Service',
      'display' : 'Service'
    },

    { 'key'     : 'voc',
      'title'   : 'Voice of the Customer',
      'display' : 'Service'
    },
    { 'key'     : 'emailservice',
      'title'   : 'Email: Service',
      'display' : 'Service'
    },
    { 'key'     : 'chatservice',
      'title'   : 'Chat: Service',
      'display' : 'Service'
    },
    {'key'      : 'webclick',
     'title'    : 'WebClicks',
     'display'  : 'Service'},
    {'key'      : 'faq',
     'title'    : 'FAQ',
     'display'  : 'Service'}
]

# users with edit access to account will see this list
CHANNEL_TYPES_LIST_ADMINS = [
    { 'key'     : 'enterprisetwitter',
      'title'   : 'Twitter : Account',
      'display' : 'Account'
    },

    { 'key'     : 'service',
      'title'   : 'Twitter : Service',
      'display' : 'Service'
    },

    { 'key'     : 'enterprisefacebook',
      'title'   : 'Facebook : Account',
      'display' : 'Fans'
    },

    { 'key'     : 'facebookservice',
      'title'   : 'Facebook : Service',
      'display' : 'Service'
    },

    { 'key'     : 'voc',
      'title'   : 'Voice of the Customer',
      'display' : 'Service'
    },

    {'key'      : 'webclick',
     'title'    : 'WebClicks',
     'display'  : 'Service'},

    {'key'      : 'faq',
     'title'    : 'FAQ',
     'display'  : 'Service'}
]


def _user_to_ui_select(user):
    return {"id": str(user.id),
            "text": user.email}


@app.route('/configure/channel_types/json', methods=['GET'])
@login_required
def list_channel_types(user):
    from copy import deepcopy
    from solariat_bottle.db.dynamic_channel import ChannelType
    channel_type_list = []
    if user.is_staff:
        channel_type_list = deepcopy(CHANNEL_TYPES_LIST)
    elif user.is_admin:
        if user.account.selected_app == 'GSE':
            # only show twitter and facebook channels
            channel_type_list = [c for c in CHANNEL_TYPES_LIST_ADMINS
                    if 'twitter'in c['title'].lower() or 'facebook' in c['title'].lower()]
        else:
            channel_type_list = deepcopy(CHANNEL_TYPES_LIST_ADMINS)
    for ct in ChannelType.objects.find(account=user.account.id):
        channel_type_list.append(dict(display=ct.name,
                                      key=str(ct.id),
                                      title=ct.name,
                                      schema_fields=ct.schema))
    return jsonify(ok=True, list=channel_type_list)


@app.route('/configure/channels/json', methods=['POST'])
@login_required
def create_channel(user):
    from copy import deepcopy
    from solariat_bottle.db.dynamic_channel import ChannelType

    data = request.json
    if data is None:
        raise abort(415)

    # import pdb; pdb.set_trace()
    if 'type' not in data:
        return jsonify(ok=False,
                       error='type should be provided')

    channel_type_map = deepcopy(CHANNEL_TYPE_MAP)
    custom_channel_types = {str(ct.id): ct for ct in ChannelType.objects.find(account=user.account)}
    channel_type_map.update({ct_id: ct.get_channel_class()
                            for ct_id, ct in custom_channel_types.iteritems()})

    if data['type'] not in channel_type_map:
        return jsonify(ok=False, error='unknown channel type')

    #if not (user.is_staff or user.is_admin and user.current_account.account_type != 'GSE'):
    # above line simplifies to:
    #if not user.is_staff and (not user.is_admin or user.current_account.account_type == 'GSE'):
    # which would mean admins in GSE are not allowed, this is going to be changed below,
    # ie. admins will be allowed to create channels whatsoever is the account type

    if not (user.is_staff or user.is_admin):
        return jsonify(ok=False, error='Only staff and admin users can create channels.')

    account = parse_account(user, data)
    if account.is_locked:
        error = "Account is locked, nobody can create the channel."
        return jsonify(ok=False, error=error)

    if data['type'] in custom_channel_types:
        channel_type = custom_channel_types[data['type']]
        data['channel_type_id'] = channel_type.id

    allow_params = ('title', 'description', 'queue_endpoint_attached','history_time_period',
                    'auto_refresh_followers', 'auto_refresh_friends', 'skip_retweets',
                    'channel_type_id')
    channel_params = {}
    for _key in allow_params:
        if _key in data:
            channel_params[_key] = data[_key]

    channel_params['account'] = account

    channel_class = channel_type_map[data['type']]
    try:
        channel = channel_class.objects.create_by_user(
                      user, **channel_params)
    except fields.ValidationError as e:
        return jsonify(ok=False, error=str(e))

    AccountEvent.create_by_user(user=user,
                                change='Channel create',
                                event_data={'new_data': channel.to_dict()})

    return jsonify(ok=True, id=str(channel.id), item=get_channel_item(channel))

def get_channel_item(channel):
    from solariat_bottle.db.dynamic_channel import DynamicEventsImporterChannel
    special_account_options = channel.account.selected_app in ['GSE'] and channel.is_service
    is_dynamic = isinstance(channel, DynamicEventsImporterChannel)

    item = {
        'id': str(channel.id),
        'title': channel.title,
        'platform': channel.platform,
        'is_compound': channel.is_compound,
        'is_service': channel.is_service,
        'is_dispatchable': channel.is_dispatchable,
        'is_dynamic': is_dynamic,
        'status': channel.status,
        'intention_types': channel.intention_types,
        'moderated_relevance_threshold': channel.moderated_relevance_threshold,
        'moderated_intention_threshold': channel.moderated_intention_threshold,
        'auto_reply_intention_threshold': channel.auto_reply_intention_threshold,
        'auto_reply_relevance_threshold':channel.auto_reply_relevance_threshold,
        'description':channel.description,
        'adaptive_learning_enabled':channel.adaptive_learning_enabled,
        'type': channel.__class__.__name__,
        'account':channel.account and channel.account.name,
        'account_id':channel.account and str(channel.account.id),

        'facebook_page_ids': channel.facebook_page_ids if hasattr(channel, 'facebook_page_ids') else None,
        'facebook_access_token':channel.facebook_access_token if hasattr(channel, 'facebook_access_token') else None,

        'access_token_key': channel.access_token_key if hasattr(channel, 'access_token_key') else None,
        'access_token_secret': channel.access_token_secret if hasattr(channel, 'access_token_secret') else None,

        'twitter_usernames' : channel.twitter_usernames if hasattr(channel, 'twitter_usernames') else None,
        'twitter_handle' : channel.twitter_handle if hasattr(channel, 'twitter_handle') else None,
        'tracking_mode' : channel.tracking_mode if hasattr(channel, 'tracking_mode') else None,

        'bitly_access_token':channel.bitly_access_token,
        'bitly_login':channel.bitly_login,
        'remove_personal':channel.remove_personal,
        'posts_tracking_enabled':channel.posts_tracking_enabled,

        'view': {
            'special_account_options': special_account_options
        }
    }
    if hasattr(channel, 'skip_retweets'):
        item.update({'skip_retweets': channel.skip_retweets})

    if special_account_options:
        item.update({
            'auto_refresh_followers': channel.auto_refresh_followers
            if hasattr(channel, 'auto_refresh_followers') else -1,
            'history_time_period': channel.history_time_period
            if hasattr(channel, 'history_time_period') else None,
            'auto_refresh_friends': channel.auto_refresh_friends
            if hasattr(channel, 'auto_refresh_friends') else -1
        })

    if channel.is_compound:
        item['primitive_channels'] = [get_channel_item(ch) for ch in channel.channels]

    if channel.is_dispatchable:
        item['review_outbound'] = channel.review_outbound

    if channel.is_service:
        item['inbound_channel'] = get_channel_item(channel.inbound_channel)
        item['outbound_channel'] = get_channel_item(channel.outbound_channel)
        item['dispatch_channel'] = channel.dispatch_channel and str(channel.dispatch_channel.id)
        if isinstance(channel, TwitterServiceChannel):
            item['grouping_timeout'] = channel.grouping_timeout
            item['grouping_enabled'] = channel.grouping_enabled
    if is_dynamic:
        item['channel_type_id'] = str(channel.channel_type_id)
        for f in channel.__class__.schema_fields:
            item[f.name] = getattr(channel, f.name)

    return item


@app.route('/select_strategy', methods=['POST', 'GET'])
@login_required
def select_strategy(user):
    if request.method == "GET":
        return jsonify(ok=True, item=user.selected_strategy)
    elif request.method == "POST":
        data = request.json
        user.selected_strategy = data['strategy']
        user.save()
        return jsonify(ok=True)


@app.route('/configure/account_update/json', methods=['POST', 'GET'])
@login_required
def update_account(user):
    if request.method == "GET":
        account_id = request.args.get('accountId', None)
        if account_id is None:
            return jsonify(ok=False, error="Need an account ID.")

        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return jsonify(ok=False, error="No account with id=%s found in database." % account_id)

        if not account.can_edit(user):
            return jsonify(ok=False,
                           error="User has no permission to edit account.")

        if not account.can_view(user):
            return jsonify(ok=False,
                           error="User has no permission to this account.")

        pricing_package = account.package
        if pricing_package is not None:
            pricing_package = pricing_package.name

        data = {
                    "accountId"     : str(account.id),
                    "accountName"   : account.name,
                    "accountType"   : account.account_type,
                    "pricingPackage": pricing_package,
                    "hasoAuth"      : account.has_oauth_token(),
                }
    elif request.method == "POST":
        data = request.json
        account_id = data.get('accountId', None)
        if account_id is None:
            return jsonify(ok=False, error="Need an account ID.")

        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return jsonify(ok=False, error="No account with id=%s found in database." % account_id)
        old_account_data = account.to_dict()

        if not account.can_edit(user):
            return jsonify(ok=False,
                           error="User has no permission to edit account.")

        account_name = data.get('accountName', None)
        if account_name is None:
            return jsonify(ok=False, error="Need a name for the account.")

        pricing_package = data.get("pricingPackage", None)
        if pricing_package is not None:
            if pricing_package == 'None':
                account.package = None
            else:
                try:
                    pricing_package = Package.objects.get(name=pricing_package)
                except Package.DoesNotExist:
                    return jsonify(ok=False, error="Unsupported pricing package: {}".format(pricing_package))
                account.package = pricing_package

        account.name = account_name
        account.account_type = data.get('accountType', None)
        account.save()
        new_account_data = account.to_dict()
        AccountEvent.create_by_user(user=user,
                                    change='Account edit',
                                    old_data=old_account_data,
                                    new_data=new_account_data)
        data = {}
    return jsonify(ok=True, data=data)


# TODO: to clean, deprecated
# @app.route('/configure/<platform>/event_types', methods=['GET'])
# @login_required
# def list_event_types(user, platform):
#     if not platform:
#         return jsonify(ok=False, error='No information for channel_type=%s' % platform)
#
#     event_types = StaticEventType.objects.find_by_user(user, platform=platform)
#     return jsonify(ok=True, list=[e_t.to_dict() for e_t in event_types])


@app.route('/configure/channel_update/json', methods=['POST', 'GET'])
@login_required
def update_channel(user):
    from solariat_bottle.db.dynamic_channel import DynamicEventsImporterChannel
    if request.method == 'POST':
        data = request.json
        if data is None:
            raise abort(415)

        if 'channel_id' not in data:
            return jsonify(ok=False, error='channel_id should be provided')

        try:
            channel = Channel.objects.find_one_by_user(user, id=data['channel_id'])
        except fields.ValidationError as e:
            return jsonify(ok=False, error='wrong id')
        if not channel:
            return jsonify(ok=False, error='wrong id')

        if channel.account.is_locked:
            error = "Account is locked, nobody can update the channel."
            return jsonify(ok=False, error=error)

        old_channel_data = channel.to_dict()
        allow_params = (
            'twitter_handle',
            'description',
            'title',
            'moderated_relevance_threshold',
            'auto_reply_relevance_threshold',
            'moderated_intention_threshold',
            'auto_reply_intention_threshold',
            'adaptive_learning_enabled',
            'primitive_channels',
            'inbound_channels',
            'outbound_channels',
            'tracking_mode',
            'review_outbound',
            'history_time_period',
            'auto_refresh_followers',
            'skip_retweets',
            'auto_refresh_friends',
            'dispatch_channel',
            'remove_personal',
            'posts_tracking_enabled',
            'grouping_timeout',
            'grouping_enabled'
        )

        if isinstance(channel, DynamicEventsImporterChannel):
            allow_params += tuple([f.name for f in channel.__class__.schema_fields])

        channel_params = {}
        for _key in allow_params:
            if _key in data:
                channel_params[_key] = data[_key]

        account = parse_account(user, data)
        # This can change the account when updating other account's channel
        #channel_params['account'] = account

        if 'twitter_handle' in channel_params and\
           channel_params['twitter_handle'] and\
           channel_params['twitter_handle'][0] == '@':
            channel_params['twitter_handle'] = channel_params['twitter_handle'][1:]

        #process compound channel update
        if channel.is_compound:
            if 'primitive_channels' in channel_params:
                channel_ids = channel_params.pop('primitive_channels')
                channel_params['channels'] = list(Channel.objects.find_by_user(user, id__in=channel_ids))

        if channel.is_service:
            if 'inbound_channels' in channel_params:
                channel_ids = channel_params.pop('inbound_channels')
                channel_params['inbound'] = map(itemgetter('id'), Channel.objects.find_by_user(user, id__in=channel_ids))

            if 'outbound_channels' in channel_params:
                channel_ids = channel_params.pop('outbound_channels')
                channel_params['outbound'] = map(itemgetter('id'), Channel.objects.find_by_user(user, id__in=channel_ids))

            if 'dispatch_channel' in channel_params:
                dispatch_channel = Channel.objects.find_one_by_user(user, id=channel_params.pop('dispatch_channel'))
                channel_params['dispatch_channel'] = dispatch_channel

            if 'posts_tracking_enabled' in channel_params:
                if channel_params['posts_tracking_enabled']:
                    from solariat_bottle import settings
                    delay = getattr(settings, 'POST_TRACKING_AUTO_SHUTDOWN', 15)
                    channel.posts_tracking_disable_at = datetime.datetime.now() + datetime.timedelta(minutes=delay)
                    app.logger.info("Post tracking will be disabled in %s minutes".format(delay))
            if 'grouping_timeout' in channel_params and not isinstance(channel, TwitterServiceChannel):
                channel_params.pop('grouping_timeout')
                channel_params.pop('grouping_enabled', None)

        if channel_params:
            try:
                for (name, value) in channel_params.items():
                    if name == 'title' and channel.title != value and Channel.objects(account=channel.account, title=value).limit(1).count():
                        raise fields.ValidationError, "Title must be unique for the account"
                    setattr(channel, name, value)
                channel.save_by_user(user)
            except fields.ValidationError as e:
                app.logger.error("Could not update channel", exc_info=True)
                return jsonify(ok=False, error=str(e))
        new_channel_data = channel.to_dict()
        AccountEvent.create_by_user(user=user,
                                    change='Channel edit',
                                    old_data=old_channel_data,
                                    new_data=new_channel_data)
        return jsonify(ok=True, item=get_channel_item(channel))

    if request.method == 'GET':

        if 'channel_id' not in request.args:
            return jsonify(ok=False, error='channel_id should be provided')
        try:
            channel = Channel.objects.find_one_by_user(
                user, id=request.args['channel_id'])
        except fields.ValidationError as e:
            return jsonify(ok=False, error='wrong id')
        if not channel:
            return jsonify(ok=False, error='wrong id')

        return jsonify(ok=True, item=get_channel_item(channel))


@app.route('/configure/outbound_channels/json', methods=['GET', 'POST'])
@login_required
def configure_outbound_channels(user):
    def _channel_json(channel):
        if channel:
            return {'id': str(channel.id),
                    'title': channel.title,
                    'status': channel.status,
                    'type': channel.type,
                    'description': channel.description,
                    'platform': channel.platform,
                    'account': channel.account and channel.account.name,
                    'account_id': channel.account and str(channel.account.id)
                    }

    from ..db.channel.base import PLATFORM_MAP
    platforms = PLATFORM_MAP.keys()

    profile = user
    if request.method == 'GET':
        if 'account_id' in request.args and request.args.get('account_id', 'undefined') != 'undefined':
            account = parse_account(user, request.args)
            profile = account

        selected_channels = {platform: _channel_json(profile.get_outbound_channel(platform)) for platform in platforms}
        available_channels = Channel.objects.find_by_user(user)
        available_channels_json = [_channel_json(ch) for ch in available_channels if ch.is_dispatchable and not ch.is_inbound]

        grouped_channels = defaultdict(list)
        for channel in available_channels_json:
            grouped_channels[channel['platform']].append(channel)
            selected_channel = selected_channels[channel['platform']]
            if selected_channel and selected_channel['id'] == channel['id']:
                channel['selected'] = True

        return jsonify(ok=True, data=grouped_channels)

    elif request.method == 'POST':
        data = request.json
        # data = {oc: {platform: channel_id, ...},
        #         account_id: 'account_id'} - account is optional
        account_id = data.get('account_id', None)
        if account_id:
            profile = Account.objects.get(id=account_id)
        data = data.get('oc')

        # validate posted data
        cleaned_data = dict((platform, data.get(platform)) for platform in platforms)
        channel_ids = [id for id in cleaned_data.values() if id and id.strip()]
        id_platform_map = dict((v, k) for k, v in cleaned_data.iteritems())
        try:
            channels = list(Channel.objects.find_by_user(user, id__in=channel_ids))
            #all channels must exist and be accessible by user
            assert(len(channels) == len(channel_ids))
            #all channels should be dispatchable
            assert(all([ch.is_dispatchable and ch.platform == id_platform_map.get(str(ch.id)) for ch in channels]))
        except:
            return jsonify(ok=False, error='Invalid channels')

        profile.outbound_channels = cleaned_data
        profile.save()
        return jsonify(ok=True)

    return jsonify(ok=False, error='Unknown action')


def _set_user_account(setter_user, target_user, account_id, perms=None, response_func=jsonify):
    """
    Set a new account for a target user. Action is initiated by a setter user.

    :param setter_user: The user that initiated the action to change another users
            account. The `setter_user` must have write access for the given account
            in order for the operation to be valid.
    :param target_user: The user for which the new account will be set.
    :param account_id: The account id that will be set as a current one for the `target_user`.
    :param perms: The permissions that the user will have on the new account. If this is
            None, just ignore and stick with whatever permissions the user had before.
    :param response_func: A function which will be called on the result of the method.
            Defaults to a funtion that will return a JSON encoded response.

    :returns: calls `response_func` on the result.
    """
    app.logger.debug('setter_user=%r, target_user=%r, account_id=%r, perms=%r', setter_user, target_user, account_id, perms)
    if account_id:
        try:
            account = Account.objects.get(id=account_id)
            if not account.can_view(setter_user):
                return response_func(ok=False,
                    error="User has no permission to this account.")
            if perms is not None:
                if account.has_perm(setter_user):
                    account.add_perm(target_user)
            target_user.current_account = account
            return response_func(ok=True)
        except Account.DoesNotExist:
            return response_func(ok=False, error='Unknown Account %s' % account_id)
    else:
        return response_func(ok=False, error='No account provided.')


def tokenize_user_search_query(search_query):
    F = User.F
    words_bag = search_query.split()

    if len(words_bag) == 1:
        query = {'$or': [
            {F.first_name: {'$regex': search_query, '$options': 'i'}},
            {F.last_name:  {'$regex': search_query, '$options': 'i'}},
            {F.email:      {'$regex': search_query, '$options': 'i'}},
        ]}
    else:
        search_query = '|'.join(words_bag)
        query = {
            F.first_name: {'$regex': search_query, '$options': 'i'},
            F.last_name:  {'$regex': search_query, '$options': 'i'},
        }

    return query


@app.route('/configure/account/userslist', methods=['GET'])
@login_required
def users_with_account(user):
    """
    Return a list of users which have the current account as passed by
    and 'account' parameter.
    """
    from ..views.account import _json_account
    account = request.args.get('account', None)
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    search_query = request.args.get('searchQuery', '').strip()

    if account is None:
        return jsonify(ok=False, error=u"Require account ID for which we want users.")

    try:
        account = Account.objects.get(id=account)
    except Account.DoesNotExist:
        return jsonify(ok=False, error='Unknown Account %s' % account)

    query = {
            User.F.account: DBRef('Account', account.id)
    }
    if search_query:
        query.update(tokenize_user_search_query(search_query))

    users_raw = list(User.objects.coll.find(query, {'_id': 1}))
    users_ids = [each['_id'] for each in users_raw]

    users = list(User.objects.find(id__in=users_ids).sort(id=1))
    _perms = [user.perms(u) for u in users]

    total_items = len(filter(bool, _perms))
    pages = int(math.ceil(total_items/float(limit)))

    users_perm = []
    skip_offset_index = 0

    # pre-compute common account details only once that are slow and pass them as cache to _json_account
    common_account_details = {
            'admins': [admin_user for admin_user in account.admins if not admin_user.is_staff],
            'users_count': len([u for u in account.get_users() if not u.is_system]),
            'all_users_count': len([u for u in account.get_all_users() if not u.is_system]),
    }

    for u, _p in zip(users, _perms):
        if _p:

            if skip_offset_index < offset:
                skip_offset_index += 1
                continue

            u_p = dict(email=u.email,
                       name='%s %s' % (u.first_name or '', u.last_name or ''),
                       id=str(u.id),
                       self=True if u.id == user.id else False,
                       main_role=u.main_role,
                       can_contact=u.id != user.id,
                       full_roles=u.roles,
                       perms=_p,
                       currentAccount=_json_account(u.current_account, u, cache=common_account_details))
            users_perm.append(u_p)

            if len(users_perm) == limit:
                break

    return jsonify(ok=True, users=users_perm, total_items=total_items, pages=pages)


@app.route('/configure/account/json', methods=['GET', 'POST'])
@login_required
def configure_current_account(user):
    """
    Handle the current account of the logged in user.
    In case of GET just return details about the account.
    In case of POST we can set the current account for some
    other users.
    """
    if request.method == 'GET':
        from .account import account_details_handler
        return account_details_handler(user)
    elif request.method == 'POST':
        #Set current account
        data = request.json or {}
        account_id = data.get('account_id', None)
        email = data.get('email', None)
        perms = data.get('perms', 'r')

        target_user = user

        # If we are a super user, then we may be setting the account for another
        if user.is_superuser:
            #Superuser can set the current account for other users
            if email:
                try:
                    from ..db.user import User
                    target_user = User.objects.get(email=email)
                except User.DoesNotExist:
                    return jsonify(ok=False, error=u"User '%s' does not exist." % email)
        return _set_user_account(user, target_user, account_id, perms, response_func=jsonify)


@app.route('/configure/accounts/remove', methods=['POST'])
@login_required
def remove_user_account(user):
    """
    Expects a user id for which (in case our permissions on account
    are higher) then we can remove that account from the user.
    """
    email = request.json.get('email', None)
    if email is None:
        return jsonify(ok=False, error=u"Need a valid user email to remove.")

    try:
        from ..db.user import User
        target_user = User.objects.get(email=email)
    except User.DoesNotExist:
        return jsonify(ok=False, error=u"User '%s' does not exist." % email)

    account = target_user.account

    if user.is_superuser or (account.can_edit(user) and not account.can_edit(target_user)):
        account.del_perm(target_user)
        return jsonify(ok=True)
    else:
        return jsonify(ok=False, error=u"You do not have permissions to remove that account.")


@app.route('/configure/accounts/', methods=['GET'])
@login_required
def configure_accounts_handler(user):
    return redirect('/configure#/accounts/')


@app.route('/accounts/switch/<account_id>', methods=['GET'])
@login_required
def accounts_switch_handler(user, account_id):
    def _response(ok, error=None, result=None):
        if not ok:
            from flask import flash
            flash(result)
        # return redirect(request.referrer or '/inbound')
        return redirect('/configure')
    return _set_user_account(user, user, account_id, response_func=_response)


@app.route('/account_app/switch/<selected_app>', methods=['GET'])
@login_required
def account_apps_switch_handler(user, selected_app):

    all_sections = [
        ('/dashboard',      'dashboard'),
        ('/reports',        'reports'),
        ('/analytics',      'analytics'),
        ('/inbox',          'inbox'),
        ('/voc',            'voc'),
        ('/omni/customers', 'customers'),
        ('/omni/agents',    'agents'),
        ('/omni/journeys',  'journeys'),
        ('/predictors',     'predictors'),
    ]
    sections_map = dict((s[1], s[0]) for s in all_sections)
    _url_for = sections_map.get

    def _response(error=None):
        if error:
            from flask import flash
            flash(error)

        print user.account.selected_app,  user.account.available_apps.keys()

        if user.account.selected_app == 'GSE':
            return redirect('/configure#/channels')

        try:
            available_sections = user.account.available_apps[user.account.selected_app]
        except KeyError:
            return ("You have no access to '%s' app. "
                    "Go back and refresh page to load apps you have access to." % user.account.selected_app)

        referer = request.referrer or '/inbound'

        if any(_url_for(section) in referer for section in available_sections):
            redirect_to = referer
        else:
            if available_sections:
                #redirect_to = _url_for(available_sections[0])
                redirect_to = '/configure#/channels'
            else:
                redirect_to = '/configure#/channels'
        return redirect(redirect_to)

    if selected_app:
        # GSE only users can be given access to new app and they should be able to switch to new app
        # so remove following 2 lines
        #if user.account.selected_app == 'GSE' and not user.is_staff:
        #    return _response()
        try:
            user.account.selected_app = selected_app
            user.account.save()
            return _response()
        except Account.DoesNotExist:
            return _response(error='Unknown app %s' % selected_app)
    else:
        return _response(error='No selected app provided.')


@app.route('/configure/users/json', methods=['GET', 'POST'])
@login_required
def configure_users_handler(user):

    def _orphan_accounts_json(user, nr_of_orphans):
        from ..views.account import _no_account
        NO_ACCOUNT = _no_account(nr_of_orphans)
        return {'email': u.email,
                'currentAccount': NO_ACCOUNT,
                'accounts' : [NO_ACCOUNT]}

    if request.args.get('orphaned') and user.is_superuser:
        from ..db.user import User
        #Return the list of users without assigned account.
        users_without_account = User.objects.find(account=None)
        nr_orphans = len(users_without_account)
        users_data = [_orphan_accounts_json(u, nr_orphans) for u in users_without_account]
        return jsonify(ok=True, result=users_data)
    else:
        return jsonify(ok=False)

@app.route('/configure/agents/json', methods=['GET'])
@login_required
def get_agents_list(user):
    def _get_service_channel(ch):
        if isinstance(ch, ServiceChannel):
            return ch
        try:
            return ServiceChannel.objects.get(id=ch.parent_channel)
        except ServiceChannel.DoesNotExist:
            return None
    data = request.args
    try:
        assert 'channel_id' in data, "No channel id provided."
        channel_id = data.get('channel_id')
        channel = Channel.objects.get_by_user(user, id=channel_id)
        assert hasattr(channel, 'account'), "No account information available for %s" % channel_id

        # Case where the user is not an admin for the account. Only show their own data
        sc = _get_service_channel(channel)
        if not (user.is_analyst or channel.account.can_edit(user)):
            agents = [user]
        else:
            agents = sc and sc.agents or []
            #agents = [a for a in agents if sc and sc.can_view(a)]   # Filter out agents which no longer have perms
            #agents = channel.account.get_all_users()

        agents = [a for a in agents if a.agent_id != 0]  # filter out common users, keep only agents
        results = []

        for agent in agents:
            results.append(dict(agent_id=str(agent.id), display_name=agent.display_agent,
                                can_view=user.account in agent.available_accounts))
    except AssertionError, e:
        return jsonify(ok=False, error=str(e))
    except Channel.DoesNotExist:
        return jsonify(ok=False, error="Channel %s not available" % channel_id)

    return jsonify(ok=True, list=results)


def user_to_dict(u):
    profile = u.user_profile
    return {
        'id': str(u.id),
        'email': u.email,
        'social_profile_platform': profile.platform if profile else '',
        'social_profile_screen_name': profile.screen_name if profile else '',
        'signature': u._signature,
        'external_id': u.external_id,
    }


@app.route('/user/json', methods=['GET', 'POST'])
@login_required
def user_configure_handler(user):
    from ..db.user import User
    from ..db.user_profiles.user_profile import UserProfile

    u = user
    if request.method == 'GET':
        email = request.args.get('email', '').strip()
        if email:
            try:
                u = User.objects.get(email=email)
            except User.DoesNotExist:
                return jsonify(ok=False, error=u"User not found: %s" % email)

    elif request.method == 'POST':
        data = request.json
        # allowed_fields = ('social_profile_platform',
        #                   'social_profile_screen_name',
        #                   'signature')
        user_id = data.get('id')
        try:
            u = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return jsonify(ok=False, error=u"User not found: %s" % user_id)

        platform = data.get('social_profile_platform')
        screen_name = data.get('social_profile_screen_name')
        signature = data.get('signature', '')
        email = data.get('email')
        external_id = data.get('external_id')

        if platform and screen_name:
            up = UserProfile.objects.upsert(platform, dict(screen_name=screen_name))
            u.user_profile = up
        if signature:
            account = u.account
            for agent in account.get_users():
                if agent.signature and agent.id != u.id and (
                        signature.lower() in agent.signature.lower()
                        or agent.signature.lower() in signature.lower()):
                    return jsonify(ok=False,
                                   error=u"Signature intersects with agent %s" % agent.email)
        u.signature = signature

        if external_id and external_id != u.external_id:
            try:
                User.objects.get(external_id=external_id)
            except User.DoesNotExist:
                u.external_id = external_id
            else:
                return jsonify(ok=False, error=u"This external ID is used by another user.")

        # do not allow empty external IDs
        if external_id.strip() == '':
            return jsonify(ok=False, error=u"Some external ID needs to be specified.")

        if email and email.lower() != u.email.lower():
            try:
                User.objects.get(email=email.lower())
            except User.DoesNotExist:
                u.email = email.lower()
            else:
                return jsonify(ok=False, error=u"This email is already in use")

        try:
            u.save()
        except DuplicateKeyError:
            return jsonify(ok=False, error=u"This email is already in use")
        except Exception, e:
            app.logger.error(u'Error in /user/json %s', e)
            return jsonify(ok=False, error="Save error")

    return jsonify(ok=True, user=user_to_dict(u))


@app.route('/users/lookup', methods=['GET'])
@login_required
def users_lookup(user):
    try:
        account = user.current_account
        assert(account)
    except (AssertionError, Account.DoesNotExist):
        return jsonify(ok=False, error="Account not found")

    data = request.json or request.args or {}

    users = account.get_all_users()
    term = data.get('term', None)

    filtered_users = []
    if term:
        def _lookup(u):
            return term.lower() in u.email.lower()

        filtered_users = filter(_lookup, users)

    if not filtered_users:
        return jsonify(ok=True, users=[{'id':term, 'text':term}])

    return jsonify(ok=True, users=map(_user_to_ui_select, filtered_users))


@app.route('/configure/outbound_review/<action>/json', methods=['POST'])
@login_required
def outbound_review_handler(user, action):
    data = request.json or {}

    channel_id = data.get('channel_id')
    users = data.get('users', [])

    if action == 'lookup':
        return users_lookup()

    try:
        channel = Channel.objects.get_by_user(user, id=channel_id)
    except Channel.DoesNotExist:
        return jsonify(ok=False, error="Channel not found")

    if not channel.is_dispatchable:
        return jsonify(ok=False, error="Channel is not outbound")

    if not channel.can_edit(user):
        return jsonify(ok=False, error="User has no permission to edit channel")

    review_team = channel.get_review_team()
    review_team.add_user(user, 'rw')  #ensure user has permission to edit group

    if action == 'fetch_users':
        #show review team members
        users = review_team.members

        return jsonify(ok=True, users=map(_user_to_ui_select, users))

    elif action in ['add_users', 'del_users']:
        add = action == 'add_users'
        #manage review team
        users_perms = []
        for u in users:
            users_perms.append({"email": u, "perm": "r" if add else 'd', "is_new": add})

        from ..utils.acl import share_object_by_user
        ok, result = share_object_by_user(user, 'group_manual', [review_team], users_perms, send_email=True)

        return jsonify(ok=ok, result=result)
    else:
        return jsonify(ok=False, error="unknown action")


@app.route('/progress/json', methods=['GET'])
@login_required
def channel_sync_progress(user):

    if 'channel_id' not in request.args:
        return jsonify(ok=False, error='channel_id should be provided')

    channel = get_doc_or_error(Channel, request.args['channel_id'])

    if isinstance(channel, FollowerTrackingChannel):

        followers_count = 0
        followers_synced = 0
        sync_status = set()

        for fts in FollowerTrackingStatus.objects.find(channel=channel.id):
            followers_count += fts.followers_count
            followers_synced += fts.followers_synced
            sync_status.add(fts.sync_status)

        item={'followers_count': followers_count,
             'followers_synced': followers_synced}

        if 'sync' in sync_status:
            item['sync_status'] = 'sync'
        else:
            item['sync_status'] = 'idle'

        return jsonify(ok=True, item=item)

    else:
        return jsonify(ok=False, error='wrong channel type %s' % channel.__class__.__name__)

@app.route('/twitter/users', methods=['GET'])
@login_required
def twitter_users(user):

    if 'twitter_handle' not in request.args:
        return jsonify(ok=False, error='twitter_handle should be provided')

    try:
        auth = get_twitter_oauth_handler()
        api = tweepy.API(auth)
        user = api.get_user(request.args['twitter_handle'])
    except AppException:
        return jsonify(ok=False, error="Sorry - we had trouble accessing the Twitter API. Please contact support.")
    except tweepy.error.TweepError, err:
        return jsonify(ok=False, error=err[0])

    # add to UserProfile
    from solariat_bottle.db.user_profiles.user_profile import UserProfile
    from solariat_bottle.daemons.helpers import parse_user_profile
    UserProfile.objects.upsert('Twitter', profile_data=parse_user_profile(user))

    res = {'name': user.name,
           'screen_name': user.screen_name,
           'profile_image_url': user.profile_image_url}

    return jsonify(ok=True, item=res)
