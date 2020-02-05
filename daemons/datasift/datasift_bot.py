#!/usr/bin/env python
# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import sys
import json
import yaml
import os

import time
sleep = lambda x: time.sleep(x)

from Queue     import Queue, Empty
from logging   import getLogger
from optparse  import OptionParser

from ws4py.client import WebSocketBaseClient

from solariat_bottle.settings        import get_var, LOGGER, LOG_LEVEL
from solariat_bottle.utils.logger    import setup_logger
from solariat_bottle.daemons.base    import BaseExternalBot
from solariat_bottle.daemons.helpers import (
    datasift_to_post_dict, get_datasift_hash, StoppableThread, systemd_notify,
    PostCreator, FeedApiPostCreator)

class DatasiftClient(WebSocketBaseClient):
    """ Datasift Websocket Client
    """

    WEBSOCKET_BASE_URL = 'websocket.datasift.com'

    def __init__(self, ds_login, ds_api_key, bot_instance, sanity_checker):
        self.username  = ds_login
        self.api_key   = ds_api_key
        self.bot_instance   = bot_instance
        self.sanity_checker = sanity_checker

        url = "ws://%s/multi?username=%s&api_key=%s" % (
            self.WEBSOCKET_BASE_URL, self.username, self.api_key)

        WebSocketBaseClient.__init__(self, url, None, None)

        self.dumper = getLogger('dumper')

    def handshake_ok(self):
        pass

    def dump_message(self, msg):
        "Writes a message to <options.dumpfile>"
        try:
            self.dumper.info(msg)
        except Exception, err:
            LOGGER.warning('%s', err)

    def received_message(self, msg):
        self.dump_message(msg)
        self.bot_instance.post_received(msg)

    # -- public api --
    def subscribe(self, ds_hash):
        LOGGER.info('subscribing %s', ds_hash)
        packet = json.dumps({'action': 'subscribe', 'hash': ds_hash})
        return self.send(packet)

    def unsubscribe(self, ds_hash):
        LOGGER.info('unsubscribing %s', ds_hash)
        packet = json.dumps({'action': 'unsubscribe', 'hash': ds_hash})
        return self.send(packet)

    def _write(self, b):
        # Just so we can make sure connection is still available
        self.sanity_checker.inc_received()
        super(DatasiftClient, self)._write(b)


class TestDatasiftClient(StoppableThread):
    """ Just a dummy client to be used for unit testing. Can be improved as we go to mymic as much as we
    need out of actual datasift client """
    WEBSOCKET_BASE_URL = 'test.genesys.test'

    def __init__(self, bot_instance):
        super(TestDatasiftClient, self).__init__()
        self.bot_instance   = bot_instance
        self.dumper = getLogger('dumper')

    def handshake_ok(self):
        pass

    def dump_message(self, msg):
        "Writes a message to <options.dumpfile>"
        try:
            self.dumper.info(msg)
        except Exception, err:
            LOGGER.warning('%s', err)

    def received_message(self, msg):
        self.dump_message(msg)
        self.bot_instance.post_received(msg)

    @property
    def terminated(self):
        return self.stopped()

    def subscribe(self, ds_hash):
        return True

    def unsubscribe(self, ds_hash):
        return True

    def connect(self):
        pass

    def run(self):
        while not self.stopped():
            LOGGER.info("Test DS Client still running.")
            sleep(5)


class DatasiftSubscriber(StoppableThread):
    """ This thread periodically checks DB for updated Datasift hash
        and (re)subscribes if necessary using a passed <DatasiftClient>.
    """
    _num = 0

    def __init__(self):
        num = self._num
        self._num = num + 1
        name = self.__class__.__name__ + ('-%s' % num if num else '')
        super(DatasiftSubscriber, self).__init__(name=name)
        self.cmd_queue = Queue()
        self.daemon    = True

    def run(self):
        cmd_queue = self.cmd_queue
        cur_hash  = None
        ds_client = None

        while not self.stopped():
            # make sure we intercept all errors
            try:
                # react on commands simultaneously making a 10 sec pause 
                try:
                    cmd, arg = cmd_queue.get(block=True, timeout=10 if not get_var('ON_TEST') else 1)
                    LOGGER.debug('received %s command', cmd)
                    if cmd == 'CLIENT':
                        ds_client = arg
                        cur_hash  = None
                    elif cmd == 'QUIT':
                        break
                except Empty:
                    LOGGER.debug('timeout (it\'s okay)')
                    pass

                if ds_client is None:
                    continue

                if ds_client.terminated:
                    LOGGER.warning('ds_client is terminated')
                    ds_client = None
                    continue

                # get current datasift hash from the db
                ds_hash = get_datasift_hash()
                if not ds_hash:
                    continue

                # subscibe/unsubscribe if necessary
                if not cur_hash:
                    ds_client.subscribe(ds_hash)

                elif cur_hash != ds_hash:
                    ds_client.unsubscribe(cur_hash)
                    ds_client.subscribe(ds_hash)

                # remember the current hash
                cur_hash = ds_hash

            except Exception, err:
                LOGGER.error(err, exc_info=True)
                pass

        LOGGER.info('quit')

    def set_client(self, client):
        "Passes a new <DatasiftClient> to the working thread using cmd_queue"
        self.cmd_queue.put(('CLIENT', client))

    def quit(self):
        "Passes a QUIT command to the working thread using its cmd_queue"
        self.cmd_queue.put(('QUIT', None))


class DatasiftBot(BaseExternalBot):
    """ Encapsulate all the required components for a fully functional datasift bot.

    There are:
     - one DatasiftClient, makes actualy connection to datasift websocket and just
       pushes incoming posts to a queue from where they can get processed
     - one DatasiftSubscriber with the role to handle subscription/unsubscription of
       the DatasiftClient based on any hash changes
     - one SanityChecker which counts volume of inbound posts and volume of skipped
       posts to try and detect anomalies
     - a number of PostCreator objects which pick posts from the queue populated by
       the DatasiftClient, match them to channels and just call post factory_by_user
    """

    def __init__(self, username, ds_login, ds_api_key, lockfile, concurrency=1, **kwargs):
        """
        :param username: The superuser email we're going to user on GSA side to create inbound posts
        :param ds_login: The username from datasift
        :param ds_api_key: The datasift API key
        :param lockfile: A unique lockfile user to make sure we are not running two instances at once
        :param concurrency: The number of parallel PostCreators we want to process inbound posts
        :param kwargs: Additional parameters for bot initialization
            - post_creator None|PostCreator|FeedApiPostCreator
            - password (*)
            - url      (*)
            (*) required if post_creator=FeedApiPostCreator
        """
        super(DatasiftBot, self).__init__(username=username,
                                          lockfile=lockfile,
                                          concurrency=concurrency,
                                          name=self.__class__.__name__,
                                          **kwargs)

        self.ds_login = ds_login
        self.ds_api_key = ds_api_key

        self.ds_subscriber = DatasiftSubscriber()
        self.ds_subscriber.start()

        systemd_notify()

    def run(self):
        self.ds_client = None

        while not self.stopped():
            try:
                del self.ds_client  # to garbage-collect the old client ASAP
                self._running = False

                if not get_var('ON_TEST'):
                    self.ds_client = DatasiftClient(ds_login=self.ds_login,
                                                    ds_api_key=self.ds_api_key,
                                                    bot_instance=self,
                                                    sanity_checker=self.checker)
                else:
                    self.ds_client = TestDatasiftClient(bot_instance=self)

                self.ds_client.connect()
                self._running = True

                LOGGER.info('connected to %s', self.ds_client.WEBSOCKET_BASE_URL)

                self.checker.set_client(self.ds_client)
                self.ds_subscriber.set_client(self.ds_client)

                self.ds_client.run()  # receives posts from Datasift
            except Exception as e:
                LOGGER.error(e, exc_info=True)
                sleep(5)  # wait a bit on any unexpected error

    def stop(self):
        """ Attempt to gracefully stop the bot and all other threads running for it """
        self.ds_client.stop()
        self.ds_subscriber.quit()
        super(DatasiftBot, self).stop()

    def post_received(self, post_field):
        """ Expose post_received functionality mainly for testing purposes. Could also use
         it for loading post data directly through bot in case of historics / load_data scripts """
        self.checker.inc_received()
        try:
            data = json.loads(str(post_field))
        except ValueError, err:
            LOGGER.warning(err)
            pass
        else:
            if 'status' in data:
                LOGGER.error(data['message'])
            elif 'hash' in data:
                data = data['data']
                if 'twitter' in data:
                    LOGGER.debug('received %s (%s bytes)', repr(data)[:60]+'...', len(data))
                    try:
                        post_fields = datasift_to_post_dict(data)
                        if post_fields:
                            self.post_queue.put(post_fields)
                    except Exception, err:
                        LOGGER.error(err)

    def isAlive(self):
        bot_alive = super(DatasiftBot, self).isAlive()
        subscriber_alive = self.ds_subscriber.isAlive()
        return bot_alive or subscriber_alive


def setup_dumper(options):
    from logging          import NullHandler, getLogger, Formatter, INFO
    from logging.handlers import WatchedFileHandler

    dumper = getLogger('dumper')
    dumper.setLevel(INFO)

    if options.dumpfile:
        handler = WatchedFileHandler(options.dumpfile, delay=True)
    else:
        handler = NullHandler()

    dumper.addHandler(handler)

    formatter = Formatter("%(message)s")
    handler.setFormatter(formatter)

    return dumper


def main(bot_options):
    post_creator_factory = {
        'factory_by_user': PostCreator,
        'http_post_api': FeedApiPostCreator
    }

    ds_bot = DatasiftBot(username=bot_options.username,
                         ds_login=bot_options.ds_login,
                         ds_api_key=bot_options.ds_api_key,
                         lockfile=bot_options.lockfile,
                         concurrency=bot_options.concurrency,
                         password=bot_options.password,
                         url=bot_options.url,
                         post_creator=post_creator_factory.get(bot_options.post_creator))
    ds_bot.start()
    ds_bot.join()


if __name__ == '__main__':
    io_pool.run_prefork()
    parser = OptionParser(usage="Usage: %prog [options]")
    parser.add_option(
        '--config',
        action  = 'store',
        type    = 'string',
        default = '',
        help    = "Bot config file"
    )
    parser.add_option('--username', action='store', type='string', help='Solariat user')
    parser.add_option('--password', action='store', type='string', help='Solariat user password (required when --post_creator=http_post_api)')
    parser.add_option('--url', action='store', type='string', help='Base url (required when --post_creator=http_post_api)')
    parser.add_option(
        '--post_creator',
        action='store',
        type='string',
        default='factory_by_user',
        help='Post creation strategy (factory_by_user | http_post_api) [default: %%default]')

    parser.add_option('--ds_login',   action='store', type='string', help='Datasift user')
    parser.add_option('--ds_api_key', action='store', type='string', help='Datasift API key')
    parser.add_option('--pidfile', action='store', type='string')

    parser.add_option(
        '--lockfile',
        action  = 'store',
        type    = 'string',
        default = '/tmp/datasift_bot.lock',
        help    = "[default: %%default]"
    )
    parser.add_option('--dumpfile', action='store', type='string', help='file to dump incoming posts')

    parser.add_option(
        '--concurrency',
        metavar = 'N',
        action  = 'store',
        type    = 'int',
        default = 16,
        help    = "number of post-creating threads [default: %%default]"
    )
    parser.add_option(
        '--mode',
        action  = 'store',
        type    = 'string',
        default = 'dev',
        help    = "app mode: %s [default: %%default]" % ', '.join(get_var('DB_NAME_MAP').keys())
    )

    options, args = parser.parse_args()

    config_from_file = {}
    if options.config:
        with open(options.config) as conf:
            try:
                config_from_file = yaml.load(conf)
            except:
                print("Cannot load config from file %s" % options.config)

    # merge options from config file,
    # command-line passed arguments have priority
    for opt, value in config_from_file.items():
        if not hasattr(options, opt) or getattr(options, opt) is None:
            setattr(options, opt, value)

    if not (options.username and options.ds_login and options.ds_api_key):
        parser.print_help()
        sys.exit(1)

    if options.post_creator == 'http_post_api' and not (options.password and options.url):
        parser.print_help()
        sys.exit(1)

    LOG_FORMAT = '%(asctime)-15s (%(threadName)-9s) %(levelname)s %(message)s'
    setup_logger(LOGGER, level=LOG_LEVEL, format=LOG_FORMAT, patch_logging=True)

    if options.pidfile:
        open(options.pidfile, "w+").write(str(os.getpid()))

    setup_dumper(options)

    main(options)

