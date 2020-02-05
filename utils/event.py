
from solariat_bottle.db.post.chat import ChatPost
from solariat_bottle.db.events.event import PostEvent, ClickEvent, Event
from solariat_bottle.db.post.base import Post
from solariat_bottle.db.post.twitter import TwitterPost
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.conversation_state_machine import make_post_vector

EVENT_CLASS_MAP = {
    'Base': Event,
    'Click' : ClickEvent,
    'Post' : PostEvent,
    'Chat' : PostEvent,
    'Twitter' : PostEvent,
}


def get_platform_class(type):
    return EVENT_CLASS_MAP[type]
    return klass or Post

def get_event_data(post, channel):
    kw = {}
    if isinstance(post, ChatPost):
        parent_post_id = post.extra_fields.get('chat', {}).get('in_reply_to_status_id')
        parent_post = ChatPost.objects.get(id=parent_post_id) if parent_post_id else None
    elif isinstance(post, TwitterPost):
        parent_post = post.parent
    else:
        raise Exception('unknown post type')
    sc = Channel.objects.get(id=str(channel.parent_channel))
    assert sc.is_service, sc
    kw['post'] = post
    kw['is_inbound'] = sc.route_post(post) == 'inbound'
    kw['actor_id'] = post.user_profile.id if kw['is_inbound'] else post.find_agent(sc).id
    # kw['extra_fields'] = make_post_vector(post, sc)
    kw['channels'] = [channel.id]
    return kw


