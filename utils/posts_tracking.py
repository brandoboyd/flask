from solariat.utils.timeslot import utc, now
from solariat_bottle.db import get_connection
from solariat.db.abstract import Document
from solariat.db import fields
from solariat_bottle.settings import LOGGER
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from multiprocessing import RLock


init_lock = RLock()
cache_lock = RLock()
CHANNELS_ENABLED_CACHE = set()
CACHE_UPDATE = None
CACHE_EXPIRE_IN = timedelta(seconds=30)


class PostState(Document):
    INITIALIZED = False

    STATES = ARRIVED_IN_BOT, ARRIVED_IN_RECOVERY, ADDED_TO_WORKER_QUEUE, \
        REMOVED_FROM_WORKER_QUEUE, DELIVERED_TO_TANGO, DELIVERED_TO_GSE_QUEUE, \
        FETCHED_FROM_GSE_QUEUE, CONFIRMED_FROM_GSE_QUEUE = \
        'ARRIVED_IN_BOT', 'ARRIVED_IN_RECOVERY', 'ADDED_TO_WORKER_QUEUE', \
        'REMOVED_FROM_WORKER_QUEUE', 'DELIVERED_TO_TANGO', 'DELIVERED_TO_GSE_QUEUE', \
        'FETCHED_FROM_GSE_QUEUE', 'CONFIRMED_FROM_GSE_QUEUE'

    channel_id = fields.ObjectIdField()
    post_id = fields.StringField()
    state = fields.StringField(choices=STATES)

    indexes = [('post_id', ), ('channel_id', )]


def init():
    with init_lock:
        if PostState.INITIALIZED:
            return

        db = get_connection()
        coll_name = PostState.get_collection_name()
        need_create = True

        if coll_name in db.collection_names():
            # INFO: coll.options() does not with current mongodb
            coll_opts = db.command('collStats', coll_name)
            if coll_opts and not coll_opts.get('capped'):
                db.drop_collection(coll_name)
            else:
                need_create = False

        if need_create:
            db.create_collection(coll_name, capped=True, size=50 * 1024 * 1024, max=100 * 1000)

        PostState.INITIALIZED = True


def log_state(channel_id, post_id, state):
    if post_id is None:
        LOGGER.debug('no post id, skip: %s', (channel_id, post_id, state))
        return
    try:
        init()
        ch_ids = is_enabled(channel_id)
        if ch_ids:
            if channel_id is None:
                LOGGER.debug('track post_id=%s, state=%s without channel_id' % (post_id, state))
            else:
                channel_id = list(ch_ids & CHANNELS_ENABLED_CACHE)[0]
            PostState(channel_id=channel_id, post_id=str(post_id), state=state).save()
        # elif ch_ids is not None:
        #     LOGGER.debug('posts tracking for channel_id:%s is disabled', channel_id)
    except:
        LOGGER.warning("log_state(%s, %s, %s) failed" % (channel_id, post_id, state), exc_info=True)
        pass


def is_enabled(channel_id):
    from solariat_bottle.db.channel.base import Channel, ServiceChannel
    global CACHE_UPDATE, CHANNELS_ENABLED_CACHE

    if not CACHE_UPDATE or datetime.utcnow() - CACHE_UPDATE > CACHE_EXPIRE_IN:
        with cache_lock:
            LOGGER.debug('posts tracking: update cache')
            if not CACHE_UPDATE or datetime.utcnow() - CACHE_UPDATE > CACHE_EXPIRE_IN:
                channels = set()
                for ch in Channel.objects.find(status__in=['Active', 'Interim'],
                                               posts_tracking_enabled=True):

                    if ch.posts_tracking_disable_at and now() > utc(ch.posts_tracking_disable_at):
                        ch.update(posts_tracking_enabled=False)
                        LOGGER.debug('Disabling post tracking for channel: ' + str(ch.id))
                        continue

                    channels.add(ch.id)
                    if isinstance(ch, ServiceChannel):
                        channels.add(ch.inbound)
                        channels.add(ch.outbound)

                CHANNELS_ENABLED_CACHE = channels
                CACHE_UPDATE = datetime.utcnow()

    if channel_id is None:
        return True
    if not channel_id:
        LOGGER.debug("post tracking: skip log for channel_id: %s" % channel_id)
        return None
    if not isinstance(channel_id, (list, tuple, set)):
        channel_id = [channel_id]
    try:
        ch_ids = {ch.id if isinstance(ch, Channel) else ObjectId(ch) for ch in channel_id}
    except TypeError:
        return set([])
    return {ch for ch in ch_ids if ch in CHANNELS_ENABLED_CACHE}


class DummyLogger(object):
    def __getattr__(self, item):
        return lambda *args, **kwargs: None


def get_logger(channel):
    if is_enabled(channel):
        return LOGGER
    else:
        return DummyLogger()


def get_post_natural_id(post):
    if 'twitter' in post:
        return post['twitter']['id']
    if 'facebook' in post:
        return post['facebook']['facebook_post_id']
    # LOGGER.warn('Unsupported post to track: %s', post)
