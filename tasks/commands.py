# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_bottle.workers  import io_pool
from solariat_bottle.settings import AppException, LOGGER

logger = io_pool.logger


# --- IO-worker initialization ----

@io_pool.prefork  # IO-workers will run this before forking
def pre_import_commands():
    """ Master init
        Pre-importing heavy modules with many dependencies here
        to benefit from the Copy-on-Write kernel optimization.
    """
    logger.info('pre-importing commands dependencies')

    import solariat_bottle.db.auth
    import solariat_bottle.db.account
    import solariat_bottle.db.message_queue

    import solariat_bottle.utils.tweet
    import solariat_bottle.utils.facebook_extra
    import solariat.elasticsearch

    # to disable a pyflakes warnings
    del solariat_bottle


# --- Commands tasks ----

@io_pool.task
def cmd_perform(command, user):
    from solariat_bottle.db.auth          import AuthError
    from solariat_bottle.db.account       import ChannelConfigurationError
    from solariat_bottle.db.message_queue import TaskMessage

    from solariat_bottle.tasks.exceptions import (FacebookCommunicationException, TwitterCommunicationException,
                                                  FacebookConfigurationException)
    from solariat.elasticsearch    import ElasticSearchException

    try:
        command.perform(user)
    except (ChannelConfigurationError, TwitterCommunicationException, FacebookCommunicationException,
            ElasticSearchException, AppException, FacebookConfigurationException) as exc:
        TaskMessage.objects.create_error(user, str(exc))
    except AuthError as exc:
        logger.error(exc)
        TaskMessage.objects.create_error(user, "Command could not be executed due to user permissions. Please make sure you have write permissions on service channel.")
    except RuntimeError, exc:
        logger.error(exc, exc_info=True)
        TaskMessage.objects.create_error(user, str(exc))
    except Exception, exc:
        logger.error(exc, exc_info=True)
        TaskMessage.objects.create_error(user, "An unknown error occurred; check logs for details. " + str(exc))


def compute_sam_match_query(channel):
    """ Compute the query which would match all speech acts for the given
    channels list, in the timeslot interval (from - to)"""
    from solariat.db import fields
    from solariat_bottle.utils.id_encoder import BIGGEST_POST_VALUE, TIMESLOT_WIDTH
    from solariat_bottle.db.speech_act import SpeechActMap, pack_speech_act_map_id

    from_timeslot = 0 << TIMESLOT_WIDTH
    to_timeslot = (1L << TIMESLOT_WIDTH) - 1

    to_binary = fields.BytesField().to_mongo
    match_query_base = []
    for status in SpeechActMap.STATUS_NAME_MAP.keys():
        # compute id bounds for all posts for this slot
        id_lower_bound = pack_speech_act_map_id(channel, status, from_timeslot, 0)
        id_upper_bound = pack_speech_act_map_id(channel, status, to_timeslot, BIGGEST_POST_VALUE)
        match_query_base.append({'_id': { "$gte": to_binary(id_lower_bound), "$lte": to_binary(id_upper_bound)}})

    day_speech_act_filter = {"$or": match_query_base}
    return day_speech_act_filter


def _clear_posts_for_channel(channel_id):
    """ Also remove all the posts so the benchmark can be re-ran """
    from solariat_bottle.db.channel.base import Channel
    from solariat_bottle.db.post.base import Post
    from solariat_bottle.db.speech_act import SpeechActMap

    batch_size = 500
    try:
        channel = Channel.objects.get(channel_id)
    except Channel.DoesNotExist, ex:
        return
    post_ids = list(set([s['pt'] for s in SpeechActMap.objects.coll.find(compute_sam_match_query(channel))]))
    for idx in range(0, len(post_ids), batch_size):
        Post.objects.remove(id__in=post_ids[idx * batch_size:(idx + 1) * batch_size])


@io_pool.task
def reset_channel_data(channel_id):
    _clear_posts_for_channel(channel_id)

