from solariat_bottle.db.auth import ArchivingAuthDocument
from solariat.db import fields
from solariat_bottle.settings import LOGGER
from solariat.utils.timeslot import utc, now


class JobStatus(ArchivingAuthDocument):

    STATUSES = PENDING, RUNNING, ABANDONED, SUCCESSFUL, FAILED, \
        RESUBMITTED, SLEEPING, TERMINATED = \
        'Pending', 'Running', 'Abandoned', 'Successful', 'Failed', \
        'Resubmitted', 'Sleeping', 'Terminated'

    RUNNABLE_STATUSES = PENDING, SLEEPING

    collection = 'jobs'

    account = fields.ObjectIdField(null=True)
    topic = fields.StringField()
    name = fields.StringField()
    args = fields.PickledField()
    kwargs = fields.PickledField()
    metadata = fields.DictField(null=True)
    created_at = fields.DateTimeField()
    started_date = fields.DateTimeField()
    completion_date = fields.DateTimeField()
    status = fields.StringField(choices=STATUSES)
    state = fields.DictField()
    last_activity = fields.DateTimeField()
    awake_at = fields.DateTimeField(null=True)

    @property
    def git_commit(self):
        return (self.metadata or {}).get('git_commit')

    @property
    def resubmission_info(self):
        return (self.metadata or {}).get('resubmitted')

    def abandon(self):
        if self.status == self.PENDING:
            self.status = self.ABANDONED
        res = self.objects.coll.update(
            {self.F.id: self.id, self.F.status: self.PENDING},
            {"$set": {self.F.status: self.ABANDONED}})

        if isinstance(res, dict) and res.get('nModified') == 1:
            return True

    def resume(self):
        if self.status != self.FAILED:
            raise RuntimeError("Job can not be resumed in '{}' state.".format(self.status))
        from solariat_bottle.jobs.manager import manager

        job = manager.registry.get(self.name)
        res = job.submit(self.topic, self.name, self.args, self.kwargs, self.metadata)
        # updating old job
        meta = self.metadata or {}
        meta.update(resubmitted={'new_id': res.job_instance.id, 'result': str(res.submission_result)})
        self.update(
            status=JobStatus.RESUBMITTED,
            metadata=meta)
        # updating new job
        meta = res.job_instance.metadata or {}
        meta.update(resubmitted={'old_id': self.id})
        res.job_instance.update(metadata=meta)
        return [self, res.job_instance]

    def can_edit(self, user_or_group, admin_roles=None):
        if admin_roles is None:
            admin_roles = self.admin_roles
        account_check = user_or_group.is_staff or (
            user_or_group.is_admin and user_or_group.account.id == self.account)
        edit_check = (bool(set(admin_roles).intersection(set(user_or_group.user_roles)))
                      or (hasattr(user_or_group, 'is_superuser') and user_or_group.is_superuser))

        return account_check and edit_check

    @property
    def wait_time(self):
        if self.started_date and self.created_at:
            return (utc(self.started_date or now()) - utc(self.created_at)).total_seconds()

    @property
    def execution_time(self):
        if self.completion_date and self.started_date:
            now_ = now()
            return (utc(self.completion_date or now_) - utc(self.started_date or now_)).total_seconds()


class Job(object):

    def __init__(self, func, topic, manager, timeout):
        self.func = func
        self.topic = topic
        self.manager = manager
        self.config = manager.config
        self.timeout = timeout
        self.terminate_handler = None

        self.name = '%s.%s' % (func.__module__, func.__name__)
        self.manager.registry.add(self)

    def __call__(self, *args, **kwargs):
        LOGGER.info('invoke "%s" like Job to topic "%s" with args: %s, kwargs: %s' % (
            self.func.__name__, self.topic, args, kwargs
        ))
        return self.submit(self.topic, self.name, args, kwargs, {'git_commit': self.config.git_commit})

    def submit(self, topic, name, args, kwargs, metadata=None):
        return self.manager.producer.send(topic, name, args, kwargs, metadata)
