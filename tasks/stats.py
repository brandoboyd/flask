# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from math      import ceil
from datetime  import datetime
from calendar  import monthrange
from itertools import product

from solariat_bottle.settings import get_var
from solariat_bottle.workers  import io_pool
from solariat_bottle.settings import get_var
from solariat.utils.timeslot  import timeslot_to_datetime, gen_timeslots


logger = io_pool.logger

MAX_BATCH_SIZE = 10000 # The actual max batch call for one mongo post fetch


# --- IO-worker initialization ----

@io_pool.prefork  # IO-workers will run this before forking
def pre_import_stats():
    """ Master init
        Pre-importing heavy modules with many dependencies here
        to benefit from the Copy-on-Write kernel optimization.
    """
    logger.info('pre-importing stats dependencies')

    import solariat_bottle.db.speech_act
    import solariat_bottle.db.post.utils
    import solariat_bottle.db.channel.utils
    import solariat_bottle.db.channel_trends
    import solariat_bottle.db.channel_stats_base
    import solariat_bottle.db.channel_hot_topics
    import solariat_bottle.db.channel_topic_trends

    import solariat_bottle.utils.stats
    import solariat_bottle.utils.purging
    import solariat_bottle.utils.topic_tree

    # to disable a pyflakes warnings
    del solariat_bottle


# --- utils ---

def _generate_daily_hour_buckets(from_date, to_date):
    """ Generate a list of hour level timeslots, for each day from the interval. """
    timeslot_ranges = []
    day_timeslots = gen_timeslots(from_date, to_date, level='day')
    for ts in day_timeslots:
        from_date_d = timeslot_to_datetime(ts)
        to_date_d = from_date_d.replace(hour=23, minute=59)
        hourly_levels = list(gen_timeslots(from_date_d, to_date_d, level='hour'))
        timeslot_ranges.append(hourly_levels)
    return timeslot_ranges

def _compute_sam_match_query(channels_list, from_timeslot, to_timeslot):
    """ Compute the query which would match all speech acts for the given
    channels list, in the timeslot interval (from - to)"""
    from solariat.db.fields               import BytesField
    from solariat_bottle.db.speech_act    import SpeechActMap, pack_speech_act_map_id
    from solariat_bottle.utils.id_encoder import BIGGEST_POST_VALUE

    to_binary = BytesField().to_mongo
    match_query_base = []
    for channel in channels_list:
        for status in SpeechActMap.STATUS_NAME_MAP.keys():
            # compute id bounds for all posts for this slot
            id_lower_bound = pack_speech_act_map_id(channel, status, from_timeslot, 0)
            id_upper_bound = pack_speech_act_map_id(channel, status, to_timeslot, BIGGEST_POST_VALUE)
            match_query_base.append({'_id': { "$gte": to_binary(id_lower_bound), "$lte": to_binary(id_upper_bound)}})

    day_speech_act_filter = {"$or": match_query_base }
    return day_speech_act_filter

def _process_channel(channel, post_list, month_timeslots, ignore_purging=True, levels=('hour', 'day'),
                    cts_cache=None):
    """ Given a post list. Process all the posts for this """
    from solariat_nlp.utils.topics import gen_speech_act_terms
    from solariat_bottle.utils.stats      import _prepare_stats_increments
    from solariat_bottle.db.speech_act    import SpeechActMap

    top_topics = set([])
    if not ignore_purging:
        top_topics = set([])
        for time_slot in month_timeslots:
            _get_top_topics(channel, time_slot, top_topics, 0)
    chts_cache = {}
    ctts_cache = {}
    for post in post_list:
        # This is only needed if we also do the check of correctness
        if not post.get_assignment(channel):
            continue

        top_terms = []
        for speech_act in post.speech_acts:
            terms = gen_speech_act_terms(speech_act, channel=channel, post=post, include_all=True)
            for term in terms:
                if term[0] in top_topics or ignore_purging:
                    top_terms.append(term[0])

        if channel.is_smart_tag and (str(channel.id) not in post.tag_assignments
            or SpeechActMap.STATUS_MAP[post.get_assignment(channel, tags=True)] == SpeechActMap.REJECTED):
            continue

        context = {}
        if channel.is_smart_tag:
            update_context = post._get_last_update_context(channel)
            if update_context and not update_context['outbound_stats']:
                # see reset_outbound so SpeechActMap.reset() works
                context['reset_outbound'] = True
            context.update(update_context)

            old_status = post.tag_assignments.get(str(channel.id))
            context["old_status"] = old_status
        else:
            if SpeechActMap.STATUS_MAP[post.get_assignment(channel)] == SpeechActMap.ACTUAL:
                reply_context_history = post._reply_context.get(str(channel.id), [])
                if reply_context_history:
                    reply_context = reply_context_history[-1]
                    if 'a' in reply_context:
                        context['agent'] = reply_context['a']
                    if 'os' in reply_context:
                        context['outbound_stats'] = reply_context['os']
        _prepare_stats_increments(post, status=None, channel=channel, is_new=True, ctts_cache=ctts_cache,
                                  chts_cache=chts_cache, cts_cache=cts_cache, levels=levels,
                                  terms_list=top_terms, **context)
    return chts_cache, ctts_cache

def _get_top_topics(channel, time_slot, topic_set, depth, parent=None):
    """ Return the top topics for a given channel and timeslot. Update
    a topic_set parameter as you go 'down' from unigrams to bigrams and trigrams """
    from solariat_bottle.utils.purging import fetch_child_topics

    topic_limit = get_var('PURGING_POLICY')[str(depth)]
    topics = fetch_child_topics(channel, time_slot, topic_limit, parent)
    topic_set.update(topics)
    if depth <= 1:
        for topic in topics:
            _get_top_topics(channel, time_slot, topic_set, depth + 1, topic)


def _upsert_channel_topic_trends(ctts_stats, partial_keys=None):
    """ For channel topic trends we already computed the hour/day
    level stats and we do not keep any month level stats. So we can
    just upsert what we have computed."""
    from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
    from solariat_bottle.db.channel_stats_base   import CountDict, batch_insert

    partial_keys = set([]) if partial_keys is None else partial_keys
    if partial_keys:
        # We need to keep track of the daily stats we partialy upserted. Keeping the whole
        # thing in memory will cost A LOT, especially since we need this for all the channels
        # so we will only keep post ids
        existing_keys = list(set(ctts_stats.keys()).intersection(partial_keys))
        batches = int(ceil(len(existing_keys) / float(MAX_BATCH_SIZE)))
        for stat_batch_idx in xrange(batches):
            stat_ids = existing_keys[stat_batch_idx * MAX_BATCH_SIZE:(stat_batch_idx + 1) * MAX_BATCH_SIZE]
            for ctt in ChannelTopicTrends.objects.coll.find({'_id' : {'$in' : stat_ids}}):
                for es in ctt['es']:
                    es_key = (es['at'], es['if'], es['in'], es['le'])
                    if es_key in ctts_stats[ctt['_id']].embedded_dict:
                        ctts_stats[ctt['_id']].embedded_dict[es_key].update({'topic_count' : es['tt']})
                    else:
                        ctts_stats[ctt['_id']].embedded_dict[es_key] = CountDict({'topic_count' : es['tt']})
    removable_keys = []
    insertable_values = []
    for key in ctts_stats.keys():
        removable_keys.append(key)
        computed = ctts_stats.pop(key)
        computed.version = 0
        insertable_values.append(computed)

    if removable_keys:
        ChannelTopicTrends.objects.coll.remove({'_id' : {'$in' : removable_keys}})

    batch_insert(insertable_values)
    partial_keys.update(removable_keys)
    return partial_keys

def _upsert_channel_hot_topics(chts_stats, partial_keys=None):
    """ For channel hot topics we don't keep hour level stats. Everything
    we computed is on a day level, but we need to integrate them into a
    monthly level in case there are any differences. """
    from solariat_bottle.db.channel_hot_topics import ChannelHotTopics
    from solariat_bottle.db.channel_stats_base import CountDict, batch_insert

    partial_keys = set([]) if partial_keys is None else partial_keys
    if partial_keys:
        # We need to keep track of the daily stats we partialy upserted. Keeping the whole
        # thing in memory will cost A LOT, especially since we need this for all the channels
        # so we will only keep post ids
        existing_keys = list(set(chts_stats.keys()).intersection(partial_keys))
        batches = int(ceil(len(existing_keys) / float(MAX_BATCH_SIZE)))
        for stat_batch_idx in xrange(batches):
            stat_ids = existing_keys[stat_batch_idx * MAX_BATCH_SIZE:(stat_batch_idx + 1) * MAX_BATCH_SIZE]
            for cht in ChannelHotTopics.objects.coll.find({'_id' : {'$in' : stat_ids}}):
                for es in cht['es']:
                    es_key = (es['at'], es['if'], es['in'], es['le'])
                    if es_key in chts_stats[cht['_id']].embedded_dict:
                        chts_stats[cht['_id']].embedded_dict[es_key].update({'topic_count' : es['tt']})
                    else:
                        chts_stats[cht['_id']].embedded_dict[es_key] = CountDict({'topic_count' : es['tt']})
    removable_keys = []
    insertable_values = []
    for key in chts_stats.keys():
        computed = chts_stats.pop(key)
        removable_keys.append(key)
        computed.version = 0
        insertable_values.append(computed)

    ChannelHotTopics.objects.coll.remove({'_id' : {'$in' : removable_keys}})
    batch_insert(insertable_values)
    partial_keys.update(removable_keys)
    return partial_keys

def _memory_usage_psutil():
    # return the memory usage in MB
    import os
    import psutil
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    mem_resident = mem_info[0] / float(2 ** 20)
    mem_virtual = mem_info[1] / float(2 ** 20)
    logger.info("Memory usage is %s MiB Resident, %s MiB Virtual" % (mem_resident, mem_virtual))
    logger.info("..............................................")

def _upsert_channel_trends(cts_cache):
    """ For channel topic trends we already computed the hour/day
    level stats and we do not keep any month level stats. So we can
    just upsert what we have computed."""
    from solariat_bottle.db.channel_trends     import ChannelTrends
    from solariat_bottle.db.channel_stats_base import batch_insert

    removable_keys = []
    insertable_values = []
    for channel in cts_cache:
        channel_status = cts_cache[channel]
        for key in channel_status.keys():
            removable_keys.append(key)
            computed = channel_status.pop(key)
            computed.version = 0
            insertable_values.append(computed)

    ChannelTrends.objects.coll.remove({'_id' : {'$in' : removable_keys}})
    batch_insert(insertable_values)

def _update_monthly_cht_values(channel, from_date_end, to_date_end, topics):
    """ Do upsert on monthly values based on the daily values.
    """
    from solariat.utils.timeslot          import datetime_to_timeslot
    from solariat_bottle.utils.id_encoder        import get_topic_hash
    from solariat_nlp.utils.topics               import get_subtopics

    from solariat_bottle.db.speech_act           import SpeechActMap
    from solariat_bottle.db.channel_hot_topics   import ChannelHotTopics
    from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
    from solariat_bottle.db.channel_stats_base   import CountDict, batch_insert

    start_time = datetime.now()
    statuses = SpeechActMap.STATUS_NAME_MAP.keys()
    insertable_values = {}

    if not topics:
        logger.warning("No topics found for channel %s." % (channel.title, ))
        return

    month_intervals = _generate_day_level_ranges(from_date_end, to_date_end)
    for topic in topics:
        for from_date, to_date in month_intervals:
            or_query = []
            # $match query
            for topic, status in product([topic], statuses):
                from_id = ChannelTopicTrends.make_id(channel, datetime_to_timeslot(from_date, 'day'),
                                                     topic, status)
                to_id = ChannelTopicTrends.make_id(channel, datetime_to_timeslot(to_date, 'day'),
                                                   topic, status)
                or_query.append({"_id": {"$gte": from_id, "$lte": to_id}})

            if len(or_query) == 1:
                match_query = or_query[0]
            else:
                match_query = {"$or": or_query}

            pipeline = [
                {"$match": match_query},
                {"$unwind": '$es'},
                {'$group': {'_id': {'grp_at': '$es.at',
                                    'grp_if': '$es.if',
                                    'grp_in': '$es.in',
                                    'grp_le': '$es.le',
                                    'grp_tc': '$tc',
                                    'grp_ss': '$ss'},
                            'count': {'$sum': '$es.tt'}}}
            ]
            month_level_counts = {}
            agreggation_result = ChannelHotTopics.objects.coll.aggregate(pipeline)
            if agreggation_result['ok']:
                for aggregated_count in agreggation_result['result']:
                    month_id = ChannelHotTopics.make_id(
                        channel   = channel,
                        time_slot = datetime_to_timeslot(from_date, 'month'),
                        topic     = aggregated_count['_id']['grp_tc'],
                        status    = aggregated_count['_id']['grp_ss']
                    )
                    if month_id in month_level_counts:
                        month_doc = month_level_counts[month_id]
                    else:
                        hashed_parents = map(
                            get_topic_hash,
                            get_subtopics(aggregated_count['_id']['grp_tc'])
                        )
                        month_doc = ChannelHotTopics(
                            channel        = channel,
                            hashed_parents = hashed_parents,
                            time_slot      = datetime_to_timeslot(from_date, 'month'),
                            topic          = aggregated_count['_id']['grp_tc'],
                            status         = aggregated_count['_id']['grp_ss']
                        )
                        month_doc.version = 0
                        month_doc.embedded_dict = {}
                        month_level_counts[month_id] = month_doc

                    es_key = (
                        aggregated_count['_id']['grp_at'],
                        aggregated_count['_id']['grp_if'],
                        aggregated_count['_id']['grp_in'],
                        aggregated_count['_id']['grp_le']
                    )
                    # Default increment for all existign stats to 0, we will add to this later.
                    month_doc.embedded_dict[es_key] = CountDict({'topic_count' : aggregated_count['count']})
                for key in month_level_counts:
                    insertable_values[key] = month_level_counts[key]
            else:
                logger.warning("Pipeline failed. Returned %s." % agreggation_result)

    if insertable_values:
        ChannelHotTopics.objects.coll.remove({'_id' : {'$in' : insertable_values.keys()}})
    batch_insert(insertable_values.values())
    logger.info("Integrating monthly level topics took: " + str(datetime.now() - start_time))

def _generate_day_level_ranges(from_date, to_date):
    """ Generate a bunch of [from-date, to-date] ranges for each month in the interval. """
    timeslot_ranges = []
    month_timeslots = gen_timeslots(from_date, to_date, level='month')
    for ts in month_timeslots:
        from_date_m = timeslot_to_datetime(ts)
        timeslot_ranges.append(_get_month_day_range(from_date_m))
    return timeslot_ranges

def _get_month_day_range(date):
    """
    For a date 'date' returns the start and end date for the month of 'date'.

    Month with 31 days:
    >>> date = datetime.date(2011, 7, 27)
    >>> get_month_day_range(date)
    (datetime.date(2011, 7, 1), datetime.date(2011, 7, 31))

    Month with 28 days:
    >>> date = datetime.date(2011, 2, 15)
    >>> get_month_day_range(date)
    (datetime.date(2011, 2, 1), datetime.date(2011, 2, 28))
    """
    first_day = date.replace(day = 1)
    last_day = date.replace(day = monthrange(date.year, date.month)[1])
    return first_day, last_day


# --- Stats tasks ----

@io_pool.task
def compute_account_stats(account, idx, from_date, to_date, levels=('hour', 'day'), output_stream=None,
                          raise_on_diffs=False, test_mode=True, ignore_purging=False, ignore_topics=False):
    from solariat_bottle.db.channel.base import Channel
    from solariat_bottle.db.post.utils   import get_platform_class
    from solariat_bottle.db.speech_act   import SpeechActMap
    from solariat.utils.timeslot  import gen_timeslots

    start_processing = datetime.now()
    all_channels = Channel.objects.find(account=account)[:]
    all_channels = [c for c in all_channels if not c.is_service]

    if not all_channels: return
    Post = get_platform_class(all_channels[0].platform)
    computed_months = list(gen_timeslots(from_date, to_date, level='month'))

    base_channels = [c for c in all_channels if not c.is_smart_tag]
    timeslot_ranges = _generate_daily_hour_buckets(from_date, to_date)
    post_count = 0
    for day_timeslot in timeslot_ranges:
        # Since we don't want to get the posts for every channel, but we also want to keep
        # post batches small so we don't overflow memory, then we need to do partial upserts
        # on a hourly timeslot basis on day level basis trends. In order to do this we need
        # to keep track of which stats were partially computed so we increment values instead
        # of just removing + batch inserting
        partial_updates = {}
        channel_trends_caches = {}
        for channel in all_channels:
            partial_updates[channel.id] = {'ctt' : set([]), 'cht' : set([])}
            channel_trends_caches[channel.id] = {}

        day_speech_act_filter = _compute_sam_match_query(base_channels, day_timeslot[0], day_timeslot[-1])
        post_ids = [sa['pt'] for sa in SpeechActMap.objects.coll.find(day_speech_act_filter)]

        if len(post_ids) > MAX_BATCH_SIZE:
            ## This is really in case of very high load channels. Go in batches of maximum
            ## MAX_BATCH_SIZE so we don't lock mongo connection
            sams_batches = int(ceil(len(post_ids) / float(MAX_BATCH_SIZE)))
        else:
            sams_batches = 1
        for sams_batch_idx in xrange(sams_batches):
            # Go in MAX_BATCH_SIZE increments through the posts
            from_idx = sams_batch_idx * MAX_BATCH_SIZE
            to_idx = (sams_batch_idx + 1) * MAX_BATCH_SIZE
            posts = Post.objects.find(id__in=post_ids[from_idx:to_idx])[:]
            for channel in all_channels:
                # For now always ignore purging, it's a huge performance leak
                if not ignore_topics:
                    chts_cache, ctts_cache = _process_channel(channel, posts, computed_months,
                                                             True, levels, channel_trends_caches[channel.id])
                    # Now do the partial updates on hourly level stats
                    _upsert_channel_topic_trends(ctts_cache, partial_keys=partial_updates[channel.id]['ctt'])
                    _upsert_channel_hot_topics(chts_cache, partial_keys=partial_updates[channel.id]['cht'])
                else:
                    _process_channel(channel, posts, computed_months,
                                    True, levels, channel_trends_caches[channel.id])
            post_count += len(posts)

        logger.info("Finished processing %s posts in %s " %(post_count, datetime.now() - start_processing))
        _memory_usage_psutil()

        _upsert_channel_trends(channel_trends_caches)

    for channel in all_channels:
        days_to_purge = list(gen_timeslots(from_date, to_date, level='day'))
        top_topics = set([])
        for time_slot in days_to_purge:
            _get_top_topics(channel, time_slot, top_topics, 0)
        if not ignore_topics:
            _update_monthly_cht_values(channel, from_date, to_date, top_topics)

    logger.info("Computed stats computations for account %s with post count %s in %s." % (
                                                        account.name, post_count, datetime.now() - start_processing))

@io_pool.task(result='ignore')
def purge_all_channel_stats(channel):
    "Task to purge topics for current time"
    from solariat_bottle.utils.purging import purge_stats
    return purge_stats(channel)


@io_pool.task
def update_conversation_stats(conversation, closing_time, quality):
    from solariat_bottle.utils.stats import _update_conversation_stats
    _update_conversation_stats(conversation, closing_time, quality)

