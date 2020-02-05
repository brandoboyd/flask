# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

'''
This file defines the structure for speech acts and how they map to posts.

A speech act is an atom of intention. Posts are composed of sequences of
such atoms. The primary data structure defined here is the SpeechActMap
which is a mapping from speech acts to posts defined in a way that is
optimized for faceted search.

'''

from pymongo.errors import DuplicateKeyError

from solariat_bottle.settings import LOGGER, AppException
from solariat.utils.timeslot import (
    datetime_to_timeslot, timeslot_to_datetime, Timeslot
)
from solariat_bottle.utils.topic_tree import get_topic_tuples
from solariat.db.abstract import Document
from solariat.db.fields import (
    NumField, ObjectIdField, BytesField, EventIdField,
    ListField, DictField, DateTimeField)
from solariat.utils.lang.support import Lang, get_lang_id

# Heavy use of encoding elements from id_encoder
from solariat_bottle.utils.id_encoder import (
    pack_components, unpack_components,
    get_channel_id, get_channel_num, get_status_code, get_post_hash,
    BIGGEST_POST_VALUE, ALL_TOPICS,
    CHANNEL_WIDTH, STATUS_WIDTH, TIMESLOT_WIDTH, SAM_GAP_WIDTH, POST_WIDTH)


# --- classes ---

class SpeechActMap(Document):
    """ Efficient structure to allow searching by intention and also
        to provide an efficient sharding key that distributes well and
        also optimizes query on a single shard because the shard key
        will usually be part of the query.
    """

    # Packed speech-act-map-id (bit-string): pack_speech_act_map_id, unpack_speech_act_map_id
    id                  = BytesField    (db_field='_id', unique=True, required=True)
    channel             = ObjectIdField (db_field='cl',  required=True)
    post                = EventIdField  (db_field='pt',  required=True)
    idx                 = NumField      (db_field='ix',  required=True)
    agent               = NumField      (db_field='at',  default=0)
    language            = NumField      (db_field='le',  default=Lang.EN)
    intention_type_conf = NumField      (db_field='ic',  required=True)
    intention_type_id   = NumField      (db_field='ii',  required=True)
    time_slot           = NumField      (db_field='ts',  required=True)
    created_at          = DateTimeField (db_field='ca',  required=True)
    topic_tuples        = ListField     (DictField(),    db_field='tt')
    message_type        = NumField      (db_field='mtp')

    # --- status constants ---

    # Defining the status values and encodings from channel

    POTENTIAL  = 0 # Note sure about the fit between post and channel
    ACTIONABLE = 1 # Confident of fit between post and channel
    REJECTED   = 2 # Confident of the lack of fit beteen post and channel
    ACTUAL     = 3 # Special extension of actionable for posts that were confirmed by reply

    # Define the assignment modes and their mappings to status. These reflect how
    # the link between post and stats was set. Sometimes it is predicted, and some
    # times it is inferred directly from a user action


    STATUS_MAP = {
        'potential'   : POTENTIAL,  # Predicted
        'assigned'    : POTENTIAL,  # Predicted
        'rejected'    : REJECTED,   # Given
        'discarded'   : REJECTED,   # Predicted
        'actionable'  : ACTIONABLE, # Predicted
        'starred'     : ACTIONABLE, # Given
        'accepted'    : ACTIONABLE, # Given
        'highlighted' : ACTIONABLE, # Predicted
        'replied'     : ACTUAL,     # Given
        'actual'      : ACTUAL,     # Given
    }

    # Reverse lookup to a display name by status code
    STATUS_NAME_MAP = {
        POTENTIAL: "potential",
        ACTIONABLE: "actionable",
        REJECTED: "rejected",
        ACTUAL: "actual"
    }

    # ASSIGNED IF ANY ONE OF THESE!
    ASSIGNED   = {'actionable', 'starred', 'accepted', 'highlighted', 'replied', 'actual'}
    PREDICTED  = {'potential', 'assigned', 'discarded', 'actionable', 'highlighted'}

    # LOOKUP Constants to support agent based access
    NO_AGENT  = -1
    ANY_AGENT = 0

    indexes = [ ('post',) ]

    def to_dict(self):
        return dict(
            id                  = self.id,
            channel             = self.channel,
            intention_type_conf = self.intention_type_conf,
            intention_type_id   = self.intention_type_id,
            time_slot           = self.time_slot,
            post_id             = self.post,
            topics              = self.topics,
            content             = self.content,
            agent               = self.agent,
            language            = self.language,
            status              = self.status,
            message_type        = self.message_type
        )

    @property
    def created(self):
        return timeslot_to_datetime(self.time_slot)

    @property
    def status(self):
        return self.unpacked[1]

    @property
    def post_obj(self):
        if not hasattr(self, '_post'):
            from solariat_bottle.db.post.base import Post
            self._post = Post.objects.get(id=self.post)
        return self._post

    @property
    def topics(self):
        '''Extract out the topics'''
        return [t['t'] for t in self.topic_tuples]

    @property
    def content(self):
        return self.post_obj.speech_acts[self.idx]['content']

    @property
    def unpacked(self):
        return unpack_speech_act_map_id(self.id)

    @classmethod
    def reset(cls, post, channels, agent=None, reset_outbound=False, action='update'):
        '''
        Clears and set keys for all the given channels. Used when assignment between post
        and channel changes, or when assignment between post and agent changes. First
        removes all the old keys, and then geneates new ones. We do not bother updating
        existing documents.
        '''

        if channels == [] or channels == None:
            raise AppException(
                "Oh no! There are no channels provided for synchronizing keys. "
                "This should never happen. Please ask support to have a look at your data."
            )
        # Remove Old Speech Act Keys
        sams = []
        agents_by_channel = {}
        for chan in channels:
            # Initialize agent mapping
            agents_by_channel[get_channel_id(chan)] = cls.ANY_AGENT

            # Now generate all possible ids for all status values
            for status in set(cls.STATUS_MAP.values()):
                sams.extend(make_objects(
                    chan,
                    post,
                    post.speech_acts,
                    status))

        # Now, retrieve the speech act data for agent wherever it exists so we do not
        # lose it.
        for sam in cls.objects(id__in=[sam.id for sam in sams]):
            # Retrieve actual setting if available
            agents_by_channel[get_channel_id(sam.channel)] = sam.agent

        # Nuke the old values. We reset them. Shard key must be immuatble so cannot just
        # change the status value.
        cls.objects.remove(id__in=[sam.id for sam in sams])

        if action == 'remove':
            return []

        # Generate New Speech Act Keys
        sams = []
        for chan in channels:
            # Skip regeneration of keys if this is for a smart tag and it is no longer
            # accepted.....
            if chan.is_smart_tag and chan not in post.accepted_smart_tags:
                continue

            status = cls.STATUS_MAP[post.get_assignment(chan)]
            old_agent  = agents_by_channel[get_channel_id(chan)]

            sams.extend(make_objects(
                chan,
                post,
                post.speech_acts,
                status,
                agent or old_agent))

        for sam in sams:
            try:
                sam.save()
            except DuplicateKeyError:
                LOGGER.error("There is already an speech act with the same ID = %s.", sam.id)
        return sams


# ---- Utils ----------

def pack_speech_act_map_id(
    channel,    # <Channel> | <ch_id:ObjectId> | <ch_num:int:0..1,048,575>
    status,     # <code:int:0..3> | <name:str>
    timeslot,   # <timeslot:int> | <Timeslot>
    post,       # <post:str> | <post_hash:int:0..16,777,215>
    index=None, # Speech act index. If not provided, post must be a number already
):
    """ Returns an encoded speech_act_map id
    """
    channel_num  = get_channel_num(channel)
    status_code  = get_status_code(status)
    timeslot     = timeslot.timeslot if isinstance(timeslot, Timeslot) else timeslot
    post_hash    = get_post_hash(post, index)

    assert 0 <= channel_num  < (1<<CHANNEL_WIDTH), channel_num
    assert 0 <= status_code  < (1<<STATUS_WIDTH)
    assert 0 <= timeslot     < (1<<TIMESLOT_WIDTH)

    return pack_components(
        (0,            SAM_GAP_WIDTH),   # RESERVED SPACE to byte align
        (channel_num,  CHANNEL_WIDTH),
        (status_code,  STATUS_WIDTH),
        (timeslot,     TIMESLOT_WIDTH),  # 2bit level prefix + 20bit number of hours since 2000
        (post_hash,    POST_WIDTH),
    )

def unpack_speech_act_map_id(speech_act_id):
    """ Returns an unpacked speech-act id as a tuple
        (
            <channel_num:int:0..1,048,575>,
            <status_code:int:0..3>,
            <timeslot:int>,
            <post_hash:int:0..16,777,215>
        )
    """
    _, channel_id, status, timeslot, post_hash = \
    unpack_components(
        speech_act_id,
        SAM_GAP_WIDTH,
        CHANNEL_WIDTH,
        STATUS_WIDTH,
        TIMESLOT_WIDTH,
        POST_WIDTH,
    )

    components = (
        channel_id,
        status,
        timeslot,
        post_hash,
    )

    return components



def make_objects(channel, post, speech_acts, status, agent=0):
    """
    Returns a list of speech act map objects to save or delete from
    """
    channel_num = get_channel_num(channel)
    time_slot   = datetime_to_timeslot(post.created_at, 'hour')

    for sa_idx, sa in enumerate(speech_acts):
        topic_tuples = get_topic_tuples(sa, post, channel=channel)
        sam_id = pack_speech_act_map_id(
            channel_num,
            status,
            time_slot,
            post,
            sa_idx
            )

        sam = SpeechActMap(
            id                  = sam_id,
            channel             = get_channel_id(channel),
            post                = post.id,
            agent               = agent,
            language            = get_lang_id(post.language),
            idx                 = sa_idx,
            intention_type_id   = int(sa['intention_type_id']),
            intention_type_conf = sa['intention_type_conf'],
            time_slot           = time_slot,
            created_at          = post.created_at,
            topic_tuples        = topic_tuples,
            message_type        = post._message_type
            )

        yield sam

# ----- Main exports -----

def reset_speech_act_keys(post, channel_id=None, **kw):
    '''
    Keys are reset on every status change for assignment of posts to channels, and
    also for cases where an agent has been linked to a post.
    '''
    from solariat_bottle.db.channel.base import Channel

    if channel_id:
        channel_ids = [channel_id]
    else:
        channel_ids = kw.get('channels') or post.channels

    channels = Channel.objects.ensure_channels(channel_ids)
    # Reset the keys
    return SpeechActMap.reset(post, channels,
                              agent=kw.get('agent', 0),
                              reset_outbound=kw.get('reset_outbound', False),
                              action=kw.get('action', 'update'))


def fetch_posts(channels, start_ts, end_ts, topics, statuses, intentions,
                min_conf, agents, sort_by='time', limit=100, message_type=None,
                create_date_limit=None, languages=None):

    from solariat_bottle.db.post.utils import get_platform_class
    from solariat_bottle.db.channel.base import Channel
    from solariat.db.fields import BytesField

    # --- Preliminary range query for the core matching elements ---
    topics = [ t if isinstance(t, dict) else dict(topic=t, topic_type='leaf') for t in topics]

    to_binary  = BytesField().to_mongo
    match_query_base = []

    for channel in channels:
        for status in statuses:
            # compute id bounds for all posts for this slot
            id_lower_bound = pack_speech_act_map_id(
                channel,
                status,
                start_ts,
                0
            )
            id_upper_bound = pack_speech_act_map_id(
                channel,
                status,
                end_ts,
                BIGGEST_POST_VALUE
            )

            # add an id-constraining query
            assert start_ts <= end_ts
            assert id_upper_bound >= id_lower_bound

            match_query_base.append({
                    '_id': {
                        "$gte": to_binary(id_lower_bound),
                        "$lte": to_binary(id_upper_bound)
                        }
                    })

    primary_filter = {"$or": match_query_base }

    # Add intention restrictions, which operate in the main fields
    primary_filter["ic"] =  { "$gte": min_conf }
    if intentions:
        primary_filter["ii"] =  { "$in":  intentions }

    if message_type is not None:
        primary_filter["mtp"] = {"$in" : message_type}

    # Constrain for agents, again, at the primary level
    if agents:
        primary_filter["at"] =  { "$in":  agents }

    if languages:
        from solariat_bottle.db.channel_trends import make_lang_query

        primary_filter = {"$and": [
            primary_filter,
            make_lang_query(languages, SpeechActMap.language.db_field)
        ]}

    pipeline = [ { "$match": primary_filter }]

    # Generate Secondary Filter only if we have topic constraints.
    topics_match_query = []
    for topic in topics:
        if topic['topic'] != ALL_TOPICS:
            topics_match_query.append({'tt.l': topic['topic_type'] == 'leaf',
                                       'tt.t': topic['topic']})

    if topics_match_query:
        pipeline.append({"$unwind": "$tt"})
        if len(topics_match_query) == 1:
            pipeline.append({"$match" : topics_match_query[0]})
        else:
            pipeline.append({"$match" : {"$or": topics_match_query}})

    # First impose a limit because we cannot spend all day fetching data, and in the worst
    # case, the data could be huge. So this limit is selected as a reasonable case for searching
    # posts. We also allow the input param to over-ride this value if it exceeds it.
    pipeline.append({"$limit": max(10000, limit)})

    # We want the data in sorted order in general.
    pipeline.append({"$sort": {"ca": -1}})

    # Now throttle the resulst to a workable page, where specified

    platform = None
    for ch in channels:
        if not isinstance(ch, Channel):
            ch = Channel.objects.get(ch)
        channel_platform = ch.platform
        if platform and platform != channel_platform:
            # TODO: Is this the correct approach or should we just
            # return a bunch of base posts objects in this case ?
            raise AppException("Trying to fetch posts over multiple platforms!")
        else:
            platform = channel_platform

    # Use the correct class depending on the platform we are searching for
    Post = get_platform_class(platform)

    are_more_speech_acts_fetched = True
    len_res_result = 0
    # we start with such limit because there are
    # ~2 speech acts per post on average
    sa_limit = 2 * limit
    posts = set([])

    # posts are created from speech acts (SA)
    # there may be several SAs for one post
    # we keep increasing `sa_limit` for the SA query until n=limit posts are fetched
    # or until no more SA are fetched
    while len(posts) < limit and are_more_speech_acts_fetched:

        pipeline.append({"$limit": sa_limit})
        res = SpeechActMap.objects.coll.aggregate(pipeline)
        new_posts = Post.objects(id__in=list(set([ r['pt'] for r in res['result']])))
        if create_date_limit:
            new_posts = [p for p in new_posts if p.created_at < create_date_limit]
        posts.update(set(new_posts))
        if len_res_result < len(res['result']):
            len_res_result = len(res['result'])
            sa_limit = 2 * sa_limit
        else:
            are_more_speech_acts_fetched = False

        # we add new limit to the pipeline in the beginning of the while loop
        del pipeline[-1]

    posts = list(posts)
    posts.sort(key=lambda p: p.created_at, reverse=True)

    # start_time = datetime.now()
    #LOGGER.debug("PostManager.by_time_point Aggregated and retrieved in %s sec. Result=%d",
    #                 datetime.now()-start_time,
    #                 len(posts))
    #LOGGER.debug("PostManager.by_time_point Pipeline=\n%s", pprint.pformat(pipeline))

    return posts

