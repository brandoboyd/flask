# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

""" Channel specific end-points
"""

from flask import jsonify, request
from solariat_bottle.db.channel.facebook import EnterpriseFacebookChannel, \
    FacebookConfigurationException

from solariat.utils.lang.iso_codes import LANG_MAP

from solariat.utils.iterfu import flatten, repeat

from ..app              import app
from ..db.channel.base  import Channel, ServiceChannel, filtered_channels
from ..db.channel.twitter import EnterpriseTwitterChannel, TwitterConfigurationException
from ..db.channel_stats import aggregate_stats
from solariat_bottle.settings import LOGGER
from solariat_bottle.db.language import MultilanguageChannelMixin
from ..utils.decorators import login_required
from solariat.utils.timeslot import (
    parse_date_interval, guess_timeslot_level, datetime_to_timestamp_ms
)
from solariat_bottle.utils.views import parse_account, parse_bool
import solariat_bottle.api.exceptions as exc


def find_channels(user, account=None, channel_class=Channel, **kwargs):
    account = account or user.account
    return channel_class.objects.find_by_user(user, account=account, **kwargs)


@app.route('/reply_channels/json', methods=['GET'])
@login_required()
def reply_channels(user):
    """
    Returns a list of channels to which replies could be sent by this user.
    :param user:
    :return: JSON with list of channels
    """
    candidates = EnterpriseTwitterChannel.objects.find_by_user(user, status='Active')[:]
    l = [c.to_dict(fields2show=['id', 'title', 'status', 'type']) for c in candidates]
    return jsonify(ok=True, list=l)


@app.route('/channels/json', methods=['POST'])
@login_required()
def list_channels(user):
    data = request.json or {}
    account = parse_account(user, data)

    try:
        results = []
        if data.get('widget'):
            channels = filtered_channels(find_channels(user, account, status='Active'))
            for channel in channels:
                results.append({
                    "id": str(channel.id),
                    "title": channel.title})

        elif data.get('primitive'):
            channels = filtered_channels(find_channels(user, account),
                                         filter_service=True,
                                         filter_compound=True)
            for channel in channels:
                results.append({
                    "id": str(channel.id),
                    "title": channel.title,
                    "platform": channel.platform,
                    "is_dispatchable": channel.is_dispatchable})

        elif data.get('service'):
            channels = find_channels(user, account, channel_class=ServiceChannel)
            for channel in channels:
                results.append({
                    "id": str(channel.id),
                    "title": channel.title})

        else:
            channels = filtered_channels(find_channels(user, account))

            if data.get('outbound') or request.args.get('outbound'):
                channels = [ch for ch in channels if ch.is_dispatchable]

            channel_stats_map = {}

            if data.get('stats'):
                from_, to_ = parse_date_interval(data.get('from'), data.get('to'))
                level = guess_timeslot_level(from_, to_)
                from operator import itemgetter
                channel_ids = map(itemgetter('id'), channels)
                channel_stats_map = aggregate_stats(
                    user, channel_ids, from_, to_, level,
                    aggregate=(
                        'number_of_posts',
                        'number_of_false_positive',
                        'number_of_true_positive',
                        'number_of_false_negative'
                    )
                )
            for channel in channels:
                stats = channel_stats_map.get(str(channel.id))
                channel_dict = {
                    "id"                    : str(channel.id),
                    "title"                 : channel.title,
                    "type_name"             : channel.__class__.__name__,
                    "type"                  : "channel",
                    "parent"                : str(channel.parent_channel or ""),
                    "status"                : channel.status,
                    "description"           : channel.description,
                    "created_at"            : datetime_to_timestamp_ms(channel.created),
                    "platform"              : channel.platform,
                    "account"               : channel.account and channel.account.name,
                    "perm"                  : 'r' if channel.read_only else channel.perms(user),
                    "facebook_page_ids"     : channel.facebook_page_ids if hasattr(channel, 'facebook_page_ids') else None,
                    "facebook_access_token" : channel.facebook_access_token if hasattr(channel, 'facebook_access_token') else None,
                    "access_token_key"      : channel.access_token_key if hasattr(channel, 'access_token_key') else None,
                    "access_token_secret"   : channel.access_token_secret if hasattr(channel, 'access_token_secret') else None,
                    "twitter_handle"        : channel.twitter_handle if hasattr(channel, 'twitter_handle') else None,
                    "is_compound"           : channel.is_compound,
                    "stats"                 : stats}
                results.append(channel_dict)


        results.sort(key=lambda x: x['title'])
        return jsonify(ok=True, list=results)

    except Exception, exc:
        app.logger.error('error on /channels/json',
                         exc_info=True)
        return jsonify(ok=False, error=str(exc))


@app.route('/channels_by_type/json', methods=['POST'])
@login_required()
def list_channels_by_type(user):
    """ Get the list of channels filtered by type (inbound/outbound/service/all)
    """
    def parse_bool_param(param, default='no'):
        value = str(request.json.get(param) or default).lower()
        return (value in ('1','true','yes'))

    def get_parameters():
        if not hasattr(request, 'json'):
            raise RuntimeError('no json parameters provided')

        for key in request.json:
            if key not in ('type', 'serviced_only', 'parent_names'):
                raise RuntimeError('unsupported parameter: %r' % key)
        types = request.json.get('type') or 'all'

        if types == 'all' or types == ['all']:
            types = 'all'
        else:
            if isinstance(types, basestring):
                types = set([types])
            else:
                types = set(types)

            for typ in types:
                if typ not in ('inbound', 'outbound', 'service', 'dispatch', 'voc'):
                    raise RuntimeError('unsupported type: %s' % typ)

            if types == set(('inbound', 'outbound', 'service')):
                types = 'all'

        serv_only    = parse_bool_param('serviced_only')
        parent_names = parse_bool_param('parent_names')

        return types, serv_only, parent_names

    def get_type(channel):
        if channel.is_service:
            return 'service'
        elif channel.is_inbound:
            return 'inbound'
        elif channel.is_dispatchable:
            return 'dispatch'
        else:
            return 'outbound'

    def adapt_result(channel):

        langs = []
        if isinstance(channel, MultilanguageChannelMixin):
            unprocessed_langs = set(channel.langs)|set(channel.post_langs)
            for lang in unprocessed_langs:
                if lang not in LANG_MAP:
                    warning = "Invalid language %s was configured on channel %s from account %s. Ignoring invalid language." % (
                        lang, channel.title, channel.account.name
                    )
                    LOGGER.warning(warning)
                else:
                    langs.append({'code': lang, 'title': LANG_MAP.get(lang), 'is_target': lang in channel.langs})

        result = dict(
            id          = str(channel.id),
            parent_id   = str(channel.parent_channel) if channel.parent_channel else None,
            title       = channel.title,
            type        = get_type(channel),
            is_compound = channel.is_compound,
            platform    = channel.platform,
            langs       = langs)

        if channel.is_dispatchable:
            result.update(dict(
                is_dispatchable = channel.is_dispatchable,
                user_in_review_team = channel.is_dispatchable and channel.review_outbound and (
                        user.is_superuser or user in channel.get_review_team().members)
            ))
        return result


    try:
        types, serviced_only, use_parent_titles = get_parameters()

        all_channels  = filtered_channels(Channel.objects.find_by_user(user))
        serv_channels = [ch for ch in all_channels if ch.is_service]

        get_title_pairs = lambda ch: zip((ch.id, ch.inbound, ch.outbound), repeat(ch.title))
        parent_titles   = dict(flatten(map(get_title_pairs, serv_channels)))  # {<ch_id>: <parent_title>}

        if types == 'all':
            results = all_channels
        else:
            results = [ch for ch in all_channels if get_type(ch) in types]

        if serviced_only:
            results = [ch for ch in results if ch.id in parent_titles]

        if use_parent_titles:
            # overwrite channel title with a title of the parent service channel where applicable
            for ch in results:
                title = parent_titles.get(ch.id)
                if title:
                    ch.title = title

        sorted_results = sorted(results, key=lambda ch: ch.title)

        return jsonify(ok=True, list=map(adapt_result, sorted_results))

    except Exception, exc:
        app.logger.error('error on /channels_by_type/json', exc_info=True)
        return jsonify(ok=False, error=str(exc))


@app.route('/get_outbound_channel/<channel_id>', methods=['GET'])
@login_required()
def get_outbound_channel(user, channel_id):
    try:
        service_channel = Channel.objects.get_by_user(user, channel_id)
        try:
            channel = service_channel.get_outbound_channel(user)
        except FacebookConfigurationException:
            # This is raised when we have multiple account channels
            # and none of them attached to the current service channel.
            # This is normal situation and we should not propagate the error.
            channel = None
        except TwitterConfigurationException as e:
            return jsonify(ok=False, error=unicode(e))
        channel_data = None
        if channel:
            channel_data = channel.to_dict()
            channel_data['is_authenticated'] = channel.is_authenticated
        return jsonify(ok=True, channel=channel_data)
    except Channel.DoesNotExist:
        raise exc.ResourceDoesNotExist("No channel with id='%s' exists in the system." % channel_id)


@app.route('/account_channels/<channel_id>', methods=['GET', 'POST'])
@login_required
def get_account_channels(user, channel_id):
    def dispatch_channel_to_ui(channel):
        if isinstance(channel, EnterpriseTwitterChannel):
            channel_user_name = channel.twitter_handle
        elif isinstance(channel, EnterpriseFacebookChannel):
            channel_user_name = channel.facebook_screen_name
        else:
            raise ValueError(u"Unexpected dispatch channel %s" % channel)

        # service_channel = channel.get_service_channel(lookup_by_page_ids=False)
        attached_service_channels = channel.get_attached_service_channels()
        channel_data = channel.to_dict()
        channel_data['is_authenticated'] = channel.is_authenticated
        channel_data['attached_service_channels'] = [{
            'id': str(service_channel.id), 'title': service_channel.title}
            for service_channel in attached_service_channels
            ]
        not_auth = not channel.is_authenticated and " (not authenticated)" or ""

        attached_to = ""
        if attached_service_channels:
            if len(attached_service_channels) > 1:
                attached_to = u" attached to %s channels" % (len(attached_service_channels))
            else:
                attached_to = u" attached to %s" % attached_service_channels[0].title
        channel_user_name = channel_user_name and u" (%s)" % channel_user_name or ""

        return {'key': str(channel.id),
                'title': u"%s%s%s%s" % (channel.title, not_auth, channel_user_name, attached_to),
                'data': channel_data}

    channel = Channel.objects.get_by_user(user, channel_id)
    if not channel.is_service:
        return jsonify(ok=False, error="Service channel expected")
    candidates = channel.list_dispatch_candidates(
        user,
        only_not_attached=parse_bool(request.values.get('only_not_attached', False)))
    return jsonify(ok=True, data=map(dispatch_channel_to_ui, candidates))
