# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

""" This module has functions to encode object ids by packing various object
    characteristics into a large integer value using hash functions and bit
    arithmetic.
"""
from datetime import timedelta

from solariat_nlp.sa_labels import (
    SAType, SATYPE_NAME_TO_ID_MAP)

from solariat.utils.timeslot import encode_timeslot, Timeslot, TIMESLOT_EPOCH
from solariat.db.abstract    import ObjectId

from solariat_bottle.db.channel.base import Channel

from solariat_bottle.utils.hash import mhash


def _gap_len(s):
    rem = s % 8
    if rem > 0:
        return 8 - rem
    return 0

# --- constants ---
CHANNEL_WIDTH        = 20 # bits encode 0..1,048,575 (channel number)
CONVERSATION_CHANNEL_WIDTH = 13
TOPIC_WIDTH          = 28 # bits encode 0..268,435,455 (topic hash)
STATUS_WIDTH         = 2  # bits encode 0..3         (post status)
TIMESLOT_WIDTH       = encode_timeslot(0, 'hour')[1] # 2bit level prefix + 20bit number of hours since 2000
POST_WIDTH           = 24 # Encoding the full post
QUALITY_WIDTH        = 2 # bits encode 0..3; "unknown", "win", "loss"

STATS_WIDTH = CHANNEL_WIDTH + TOPIC_WIDTH + STATUS_WIDTH + TIMESLOT_WIDTH
STATS_GAP_WIDTH = 0 #_gap_len(STATS_WIDTH)

SAM_WIDTH     = CHANNEL_WIDTH + STATUS_WIDTH + TIMESLOT_WIDTH + POST_WIDTH
SAM_GAP_WIDTH = _gap_len(SAM_WIDTH)

CONVERSATION_STATS_WIDTH     = CHANNEL_WIDTH + QUALITY_WIDTH + TIMESLOT_WIDTH
CONVERSATION_STATS_GAP_WIDTH = 4 # _gap_len(CONVERSATION_STATS_WIDTH)


BIGGEST_64BIT_VALUE     = (1<<64) - 1  # 64bit int with all bits set
BIGGEST_TOPIC_VALUE     = (1<<TOPIC_WIDTH) - 1
BIGGEST_STATUS_VALUE    = (1<<STATUS_WIDTH) - 1
BIGGEST_POST_VALUE      = (1<<POST_WIDTH) - 1
BIGGEST_TIMESOLT_VALUE  = (1<<TIMESLOT_WIDTH) - 1

MILLISECONDS_PER_SECOND = 1000

EVENT_TIMESTAMP_WIDTH   = 42 # BIGGEST_EVENT_TIMESTAMP = 50 (years) *365*24*60 (minutes) * 60 (seconds) * 1000 (milliseconds)
                             # the biggest date would be: 
                             # TIMESLOT_EPOCH + timedelta(milliseconds = BIGGEST_EVENT_TIMESTAMP)
                             # datetime.datetime(2069, 9, 6, 15, 47, 35, 551000, tzinfo=<UTC>)
                             # >>> len(bin(50 * 365*24*60 * 60 * 1000)[2:]) 
                             # >>> 41

USER_NUM_WIDTH          = 30 # counter for User and UserProfile 1 073 741 823
PREDICTOR_NUM_WIDTH     = 7  # max no of Predictor say 100, len(bin(100)[2:])

NO_TOPIC   = '__NONE__'
ALL_TOPICS = '__ALL__'


def pack_components(*components):
    """ Generic component packer.
        Each component is a tuple (<value>, <bit_width>)

        For example:
          pack_components((115,8), (3,2), (hash('blabla'),22)) --> <32bit_int>
    """
    final, pos = 0L, 0
    for value, width in reversed(components):
        mask   = (1L << width) - 1
        final |= (value & mask) << pos
        pos   += width

    return final


def revert_pack_components(*components):
    """
    For a list of components, pack in revers order
    Each component is a tuple (<value>, <bit_width>)

    Result is packed in reverse order bit wise.
    E.G. pack_components((1, 2), (3, 2)) ==> 01 11 ==> 1110 ==> 14
    """
    final, pos = 0L, 0
    for value, width in components:
        mask = (1L << width) - 1
        binary_format = '{:0%sb}' % width
        reversed_value = int(binary_format.format(value)[::-1], 2)
        final |= (reversed_value & mask) << pos
        pos += width
    return final


def unpack_components(packed, *widths):
    """ Generic component unpacker.

        For example:
          unpack_components(123456789, 8, 2, 22) --> (<C1:8>, <C2:2>, <C3:22>)
    """
    values = []
    for width in reversed(widths):
        mask = (1L << width) - 1
        values.append(packed & mask)
        packed >>= width

    return tuple(reversed(values))


def get_channel_id(channel):
    """ Returns a <channel_id:ObjectId> given a channel,
        where channel is <Channel> | <channel_id:ObjectId>
    """
    if isinstance(channel, Channel):
        return channel.id
    elif isinstance(channel, ObjectId):
        return channel

    raise RuntimeError('unsupported channel type: %r' % channel)


def get_channel_num(channel):
    """ Returns a <channel_num:int> given a channel,
        where channel is <Channel> | <channel_id:ObjectId> | <channel_num:int>
    """
    if isinstance(channel, (int, long)):
        channel_num = channel
    elif isinstance(channel, Channel):
        channel_num = channel.counter
    elif isinstance(channel, ObjectId):
        channel = Channel.objects.get(id=channel)
        channel_num = channel.counter
    else:
        raise RuntimeError('unsupported channel type: %r' % channel)

    # for channel "Contacts" this function returns 8.0 value (it's 8 in db)
    # this is a quick fix for "Contacts" channel
    if isinstance(channel_num, float) and channel_num.is_integer():
        channel_num = int(channel_num)

    return channel_num


def get_topic_hash(topic):
    if topic is None or topic == NO_TOPIC:
        return 0
    if topic == ALL_TOPICS:
        return (1<<TOPIC_WIDTH)-1
    elif isinstance(topic, (int, long)):
        return topic & ((1<<TOPIC_WIDTH)-1)
    elif isinstance(topic, basestring):
        return mhash(topic.lower(), n=TOPIC_WIDTH)
    else:
        raise RuntimeError('unsupported topic type: %r' % topic)


def get_post_hash(post, index=None):
    """Encodes the post, based on its id
    """

    if isinstance(post, (int, long)):
        return post & ((1<<POST_WIDTH)-1)
    elif hasattr(post, 'id'):
        assert index != None and isinstance(index, (int, long))
        return mhash("%s:%d" % (str(post.id), index), n=POST_WIDTH)
    else:
        raise RuntimeError('unsupported post type: %r' % post)


def get_status_code(status):
    if isinstance(status, (int, long)):
        code = status
    elif isinstance(status, basestring):
        status = status.strip().lower()
        if status.isdigit():
            code = int(status)
        else:
            from ..db.speech_act import SpeechActMap  # importing here to avoid circular dep
            code = SpeechActMap.STATUS_MAP[status]
    else:
        raise RuntimeError('unsupported status type: %r' % status)
    return code

def get_intention_id(intention):
    if isinstance(intention, (int, long)):
        int_id = intention
    elif isinstance(intention, SAType):
        int_id = int(intention.oid)
    elif isinstance(intention, basestring):
        intention = intention.strip().lower()
        if intention.isdigit():
            int_id = int(intention)
        else:
            int_id = int(SATYPE_NAME_TO_ID_MAP[intention])
    else:
        raise RuntimeError('unsupported intention type: %r' % intention)
    return int_id


def pack_short_stats_id(
        channel,    # <Channel> | <ch_id:ObjectId> | <ch_num:int:0..1,048,575>
        status,     # <code:int:0..3> | <name:str>
        time_slot,  # <timeslot:int> | <Timeslot>
):
    """ Returns an encoded stats id
    for the case when stats have only channel and time slot.
    """
    channel_num = get_channel_num(channel)
    status_code = get_status_code(status)
    time_slot   = time_slot.timeslot if isinstance(time_slot, Timeslot) else time_slot

    assert 0 <= channel_num < (1<<CHANNEL_WIDTH),  channel_num
    assert 0 <= status_code < (1<<STATUS_WIDTH),   status
    assert 0 <= time_slot   < (1<<TIMESLOT_WIDTH), time_slot
    # print "->>>", channel_num, topic_hash, status_code, time_slot, 0,

    return pack_components(
        (channel_num, CHANNEL_WIDTH),
        (status_code, STATUS_WIDTH),
        (time_slot,   TIMESLOT_WIDTH),
        (0,           STATS_GAP_WIDTH)
    )


def unpack_short_stats_id(stat_id):
    """ Returns an unpacked channel-timeslot id as a tuple
        (<channel_num:int>, <timeslot:int>)
        Similar to `unpack_stats_id` but without topic and status.
    """
    channel_num, status, time_slot, _ = unpack_components(
        stat_id,
        CHANNEL_WIDTH,
        STATUS_WIDTH,
        TIMESLOT_WIDTH,
        STATS_GAP_WIDTH
    )
    return channel_num, status, time_slot


def pack_stats_id(
    channel,    # <Channel> | <ch_id:ObjectId> | <ch_num:int:0..1,048,575>
    topic,      # <topic:str> | <topic_hash:int:0..268,435,455>
    status,     # <code:int:0..3> | <name:str>
    time_slot,  # <timeslot:int> | <Timeslot>
):
    """ Returns an encoded stats id
    """
    channel_num = get_channel_num(channel)
    topic_hash  = get_topic_hash(topic)
    status_code = get_status_code(status)
    time_slot   = time_slot.timeslot if isinstance(time_slot, Timeslot) else time_slot

    assert 0 <= channel_num < (1<<CHANNEL_WIDTH),  channel_num
    assert 0 <= status_code < (1<<STATUS_WIDTH),   status
    assert 0 <= time_slot   < (1<<TIMESLOT_WIDTH), time_slot
    assert 0 <= topic_hash  < (1<<TOPIC_WIDTH),    topic_hash
    # print "->>>", channel_num, topic_hash, status_code, time_slot, 0,

    return pack_components(
        (channel_num, CHANNEL_WIDTH),
        (topic_hash,  TOPIC_WIDTH),
        (status_code, STATUS_WIDTH),
        (time_slot,   TIMESLOT_WIDTH),
        (0,           STATS_GAP_WIDTH)
    )

def unpack_stats_id(stat_id):
    """ Returns an unpacked topic-trends id as a tuple
        (<channel_num:int>, <topic_hash:int>, <status_code:int>, <timeslot:int>)
    """
    channel_num, topic_hash, status_code, time_slot, _ = unpack_components(
        stat_id,
        CHANNEL_WIDTH,
        TOPIC_WIDTH,
        STATUS_WIDTH,
        TIMESLOT_WIDTH,
        STATS_GAP_WIDTH
    )
    return channel_num, topic_hash, status_code, time_slot


def pack_conversation_key(channel, conv_id):
    CONVERSATION_WIDTH = 50
    # Pack in reverse order so the most significant bits of the id are increasing as a counter
    # and shart allocation would vary ever per channel.
    return revert_pack_components((get_channel_num(channel), CONVERSATION_CHANNEL_WIDTH),
                                  (conv_id, CONVERSATION_WIDTH))


def pack_conversation_stats_id(
    channel,    # <Channel> | <ch_id:ObjectId> | <ch_num:int:0..1,048,575>
    quality,     # <code:int:0..3> | <name:str>
    time_slot,  # <timeslot:int> | <Timeslot>
):
    """ Returns an encoded stats id
    """
    channel_num = get_channel_num(channel)
    quality_code = get_quaility_code(quality)
    time_slot   = time_slot.timeslot if isinstance(time_slot, Timeslot) else time_slot

    assert 0 <= channel_num < (1<<CHANNEL_WIDTH),  channel_num
    assert 0 <= quality_code < (1<<QUALITY_WIDTH),   quality
    assert 0 <= time_slot   < (1<<TIMESLOT_WIDTH), time_slot
    # print "->>>", channel_num, topic_hash, status_code, time_slot, 0,

    return pack_components(
        (channel_num, CHANNEL_WIDTH),
        (quality_code, QUALITY_WIDTH),
        (time_slot,   TIMESLOT_WIDTH),
        (0,           CONVERSATION_STATS_GAP_WIDTH)
    )


def unpack_conversation_stats_id(stat_id):
    """ Returns an unpacked topic-trends id as a tuple
        (<channel_num:int>, <topic_hash:int>, <status_code:int>, <timeslot:int>)
    """
    channel_num, quality, time_slot, _ = unpack_components(
        stat_id,
        CHANNEL_WIDTH,
        QUALITY_WIDTH,
        TIMESLOT_WIDTH,
        CONVERSATION_STATS_GAP_WIDTH
    )
    return channel_num, quality, time_slot


def get_quaility_code(quality):
    from ..db.conversation_trends import ConversationQualityTrends
    if isinstance(quality, (int, long)):
        code = quality
    elif isinstance(quality, str):
        code = ConversationQualityTrends.CATEGORY_MAP[quality]
    else:
        raise RuntimeError('unsupported topic type: %r' % quality)
    return code


def make_channel_ts(channel, time_slot):
    time_slot = time_slot.timeslot if isinstance(time_slot, Timeslot) else time_slot
    assert isinstance(time_slot, int), type(time_slot)
    if isinstance(channel, (str, unicode)):
        channel = Channel.objects.get(id=channel)
    channel_num = get_channel_num(channel)
    res = pack_components(
        (channel_num, CHANNEL_WIDTH),
        (time_slot, TIMESLOT_WIDTH),
    )
    return res


def pack_event_id(
    actor_num,   # int
    created_at,  # datetime value
):
    """ Returns an encoded stats id
    """
    # created_at = pytz.utc.localize(created_at)
    assert created_at.tzname() == 'UTC', created_at.tzname()
    event_timestamp = int(
        (created_at - TIMESLOT_EPOCH).total_seconds() * MILLISECONDS_PER_SECOND)
    assert 0 <= actor_num < (1 << USER_NUM_WIDTH), actor_num
    assert 0 <= event_timestamp < (1 << EVENT_TIMESTAMP_WIDTH), event_timestamp
    return pack_components(
        (actor_num, USER_NUM_WIDTH),
        (event_timestamp, EVENT_TIMESTAMP_WIDTH),
    )

def unpack_event_id(event_id):
    actor_num, event_timestamp = unpack_components(
        event_id,
        USER_NUM_WIDTH,
        EVENT_TIMESTAMP_WIDTH
    )
    return actor_num, TIMESLOT_EPOCH + timedelta(milliseconds=event_timestamp)
