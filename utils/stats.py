# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from itertools                import product
from solariat_nlp.sa_labels   import SATYPE_TITLE_TO_ID_MAP
from solariat_bottle.settings import get_var, LOGGER
from solariat_nlp.utils.topics import gen_speech_act_terms

from solariat.db import fields
from solariat.utils.timeslot import datetime_to_timeslot

from solariat.db.abstract import Document



DEBUG_STATS = get_var('DEBUG_STATS', False)

seq_types = (list, tuple, set)


class PostStats(Document):
    id = fields.CustomIdField()
    stats_updates = fields.ListField(fields.DictField())

class DebugInfo(dict):
    """
    Custom dictionary class used for debugging purposes
    """
    def append(self, status, n, params):
        update_params = {
            "status": status,
            "n": n}
        update_params.update(params)
        update_params['channel_title'] = update_params['channel'].title
        update_params['channel'] = update_params['channel'].id
        self["updates"].append(update_params)


def remove_zero_counts(results):
    """
    Returns only those items that have count not equal to zero.
    """
    # we compare leave items that have non zero count
    # and also items that do not have count field
    results = [r for r in results if not r.get('count', None) == 0]
    return results

def fix_for_neg_value(results, params, pipeline):
    ''' Workaround for negative values so we do not destroy the UI'''
    fixed = False
    for r in results:
        for p in params:
            if p not in r:
                break
            if r[p] != abs(r[p]):
                fixed = True
            r[p] = abs(r[p])
    if fixed:
        LOGGER.error("Negative counts for %s query", pipeline)


def increment_post_stats(channel=None, time_slot=None, level='hour',
                         status=None, agent=None, lang_id=None,
                         inc_dict=None, n=1, cts_cache=None):
    """ Increment channel trends post conts on stats updates """
    if level != 'month':
        from ..db.channel_trends import ChannelTrends

        channel_trend_id = ChannelTrends.make_id(channel, status, time_slot)

        ct = cts_cache.get(channel_trend_id, None)
        if not ct:
            ct = ChannelTrends(channel=channel, status=status, time_slot=time_slot)
            cts_cache[channel_trend_id] = ct
        ct.compute_increments(agent, lang_id, inc_dict, n)


def increment_topic_stats(channel=None, time_slot=None, level='hour',
                          topic=None, status=None, intention_id=None,
                          is_leaf=None, agent=None, lang_id=None,
                          inc_dict=None, n=1,
                          ctts_cache=None, chts_cache=None):
    """ Updates topic specific statistics.
        ChannelTopicTrends is updated for all time slot levels
        and holding outbound stats when switching to ACTUAL status.
    """
    from ..db.channel_hot_topics   import ChannelHotTopics
    from ..db.channel_topic_trends import ChannelTopicTrends
    from ..utils.id_encoder       import ALL_TOPICS

    stat_id = ChannelTopicTrends.make_id(
        channel   = channel,
        time_slot = time_slot,
        topic     = topic,
        status    = status
    )

    if level != 'month':
        ctt = ctts_cache.get(stat_id, None)
        if not ctt:
            ctt = ChannelTopicTrends(
                channel   = channel,
                time_slot = time_slot,
                topic     = topic,
                status    = status
            )
            ctts_cache[stat_id] = ctt
        ctt.compute_increments(is_leaf, [intention_id], agent, lang_id, inc_dict, n)

    if level != 'hour' and topic != ALL_TOPICS:  # we only keep hot-topics stats for days & months
        from solariat_bottle.utils.id_encoder import get_topic_hash
        from solariat_nlp.utils.topics        import get_subtopics

        hashed_parents = map(get_topic_hash, get_subtopics(topic))
        cht = chts_cache.get(stat_id, None)

        if not cht:
            cht = ChannelHotTopics(
                channel        = channel,
                time_slot      = time_slot,
                topic          = topic,
                status         = status,
                hashed_parents = hashed_parents
            )
            chts_cache[stat_id] = cht
        cht.compute_increments(is_leaf, intention_id, agent, lang_id, n)
    return 1 + (level != 'hour')

def _prepare_stats_increments(post, status, channel, is_new=False, should_increment=True,
                              should_decrement=True, ctts_cache=None, chts_cache=None,cts_cache=None,
                              levels=('hour', 'day', 'month'), terms_list=None, **context):  #{
    """ TODO: this might also be better off as a class method which we can overwrite.
        Increments stats counters of post's topics and terms

        context (optional):
          agent
          outbound_stats = {response_volume:int, response_time:int}
    """
    ctts_cache = {} if ctts_cache is None else ctts_cache  # ChannelTopicTrends
    chts_cache = {} if chts_cache is None else chts_cache  # ChannelHotTopics
    cts_cache  = {} if cts_cache  is None else cts_cache   # ChannelTrends

    from ..db.speech_act import SpeechActMap
    from ..db.channel.base import Channel
    from ..db.channel_stats_base  import ALL_AGENTS

    timeslots = [
        (level, datetime_to_timeslot(post.created_at, level))
        for level in levels
    ]
    if not isinstance(channel, Channel):
        channel = Channel.objects.get(channel)

    from_status    = SpeechActMap.STATUS_MAP[
        context.get('from_status', None) or post.get_assignment(channel)]
    to_status      = from_status if status == None else SpeechActMap.STATUS_MAP[status]
    action         = context.pop('action', 'update')
    is_new         = is_new or action == 'add'
    lang_id = post.lang_id

    if DEBUG_STATS:
        debug_info = DebugInfo({"status": status, "from_status": from_status, "to_status": to_status,
                                "channel": channel.id, "channel_title": channel.title, "updates": []})
        debug_info.update(context)

    ''' IGNORE THIS
    assert from_status != SpeechActMap.ACTUAL or from_status == to_status, \
        "Wrong post status update %s -> %s\n channel: %s %s\n post: %s %s" % (
            from_status, to_status, channel.id, channel.title, post.id, post.content)
    '''

    inc_dict       = {'post_count' : 1}  # contains stat values to be updated
    outbound_stats = context.get('outbound_stats', {})

    if outbound_stats:  # response_* metrics
        if to_status != SpeechActMap.ACTUAL:
            error_info = {
                "status"        : status,
                "from_status"   : from_status,
                "to_status"     : to_status,
                "channel"       : channel.id,
                "channel_title" : channel.title
            }
            error_info.update(context)
            LOGGER.error(
                "Invalid stats configuration. to_status should be ACTUAL "
                "when outbound_stats are defined: to_status=%r; debug info: %s",
                to_status, error_info
            )
        else:
            inc_dict.update(outbound_stats)

    upserts_count = 0

    for (level, time_slot) in timeslots:
        if should_decrement and not is_new:
            # We need this specific check for reasons
            # The switch from a non-actual -> actual status is the only place where
            # agent / response time / response volume come into play. As such at this point
            # we don't want to decrement these specific values, since there is nothing to
            # decrement.
            if to_status == SpeechActMap.ACTUAL:
                inc_dict2 = {'post_count': inc_dict['post_count']}
                agent     = ALL_AGENTS
            else:
                inc_dict2 = inc_dict
                agent     = context.get('agent', ALL_AGENTS)

            increment_post_stats(
                channel   = channel,
                time_slot = time_slot,
                level     = level,
                status    = from_status,
                agent     = agent,
                lang_id   = lang_id,
                inc_dict  = inc_dict2.copy(),
                n         = -1,
                cts_cache = cts_cache
            )

        if should_increment and (action != 'remove' or is_new):
            increment_post_stats(
                channel   = channel,
                time_slot = time_slot,
                level     = level,
                status    = to_status,
                agent     = context.get('agent', ALL_AGENTS),
                lang_id   = lang_id,
				inc_dict  = inc_dict.copy(),
                n         = 1,
                cts_cache = cts_cache
            )

    for speech_act in post.speech_acts:
        # Make sure we update every speech act for the given post
        # for each timeslot.
        intention_id = SATYPE_TITLE_TO_ID_MAP[speech_act['intention_type']]

        terms = gen_speech_act_terms(speech_act, channel=channel, post=post, include_all=True)

        for (term, _, count, is_leaf), (level, time_slot) in product(terms, timeslots):
            if terms_list and term not in terms_list:
                # If we have a specific term list we are tracking and the current term
                # is not in that list, then we can just continue to the next term
                continue

            incr = inc_dict.copy()
            incr['topic_count'] = count
            params = dict(
                channel      = channel,
                intention_id = intention_id,
                inc_dict     = incr,
                topic        = term,
                is_leaf      = is_leaf,
                time_slot    = time_slot,
                level        = level,
                agent        = context.get('agent'),
                lang_id      = lang_id,
                ctts_cache   = ctts_cache,  # ChannelTopicTrends
                chts_cache   = chts_cache,  # ChannelHotTopics

            )

            #if (action == 'remove' or from_status != to_status) and should_decrement and not is_new:

            if should_decrement and not is_new:
                # Status transition - decrement the old stats, but not on post creation.
                #
                # Items with from_status are not agent specific, and don't have reports metrics,
                # so we override agent parameter and inc_dict.
                # Decrement if no agent in stats inc_dict or agent=ALL_AGENTS
                #
                # Update: also need to decrease agent specific stats when smart tag removed
                dec_params = params.copy()

                if dec_params['agent'] is None or dec_params['agent'] == ALL_AGENTS or \
                        to_status == SpeechActMap.ACTUAL and from_status != to_status:
                    dec_params['agent'] = ALL_AGENTS
                    dec_params['inc_dict'] = {'topic_count': count}

                upserts_count += increment_topic_stats(
                    status     = from_status,
                    n          = -1,
                    **dec_params
                )

                if DEBUG_STATS:
                    debug_info.append(from_status, -1, dec_params)

            #if should_increment or is_new:
            if (action != 'remove' or is_new) and should_increment:
                # increment the new stats on status change or on new post
                upserts_count += increment_topic_stats(
                    status     = to_status,
                    n          = 1,
                    **params
                )

                if DEBUG_STATS:
                    debug_info.append(to_status, 1, params)

    if DEBUG_STATS:
        # Create new debug entry in database
        if 'reply' in debug_info:
            debug_info['reply_content'] = debug_info['reply'].content
            debug_info['reply']         = debug_info['reply'].id

        PostStats.objects.coll.update(
            {"_id": post.id, "content": post.plaintext_content},  # TODO [encrypt]: saving post content in debug data
            {"$push": {"stats_updates": debug_info}},
            upsert=True
        )

    return ctts_cache, chts_cache, cts_cache

def _update_channel_stats(post, status, channel, is_new=False, should_increment=True,
                          should_decrement=True, **context):
    chts_cache, ctts_cache, cts_cache = _prepare_stats_increments(
        post, status, channel,
        is_new           = is_new,
        should_increment = should_increment,
        should_decrement = should_decrement,
        **context
    )
    _upsert_stats_increments(chts_cache)
    _upsert_stats_increments(ctts_cache)
    _upsert_stats_increments(cts_cache)

def _upsert_stats_increments(stats_cache):
    for item in stats_cache.values():
        item.upsert()

def _update_conversation_stats(conversation, closing_time=None, quality=None):
    from ..db.conversation_trends import ConversationQualityTrends
    agents = conversation.get_agents()
    if len(agents) > 1: # this situation is possible, but for now we don't handle it
        raise Exception("Too many agents, don't know how to handle this situation.")
    if len(agents) == 0: # situation when brand haven't engaged
        return
    # raise Exception("No agents at all in this conversation, don't know how to handle this situation.")
    agent_id = agents[0].agent_id
    for level in ("day", "hour"):
        quality_arg = ConversationQualityTrends.get_category_code(quality) if quality is not None else conversation.get_quality()
        ConversationQualityTrends.increment(
            channel=conversation.service_channel,
            category=quality_arg,
            time_slot=datetime_to_timeslot(closing_time, level),
            agent=agent_id,
            inc_dict={"count": 1})

