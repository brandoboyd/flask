#!/usr/bin/env python
import subprocess
import os
from tempfile import gettempdir
import glob
import sys
import signal

import solariat_bottle.app
from solariat_bottle.jobs.executor import __file__ as executor_file
from solariat_bottle.jobs.config import jobs_config


JOBS_CONSUMERS_DIR = 'jobs_consumers'
JOBS_CONSUMER_LOG_TMPL = 'jobs_consumer_%s.log'
JOBS_CONSUMER_PID_TMPL = 'jobs_consumer_%s.pid'

def is_process_exists(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def make_log(logdir, idx):
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    return os.path.join(logdir, JOBS_CONSUMER_LOG_TMPL % idx)

def make_pid(piddir, idx, pid):
    if not os.path.exists(piddir):
        os.makedirs(piddir)
    pidfile = os.path.join(piddir, JOBS_CONSUMER_PID_TMPL % idx)
    with open(pidfile, 'w') as pfile:
        pfile.write(str(pid))

def is_consumers_running(piddir):
    pids = []
    pids_pattern = os.path.join(piddir, JOBS_CONSUMER_PID_TMPL % '*')
    for pidfile in glob.glob(pids_pattern):
        with open(pidfile, 'r') as pfile:
            pid = pfile.read()
            if pid and is_process_exists(int(pid)):
                print 'JobsConsumer already running with pid:%s' % pid
                pids.append(int(pid))
            else:
                os.unlink(pidfile)
    return pids

def stop_consumers(piddir, pids):
    print 'Stopping consumers...'
    for pid in pids:
        os.kill(pid, signal.SIGINT)
    print 'Consumers stopped.'


# TODO:
# - create pid/log dir with machine_id
# - add machine_id to stop
# - rewrite stopping: if not stopped after timeout, kill executors
if __name__ == '__main__':
    from argparse import ArgumentParser
    import solariat_bottle.jobs.test_job

    parser = ArgumentParser(description='Running Jobs Consumers.')
    parser.add_argument('--start', type=str, dest='machine', default=None,
                        help='start <machine_id> consumers.')
    parser.add_argument('--stop', action='store_true', help='stop machine consumers.')
    parser.add_argument('--piddir', type=str, help='set directory for pid files.')
    parser.add_argument('--logdir', type=str, help='set directory for log files.')

    options = parser.parse_args()
    if options.machine is None and not options.stop:
        print parser.print_help()
        print 'One of "--start <machine_id>" or "--stop" action must be defined.'
        sys.exit(1)

    default_dir = os.path.join(gettempdir(), JOBS_CONSUMERS_DIR)
    piddir = options.piddir or default_dir
    logdir = options.logdir or default_dir

    if options.stop:
        pids = is_consumers_running(piddir)
        if not pids:
            sys.exit(0)
        stop_consumers(piddir, pids)
        sys.exit(0)

    broker = jobs_config.kafka_broker
    if isinstance(broker, list):
        broker = ' '.join(broker)
    group = jobs_config.consumers_group
    processes = jobs_config.get_machine_options(options.machine)
    executor_file = executor_file.replace('.pyc', '.py')

    if is_consumers_running(piddir):
        print 'Stop machine consumers first.'
        sys.exit(1)

    idx = 0
    for params in processes:
        topics = params['topics']
        consumers = params['consumers']

        for n in xrange(consumers):
            logfile = make_log(logdir, idx)
            out = open(logfile, 'a')
            err = open(logfile, 'a')
            cmd = ['python', executor_file, '--topics']
            cmd.extend(topics)
            cmd.extend([
                '--broker', broker,
                '--group', group,
                '--idx', str(idx)
            ])
            p = subprocess.Popen(cmd, stdin=None, stdout=out, stderr=err)
            make_pid(piddir, idx, p.pid)
            idx += 1
            print 'JobsConsumer pid:%s started' % p.pid
