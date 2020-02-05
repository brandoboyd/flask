from solariat_bottle.tests.base import BaseCase
from solariat_bottle.jobs.manager import manager, JobsManager
from solariat_bottle.jobs.executor import JobsConsumer, TerminateException
from solariat_bottle.jobs.registry import RegistryError
from solariat_bottle.jobs.creator import JobStatus as JobModel
from solariat_bottle.jobs.config import jobs_config
from solariat.tests.base import LoggerInterceptor

from mock import MagicMock
from threading import Thread
from datetime import datetime
import time


class ProducerConsumerTest(BaseCase):
    def setUp(self):
        super(ProducerConsumerTest, self).setUp()
        self.jobs_origin_transport = jobs_config.transport
        self.setup_jobs_transport('memory')

    def tearDown(self):
        self.setup_jobs_transport(self.jobs_origin_transport)
        super(ProducerConsumerTest, self).tearDown()

    def test_workflow(self):
        manager = JobsManager(jobs_config)
        job = manager.job
        manager.registry.add = MagicMock(side_effect=manager.registry.add)
        manager.producer.send = MagicMock(side_effect=manager.producer.send)

        @job(topic='pytest')
        def test_task(*args, **kwargs):
            pass

        assert manager.registry.add.call_count == 1

        # task with unsupported topic
        with self.assertRaises(RegistryError):
            @job(topic='unsupported')
            def task1(*args, **kwargs):
                pass

        @job(topic='pytest')
        def real_task(*args, **kwargs):
            pass

        # task with this name is already registered
        with self.assertRaises(RegistryError):
            @job(topic='pytest')
            def real_task(*args, **kwargs):
                pass

        job_args = ('a', 'b', 'c')
        job_kw = {'something': True}
        real_task(*job_args, **job_kw)
        self.assertEqual(JobModel.objects.count(), 1)
        job_item = JobModel.objects.get()
        self.assertTupleEqual(
            (job_item.topic, job_item.args, job_item.kwargs),
            ('pytest', job_args, job_kw)
        )
        expected_args = (job_item.topic, job_item.name, job_args, job_kw, job_item.metadata)
        manager.producer.send.assert_called_once_with(*expected_args)

        messages = []
        for message in manager.create_consumer(topics=[job_item.topic]):
            messages.append(message)
        self.assertEqual(len(messages), 1)
        msg = messages[0]
        self.assertIsNotNone(msg)
        self.assertEqual(msg, job_item)

    def test_consumer(self):
        manager = JobsManager(jobs_config)
        job = manager.job

        # test consumer/executor success
        @job('pytest')
        def task1(arg):
            return 1

        class Consumer(Thread):
            def run(self):
                JobsConsumer(['pytest'], manager=manager).run()

        Consumer().start()
        with LoggerInterceptor() as logs:
            task1(None)
            time.sleep(0.1)
            success = [1 for log in logs if 'execution successful\nresult: 1' in log.message]
            self.assertTrue(success)

        original_send_message = manager.producer.send_message
        send_message = MagicMock()
        manager.producer.send_message = send_message

        # test NoJobStatusFound
        send_message.side_effect = lambda topic, message: original_send_message(topic, None)

        Consumer().start()
        with LoggerInterceptor() as logs:
            task1(None)
            time.sleep(0.1)
            fail_nojob = [1 for log in logs if 'Error creating JobExecutor' in log.message
                          and log.levelname == 'ERROR']
            self.assertTrue(fail_nojob)

        # test NoPendingJobsFound
        def _create_running_job(topic, message):
            message.update(status=JobModel.RUNNING)
            return original_send_message(topic, message)
        send_message.side_effect = _create_running_job

        Consumer().start()
        with LoggerInterceptor() as logs:
            task1(None)
            time.sleep(0.1)
            fail_nojob = [1 for log in logs if 'Another consumer may handle it' in log.message
                          and log.levelname == 'ERROR']
            self.assertTrue(fail_nojob)

        # test execution fail (different git)
        newer_git_commit = 'newer'
        def _commit_hash_mismatch(topic, message):
            message.metadata = {'git_commit': newer_git_commit}
            return original_send_message(topic, message)

        send_message.side_effect = _commit_hash_mismatch

        @job('pytest')
        def fail_task():
            raise Exception('FakeInternalTaskError')

        Consumer().start()
        with LoggerInterceptor() as logs:
            fail_task()
            time.sleep(0.1)
            err = 'has git_commit: %s' % newer_git_commit
            fail = [1 for log in logs if err in log.message and log.levelname == 'ERROR']
            self.assertTrue(fail)

    def test_termination(self):
        from solariat_bottle.jobs.manager import manager, terminate_handler
        from solariat_bottle.jobs.checker import main as checker_process
        job = manager.job

        @job('pytest', timeout=0.01)
        def task1(arg):
            raise TerminateException('imagine consumer process is killed')

        global STATE_HANDLED
        STATE_HANDLED = False

        @terminate_handler(task1)
        def handle_state(arg):
            assert arg == 1
            global STATE_HANDLED
            STATE_HANDLED = True

        class Consumer(Thread):
            def run(self):
                JobsConsumer(['pytest'], manager=manager).run()

        c = Consumer()
        c.start()
        task1(1)
        time.sleep(0.1)

        job_doc = JobModel.objects.find_one()
        self.assertFalse(c.is_alive())
        self.assertEqual(job_doc.status, JobModel.RUNNING)

        checker_process()
        job_doc.reload()
        self.assertEqual(job_doc.status, JobModel.TERMINATED)
        self.assertTrue(STATE_HANDLED)

    def test_sleep_resume(self):
        from solariat_bottle.jobs.manager import JobsManager
        from solariat_bottle.jobs.checker import main as checker_process
        from solariat_bottle.utils.tweet import TwitterApiRateLimitError

        origin_transport = jobs_config.transport
        self.setup_jobs_transport('serial')
        manager = JobsManager(jobs_config)
        job = manager.job

        @job('pytest', timeout=0.01)
        def task_with_rate_limits(first_run):
            if first_run:
                raise TwitterApiRateLimitError('task_with_rate_limits', wait_for=0.01)

        start = datetime.utcnow()
        task_with_rate_limits(True)
        time.sleep(0.01)

        job_doc = JobModel.objects.find_one()
        self.assertEqual(job_doc.status, JobModel.SLEEPING)
        self.assertTrue(job_doc.awake_at > start)

        job_doc.args = (False,)
        job_doc.save()
        checker_process(manager)
        job_doc.reload()
        self.assertEqual(job_doc.status, JobModel.SUCCESSFUL)

        self.setup_jobs_transport(origin_transport)
