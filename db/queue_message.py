from datetime import datetime, timedelta
from random import Random
from pymongo.errors import DuplicateKeyError

from solariat.db import fields
from solariat.db.abstract import Document, Manager
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.posts_tracking import log_state, PostState, get_logger, is_enabled


DEFAULT_RESERVE_TIME = 100
DEFAULT_LIMIT = 1000
SEPARATOR = ":"

class QueueMessageManager(Manager):

    def make_id(self, channel_id, post_id):
        return str(channel_id) + SEPARATOR + str(post_id)

    def push(self, post, channel_id):
        try:
            self.create(id=self.make_id(channel_id, post.id),
                        channel_id=channel_id,
                        created_at=datetime.utcnow(),
                        post_data=post.data,
                        reserved_until=datetime(1970, 1, 1))
        except DuplicateKeyError:
            LOGGER.warning("Trying to push post %s twice on channel %s" % (post, channel_id))
        else:
            log_state(channel_id, post.native_id, PostState.DELIVERED_TO_GSE_QUEUE)

    def count_non_reserved_entries(self, channel):
        query = {'channel_id': str(channel),
                 'reserved_until': {'$lt': datetime.utcnow()},}
        return self.find(**query).count()

    def select_and_reserve(self, channel, limit=DEFAULT_LIMIT, reserve_time=DEFAULT_RESERVE_TIME):
        """
        Query batch of messages from database and reserve it until successful pull callback
        """
        from solariat_bottle.db.post.base import Post

        log_enabled = is_enabled(channel)
        query = {'channel_id': str(channel), 'reserved_until': {'$lt': datetime.utcnow()}}
        messages = self.find(**query).limit(limit)

        result = []
        duplicate_count = 0
        queue_messages = []

        salt_length = 5
        batch_token = None
        deadline = datetime.utcnow() + timedelta(seconds=reserve_time)
        expired_tokens = set([])
        for message in messages:
            if batch_token is None:
                batch_token = '%s%s%s' % (datetime.utcnow().__hash__(), message.id, Random().getrandbits(salt_length))
            if message.batch_token:
                duplicate_count += 1
                # If we re-added these posts, then the token has expired
                expired_tokens.add(message.batch_token)
            message.reserved_until = deadline
            message.batch_token = batch_token
            message.save()
            if log_enabled:
                queue_messages.append(Post(message.post_data).plaintext_content)
            result.append(message)

        if expired_tokens:
            self.coll.update({'batch_token': {'$in': list(expired_tokens)}},
                             {'$set': {'batch_token': None}},
                             multi=True)
        if log_enabled:
            get_logger(channel).info(u"QMD: Pulling / Reserving from queue messages: %s", unicode(queue_messages))
        return result, duplicate_count

    def remove_reserved(self, batch_token):
        '''
        Remove all records from database with provided batch_token
        '''
        reserver = self.find(**{'batch_token': batch_token})[:]
        channel_ids = []
        for message in reserver:
            channel_ids.extend(list(message.channel_id))
        if is_enabled(channel_ids):
            from solariat_bottle.db.post.base import Post

            queue_messages = []
            for message in reserver:
                queue_messages.append(Post(message.post_data).plaintext_content)
            get_logger(channel_ids).info(u"QMD: Confirming / Clearing from queue messages: %s", unicode(queue_messages))
        return self.remove(**{'batch_token': batch_token})

    def clear_reserved_id_based(self, post_ids):
        reserver = self.find(id__in=post_ids)[:]
        channel_ids = []
        for message in reserver:
            channel_ids.extend(list(message.channel_id))
        if is_enabled(channel_ids):
            from solariat_bottle.db.post.base import Post

            queue_messages = []
            for message in reserver:
                queue_messages.append(Post(message.post_data).plaintext_content)
            get_logger(channel_ids).info(u"QMD: Confirming / Clearing from queue messages: %s", unicode(queue_messages))
        return self.remove(id__in=post_ids)

    def get_unsafe(self, channel, limit):
        '''
        Get the data and remove it right after that, without callback
        '''
        time_stub = 1000
        messages, duplicates_count = self.select_and_reserve(channel, limit, time_stub)
        if messages:
            batch_token = messages[0].batch_token
            self.remove_reserved(batch_token)

        return messages, duplicates_count

    def reset_reservation(self, skipped_messages):
        """Resets previously set reserved_until time and batch token
        :param skipped_messages: list of QueueMessage entities
        """
        self.coll.update(
            {QueueMessage.id.db_field: {'$in': [message.id for message in skipped_messages]}},
            {'$set': {QueueMessage.batch_token.db_field: None,
                      QueueMessage.reserved_until.db_field: datetime(1970, 1, 1)}},
            multi=True)


class BrokenQueueMessageManager(QueueMessageManager):

    def save_from_messages(self, messages):
        new_messages = [BrokenQueueMessage(data=msg.data)
                        for msg in messages]
        for msg in new_messages:
            msg.persisted_at = datetime.utcnow()
            msg.save()


class QueueMessage(Document):

    manager = QueueMessageManager

    channel_id = fields.ListField(fields.StringField())
    created_at = fields.DateTimeField()
    reserved_until = fields.DateTimeField()
    post_data = fields.DictField()
    batch_token = fields.StringField()

    indexes = [('channel_id', 'reserved_until'), ('batch_token',), ]


class BrokenQueueMessage(QueueMessage):

    manager = BrokenQueueMessageManager
    persisted_at = fields.DateTimeField(default=datetime.utcnow)

