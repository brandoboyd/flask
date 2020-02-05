#!/usr/bin/env python

# from __future__ import absolute_import
#
# import facebook  # workaround a Python import issue (name shadowing)
# del facebook     # disable pyflakes warning

import os
from datetime import datetime, timedelta

from solariat_bottle.db.user import User
from solariat_bottle.settings import LOGGER, FB_DATA_PULL_USER
from solariat_bottle.tasks.scheduled.base import BaseScheduledTask, TaskStateEnum


MODULE_BASE = 'solariat_bottle.tasks.scheduled.'

TIME_GAP_IN_SECONDS = 50 #should be defined based on cron running settings to avoid, that task wasn't run


class ScheduledTaskRunner(object):

    def get_task_list(self, path):

        for module in os.listdir(path or '.'):
            if module == '__init__.py' or module[-3:] != '.py':
                continue
            __import__(MODULE_BASE+module[:-3], locals(), globals())

        tasks = [subclass.instance() for subclass in BaseScheduledTask.__subclasses__()]
        tasks_to_run = [task for task in tasks if self.should_run_now(task)]
        return tasks_to_run


    def should_run_now(self, task):

        return task.get_state() in [TaskStateEnum.WAIT_NEXT, TaskStateEnum.FAILED] and\
               (task._get_db_task().next_run - datetime.utcnow()) < timedelta(seconds=TIME_GAP_IN_SECONDS)


    def _log(self, message):

        LOGGER.info(message)


if __name__ == '__main__':

    runner = ScheduledTaskRunner()
    runner._log("Start execution for scheduled tasks")
    tasks = runner.get_task_list(os.path.dirname(__file__))
    runner._log("%d tasks should be executed" % len(tasks))
    user = User.objects.get(email=FB_DATA_PULL_USER)

    for task in tasks:
        runner._log('Start executing tasks %s' % task.__name__)
        task.execute(user)
        runner._log('Task %s execution finished. Task state is %s' % (task.__name__, task.get_state()))
