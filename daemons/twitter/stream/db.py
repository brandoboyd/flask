from solariat.db.abstract import Document, Manager
from solariat.db import fields
from solariat_bottle.utils.hash import mhash
from solariat_bottle.utils.tracking import freeze
from solariat.utils.timeslot import now


class StreamRefManager(Manager):
    def get_or_create(self, track, follow, languages, account_ids, channel_ids):
        ref = StreamRef(track=track,
                        follow=follow,
                        languages=languages)
        is_new = False
        existing_ref = StreamRef.objects.find_one(id=ref.key)
        if existing_ref is None:
            is_new = True
            ref.status = StreamRef.QUEUED
            log = StreamLog(accounts=account_ids,
                            channels=channel_ids,
                            stream_ref_id=ref.id)
            log.save()
            ref.log = log
            ref.save()
        else:
            ref = existing_ref
            ref_log = ref.log
            if (not ref_log or
                    set(ref_log.channels) != set(channel_ids) or
                    set(ref_log.accounts) != set(account_ids) or
                    ref.is_stopped()):
                # if tracked accounts or channels change
                # update stream log
                if ref_log:
                    ref_log.update(stopped_at=now())
                else:
                    is_new = True
                if ref.is_stopped():
                    is_new = True
                log = StreamLog(accounts=account_ids,
                                channels=channel_ids,
                                stream_ref_id=existing_ref.id)
                log.save()
                ref.update(log=log, status=StreamRef.RUNNING)
        return ref, is_new

    def update_running_streams(self):
        """This is to be run on bot start. If bot was not properly stopped
        some streams might left in running state so they would be
        skipped during sync."""
        for ref in self.find(status=StreamRef.RUNNING):
            ref.update(status=StreamRef.STOPPED)


class StreamRef(Document):
    QUEUED = 'queued'
    RUNNING = 'running'
    ERROR = 'error'
    STOPPED = 'stopped'
    STREAM_STATUSES = [QUEUED, RUNNING, ERROR, STOPPED]

    id = fields.BytesField(db_field='_id', unique=True, required=True)
    track = fields.ListField(fields.StringField())
    follow = fields.ListField(fields.StringField())  # user_ids
    languages = fields.ListField(fields.StringField(), db_field='lng')

    status = fields.StringField(choices=STREAM_STATUSES)
    log = fields.ReferenceField('StreamLog')

    manager = StreamRefManager
    indexes = [('status',)]

    def is_stopped(self):
        return self.status == self.STOPPED or (
            self.log and self.log.stopped_at is not None)

    @property
    def key(self):
        if not self.id:
            footprint = self.filters
            self.id = mhash(footprint, n=128)
        return self.id

    @property
    def filters(self):
        return tuple([freeze(self.track),
                      freeze(self.follow),
                      freeze(self.languages)])

    def set_added(self):
        self.update(status=self.RUNNING)
        self.log.update(started_at=now())

    def set_removed(self):
        self.update(status=self.STOPPED)
        self.log.update(stopped_at=now())

    def save(self, **kw):
        self.id = self.key  # fill hash id
        super(StreamRef, self).save(**kw)


class StreamLog(Document):
    """Created on streamref creation, updated on stream stops"""
    accounts = fields.ListField(fields.ObjectIdField())
    channels = fields.ListField(fields.ObjectIdField())

    stream_ref_id = fields.BytesField()

    started_at = fields.DateTimeField(null=True)
    stopped_at = fields.DateTimeField(null=True)

    indexes = [('accounts',), ('channels',), ('stream_ref_id',)]