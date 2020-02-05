'''
Utilities for purging data.
'''

import inspect
import random

from time     import localtime
from socket   import gethostname
from datetime import timedelta, datetime, date

# from profilehooks import profile
from dateutil.relativedelta import relativedelta

from solariat.mail          import Message
from solariat_nlp.sa_labels import ALL_TYPES_IN_DISPLAY_ORDER, JUNK

from solariat_bottle.settings                import get_var, LOGGER
from solariat.db.fields import BytesField
from solariat.db.abstract import DBRef
from solariat_bottle.db.post.base            import Post
from solariat_bottle.db.channel.base         import Channel
from solariat_bottle.db.speech_act           import SpeechActMap, pack_speech_act_map_id
from solariat_bottle.db.conversation         import Conversation
from solariat_bottle.db.channel_stats        import ChannelStats
from solariat_bottle.db.channel_hot_topics   import ChannelHotTopics
from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
from solariat_bottle.app                     import app, MAIL_SENDER as mail

from .id_encoder import get_channel_num, POST_WIDTH, CHANNEL_WIDTH
from solariat.utils.timeslot import (
    gen_timeslots, now, datetime_to_timeslot, utc,
    decode_timeslot, TIMESLOT_EPOCH, TIMESLOT_LEVEL_NAMES)


F  = ChannelHotTopics.F
FT = ChannelTopicTrends.F
to_binary = BytesField().to_mongo
logger = LOGGER

CONCURRENCY = 4

BIGGEST_COUNTER_VALUE = (1<<16)
MARKED_TO_KEEP = 0

INTENTIONS_FOR_FETCHING = [x.oid for x in ALL_TYPES_IN_DISPLAY_ORDER]
INTENTIONS_FOR_FETCHING.remove(JUNK.oid)
VERIFICATION_DELTA  = 100

MSG_TEMPLATE = "Channel: %(channel)s | %(initial_count)d (initial_count) != %(marked)d (marked) + %(removed)d | (removed) %(marked)d (marked) + %(removed)d (removed) == %(real_sum)d "

def send_notification_for_team(subject, body=None):
    suffix = "| host: '%s' at %s'" % (gethostname(), datetime.now())
    subject = subject+suffix
    if body is None:
        body = subject
    with app.app_context():
        msg = Message(
            subject=subject,
            sender=get_var("MAIL_DEFAULT_SENDER"),
            recipients=get_var("SCRIPTS_EMAIL_LIST"),
            body=body)
        if get_var('APP_MODE') == 'prod':
            mail.send(msg)
        else:
            LOGGER.info(msg.subject)
            LOGGER.info(msg.body)


def purge_channels(channels_arg):
    from solariat_bottle.tasks       import io_pool
    from solariat_bottle.tasks.stats import purge_all_channel_stats
    io_pool.initialize()

    channels = []
    for ch in channels_arg:
        if not ch.is_service:
            channels.append(ch)
        else:
            LOGGER.info("channel '%s' wont be handled, because it is service channel" % ch.title)

    LOGGER.info("  preparing to purge stats for %s channels", len(channels))
    start_time = datetime.now()
    send_notification_for_team(subject="purge_hot_topics.py started")
    tasks = []
    for channel in channels:
        LOGGER.info("  asynchronously purging channel: %s", channel.title)
        task = purge_all_channel_stats.async(channel)
        tasks.append((channel, task))
    LOGGER.info("  created tasks num: %s", len(tasks))

    task_results = []
    for channel, task in tasks:
        result = task.result()
        task_results.append(result)
        LOGGER.info("task finished:: channel: %s; res: %s", channel.title, result)
    LOGGER.info("all tasks finished")

    # calculating time stats
    time_stats = {}
    timedelta_message = ""
    for key in ("discard_junk", "purge_months", "purge_days"):
        for result in task_results:
            time_stats.setdefault(key, []).append(result["timedeltas"][key+"_timedelta"])
    for key, stats in time_stats.items():
        timedelta_message += "final stats:: time stats:: type: %s; avg: %s; min: %s; max: %s;\n" % (
            key, sum(stats, timedelta(0))/len(stats), min(stats), max(stats))

    # calculating total stats
    total_stats = {}
    stats_message = ""
    for key in ("month_topic_stats", "month_trend_stats", "day_topic_stats", "day_trend_stats"):
        total_stats.setdefault(key, [0, 0, 0])
        for result in task_results:
            total_stats[key] = [x+y for x, y in zip(total_stats[key], result[key])]
        stats_message += "final stats:: %s: %d initially, %d marked + %d removed; %d (marked+removed) \n" % (
            key,
            total_stats[key][0],
            total_stats[key][1],
            total_stats[key][2],
            total_stats[key][1] + total_stats[key][2],
        )

    total_topics_day_count = 0
    total_topics_month_count = 0
    total_trends_day_count = 0
    total_trends_hour_count = 0
    for result in task_results:
        total_topics_day_count += result["discard_junk_stats"]["topics_day_count"]
        total_topics_month_count += result["discard_junk_stats"]["topics_month_count"]
        total_trends_day_count += result["discard_junk_stats"]["trends_day_count"]
        total_trends_hour_count += result["discard_junk_stats"]["trends_hour_count"]
    discard_junk_message = "final stats:: discard_junk: topic day: %s; topic month: %s\n; trends day: %s; trends hour: %s;" % (
        total_topics_day_count, total_topics_month_count, total_trends_day_count, total_trends_hour_count)

    # stats_message += "discard_junk_stats: %s\n" % discard_junk_stats
    total_time_delta = datetime.now()-start_time
    total_time_delta_message = "final stats:: timedelta of execution: %s; CONCURRENCY: %s \n" % (total_time_delta, CONCURRENCY)
    
    # LOGGER.info(stats_message)
    # LOGGER.info(discard_junk_message)
    # LOGGER.info(timedelta_message)
    # LOGGER.info(total_time_delta_message)

    body = stats_message + discard_junk_message + timedelta_message + total_time_delta_message
    body += "\n Channels: %s; " % len(channels)
    body += channels[0].title if len(channels) == 1 else ''
    LOGGER.info(body)
    send_notification_for_team(
        subject="purge_hot_topics.py finished",
        body=body)

def purge_stats(channel):
    "Task to purge topics for current time"

    t0 = datetime.now()
    discard_junk_stats = discard_junk(channel)
    discard_junk_timedelta = datetime.now()-t0
    LOGGER.info(
        "purging summary:: channel: %s; applying discard junk; records number: %s timedelta: %s",
        channel.title,
        discard_junk_stats,
        discard_junk_timedelta)

    t0 = datetime.now()
    purged_months, month_topic_stats, month_trend_stats = purge_months(channel)
    purge_months_timedelta = datetime.now()-t0
    LOGGER.info(
        "purging summary:: channel: %s; level: month; purge_months: %s; topics_stats: %s; trends_stats: %s; timedelta: %s",
        channel.title,
        [decode_timeslot(x) for x in purged_months],
        month_topic_stats,
        month_trend_stats,
        purge_months_timedelta)

    t0 = datetime.now()
    purged_days, day_topic_stats, day_trend_stats = purge_days(channel)
    purge_days_timedelta = datetime.now()-t0
    LOGGER.info(
        "purging summary:: channel: %s; level: day; purge_days: %s; topics_stats: %s; trends_stats: %s; timedelta: %s",
        channel.title,
        [decode_timeslot(x) for x in purged_days],
        day_topic_stats,
        day_trend_stats,
        purge_days_timedelta)

    # Update channels last_purge field and save it
    Channel.objects.coll.update(
        {"_id": channel.id},
        { '$set' : {'ld' : now()}}) # updating last_purged field

    stats = {
        "last_purged":  channel.last_purged,
        "purge_months": [decode_timeslot(x) for x in purged_months],
        "purge_days":   [decode_timeslot(x) for x in purged_days],
        "month_topic_stats":  month_topic_stats,
        "month_trend_stats":  month_trend_stats,
        "day_topic_stats":    day_topic_stats,
        "day_trend_stats":    day_trend_stats,
        "discard_junk_stats": discard_junk_stats,
        "timedeltas":         {
            "discard_junk_timedelta": discard_junk_timedelta,
            "purge_months_timedelta": purge_months_timedelta,
            "purge_days_timedelta": purge_days_timedelta,
        }
    }
    return stats

def discard_outdated_topics_for_day_level(channel):
    # Remove all days 2 weeks old or more
    channel_num = get_channel_num(channel)
    until_day = datetime_to_timeslot(now()-timedelta(days=get_var('HOT_TOPICS_DAY_STATS_KEEP_DAYS')), 'day')
    from_day  = datetime_to_timeslot(TIMESLOT_EPOCH, 'day')
    t0  = datetime.now()
    res = ChannelHotTopics.objects.coll.remove( { F('channel_num'): channel_num,
                                            F('time_slot') : { '$lt': until_day, '$gte': from_day}})
    LOGGER.info("purging Q:: channel: %s; collection: ChannelHotTopics; func: %s; timedelta: %s" % (
        channel.title, inspect.stack()[0][3], datetime.now()-t0))
    return res["n"]

def discard_outdated_topics_for_month_level(channel):
    # Remove all months
    channel_num = get_channel_num(channel)
    until_month = datetime_to_timeslot(now()-relativedelta(months=get_var('HOT_TOPICS_MONTH_STATS_KEEP_MONTHS')), 'month')
    from_month   = datetime_to_timeslot(TIMESLOT_EPOCH, 'month')
    t0  = datetime.now()
    res = ChannelHotTopics.objects.coll.remove( { F('channel_num'): channel_num,
                                            F('time_slot') : { '$lte': until_month, '$gte': from_month }})
    LOGGER.info("purging Q:: channel: %s; collection: ChannelHotTopics; func: %s; timedelta: %s" % (
        channel.title, inspect.stack()[0][3], datetime.now()-t0))
    LOGGER.info("discard_junk call (month): %s", res["n"])
    return res["n"]

def discard_outdated_trends_for_day_level(channel):
    months = get_var('TOPIC_TRENDS_DAY_STATS_KEEP_MONTHS')
    res = purge_outdated_trends_stats(ChannelTopicTrends, channel, 'day', months)
    return res

def discard_outdated_trends_for_hour_level(channel):
    days = get_var('TOPIC_TRENDS_HOUR_STATS_KEEP_DAYS')
    res = purge_outdated_trends_stats(ChannelTopicTrends, channel, 'hour', days)
    return res

def discard_junk(channel):
    '''
    From current time, work backwards to remove all extraneuous days and months
    '''
    topics_day_count = discard_outdated_topics_for_day_level(channel)
    topics_month_count = discard_outdated_topics_for_month_level(channel)

    trends_day_count = discard_outdated_trends_for_day_level(channel)
    trends_hour_count = discard_outdated_trends_for_hour_level(channel)

    return {
        "topics_day_count": topics_day_count,
        "topics_month_count": topics_month_count,
        "trends_day_count": trends_day_count,
        "trends_hour_count": trends_hour_count,
    }

def purge_months(channel):
    '''
    From now, purge months that we want to maintain in our history, that have not been
    purged yet.
    '''
    if channel.last_purged:
        range_start = utc(channel.last_purged)
    else:
        range_start = now() - relativedelta(months=2)

    mday = localtime().tm_mday

    if mday > 7:
        range_end = now()
    else:
        range_end = now() - relativedelta(months=1)

    months_to_purge = []

    trend_stats = [0, 0, 0]
    topic_stats = [0, 0, 0]
    if range_start <= range_end:
        months_to_purge = list(gen_timeslots(range_start, range_end, level='month'))

        for month in months_to_purge:
            topic_res   = mark_and_sweep_topics(channel, month)
            topic_stats = [x+y for x, y in zip(topic_stats, topic_res)]
            #LOGGER.debug("TOPIC STATS: %s", topic_res)
            trend_res   = purge_corresponding_trends(channel=channel, timeslot=month)
            trend_stats = [x+y for x, y in zip(trend_stats, trend_res)]

    return months_to_purge, topic_stats, trend_stats

def purge_days(channel):
    '''
    From now, purge days that we want to maintain in our history, that have not been
    purged yet.
    '''

    # for all the days in the intersection between [last_purged, today], [3 days ago, today]
    if channel.last_purged:
        range_start = utc(channel.last_purged)
    else:
        range_start = now() - relativedelta(days=14)

    days_to_purge = list(gen_timeslots(range_start, now(), level='day'))

    trend_stats = [0, 0, 0]
    topic_stats = [0, 0, 0]

    for day in days_to_purge:
        topic_res = mark_and_sweep_topics(channel, day)
        topic_stats = [x+y for x, y in zip(topic_stats, topic_res)]
        #LOGGER.debug("TOPIC STATS: %s", topic_res)
        trend_res   = purge_corresponding_trends(channel=channel, timeslot=day)
        trend_stats = [x+y for x, y in zip(trend_stats, trend_res)]

    return days_to_purge, topic_stats, trend_stats

def mark_to_remove(channel_or_tag, time_slot, counter):
    t0  = datetime.now()
    update = ChannelHotTopics.objects.coll.update(
        {F('channel_num') : get_channel_num(channel_or_tag),
        F('time_slot') : time_slot},
        { '$set' : { F('gc_counter') : counter }},
        multi=True)
    LOGGER.info("purging Q:: channel: %s; collection: ChannelHotTopics; func: %s; timedelta: %s" % (
        channel_or_tag.title, inspect.stack()[0][3], datetime.now()-t0))
    return update

def remove_records(counter):
    update = ChannelHotTopics.objects.coll.remove({ F('gc_counter'): counter })
    return update

def mark_items_to_keep_query(doc_ids):
    t0  = datetime.now()
    update = ChannelHotTopics.objects.coll.update(
        { '_id': { '$in': doc_ids }},
        { '$set': { F('gc_counter'): MARKED_TO_KEEP }},
        multi=True)
    LOGGER.info("purging Q:: collection: ChannelHotTopics; func: %s; timedelta: %s" % (
        inspect.stack()[0][3], datetime.now()-t0))
    return update

def mark_and_sweep_topics(channel_or_tag, time_slot, rank=None):
    '''
    Given any time slot, this algorithm will remove all root topics that
    are not in the top list
    '''

    # Reset everything with a counter. We use a random number generator so that
    # we have to be very specific on what to remove, to avoid accidents
    counter = random.randrange(MARKED_TO_KEEP + 1, BIGGEST_COUNTER_VALUE)
    update = mark_to_remove(channel_or_tag, time_slot, counter)
    initial_count = update['n']
    #logger.debug("Reset %s items" % initial_count)

    # Now recursively mark items to keep
    marked = mark_items_to_keep(channel_or_tag, time_slot, rank=rank)
    #logger.debug("Marked %d items to keep" % marked)

    # Now remove what is left
    update = remove_records(counter)
    removed = update['n']
    #logger.debug("Removed %d items" % removed)

    stats = initial_count, marked, removed
    if (initial_count > (marked + removed) + VERIFICATION_DELTA
        or
        initial_count < (marked + removed) - VERIFICATION_DELTA
    ):
        msg_info = {
            "channel": channel_or_tag.title, 
            "initial_count": initial_count, 
            "marked": marked, 
            "removed": removed,
            "real_sum": marked+removed
        }
        subject = """[!]checksum for topics FAILED during purging. Channel: %s""" % channel_or_tag.title
        body    = MSG_TEMPLATE % msg_info
        send_notification_for_team(subject=subject, body=body)
        LOGGER.warn(
            "invalid checksum for topics:: channel: %s; %d initially, %d marked, and %d removed", 
            channel_or_tag.title, 
            *stats)

    return stats

def mark_items_to_keep(channel_or_tag, time_slot, rank=None, parent=None, call_depth=0):
    '''
    Tail-recursive algorithm to mark top topics. Sets them to a RESET value. If rank
    is specified, use it, and divide by 2 each time, otherwise use the call_depth.
    '''

    # Sort out the topic limit
    if rank == None:
        topic_limit = get_var('PURGING_POLICY')[str(call_depth)]
    else:
        topic_limit = rank
        rank = max(rank / 2, 1)

    topics = fetch_child_topics(channel_or_tag, time_slot, topic_limit, parent)
    doc_ids  = [x for x in get_document_ids(channel_or_tag, time_slot, topics)]

    # Mark the children to keep them
    update = mark_items_to_keep_query(doc_ids)
    marked = update['n']

    if call_depth <= 1:
        for topic in topics:
            marked += mark_items_to_keep(channel_or_tag, time_slot, rank=rank, parent=topic, call_depth=call_depth+1)

    return marked

def fetch_child_topics(channel_or_tag, time_slot, limit, parent_topic=None):
    '''
    Query the top topics with his parent
    '''

    t0  = datetime.now()
    results = ChannelHotTopics.objects.by_time_span(channel=channel_or_tag,
                                                    parent_topic=parent_topic,
                                                    from_ts=time_slot,
                                                    intentions=INTENTIONS_FOR_FETCHING,
                                                    limit=limit)
    LOGGER.info("purging Q:: channel: %s; collection: ChannelHotTopics; func: %s; timedelta: %s" % (
        channel_or_tag.title, inspect.stack()[0][3], datetime.now()-t0))

    return [r['topic'] for r in results]

def get_document_ids(channel_or_tag, time_slot, topics):
    from ..db.speech_act import SpeechActMap

    for status in SpeechActMap.STATUS_NAME_MAP.keys():
        for topic in topics:
            yield ChannelHotTopics.make_id(channel_or_tag, time_slot, topic, status)

def trends_mark_to_remove(time_slot, channel_or_tag, counter):
    channel_ts_val = ChannelTopicTrends.make_channel_ts(channel_or_tag, time_slot)
    # import ipdb; ipdb.set_trace()
    t0  = datetime.now()
    res = ChannelTopicTrends.objects.coll.update(
        { FT("channel_ts"): to_binary(channel_ts_val) },
        { '$set' : { FT('gc_counter') : counter }},
        multi=True)
    LOGGER.info("purging Q:: channel: %s; collection: ChannelTopicTrends; func: %s; timedelta: %s" % (
        channel_or_tag.title, inspect.stack()[0][3], datetime.now()-t0))
    return res

def trends_mark_to_keep(time_slot, channel_or_tag, topics):
    channel_ts_val = ChannelTopicTrends.make_channel_ts(channel_or_tag, time_slot)
    t0  = datetime.now()
    res = ChannelTopicTrends.objects.coll.update({
            FT("channel_ts"): to_binary(channel_ts_val),
            FT('topic'): {"$in": topics+["__ALL__"]}
        },
        { '$set' : { FT('gc_counter') : MARKED_TO_KEEP }},
        multi=True)
    LOGGER.info("purging Q:: channel: %s; collection: ChanneTopicTrends; func: %s; timedelta: %s" % (
        channel_or_tag.title, inspect.stack()[0][3], datetime.now()-t0))
    return res

def trends_remove(counter):
    t0  = datetime.now()
    res = ChannelTopicTrends.objects.coll.remove({FT('gc_counter'): counter})
    LOGGER.info("purging Q:: collection: ChannelTopicTrends; func: %s; timedelta: %s" % (
        inspect.stack()[0][3], datetime.now()-t0))
    return res

def trends_find_topics(time_slot, channel_or_tag):
    channel_num = get_channel_num(channel_or_tag)
    # import ipdb; ipdb.set_trace(); assert False
    t0  = datetime.now()
    records = ChannelHotTopics.objects.coll.find({
        F('channel_num'): channel_num,
        F('time_slot') : time_slot,
        # F('gc_counter'): MARKED_TO_KEEP
    })
    LOGGER.info("purging Q:: channel: %s; collection: ChannelHotTopics; func: %s; timedelta: %s" % (
        channel_or_tag.title, inspect.stack()[0][3], datetime.now()-t0))
    topics = [x["tc"] for x in records]
    LOGGER.info("FIND TOPICS RES: %s %s", len(topics), decode_timeslot(time_slot))
    return topics

def mark_and_sweep_trends(channel_or_tag, time_slot, topics):
    counter          = random.randrange(MARKED_TO_KEEP + 1, BIGGEST_COUNTER_VALUE)
    marked_to_remove = trends_mark_to_remove(time_slot, channel_or_tag, counter)
    marked_to_keep   = trends_mark_to_keep(time_slot, channel_or_tag,  topics)
    remove_result    = trends_remove(counter)
    initial_count, marked, removed = marked_to_remove['n'], marked_to_keep['n'], remove_result['n']
    if (initial_count > (marked + removed) + VERIFICATION_DELTA
        or
        initial_count < (marked + removed) - VERIFICATION_DELTA
    ):
        msg_info = {
            "channel": channel_or_tag.title, 
            "initial_count": initial_count, 
            "marked": marked, 
            "removed": removed,
            "real_sum": marked+removed
        }
        subject = """[!]checksum for trends FAILED during purging. Channel: %s""" % channel_or_tag.title
        body    = MSG_TEMPLATE % msg_info
        send_notification_for_team(subject=subject, body=body)
        LOGGER.warn(
            "invalid checksum for trends:: channel: %s; %d initially, %d marked, and %d removed", 
            channel_or_tag.title, initial_count, marked, removed)
    return initial_count, marked, removed

def purge_channel_stats(channel):
    days       = get_var('CHANNEL_STATS_KEEP_DAYS')

    start_date = datetime(year=2012, month=1, day=1)
    end_date   = now()-timedelta(days=days)
    # end_date   = datetime(year=end_date.year, month=end_date.month, day=1)
    timeslots  = (
        (datetime_to_timeslot(start_date, level), datetime_to_timeslot(end_date, level)) \
        for level in TIMESLOT_LEVEL_NAMES
    )

    F = ChannelStats.F
    removed_count = 0
    for start_ts, end_ts in timeslots:
        t0  = datetime.now()
        res = ChannelStats.objects.coll.remove({
            F('time_slot') : { '$lte': end_ts, '$gt': start_ts },
            F('channel') : channel.id
        })
        LOGGER.info("purging Q:: channel: %s; collection: ChannelStats; func: %s; timedelta: %s" % (
            channel.title, inspect.stack()[0][3], datetime.now()-t0))
        removed_count += res['n']
    return removed_count

def purge_corresponding_trends(channel, timeslot):
    ts_date, ts_level = decode_timeslot(timeslot)
    sub_level         = {"month": "day", "day": "hour"}[ts_level]
    range_start       = ts_date

    if "month" == ts_level:
        range_end = ts_date + relativedelta(months=1)
    else:
        range_end = ts_date + relativedelta(days=1)

    timeslots_to_purge = list(gen_timeslots(range_start, range_end, level=sub_level))[:-1]
    topics             = trends_find_topics(timeslot, channel)
    trend_stats        = [0, 0, 0]

    total_number = len(timeslots_to_purge)
    for i, ts in enumerate(timeslots_to_purge):
        LOGGER.info('timeslot info: channel: %s; current timeslot "%s"; %sth timeslot of %s timeslots',
            channel.title, decode_timeslot(ts), i, total_number)
        trend_res = mark_and_sweep_trends(channel, ts, topics)
        trend_stats = [x+y for x, y in zip(trend_stats, trend_res)]
    return tuple(trend_stats)

def purge_outdated_trends_stats(coll, channel, level, delta):
    initial_timedelta_arg_name = {"hour": "days", "day": "months"}[level]
    timedelta_arg_name         = {"hour": "hours", "day": "days"}[level]
    start_dt       = now() - relativedelta(**{initial_timedelta_arg_name: delta})
    current_dt     = start_dt 
    time_step      = relativedelta(**{timedelta_arg_name: 1})
    ts             = datetime_to_timeslot(current_dt, level)
    zero_counts    = 0
    total_records_removed = 0
    EMPTY_SLOTS_NUMBER    = 10
    while zero_counts <= EMPTY_SLOTS_NUMBER:
        t0         = datetime.now()
        channel_ts_val = ChannelTopicTrends.make_channel_ts(channel, ts)
        res = coll.objects.coll.remove(coll.objects.get_query(time_slot=ts))
        if res['n'] == 0:
            zero_counts += 1
        current_dt = current_dt - time_step
        total_records_removed += res['n']
        ts         = datetime_to_timeslot(current_dt, level)
        LOGGER.info("purging Q:: collection: %s; func: %s; timedelta: %s; date: %s; level: %s; records removed: %s",
            coll.__name__, inspect.stack()[0][3], datetime.now()-t0, current_dt, level, res['n'])
    return total_records_removed

# def purge_outdated_topic_trends(channel):
#     days=get_var('TOPIC_TRENDS_HOUR_STATS_KEEP_DAYS')
#     months=get_var('TOPIC_TRENDS_DAY_STATS_KEEP_MONTHS')
#     hour_records_removed = purge_outdated_trends_stats(ChannelTopicTrends, channel, 'hour', delta=days)
#     day_records_removed = purge_outdated_trends_stats(ChannelTopicTrends, channel, 'day', delta=months)
#     return hour_records_removed, day_records_removed

def purge_channel_entities(channel, run_in_prod_mod=False, now_date=None):
    """ purges outdated and unused Conversation, Post, SpeechActMap, Response entities """
    total_stats = [0, 0, 0, 0]

    today_dt = now_date if now_date else utc(now())
    delta    = relativedelta(days=get_var("CHANNEL_ENTITIES_KEEP_DAYS"))
    to_dt    = today_dt - delta

    query_type = "remove" if run_in_prod_mod else "find"

    # removing Conversations
    t0 = datetime.now()
    post_ids = []
    if channel.is_service or channel.is_smart_tag:
        channel_arg = str(channel.id)
    elif hasattr(channel, "parent_channel"):
        if channel.parent_channel is not None:
            channel_arg = Channel.objects.get(id=str(channel.parent_channel), include_safe_deletes=True).id
        else:
            channel_arg = channel.id
    else:
        raise Exception("Don't know how to handle channel: %s; %s" % (type(channel), channel.title))
    for conv in Conversation.objects.coll.find({'cl': channel_arg, 'lm': {'$lt': to_dt}}):
        post_ids += conv['p']
    conv_res = getattr(Conversation.objects.coll, query_type)({
        'cl': channel_arg,
        'lm': {'$lt': to_dt}
    })
    LOGGER.info("purging Q:: channel: %s; collection: Conversation; func: %s; timedelta: %s" % (
        channel.title, inspect.stack()[0][3], datetime.now()-t0))

    # removing Posts
    t0         = datetime.now()
    slice_size = 10
    post_res   = 0
    post_ids_slices = map(None, *(iter(post_ids),) * slice_size)
    for ids in post_ids_slices:
        post_res_temp = getattr(Post.objects.coll, query_type)({'_id': {'$in': ids}})
        post_res_temp = post_res_temp['n'] if run_in_prod_mod else post_res_temp.count()
        post_res += post_res_temp
    LOGGER.info("purging Q:: channel: %s; collection: Post; func: %s; timedelta: %s" % (
        channel.title, inspect.stack()[0][3], datetime.now()-t0))


    # removing SpeechActMaps
    sas_res  = 0
    for status in SpeechActMap.STATUS_NAME_MAP.keys():
        if 0 <= channel.counter < (1<<CHANNEL_WIDTH):
            # remove by id range
            lower_bound = pack_speech_act_map_id(  #{
                channel=channel,
                status=status,
                timeslot=datetime_to_timeslot(TIMESLOT_EPOCH),
                post=0)
            upper_bound = pack_speech_act_map_id(  #{
                channel=channel,
                status=status,
                timeslot=datetime_to_timeslot(to_dt),
                post=POST_WIDTH)

            t0 = datetime.now()
            sas_res_temp = getattr(SpeechActMap.objects.coll, query_type)({
                "_id": {"$gte": to_binary(lower_bound), "$lt": to_binary(upper_bound)}
            })
            LOGGER.info("purging Q:: channel: %s; collection: SpeechActMap; func: %s; timedelta: %s" % (
                channel.title, inspect.stack()[0][3], datetime.now()-t0))
            sas_res_temp = sas_res_temp['n'] if run_in_prod_mod else sas_res_temp.count()
            sas_res += sas_res_temp
        else:
            # remove by post ids
            LOGGER.info("channel counter is not in range %s %s : %s" % (0, (1<<CHANNEL_WIDTH), channel.counter))
            post_ids_slices = map(None, *(iter(post_ids),) * slice_size)
            for post_ids in post_ids_slices:
                t0 = datetime.now()
                sas_res_temp = getattr(SpeechActMap.objects.coll, query_type)({
                    SpeechActMap.post.db_field: {"$in": post_ids}
                })
                LOGGER.info(
                    "purging Q:: channel: %s; collection: SpeechActMap; func: %s; timedelta: %s" % (
                        channel.title, inspect.stack()[0][3], datetime.now() - t0))
                sas_res_temp = sas_res_temp['n'] if run_in_prod_mod else sas_res_temp.count()
                sas_res += sas_res_temp

    if run_in_prod_mod:
        total_stats = [conv_res['n'], post_res, sas_res] #, resp_res['n']]
    else:
        total_stats = []

        t0 = datetime.now()
        total_stats.append(conv_res.count())
        LOGGER.info("purging Q:: channel: %s; collection: Conversation; func: %s; timedelta: %s" % (
            channel.title, inspect.stack()[0][3], datetime.now()-t0))

        total_stats.append(post_res)
        total_stats.append(sas_res)


    return total_stats

def purge_channel_outdated_posts_and_sas(channel, now_date=None, run_in_prod_mod=False):
    """ 
    purges outdated posts and sas 
    basing on CHANNEL_ENTITIES_KEEP_DAYS setting
    """
    today_dt = now_date if now_date else utc(now())
    delta    = relativedelta(days=get_var("CHANNEL_ENTITIES_KEEP_DAYS"))
    to_dt    = today_dt - delta

    # counting chunks
    CHUNK_SIZE = 100
    post_number = Post.objects(channels=str(channel.id), _created__lt=to_dt).count()
    res = {'post_total': 0, 'sas_total': 0}
    if not post_number:
        LOGGER.info("purge_outdated_posts:: %s: no posts to purge" % channel.title)
        return res
    chunks_number = post_number/CHUNK_SIZE + 1
    start_dt = datetime.now()

    # handling posts and sas chunk by chunk
    for i in range(chunks_number):
        offset = i*CHUNK_SIZE
        t0 = datetime.now()
        # getting posts for removal
        if run_in_prod_mod:
            post_query  = Post.objects(channels=str(channel.id), _created__lt=to_dt).limit(CHUNK_SIZE)
        else:
            post_query  = Post.objects(channels=str(channel.id), _created__lt=to_dt).limit(CHUNK_SIZE).skip(offset)
        posts  = [p for p in post_query]
        post_query = None
        LOGGER.info('purge_outdated_posts:: %s: chunk #%s of %s chunks (%s posts_number; post query timedelta: %s', 
                    channel.title, i, chunks_number, post_number, datetime.now()-t0)
        post_ids = [long(p.id) if isinstance(p.id, (str, unicode)) and p.id.isdigit() else p.id for p in posts]
        
        if run_in_prod_mod:
            # perform actual removal
            t0 = datetime.now()
            sas_res = SpeechActMap.objects.coll.remove(SpeechActMap.objects.get_query(post__in=post_ids))
            post_res = Post.objects.coll.remove(Post.objects.get_query(id__in=post_ids))
            LOGGER.info(
                'purge_outdated_posts:: %s: post removed: %s; sas removed: %s;'
                ' chunk #%s of %s chunks; sas and post'
                ' remove queries timedelta: %s',
                channel.title, post_res['n'], sas_res['n'],
                i, chunks_number,
                datetime.now()-t0)
            res['post_total'] += post_res['n']
            res['sas_total'] += sas_res['n']
        else:
            t0 = datetime.now()
            # getting sas for removal
            sas = [s for s in SpeechActMap.objects(post__in=post_ids)]
            LOGGER.info('purge_outdated_posts:: %s: chunk #%s of %s chunks; sas count: %s; sas query timedelta: %s', 
                        channel.title, i, chunks_number, len(sas), datetime.now()-t0)
            res['post_total'] += len(posts)
            res['sas_total'] += len(sas)
    LOGGER.info('purge_outdated_posts:: %s: total timedelta: %s; stats: %s', channel.title, datetime.now()-start_dt, res)
    return res
    

