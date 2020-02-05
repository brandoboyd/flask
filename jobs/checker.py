#!/usr/bin/env python
from solariat_bottle.jobs.creator import JobStatus
from solariat_bottle.jobs.manager import manager
from solariat.utils.timeslot import now, utc
from solariat_bottle.settings import LOGGER
import solariat_bottle.db   # setup connection

from datetime import timedelta


def main(manager=manager):
    """ Supposed to be invoked by cron periodically
    """

    # 1. check sleeping jobs
    _now = now()
    for job_status in JobStatus.objects.find(status=JobStatus.SLEEPING):
        if utc(job_status.awake_at) > _now:
            continue

        job = manager.registry.get(job_status.name)
        manager.producer.send_message(job.topic, job_status)
        LOGGER.info('Job: %s awakened and sent to execution.', job_status.id)

    # 2. check timed out jobs
    for job_status in JobStatus.objects.find(status=JobStatus.RUNNING):
        job = manager.registry.get(job_status.name)

        last_activity = job_status.last_activity or job_status.started_date
        if _now - utc(last_activity) < timedelta(seconds=job.timeout):
            continue

        job_status.update(completion_date=now(), status=JobStatus.TERMINATED)
        LOGGER.info('Job: %s terminated. No activity last %s seconds.', job_status.id, job.timeout)
        if job.terminate_handler:
            try:
                job.terminate_handler(*job_status.args, **job_status.kwargs)
                LOGGER.info('terminate_handler complete for Job: %s.', job_status.id)
            except Exception as ex:
                LOGGER.error('Error executing terminate_handler: %s', ex, exc_info=True)


if __name__ == '__main__':
    import solariat_bottle.jobs.test_job
    main()
