import unittest
import json
from mock import patch, Mock
from os.path import join, dirname
from solariat_bottle.db.conversation import Conversation
from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.tasks.scheduled.base import BaseScheduledTask, TaskStateEnum
from datetime import timedelta
from solariat_bottle.tasks.scheduled.facebook_pull import FBPostCommentsPullTask, FBPrivateMessagePullTask, \
    FBCheckConversationUpdate
from solariat_bottle.tests.base import BaseCase


class _TestScheduledTask(BaseScheduledTask):

    @classmethod
    def instance(cls):
        return cls._resolve(interval=timedelta(minutes=10))

    @classmethod
    def should_do(cls, user):
        pass


class TestScheduledTasks(BaseCase):

    def setUp(self):
        BaseCase.setUp(self)
        self.task = _TestScheduledTask.instance()


    def test_execute_task(self):

        self.assertEquals(self.task.get_state(), TaskStateEnum.WAIT_NEXT)
        next_run = self.task._get_db_task().next_run

        self.task.execute(self.user)
        self.task._get_db_task().reload()
        self.assertTrue(self.task._get_db_task().next_run > next_run)
        self.assertEquals(self.task.get_state(), TaskStateEnum.WAIT_NEXT)


class TestFBPostCommentsPullTask(BaseCase):

    def setUp(self):

        BaseCase.setUp(self)
        self.task = FBPostCommentsPullTask.instance()
        self.sfc = FacebookServiceChannel.objects.create_by_user(self.user, title='sf1',
                                                         account=self.user.account)
        self.sfc.tracked_fb_event_ids.append('fake_event_id')
        self.sfc.tracked_fb_group_ids.append('fake_group_id')
        self.sfc.status = 'Active'
        self.sfc.save()


    @patch('solariat_bottle.tasks.scheduled.facebook_pull.fb_get_latest_posts')
    def test_execute_task(self, fake_task):

        self.assertEquals(self.task.get_state(), TaskStateEnum.WAIT_NEXT)
        next_run = self.task._get_db_task().next_run

        self.task.execute(self.user)
        self.task._get_db_task().reload()
        self.assertTrue(self.task._get_db_task().next_run > next_run)
        self.assertEquals(self.task.get_state(), TaskStateEnum.WAIT_NEXT)
        fake_task = fake_task.sync
        self.assertEquals(fake_task.call_count, 2)


class TestFBPrivateMessagePullTask(BaseCase):

    def setUp(self):

        BaseCase.setUp(self)
        self.task = FBPrivateMessagePullTask.instance()
        self.sfc = FacebookServiceChannel.objects.create_by_user(self.user, title='sf1',
                                                         account=self.user.account)
        self.sfc.facebook_page_ids.append('fake_page_id')
        self.sfc.status = 'Active'
        self.sfc.save()


    @patch('solariat_bottle.tasks.scheduled.facebook_pull.fb_get_latest_pm')
    def test_execute_task(self, fake_task):

        self.assertEquals(self.task.get_state(), TaskStateEnum.WAIT_NEXT)
        next_run = self.task._get_db_task().next_run

        self.task.execute(self.user)
        self.task._get_db_task().reload()
        self.assertTrue(self.task._get_db_task().next_run > next_run)
        self.assertEquals(self.task.get_state(), TaskStateEnum.WAIT_NEXT)
        fake_task = fake_task.sync
        fake_task.assert_called_once_with(self.sfc, self.sfc.facebook_page_ids[0], self.user)


@unittest.skip("98% chance this code isn't in use anymore")
class TestFBCheckConversationUpdate(BaseCase):

    def setUp(self):

        BaseCase.setUp(self)
        self.task = FBCheckConversationUpdate.instance()
        self.sfc = FacebookServiceChannel.objects.create_by_user(self.user, title='sf1',
                                                         account=self.user.account)

        self.sfc.status = 'Active'
        self.sfc.save()

        self.post = self._create_db_post(
            channel = self.sfc,
            content = "Some funny text",
            url = "708608465882686_708610792549120"
        )


    @patch('solariat_bottle.tasks.scheduled.facebook_pull.fb_get_comments_for')
    def test_task_execute(self, task_mock):

        task_mock.sync = Mock()
        task_mock.return_value = json.load(open(join(dirname(__file__), 'data/fb_comment1.json')))

        self.task.execute(self.user)
        conv = Conversation.objects.find_one(channel=self.sfc.id)
        task_mock.sync.assert_called_once_with(self.sfc, long(self.post.id).split(':')[1], self.user, conv.last_modified)

