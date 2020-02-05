from cStringIO import StringIO

from solariat.db import fields

from solariat.utils.timeslot import now
from solariat.utils.helpers import enum
from solariat.utils.unicode_csv import UnicodeWriter
from solariat.utils.memory_zip import InMemoryZipWriter

from solariat_bottle.db.auth import ArchivingAuthDocument, ArchivingAuthManager
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.utils.hash import mhash
from solariat.utils.hidden_proxy import unwrap_hidden


def hash_dict(d):
    return mhash(tuple(sorted(d.items())), n=128)

joined = lambda lst, sep=', ': sep.join(lst)


def translate(facet_type, values):
    facets = {
        'intentions': {'junk': 'other'},
        'statuses': {'actual': 'replied'}}
    translate_one = lambda v: facets.get(facet_type, {}).get(v, v)

    if isinstance(values, basestring):
        return translate_one(values)
    elif isinstance(values, (list, tuple)):
        return map(translate_one, values)


class DataExportManager(ArchivingAuthManager):
    def get_query(self, **kw):
        if 'input_filter' in kw:
            kw['input_filter_hash'] = hash_dict(kw.pop('input_filter', {}))
        return super(DataExportManager, self).get_query(**kw)

    def create_by_user(self, user, **kw):
        kw['created_by'] = user
        kw['recipients'] = [user]
        kw['account'] = user.current_account

        if 'input_filter' in kw:
            input_filter = kw.pop('input_filter', {})
            kw['_input_filter'] = input_filter
            kw['input_filter_hash'] = hash_dict(input_filter)

        doc = super(DataExportManager, self).create_by_user(user, **kw)
        return doc


class DataExport(ArchivingAuthDocument):

    STATES = dict(
        CREATED=0,
        FETCHING=1,
        FETCHED=2,
        GENERATING=3,
        GENERATED=4,
        SENDING=5,
        SENT=6,
        SUCCESS=7, ERROR=8, CANCELLED=9)
    State = enum(**STATES)

    account = fields.ReferenceField('Account', db_field='at')
    created_by = fields.ReferenceField('User', db_field='ur')
    recipients = fields.ListField(fields.ReferenceField('User'), db_field='rs')
    recipient_emails = fields.ListField(fields.StringField(), db_field='rse')
    state = fields.NumField(choices=STATES.values(),
                            default=State.CREATED, db_field='se')
    created_at = fields.DateTimeField(db_field='ct', default=now)
    _input_filter = fields.DictField(db_field='ir')
    input_filter_hash = fields.BytesField(db_field='irh')
    states_log = fields.ListField(fields.DictField(), db_field='sg')

    indexes = [('acl', 'input_filter_hash')]
    manager = DataExportManager

    def set_input_filter(self, data):
        self._input_filter = data
        self.input_filter_hash = hash_dict(data)

    input_filter = property(lambda self: self._input_filter, set_input_filter)

    def _log_state_change(self, from_state, to_state, extra_info):
        doc = {
            "from": from_state,
            "to": to_state,
            "ts": now()}
        if extra_info:
            doc["info"] = extra_info
        self.states_log.append(doc)
        return {"push__states_log": doc}

    def change_state(self, new_state, **kwargs):
        current_state = self.state
        assert \
            new_state in {self.State.ERROR, self.State.CANCELLED} \
            or new_state - current_state <= 2, \
            "Cannot switch to state %s from state %s" % (
                new_state, current_state)

        self.state = new_state
        update_dict = self._log_state_change(current_state, new_state, kwargs)
        update_dict.update(set__state=new_state)
        self.update(**update_dict)

    def to_json(self, fields_to_show=None):
        data = super(DataExport, self).to_json(
            fields_to_show=('id', 'input_filter_hash', 'state', 'created_at'))
        data['input_filter_hash'] = str(data['input_filter_hash'])
        return data

    def process(self, user, params=None):
        state = self.change_state
        S = DataExport.State
        initial_args = user, params

        pipeline = [
            (S.FETCHING, fetch_posts),
            (S.GENERATING, PostsCsvGenerator.generate_csv),
            (None, create_zip_attachments),
            (S.SENDING, DataExportMailer(self).send_email)
        ]

        try:
            args = initial_args
            for step, command in pipeline:
                step and state(step)
                result = command(*args)
                if not isinstance(result, tuple):
                    args = (result,)
                else:
                    args = result

            state(S.SUCCESS)
        except Exception as exc:
            state(S.ERROR, exception=unicode(exc))
            raise exc


def post_to_export_dict(p, *args, **kwargs):
    from solariat_bottle.utils.views import post_to_dict_fast

    post_dict = post_to_dict_fast(p, *args, **kwargs)
    post_dict['content'] = p.plaintext_content
    post_dict['parent'] = p.parent
    post_dict['created_at'] = p.created_at.strftime('%Y-%m-%d %H:%M:%S')
    post_dict['smart_tags'] = joined([tag['title'] for tag in post_dict['smart_tags']], sep='|')
    post_dict['intentions'] = joined(translate('intentions', [intent['type'] for intent in post_dict['intentions']]), sep='|')
    post_dict['filter_status'] = translate('statuses', post_dict['filter_status'])
    post_dict['topics'] = joined([topic['content'] for topic in post_dict['topics']], sep='|')
    return post_dict


def fetch_posts(user, params):
    from solariat_bottle.views.facets import get_posts, seq_types
    from solariat_bottle.utils.views import render_posts

    posts, are_more_posts_available = get_posts(params)
    channel = params['channel']
    if isinstance(channel, seq_types):
        channel = channel[0]

    post_dicts = render_posts(user, posts, channel, post_to_dict_fn=post_to_export_dict)

    parent_channel = channel
    if channel.is_smart_tag:
        parent_channel = Channel.objects.get(channel.parent_channel)
    channel_params = {
        "platform": parent_channel.platform,
        "channel_name": parent_channel.title,
        "channel_direction": "Inbound" if parent_channel.is_inbound else "Outbound"
    }
    return post_dicts, channel_params


class PostsCsvGenerator(object):

    class PrefetchedValue(unicode):
        pass

    @classmethod
    def csv_row(cls, value_getters, data):
        def gen():
            for v in value_getters:
                if isinstance(v, cls.PrefetchedValue):
                    yield v
                elif isinstance(v, (basestring, int)):
                    yield data[v]
                elif callable(v):
                    yield v(data)

        return list(gen())

    @classmethod
    def generate_csv(cls, iterable_data, context):
        header = [
            'Channel Type',
            'Channel Name',
            'Inbound/Outbound',
            'Post/Comment',
            'Initial Post',
            'Date/Time (UTC)',
            'Smart Tags',
            'Intentions',
            'Post Status',
            'Topics'
        ]

        def get_post_content(p):
            _get = lambda p, attr: \
                p.get(attr) if isinstance(p, dict) else getattr(p, attr)
            attr = 'url' if context.get('platform') == 'Twitter' else 'content'
            return unwrap_hidden(_get(p, attr))

        def get_initial_post(p):
            if p['parent']:
                return get_post_content(p['parent'])
            return ''

        value_getters = [
            cls.PrefetchedValue(context.get('platform')),
            cls.PrefetchedValue(context.get('channel_name')),
            cls.PrefetchedValue(context.get('channel_direction')),
            get_post_content,
            get_initial_post,
            'created_at',
            'smart_tags',
            'intentions',
            'filter_status',
            'topics'
        ]

        stream = StringIO()
        writer = UnicodeWriter(stream)
        writer.writerow(header)

        from solariat_bottle.settings import LOGGER

        for item in iterable_data:
            try:
                row = cls.csv_row(value_getters, item)
            except Exception:
                LOGGER.exception(u"Cannot generate csv tuple for %s" % item)
            else:
                LOGGER.debug(row)
                writer.writerow(row)
        stream.seek(0)
        return stream


def create_zip_attachments(stream, arcname='export_posts.csv'):
    zipper = InMemoryZipWriter()
    zipper.append(arcname, stream.read())
    #zipper.writetofile('export_posts.csv.zip')
    return [(arcname + ".zip", "application/zip", zipper.stream)]


class DataExportMailer(object):
    EMAIL_SUBJECT = "Genesys Social Analytics Data Export"

    def __init__(self, data_export_item):
        self.export_item = data_export_item

    def get_email_parameters(self):
        from solariat_bottle.db.channel.base import Channel
        from solariat_nlp.utils.topics import ALL_TOPICS

        ir = self.export_item.input_filter
        params = {}

        report_name_map = {
            'inbound-volume': 'Inbound Volume',
            'response-time': 'Reponse Time',
            'response-volume': 'Response Volume',
            'missed-posts': 'Missed Posts',
            'sentiment': 'Sentiment',
            'top-topics': 'Trending Topics'
        }
        if 'plot_type' in ir and ir['plot_type'] != 'topics':
            params['report_name'] = report_name_map.get(ir['plot_type'])

        def date_part(s):
            return s.split()[0]

        def date_range(d1, d2):
            d1 = date_part(d1)
            d2 = date_part(d2)
            if d1 == d2:
                return d1
            else:
                return "from: %s  to: %s" % (d1, d2)

        params['date_range'] = date_range(ir['from'], ir['to'])
        ch = Channel.objects.find_one(id=ir['channel_id'])
        if ch and ch.is_smart_tag:
            params['smart_tags'] = ch.title

        for key in {'intentions', 'statuses', 'languages', 'sentiments'}:
            if ir.get(key) and key not in set(ir.get('all_selected', [])):
                params[key] = joined(translate(key, ir[key]))

        if ir['topics']:
            params['keywords'] = joined([x['topic'] for x in ir['topics']
                                         if x['topic'] != ALL_TOPICS])
        if ir.get('agents'):
            from solariat_bottle.db.user import User

            agents = User.objects(id__in=ir['agents'], agent_id__ne=0)
            params['agents'] = joined([u.display_agent for u in agents])
        return params

    @property
    def recipient_emails(self):
        def make_rcp(u):
            name = [s.strip() for s in [u.first_name, u.last_name] if s and s.strip()]
            if name:
                return u"%s <%s>" % (' '.join(name), u.email)
            return u.email

        return map(make_rcp, self.export_item.recipients)

    def send_email(self, attachments):
        from solariat_bottle.utils.mailer import \
            send_mail, Message, _get_sender, render_template

        rcps = self.recipient_emails
        self.export_item.update(set__recipient_emails=rcps)

        msg = Message(
            subject=DataExportMailer.EMAIL_SUBJECT,
            sender=_get_sender(),
            recipients=rcps)

        params = self.get_email_parameters()
        msg.html = render_template("mail/export/posts.html", **params)
        msg.body = render_template("mail/export/posts.txt", **params)
        from solariat_bottle.settings import LOGGER
        LOGGER.debug(msg.body)
        for (filename, mimetype, stream) in attachments:
            msg.attach(filename, mimetype, stream.getvalue())
        send_mail(msg)