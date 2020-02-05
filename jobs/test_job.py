from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.user import User
from solariat_bottle.jobs.manager import job, manager, terminate_handler
from solariat_bottle.utils.tweet import TwitterApiRateLimitError
import time


@job('pytest', timeout=10)
def some_hanging_func(channel, user_id):
    for i in xrange(10):
        print 'some_func: doing work', i
        time.sleep(0.1)

    manager.produce_state_update({})

    print 'func is hanging now'
    time.sleep(100)
    return 1

@terminate_handler(some_hanging_func)
def terminage_func(channel, user_id):
    print 'handle proper shutdown of channel'


@job('pytest')
def some_rate_limited_func(channel, user_id):
    print 'start working'
    time.sleep(5)
    print 'rate limits hit'
    raise TwitterApiRateLimitError('tweepy_api_method', 300)


if __name__ == '__main__':
    from solariat_bottle.jobs.test_job import some_hanging_func, some_rate_limited_func

    user = User.objects.find_one(email='super_user@solariat.com')
    channel = TwitterServiceChannel.objects.find_one_by_user(user)

    # some_hanging_func(channel, user.id)
    from solariat.utils.logger import setup_logger
    from solariat_bottle.settings import LOG_LEVEL
    LOG_FORMAT = '%(asctime)-15s (%(threadName)-9s) %(levelname)s %(message)s'
    setup_logger('kafka.conn', level=LOG_LEVEL, format=LOG_FORMAT, patch_logging=True)
    setup_logger('kafka.client', level=LOG_LEVEL, format=LOG_FORMAT, patch_logging=True)

    some_rate_limited_func(channel, user.id)
