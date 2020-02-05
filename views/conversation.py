#!/usr/bin/env python

""" Channel specific end-points
"""
import json

from flask import jsonify, request

from ..settings                import LOGGER
from ..app                     import app
from ..db.channel.base         import Channel
from ..db.conversation         import Conversation
from ..db.conversation_trends  import ConversationQualityTrends
from ..db.post.base            import Post
from ..utils.decorators        import login_required
from ..utils.views             import render_posts, reorder_posts, post_to_dict
from ..utils.id_encoder        import make_channel_ts
from solariat.utils.timeslot          import Timeslot

from solariat.db.fields import BytesField
to_binary = BytesField().to_mongo

@app.route('/conversation/json', methods=['GET'])
@login_required()
def get_conversation_posts(user): 
    post_id    = request.args.get('post_id')
    channel_id = request.args.get('channel_id')
    tag_id     = request.args.get('tag_id', None)
    post       = Post.objects.get(id=post_id)
    channel    = Channel.objects.get(id=channel_id) if channel_id else None
    if not channel or not channel.parent_channel:
        # No service channel has been passed, so it's a click on
        # 'View conversations' from a different channel (e.g. outbound dispatch)
        # Just try and get the service channel directly from post.
        channel = post.channel
        if not channel or not channel.parent_channel:
            return jsonify(ok=False, 
                           error="Could not retrieve ant conversations. No service channel was found.")
    service_channel = Channel.objects.get(id=channel.parent_channel)
    try:
        conv = Conversation.objects.lookup_by_posts(service_channel, [post],
                                                    include_closed=True)[0]
    except IndexError:
        return jsonify(ok=False, error="No such conversation.")

    posts = [p for p in conv.POST_CLASS.objects(id__in=conv.posts)]
    posts = reorder_posts(posts)
    if tag_id:
        # If a tag was passed in to conversation filter, only return posts which are tagged
        tag = Channel.objects.get(tag_id)
        posts = [p for p in posts if tag in p.accepted_smart_tags]
    results = render_posts(user, posts, channel, conversation=conv)
    return jsonify(ok=True, list=results)


def __get_conversations(data):
    "preparing query params and performing first bulk query to get the conversations"
    assert data.get('level') in ("hour", "day"), data.get('level')
    channel_ts_key = "channel_ts_day" if data.get('level') == "day" else "channel_ts_hour"    
    channel_ts_lower_bound = make_channel_ts(
        data.get('channel_id'), 
        Timeslot(data.get('from'), data.get('level')))
    channel_ts_upper_bound = make_channel_ts(
        data.get('channel_id'), 
        Timeslot(data.get('to'), data.get('level')))
    query = {
        channel_ts_key+"__lte": to_binary(channel_ts_upper_bound),
        channel_ts_key+"__gte": to_binary(channel_ts_lower_bound),
        "is_closed": True}
    if data.get('categories'):
        categories_param = []
        for cat in data.get('categories'):
            if isinstance(cat, int):
                categories_param.append(cat)
            elif isinstance(cat, (str, unicode)):
                categories_param.append(ConversationQualityTrends.get_category_code(cat))
            else:
                raise Exception("Wrong type for category param; value: %s, type: %s", cat, type(cat))
        query["quality__in"] = categories_param
    conversations = (Conversation.objects(**query)
        .limit(data.get('limit'))
        .skip(data.get('offset')))
    if 'time' == data.get('sort_by'):
        conversations = conversations.sort(**{'last_modified': 1})
    return conversations


def __get_post_list(conversations, data):
    response = []
    post_ids = []
    conversation_post_map = {}
    "building response list and collecting ids of the first post of each conversation"
    for conversation in conversations:
        item = {
            "id_str": str(conversation.id),
            "are_more_posts_available": len(conversation.posts) > 1,
            "quality": conversation.quality
        }
        response.append(item)
        post_ids.append(conversation.posts[0])
        conversation_post_map[str(conversation.id)] = str(conversation.posts[0])

    "Second bulk query. We getting all first posts of all conversations"
    post_map = {}
    for post in Post.objects(id__in=post_ids):
        post_map[post.id] = post

    return response, post_map, conversation_post_map



@app.route('/conversations/json', methods=['POST'])
@login_required
def get_conversations_list(user):
    """
    Request params: 'channel_id', 'from', 'to', 'level', 
                    'limit', 'offset', 'sort_by', 'categories',
    """
    data = json.loads(request.data)
    try:
        conversations = __get_conversations(data)    
        response, post_map, conversation_post_map = __get_post_list(conversations, data)
        "adding first posts to response list"
        for i, item in enumerate(response):
            post = post_map[conversation_post_map[item["id_str"]]]
            response[i]["first_post"] = post_to_dict(post, user)
        "preparing response"
        response = {
            'list': response,
            'limit': data.get('limit'),
            'offest': data.get('offest'),
            'ok': True
        }
        return jsonify(response)

    except Exception, exc:
        LOGGER.error('error on /conversation/json', exc_info=True)
        return jsonify(ok=False, error=str(exc))




