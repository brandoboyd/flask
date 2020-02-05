# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from flask       import jsonify, request, abort
from collections import defaultdict
from solariat_nlp.sa_labels import SATYPE_NAME_TO_ID_MAP, SATYPE_ID_TO_NAME_MAP

from ..app       import app
from solariat.utils.timeslot import (
    timeslot_to_timestamp_ms, datetime_to_timestamp_ms, datetime_to_timeslot,
    parse_date_interval, guess_timeslot_level, gen_timeslots, now
)
from ..utils.views import (
    matchable_to_dict, post_to_dict, get_paging_params
)
from ..utils.decorators       import login_required
from ..db.channel.base        import Channel
from ..db.response            import (
    Response, RESPONSE_STATUSES, REVIEW_STATUSES, POSTED_MATCHABLE
)
from ..db.response_term_stats import ResponseTermStats, ALL_INTENTIONS
from ..db.speech_act          import SpeechActMap


def _get_response_data_by_user(user, **kw):
    level = kw.pop('level')
    aggregate_clicks = 'clicks' in kw.get('status__in')
    if aggregate_clicks:
        kw['status__in'].extend(['posted', 'retweeted'])

    def _combine_statuses(resp_status, match_status):
        result = []
        if match_status:
            result.append(match_status)

        if resp_status in REVIEW_STATUSES:
            result.append('review')
        elif resp_status:
            result.append(resp_status)

        if aggregate_clicks:
            result.append('clicks')
        return result
    query = Response.objects.get_query(**kw)

    _post_date = Response.fields['post_date'].db_field
    _status = Response.status.db_field
    _clicks = Response.clicked_count.db_field
    _posted_matchable_status = Response.posted_matchable.db_field

    fields={'_id': 0,
            _post_date: 1,
            _status: 1,
            _clicks: 1,
            _posted_matchable_status: 1}

    for r in Response.objects.coll.find(query, fields=fields):
        yield {'time_slot': datetime_to_timeslot(r[_post_date], level=level),
               'statuses' : _combine_statuses(r.get(_status), r.get(_posted_matchable_status)),
               'clicks'   : r.get(_clicks, 0)}


@app.route('/performance_stats/json', methods=['POST'])
@login_required()
def performance_stats(user):

    #"stats_type":["review","posted","rejected","skipped","filtered","retweeted","clicked","custom","alternate"]

    data = request.json
    if data is None:
        raise abort(415)

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist, e:
        return jsonify(ok=False, error=str(e))

    from_dt, to_dt = parse_date_interval(data['from'], data['to'])
    level          = guess_timeslot_level(from_dt, to_dt)

    stats_type = data.get('stats_type', None)
    if stats_type:
        stats_type = map(str, stats_type)

    def _get_statuses(stats):
        statuses = []
        if set(stats).intersection(['posted', 'custom', 'alternate']):
            statuses.append('posted')

        if 'review' in stats:
            statuses.extend(REVIEW_STATUSES)

        statuses.extend(set(stats).intersection(RESPONSE_STATUSES))

        if not statuses:
            statuses = list(RESPONSE_STATUSES)

        if 'clicks' in stats:
            statuses.append('clicks')

        return list(set(statuses))

    def _get_data(from_dt, to_dt, level, pairs, stat_type):
        count = len(pairs)

        date_counts = defaultdict(int)
        total = 0
        for p in pairs:
            #p[0] - time slot
            #p[1] - increment
            date_counts[p[0]] += p[1]
            total += p[1]

        data = []
        for slot in gen_timeslots(from_dt, to_dt, level):
            js_time_stamp = timeslot_to_timestamp_ms(slot)
            data.append((js_time_stamp, date_counts[slot]))

        if stat_type == 'clicks':
            count = total

        return count, data


    response_filters = {'channel'        : channel.id,
                        'post_date__gte' : from_dt,
                        'post_date__lte' : to_dt,
                        'status__in'     : _get_statuses(stats_type),
                        'level'          : level}

    timeslot_stat = defaultdict(list)

    for resp_dict in _get_response_data_by_user(user, **response_filters):
        for rs in resp_dict['statuses']:
            n = 1
            if rs == 'clicks':
                n = resp_dict['clicks']

            timeslot_stat[str(rs)].append((resp_dict["time_slot"], n))

    l = []
    for stype in stats_type:
        count, data = _get_data(from_dt, to_dt, level, timeslot_stat[stype], stype)
        item = {'label' : stype,
                'count' : count,
                'data'  : data}
        l.append(item)

    return jsonify(ok=True, list=l)


@app.route('/performance/topics/json', methods=['POST'])
@login_required()
def performance_topics(user):

    data = request.json
    if data is None:
        raise abort(415)

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist, e:
        return jsonify(ok=False, error=str(e))

    from_dt, to_dt = parse_date_interval(data['from'], data['to'])
    level          = guess_timeslot_level(from_dt, to_dt)
    if level == 'hour':
        level = 'day'  # we don't store response stats for hours

    stats_type = data.get('stats_type', None)
    if stats_type:
        stats_type = map(str, stats_type)

    topics_terms = defaultdict(int)
    topics_posts = defaultdict(set)

    response_filters = dict(
        intention_id    = ALL_INTENTIONS.oid,
        start_time      = from_dt,
        end_time        = to_dt,
        level           = level,
        topic_count__gt = 0
    )
    if stats_type:
        if 'review' in stats_type:
            stats_type.remove('review')
            stats_type.extend(REVIEW_STATUSES)
        response_filters['response_types__in'] = stats_type

    for i in ResponseTermStats.objects.by_time_span(user, channel.id, **response_filters):
        #print i
        topics_posts[i.topic].add(i.post)
        topics_terms[i.topic] += i.topic_count

    topics_resp = defaultdict(int)
    for t in topics_posts.iterkeys():
        topics_resp[t] += len(topics_posts[t])

    #Sort by terms count
    res = sorted(topics_terms.items(), key=lambda x:x[1], reverse=True)[:100]
    res = [ {'term': term, 'count': terms_count, 'response_count': topics_resp[term]} for (term, terms_count) in res ]

    return jsonify(ok=True, list=res)


@app.route('/performance/responses/json', methods=['POST'])
@login_required()
def performance_responses(user):
    response_type = None
    try:
        response_type = request.json.get('stats_type') or request.json.get('response_type')
        if response_type:
            assert(isinstance(response_type, list))
            response_type = map(str, response_type)
    except:
        return jsonify(ok=False, error="Wrong response_type parameter.")

    paging_params = get_paging_params(request.json)

    def query_responses(post_ids, sort_by, user):
        t_start = now()
        response_ids = [ "%s:r" % post_id for post_id in post_ids ]
        response_filter = {"id__in": response_ids}
        if response_type:
            queries = []

            if 'review' in response_type:
                response_type.remove('review')
                response_type.extend(REVIEW_STATUSES)

            posted_matchable_filters = set(POSTED_MATCHABLE).intersection(set(response_type))
            response_status_filters  = set(RESPONSE_STATUSES).intersection(set(response_type))

            if posted_matchable_filters:
                queries.append({
                    #"status": "posted",
                    "posted_matchable__in": list(posted_matchable_filters)})

            if 'clicks' in response_type:
                queries.append({"clicked_count__gt": 0})

            if response_status_filters:
                queries.append({"status__in": response_type})

            if len(queries) > 1:
                response_filter.update({"$or": queries})
            elif queries:
                response_filter.update(queries[0])

        responses = list(Response.objects.find(**response_filter).limit(paging_params['limit']))

        total_count = len(responses)
        if sort_by == 'intention':
            responses.sort(key=lambda p: -p.intention_confidence)
        else:
            responses.sort(key=lambda p: p.created, reverse=True)

        app.logger.debug("Fetched %d responses in %s seconds" % (
                total_count, now() - t_start))

        res = [
            {'match'         : matchable_to_dict(resp.matchable, resp.relevance),
             'post'          : post_to_dict(resp.post, user),
             'response_type' : resp.status,
             'clicks'        : resp.clicked_count,
             'acted_date'    : datetime_to_timestamp_ms(resp.created)}
            for resp in responses
        ]

        return res


    # NO LONGER GOING TO WORK
    return handle_speech_act_map_query(user, query_responses, acted_on=True)


@app.route('/performance/by_intentions/json', methods=['POST'])
@login_required()
def performance_by_intentions(user):

    data = request.json
    if data is None:
        raise abort(415)

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist, e:
        return jsonify(ok=False, error=str(e))

    from_dt, to_dt = parse_date_interval(data['from'], data['to'])
    #level          = guess_timeslot_level(from_dt, to_dt)
    #print from_dt, to_dt, level

    intention_type_ids = [ SATYPE_NAME_TO_ID_MAP[intention]
                           for intention in data['intentions'] ]

    intention_types = defaultdict(int)
    for speech_act in SpeechActMap.objects.find_by_user(
        user,
        channels__in          = [channel.id],
        intention_type_id__in = intention_type_ids,
        time_slot__in         = list(gen_timeslots(from_dt, to_dt, 'hour'))
    ):
        intention_types[speech_act.intention_type_id] += 1

    res = []
    for (intention_type_id, count) in intention_types.items():
        res.append({
            'label': SATYPE_ID_TO_NAME_MAP[str(intention_type_id)],
             'data': count})

    return jsonify(ok=True, list=res)


@app.route('/performance/trends/json', methods=['POST'])
@login_required()
def performance_trends(user):

    data = request.json
    if data is None:
        raise abort(415)

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist, e:
        return jsonify(ok=False, error=str(e))

    from_dt, to_dt = parse_date_interval(data['from'], data['to'])
    level          = guess_timeslot_level(from_dt, to_dt)

    slots = dict([ (s, 0) for s in gen_timeslots(from_dt, to_dt, level=level) ])
    cache = defaultdict(lambda :{'count': 0, 'slots': slots.copy()})

    for resp in Response.objects.find_by_user(user,
            channel=channel,
            post_date__gte=from_dt, post_date__lt=to_dt,
            punks__in=data['terms'],
            intention_name__in=data['intentions']):

        for punk in resp.punks:
            if punk in data['terms']:
                slot = datetime_to_timeslot(resp.post_date, level=level)
                cache[(punk, resp.intention_name)]['count'] += 1
                cache[(punk, resp.intention_name)]['slots'][slot] += 1

    l = []
    for ((punk, intention_name), stat) in cache.items():
        data = [ (timeslot_to_timestamp_ms(ts), count)
                  for (ts, count) in sorted(stat['slots'].items()) ]
        l.append({'count': stat['count'],
                  'label': '%s||%s||%s' % (punk, stat['count'], intention_name),
                  'data': data})

    return jsonify(ok=True, list=l)


@app.route('/performance/trends2/json', methods=['POST'])
@login_required()
def performance_trends_by_responses(user):
    data = request.json
    if data is None:
        raise abort(415)

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist, e:
        return jsonify(ok=False, error=str(e))

    from_dt, to_dt = parse_date_interval(data['from'], data['to'])
    level          = guess_timeslot_level(from_dt, to_dt)

    slots = dict([ (s, 0) for s in gen_timeslots(from_dt, to_dt, level=level) ])
    cache = defaultdict(lambda :{'count': 0, 'slots': slots.copy()})

    for resp in Response.objects.find_by_user(user,
        channel=channel,
        post_date__gte=from_dt, post_date__lt=to_dt,
        punks__in=data['terms'],
        status__in=data['response_type']):

        for punk in resp.punks:
            if punk in data['terms']:
                slot = datetime_to_timeslot(resp.post_date, level=level)
                cache[(punk, resp.status)]['count'] += 1
                cache[(punk, resp.status)]['slots'][slot] += 1

    l = []
    for ((punk, response_type), stat) in cache.items():
        data = [ (timeslot_to_timestamp_ms(ts), count)
                 for (ts, count) in sorted(stat['slots'].items()) ]
        l.append({'count': stat['count'],
                  'label': '%s||%s||%s' % (punk, stat['count'], response_type),
                  'data': data})

    return jsonify(ok=True, list=l)

