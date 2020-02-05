'''
This file contains a bunch of common elements used for
general analytics and reporting. The main users of this are going to be:
* ChannelStats
* ChannelTrends
* ChannelHotTopics
* ChanelTopicTrends

Eventually, we will possibly deprecate ChannelStats as it will likely be
more efficient and more concise with code to integrate these things.
'''
from time        import sleep
from random      import normalvariate
from itertools   import product
from collections import defaultdict

from pymongo.errors import DuplicateKeyError
from solariat.db                 import fields
from solariat.db.abstract        import SonDocument, Document
from solariat.utils.lang.support import Lang, get_lang_code

from solariat_nlp.sa_labels import ALL_INTENTIONS, SATYPE_ID_TO_NAME_MAP
from solariat_bottle.settings         import LOGGER, AppException, get_var
from solariat_bottle.db.channel.base  import Channel
from solariat_bottle.utils.id_encoder import (
    pack_stats_id, unpack_stats_id, pack_components, get_channel_num,
    CHANNEL_WIDTH, TIMESLOT_WIDTH)


ALL_AGENTS          = 0
ANONYMOUS_AGENT_ID  = -1
DEFAULT_NEW_VERSION = 0
ALL_INTENTIONS_INT  = int(ALL_INTENTIONS.oid)

to_python = fields.BytesField().to_python
to_mongo  = fields.BytesField().to_mongo
to_binary = to_mongo

def conversation_closed(conversation, closing_time, quality):
    from solariat_bottle.tasks.stats import update_conversation_stats
    if get_var('ON_TEST'):
        update_conversation_stats(conversation, closing_time, quality)
    else:
        update_conversation_stats.ignore(conversation, closing_time, quality)

def post_created(post, **context):
    # Avoid circular imports. TODO: We should have a clearer package dep chain.
    from solariat_bottle.utils.stats import _update_channel_stats

    post_channels = list(set(post._get_channels() + post.accepted_smart_tags))

    for channel in post_channels:
        agents_data = post.get_agent_data(channel)
        context.update(agents_data)
        _update_channel_stats(post, status=None, channel=channel, is_new=True, **context)


def post_updated(post, status, channels=None, **context):
    # Avoid circular imports. TODO: We should have a clearer package dep chain.
    from solariat_bottle.utils.stats import _update_channel_stats

    post_channels = list(set(post._get_channels() + post.accepted_smart_tags))
    channels = Channel.objects.ensure_channels(channels) or post_channels

    for channel in channels:
        _update_channel_stats(post, status, channel, **context)


def batch_insert(docs):
    if not docs:
        return
    docs_queries = []
    for doc in docs:
        new_embedded_stats = doc.compute_new_embeded_stats()
        # Generate and updated list based on in memory entries and
        # the existing entries from the database.
        updated_list = doc.EmbeddedStatsCls.update_list(doc.embedded_stats,
                                                         new_embedded_stats)
        doc_data = {doc.name2db_field('embedded_stats') : updated_list}

        find_query = doc._query
        # remove 'gc_counter' if exists
        find_query.pop(doc.name2db_field('gc_counter'), None)
        doc_data.update(find_query)
        docs_queries.append(doc_data)
    docs[0].objects.coll.insert(docs_queries)


class CountDict(dict):
    """
    An 'enhanced' dictionary that for all updates will just
    increment with the new values instead of rewriting.
    """
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def update(self, *args, **kwargs):
        if args:
            other_dict = dict(args[0])
            for key in other_dict:
                if key in self:
                    self[key] = self[key] + other_dict[key]
                else:
                    self[key] = other_dict[key]
        for key in kwargs:
            self[key] = kwargs[key]

    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]


class EmbeddedStatsBase(SonDocument):
    """ Base class for `EmbeddedStats` and `ExtendedEmbeddedStats`. """
    comparable_keys = []
    countable_keys = []

    def __eq__(self, other):
        return all(getattr(self, key) == getattr(other, key)
                   for key in self.comparable_keys)

    def __hash__(self):
        return hash(tuple(getattr(self, key) for key in self.comparable_keys))

    def __str__(self):
        vals = ((key, getattr(self, key))
                for key in self.comparable_keys + self.countable_keys)
        return u"%s(%s)" % (self.__class__.__name__,
                            ", ".join(["%s=%s" % v for v in vals]))

    def inc(self, name, value):
        try:
            dbf = self.name2db_field(name)
        except AppException:
            # Field does not exist
            return
        self.data[dbf] += value

    def set(self, name, value):
        dbf = self.name2db_field(name)
        self.data[dbf] = value

    @classmethod
    def split(cls, collection, items):
        ''' Splits the list up into the unmatched items, and the matched items'''
        unmatched_collection = []
        matched_items = []
        not_found = list(items)
        for candidate in collection:
            found = False
            for item in not_found:
                if item == candidate:
                    matched_items.append(candidate)
                    not_found.remove(item)
                    found = True
                    break
            if found == False:
                unmatched_collection.append(candidate)
        return unmatched_collection, matched_items, not_found

    @classmethod
    def pack(cls, collection):
        return [c.to_mongo(c.to_dict()) for c in collection]

    @classmethod
    def unpack(cls, item_list):
        return [cls(item) if isinstance(item, dict) else item
                for item in item_list]

    @classmethod
    def update_list(cls, existing_items, items_to_update):
        """
        Having two lists of embedded stats, existing stats and new
        stats to update, generate a unified list of the two, where
        we increment counts for common stats.
        """
        existing_items = cls.unpack(existing_items)

        unmatched = []
        matched   = []
        not_found = list(items_to_update)

        for candidate in existing_items:
            found = False

            for item in not_found:
                if item == candidate:
                    for key in cls.countable_keys:
                        candidate.inc(key, item[key])

                    matched.append(candidate)
                    not_found.remove(item)
                    found = True
                    break

            if found == False:
                unmatched.append(candidate)

        new_collection = unmatched + not_found + matched

        return cls.pack(new_collection)


class EmbeddedStats(EmbeddedStatsBase):
    ''' This is a structure to handle short stats we need within
    a slot to show in reports. It is a lean version of ExtendedEmbeddedStats.
    '''
    agent           = fields.NumField(db_field='at', default=0)
    language        = fields.NumField(db_field='le', default=Lang.ALL)

    comparable_keys = ['agent', 'language']


class ExtendedEmbeddedStats(EmbeddedStatsBase):
    ''' This is a structure to handle all the stats we need within
    a slot. It will be used as an embedded document in a list field. It is designed
    to support faceted analysis of data. So we have an underlying document list
    embedded in a slot.
    '''
    # Filter Criteria
    agent          = fields.NumField(db_field='at', default=0)
    is_leaf        = fields.BooleanField(db_field='if', default=True)
    intention      = fields.NumField(db_field='in', default=0)
    language       = fields.NumField(db_field='le', default=Lang.ALL)

    # Metrics
    topic_count    = fields.NumField(db_field='tt', default=0)

    countable_keys  = ['topic_count']   # There are the keys which are keeping counts, so we know what to
                                        # go over in increment process.
    comparable_keys = ['agent', 'is_leaf', 'intention', 'language']

    def __str__(self):
        return "%s(agent=%s, is_leaf=%-5s, intention='%s', language='%s', topic_count=%d)" % (
            self.__class__.__name__,
            self.agent,
            bool(self.is_leaf),
            SATYPE_ID_TO_NAME_MAP.get(str(self.intention), self.intention),
            get_lang_code(self.language),
            self.topic_count
        )


class ChannelStatsBase(Document):
    """
    Base class for trend and topic stats.
    """
    version    = fields.NumField(db_field='_v')

    id         = fields.BytesField(db_field='_id', unique=True, required=True)
    time_slot  = fields.NumField(default=0, db_field='ts')
    gc_counter = fields.NumField(db_field='g')
    channel_ts = fields.BytesField(db_field='ct')

    indexes    = [('gc_counter')]

    def channel_ts_from_id(self, data_id):
        """ From a document id compute a channel ts """
        channel_num, _, _, time_slot = unpack_stats_id(to_python(data_id))
        return self.make_channel_ts(channel=channel_num, time_slot=time_slot)

    @classmethod
    def make_channel_ts(cls, channel, time_slot):
        channel_num = get_channel_num(channel)
        res = pack_components(
            (channel_num, CHANNEL_WIDTH),
            (time_slot, TIMESLOT_WIDTH),
        )
        return res

    @property
    def EmbeddedStatsCls(self):
        return self.fields['embedded_stats'].field.doc_class

    @property
    def _query(self):
        raise AppException('unimplemented method, to be overrided in a subclass')

    def prepare_update_query(self, item_id, item_topic):
        """
        Genereate the update query for all the embedded stats. Also return
        the item version so that we can do optimistic locking on stats update.
        This is needed because we are setting new embedded stats every time.
        """
        item = self.objects.find_one(id=item_id)

        if item:
            # In case of hash collision, this should make sure we are not retrying again
            # and again.
            # item_topic can be None for simple trends
            if not item_topic is None:
                assert item.topic == item_topic, u"Collision '%s' '%s'" % (item.topic, item_topic)
            version = item.version if item.version else DEFAULT_NEW_VERSION
            existing_embedded_stats = item.embedded_stats
        else:
            version = DEFAULT_NEW_VERSION
            existing_embedded_stats = []

        new_embedded_stats = self.compute_new_embeded_stats()
        # Generate and updated list based on in memory entries and
        # the existing entries from the database.
        updated_list = self.EmbeddedStatsCls.update_list(
            existing_embedded_stats,
            new_embedded_stats
        )
        self._upsert_data = {"$set" : {self.name2db_field('embedded_stats') : updated_list}}
        return version

    def upsert(self, w=1):
        # Try 5 times just to make it safe for conflicts.
        if self.stats_upsert(max_tries=5):
            return True
        return False

    def get_expected_topic(self, query):
        """ In the simple reports we expect no topic. """
        return None

    def stats_upsert(self, max_tries=4, logger=LOGGER):
        """Used in upsert() method for documents with embedded stats list.

        Returns True if document has been successfully saved within `max_tries` iterations,
        else False.
        """
        _v = self.name2db_field('version')
        find_query = self._query

        # remove 'gc_counter' if exists
        find_query.pop(self.name2db_field('gc_counter'), None)
        # simple trends do not have topics
        item_topic = self.get_expected_topic(find_query)
        item_id    = find_query["_id"]

        nr_of_tries = 0
        while nr_of_tries < max_tries:
            nr_of_tries += 1
            try:
                version = self.prepare_update_query(item_id, item_topic)
            except AssertionError, e:
                logger.warning(u"Topic hashing collision. Stats not updated! \nfind query=%s\nitem topic=%s\n%s" %
                    (find_query, item_topic, e))
                return False

            # Increment version using $set to be more robust to new documents
            self._upsert_data["$set"][_v] = version + 1
            if version > DEFAULT_NEW_VERSION:
                # If it's an update, just look by id and version, nothing else really matters
                find_query = {_v: version, "_id": find_query["_id"]}
            else:
                # On new documents, set the default version and use whole find query so upsert
                # generates a document with whole data
                find_query[_v] = version

            try:
                assert '_id' in find_query, 'unique id required'
                assert '_v'  in find_query, 'version required'
                self.objects.coll.update(find_query, self._upsert_data, upsert=True, w=1)
                return True
            except AssertionError, e:
                logger.error(
                    u"Find query needs at very least _id and _v. Instead got: %s" %
                    str(find_query))
                return False
            except DuplicateKeyError, e:
                # This is just part of our optimistic lock and can fail a lot especially for high
                # traffic channels, so we should not consider it an error since it just makes actual
                # error tracking in logs harder to do.
                if 2 <= nr_of_tries <= 3:
                    # We already tried 2 or 3 times, it might be an actual problem
                    LOGGER.warning(
                        "channel stats locking: collision %s times in a row. id=%r",
                        nr_of_tries,
                        find_query['_id']
                    )
                elif nr_of_tries >= 4:
                    # We already tried 4 times, something is definitely wrong
                    LOGGER.error(u"channel stats locking: collision repeated %s times. Find query=%s, Upsert=%s" %
                                                (nr_of_tries, find_query, self._upsert_data))
                # If we just had an optimistic lock fail, sleep for a random period
                # until trying again.
                delay_sec = max(0.01, normalvariate(0.1, 0.03))
                LOGGER.debug('channel stats locking: waiting for %.2f sec after a collision', delay_sec)
                sleep(delay_sec)
            except Exception, e:
                LOGGER.error(u"Unhandled exception on stats upsert: %s" % e, exc_info=True)

        LOGGER.error('channel stats locking: giving up after %s collisions', nr_of_tries)
        return False

    def reload(self):
        assert self._query
        obj = self.objects.get(id=self.id)
        self.data = obj.data
        return self

    def save(self):
        raise Exception("Could not save, use upsert instead")

    def filter(self, **kw):
        """Filters embedded_stats list using fields of EmbeddedStat document.
        Example
        >> s = ChannelTrends.objects.get()
        >> s.filter(agent=2)

        """
        def predicate(x):
            preds = []
            for field, value in kw.iteritems():
                op = 'eq'
                if '__' in field:
                    field, op = field.split('__')

                v = getattr(x, field)
                if op == 'eq':
                    preds.append(v == value)
                elif op == 'ne':
                    preds.append(v != value)
                elif op == 'in':
                    preds.append(v in value)
                elif op == 'nin':
                    preds.append(v not in value)
            return all(preds)

        stats = self.EmbeddedStatsCls.unpack(self.embedded_stats)
        return filter(predicate, stats)

    def filter_one(self, **kwargs):
        result = self.filter(**kwargs)
        assert len(result) == 1
        return result[0]


class ChannelTrendsBase(ChannelStatsBase):
    """ This is a base class only for channel trends. """
    def __init__(self, data=None, **kwargs):
        if kwargs and not kwargs.get("channel_ts"):
            channel = kwargs.get("channel") or kwargs.get("channel_num")
            if channel:
                kwargs["channel_ts"] = self.make_channel_ts(channel=channel,
                                                            time_slot=kwargs.get("time_slot"))
        elif data and not data.get("ct"):
            data["ct"] = to_mongo(self.channel_ts_from_id(data["_id"]))
        if data is None:
            self.channel = kwargs.pop('channel', None)
            if not self.channel:
                self.channel_num = kwargs.pop('channel_num', None)
        super(ChannelStatsBase, self).__init__(data, **kwargs)


class ChannelTopicsBase(ChannelStatsBase):
    """Base for topic specific stats
    (ChannelHotTopics and ChannelTopicTrends).

    It is also used for .channel_hot_topics.ChannelHotTopics
    """
    @property
    def _query(self):
        if not self.id:
            self.id = self.__class__.make_id(self.channel, self.time_slot, self.topic, self.status)

        data = self.data.copy()
        data.pop(self.name2db_field('embedded_stats'), None)
        return data

    def get_expected_topic(self, query):
        """ From a document query, what is the topic we require"""
        return query[self.name2db_field("topic")]

    def compute_new_embeded_stats(self):
        new_embedded_stats = []

        for (agent, is_leaf, intention, lang_id), inc_dict in self.embedded_dict.items():
            # For each in memory cached items, create actual embedded
            # stats instances, and increment stat values.
            es = self.EmbeddedStatsCls(
                agent=agent, is_leaf=is_leaf, intention=intention, language=lang_id)
            for stat, value in inc_dict.items():
                es.inc(stat, value)
            new_embedded_stats.append(es)
        return new_embedded_stats

    def update_embedded_stats(self, intention_id, is_leaf, agent, lang_id, inc_dict):
        """
        Generate a dictionary of the form: { (agent,is_leaf,intention) : inc_dict }
        This can then be used to incrementally upgrade the inc_dict for this pair in
        memory and do the save to the database in once call.
        """
        if not hasattr(self, 'embedded_dict'):
            self.embedded_dict = defaultdict(lambda: CountDict({}))

        intentions = {ALL_INTENTIONS_INT}

        if isinstance(intention_id, (tuple, set, list)):
            intentions.update(map(int, intention_id))
        else:
            intentions.add(int(intention_id))

        agents = {ALL_AGENTS}
        if agent:
            agents.add(agent)

        languages = {Lang.ALL}
        if lang_id is not None:
            languages.add(lang_id)

        for key in product(agents, [is_leaf], intentions, languages):
            self.embedded_dict[key].update(inc_dict)

    @classmethod
    def make_id(cls, channel, time_slot, topic, status):
        channel_num = channel.counter

        assert isinstance(channel_num, (int,long)), \
               'channel.counter must be an integer: %r' % channel_num
        assert isinstance(topic,       (basestring,int,long)), \
               'topic must be a string or an integer: %r' % topic

        return to_binary(pack_stats_id(channel_num, topic, status, time_slot))

    @property
    def unpacked(self):
        return unpack_stats_id(self.id)

    def unpack(self):
        self.channel_num, self.topic_hash, self.status, self.time_slot = self.unpacked

