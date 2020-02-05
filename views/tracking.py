#!/usr/bin/env python2.7

from flask import jsonify, request
from ..app import app
from solariat.utils.lang.helper import convert_to_lang_form, convert_to_ui_form
from ..utils.decorators import login_required
from ..db.channel.base import Channel
from ..db.channel.twitter import UserTrackingChannel
from ..db.post.base import Post
from ..db.account import AccountEvent
from ..db.tracking import get_all_tracked_channels

@app.route('/tracking/keywords/json', methods=['GET', 'POST', 'DELETE'])
@login_required()
def tracking_keywords(user):
    '''
    Handler for addition and deletion of keywords for a tracking channel.
    '''

    if request.json is not None:
        data = request.json
    else:
        data = request.args

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist:
        return jsonify(ok=False,
                       error='Channel %s does not exist' % data['channel_id'])

    try:
        assert(hasattr(channel, 'keywords'))
        assert(hasattr(channel, 'add_keyword'))
        assert(hasattr(channel, 'del_keyword'))
    except AssertionError:
        return jsonify(ok=False,
                       error='Channel does not support requested action.')

    if request.method == 'GET':
        return jsonify(ok=True, item=[convert_to_ui_form(key) for key in channel.keywords])

    old_data = channel.keywords
    if request.method == 'POST':

        if 'keyword' not in data:
            return jsonify(ok=False, error='keyword should be provided')
        if not channel.add_keyword(convert_to_lang_form(data['keyword'])):
            return jsonify(ok=False, error="This keyword is incorrect. Probably it's exist on other language.")

    if request.method == 'DELETE':

        if 'keyword' not in data:
            return jsonify(ok=False, error='keyword should be provided')
        channel.del_keyword(convert_to_lang_form(data['keyword']))

    new_data = channel.keywords
    AccountEvent.create_by_user(user=user,
                                change='Keywords modifications',
                                old_data={'keywords': old_data},
                                new_data={'keywords': new_data})

    return jsonify(ok=True)

@app.route('/tracking/skipwords/json', methods=['GET', 'POST', 'DELETE'])
@login_required()
def tracking_skipkeywords(user):
    '''
    Handler for addition and deletion of keywords for a tracking channel.
    '''

    if request.json is not None:
        data = request.json
    else:
        data = request.args

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist:
        return jsonify(ok=False,
                       error='Channel %s does not exist' % data['channel_id'])

    assert(hasattr(channel, 'skipwords'))
    assert(hasattr(channel, 'add_skipword'))
    assert(hasattr(channel, 'del_skipword'))

    if request.method == 'GET':
        return jsonify(ok=True, item=[convert_to_ui_form(skip) for skip in channel.skipwords])

    old_data = channel.skipwords
    if request.method == 'POST':
        if 'keyword' not in data:
            return jsonify(ok=False, error='skip word should be provided')
        else:
            if not channel.add_skipword(convert_to_lang_form(data['keyword'])):
                return jsonify(ok=False, error="This skip word is incorrect. Probably it's exist on other language.")

    if request.method == 'DELETE':
        if 'keyword' not in data:
            return jsonify(ok=False, error='skip word should be provided')
        else:
            channel.del_skipword(convert_to_lang_form(data['keyword']))

    new_data = channel.skipwords
    AccountEvent.create_by_user(user=user,
                                change='Skipwords modifications',
                                old_data={'skipwords': old_data},
                                new_data={'skipwords': new_data})
    return jsonify(ok=True)

@app.route('/tracking/watchwords/json', methods=['GET', 'POST', 'DELETE'])
@login_required()
def tracking_watchwords(user):
    '''
    Handler for addition and deletion of watchwords for a tracking channel.
    '''

    if request.json is not None:
        data = request.json
    else:
        data = request.args

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist:
        return jsonify(ok=False,
                       error='Channel %s does not exist' % data['channel_id'])

    assert(hasattr(channel, 'watchwords'))
    assert(hasattr(channel, 'add_watchword'))
    assert(hasattr(channel, 'del_watchword'))

    if request.method == 'GET':
        return jsonify(ok=True, item=[convert_to_ui_form(watch) for watch in channel.watchwords])

    old_data = channel.watchwords
    if request.method == 'POST':
        if 'watchword' not in data:
            return jsonify(ok=False, error='watch word should be provided')
        else:
            if not channel.add_watchword(convert_to_lang_form(data['watchword'])):
                return jsonify(ok=False, error="This actionable word is incorrect. Probably it's exist on other language.")

    if request.method == 'DELETE':
        if 'watchword' not in data:
            return jsonify(ok=False, error='watch word should be provided')
        else:
            channel.del_watchword(convert_to_lang_form(data['watchword']))

    new_data = channel.watchwords
    AccountEvent.create_by_user(user=user,
                                change='Watchwords modifications',
                                old_data={'watchwords': old_data},
                                new_data={'watchwords': new_data})
    return jsonify(ok=True)

@app.route('/tracking/usernames/json', methods=['GET', 'POST', 'DELETE'])
@login_required()
def tracking_usernames(user):
    '''
    Handler for addition and removal of usernames for user tracking channel or FollowerTrackingChannel.

    Should also work for other types of channels with following attributes defined:
    usernames
    add_username
    del_username
    '''

    if request.json is not None:
        data = request.json
    else:
        data = request.args

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist:
        return jsonify(ok=False,
                       error='Channel %s does not exist' % data['channel_id'])
    try:
        assert(hasattr(channel, 'usernames'))
        assert(hasattr(channel, 'add_username'))
        assert(hasattr(channel, 'del_username'))
    except AssertionError:
        return jsonify(ok=False,
            error='Channel does not support requested action. User/follower tracking channel expected.')

    if request.method == 'GET':
        return jsonify(ok=True, item=channel.usernames)

    if request.method == 'POST':

        if 'username' not in data:
            return jsonify(ok=False, error='username should be provided')
        channel.add_username(data['username'])

    if request.method == 'DELETE':

        if 'username' not in data:
            return jsonify(ok=False, error='username should be provided')
        channel.del_username(data['username'])

    return jsonify(ok=True)

@app.route('/post/track/json', methods=['GET'])
@login_required()
def post_track(user):
    '''
    Obtain the list and state of channel ids for the post. It is
    dependent on the data for the post itself, and also the state
    of the system configuration for future tracking
    '''

    def render_channels_state(channels, color):
        "Helper method for setting display data"
        items = []
        for c in channels:
            item = {'text': c.title, 
                    'id': str(c.id), 
                    'color': color, 
                    'change': color != 'red' and isinstance(c, UserTrackingChannel)}
            items.append(item)
        return items

    if request.json is not None:
        data = request.json
    else:
        data = request.args

    if 'post_id' not in data:
        channels = [ {'text': c.title, 'id': str(c.id)} 
                     for c in UserTrackingChannel.objects.find_by_user(user) ]
        return jsonify(ok=True, items=channels)

    try:
        post = Post.objects.get(data['post_id'])
        l1 = set(list(Channel.objects.find_by_user(user,
                                                   id__in=post.channels)))

        post_data = post.to_dict()
        post_data['user_profile'] = post.get_user_profile().to_dict()
        l2 = set(get_all_tracked_channels(user, post_data))

        items = []
        items.extend( render_channels_state(l1.difference(l2), 'red') )
        items.extend( render_channels_state(l2.difference(l1), 'yellow') )
        items.extend( render_channels_state(l1.intersection(l2), 'green') )
        return jsonify(ok=True, items=items)

    except Post.DoesNotExist:
        err_msg = 'Post %s does not exist' % data['post_id']

    app.logger.error(err_msg)
    return jsonify(ok=False, error=err_msg)



