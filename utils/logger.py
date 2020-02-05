# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

# imported from here
from solariat.utils.logger import setup_logger  # NOQA
setup_logger  # disable pyflakes warning
from logging   import Handler, LogRecord
from traceback import extract_stack, print_exc


def get_tango_handler():
    """ Returns the tango logging handler singleton.
    """
    return TangoHandler.instance()


def make_post(system_user, channel, content,
              event_name="system_logging",
              account="Solariat",
              user="system@solariat.com"):
    ''' Take a post dictionary and make a post for logging'''
    from solariat_bottle.db.post.utils import factory_by_user
    from solariat_nlp import sa_labels

    # Topics are created to allow easier analysis
    topics = [
        "%s %s %s" % (event_name, account, user),
        "%s %s"    % (user, event_name),
        "%s %s"    % (account, event_name),
        "%s %s %s" % (account, user, event_name),
        ]

    topics = [t.lower() for t in topics]

    speech_act = dict(
        content              = content,
        intention_type       = "Junk",
        intention_type_id    = sa_labels.SATYPE_TITLE_TO_ID_MAP["Junk"],
        intention_type_conf  = 1.0,
        intention_topics     = topics,
        intention_topic_conf = 1.0
        )

    post_content = "%s. %s%s%s" % (content, account, user, event_name)

    post = factory_by_user(system_user,
                           channel=channel,
                           content=post_content,
                           speech_acts=[speech_act],
                           sync=True)
    return post


class TangoHandler(Handler):
    '''
    This class is designed to stream log output to a dedicated
    Tango Channel in the current database.
    '''
    _tango_handler = None

    def __init__(self, *args, **kw):
        super(TangoHandler, self).__init__(*args, **kw)

        self._account = None
        self._channel = None
        self._user    = None

    @classmethod
    def instance(cls):
        if cls._tango_handler is None:
            cls._tango_handler = TangoHandler()
        return cls._tango_handler

    @property
    def account(self):
        if not self._account:
            from solariat_bottle.db.account import Account
            self._account = Account.objects.get_or_create(
                name    = "SOLARIAT_OPERATIONS"
            )

        system_acct = self._account.ACCOUNT_TYPE_SYSTEM
        if self._account.account_type != system_acct:
            self._account.account_type = system_acct
            self._account.update(set__account_type=system_acct)

        return self._account

    @property
    def user(self):
        if not self._user:
            from solariat_bottle.db.user import User
            self._user = User.objects.get_or_create(
                email   = 'ops_user@solariat.com',
                account = self.account
            )
        return self._user

    @property
    def channel(self):
        if not self._channel:
            from solariat_bottle.db.channel.twitter import KeywordTrackingChannel

            self.account.add_perm(self.user)

            self._channel = KeywordTrackingChannel.objects.get_or_create(
                title   = "TANGO_LOG_STREAM",
                account = self.account
            )
            if not self._channel.can_edit(self.user):
                self.channel.add_perm(self.user)

        return self._channel

    def log_record_to_channel(self, record):
        ''' Do output as a post to our system '''
        return
        try:
            if isinstance(record, dict):
                return make_post(
                    self.user,
                    self.channel,
                    record['note'],
                    event_name = record['name'],
                    account    = record['account'],
                    user       = record['user']
                )

            if isinstance(record, str) or isinstance(record, unicode):
                content = record
            else:
                assert isinstance(record, LogRecord), "Invalid record type: %s" % record
                content = "%s (%s:%d)" % (
                    record.getMessage(),
                    record.pathname.split('/')[-1],
                    record.lineno
                )
            return make_post(self.user, self.channel, content)

        except Exception, exc:
            # use print here to avoid recursion
            print "Failed to log record %s" % record
            print_exc()
            if hasattr(exc, 'traceback'):
                print exc.traceback

    def _already_called(self):
        for entry in extract_stack():
            if entry[2].find('log_record_to_channel') >= 0:
                return True
        return False

    def emit(self, record):
        ''' Sends logging records to the database
        '''
        if not self._already_called():
            self.log_record_to_channel(record)


class Dumper(object):
    def __init__(self, filename=None, logger_name='datasift_historics_endpoint'):
        self.logger = None
        if not filename:
            return

        from logging.handlers import WatchedFileHandler
        from logging import Formatter, getLogger, INFO

        dumper = getLogger(logger_name)
        dumper.setLevel(INFO)
        handler = WatchedFileHandler(filename, delay=True)
        formatter = Formatter("%(message)s")
        handler.setFormatter(formatter)
        dumper.addHandler(handler)
        self.logger = dumper

    def log(self, data):
        if self.logger:
            self.logger.info(data)
