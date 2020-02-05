from solariat_nlp.analytics             import distances

from solariat.utils       import timeslot
from solariat.utils.hidden_proxy import unwrap_hidden
from solariat.db          import fields
from solariat.db.abstract import Document, Index, Manager

from solariat_bottle.settings      import get_var, LOGGER, AppException
from solariat_bottle.db.mixins   import ClassifierMixin
from solariat.elasticsearch import ElasticCollection, ESMixin, ESManager


def migrate_channel_filter(channel, channel_filter_cls):
    current_cf = channel.channel_filter
    new_cf     = ChannelFilter.objects.create_instance(channel,
                                                       channel_filter_cls)
    for item in ChannelFilterItem.objects(channel_filter=current_cf):
        current_cf._withdraw(item)
        item.channel_filter = new_cf
        item.save()
        new_cf._deploy(item)

    channel.channel_filter = new_cf
    channel.save()

    # Finally, retrain
    channel.channel_filter.retrain()

    # And remove the old one
    current_cf.delete()


def get_channel_filter_class(filter_name):
    channel_filter_map = {
            'ChannelFilter': ChannelFilter,
            'OnlineChannelFilter': OnlineChannelFilter,
            'LocalStoreChannelFilter': LocalStoreChannelFilter,
            'DbChannelFilter': DbChannelFilter,
            'ESBasedChannelFilter': ESBasedChannelFilter,
            'OnlineChannelFilter': OnlineChannelFilter
        }
    return channel_filter_map[filter_name]


class ChannelFilterManager(Manager):
    ''' Customization of access for factory class creation and also for cache access '''

    # TODO: protect this shared cache with a lock

    # Support for object cache
    CACHE       = {}  # TODO: replace with solariat.datastruct.LRU_cache
    CACHE_LIMIT = 100

    def _set_cache(self, _id, item):
        ''' Handle cache update. Will first free space as needed'''
        if len(self.CACHE.keys()) > self.CACHE_LIMIT:
            lru_key = sorted(self.CACHE.items(), key=lambda i: i[1])[0][0]
            del self.CACHE[lru_key]

        self.CACHE[str(_id)] = (item, timeslot.now())

    def create_instance(self, channel, cls_name=None):
        '''
        A Factory class based on config settings.
        '''
        class_name = cls_name if cls_name != None else get_var('CHANNEL_FILTER_CLS', 'OnlineChannelFilter')
        channel_filter = get_channel_filter_class(class_name).objects.create(channel=channel)
        self._set_cache(channel_filter.id, channel_filter)
        return channel_filter

    def get_instance(self, _id):
        '''
        Interception point for a local cache.
        '''
        str_id = str(_id)
        if str_id not in self.CACHE or self.CACHE[str_id][0].requires_refresh:
            self._set_cache(str_id, super(ChannelFilterManager, self).get(id=_id))

        return self.CACHE[str_id][0]


class ChannelFilter(Document):
    ''' Base channel filter class (abstract)
    '''
    collection        = 'ChannelFilter'
    allow_inheritance = True
    channel           = fields.ReferenceField('Channel', db_field='cl')
    manager           = ChannelFilterManager


    '''
    Methods for channel classification on inbound and outbound actions
    '''
    @property
    def accepted_items(self):
        raise AppException('unimplemented method, to be overrided in a subclass')

    @property
    def rejected_items(self):
        raise AppException('unimplemented method, to be overrided in a subclass')

    @property
    def requires_refresh(self):
        return False

    @property
    def inclusion_threshold(self):
        return self.channel.inclusion_threshold

    @property
    def exclusion_threshold(self):
        return self.channel.exclusion_threshold

    @property
    def reject_count(self):
        return 0

    @property
    def accept_count(self):
        return 0

    def _predict_fit(self, item):
        raise AppException('unimplemented method, to be overrided in a subclass')

    def handle_accept(self, item):
        raise AppException('unimplemented method, to be overrided in a subclass')

    def handle_reject(self, item):
        raise AppException('unimplemented method, to be overrided in a subclass')

    def retrain(self):
        ''' For forcing a retraining of the filter.'''
        pass

    def reset(self):
        ''' Remove all related items '''
        pass

    def extract_features(self, item):
        ''' Return the list of features for the given item'''
        return []


class LocalStoreChannelFilter(ChannelFilter):
    _accepted_items = fields.ListField(fields.DictField(),
                                       db_field='as')
    _rejected_items = fields.ListField(fields.DictField(),
                                       db_field='rs')
    @property
    def accepted_items(self):
        return self._accepted_items
    @property
    def rejected_items(self):
        return self._rejected_items

    def reset(self):
        ''' Remove all related items '''
        self._accepted_items = []
        self._rejected_items = []
        self.save()


class DbChannelFilter(ChannelFilter):
    ''''
    A channel filter implemnetation based on similarity with examples
    stored and retrived from the DB alone. NO ES based matching.
    '''

    _reject_count = fields.NumField(db_field='rc', default=-1)
    _accept_count = fields.NumField(db_field='ac', default=-1)

    def handle_accept(self, item):
        obj = self.get_or_create_item(item, 'accepted')
        return obj

    def handle_reject(self, item):
        return self.get_or_create_item(item, 'rejected')

    @property
    def accepted_items(self):
        return ChannelFilterItem.objects(channel_filter=self, filter_type='accepted')

    @property
    def rejected_items(self):
        return ChannelFilterItem.objects(channel_filter=self, filter_type='rejected')

    @property
    def reject_count(self):
        if self._reject_count == -1:
            self._reject_count = len(self.rejected_items)
            self.save()
        return self._reject_count

    @property
    def accept_count(self):
        if self._accept_count == -1:
            self._accept_count = len(self.accepted_items)
            self.save()
        return self._accept_count

    def _compute_distance(self,
                          filter_type,
                          item):
        score = 0
        top_matches = self._search(filter_type, item)

        if isinstance(item, ChannelFilterItem):
            content = item.vector['content']
        else:
            content = item.content
        content = unwrap_hidden(content)

        def _normalize(m):
            return isinstance(m, dict) and m['content'] or m.vector['content']

        for match in [_normalize(m) for m in top_matches]:
            d = distances.calc_distance(content, match)
            score = max(d, score)

        return score

    '''
    Methods for channel classification on inbound and outbound actions
    '''
    def _predict_fit(self, item):
        reject_score = self._compute_distance('rejected', item)
        accept_score = self._compute_distance('accepted', item)

        score =  0.5 +  accept_score / 2  - reject_score / 2

        '''
        print "REJECT SCORE", reject_score
        print "ACCEPT SCORE", accept_score
        print "ACTUAL SCORE", score
        '''
        return score

    def make_post_vector(self, item):
        ''' Convert the post to a useful dictionary of data that will allow
            all sorts of features to be applied.
        '''
        post = item
        if isinstance(item, dict):
            content     = post['content']
            speech_acts = post['speech_acts']
        else:
            content     = post.content
            speech_acts = post.speech_acts

        content = unwrap_hidden(content)
        speech_acts = map(unwrap_hidden, speech_acts)

        post_vector = self.channel.make_post_vector(post)
        post_vector.update(dict(speech_acts=speech_acts, content=content))
        return post_vector

    def reset_counters(self):
        self._reject_count = -1
        self._accept_count = -1
        self.save()

    def get_or_create_item(self, item, filter_type):
        from solariat.db.abstract import DBRef

        # TODO: This should probably just add the item rather than swap it
        query={
            ChannelFilterItem.channel_filter.db_field:
                DBRef(self.collection, self.id),
            ChannelFilterItem.item_id.db_field:
                item.data['_id']}

        update={"$set": {
                ChannelFilterItem.filter_type.db_field:
                    filter_type,
                ChannelFilterItem.vector.db_field:
                    self.make_post_vector(item)}}

        fam_obj = ChannelFilterItem.objects.coll.find_and_modify(
            query=query,
            update=update,
            upsert=True,
            new=True,
            full_response=True)

        # Reset counters
        self.reset_counters()

        if fam_obj['ok'] and fam_obj['value']:
            filter_item = ChannelFilterItem(fam_obj['value'])
            filter_item.channel_filter = self
            if fam_obj['lastErrorObject']['updatedExisting']:
                self._withdraw(filter_item)
            self._deploy(filter_item)
            return filter_item
        else:
            LOGGER.error("%s", fam_obj['lastErrorObject'])
            return None

    def _search(self, filter_type, item):
        '''Over-ride default to use ES'''

        return [i.vector for i in ChannelFilterItem.objects(
                channel_filter=self,
                filter_type=filter_type)]

    def reset(self):
        ''' Remove all related items '''
        for item in ChannelFilterItem.objects(channel_filter=self):
            self._withdraw(item)
            item.delete()

        self.reset_counters()

    def _withdraw(self, filter_item):
        pass

    def _deploy(self, filter_item):
        pass


class ESBasedChannelFilter(DbChannelFilter):
    ''''
    A channel filter implementation that utilizes ES for matching with full text
    matching
    '''

    def _search(self, filter_type, item):
        '''Over-ride default to use ES'''
        content = hasattr(item, 'content') and item.content or item.get('content')
        content = unwrap_hidden(content)
        return ChannelFilterItem.objects.search(
            channel=self.channel,
            filter_type=filter_type,
            item=dict(content=content))

    def _withdraw(self, filter_item):
        filter_item.withdraw()

    def _deploy(self, filter_item):
        filter_item.deploy(refresh=True)


class OnlineChannelFilter(ClassifierMixin, DbChannelFilter):
    '''
    A channel filter implementation using FilterClassifier
    '''
    #packed_clf = fields.BinaryField()  # WARNING: 2MB limit!
    #counter    = fields.NumField(default=0)     # Use to track iterations

    def __init__(self, *args, **kw):
        self._clf = None
        super(OnlineChannelFilter, self).__init__(*args, **kw)

    def save(self):
        # make sure we also save classifier state (pickled and zipped)
        #print 'save(): _clf=%r' % self._clf
        self.pack_model()
        super(OnlineChannelFilter, self).save()

    @property
    def requires_refresh(self):
        ''' Must refresh if the counts are off'''
        return OnlineChannelFilter.objects.find_one(id=self.id, counter=self.counter) is None

    def handle_accept(self, item):
        # Call super class and get the vector
        vec = super(OnlineChannelFilter, self).handle_accept(item).vector
        self.clf.train([vec], [1])
        self.save()

        # Re-train
        #self.retrain()

    def handle_reject(self, item):
        vec = super(OnlineChannelFilter, self).handle_reject(item).vector
        self.clf.train([vec], [0])
        self.save()
        #self.retrain()

    def reset(self):
        ''' Remove all related items - retrain the empty model '''
        super(OnlineChannelFilter, self).reset()
        self.retrain()


class ChannelFilterItemCollection(ElasticCollection):
    "ES collection to store Inbound filters"

    def __init__(self):
        self.INDEX_NAME = get_var('CHANNEL_FILTER_ITEM_INDEX_NAME') or 'channelfilteritems'
        self.DOCUMENT_NAME = get_var('CHANNEL_FILTER_ITEM_DOCUMENT_NAME') or 'channelfilteritem'

        ElasticCollection.__init__(self)

    MAPPING = {
        "text": {"type": "string", "boost": 2.0},
        "channel": {"type": "string", "index": "not_analyzed"},
        "filter_type": {"type": "string", "index": "not_analyzed"},
    }

    def set_mapping(self):
        import json

        mapping_data = """{"%s":{
            "_boost" : {"name" : "_boost", "null_value" : 1.0},
            "properties": %s
        }
        }""" % (self.DOCUMENT_NAME, self.MAPPING)

        url = "%s/_mapping" % self.item_url()

        return self.index.request(
            url,
            method='PUT',
            body=json.dumps(mapping_data))

class ChannelFilterItemManager(ESManager):
    ESCollection = ChannelFilterItemCollection()

    def search(self, channel, filter_type, item):
        '''
        Search channel filter items based on a given item in a specific channel
        and for a specific filter
        '''

        query = {"bool": {"must": [
                    {"match": { "content": item['content'] }},
                    ]}}



        query_filter = {"and" :
                        [ {"term": { "channel": str(channel.id) }},
                          {"term": { "filter_type": filter_type }}
                          ]
                        }

        filtered_query = { "filtered" : { "query": query,
                                          "filter": query_filter
                                          }
                           }

        return super(ChannelFilterItemManager, self).search(size=1,
                                                            query=filtered_query)


class PostOrResponseId(fields.EventIdField):
    def to_python(self, value):
        if isinstance(value, basestring) and value.endswith(':r'):
            return value
        else:
            return super(PostOrResponseId, self).to_python(value)


class ChannelFilterItem(Document, ESMixin):
    ESCollection   = ChannelFilterItemCollection()
    manager        = ChannelFilterItemManager
    item_id        = PostOrResponseId(db_field='it')
    channel_filter = fields.ReferenceField(ChannelFilter, db_field='cr')
    content        = fields.StringField(db_field='ct')
    vector         = fields.DictField(db_field='vr')
    filter_type    = fields.StringField(choices=['rejected', 'starred'],
                                        default='rejected',
                                        db_field='fe')
    is_active      = fields.BooleanField(default=True, db_field='ia')

    indexes = [ Index(('channel_filter', 'item_id'), unique=True) ]

    def to_dict(self):
        ''' Used for pushing to ES '''
        d = super(ChannelFilterItem, self).to_dict()
        d['content'] = self.vector['content']
        d['filter_type'] = str(self.filter_type)
        d['channel'] = str(self.channel_filter.channel.id)
        d['item_id'] = str(d['item_id'])
        return d

# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
