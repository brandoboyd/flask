from solariat_bottle.tests.base import BaseCase
from solariat_bottle.daemons.helpers import StoppableThread
from solariat_bottle.settings import LOGGER
import time
import random
import string
import json

from solariat_bottle.utils.stateful import *


class StatefulProcess(Stateful, StoppableThread):
    DELAY = 0.1

    def __init__(self, *args, **kwargs):
        self.counter = 0
        super(StatefulProcess, self).__init__(*args, **kwargs)

    @state_updater
    def do_work(self):
        self.counter += 1

    def run(self):
        while not self.stopped():
            self.do_work()
            self.wait(self.DELAY)

    def stateful_params(self):
        return {}  # '__class__': WorkerIsHolder injected if not present

    def serialize_state(self):
        return {
            'progress': self.counter,
        }

    def deserialize_state(self, state):
        self.counter = state['progress']


class TestStateful(BaseCase):

    def get_state_from_db(self):
        _class_ = StatefulProcess.get_stateful_cls()
        state_doc_qs = TaskState.objects.coll.find({'params._class_': _class_})
        assert state_doc_qs.count() == 1
        return next(state_doc_qs)

    def test_stateful(self):
        # 1. create stateful, run process, stop process, run process again, check assert state
        stateful = StatefulProcess()
        assert stateful.counter == 0, 'counter: %s' % stateful.counter
        stateful.start()

        time.sleep(1.5)
        assert stateful.counter > 0
        stateful.stop()
        stateful.join()

        saved_val = stateful.counter

        state_doc = self.get_state_from_db()
        assert state_doc['state']['progress'] == saved_val

        # 1.1 run process again, check assert state
        stateful = StatefulProcess()
        assert stateful.counter == saved_val
        stateful.start()
        time.sleep(0.5)
        assert stateful.counter > saved_val
        stateful.stop()
        stateful.join()
        saved_val = stateful.counter

        self.get_state_from_db()

        # 2. check reset state: run with reset will reset state in DB, check that
        stateful = StatefulProcess(reset_state=True)
        assert stateful.counter == 0
        stateful.start()
        time.sleep(1.5)
        assert stateful.counter < saved_val, 'current val: %s, saved val: %s' % (stateful.counter, saved_val)
        stateful.stop()
        stateful.join()
        saved_val = stateful.counter

        state_doc = self.get_state_from_db()

        # 3. check that in stateless mode, the State in DB will not changed
        stateless = StatefulProcess(stateless=True)
        assert stateless.counter == 0
        stateless.start()
        time.sleep(1.5)
        stateless.stop()
        stateless.join()
        assert stateless.counter > 0

        saved_val = state_doc['state']['progress']
        state_doc = self.get_state_from_db()
        assert saved_val == state_doc['state']['progress']

        # 4. test decorators
        # create same class but with devorators and run the same test


# Case 1:
# =====================================================================
# Simulate HistoricSubscription-like processes,
# where real state (& progress) holders are:
# - TwitterTimelineRequests (let's run them simultaneously)
# - HistoricLoader runs sequentally after TwitterTimelineRequests
# and Subscriber only gather state info from child requests & historic loader.

class Worker(Stateful, StoppableThread):
    DELAY = 0.1

    @property
    def cls_name(self):
        return self.__class__.__name__

    def __init__(self):
        self.w_status = 0
        super(Worker, self).__init__()

    @state_updater
    def do_work(self):
        self.w_status += 1

    def run(self):
        while not self.stopped():
            self.do_work()
            self.wait(self.DELAY)

    def get_progress(self):
        return self.w_status

    def stateful_params(self):
        return {}  # '__class__': WorkerIsHolder injected if not present

    def serialize_state(self):
        return {'key': self.w_status}

    def deserialize_state(self, state):
        self.w_status = state['key']


class ParallelWorkerOne(Worker):
    pass


class ParallelWorkerTwo(Worker):
    pass


class SerialWorker(Worker):
    pass


class Subscriber(object):
    def __init__(self):
        self.worker1 = ParallelWorkerOne()
        self.worker2 = ParallelWorkerTwo()
        self.serial = SerialWorker()

    def print_progress(self):
        info = {
            self.worker1.cls_name: self.worker1.get_progress(),
            self.worker2.cls_name: self.worker2.get_progress(),
            self.serial.cls_name: self.serial.get_progress(),
        }
        LOGGER.debug(json.dumps(info, indent=4))

    def fetch(self):
        self.worker1.start()
        self.worker2.start()

        for _ in xrange(3):
            time.sleep(1)
            self.print_progress()

        self.worker1.stop()
        self.worker2.stop()
        self.worker1.join()
        self.worker2.join()

        self.serial.start()
        for _ in xrange(2):
            time.sleep(1)
            self.print_progress()
        self.serial.stop()
        self.serial.join()


# def test_case1():
#     s = Subscriber()
#     s.fetch()


# Case 2:
# =====================================================================
# Simulate processes, where state holder is a process itself,
# but resulting progress is still built from process-progress and its child's progress.

class WorkerIsHolder(Stateful, StoppableThread):
    DELAY = 0.5

    def __init__(self):
        self.w_status = 0
        super(WorkerIsHolder, self).__init__()

    @state_updater
    def do_work(self):
        self.w_status += 1

    def run(self):
        while not self.stopped():
            self.do_work()
            self.wait(self.DELAY)

    def get_progress(self):
        return self.w_status

    @stateful_params
    def get_task_state_id(self):
        return {}  # '__class__': WorkerIsHolder injected if not present

    @serializer
    def serialize_(self):
        # super serialize_state(fields=[f_1, f_2, f_3])
        return {
            'key': self.w_status,
        }

    @deserializer
    def deserialize_(self, state):
        self.w_status = state['key']


class SubscriberIsHolder(Stateful, StoppableThread):
    DELAY = 2

    def __init__(self, start_date, end_date, **kwargs):
        self.worker = WorkerIsHolder()
        self.worker.daemon = True
        self.my_status = '0'
        self.start_date = start_date
        self.end_date = end_date
        super(SubscriberIsHolder, self).__init__(**kwargs)

    @property
    def cls_name(self):
        return self.__class__.__name__

    @state_updater
    def do_work(self):
        self.my_status += random.choice(string.ascii_uppercase)

    def run(self):
        LOGGER.debug('[%s restored?] my_status=%s', self.cls_name, self.my_status)
        self.worker.start()

        while not self.stopped():
            self.do_work()
            self.wait(self.DELAY)
            self.print_progress()

        self.worker.stop()
        self.worker.join()

    def print_progress(self):
        prog = {
            'my': self.my_status,
            'worker': self.worker.get_progress(),
        }
        LOGGER.debug('[%s progress] %s', self.cls_name, prog)

    def stateful_params(self):
        return {
            # 'start_date': self.start_date,
            # 'end_date': self.end_date,
            'key': ['val1', 'val2']
        }

    def serialize_state(self):
        return {
            'my_status': self.my_status
        }

    def deserialize_state(self, data):
        self.my_status = data['my_status']


# def test_case2():
#     end_date = datetime.now()
#     start_date = end_date - timedelta(days=1)
#     # s = SubscriberIsHolder(stateless=True)
#     # s = SubscriberIsHolder(reset_state=True)
#     s = SubscriberIsHolder(start_date=start_date, end_date=end_date)
#     s.start()
#     time.sleep(5)
#     s.stop()


# Case 3
# Parent, Child1(Parent), Child2(Paremt), both uses parent's stateful_id,
# workflow:
# child1 - progress, 1-50, child2- progress 51-100

class StatefulWork(Stateful, StoppableThread):

    def __init__(self, manager):
        self.counter = 0
        self.manager = manager
        super(StatefulWork, self).__init__()

    def serialize_state(self):
        status = {
            'cnt': self.counter,
            'worker': self.__class__.__name__,
        }
        self.manager.status = status
        return status

    def deserialize_state(self, state):
        self.counter = state['cnt']

    def run(self):
        while not self.stopped():
            self.do_work()
            self.wait(0.5)


class SerialWorker1(StatefulWork):

    @stateful_params_cls(StatefulWork)
    def stateful_params(self):
        return {}

    @state_updater
    def do_work(self):
        self.counter += 1


class SerialWorker2(StatefulWork):

    # stateful_params_cls(StatefulWork)
    def stateful_params(self):
        return {'_class_': StatefulWork}

    @state_updater
    def do_work(self):
        self.counter += 11


class WorkManager(object):
    def __init__(self):
        self.status = {}

    def get_status(self):
        LOGGER.debug('STATUS: %s', self.status)

    def run(self):
        worker1 = SerialWorker1(self)
        worker1.start()
        for _ in xrange(2):
            time.sleep(0.5)
            self.get_status()
        worker1.stop()

        worker2 = SerialWorker2(self)
        worker2.start()
        for _ in xrange(2):
            time.sleep(0.5)
            self.get_status()
        worker2.stop()

        worker1.join()
        worker2.join()


# def test_case3():
#     m = WorkManager()
#     m.run()
#
