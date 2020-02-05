from collections import Iterator
import logging
import time
from solariat.utils.timeslot import now
from solariat_bottle.jobs.creator import JobStatus
from .base import AbstractTransport, AbstractConsumer, AbstractProducer, \
    ProducerResult


def get_current_user_and_account():
    def _get_default_jobs_creator(email='_system_jobs_creator@internal.local'):
        from solariat_bottle.db.user import User

        su = User.objects.find_one(is_superuser=True)
        if su is None:
            su = User.objects.create(email=email,
                                     is_superuser=True)
        return su

    from solariat_bottle.utils.decorators import _get_user

    account = None
    current_user = None
    try:
        current_user = _get_user()
    except:
        pass
    if current_user is not None:
        account = current_user.account.id
    else:
        current_user = _get_default_jobs_creator()
        account = current_user.account.id if current_user.account else account
    return current_user, account


def tail_db(topics, timeout=0.5):
    empty = False
    while True:
        job = JobStatus.objects.find_one(status=JobStatus.PENDING,
                                         topic__in=topics)
        if not job:
            if empty:
                break
            empty = True
            time.sleep(timeout)
        else:
            empty = False
        yield job


class _DBProducer(AbstractProducer):

    def send(self, topic, name, args, kwargs, metadata=None):
        """Creates a Job entry in database
        :param topic:
        :param name:
        :param args:
        :param kwargs:
        :param metadata:
        :return:
        """
        user, account = get_current_user_and_account()
        job = JobStatus.objects.create_by_user(
            user,
            account=account,
            topic=topic, name=name, created_at=now(),
            args=args, kwargs=kwargs, metadata=metadata,
            status=JobStatus.PENDING,
        )
        return ProducerResult(True, job)


class _DBConsumer(AbstractConsumer):
    def __init__(self, topics, timeout=10):
        self.topics = topics
        self.timeout = timeout

    def iterator(self):
        while True:
            db_iterator = tail_db(self.topics, self.timeout)
            try:
                message = next(db_iterator)
            except StopIteration:
                # queue is empty or timed out
                logging.getLogger('jobs.timeout').info('*')
                time.sleep(self.timeout)
            else:
                yield message


class DatabaseTransport(AbstractTransport):
    timeout = 10

    def create_producer(self, *args, **kwargs):
        return _DBProducer()

    def create_consumer(self, topics, *args, **kwargs):
        return _DBConsumer(topics=topics, timeout=self.timeout)
