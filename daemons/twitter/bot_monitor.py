import argparse
import os
import signal
import sys
import time
from bson import json_util

from solariat_bottle.daemons.twitter.stream.eventlog import PublicStreamDbEvents, UserStreamDbEvents
import solariat_bottle.app


def get_status(options):
    try:
        with open(options.pidfile) as f:
            pid = int(f.readline())
    except:
        print("Can't get bot pid")
        sys.exit(-1)

    os.kill(pid, signal.SIGUSR2)
    time.sleep(1)
    # mongo solariat_bottle --eval="db.twsbot_pub_status.find().sort({'_id': -1}).limit(1).pretty()"
    coll = options.bot_events.status_coll
    # print coll
    return coll.find_one(sort=[('_id', -1)])


def parse_options():
    parser = argparse.ArgumentParser(
        description=r"""Twitter bots monitor""",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--bot',
                        help='public|user')
    parser.add_argument('--pidfile',
                        help='path to bot pidfile')
    parser.add_argument('--mode',
                        default='dev')
    parser.add_argument('--debug', action='store_true', default=False)
    parser.set_defaults(bot='public')

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    if args.bot == 'public':
        args.bot_events = PublicStreamDbEvents()
    elif args.bot == 'user':
        args.bot_events = UserStreamDbEvents()

    return args


if __name__ == '__main__':
    options = parse_options()

    print json_util.dumps(get_status(options), indent=4)
