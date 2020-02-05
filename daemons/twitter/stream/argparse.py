import os
import sys
import yaml

from optparse import OptionParser, Values
from solariat_bottle.daemons.helpers import get_default_lockfile
from solariat_bottle.settings import get_var, DB_NAME_MAP


def parse_options():
    parser = OptionParser(usage="Usage: %prog [options]")
    parser.add_option(
        '--config',
        action  = 'store',
        type    = 'string',
        default = '',
        help    = "Bot config file"
    )
    parser.add_option(
        '--kafka_config',
        action  = 'store',
        type    = 'string',
        default = '',
        help    = "Bot kafka config file"
    )
    parser.add_option(
        '--use_curl',
        action  = 'store_true',
        default = False,
        help    = "if set then use CURL multi connections, otherwise UserStream greenlets"
    )
    parser.add_option(
        '--username',
        action  = 'store',
        type    = 'string',
        default = get_var('TWITTER_BOT_USERNAME', 'super_user@solariat.com'),
        help    = "[default: %%default]"
    )
    parser.add_option('--password', action='store', type='string', help='Solariat user password (required when --post_creator=http_post_api)')
    parser.add_option('--url', action='store', type='string', help='Base url (required when --post_creator=http_post_api)')
    parser.add_option(
        '--post_creator',
        action='store',
        type='string',
        default='factory_by_user',
        help='Post creation strategy (factory_by_user | http_post_api) [default: %%default]')
    parser.add_option(
        '--post_creator_senders',
        action='store',
        type='int',
        default=4,
        help='Number of each post creator http senders')
    parser.add_option('--bot_user_agent', action='store', type='string', default=None)
    parser.add_option('--pidfile', action='store', type='string')
    parser.add_option(
        '--lockfile',
        action  = 'store',
        type    = 'string',
        default = get_default_lockfile(),
        help    = "[default: %default]"
    )
    parser.add_option('--dumpfile', action='store', type='string', help='file to dump incoming posts')
    parser.add_option(
        '--concurrency',
        metavar = 'N',
        action  = 'store',
        type    = 'int',
        default = 2,
        help    = "number of post-creating green threads [default: %default]"
    )
    parser.add_option(
        '--multiprocess_concurrency',
        metavar = 'N1',
        action  = 'store',
        type    = 'int',
        default = 0,
        help    = "number of post-creating processes, 0 - do not fork, start greenlets in current process [default: %default]"
    )
    parser.add_option(
        '--mode',
        action  = 'store',
        type    = 'string',
        default = 'dev',
        help    = "app mode: %s [default: %%default]" % ', '.join(DB_NAME_MAP)
    )
    parser.add_option('--only_accounts', action='store', type='string', help='accounts to track only, comma separated ids')
    parser.add_option('--exclude_accounts', action='store', type='string', help='exclude accounts, comma separated ids')
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
        opt_val = getattr(options, opt, None)
        parser_opt = parser.get_option('--' + opt)

        if not opt_val or opt_val is None or not parser_opt or parser_opt.default == opt_val:
            setattr(options, opt, value)

    if not options.username:
        parser.print_help()
        sys.exit(1)

    if options.post_creator == 'http_post_api' and not (options.password and options.url):
        parser.print_help()
        sys.exit(1)

    if options.pidfile:
        open(options.pidfile, "w+").write(str(os.getpid()))

    if not hasattr(options, 'use_kafka'):
        setattr(options, 'use_kafka', False)

    return options

def parse_kafka_options(bot_options):

    options = Values()

    config_from_file = {}
    if bot_options.kafka_config:
        with open(bot_options.kafka_config) as conf:
            try:
                config_from_file = yaml.load(conf)
            except:
                print("Cannot load config for kafka from file %s" % bot_options.kafka_config)

    for opt, value in config_from_file.items():
        setattr(options, opt, value)

    return options