from datetime import datetime

from solariat.db.abstract import Document, Index
from solariat.db import fields
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.channel.twitter import UserTrackingChannel, KeywordTrackingChannel
from solariat_bottle.utils.tracking import TrackingNLP, lookup_tracked_channels
from solariat.utils.lang.support import LangCode


def handle_post(platform_name, user_profile, post):
    from solariat_bottle.tasks import get_tracked_channels

    return get_tracked_channels.sync(platform_name, user_profile, post)


def get_all_tracked_channels(user, post):
    '''
    Inlcudes inactive user tracking channels
    '''
    keywords = TrackingNLP.extract_all(post)

    any_active_channels = [
        c.id for c in
        lookup_tracked_channels(post['platform'], post, keywords)
    ]

    channels = list(Channel.objects.find_by_user(user,
                                                 id__in=any_active_channels))

    accessible_keyword_tracking_channels = list(
        KeywordTrackingChannel.objects.find_by_user(user, keywords__in=keywords))

    channels.extend(accessible_keyword_tracking_channels)

    accessible_user_tracking_channels = list(
        UserTrackingChannel.objects.find_by_user(user, usernames=post['user_profile']['user_name']))

    channels.extend(accessible_user_tracking_channels)

    return channels


# FILTER RELATED DATA MODEL

POSTFILTER_CAPACITY = 80000
FILTER_TYPES = ['KEYWORD', 'USER_NAME', 'USER_ID', 'SKIPWORD']
FILTER_TYPE_IDS = range(0, len(FILTER_TYPES))


def get_filter_type_id(filter_type):
    for i in FILTER_TYPE_IDS:
        if FILTER_TYPES[i] == filter_type:
            return i

    raise Exception("Invalid Filter Type: %s" % filter_type)


class PostFilterStream(Document):

    datasift_hash = fields.StringField(db_field='dh')
    last_sync = fields.DateTimeField(db_field='ls')

    @classmethod
    def get(cls):
        return cls.objects.get_or_create(id='datasift_stream1')

    @staticmethod
    def refresh_stats():
        _pf_field = PostFilterEntry.fields['post_filter'].db_field
        res = PostFilterEntry.objects.coll.aggregate([
            {'$match': PostFilterEntry.objects.get_query(channels=[])},
            {'$group': {'_id': '$' + _pf_field, 'sum': {'$sum': 1}}}])

        for pf in res['result']:
            PostFilter(id=pf['_id'].id)._update_item(-int(pf['sum']))

    def untrack_channel(self, channel, twitter_handle=None):
        " untrack all keywords for channel "

        query = PostFilterEntry.objects.get_query(channels=channel)
        if twitter_handle:
            usernames = set(channel.usernames)
            if twitter_handle in usernames:
                usernames.remove(twitter_handle)
            subquery1 = PostFilterEntry.objects.get_query(twitter_handle=twitter_handle)
            subquery2 = PostFilterEntry.objects.get_query(twitter_handle__nin=list(usernames))
            query['$and'] = [subquery1, subquery2]

        PostFilterEntry.objects.coll.update(query,
            {'$pull': PostFilterEntry.objects.get_query(channels=channel)},
            multi=True)

        self.refresh_stats()
        PostFilterEntry.objects.remove(channels=[])

    def untrack_channel_passive(self, channel, twitter_handle=None):
        " untrack all keywords for channel "

        query = PostFilterEntryPassive.objects.get_query(channels=channel)
        if twitter_handle:
            usernames = set(channel.usernames)
            if twitter_handle in usernames:
                usernames.remove(twitter_handle)
            subquery1 = PostFilterEntryPassive.objects.get_query(twitter_handle=twitter_handle)
            subquery2 = PostFilterEntryPassive.objects.get_query(twitter_handle__nin=list(usernames))
            query['$and'] = [subquery1, subquery2]

        PostFilterEntryPassive.objects.coll.update(query,
            {'$pull': PostFilterEntryPassive.objects.get_query(channels=channel)},
            multi=True)

        PostFilterEntryPassive.objects.remove(channels=[])

    def tracking_state(self, filter_type, entries, channels, langs):
        tracked = []
        for lang in langs:
            for entry in map(TrackingNLP.normalize_kwd, entries):
                tracked.append((entry, lang, PostFilterEntry.objects(
                    filter_type_id=get_filter_type_id(filter_type),
                    entry=entry,
                    lang=lang,
                    channels__all=channels).limit(1).count() == 1))

        return tracked

    def track(self, filter_type, entries, channels, twitter_handle=None, langs=None):
        if langs is None:
            langs = [LangCode.EN]

        for lang in langs:

            for entry in map(TrackingNLP.normalize_kwd, entries):

                query = PostFilterEntry.objects.get_query(
                    filter_type_id=get_filter_type_id(filter_type),
                    entry=entry,
                    lang=lang)

                # restrict channels because if it has not actually been saved yet
                # then this update would trigger a recursion.
                kwargs = {'channels__each': [c for c in channels if c.id]}
                if filter_type == 'USER_ID' and twitter_handle:
                    kwargs['twitter_handle'] = twitter_handle

                update = {'$addToSet': PostFilterEntry.objects.get_query(**kwargs)}

                res = PostFilterEntry.objects.coll.update(query, update, upsert=True, multi=True)

                if res['updatedExisting'] == False:
                    post_filter = self.get_available_filter(filter_type)
                    PostFilterEntry.objects.coll.update(
                        {'_id': res['upserted']},
                        {'$set': PostFilterEntry.objects.get_query(post_filter=post_filter)})
                    
                    post_filter.add_item()

    def track_passive(self, entries, channels, twitter_handle=None):

        for entry in map(TrackingNLP.normalize_kwd, entries):

            query = PostFilterEntryPassive.objects.get_query(entry=entry)

            # restrict channels because if it has not actually been saved yet
            # then this update would trigger a recursion.
            kwargs = {'channels__each': [c for c in channels if c.id]}
            if twitter_handle:
                kwargs['twitter_handle'] = twitter_handle
            update = {'$addToSet': PostFilterEntryPassive.objects.get_query(**kwargs)}

            PostFilterEntryPassive.objects.coll.update(query, update, upsert=True)

    def untrack(self, filter_type, entries, channels, langs=None):
        if langs is None:
            langs = [LangCode.EN]

        for lang in langs:

            channels_field = PostFilterEntry.fields['channels'].db_field
            post_filter_field = PostFilterEntry.fields['post_filter'].db_field

            for entry in map(TrackingNLP.normalize_kwd, entries):

                query = PostFilterEntry.objects.get_query(
                    filter_type_id=get_filter_type_id(filter_type), entry=entry, lang=lang)

                update={'$pullAll': PostFilterEntry.objects.get_query(channels=channels)}
                res = PostFilterEntry.objects.coll.find_and_modify(query=query,
                    update=update,
                    fields={channels_field: True, post_filter_field: True},
                    new=True)

                if isinstance(res, dict) and not res[channels_field]:
                    post_filter = PostFilter.objects.find_one(res[post_filter_field].id)
                    if post_filter:
                        post_filter.remove_item()
                    PostFilterEntry.objects.remove(id=res['_id'])

    def get_available_filter(self,
                             filter_type):
        candidates = [f for f in PostFilter.objects.find(
                filter_type_id=get_filter_type_id(filter_type),
                spare_capacity__gt=0).limit(1)]

        if candidates != []:
            return candidates[0]

        return PostFilter.objects.create(
            filter_type_id=get_filter_type_id(filter_type))

    def set_datasift_hash(self, datasift_hash):
        " set atomically datasift hash and update last_sync "

        now = datetime.now()
        self.update(set__datasift_hash=datasift_hash,
                    set__last_sync=now)

        self.datasift_hash = datasift_hash
        self.last_sync = now


class PostFilter(Document):
    '''
    Internal Structure representing the integartion
    data structure with a data stream provider.
    '''
    filter_type_id = fields.NumField(db_field='fd',
                                     choices=FILTER_TYPE_IDS)

    # How many entries
    entry_count = fields.NumField(db_field='et',
                                  default=0)

    # How many more entries can you handle
    spare_capacity = fields.NumField(db_field='sy',
                                     default=POSTFILTER_CAPACITY)

    datasift_hash = fields.StringField(db_field='dh')

    last_update = fields.DateTimeField(db_field='lu',
                      default=datetime.now())
    last_sync = fields.DateTimeField(db_field='ls')

    def _update_item(self, n):
        self.update(inc__entry_count=n,
                    inc__spare_capacity=-n,
                    set__last_update=datetime.now())

    def add_item(self):
        ''' Increment counters'''
        self._update_item(1)

    def remove_item(self):
        ''' Decrement counters or remove if empty '''
        if self.entry_count >= 2:
            self._update_item(-1)
        else:
            self.delete()

    def set_datasift_hash(self, datasift_hash):
        " set atomically datasift hash and update last_sync "

        return self.objects.coll.find_and_modify(
            query={'_id': self.id},
            update={'$set': {
                self.fields['datasift_hash'].db_field: datasift_hash,
                self.fields['last_sync'].db_field: datetime.now()}},
            new=True)


class PostFilterEntry(Document):

    entry = fields.StringField(db_field='kd')

    filter_type_id = fields.NumField(db_field='ee',  choices=FILTER_TYPE_IDS)

    post_filter = fields.ReferenceField(PostFilter, db_field='pr')

    twitter_handles = fields.ListField(fields.StringField(), db_field='th')

    channels = fields.ListField(fields.ReferenceField('Channel'), db_field='cs')

    lang = fields.StringField(default=LangCode.EN)

    indexes = [
        ('entry', 'channels', 'lang'),
        Index(('filter_type_id', 'entry', 'lang'), unique=True),
        ('channels',)
    ]

    @property
    def filter_type(self):
        if self.filter_type_id is not None:
            return FILTER_TYPES[int(self.filter_type_id)]


class PostFilterEntryPassive(Document):

    entry = fields.StringField(db_field='kd')

    channels = fields.ListField(fields.ReferenceField('Channel'),
                                                      db_field='cs')

    twitter_handles = fields.ListField(fields.StringField(), db_field='th')

    indexes = [ Index(('entry'), unique=True) ]
