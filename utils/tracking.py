from functools import partial
from itertools import chain
from collections import defaultdict
import re

from solariat.utils.hidden_proxy import unwrap_hidden
from solariat.utils.iterfu import partition
from solariat.utils.lang.support import get_supported_languages, FULL_SUPPORT, \
    LANG_CODES
from solariat_bottle.settings import LOGGER


def get_content(post):
    if hasattr(post, 'content'):
        content = post.content
    elif isinstance(post, dict) and 'content' in post:
        content = post['content']
    else:
        content = post
    return unwrap_hidden(content)


class TrackingNLP:
    '''
    Used when handling inbound post creation. Tokenizes posts to extract
    search terms which are then used for post filter querues.

    @see get_tracked_channels
    '''
    import nltk
    import re
    keywords_tokenizer = nltk.tokenize.RegexpTokenizer(r'[\w\']+')
    hashtags_tokenizer = nltk.tokenize.RegexpTokenizer(r'[#\w]+')
    mentions_tokenizer = nltk.tokenize.RegexpTokenizer(r'[@\w]+')
    re_hashtag = re.compile(r'^#\w+$')
    re_mention = re.compile(r'^@\w+$')

    @staticmethod
    def normalize_kwd(kwd):
        return kwd.lower()

    @classmethod
    def extract_hashtags(cls, post):
        tokens = cls.hashtags_tokenizer.tokenize(get_content(post))
        return [ cls.normalize_kwd(h) for h in tokens if cls.re_hashtag.match(h) ]

    @classmethod
    def extract_mentions(cls, post):
        tokens = cls.mentions_tokenizer.tokenize(get_content(post))
        return [ cls.normalize_kwd(m) for m in tokens if cls.re_mention.match(m) ]

    @classmethod
    def extract_keywords(cls, post):
        import nltk
        keywords = cls.keywords_tokenizer.tokenize(get_content(post))
        keywords = [ cls.normalize_kwd(k) for k in keywords ]
        keywords.extend([ ' '.join(k) for k in
                          nltk.ngrams(keywords, 2) +
                          nltk.ngrams(keywords, 3) +
                          nltk.ngrams(keywords, 4) ])
        return keywords

    @classmethod
    def extract_all(cls, post):
        return list(chain(
            cls.extract_keywords(post),
            cls.extract_hashtags(post),
            cls.extract_mentions(post),
        ))

    @classmethod
    def extract_simplified(cls, content):
        return re.findall('[\w#@]+', get_content(content))


def filter_ids(keys):
    " check that all keys type of int "
    _keys = []
    for key in keys:
        try:
            _keys.append(str(int(key)))
        except ValueError:
            LOGGER.warn('incorrect id: %s', key)
    return _keys


def split_keywords_and_mentions(keys):

    keywords = []
    mentions = []

    for k in keys:
        if k.startswith('@'):
            mentions.append(k.lstrip('@'))
        else:
            keywords.append(k)

    return (keywords, mentions)


def freeze(iterable):
    return tuple(sorted(iterable))


def analyze_channel_keywords(channel_key_map, keyword_skipword_pairs):
    """Analyzes differences between per channel keywords and generalized keywords"""

    keyword_skipword_map = dict(keyword_skipword_pairs)
    details = defaultdict(list)

    def _test(channel_skips, general_skips):
        if set(channel_skips) < set(general_skips):
            diff = set(general_skips) - set(channel_skips)
            details[channel].append(('error', u'skip list for channel is less than combined skip list, diff: %s' % diff))
        else:
            diff = set(channel_skips) - set(general_skips)
            if diff:
                details[channel].append(('info', u'suppressed skipwords: %s' % diff))

    def _find_general_skips(keyword):
        for kwds, skips in keyword_skipword_map.iteritems():
            if keyword in kwds:
                return skips
        return None

    for (channel, kwds) in channel_key_map.items():
        if not kwds['KEYWORD']:
            details[channel].append(('warn', 'found only skipwords'))
            continue
        k, s = freeze(kwds['KEYWORD']), freeze(kwds['SKIPWORD'])
        if k in keyword_skipword_map and keyword_skipword_map[k] == s:
            details[channel].append(('info', 'channel has no common keywords with other channels'))
        elif k in keyword_skipword_map:
            _test(s, keyword_skipword_map[k])
        else:
            for kwd in k:
                skips = _find_general_skips(kwd)
                if skips is None:
                    details[channel].append(('error', u'missing: %s' % kwd))
                else:
                    _test(s, skips)
    return details


def sanity_check(CHANNEL_KEY_MAP, keywords_skipwords_pairs):
    try:
        details = analyze_channel_keywords(CHANNEL_KEY_MAP, keywords_skipwords_pairs)
    except:
        LOGGER.exception(u'analyze_channel_keywords failed with params:\n%s\n%s' % (
            CHANNEL_KEY_MAP, keywords_skipwords_pairs))
    else:
        for channel, logs in details.iteritems():
            for (log_level, msg) in logs:
                message = u"%s[%s]: %s" % (channel.id, channel.title, msg)
                getattr(LOGGER, log_level, 'info')(message)


def minimize(keyword_skipwords_iter):
    keyword_skipwords_map = {}
    for kwd, skipwords in keyword_skipwords_iter:
        assert isinstance(skipwords, set)
        if kwd not in keyword_skipwords_map:
            keyword_skipwords_map[kwd] = skipwords.copy()
        else:
            keyword_skipwords_map[kwd] &= skipwords

    group_by_skipwords = defaultdict(list)
    for kwd, skipwords in keyword_skipwords_map.items():
        group_by_skipwords[freeze(skipwords)].append(kwd)
    return tuple((freeze(keywords), skipwords) for skipwords, keywords in group_by_skipwords.items())


def get_channel_post_filters_map(channels=None):
    from solariat_bottle.db.tracking import PostFilterEntry

    channel_key_map = defaultdict(lambda: {'KEYWORD': set(),
                                           'SKIPWORD': set(),
                                           'USER_NAME': set(),
                                           'USER_ID': set()})

    q = {}
    if channels:
        q['channels__in'] = channels
    post_filter_entries = PostFilterEntry.objects(**q)
    for pfe in post_filter_entries:

        pfe.entry = pfe.entry.encode('utf-8')

        _type = pfe.filter_type

        if _type in ('KEYWORD', 'SKIPWORD', 'USER_NAME', 'USER_ID'):
            chs = pfe.channels
            if channels:
                chs = [ch for ch in channels if ch in pfe.channels]
            for channel in chs:
                channel_key_map[channel][_type].add(pfe.entry)

    return channel_key_map


def flatten_channel_post_filters_map(channels_map, extract_fields=('USER_NAME', 'USER_ID')):
    result = {field: set([]) for field in extract_fields}
    for channel_id, values in channels_map.viewitems():
        for field in extract_fields:
            if field in values:
                result[field] |= set(map(clean_username, values[field]))
    return tuple(result[field] for field in extract_fields)


def build_uname_to_id_map(channel_key_map):
    user_name_to_id = {}

    usernames = set()
    for channel, key_map in channel_key_map.iteritems():
        if 'USER_NAME' in key_map:
            usernames = usernames.union(key_map['USER_NAME'])

    from solariat_bottle.db.user_profiles.social_profile import TwitterProfile

    expected_usernames = set(map(clean_username, usernames))
    missing = expected_usernames.copy()
    profiles = TwitterProfile.objects(user_name__in=expected_usernames)

    for profile in profiles:
        uname = profile.user_name
        missing.discard(uname)
        user_name_to_id[uname] = profile.user_id

    return user_name_to_id, missing


def preprocess_keyword(kwd, strip_special_chars=False):
    """Cleanup keywords for passing to twitter stream api"""
    if strip_special_chars:
        if kwd.startswith('@'):
            kwd = kwd.lstrip('@')
        if kwd.startswith('#'):
            kwd = kwd.lstrip('#')
    kwd = kwd.lstrip('"').rstrip('"').lstrip("'").rstrip("'")
    # Each phrase must be between 1 and 60 bytes, inclusive.
    if len(kwd) > 60:
        return None
    return kwd

clean_username = partial(preprocess_keyword, strip_special_chars=True)


def combine_and_split(channel_key_map=None, max_track=400, max_follow=5000,
                      fetch_missing_profiles=True):
    user_name_to_id, missing_profiles = build_uname_to_id_map(channel_key_map)

    if missing_profiles and fetch_missing_profiles:
        LOGGER.info(u"Fetching missing profiles: %s" % missing_profiles)
        from solariat_bottle.utils.tweet import TwitterApiWrapper
        from solariat_bottle.utils.oauth import get_twitter_oauth_handler
        from solariat_bottle.db.user_profiles.user_profile import UserProfile
        from solariat_bottle.daemons.helpers import parse_user_profile
        try:
            api = TwitterApiWrapper.make_api(get_twitter_oauth_handler())
            for user in api.lookup_users(screen_names=missing_profiles, include_entities=True):
                UserProfile.objects.upsert('Twitter', profile_data=parse_user_profile(user))
                uname = user.screen_name.lower()
                user_name_to_id[uname] = str(user.id)
                missing_profiles.discard(uname)
        except:
            pass

    if missing_profiles:
        LOGGER.warn(u'Missing UserProfiles. '
                    u'User names won\'t be tracked: %s' % missing_profiles)

    # regroup by postfilter entry
    group_by_entry = defaultdict(lambda: {'accounts': set(),
                                          'channels': set()})
    for channel, key_map in channel_key_map.iteritems():
        for entry_type, entries in key_map.iteritems():
            if entry_type == 'SKIPWORD':
                continue

            for entry in entries:
                entry_key = None
                if entry_type == 'USER_NAME':
                    uid = user_name_to_id.get(preprocess_keyword(entry, strip_special_chars=True))
                    if not uid:
                        LOGGER.warn(u'user id not found for %s' % entry)
                        continue
                    entry_key = ('USER_ID', uid)
                if entry_type == 'USER_ID' or entry_type == 'KEYWORD':
                    updated_entry = preprocess_keyword(entry)
                    if not updated_entry:
                        LOGGER.warn('Skipped keyword %s' % entry)
                        continue
                    else:
                        entry_key = (entry_type, updated_entry)

                group_by_entry[entry_key]['channels'].add(channel)
                group_by_entry[entry_key]['accounts'].add(channel.account)

    def _minimize(group_by_entry):
        """if there is keyword without [@#] then remove same keywords with @#
        and merge channels"""
        result = defaultdict(lambda: {'accounts': set(),
                                      'channels': set()})
        for item, channels_and_accounts in group_by_entry.iteritems():
            filter_type, value = item
            if filter_type == 'KEYWORD':
                clean_value = value.lstrip('#').lstrip('@')
                key = (filter_type, clean_value)
                if key in group_by_entry:
                    result[key]['accounts'].update(channels_and_accounts['accounts'])
                    result[key]['channels'].update(channels_and_accounts['channels'])
                else:
                    result[item] = channels_and_accounts
            else:
                result[item] = channels_and_accounts
        return result

    def _iter_parts(group_by_entry):
        from itertools import izip_longest, ifilter

        def _filter(entry_type):
            return ifilter(lambda ((filter_type, _1), _2): filter_type == entry_type,
                           group_by_entry.iteritems())

        for keywords_data, user_ids_data in izip_longest(
            partition(_filter('KEYWORD'), max_track),
            partition(_filter('USER_ID'), max_follow),
            fillvalue=[]
        ):
            merged_channels = set()
            merged_accounts = set()
            keywords = []
            user_ids = []
            for item, accounts_and_channels in chain(keywords_data, user_ids_data):
                filter_type, value = item
                merged_channels.update(accounts_and_channels['channels'])
                merged_accounts.update(accounts_and_channels['accounts'])
                if filter_type == 'KEYWORD':
                    keywords.append(value)
                elif filter_type == 'USER_ID':
                    user_ids.append(value)

            yield keywords, user_ids, merged_accounts, merged_channels

    return list(_iter_parts(_minimize(group_by_entry)))


def get_csdl_data(channels=None):
    """Returns building parts of csdl query from PostFilterEntries:
    usernames, user ids, common keywords, keywords with skipwords
    """
    channel_key_map = get_channel_post_filters_map(channels)
    user_name_list, user_id_list = flatten_channel_post_filters_map(channel_key_map)

    keywords_skipwords_pairs = []
    if channel_key_map:
        def gen_keyword_skipwords():
            for (channel, kwds) in channel_key_map.items():
                for kwd in kwds['KEYWORD']:
                    yield kwd, kwds['SKIPWORD']

        keywords_skipwords_pairs = sorted(minimize(list(gen_keyword_skipwords())))
        sanity_check(channel_key_map, keywords_skipwords_pairs)

    return freeze(user_name_list), freeze(filter_ids(user_id_list)), keywords_skipwords_pairs


def get_languages(channels=None):
    UNDEFINED = 'und'

    if channels is None:
        return get_supported_languages(FULL_SUPPORT) + [UNDEFINED]
    else:
        from solariat_bottle.db.channel.base import Channel
        from solariat_bottle.utils.post import get_service_channel

        langs = {UNDEFINED}
        for ch in Channel.objects.ensure_channels(channels):
            if hasattr(ch, 'get_allowed_langs'):
                langs.update(set(ch.get_allowed_langs()))
            else:
                sc = get_service_channel(ch)
                if sc:
                    langs.update(set(sc.get_allowed_langs()))

        return sorted(langs)

def get_twitter_post_users(post):
    """Returns conversation parties from the DM or public tweet"""
    user_ids, user_screen_names, recipient_screen_names = [], [], []

    if 'twitter' not in post:
        # compatibility for tests not passing a fully formatted tweet to the get_tracked_channels
        if 'user_profile' in post and isinstance(post['user_profile'], dict):
            user_ids.append(post['user_profile']['user_id'])
            user_screen_names.append(post['user_profile']['user_name'])
        return user_ids, user_screen_names, recipient_screen_names

    tweet_json = post['twitter']
    is_direct_message = 'recipient' in tweet_json and 'sender' in tweet_json

    try:
        if is_direct_message:
            user_ids.append(tweet_json['sender']['id_str'])
            user_screen_names.append(tweet_json['sender']['screen_name'])
            recipient_screen_names.append(tweet_json['recipient']['screen_name'])
        else:
            # all mentions
            if 'entities' in tweet_json and 'user_mentions' in tweet_json['entities']:
                for user_data in tweet_json['entities']['user_mentions']:
                    recipient_screen_names.append(user_data['screen_name'])
            # sender
            if 'user' in tweet_json:
                user_ids.append(tweet_json['user']['id_str'])
                user_screen_names.append(tweet_json['user']['screen_name'])
            elif 'user_profile' in post:
                user_ids.append(post['user_profile']['user_id'])
                user_screen_names.append(post['user_profile']['user_name'])
            # recipient
            if 'in_reply_to_screen_name' in tweet_json and tweet_json['in_reply_to_screen_name']:
                recipient_screen_names.append(tweet_json['in_reply_to_screen_name'])
    except KeyError:
        LOGGER.warning("Malformed post data {}".format(post), exc_info=True)

    all_str = lambda iterable: all(isinstance(x, basestring) for x in iterable)
    assert all_str(user_ids), user_ids
    assert all_str(user_screen_names), user_screen_names
    assert all_str(recipient_screen_names), recipient_screen_names
    return user_ids, user_screen_names, recipient_screen_names


def lookup_tracked_channels(platform_name, post, keywords=None, logger=LOGGER):
    from solariat_bottle.db.channel.base import Channel
    from solariat_bottle.db.channel.twitter import get_sync_usernames_list, \
        KeywordTrackingChannel
    from solariat_bottle.db.tracking import PostFilterEntry, \
        PostFilterEntryPassive, PostFilterStream, get_filter_type_id
    from solariat_bottle.utils.post import get_language, is_retweet, \
        get_service_channel_memoized

    F = PostFilterEntry.F
    normalize = TrackingNLP.normalize_kwd

    post['lang'] = get_language(post)
    lang_code = post['lang'].lang

    if keywords is None:
        keywords = TrackingNLP.extract_all(post)

    def safe_channels(filter_channel_map):
        channel_id_filter_map = defaultdict(set)
        for filter_id, (filter_type, channel_refs) in filter_channel_map.iteritems():
            for ref in channel_refs:
                channel_id_filter_map[ref.id].add((filter_id, filter_type))

        expected_channel_ids = channel_id_filter_map.keys()
        channels = list(Channel.objects.coll.find(
            {Channel.F.id: {"$in": expected_channel_ids},
             Channel.F.status: {"$in": ['Active', 'Interim']}
             }))
        channels = map(Channel, channels)
        active_channel_ids = set(ch.id for ch in channels)
        missing_channels = set(expected_channel_ids) - active_channel_ids

        if missing_channels:
            from solariat.db.abstract import DBRef
            models = {ACTIVE: PostFilterEntry, PASSIVE: PostFilterEntryPassive}
            for channel_id in missing_channels:
                channel_ref = DBRef('Channel', channel_id)
                for filter_id, filter_type in channel_id_filter_map[channel_id]:
                    model = models[filter_type]
                    logger.warning("Channel pulled from %s(%s): %s" % (model.__name__, filter_id, channel_id))
                    model.objects.coll.update(
                        {"_id": filter_id},
                        {"$pull": {model.F('channels'): channel_ref}})
            PostFilterStream.refresh_stats()
            PostFilterEntry.objects.remove(channels=[])
        return channels

    filter_channel_refs_map = {}
    ACTIVE = 0
    PASSIVE = 1
    post_filter_query = {
        F.entry: {"$in": keywords},
        F.filter_type_id: get_filter_type_id('KEYWORD')
    }
    if lang_code in LANG_CODES:
        post_filter_query[F.lang] = lang_code

    for item in PostFilterEntry.objects.coll.find(
            post_filter_query,
            fields={F.channels: True}):
        filter_channel_refs_map[item['_id']] = (ACTIVE, item[F.channels])

    sender_user_ids, sender_user_screen_names, recipient_user_screen_names = get_twitter_post_users(post)
    user_screen_names = get_sync_usernames_list([name.lower() for name in set(sender_user_screen_names)])
    recipient_user_screen_names = get_sync_usernames_list([name.lower() for name in set(recipient_user_screen_names)])

    if recipient_user_screen_names:
        # lookup recipients among keywords
        for item in PostFilterEntry.objects.coll.find(
                {F.entry: {"$in": recipient_user_screen_names},
                 F.filter_type_id: get_filter_type_id('KEYWORD')},
                fields={F.channels: True}):
            filter_channel_refs_map[item['_id']] = (ACTIVE, item[F.channels])

    if user_screen_names:
        # lookup senders among tracked screen names
        for item in PostFilterEntry.objects.coll.find(
                {F.entry: {"$in": user_screen_names},
                 F.filter_type_id: get_filter_type_id('USER_NAME')},
                fields={F.channels: True}):
            filter_channel_refs_map[item['_id']] = (ACTIVE, item[F.channels])

    if sender_user_ids:
        # lookup senders among tracked user ids
        for item in PostFilterEntry.objects.coll.find(
                {F.entry: {"$in": sender_user_ids},
                 F.filter_type_id: get_filter_type_id('USER_ID')}):
            filter_channel_refs_map[item['_id']] = (ACTIVE, item[F.channels])

        for item in PostFilterEntryPassive.objects.coll.find(
                {F.entry: {"$in": sender_user_ids}}):
            filter_channel_refs_map[item['_id']] = (PASSIVE, item[F.channels])

    channels = safe_channels(filter_channel_refs_map)
    # for channel in list(channels):
    #     if isinstance(channel, KeywordTrackingChannel) and \
    #             set(map(normalize, channel.skipwords)).intersection(set(
    #                     LingualToken.extend_langifyed(keywords, lang=lang_code))):
    #         channels.remove(channel)

    if platform_name == 'Twitter' and is_retweet(post):
        service_channel_map = {c: get_service_channel_memoized(c) for c in channels}
        for channel, sc in service_channel_map.iteritems():
            if sc:
                try:
                    sc.reload()
                except Channel.DoesNotExist:
                    channels.remove(channel)
                    continue

            if sc and sc.skip_retweets is True:
                logger.debug('skipping retweet "%s" for channel %s' % (post['content'], channel))
                channels.remove(channel)

    # For direct messages, also make sure that all the channels actually have access to it
    if post.pop('direct_message', False):
        logger.debug('extra-filtering channels for a direct message')
        sender_handle = post.pop('sender_handle', False)
        recipient_handle = post.pop('recipient_handle', False)
        if not (sender_handle and recipient_handle):
            # We don't have a handle so we don't know who this is adressed to.
            # Just return empty list.
            logger.warning("Need a sender and reciever handle in order to process direct messages, but got none.")
            return []
        channels = [c for c in channels if (get_service_channel_memoized(c) and
                                            c.has_private_access(sender_handle, recipient_handle))]

    tracked_channels = [c for c in channels if c.platform == platform_name]
    # if app_mode == 'test':
    #     try:
    #         LOGGER.debug(u'channels for post %s\n%s' % (u'%s %s' % (post['content'], post['user_profile']['user_name']),
    #                                                     '\n'.join(u"%s[%s]" % (ch.title, ch) for ch in tracked_channels)))
    #     except:
    #         pass
    return tracked_channels
