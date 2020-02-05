from solariat_bottle.daemons.twitter.stream.common import sleep
import signal
import sys
import json
import logging
from solariat_bottle.daemons.base import BaseExternalBot
from solariat_bottle.settings import LOGGER
from solariat.utils.timeslot import now


trap_signals = {
    getattr(signal, name): name
    for name in ['SIGINT', 'SIGQUIT', 'SIGTERM', 'SIGHUP', 'SIGUSR1', 'SIGUSR2']
}


class BaseStreamBot(BaseExternalBot):

    def __init__(self, username, lockfile, concurrency=1, heartbeat=60,
                 stream_manager_cls=None, db_events=None, logger=LOGGER,
                 **kwargs):
        """
         :type stream_manager_cls: solariat_bottle.daemons.twitter.stream.base.manager.StreamManager
        """
        super(BaseStreamBot, self).__init__(username=username,
                                            lockfile=lockfile,
                                            concurrency=concurrency,
                                            name=self.__class__.__name__,
                                            **kwargs)

        self.server = stream_manager_cls(self, logger)
        self.heartbeat = heartbeat
        self.logger = logger
        self.db_events = db_events
        self.dumper = logging.getLogger('dumper')
        self.server.start()

    def run(self):
        self.on_start()
        self._running = True
        while not self.stopped():
            self.logger.info("heartbeat")
            self.server.heartbeat()
            self.wait(self.heartbeat)

    def stop(self):
        """ Attempt to gracefully stop the bot and all other threads running for it """
        self.server.stop()
        super(BaseStreamBot, self).stop()

    def signal(self, sgn):
        self.logger.info("Received signal %s (%s)" % (sgn, trap_signals.get(sgn)))

        if sgn == signal.SIGHUP:
            self.server.sync_streams()
        elif sgn in {signal.SIGUSR1, signal.SIGUSR2}:
            try:
                status = self.get_status()
                print('---')
                print(json.dumps(status, indent=4))
                print('---')
                sys.stdout.flush()

                if sgn == signal.SIGUSR2:
                    status.update({"timestamp": now()})
                    self.db_events.add_bot_status(status)
            except:
                self.logger.exception("dm_bot.signal")
        elif sgn in {signal.SIGINT, signal.SIGQUIT, signal.SIGTERM}:
            self.stop()
            # gevent.get_hub().destroy()
            timeout = self.heartbeat
            for idx in xrange(timeout):
                sleep(1)
                if not self.isAlive():
                    break
            else:
                print("Bot never stopped after waiting %s seconds." % (timeout,))
                sys.exit(2)
            sys.exit(0)

    def dump_message(self, msg):
        try:
            self.dumper.info(msg)
        except:
            self.logger.exception("dumper exception")

    def post_received(self, post_message, stream=None):
        """ Expose post_received functionality mainly for testing purposes. Could also use
         it for loading post data directly through bot in case of historics / load_data scripts """
        self.dump_message(post_message)
        if isinstance(post_message, basestring):
            try:
                event_json = json.loads(post_message)
            except ValueError:
                self.logger.exception(post_message)
                return False
        else:
            event_json = post_message

        try:
            self.on_message(event_json, stream=stream)
        except Exception, err:
            self.logger.exception(err)

    def on_message(self, event_json, stream=None):
        pass

    def on_start(self):
        pass

    def isAlive(self):
        bot_alive = super(BaseStreamBot, self).isAlive()
        server_alive = self.server.isAlive()
        self.logger.info("%s.isAlive bot:%s server:%s", self.__class__.__name__, bot_alive, server_alive)
        return bot_alive or server_alive

    def get_status(self):
        bot_stats = {
            "alive": self.isAlive(),
            "running": self.is_running(),
            "busy": self.is_busy(),
            "blocked": self.is_blocked(),
            "qsize": self.q_size(),
            "post_creators": {
                "total": len(self.creators),
                "stats": self.creators.get_status()
            },
            "sanity_checker": self.checker.get_status()
        }
        return {"bot": bot_stats, "stream_manager": self.server.get_status()}

    def listen_signals(self, on_gevent=True):
        if on_gevent:
            import gevent

            for sgn in trap_signals:
                gevent.signal(sgn, self.signal, sgn)
        else:
            def handle_signal(sgn, frame):
                self.signal(sgn)

            for sgn in trap_signals:
                signal.signal(sgn, handle_signal)
            signal.pause()
