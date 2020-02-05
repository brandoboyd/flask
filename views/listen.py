# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

""" Views for listen screen
"""

import json
from collections import defaultdict
from flask import request, jsonify
from solariat_nlp.sa_labels import (
    SAType, get_sa_type_title_by_name as get_sa_type_by_name,
    SATYPE_ID_TO_NAME_MAP
)

from ..app import app
from ..utils.decorators import login_required
from solariat.utils.timeslot import (
    parse_date_interval,
    parse_date,
    gen_timeslots,
    timeslot_to_timestamp_ms,
)
from ..db.post.base     import Post
from solariat.db.fields import ValidationError
from ..db.channel.base  import Channel, filtered_channels
from ..db.channel_stats import ChannelStats


@app.route('/channels_and_bookmarks/json', methods=['POST'])
@login_required()
def list_channels_with_bookmarks(user):
    """
    Get the list of channels with their bookmarks, in alphabetical
    order.
    """
    # First compose results
    results = []
    try:
        type(request.json) # workaround, don't touch that
    except:
        pass

    try:
        channels = filtered_channels(Channel.objects.find_by_user(user), filter_service=True)
        for channel in channels:
            results.append({
                    "channel_id": str(channel.id),
                    "channel_title": channel.title,
                    "bookmark_id": None,
                    "bookmark_title": None,
                    "type": "channel"})

        for bm in Bookmark.objects.find_by_user(user):
            if (bm.channels[0].account and user.account
                and bm.channels[0].account.id == user.account.id):
                results.append({
                        "channel_id": str(bm.channels[0].id),
                        "channel_title": bm.channels[0].title,
                        "bookmark_id": str(bm.id),
                        "bookmark_title": bm.title,
                        "type": "bookmark"})

        results.sort(key=lambda x: "%s%s" % (x['channel_title'],
                                             x['bookmark_title']))

        return jsonify( ok=True, list=results)

    except Exception, exc:
        app.logger.error('error on /channels_and_bookmarks/json',
                         exc_info=True)
        return jsonify(ok=False, error=str(exc))


@app.route('/bookmarks/json', methods=['GET', 'PUT', 'POST', 'DELETE'])
@login_required()
def bookmarks(user):
    app.logger.debug("Handling Bookmark Request.")
    if request.method == 'PUT':
        return _update_bookmark(user)

    if request.method == 'DELETE':
        return _delete_bookmark(user)

    if request.method == 'POST':
        app.logger.debug("Loading POST data.")
        data = json.loads(request.data)
        if not data:
            return jsonify(ok=False,
                           error='no parameters provided')

        bookmark_id = data.get('bookmark_id')
        if not bookmark_id:
            return jsonify(ok=False,
                           error='no bookmark id provided')

        return _toggle_bookmark(user, bookmark_id)

    return _get_bookmark(user)


def _toggle_bookmark(user, bookmark_id):
    """ Toggles state of bookmark between active and inactive"""
    try:
        app.logger.debug("Fetching Bookmark")
        bookmark = Bookmark.objects.get_by_user(user, bookmark_id)
        if bookmark.is_active == True:
            app.logger.debug("Withdrawing")
            bookmark.withdraw(refresh=True)
        else:
            app.logger.debug("Depoying")
            bookmark.deploy(refresh=True)
        return jsonify(ok=True, item=bookmark.to_dict())

    except Bookmark.DoesNotExist:
        return jsonify(
            ok=False,
            error="Bookmark with id %s does not exist" % bookmark_id)
    except Exception, exc:
        app.logger.error("error in handling bookmark: %s" % str(exc),
                         exc_info=True)
    return jsonify(ok=False, error='error on bookmark view')


def _get_bookmark(user):
    """Return bookmark for bookmark_id, or list
    of bookmarks for channel_id

    """
    data = request.args
    if not data:
        return jsonify(
            ok=False, error='no parameters provided')

    bookmark_id = data.get('bookmark_id')
    if bookmark_id:
        try:
            bookmark = Bookmark.objects.get_by_user(user, bookmark_id)
        except Bookmark.DoesNotExist:
            return jsonify(
                ok=False,
                error="Bookmark with id %s does not exist" % bookmark_id)
        try:
            return jsonify(ok=True, item=bookmark.to_display_dict(user))
        except Exception:
            app.logger.error("error in Bookmark.to_dict()", exc_info=True)
            return jsonify(ok=False, error='error on bookmark view')

    channel_id = data.get('channel_id')
    if channel_id:
        return jsonify(
            ok=True,
            list = [{'title':x.title, 'id': str(x.id)
                     } for x in Bookmark.objects.find_by_user(
                    user, owner=user, channels=channel_id)])

    return jsonify(
        ok=False, error='channel_id or bookmark_id should be provided')


def _update_bookmark(user):
    "Create or update Bookmark obj"
    data = request.json
    if not data:
        try:
            data = json.loads(request.data)
        except ValueError:
            return jsonify(
                ok=False, error='parameters as JSON should be provided')
    try:
        start = parse_date(data.get('start'))
        end   = parse_date(data.get('end'))
        if not start or not end:
            raise RuntimeError('start and end')
        title = data['title']

        if title == '':
            return jsonify(
                ok=False, error='A Title must be provided')

        channel_id = data['channel_id']
        intention_topics = data['terms']
        intention_types = [ get_sa_type_by_name(name)
                            for name in data['intentions'] ]

    except (RuntimeError, KeyError), exc:
        app.logger.error('error on update bookmark', exc_info=True)
        return jsonify(
            ok=False, error="%s parameter should be provided" % str(exc))

    bookmark = Bookmark.objects.find_one_by_user(user,
                                                 owner=user,
                                                 title=title)
    if not bookmark:
        try:
            bookmark = Bookmark.objects.create_by_user(
                user,
                title=title,
                intention_topics=intention_topics,
                intention_types=intention_types,
                channels=[channel_id],
                creative=' '.join(intention_topics),
                is_active=False,
                start=start,
                end=end)
        except ValidationError, exc:
            app.logger.error("Could not create Bookmark",
                             exc_info=True)
            return jsonify(ok=False, error=str(exc))
    else:
        try:
            if channel_id not in bookmark.channels:
                bookmark.channels.append(channel_id)
            bookmark.intention_types = intention_types
            bookmark.intention_topics = intention_topics
            bookmark.start = start
            bookmark.end = end
            bookmark.save_by_user(user)
        except ValidationError, exc:
            app.logger.error("Could not create Bookmark",
                             exc_info=True)
            return jsonify(ok=False, error=str(exc))

    return jsonify(
        ok=True, item=bookmark.to_display_dict(user))


def _delete_bookmark(user):
    "Removes bookmark"
    data = request.args
    if not data:
        return jsonify(
            ok=False, error='no parameters provided')

    bookmark_id = data.get('bookmark_id')
    if bookmark_id:
        try:
            bookmark = Bookmark.objects.get_by_user(user, bookmark_id)
        except Bookmark.DoesNotExist:
            return jsonify(
                ok=False,
                error="Bookmark with id %s does not exist" % bookmark_id)
    else:
        return jsonify(
            ok=False,
            error="No bookmark id")

    try:
        bookmark.delete_by_user(user)
        return jsonify(ok=True)
    except Exception:
        app.logger.error("error deleting Bookmark", exc_info=True)
        return jsonify(ok=False, error='Could not delete bookmark')


@app.route('/feedback/json', methods=['POST'])
@login_required()
def feedback(user):
    def force_unicode(s):
        if not isinstance(s, basestring):
            return s
        if not isinstance(s, unicode):
            return s.decode('utf-8')
        return s

    data = request.json
    if not data:
        return jsonify(ok=False, error='JSON data should be provided')
    for param in ['post_id', 'vote']:
        if not param in data:
            return jsonify(
                ok=False,
                error='"%s" parameter is not provided, got %s ' % (
                    param, str(data)))
    try:
        post = Post.objects.get_by_user(user, id=data['post_id'])
    except Response.DoesNotExist, ex:
        print ex
        return jsonify(ok=False, error='No such Post %s obj' % data['post_id'])

    topic = force_unicode(data.get('topic', None))
    intention = force_unicode(data.get('intention', None))

    if topic or intention:
        try:
            vote = int(data['vote'])
            assert(vote in [-1, 1])
        except:
            return jsonify(ok=False,
                error='Vote must be -1 or 1, got %s' % data['vote'])
        try:
            sa_idx = str(int(data['speech_act_id']))  # note: this is really sa_idx
            assert sa_idx >= 0
        except:
            return jsonify(ok=False, error='Speech act idx is missing')

        scope = 'intention' if intention else 'topic'
        value = intention or topic

        #Validate posted topic or intention
        valid_intentions, valid_topics = set([]), set([])
        for sa in post.speech_acts:
            intention_type_id = str(sa["intention_type_id"])
            intention_type = SATYPE_ID_TO_NAME_MAP[intention_type_id]
            valid_intentions.add(force_unicode(intention_type))
            for topic_content in sa["intention_topics"]:
                valid_topics.add(force_unicode(topic_content).lower())

        if scope == 'topic':
            if value.lower() not in valid_topics:
                return jsonify(ok=False, error="Topic not found.")
        else:
            if value not in valid_intentions:
                return jsonify(ok=False, error="Intention not found.")

        kw = {scope: value}
        current_vote = post.get_vote_for(user, sa_idx, **kw)

        if current_vote != 0:
            return jsonify(ok=False,
                error='You have already voted.')

        post.set_vote_for(user, vote, sa_idx, **kw)
        post.save()

        return jsonify(ok=True)
    else:
        if not data['vote'] in [False, True]:
            return jsonify(ok=False,
                           error='vote must be false or true, got %s' % data['vote'])
        try:
            post.set_vote(user, data['vote'])
            return jsonify(ok=True)
        except Exception:
            app.logger.error("Could not set vote", exc_info=True)
            return jsonify(ok=False, error='Internal error')


@app.route('/channel_stats/json', methods=['POST'])
@login_required()
def get_channel_stats(user):
    data = request.json

    if not data:
        return jsonify(ok=False, error='JSON data is required')

    for param in ['channel_id', 'from', 'to', 'level', 'stats_type']:
        if not data.get(param):
            return jsonify(
                ok    = False,
                error = '%s is not provided, got %s' % (param, data)
            )
    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist:
        return jsonify(ok=False, error='Channel %(channel_id)s does not exist' % data)

    try:
        from_dt, to_dt = parse_date_interval(data['from'], data['to'])
    except:
        return jsonify(
            ok    = False,
            error = '"from" and "to" parameters should be dates encoded like mm/dd/YY"'
        )
    level = data['level']

    try:
        if data['stats_type'] == 'speech_acts':
            if 'intention' not in data:
                raise RuntimeError('intention is not provided, got %s' % data)
            return _get_speech_acts_stats(
                user, channel, from_dt, to_dt, level, data['intention']
            )
        else:
            return _get_performance_stats(
                user, channel, from_dt, to_dt, level, data['stats_type']
            )
    except RuntimeError, exc:
        app.logger.error("on getting speech act stats", exc_info=True)
        return jsonify(ok=False, error=str(exc))
    except Exception, exc:
        app.logger.error("on getting speech act stats", exc_info=True)
        return jsonify(ok=False, error='Internal error')


def _get_channel_stats(user, channel, from_, to_, level):
    "Return QuerySet of ChannelStats for given parameters"

    return ChannelStats.objects.by_time_span(
        user,
        channel,
        start_time = from_,
        end_time   = to_,
        level      = level
    )

def _get_channel_stats_values(user, channel, from_, to_, level, stats_name):
    result = {}
    for stat in _get_channel_stats(user, channel, from_, to_, level):
        result[stat.time_slot] = getattr(stat, stats_name)
    return result

def _get_performance_stats(user, channel, from_, to_, level, stats_type):
    """ Return list of items for Performance stats graph

    """

    if not isinstance(stats_type, list):
        raise RuntimeError('stats_type should be an array')

    result = []
    for stype in stats_type:
        if stype not in ['number_of_posts', 'number_of_actionable_posts',
                         'number_of_impressions', 'number_of_clicks',
                         'number_of_rejected_posts']:
            raise RuntimeError("unsupported stats_type %s" % stype)

        values = _get_channel_stats_values(
            user, channel, from_, to_, level, stype)
        data = []
        count = 0
        for slot in gen_timeslots(from_, to_, level):
            value = values.get(slot, 0)
            data.append([timeslot_to_timestamp_ms(slot), value])
            count+=value
        result.append(dict(data=data, label=stype.split("_")[2], count=count))

    return jsonify(ok=True, list=result, level=level)

def _get_speech_acts_stats(user, channel, from_dt, to_dt, level, intention):
    ''' Get aggregate stats by intention types '''

    # Prepare result structure
    ts_counts   = defaultdict(int)  # {<timeslot>: <count>}
    total_count = 0
    int_id      = SAType.by_name(intention).oid

    for stat in _get_channel_stats(user, channel, from_dt, to_dt, level):
        count = stat.feature_counts.get(int_id, 0)
        total_count += count
        ts_counts[stat.time_slot] += count

    def _get_data(int_id):
        data = []
        for slot in gen_timeslots(from_dt, to_dt, level):
            timestamp = timeslot_to_timestamp_ms(slot)
            count     = ts_counts.get(slot, 0)
            data.append((timestamp, count))
        return data

    results = [  # a list with only one item for compatibility with the UI code
        dict(
            count = total_count,
            data  = _get_data(int_id),
            label = intention
        )
    ]

    return jsonify(ok=True, list=results, level=level)

