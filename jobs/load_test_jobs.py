import argparse
import random
import struct
from itertools import cycle, islice
from bson import ObjectId
from solariat_bottle.jobs.manager import job
from solariat_bottle.jobs.creator import JobStatus
from solariat_bottle.db.account import Account
from solariat.utils.timeslot import now, timedelta, datetime_to_timestamp


@job(topic='pytest')
def recovery(*args, **kwargs):
    pass


@job(topic='pytest')
def train_predictor(*args, **kwargs):
    pass


@job(topic='pytest')
def analysis(*args, **kwargs):
    pass


def random_date(interval=30 * 24 * 60 * 60):
    return now() - timedelta(seconds=random.randint(0, interval) + 300)


def gen_jobs():
    from solariat_bottle.jobs.load_test_jobs import recovery, train_predictor, analysis
    n = 0
    for account in cycle(Account.objects()[:]):
        for fn in [recovery, train_predictor, analysis]:
            for status in JobStatus.STATUSES:

                started_date = random_date()
                created_at = started_date - timedelta(seconds=random.randint(1, 30))
                object_id = ObjectId.from_datetime(created_at)
                object_id = ObjectId(object_id.binary[:-4] + struct.pack('>i', datetime_to_timestamp(created_at)))
                completion_date = started_date + timedelta(seconds=random.randint(1, 300))
                awake_at = completion_date + timedelta(seconds=random.randint(100, 300))
                result = fn(n)
                job_status = result.job_instance
                update_dict = {
                    'created_at': created_at,
                    'status': status,
                    'account': account.id}
                if status in (JobStatus.SUCCESSFUL, JobStatus.FAILED):
                    update_dict['started_date'] = started_date
                    update_dict['completion_date'] = completion_date
                if status in (JobStatus.RUNNING, JobStatus.ABANDONED):
                    update_dict['started_date'] = started_date
                if status in (JobStatus.SLEEPING, ):
                    update_dict['awake_at'] = awake_at

                job_status.update(**update_dict)
                JobStatus.objects.coll.remove({'_id': job_status.id})
                job_status.id = object_id
                job_status.save()
                n += 1
                yield job_status


def jobs_cmd(options):
    if options.action == 'load':
        JobStatus.objects.coll.remove({})
        return list(islice(gen_jobs(), options.n_jobs))
    elif options.action == 'clear':
        JobStatus.objects.coll.remove({})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--n_jobs', type=int, default=25)
    parser.add_argument('--action', default='load')
    args = parser.parse_args()
    jobs_cmd(args)
