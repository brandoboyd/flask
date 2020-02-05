#!/usr/bin/python2.7
import sys
import cgi
import time
import urlparse
from optparse import OptionParser
from gevent import pywsgi, monkey, spawn

from solariat_bottle.settings import get_var
from solariat_bottle.utils import facebook_driver

if not get_var('ON_TEST'):  # Only tests would be blocked by this, we still use gevent based pywsgi server to handle
    monkey.patch_all()      # realtime update calls

import facebook

from solariat_bottle.settings  import LOGGER, LOG_LEVEL, DB_NAME_MAP, FACEBOOK_APP_ID, FACEBOOK_APP_SECRET
from solariat_bottle.utils.logger import setup_logger
from solariat_bottle.daemons.facebook.facebook_client import FacebookBot

VERIFY_TOKEN = 'token'


BOT_INSTANCE = None

class WebApp(object):

    def __init__(self, callback_url):
        self.start_time = int(time.time())
        self.path = urlparse.urlparse(callback_url).path

    def callback(self, env, start_response):
        if env['REQUEST_METHOD'] == 'GET':
            if env['PATH_INFO'] == self.path:
                args = cgi.parse_qs(env['QUERY_STRING'], keep_blank_values=1)
                if VERIFY_TOKEN == args['hub.verify_token'][0]:
                    start_response('200 OK', [('Content-Type', 'text/html')])
                    return [args['hub.challenge'][0]]
            if env['PATH_INFO'] == '/uptime':
                start_response('200 OK', [('Content-Type', 'text/html')])
                return ['up %d seconds' % (int(time.time()) - self.start_time)]

        if env['REQUEST_METHOD'] == 'POST':
            if env['CONTENT_TYPE'] == 'application/json':
                data = env['wsgi.input'].read()
                if BOT_INSTANCE is not None:
                    BOT_INSTANCE.post_received(data)
                else:
                    LOGGER.warning("Did not find any facebook bot.")
                start_response('200 OK', [('Content-Type', 'text/html')])
                return []

        start_response('404 Not Found', [('Content-Type', 'text/html')])
        return ['<h1>Not Found</h1>']


def subscribe_to_app(server, callback_url):
    while not server.started:
        LOGGER.warn("Server not started, going to sleep")
        time.sleep(5)
    LOGGER.info("Subscribing to app")
    # Now subscribe to our app on facebook
    G = facebook_driver.GraphAPI(version='2.2')
    app_access_token = FACEBOOK_APP_ID + "|" + FACEBOOK_APP_SECRET
    path = FACEBOOK_APP_ID + "/subscriptions"
    post_args = {'access_token': app_access_token, 'callback_url': callback_url,
                 'fields': 'feed', 'object': 'page', 'verify_token': 'token'}
    subs = G.request(G.version + "/" + path, post_args=post_args)
    if subs:
        print "Subscription response was: " + str(subs)

def get_listen_port(url):

    res = urlparse.urlparse(url)
    assert res.scheme in ('http', 'https'), "wrong scheme '%s'" % res.scheme

    if res.port:
        return res.port
    if res.scheme == 'https':
        return 443
    if res.scheme == 'http':
        return 80

def main(bot_options):

    if bot_options.port:
        port = bot_options.port
    else:
        port = get_listen_port(bot_options.callback_url)

    app = WebApp(bot_options.callback_url)
    server = pywsgi.WSGIServer(('0.0.0.0', port), app.callback)
    server.start()
    global BOT_INSTANCE

    subscriber = spawn(subscribe_to_app, server, bot_options.callback_url)
    subscriber.start()

    BOT_INSTANCE = FacebookBot(username=bot_options.username,
                               lockfile=bot_options.lockfile,
                               concurrency=bot_options.concurrency)
    BOT_INSTANCE.start()
    BOT_INSTANCE.join()


if __name__ == "__main__":
    parser = OptionParser(usage="Usage: %prog [options]")
    parser.add_option('--url',
                      action='store',
                      type='string',
                      default='http://127.0.0.1:3031',
                      help="[default: %default]")
    parser.add_option('--callback_url',
                      action='store',
                      type='string',
                      default='http://127.0.0.1:8081',
                      help="[default: %default]")
    parser.add_option('--port', action='store', type='int')
    parser.add_option('--username', action='store', type='string')
    parser.add_option('--password', action='store', type='string')
    parser.add_option(
                     '--concurrency',
                     metavar = 'N',
                     action  = 'store',
                     type    = 'int',
                     default = 4,
                     help    = "number of post-creating threads [default: %%default]"
    )
    parser.add_option('--lockfile',
                      action='store',
                      type='string',
                      default='/tmp/facebook_bot2.lock',
                      help="[default: %default]")
    parser.add_option('--mode',
                      action='store',
                      type='string',
                      default='dev',
                      help="mode: %s [default: %%default]" % ', '.join(DB_NAME_MAP))
    (options, args) = parser.parse_args()

    if not (options.username and options.password):
        parser.print_help()
        sys.exit(1)

    LOG_FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
    setup_logger(LOGGER, level=LOG_LEVEL, format=LOG_FORMAT, patch_logging=True)

    main(options)
