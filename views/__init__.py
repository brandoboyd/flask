import json

import operator
from flask import render_template, jsonify, request
from flask import redirect as flask_redirect

from solariat_bottle.utils.request import _get_request_data
from ..app import app
from solariat.utils.lang.support import get_lang_code, \
    get_all_detected_langs, lang_to_ui
from ..utils.decorators import login_required
from ..db.channel.base import Channel, ServiceChannel
from ..db.account import AccountEvent


# register routes - flake8 warnings should be ignored
import account          # NOQA
import signup           # NOQA
import gse_signup       # NOQA
import acl              # NOQA
import api_keys         # NOQA
import channels         # NOQA
import configure        # NOQA
import contact_labels   # NOQA
import contacts         # NOQA
import conversation     # NOQA
import dashboard        # NOQA
import dashboards       # NOQA
import funnel           # NOQA
import gallery          # NOQA
import error_handlers   # NOQA
import events           # NOQA
import facebook_extra   # NOQA
import journeys         # NOQA
import facets           # NOQA
import group            # NOQA
import jobs             # NOQA
import listen           # NOQA
import insights_analysis
import mailform         # NOQA
import messages         # NOQA
import message_queue    # NOQA
import multi_channel_tags #NOQA
import oauth            # NOQA
import playground       # NOQA
import profile          # NOQA
import redirect         # NOQA
import smart_tags       # NOQA
import test             # NOQA
import tracking         # NOQA
import trials           # NOQA
import unsubscribe      # NOQA
import work_time
import predictors
import dataset
import dynamic_profiles
import dynamic_channel
import dynamic_event
import agent_matching.agents
import agent_matching.customers
from journey import journey_type  # NOQA
from journey import journey_tag  # NOQA
from login import login # NOQA

# to disable pyflakes warnings
(account, signup, gse_signup, acl, api_keys, channels, configure, contact_labels,
 contacts, conversation, dashboard, error_handlers, events,
 facebook_extra, facets, group, listen, mailform,
 messages, oauth, playground, profile, redirect, smart_tags,
 test, tracking, trials, login, work_time)


@app.route('/')
@login_required()
def console_home(user):
    return flask_redirect(user.landing_page)

@app.route('/analytics')
@login_required()
def analytics_shortcut(user):
    return flask_redirect('/inbound')

@app.route('/<any(dashboard, agent-dashboard, jobs, inbound, outbound, engage, inbox, configure, messages, reports, predictors, contacts, conversations, trials, users/*/password):page>')
@login_required()
def console_handler(user, page):
    from .account import _json_account

    if page in ('inbound', 'outbound') :
        top_level    = 'analytics'
        channel_type = page
        template = 'listen'
    else :
        top_level    = page
        channel_type = 'inbound'
        template = page
    template_context = dict(top_level = top_level,
                            section = page,
                            user = user,
                            account = json.dumps(_json_account(user.account, user)),
                            c_type = channel_type
                            )
    return render_template("/%s.html" % template, **template_context)


@app.route('/partials/<section>/<path:page>')
@login_required()
def partials_section_handler(user, section, page):
    return render_template("/partials/%s/%s.html" % (section, page),
        section = section,
        user = user
    )


def get_twitter_supported_languages():
    """GET https://api.twitter.com/1.1/help/languages.json"""
    from solariat_bottle.utils.tweet import TwitterApiWrapper

    api = TwitterApiWrapper.init_with_channel(None)
    result = api.supported_languages()
    import logging
    logging.info(u"GET https://api.twitter.com/1.1/help/languages.json\n%s" % result)
    return result


@app.route('/languages/all/json', methods=['GET'])
@login_required()
def get_all_languages(user):
    request_data = _get_request_data()
    language_set = request_data.get('languageSet', 'all')
    force_fetch = request_data.get('forceFetch', False)

    if language_set == 'twitter':
        twitter_langs_key = '/languages/all/json?languageSet=twitter'
        from solariat_bottle.utils.cache import MongoDBCache

        cache = MongoDBCache()
        langs = cache.get(twitter_langs_key)
        if langs is None or force_fetch:
            langs = get_twitter_supported_languages()
            langs = sorted(map(lang_to_ui, set([get_lang_code(lang['code']) for lang in langs])),
                           key=operator.itemgetter('title'))
            one_week = 60 * 60 * 24 * 7
            cache.set(twitter_langs_key, langs, timeout=one_week)
        return jsonify(ok=True, list=langs)
    else:
        # list all currently supported langs
        languages = get_all_detected_langs()
        return jsonify(ok=True, list=languages)


@app.route('/tracking/languages/json', methods=['GET', 'POST', 'DELETE'])
@login_required()
def tracking_channel_languages(user):
    '''
    Handler for addition and deletion of languages for a tracking channel.
    '''
    if request.json is not None:
        data = request.json
    else:
        data = request.args

    if 'channel_id' not in data:
        return jsonify(ok=False, error='channel_id should be provided')

    try:
        channel = Channel.objects.get_by_user(user, data['channel_id'])
    except Channel.DoesNotExist:
        return jsonify(ok=False,
                       error='Channel %s does not exist' % data['channel_id'])
    old_data = {"languages": channel.langs}

    if request.method == 'GET':
        from solariat.utils.lang.support import lang_to_ui

        return jsonify(ok=True, item=map(lang_to_ui, channel.langs))

    if request.method == 'POST':
        if 'language' not in data:
            return jsonify(ok=False, error='language should be provided')
        else:
            if isinstance(channel, ServiceChannel):
                channel.set_allowed_langs([get_lang_code(data['language'])])
                new_data = {"languages": channel.langs}
                AccountEvent.create_by_user(user=user,
                                            change='Languages modifications',
                                            old_data=old_data,
                                            new_data=new_data)
                return jsonify(ok=True)
            else:
                return jsonify(ok=False, error="Incorrect channel type")

    if request.method == 'DELETE':
        if 'language' not in data:
                return jsonify(ok=False, error='language should be provided')
        else:
            if isinstance(channel, ServiceChannel):
                channel.remove_langs([get_lang_code(data['language'])])
                new_data = channel.langs
                AccountEvent.create_by_user(user=user,
                                            change='Languages modifications',
                                            old_data={'langs': old_data},
                                            new_data={'langs': new_data})
                return jsonify(ok=True)
            else:
                return jsonify(ok=False, error="Incorrect channel type")

    return jsonify(ok=True)
