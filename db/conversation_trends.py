
from solariat.db                           import fields

from solariat_bottle.settings              import LOGGER
from solariat_bottle.db.channel_trends     import ChannelTrendsManager
from solariat_bottle.db.channel_stats_base import ChannelTrendsBase, EmbeddedStats
from solariat_bottle.utils.id_encoder      import pack_conversation_stats_id, unpack_conversation_stats_id
from solariat_bottle.db.channel_stats_base import ALL_AGENTS, CountDict

to_binary = fields.BytesField().to_mongo

class ConversationEmbeddedStats(EmbeddedStats):

    # Metrics
    count = fields.NumField(db_field='cn', default=0)

    countable_keys    = ['count']

    # def __hash__(self):
    #     return hash(self.agent)

    def __str__(self):
        return "|agent=%s;count=%s|" % (self.agent, self.count)

class ConversationTrends(ChannelTrendsBase):
    """ Base class for all conversation trends.
    has allow_inheritance set to True
    """
    manager = ChannelTrendsManager

    collection = 'ConversationTrends'
    allow_inheritance = True

    category       = fields.NumField(db_field='cy', default=0)
    embedded_stats = fields.ListField(fields.EmbeddedDocumentField('ConversationEmbeddedStats'), db_field='es')

    def __str__(self):
        res = "%s:: timeslot: %s; category: %s" % (
            self.__class__.__name__,
            self.time_slot,
            self.__class__.get_category_name(self.category))
        return res

    @classmethod
    def get_category_code(cls, category):
        if isinstance(category, int):
            category = category
        elif isinstance(category, (str, unicode)):
            category = cls.CATEGORY_MAP[category]
        else:
            raise Exception("wrong category type: %s; %s;" % (category, type(category)))
        return category

    @classmethod
    def get_category_name(cls, category):
        if isinstance(category, int):
            category = cls.CATEGORY_MAP_INVERSE[category]
        elif isinstance(category, str):
            category = category
        else:
            raise Exception("wrong category type: %s; %s;" % (category, type(category)))
        return category

    @property
    def _query(self):
        if not self.id:
            self.id = self.__class__.make_id(self.channel, self.category, self.time_slot)
        data = self.data.copy()
        data.pop(self.name2db_field('embedded_stats'), None)
        return data

    @classmethod
    def make_id(cls, channel, category, time_slot):
        channel_num = channel.counter
        assert isinstance(channel_num, (int,long)), \
               'channel.counter must be an integer: %r' % channel_num
        return to_binary(
            pack_conversation_stats_id(
                channel_num, 
                category, 
                time_slot))

    @property
    def unpacked(self):
        return unpack_conversation_stats_id(self.id)
    

    @classmethod
    def increment(cls, channel, category, time_slot, agent=None, inc_dict={}, n=1):
        category = cls.get_category_code(category)
        stat = cls(
            channel=channel, 
            category=category, 
            time_slot=time_slot)
        stat.update_embedded_stats(agent=agent, inc_dict=inc_dict)
        stat.upsert()
        return stat
 
    def stats_upsert(self, max_tries=4, logger=LOGGER):
        find_query = {"_id": self._query["_id"]}
        item_id = find_query["_id"]
        update_query = self.__prepare_update_query(item_id)
        self.objects.coll.update(find_query, update_query, upsert=True, w=1)
        return True

    def __prepare_update_query(self, item_id):
        item = self.objects.find_one(id=item_id)
        existing_embedded_stats = item.embedded_stats if item else self.embedded_stats 
        new_embedded_stats      = self.compute_new_embeded_stats()
        updated_list = ConversationEmbeddedStats.update_list(
            existing_embedded_stats, new_embedded_stats)
        data = self._query
        data.pop("_id")
        data[self.name2db_field('embedded_stats')] = updated_list
        update_query  = {"$set" : data}
        return update_query

    def compute_new_embeded_stats(self):
        new_embedded_stats = []
        for agent in self.embedded_dict.keys():
            # For each in memory cahced itemd, create actual embedded
            # stats instances, and increment stat values.
            es = ConversationEmbeddedStats(agent=agent)
            inc_dict = self.embedded_dict[agent]
            for stat, value in inc_dict.items():
                es.inc(stat, value)
            new_embedded_stats.append(es)
        return new_embedded_stats


    def update_embedded_stats(self, agent, inc_dict):
        if not hasattr(self, 'embedded_dict'):
            self.embedded_dict = {}

        agents = {ALL_AGENTS}
        if agent:
            agents.add(agent)

        #items_to_update = []
        for agent in agents:
            if agent in self.embedded_dict:
                self.embedded_dict[agent].update(inc_dict)
            else:
                self.embedded_dict[agent] = CountDict(inc_dict)


class ConversationQualityTrends(ConversationTrends):

    collection = 'ConversationQualityTrends'
    CATEGORY_MAP = {
        "unknown" : 0,
        "loss": 1,
        "win": 2
    }

    CATEGORY_MAP_INVERSE = {v: k for k, v in CATEGORY_MAP.items()}

