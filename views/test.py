
from flask import render_template, jsonify, request, abort

from ..app import app

from ..utils.decorators import staff_or_admin_required, superuser_required
from ..db.channel.base  import Channel
from ..db.conversation  import Conversation

from ..tasks.salesforce import sf_close_conversation


@app.route('/test')
@staff_or_admin_required
def matching_handler(user):
    return render_template("/test.html",
                           parent='test',
                           top_level='test',
                           section='matching',
                           user=user)


@app.route('/test_agents')
@staff_or_admin_required
def agent_matching_create_agent(user):
    return render_template("/agent_matching/test-agent-matching.html",
                           parent='test_agents',
                           top_level='test',
                           section='agent_matching',
                           user=user)

@app.route('/test/integration-sf')
@staff_or_admin_required
def sf_integration_handler(user):
    return render_template(
        "/test-integration-sf.html",
        parent='test',
        section='integration-sf',
        user=user)



@app.route('/test/filtering')
@superuser_required
def filtering_handler(user):
    return render_template("/test-filtering.html",
                           parent='test',
                           top_level='test',
                           section='filtering',
                           user=user)


@app.route('/test/classifier', methods=['POST'])
@superuser_required
def classifier(user):
    """"Takes channel id and reset's it's classifier"""
    data = request.json
    if 'channel' not in data or 'action' not in data:
        return abort(400)
    else:
        channel = None
        channel_id = data['channel']
        try:
            channel = Channel.objects.find_by_user(user, id=channel_id)[0]
        except:
            return jsonify({'ok': False,
                            'error': 'channel not found.'})
        try:
            import time
            start_time = time.time()
            tags = [t for t in Channel.objects.find_by_user(user,
                                                            parent_channel=channel.id)]
            things_to_reset = [channel] + tags
            for c in things_to_reset:
                action = data['action']
                func = {
                    'reset': c.channel_filter.reset,
                    'retrain': c.channel_filter.retrain
                }[action]
                func()
            total_time = time.time() - start_time

        except Exception, e:
            app.logger.error(e)
            return abort(500)

    return jsonify({'ok': True,
                    'elapsed_time': "%.2f" % total_time,
                    'action': action,
                    'message': "All is well."})


@app.route('/test/close_conversations', methods=['POST'])
@staff_or_admin_required
def close_conversations(user):
    """"
    Takes channel id and closes all its conversations.
    """
    data = request.json
    if 'channel' not in data:
        return abort(400)
    else:
        channel = None
        channel_id = data['channel']
        try:
            channel = Channel.objects.find_by_user(user, id=channel_id)[0]
            conversations = Conversation.objects(channel=channel.parent_channel)
            count_conversations_have_external_id = 0
            count_errors_while_closing = 0
            closing_errors = []
            for conv in conversations:
                if conv.external_id:
                    count_conversations_have_external_id += 1
                    try:
                        sf_close_conversation.sync(conv)
                    except Exception, e:
                        closing_errors.append(e)
                        count_errors_while_closing += 1
            return jsonify({
                'ok': True,
                'message': "Conversations are closed.",
                'count_conversations_total': len(conversations),
                'count_conversations_have_external_id': count_conversations_have_external_id,
                'count_errors_while_closing': count_errors_while_closing,
                'closing_errors': str(closing_errors),
            })
        except Exception, e:
            return jsonify({
                'ok': False,
                'error': e
            })

@app.route('/test/matcher',methods=['POST'])
@superuser_required
def matcher(user):
    """"Takes channel id and reset's it messsages for all feedback"""
    data = request.json
    try:
        channel_id = data['channel']
        assert 'action' in data, "Action must be provided"
        action = data['action']
        assert action == 'reset', "%s is not a valid action" % action

        Channel.objects.find_by_user(user, id=channel_id)[0]

        import time
        start_time = time.time()

        updated = 0
        updated_active = 0

        total_time = time.time() - start_time
        result = {'ok':True,
                  'elapsed_time':"%.2f"%total_time,
                  'action':action,
                  'message': "Updated %d messages and redeployed %d active items" % (updated, updated_active)
                  }

    except Exception, e:
        err_msg = "Failed to execute %s" % action
        result = {'ok': False, 'error': "%s %s" % (err_msg, str(e))}

    return jsonify(result)


def bson_safe(data):
    import json
    from bson import json_util
    return json.loads(json_util.dumps(data))


def post_to_data(post):

    return bson_safe(dict(
        _id_str=str(post.id),
        _id=post.data['_id'],
        native_id=post.native_id,
        native_data=post.native_data,
        content=post.plaintext_content,
        created_at=post.created_at,
        conversation_ids=[c.id for c in Conversation.objects(posts=post.data['_id'])]
    ))


@app.route('/_admin/check_facebook_channels')
@superuser_required
def su_check_facebook_channels(user):
    data = request.args
    if not {'channel', 'account'}.intersection(set(data)):
        return jsonify(error='Missing channel or account arg (name or id)')

    from solariat_bottle.scripts.analyze_facebook_channels_config import check_accounts, \
        check_service_channels

    if 'account' in data:
        from solariat_bottle.db.account import Account
        items = Account.objects(name=data['account'])[:]
        items.extend(Account.objects(id=data['account'])[:])
        verify_fn = check_accounts

    elif 'channel' in data:
        from solariat_bottle.db.channel.base import Channel
        items = Channel.objects(include_safe_deletes=True, id=data['channel'])[:]
        items.extend(Channel.objects(title=data['channel'])[:])
        verify_fn = check_service_channels
    else:
        return jsonify(error='account or channel arg expected')

    try:
        result = verify_fn(
            items,
            include_safe_deletes=data.get('x', data.get('include_safe_deletes', False)),
            show_sensitive_info=data.get('s', data.get('show_sensitive_info', False)))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    else:
        return jsonify(result=result)


@app.route('/_admin/print_conversation/<conv_id>')
@superuser_required
def su_print_conversation(user, conv_id):
    try:
        conv = Conversation.objects.get(long(conv_id))
    except (Conversation.DoesNotExist, ValueError):
        return jsonify(ok=False, error='Does not exists')

    from solariat_bottle.db.post.base import Post

    data = {
        'conversation_data': bson_safe(conv.data),
        'posts': []
    }

    for post in Post.objects(id__in=conv.posts):
        data['posts'].append(post_to_data(post))
    return jsonify(data)


@app.route('/_admin/corrupted_conversations')
@superuser_required
def su_corrupted_conversation(user):
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))

    data = {'conversations': []}
    for conv in Conversation.objects(is_corrupted=True).limit(limit).skip(offset):
        data['conversations'].append(bson_safe(conv.data))

    data['total'] = len(data['conversations'])
    return jsonify(data)


def channels_to_json(channels, with_data=False):
    def _to_json(channel):
        item = {
            '__repr__': str(channel),
            'id_str': str(channel.id),
            'title': channel.title,
            'account': {'id_str': str(channel.account.id), 'name': channel.account.name}}
        if with_data:
            item.update(data=bson_safe(channel.data))
        return item

    return map(_to_json, channels)


def get_posts_by_id(post_id):
    """
    Returns QuerySet of posts list
    :param post_id: antive or tango id
    :return:
    """
    from solariat.db.fields import Binary
    from solariat_bottle.db.post.facebook import FacebookEventMap
    from solariat_bottle.db.post.twitter import TwitterEventMap
    from solariat_bottle.db.post.base import Post
    post_ids = []
    for em in FacebookEventMap.objects(native_id=post_id):
        post_ids.append(em.event_id)
    for em in TwitterEventMap.objects(native_id=post_id):
        post_ids.append(em.event_id)

    try:
        post_ids.append(Binary(post_id.decode('base64')))
    except Exception:
        pass
    try:
        post_ids.append(long(post_id))
    except Exception:
        pass

    return Post.objects(id__in=post_ids)


@app.route('/_admin/print_post/<post_id>')
@superuser_required
def su_print_post(user, post_id):
    from solariat_bottle.utils.posts_tracking import PostState

    result = []
    for post in get_posts_by_id(post_id):
        post_json = post_to_data(post)
        post_json['service_channels'] = channels_to_json(post.service_channels)
        post_json['channels'] = str(post.channels)
        post_json['tracks'] = [
            {'timestamp': str(track.id.generation_time),
             'state': track.state}
            for track in PostState.objects(post_id__in=[post.native_id, str(post.native_id)])
        ]
        result.append(post_json)
    return jsonify(post_id=post_id, result=result)


@app.route('/_admin/fb_channel_assignment/<object_id>')
@superuser_required
def su_fb_channel_assignment(user, object_id):
    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))

    query = {}
    page_ids = []
    if object_id != 'all':
        object_ids = [object_id]
        for post in get_posts_by_id(object_id):
            object_ids.append(post.native_id)

        for object_id in object_ids:
            if '_' in object_id:
                page_ids.extend(object_id.split('_'))
            else:
                page_ids.append(object_id)
        query = {'object_id__in': page_ids}

    from solariat_bottle.db.facebook_tracking import FacebookTracking

    result = []
    for item in FacebookTracking.objects(**query).limit(limit).skip(offset):
        result.append({
            'object_id': item.object_id,
            'object_type': item.object_type,
            'channels': channels_to_json(item.channels)
        })
    return jsonify(ok=True, object_id=object_id, lookup=page_ids, limit=limit, offset=offset, result=result)


@app.route('/_admin/post_filter_entries/<channel_id>')
@superuser_required
def su_post_filter_entries(user, channel_id):
    from solariat_bottle.utils.post import get_service_channel

    query = {}
    if channel_id != 'all':
        channels = []
        try:
            channel = Channel.objects.get(channel_id)
            service_channel = get_service_channel(channel)
            dispatch_channel = service_channel.get_outbound_channel(user)
            channels.append(channel)
            if service_channel:
                channels.extend([service_channel, service_channel.inbound_channel, service_channel.outbound_channel])
            if dispatch_channel:
                channels.append(dispatch_channel)
        except Exception as exc:
            return jsonify(ok=False, error=str(exc))
        query = {'channels__in': channels}

    from solariat_bottle.db.tracking import PostFilterEntry

    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))

    result = []

    for pfe in PostFilterEntry.objects(**query).limit(limit).skip(offset):
        result.append(dict(
            entry=pfe.entry,
            filter_type=pfe.filter_type_id,
            lang=pfe.lang,
            channels=channels_to_json(pfe.channels)))
    return jsonify(list=result)


@app.route('/_admin/queue_view/<channel_id>')
@superuser_required
def su_queue_view(user, channel_id):
    query = {}
    if channel_id != 'all':
        try:
            from solariat_bottle.utils.post import get_service_channel
            service_channel = get_service_channel(Channel.objects.get(channel_id))
            dispatch_channel = service_channel.get_outbound_channel(user)
        except Exception as exc:
            return jsonify(ok=False, channel_id=channel_id, error=str(exc))
        else:
            channel_ids = []
            if service_channel:
                channel_ids.append(str(service_channel.id))
            if dispatch_channel:
                channel_ids.append(str(dispatch_channel.id))
            query = dict(channel_id__in=channel_ids)

    limit = int(request.args.get('limit', 20))
    offset = int(request.args.get('offset', 0))

    from solariat_bottle.db.queue_message import QueueMessage
    from solariat_bottle.db.post.base import Post
    messages = []
    for message in QueueMessage.objects(**query).limit(limit).skip(offset):
        post_data = post_to_data(Post(message.post_data))
        post_data['message_id'] = str(message.id)
        post_data['reserved_until'] = str(message.reserved_until)
        messages.append(post_data)
    return jsonify(channel_id=channel_id, limit=limit, offset=offset, result=messages,
                   total=QueueMessage.objects(**query).count())


@app.route('/_admin/print_channel/<channel_id>')
@superuser_required
def su_print_channel(user, channel_id):
    try:
        channel = Channel.objects.get(channel_id)
    except Channel.DoesNotExist as exc:
        return jsonify(ok=False, error=str(exc))

    from solariat_bottle.utils.post import get_service_channel
    service_channel = get_service_channel(channel)
    dispatch_channel = service_channel.get_outbound_channel(user)
    channels = filter(None, {channel, service_channel, dispatch_channel})
    return jsonify(
        channel_id=channel_id,
        list=channels_to_json(channels, with_data=True))


@app.route('/_admin/print_account/<account_id>')
@superuser_required
def su_print_account(user, account_id):
    from solariat_bottle.db.account import Account
    try:
        account = Account.objects.get(account_id)
    except Account.DoesNotExist as exc:
        return jsonify(error=str(exc))

    return jsonify(
        account_id=account_id,
        data=bson_safe(account.data),
        channels=channels_to_json(Channel.objects(account=account)[:], with_data=True))

