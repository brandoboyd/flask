# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

" Utilities shared across views "

from re          import compile as re_compile
from collections import OrderedDict
from functools import wraps

from bson import ObjectId
from flask import abort
from solariat_nlp.sa_labels import SATYPE_ID_TO_NAME_MAP
from solariat_bottle.settings import LOGGER, AppException
from solariat.utils.helpers  import trim_to_fixed_point
from solariat.utils.timeslot import datetime_to_timeslot, datetime_to_timestamp_ms
from ..db.post.base    import Post, UntrackedPost
from ..db.user_profiles.nps_profile    import NPSProfile
from ..db.post.nps    import NPSOutcome
from ..db.channel.base import Channel
from ..db.user_profiles.user_profile import UserProfile
from ..db.speech_act import SpeechActMap


date_re     = re_compile(r'\d{2}/\d{2}/\d{4}')
datetime_re = re_compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')


class Param(object):
    """ Represents a single input parameter of a view/controller.
        May hold necessary information to check the validness of types and values.
        Also stores a default value or the REQUIRED constant.

        Although it can be used on it's own, the recommended usage is via
        the Parameters class (see below).

        Usage examples
        --------------

        NoneType  = type(None)
        is_dict   = lambda v: isinstance(v, dict)
        all_dicts = lambda l: all(map(is_dict, l or []))

        supported_params = (
            #     name           valid_types      valid_values            value
            #     -------------  ---------------  ----------------------  --------------
            Param('channel_id',  basestring,      Param.UNCHECKED,        Param.REQUIRED),
            Param('level',       basestring,      ['hour','day','month'], 'hour'),
            Param('topics',      (list,NoneType), all_dicts,              []),
        )
    """
    REQUIRED  = object()
    UNCHECKED = object()

    def __init__(self, name, valid_types, valid_values, value):
        self.name         = name
        self.valid_types  = valid_types
        self.valid_values = valid_values
        self.value        = value

    @property
    def is_valid(param):
        if param.value is param.REQUIRED:
            return False
        if param.valid_types is not param.UNCHECKED and not isinstance(param.value, param.valid_types):
            return False
        if param.valid_values is not param.UNCHECKED:
            if callable(param.valid_values):
                if not param.valid_values(param.value):
                    return False
            else:
                if isinstance(param.value, list) and isinstance(param.valid_values, list):
                    for val in param.value:
                        if val not in param.valid_values:
                            return False
                    return True
                if param.value not in param.valid_values:
                    return False
        return True

class Parameters(object):
    """ Represents a set of supported input parameters of a view/controller.
        Each parameter is represented as an instance of the Param class (see above).

        Supports iteration protocol and has a __getitem__ defined to access individual
        parameters by name.

        Usage example
        -------------

        NoneType  = type(None)
        is_dict   = lambda v: isinstance(v, dict)
        all_dicts = lambda l: all(map(is_dict, l or []))

        params = Parameters(
            #     name           valid_types      valid_values            value
            #     -------------  ---------------  ----------------------  --------------
            Param('channel_id',  basestring,      Param.UNCHECKED,        Param.REQUIRED),
            Param('level',       basestring,      ['hour','day','month'], 'hour'),
            Param('topics',      (list,NoneType), all_dicts,              []),
        )
        params.update(request.json)  # may raise an exception
        params.check()               # may raise an exception
    """
    def __init__(self, *params):
        self.params = OrderedDict((p.name, p) for p in params)

    def __iter__(self):
        return self.params.itervalues()

    def __getitem__(self, name):
        return self.params[name]

    def update(self, data, check_unsupported=True):
        """ Updates parameter values from the passed data (<dict> or a key-value iterable).
            May raise an exception if check_unsupported is True.
        """
        get_pairs = getattr(data,'iteritems',None) or getattr(data,'items',None) or (lambda:data)
        params    = self.params

        for name, value in get_pairs():
            param = params.get(name)
            if param:
                param.value = value
            elif check_unsupported:
                raise RuntimeError('unsupported parameter: %s=%r' % (name, value))

    def check(self):
        """ Checks if all values are valid. Raises an exception if anything's wrong.
        """
        for param in self:
            if param.value is Param.REQUIRED:
                raise ValueError('required parameter is missing: %s' % param.name)
            if not param.is_valid:
                raise ValueError('parameter value is invalid: %s=%r' % (param.name, param.value))

        return True

    def as_dict(self):
        return dict((p.name, p.value) for p in self)


def build_user_profile_cache(posts):
    """ Returns a dict {<user_profile_id> : <user_profile_dict>} for a given
        set of posts. Also one for the object itself.
    """
    if posts:
        _profile_klass = posts[0].PROFILE_CLASS
    else:
        return {'user_profile_objects': {}}

    post = posts[0]
    # in that case we don't have direct link to platform profile (NPSProfile), so we gonna use CustomerProfile to access NPSProfile model
    # above statement is at least not always true, VOC Post._user_profile is actually refering to NPSProfile
    if post.platform == 'VOC':
        customer_profile_ids = [p.actor_id for p in posts]
        # profiles    = [nps_profile for nps_profile in _profile_klass.objects(_customer_profile__in=customer_profile_ids)]
        profiles = []
    else:
        profile_ids = [p.user_profile_id for p in posts]
        # profiles    = [up for up in _profile_klass.objects(id__in=profile_ids) ]
        profiles = [_profile_klass(up) for up in _profile_klass.objects.coll.find({'_id': {'$in': profile_ids}})]

    cache       = dict((up.id, up.to_dict()) for up in profiles)
    cache[None] = UserProfile().to_dict()
    if post.platform == 'VOC':
        # cache['user_profile_objects'] = dict((up._customer_profile.id, up) for up in profiles)
        # since currently generated VOC data is doing lookup against post._user_profile which is actually NPSProfile ObjectId
        cache['user_profile_objects'] = {}
        cache['user_profile_objects'].update(dict((up.id, up) for up in profiles))
    else:
        cache['user_profile_objects'] = dict((up.id, up) for up in profiles)

    return cache


def matchable_to_dict(matchable, relevance):
    return  dict(
        id              = str(matchable.id),
        landing_url     = matchable.get_url(),
        creative        = matchable.creative,
        topics          = matchable.intention_topics,
        is_dispatchable = matchable.is_dispatchable,
        stats           = {
            "ctr"         : matchable.ctr,
            "impressions" : matchable.accepted_count,
            "relevance"   : trim_to_fixed_point(relevance, 2)
        }
    )

def post_to_dict(post, user, channel=None, profile_cache=None, tags=None):
    """
    Converts a <Post> instance into a dict of defined structure.
    This function will get all the extra params and then call the
    fast implementation
    """

    if channel is None:
        channel = post.channel

    profile_cache = profile_cache or {}
    user_profile = post.get_user_profile()
    outbound_channel = channel.get_outbound_channel(user)

    service_channel = None
    if channel.parent_channel is not None:
        service_channel = Channel.objects.get(id=channel.parent_channel)

    user_profile_id = post.user_profile_id
    profile_cache[user_profile_id] = user_profile.to_dict()

    return post_to_dict_fast(post, user,
                             channel, service_channel, outbound_channel,
                             user_profile, profile_cache, tags=tags,
                             has_conversation=post.has_conversation(service_channel),
                             conversation_external_id=None)


def _from_speech_acts(post, user):
    intentions  = []
    topics      = []

    for sa_idx, sa in enumerate(post.speech_acts):
        intention_type_id = str(sa["intention_type_id"])
        intention_type    = SATYPE_ID_TO_NAME_MAP[intention_type_id]
        intentions.append({
            "content"       : sa["content"],
            "type"          : intention_type,
            "score"         : "%2.2f" % sa["intention_type_conf"],
            "speech_act_id" : sa_idx,
            "vote"          : post.get_vote_for(user, sa_idx, intention=intention_type)
        })
        for topic_content in sa["intention_topics"]:
            topics.append({
                "content"       : topic_content,
                "intention"     : intention_type,
                "score"         : "%2.2f" % sa["intention_topic_conf"],
                "speech_act_id" : sa_idx,
                "vote"          : post.get_vote_for(user, sa_idx, topic=topic_content)
            })
    return intentions, topics

def post_assignment_to_status(post, channel):
    value = SpeechActMap.STATUS_NAME_MAP[SpeechActMap.STATUS_MAP[
        post.get_assignment(channel) or 'assigned']]
    return value

def find_smart_tags(post, tags, user):
    # Figure out the smart tags
    smart_tags = []
    if tags != None:
        for k, v in post.tag_assignments.items():
            # Check these
            if k in tags:
                if v in SpeechActMap.STATUS_MAP:
                    if SpeechActMap.STATUS_MAP[v] not in [
                        SpeechActMap.POTENTIAL, SpeechActMap.REJECTED]:
                        tag = tags[k]
                        smart_tags.append(dict(id=k,
                                               title=tag.title,
                                               status=tag.status,
                                               assignment=post.tag_assignments[k],
                                               perm='w' if tag.can_edit(user) else 'w'))
                else:
                    LOGGER.error("%s is not a valid speech act map key", v)
    return smart_tags


def post_to_dict_fast(post, user,
                      channel, service_channel, outbound_channel,
                      user_profile, profile_cache, tags,
                      has_conversation,
                      conversation_external_id):
    """ Converts a <Post> instance into a dict of defined structure.

        profile_cache - is an optional optimization, a caller may pass
                        a dict {<user_profile_id> : <user_profile_dict>}

        parent_channel- used to pull out smat tags per post, efficiently
    """

    #from datetime import datetime
    #start_ts = datetime.now()

    smart_tags = find_smart_tags(post, tags, user)
    #SKIP  "Y1", datetime.now() - start_ts
    intentions, topics = _from_speech_acts(post, user)

    #SKIP  "Y2", datetime.now() - start_ts
    serv_history = out_history = False
    if outbound_channel:
        out_history = user_profile.has_history(outbound_channel)
    if service_channel:
        serv_history = user_profile.has_history(service_channel)
    has_history = out_history or serv_history

    # NOTE: This is expensive and should be optimized
    res = {
        "id_str"              : str(post.id),
        "created_at"          : datetime_to_timestamp_ms(post.created_at),
        "text"                : post.plaintext_content,
        "lang"                : post.language,
        "intentions"          : intentions,
        "topics"              : topics,
        # this if below is for NPS post case (Alex G.)
        "user"                : profile_cache[post.user_profile_id] if post.user_profile_id else profile_cache['user_profile_objects'][post.actor_id].to_dict(),
        "url"                 : post.url,
        "url_href_text"       : post.view_url_link,
        #"channel_assignments" : post.channel_assignments,
        "filter_status"       : channel and post_assignment_to_status(post, channel) or None,
        "on_outbound_chan"    : not channel or not (channel.is_service or channel.is_inbound),
        "channel_id"          : channel and str(channel.id) or None,
        "channel_platform"    : channel and str(channel.platform) or None,
        "smart_tags"          : smart_tags,
        "has_history"         : has_history,
        "has_conversation"    : has_conversation,
        "conversation_external_id": conversation_external_id,
        #"reply_to"            : post.reply_to,
        "stats"               : {
            "intention"     : {
                "type"  : post.intention_name,
                "score" : "%.2f" % post.intention_confidence,
                "vote"  : post.get_vote(user)
            },
            #"actionability" : post.actionability,
            #"influence"     : 0,
            #"receptivity"   : 0
        },
    }

    res.update(post.platform_specific_data(outbound_channel))

    #SKIP  "Y4", datetime.now() - start_ts
    return res

def response_to_dict(resp, user, with_post=False):
    from solariat_bottle.db import trim_to_fixed_point
    ctr = resp.matchable.accepted_count and trim_to_fixed_point(
        resp.matchable.clicked_count / float(resp.matchable.accepted_count),
        2) or 0

    resp_dict = {
        "id"               : str(resp.id),
        "starred"          : user.id in resp.starred,
        "rejected"         : resp.status == 'rejected',
        "forwarded"        : False,
        "channel_title"    : resp._channel_title,
        "channel_id"       : str(resp.channel.id),
        "platform"         : resp.channel.platform,
        #"has_history"     : has_history,
        "has_more_matches" : resp.has_more_matches,

        "match"            : dict(
            post_id_str = resp.post.id,
            matchable   = dict(
                id              = str(resp.matchable.id),
                landing_url     = resp.matchable.get_url(),
                creative        = resp.matchable.creative,
                topics          = resp.matchable.intention_topics,
                types           = resp.matchable.intention_types,
                is_dispatchable = resp.matchable.is_dispatchable,
                best_match      = True,
                stats           = {
                    "ctr"         : ctr,
                    "impressions" : resp.matchable.accepted_count,
                    "relevance"   : resp.relevance
                }
            )
        ),
    }

    if with_post:
        resp_dict["post"] = post_to_dict(resp.post, user)

    return resp_dict

def get_posts(
    channel,
    from_dt,
    to_dt,
    terms,
    intentions,
    thresholds,
    sort_by  = 'date',
    statuses = None,
    limit    = 100,
    offset   = 0,
):
    # Note: we only use the 'hour' level when storing speech-act-maps

    assert intentions, repr(intentions)
    assert 'intention' in thresholds, repr(thresholds)
    assert sort_by in ['date', 'intention', 'receptivity', 'influence'], \
        "%r is not a valid sort key" % sort_by

    if sort_by == 'intention':
        sam_sort = {'intention_type_conf': -1}
    else:
        sam_sort = {'_created': -1}

    statuses = statuses or ['assigned']

    posts, are_more_posts_available = Post.objects.by_time_point(
        channel,
        terms,
        time_slot = datetime_to_timeslot(from_dt, 'month'),
        status    = statuses,
        intention = intentions,
        min_conf  = thresholds['intention']
        ).sort(**sam_sort).skip(offset).limit(limit)

    return posts


def get_paging_params(data, default_offset=0, default_limit=20):
    try:
        offset = int(data.get('offset', default_offset))
        limit = int(data.get('limit', default_limit))
        assert (0 <= offset)
        assert (0 < limit < 1000)
    except:
        offset = default_offset
        limit = default_limit
    return {'offset': offset, 'limit': limit}

def pluck_ids(query):
    from operator import itemgetter
    return map(itemgetter('id'), query.fields('id'))


def render_posts(user, posts, channel, conversation=None, post_to_dict_fn=post_to_dict_fast):
    ''' Utility to opitmally fetch posts in a form for rendering.'''
    from ..utils.post import get_service_channel
    service_channel = get_service_channel(channel)
    outbound_channel = channel.get_outbound_channel(user)
    if service_channel and outbound_channel is None:
        outbound_channel = service_channel.get_outbound_channel(user)

    # Batch Fecth Profile Data
    profile_cache = build_user_profile_cache(posts)
    profile_object_cache = profile_cache['user_profile_objects']

    # Batch Fetch Tags
    if channel.is_smart_tag:
        parent_channel = Channel.objects.get_by_user(user=user, id=channel.parent_channel)
    else:
        parent_channel = channel

    tags = dict( [ (str(tag.id), tag)
                   for tag in Channel.objects.find_by_user(user=user, account=channel.account, parent_channel=parent_channel.id) ] )

    # Handle conversations
    has_conversation_cache = {}
    external_id_cache  = {}
    all_conversations = []
    if service_channel:
        if conversation:
            all_conversations = [ conversation ]
        else:
            if posts:
                from ..db.conversation import Conversation
                all_conversations = Conversation.objects.lookup_by_posts(service_channel, posts, include_closed=True)
            else:
                all_conversations = []

    for c in all_conversations:
        if len(c.posts) > 1:
            for p_id in c.posts:
                external_id_cache[p_id] = c.external_id
                has_conversation_cache[p_id] = True

    # assert False, (p.data[Post._user_profile._db_field], p.data[Post.actor_id._db_field], profile_object_cache)
    post_dicts = [post_to_dict_fn(p, user,
                                channel=channel,
                                service_channel=service_channel,
                                outbound_channel=outbound_channel,
                                user_profile=profile_object_cache.get(p.user_profile_id or p.data[Post.actor_id._db_field]),
                                profile_cache=profile_cache,
                                tags=tags,
                                has_conversation=has_conversation_cache.get(p.id, False),
                                conversation_external_id=external_id_cache.get(p.id, None))
              for p in posts]
    return post_dicts


def reorder_posts(posts):
    """
    Reorders posts in such way that
    all children posts (replies) of some post will go after it.
    Everything else is in chronological order.
    """
    def __handle_children(children, parent_child_map, result_list):
        for child in children:
            if child in result_list:
                # This was already added as a child of some other node
                pass
            else:
                result_list.append(child)
                if child in parent_child_map:
                    # He has some children of his own, need to take care of these 1st
                    __handle_children(parent_child_map[child], parent_child_map, result_list)

    # important: we need [:] here so that Python don't call posts.__len__()
    #            which would result in a redundant call to posts.count()
    posts_sorted = sorted(posts[:], key=lambda p: p.created_at)

    # maps post_id -> [post, post_child1, post_child2]
    POST_CHILDREN_MAP = OrderedDict()
    for post in posts_sorted:
        try:
            parent = post.parent
        except Post.DoesNotExist:
            parent = None
        if parent and not isinstance(parent, UntrackedPost):
            if parent in POST_CHILDREN_MAP:
                POST_CHILDREN_MAP[parent].append(post)
            else:
                POST_CHILDREN_MAP[parent] = [post]
        else:
            if post not in POST_CHILDREN_MAP:
                # Anomally where somehow parent got there already from a child
                POST_CHILDREN_MAP[post] = []
    posts_reoredered = []
    # At this point the map should be {'parent.id': ['list of children ids']}
    __handle_children(POST_CHILDREN_MAP.keys(), POST_CHILDREN_MAP, posts_reoredered)
    return [p for p in posts_reoredered if not isinstance(p, UntrackedPost) and p in posts]


def get_doc_or_error(model, *args, **kw):
    """Return instance or raise 404 or 401
    if args is provided - args[0] is ID

    """
    from solariat_bottle.db import user

    if args:
        kw['id'] = args[0]

    try:
        current_user = user.User.objects.get_current()
    except user.AuthError:
        current_user = None

    try:
        if current_user:
            obj = model.objects.get_by_user(current_user, **kw)
            if not obj.has_perm(current_user):
                abort(401)
        else:
            obj = model.objects.get(**kw)
        return obj
    except model.DoesNotExist:
        abort(404)


def parse_account(user, data):
    """ Parses account from request data. Staff/Superuser may choose account.
    For other users it returns user's account.

    :param data: is `request.json`, we expect `account_id` key there
    :param user: authorized user
    """
    from solariat_bottle.db.account import Account
    from solariat.db.abstract import DoesNotExist

    account_id = data.get('account_id', data.get('account'))
    account = user.account
    if user.is_staff and account_id:
        try:
            account = Account.objects.get(account_id.strip())
        except DoesNotExist:
            pass
    return account


def jsonify_response(*args, **kwargs):
    from flask import jsonify

    def prepare_json(d):
        if hasattr(d, 'to_json') and callable(getattr(d, 'to_json')):
            return d.to_json()
        elif isinstance(d, dict):
            result = {}
            for k, v in d.iteritems():
                result[k] = prepare_json(v)
            return result
        elif isinstance(d, (tuple, list, set)):
            return [prepare_json(x) for x in d]
        elif isinstance(d, ObjectId):
            return str(d)
        else:
            return d
    return jsonify(prepare_json(dict(*args, **kwargs)))


def parse_bool(value):
    return isinstance(value, bool) and value or (str(value).lower() in {'1', 'true', 'yes'})


class ParamIsMissing(AppException):
    http_code = 400


def required_fields(*fields):
    def _required_fields(method):
        @wraps(method)
        def _check_required_fields(*args, **kwargs):
            for field in fields:
                if kwargs.get(field) is None:
                    raise ParamIsMissing('Parameter "%s" is missing.' % field)
            return method(*args, **kwargs)

        return _check_required_fields
    return _required_fields
