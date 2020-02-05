from datetime import datetime
from Queue import Queue

from solariat_bottle.settings import get_var, LOGGER
from solariat_bottle.db.historic_data import QueuedHistoricData, SUBSCRIPTION_RUNNING
from solariat_bottle.db.user import User
from solariat_bottle.daemons.helpers import PostCreator
from solariat_bottle.utils.stateful import Stateful, state_updater
from solariat_bottle.utils.posts_tracking import log_state, PostState, get_post_natural_id


class HistoricLoader(Stateful):
    """
    Load a bunch of queued posts for an existing subscription
    """

    UPDATE_PROGRESS_EVERY = 10

    def __init__(self, subscription, candidate_channels, subscriber):
        """
        :param subscription: A SocialAnalytics subscription for historic load. We need it to get the
        posts that were queued only for a specific channel and start pushing those into our system.
        """
        self.subscription = subscription
        self.subscriber = subscriber

        self.post_queue = Queue(maxsize=100)   # A queue used to stream posts for processing from the creators
        user = User.objects.get(email=get_var('DATASIFT_POST_USER'))
        # Have a creator that will push data into our system
        self.creator = PostCreator(user, self.post_queue)

        self.candidate_channel_ids = [ch.id for ch in candidate_channels]
        self.posts_queued = 0
        self.posts_processed = 0
        self.posts_total = 0
        self._fetch_buffer = []
        super(HistoricLoader, self).__init__()

    def _find_channels(self, post_fields):
        from solariat_bottle.utils.tracking import lookup_tracked_channels

        tracked_channels = lookup_tracked_channels('Twitter', post_fields)
        tracked_channel_ids = [ch.id for ch in tracked_channels]
        if not tracked_channel_ids:
            channels = map(str, self.candidate_channel_ids)
        else:
            channels = map(str, set(tracked_channel_ids) & set(self.candidate_channel_ids))
        return channels

    def _query_posts(self):
        qs = QueuedHistoricData.objects(subscription=self.subscription).sort(timestamp=1)
        qs.cursor.batch_size(100)   # prevent CursorNotFound when PostCreator is too slow
        return qs

    def flush_buffer(self, force=False):
        if not force and len(self._fetch_buffer) >= 200:
            del_all_except_last_100 = self._fetch_buffer[:-100]
            QueuedHistoricData.objects.remove(id__in=[i.id for i in del_all_except_last_100])
            self._fetch_buffer = self._fetch_buffer[-100:]
        elif force and self._fetch_buffer:
            QueuedHistoricData.objects.remove(id__in=[item.id for item in self._fetch_buffer])
            self._fetch_buffer = []

    @property
    def progress(self):
        if self.posts_total > 0:
            return 100 * round(float(self.posts_processed) / self.posts_total, 3)
        return 0

    @state_updater
    def update_progress(self):
        LOGGER.info('HistoricLoader progress: %s%% (%s/%s) ' % (
            self.progress, self.posts_processed, self.posts_total))

    def stateful_params(self):
        return {'subscription_id': self.subscription.id}

    def serialize_state(self):
        return {
            'queued': self.posts_queued,
            'processed': self.posts_processed,
            'total': self.posts_total,
            'progress': self.progress,
        }

    def deserialize_state(self, state):
        queued = state.get('queued')
        processed = state.get('processed')
        total = state.get('total')

        if queued:
            self.posts_queued = queued
        if processed:
            self.posts_processed = processed
        if total:
            self.posts_total = total
        self.subscriber.aggregate_state(self, {'restored': self.progress})

    def fetch_and_post(self):
        ch_id = self.subscription.channel.id
        for posts_processed, entry in enumerate(self._query_posts(), start=self.posts_processed + 1):
            if self.subscriber.stopped():
                break

            post_fields = entry.solariat_post_data
            if not post_fields:
                LOGGER.warning('no post_fields in: %s', entry)
                self.flush_buffer()
                continue

            try:
                log_state(ch_id, get_post_natural_id(post_fields),
                          PostState.REMOVED_FROM_WORKER_QUEUE)
            except KeyError:
                LOGGER.error('cannot get post id: %s', post_fields)

            channels = self._find_channels(post_fields)
            if channels:
                post_fields['channels'] = channels
                self.post_queue.put(post_fields)  # blocked by queue maxsize
                self.posts_queued += 1
                self._fetch_buffer.append(entry)
            else:
                LOGGER.warn("No channels found for queued post %s\n"
                            "queue item id: %s" % (post_fields, entry.id))

            self.posts_processed = posts_processed
            if posts_processed % self.UPDATE_PROGRESS_EVERY == 0:
                self.update_progress()
                self.subscriber.aggregate_state(self, {'running': self.progress})
            self.flush_buffer()
            self.subscriber.update_status(SUBSCRIPTION_RUNNING)

    def load(self):
        if self.posts_total is 0:
            self.posts_total = self._query_posts().count()

        self.creator.start()
        self.fetch_and_post()
        self.subscriber.aggregate_state(self, {'wait_post_creator': True})

        self.creator.quit()
        self.flush_buffer(force=True)
        self.update_progress()
        # if subscription was stopped, update progress and return immediately:
        # let subscription update self status (to STOPPED) and then wait while creator finished.
        if not self.subscriber.stopped():
            self.creator.join()
            self.subscriber.aggregate_state(self, {'finished': True})
