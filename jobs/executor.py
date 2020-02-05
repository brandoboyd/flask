#!/usr/bin/env python
import solariat_bottle.app  # config keys, proxy, schema
from solariat_bottle.jobs.creator import JobStatus
from solariat_bottle.jobs.manager import manager
from solariat_bottle.jobs.config import jobs_config

from solariat_bottle.utils.tweet import TwitterApiRateLimitError
from solariat_bottle.settings import LOGGER
from solariat.utils.timeslot import now
import solariat_bottle.db   # setup connection

from datetime import timedelta


class NoJobStatusFound(Exception):
    pass

class NoRunnableJobFound(Exception):
    pass

class TerminateException(Exception):
    pass


class JobExecutor(object):

    def __init__(self, job_status, manager):
        self.job_status = job_status
        if not self.job_status:
            raise NoJobStatusFound()
        if self.job_status.status not in JobStatus.RUNNABLE_STATUSES:
            raise NoRunnableJobFound('Job: %s, status: %s. Another consumer may handle it.' % (
                self.job_status.id, self.job_status.status))

        self.job_git_commit = job_status.git_commit
        self.job = manager.registry.get(self.job_status.name)
        self.func = self.job.func
        self.args = self.job_status.args
        self.kwargs = self.job_status.kwargs
        manager.subscribe_state_update(self.__handle_state_signal)

    def execute(self):
        if self.job_status.status == JobStatus.SLEEPING:
            upd = {'awake_at': None, 'status': JobStatus.RUNNING}
            log_msg = 'Continue'
        else:
            upd = {'started_date': now(), 'status': JobStatus.RUNNING}
            log_msg = 'Start'
        self.job_status.update(**upd)
        LOGGER.info('%s Job: %s execution', log_msg, self.job_status.id)

        try:
            result = self.func(*self.args, **self.kwargs)
        except TerminateException as e:
            raise
        except TwitterApiRateLimitError as e:
            awake_at = now() + timedelta(seconds=e.wait_for)
            self.job_status.update(status=JobStatus.SLEEPING, awake_at=awake_at)
            LOGGER.warning('Job: %s execution interrupted. Waiting rate limits reset: %s sec.' % (
                self.job_status.id, e.wait_for))
        except Exception as ex:
            LOGGER.error('Job: %s execution failed with error: %s' % (self.job_status.id, ex),
                         exc_info=True)
            if self.job_git_commit != jobs_config.git_commit:
                LOGGER.error('Job: %s has git_commit: %s while consumer on: %s' % (
                    self.job_status.id, self.job_git_commit, jobs_config.git_commit))
            self.job_status.update(completion_date=now(), status=JobStatus.FAILED)
        else:
            self.job_status.update(completion_date=now(), status=JobStatus.SUCCESSFUL)
            # value=to_bin(result)
            LOGGER.info('Job: %s execution successful\nresult: %s', self.job_status.id, result)

    def __handle_state_signal(self, action, **state):
        LOGGER.debug('[StateUpdate] action:%s, state:%s', action, state)
        upd = {'last_activity': now()}
        if state != self.job_status.state:
            upd['state'] = state
        self.job_status.update(**upd)


class JobsConsumer(object):

    def __init__(self, topics=None, broker=None, group=None, manager=None):
        self.jobs_manager = manager
        self.consumer = self.jobs_manager.create_consumer(topics, group=group, broker=broker)

    def run(self):
        consumer = self.consumer
        for job_status in consumer:
            try:
                executor = JobExecutor(job_status, self.jobs_manager)
            except NoRunnableJobFound as ex:
                LOGGER.error(ex)
                continue
            except Exception as ex:
                LOGGER.error('Error creating JobExecutor: %s', ex, exc_info=True)
                continue
            try:
                executor.execute()
            except Exception:
                LOGGER.exception("Exception while executing job")
            try:
                consumer.commit()
            except Exception:
                LOGGER.exception("Could not commit offset")


class JobsSerialConsumer(JobsConsumer):

    class ListConsumer(list):
        def commit(self):
            pass

    def __init__(self, job_msg, manager=None):
        self.jobs_manager = manager
        self.consumer = self.ListConsumer([job_msg])


if __name__ == '__main__':
    from argparse import ArgumentParser
    import solariat_bottle.tasks.twitter
    from solariat_bottle.utils.config import sync_with_keyserver
    from solariat_bottle.tasks.nlp import warmup_nlp
    sync_with_keyserver()
    warmup_nlp()

    parser = ArgumentParser(description='Running Jobs Consumers.')
    parser.add_argument('--topics', type=str, nargs='+', help='List of topics to consume from.')
    parser.add_argument('--broker', type=str, nargs='+', help='List of brokers.')
    parser.add_argument('--group', type=str, help='Consumer group.')
    parser.add_argument('--idx', type=int, help='Identification numer to bind log/pid files.')
    options = parser.parse_args()

    params = {}
    params['topics'] = options.topics
    params['broker'] = options.broker or jobs_config.kafka_broker
    params['group'] = options.group or jobs_config.consumers_group

    consumer = JobsConsumer(manager=manager, **params)
    consumer.run()
