# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from operator    import itemgetter
from collections import defaultdict

from flask import jsonify, request

from ..app                      import app
from ..views.messages           import escape_regex
from ..db.channel.base          import Channel, ContactChannel, PLATFORM_MAP
from ..db.service_channel_stats import ServiceChannelStats
from ..db.account               import Account
from ..db.user_profiles.user_profile import UserProfile
from ..db.conversation          import Conversation
from ..utils.decorators         import login_required
from ..utils.views              import (
    get_paging_params, pluck_ids,
    post_to_dict, response_to_dict,
    build_user_profile_cache
)
from solariat.utils.timeslot import (
    parse_date_interval,
    guess_timeslot_level,
    gen_timeslots,
    timeslot_to_timestamp_ms
)


@app.route('/contacts/json')
@login_required()
def contacts_handler(user):
    def getlist(source, key):
        if hasattr(source, 'getlist'):
            return source.getlist(key)
        else:
            return source.get(key, [])

    data = request.args.copy()
    if not data:
        data = request.json

    data = data or {}

    allowed_params = ('offset', 'limit', 'channels', 'search_term', 'accounts', 'platforms')
    for param in data.copy().iterkeys():
        if param not in allowed_params:
            data.pop(param, None)
    paging_params = get_paging_params(data)

    #Filtering Contact channels by accounts and platforms
    cc_filters = {}

    accounts = getlist(data, 'accounts')
    if accounts:
        accounts = pluck_ids(Account.objects.find_by_user(user, name__in=accounts))

    accounts = accounts or user.current_account and [user.current_account.id]
    if not accounts:
        return jsonify(ok=False, error="no account found")
    else:
        cc_filters['account__in'] = accounts


    platforms = getlist(data, 'platforms')
    if platforms:
        cc_filters['platform_id__in'] = [PLATFORM_MAP[p]['index'] for p in platforms if PLATFORM_MAP.get(p)]

    contact_channels = pluck_ids(ContactChannel.objects(**cc_filters))

    #Filtering UserProfiles by contact_channels and engaged_channels
    channels = getlist(data, 'channels')
    if channels:
        channels = Channel.objects.find_by_user(user, id__in=channels)

    filters = {'contact_channels__in': contact_channels}
    if channels:
        filters['engaged_channels__in'] = list(channels)

    search_term = data.pop('search_term', None)
    if search_term is not None and search_term.strip():
        filters['id__regex'] = "^%s" % escape_regex(search_term)
        filters['id__options'] = 'i'

    contacts = UserProfile.objects(**filters).limit(paging_params['limit']).skip(paging_params['offset'])
    contacts = [c.to_dict() for c in contacts]

    return jsonify(ok=True, list=contacts)


@app.route('/contacts/threads/json')
@login_required()
def contacts_threads_handler(user):
    """Show all conversations for given user_profile
    GET /contacts/threads/json?user_profile=id&limit=int&offset=int
    """
    data = request.args.copy()
    if not data:
        data = request.json
    data = data or {}

    profile_id = data.get('user_profile')
    try:
        user_profile = UserProfile.objects.get(id=profile_id)
    except UserProfile.DoesNotExist:
        user_profile = None
    if not user_profile:
        return jsonify(ok=False, error="user profile not found")

    try:
        contact_id = int(user_profile.user_id)
    except:
        return jsonify(ok=False, error="user has no original id")

    paging_params = get_paging_params(data)

    threads = []

    conversations = Conversation.objects(contact_ids=contact_id) \
        .sort(**{'last_modified':-1}) \
        .limit(paging_params['limit']) \
        .skip(paging_params['offset'])

    threads       = conversations[:]
    root_post_map = dict((t.id, t.root_post) for t in threads)
    profile_cache = build_user_profile_cache(root_post_map.values())

    for thread in threads:
        post        = root_post_map[thread.id]
        thread_dict = thread.to_dict()
        post_dict   = post_to_dict(post, user, profile_cache)

        try:
            response = Response.objects.get(id=post.response_id)
        except Response.DoesNotExist:
            response = None

        if response:
            post_dict['response'] = response_to_dict(response, user)

        thread_dict['root_post'] = post_dict
        threads.append(thread_dict)

    return jsonify(ok=True, list=threads)


@app.route('/thread/json')
@login_required()
def thread_posts_handler(user):
    conversation_id = request.args.get('id')
    try:
        conversation = Conversation.objects.get_by_user(user, id=conversation_id)
    except Conversation.DoesNotExist:
        return jsonify(ok=False, error="Thread not found")

    posts = list(conversation.query_posts())
    posts = sorted(posts, key=itemgetter('created'))
    result = []

    profile_cache = build_user_profile_cache(posts)

    for post in posts:
        post_dict = post_to_dict(post, user, profile_cache)

        try:
            response = Response.objects.get(id=post.response_id)
        except Response.DoesNotExist:
            response = None
        if response:
            post_dict['response'] = response_to_dict(response, user)
        result.append(post_dict)

    return jsonify(ok=True,
                   item=conversation.to_dict(),
                   list=result)


def aggregate_stats(user, channel, from_, to_, level, stats=('volume', 'latency')):
    data = {}
    for a in stats:
        data[a] = []

    by_ts = {}

    for stat in ServiceChannelStats.objects.by_time_span(
            user,
            channel,
            start_time=from_,
            end_time=to_,
            level=level):
        by_ts[stat.time_slot] = stat

    counts = defaultdict(int)
    for slot in gen_timeslots(from_, to_, level):
        for stat in stats:
            stat_obj = by_ts.get(slot, None)
            if stat_obj:
                value = getattr(stat_obj, 'average_latency' if stat == 'latency' else stat)
            else:
                value = 0

            data[stat].append([timeslot_to_timestamp_ms(slot), value])
            counts[stat] += value

    return data, counts


@app.route('/service_channel_stats/json', methods=['POST'])
@login_required()
def service_channel_stats(user):
    data = request.json
    if not data:
        return jsonify(ok=False, error='JSON data is required')
    for param in ['from', 'to', 'stats', 'channel_id']:
        if not data.get(param):
            return jsonify(ok=False,
                           error='%s is not provided, got %s' % (
                               param, str(data)))
    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist:
        return jsonify(ok=False, error='Channel %s does not exist' %  data['channel_id'])

    from_, to_ = parse_date_interval(data['from'], data['to'])
    level = guess_timeslot_level(from_, to_)
    if not from_ or not to_:
        return jsonify(ok=False,
                       error = '"from" and "to" paramater should be provided"')

    #valid_stats = set(['volume', 'latency'])
    #stats = list(set(data['stats']).intersection(valid_stats))
    stats = ['volume', 'latency']
    try:
        data, counts = aggregate_stats(user, channel, from_, to_, level, stats)

        result = dict(zip(stats, [dict(data=data[stat], label=stat, count=counts[stat]) for stat in stats]))
        return jsonify(ok=True, data=result)

    except RuntimeError, exc:
        app.logger.error("on getting speech act stats", exc_info=True)
        return jsonify(ok=False, error=str(exc))
    except Exception, exc:
        app.logger.error("on getting speech act stats", exc_info=True)
        return jsonify(ok=False, error='Internal error')

