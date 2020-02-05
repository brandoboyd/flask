#! /usr/bin/python
# -*- coding: utf-8 -*-
'''
Views for Dealing with User Profile data. This info
will cut across pages.
'''

from flask import jsonify, request

from ..app              import app
from ..utils.decorators import login_required
from solariat.utils.timeslot import datetime_to_timestamp_ms
from ..db.user_profiles.social_profile import SocialProfile
from ..db.channel.base  import Channel
from ..utils.views      import post_to_dict, reorder_posts


def get_platform_profile_class(platform):
    from solariat_bottle.db.user_profiles.chat_profile import ChatProfile
    from solariat_bottle.db.user_profiles.user_profile import UserProfile
    from solariat_bottle.db.user_profiles.web_profile import WebProfile

    platform_profile_map = {
        'Chat': ChatProfile,
        'Voice': ChatProfile,
        'Twitter': UserProfile,
        'Facebook': UserProfile,
        'Solariat': UserProfile,
        'VOC': UserProfile,
        'Email': UserProfile,
        'FAQ': WebProfile
    }
    platform_profile_map.update({
        'ChatProfile': ChatProfile,
        'UserProfile': UserProfile,
        'WebProfile': WebProfile,
    })

    return platform_profile_map.get(platform, UserProfile)


@app.route('/user_profile/json')
@login_required()
def get_user_profile(user):
    '''
    Fetch the details of a user. Expecting a channel
    and a user name.
    '''
    def get_items(channel, user_profile, status='posted'):
        "Return list of pair post-response that were sent to user"
        def to_dict(resp):
            result = dict(
                created_at = datetime_to_timestamp_ms(resp.post.created),
                stats      = dict(
                    #influence     = 0.0,
                    #receptivity   = 0.0,
                    #actionability = 0.0, #resp.post.actionability,
                    intention     = {
                        'vote'  : resp.post.get_vote(user),
                        'type'  : resp.post.intention_name,
                        'score' : "%.2f" % resp.post.intention_confidence
                    },
                ),
                text       = resp.post.plaintext_content,
                topics     = resp.post.punks,
                url        = resp.post.url,
                id_str     = str(resp.post.id)
            )

            if resp.status == 'posted':
                result['response'] = dict(
                    post_id_str = str(resp.post.id),
                    creative    = resp.matchable.creative,
                    id          = str(resp.id),
                    landing_url = resp.matchable.get_url(),
                    topics      = resp.matchable.intention_topics,
                    stats       = {
                        "ctr": resp.matchable.ctr,
                        "impressions" : resp.matchable.accepted_count,
                        "relevance" : resp.relevance
                        }
                    )
            else:
                result['response'] = None

            return result

        return [to_dict(x) for x in Response.objects.find_by_user(
                user, channel=channel, user_profile=user_profile)]

    if 'channel_id' not in request.args:
        app.logger.error('channel_id required')
        return jsonify(ok=False,
                       error='channel_id is required')
    try:
        channel = Channel.objects.get(id=request.args['channel_id'])
    except Channel.DoesNotExist:
        return jsonify(ok=False,
                       error='Channel with id %s does not exists' % (request.args['channel_id']))

    user_id = None or request.args.get('user_id', None)
    if user_id is None and 'user_name' in request.args:
        try:
            user_id = SocialProfile.objects.get(user_name=request.args['user_name']).id
        except SocialProfile.DoesNotExist:
            pass

    if not user_id:
        app.logger.error('user_id required')
        return jsonify(ok=False, error='user_id is required')

    platform_classes = [
        get_platform_profile_class(platform=channel.platform),
        get_platform_profile_class(platform=request.args.get('_type', 'UserProfile'))
    ]
    user_profile = None
    for UserProfileCls in platform_classes:
        user_profile = UserProfileCls(UserProfileCls.objects.coll.find_one({'_id': user_id}))
        if user_profile:
            break
    if not user_profile:
        return jsonify(ok=False,
                       error='%s with id %s does not exists' % (
                             '|'.join(set([cls.__name__ for cls in platform_classes])),
                             user_id))

    result = []
    conversations = user_profile.get_conversations(user, channel)

    # Batch Fetch Tags
    if channel.is_smart_tag:
        parent_channel = Channel.objects.get_by_user(user=user, id=channel.parent_channel)
    else:
        parent_channel = channel

    tags = dict( [ (str(tag.id), tag)
               for tag in Channel.objects.find_by_user(user=user, account=channel.account, parent_channel=parent_channel.id) ] )

    for conv in conversations[::-1]:
        # posts are reordered in chronological order, but replies immediately after parents
        posts = reorder_posts(conv.query_posts()[:])
        item  = [post_to_dict(p, user, channel=channel, tags=tags) for p in posts[::-1]]
        result.append(item)

    return jsonify(ok=True, user=user_profile.to_dict(), list=result)
