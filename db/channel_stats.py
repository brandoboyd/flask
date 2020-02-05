# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

"#Document to store statistic data"

from collections import defaultdict
from solariat_nlp.sa_labels import ALL_INTENTIONS

from ..settings import LOGGER, AppException
from solariat.db import fields
from solariat.utils.timeslot import (
    now as get_now, datetime_to_timeslot, TIMESLOT_EPOCH, decode_timeslot
)
from .channel.base import (
    Channel, ChannelAuthDocument, ChannelAuthManager, REJECT_STATUSES)


def update_for_actionable_post(stats, max_intention,  relevance, bulk=None):
    ''' This method handles stats update when we get an actionable post.
    Breaking it out to enable easier testing.

    '''
    # threshold crossed for this channel
    stats.inc('number_of_actionable_posts', 1,             bulk=bulk)
    stats.inc('cumulative_relevance',       relevance,     bulk=bulk)
    stats.inc('cumulative_intention',       max_intention, bulk=bulk)

def get_max_intention(speech_acts, channel):
    '''
    Extracts the highest intention signal for selected speech
    act types.

    This could move to a channel. Arguably.
    '''

    # The default is strictly negative so that the returned value in
    # the event of no match will be less than the default threshold.
    max_intention = -1.0

    for speech_act in speech_acts:
        # If it is discarded, then the confidence will be 0.0
        if speech_act['intention_type'] == 'DISCARDED':
            continue

        in_constraints = (speech_act[
                'intention_type'] in channel.intention_types)
        if not channel.intention_types or in_constraints:
            max_intention = max(speech_act['intention_type_conf'],
                                max_intention)

    return max_intention

def no_post_created(post, now=None):
    """ Update post count for case where the post is irrelevant.

    """
    if now is None:
        now = post.created

    for channel in post._get_channels():
        for stats in get_levels(channel, now):
            stats.inc('number_of_posts', 1)

def post_created(post):
    """
    Do the work for updating stats.
    """
    try:
        info = post.to_dict(include_summary=False)
    except:
        info = post.to_dict()
    bulk = ChannelStats._new_bulk_operation()

    for channel in post._get_channels() + post.accepted_smart_tags:
        _post_created(post, channel, info, bulk=bulk)

    bulk.execute()  # run all the stats updates at once


def _post_created(post, channel, info, bulk=None):
    max_intention = get_max_intention(info['speech_acts'], channel)

    if max_intention > 1.0:
        msg = "Intention score is: %.2f" % max_intention
        LOGGER.error(msg)
        raise AppException(msg)

    relevance = 0.0
    if not channel.use_matchable_for_relevance():
        relevance = channel.compute_post_relevance(post)

    for stats in get_levels(channel, post.created_at):
        stats.inc('number_of_posts', 1, bulk=bulk)

        #update discarded/highlighted counters
        post_status = post.get_assignment(channel)
        if post_status:
            stats.inc('number_of_%s_posts' % post_status, 1, bulk=bulk)

        update_for_actionable_post(
            stats         = stats,
            max_intention = max_intention,
            relevance     = relevance,
            bulk          = bulk,
        )
        stats.inc_feature_counts(info['speech_acts'], bulk=bulk)

    return True

def post_updated(post, status, inc_value=1, channels=(), date=None, **kw):
    _date = date or post.created_at
    channels = channels or post._get_channels()
    from_status = kw.get('from_status')
    old_status = kw.get('old_status')
    if (kw.get("action") == "remove" and old_status in REJECT_STATUSES
        or kw.get("action") == "add" and old_status in ('starred', 'accepted')):
        # Removing an already removed status should not influence stats
        # Same for adding an already added tag
        return

    for channel in channels:
        for stats in get_levels(channel, _date):
            # collecting classifier impact stats in this block
            if kw.get("update_classifier_stats", True):
                if channel.is_smart_tag:
                    # print old_status, kw.get("action"), inc_value
                    if kw.get("action") == "add":
                        # that means that user is assigning a tag to post
                        if old_status in REJECT_STATUSES:
                            stats.inc('number_of_false_negative', 1)
                        # that means that user is confirming a tag (which was assigned automatically)
                        elif "highlighted" == old_status:
                            stats.inc('number_of_true_positive', 1)
                    # that means that user is removing a tag
                    elif kw.get("action") == "remove":
                        stats.inc('number_of_false_positive', 1)
                if not channel.is_smart_tag and from_status and from_status != status:
                    # user replying to a post
                    if (from_status == "highlighted"
                        and status in ("replied")
                    ):
                        stats.inc('number_of_true_positive', 1)
                    # user rejecting a post
                    elif (from_status not in REJECT_STATUSES
                        and status in ("rejected", "discarded")
                    ):
                        stats.inc('number_of_false_positive', 1)
                    # user accepting a post
                    elif (from_status in REJECT_STATUSES
                        and status not in ("rejected", "discarded")
                    ):
                        stats.inc('number_of_false_negative', 1)

            if (channel.is_smart_tag and kw.get('tag_assignment')):
                stats.inc('number_of_posts', inc_value)

            stats.inc('number_of_%s_posts' % status, inc_value)
            if from_status and from_status != status:
                stats.inc('number_of_%s_posts' % from_status, -inc_value)

def post_clicked(post, matchable):
    "Update statistic"
    for channel in Channel.objects(id__in=post.channels):
        for stats in get_levels(channel):
            stats.inc('number_of_clicks', 1)
    matchable.inc('clicked_count', 1)


def get_levels(channel, now=None):
    """Yield stats documents from hour to month
    It could be in ChannelStats.objects but
    for some reason that doesn't work

    """
    try:
        channel_id_str = str(channel.id)
    except AttributeError:
        channel_id_str = str(channel)
    if now is None:
        now = get_now()
    for level in ('hour','day','month'):
        time_slot = datetime_to_timeslot(now, level)
        yield ChannelStats(time_slot=time_slot, channel=channel_id_str)

def aggregate_stats(user, channel_ids, from_, to_, level, aggregate=('number_of_posts', 'number_of_actionable_posts')):
    stats = defaultdict(dict)
    for stat in ChannelStats.objects.by_time_span(user,
        channel_ids,
        start_time=from_,
        end_time=to_,
        level=level):
        for a in aggregate:
            stats[str(stat.channel)].setdefault(a, 0)
            stats[str(stat.channel)][a] += getattr(stat, a)
    return stats


class ChannelStatsManager(ChannelAuthManager):

    "Calcualte meta data on every create"

    def by_time_span(self, user, channel, start_time=None, end_time=None, level='hour', **extra):
        "Return generator of docs for time period"

        start_time = start_time or TIMESLOT_EPOCH
        end_time   = end_time   or get_now()

        from_ts = datetime_to_timeslot(start_time, level)
        to_ts   = datetime_to_timeslot(end_time,   level)

        if from_ts == to_ts:
            extra['time_slot'] = from_ts
        else:
            extra['time_slot__gte'] = from_ts
            extra['time_slot__lte'] = to_ts

        if hasattr(channel, '__iter__'):
            extra['channel__in'] = channel
        else:
            extra['channel'] = channel

        # from time import time
        # start_t = time()
        stats = self.find_by_user(user, **extra)
        #LOGGER.debug("%s.by_time_span(): querty time %.3f sec", self.__class__.__name__, time() - start_t)

        return stats

    def by_time_point(self, user, channel, time_point=None, level='hour', **extra):
        "Return generator of docs for time period"

        return self.find_by_user(
            user,
            channel   = channel,
            time_slot = datetime_to_timeslot(time_point, level),
            **extra
        )

class ChannelStats(ChannelAuthDocument):
    "Store stats for month, day and hour"
    manager = ChannelStatsManager

    channel = fields.ObjectIdField(required=True,
                                   unique_with='time_slot',
                                   db_field='cl')

    # The time slot is a numeric encoding of elapsed time
    # see utils.timeslot for details
    time_slot = fields.NumField(required=True, db_field="ts")

    number_of_posts = fields.NumField(default=0, db_field='nop')
    feature_counts  = fields.DictField(db_field="fc")

    number_of_rejected_posts    = fields.NumField(default=0, db_field='norp')
    number_of_starred_posts     = fields.NumField(default=0, db_field='nosp')
    number_of_discarded_posts   = fields.NumField(default=0, db_field='nodp')
    number_of_highlighted_posts = fields.NumField(default=0, db_field='nohp')
    number_of_actionable_posts  = fields.NumField(default=0, db_field="noaep")
    number_of_assigned_posts    = fields.NumField(default=0, db_field="noadp")
    number_of_replied_posts     = fields.NumField(default=0, db_field="noalp")
    number_of_accepted_posts    = fields.NumField(default=0, db_field="noacp")

    number_of_false_negative = fields.NumField(default=0, db_field="nofn")
    number_of_true_positive  = fields.NumField(default=0, db_field="notp")
    number_of_false_positive = fields.NumField(default=0, db_field="nofp")

    # Quality Measures
    cumulative_relevance = fields.NumField(default=0.0, db_field="cr")
    cumulative_intention = fields.NumField(default=0.0, db_field="ci")

    # Outbound Statistics
    number_of_impressions = fields.NumField(default=0, db_field="noi")
    number_of_clicks      = fields.NumField(default=0, db_field="noc")

    indexes = [ ('channel', ), ('time_slot') ]

    @property
    def level(self):
        return decode_timeslot(self.time_slot)[1]

    @property
    def mean_relevance(self):
        if self.number_of_posts:
            return self.cumulative_relevance / self.number_of_posts
        return 0.0

    @property
    def mean_intention(self):
        if self.number_of_actionable_posts:
            return self.cumulative_intention / self.number_of_actionable_posts
        return 0.0

    def to_dict(self, fields2show=None):
        result = ChannelAuthDocument.to_dict(self, fields2show)
        del result['cumulative_relevance']
        del result['cumulative_intention']
        result['mean_relevance'] = self.mean_relevance
        result['mean_intention'] = self.mean_intention
        result['level'] = self.level
        return result

    def __str__(self):
        "String repr"
        return str(self.time_slot)

    @classmethod
    def _new_bulk_operation(cls, ordered=False):
        """ Allocates a new bulk DB operation
            (only available in PyMongo 2.7+)
        """
        coll = cls.objects.coll
        if ordered:
            return coll.initialize_ordered_bulk_op()
        else:
            return coll.initialize_unordered_bulk_op()

    def inc(self, field_name, value, bulk=None):
        """ Issue an update DB operation that increments a specified field
            in the corresponding document.

            bulk -- an optional <BulkOperationBuilder> instance to store
                    the postponed $inc operation instead of doing it right away
                    (only available in PyMongo 2.7+)
        """
        if not isinstance(value, (int, float)):
            raise AppException(
                "%s must be integer or float" % value)

        query = self.__class__.get_query(
            time_slot = self.time_slot,
            channel   = str(self.channel)
        )
        update = {'$inc': {self.fields[field_name].db_field:value}}

        if bulk is None:
            # sending a DB request right away
            coll = self.objects.coll
            return coll.update(query, update, upsert=True)
        else:
            # adding a postponed DB request to the bulk set
            return bulk.find(query).upsert().update_one(update)

    def set(self, field_name, value, bulk=None):
        """ Issue an update DB operation that sets a specified field
            in the corresponding document.

            bulk -- an optional <BulkOperationBuilder> instance to store
                    the postponed $set operation instead of doing it right away
                    (only available in PyMongo 2.7+)
        """
        if not isinstance(value, (int, float)):
            raise AppException(
                "%s must be integer or float" % value)

        query = self.__class__.get_query(
            time_slot=self.time_slot,
            channel=str(self.channel))
        update = {'$set': {self.fields[field_name].db_field:value}}

        if bulk is None:
            # sending a DB request right away
            coll = self.objects.coll
            return coll.update(query, update, upsert=True)
        else:
            # adding a postponed DB request to the bulk set
            return bulk.find(query).upsert().update_one(update)

    def inc_feature_counts(self, speech_acts, bulk=None):
        """ Update SpeechAct stats.

            Issue an update DB operation that increments SpeechAct counters
            in the corresponding document.

            bulk -- an optional <BulkOperationBuilder> instance to store
                    the postponed $inc operation instead of doing it right away
                    (only available in PyMongo 2.7+)
        """
        increments = {}
        field_name = self.fields['feature_counts'].db_field

        def add_increment(int_id):
            key = '%s.%s' % (field_name, int_id)
            increments[key] = 1

        for sa in speech_acts:
            int_id = sa['intention_type_id']
            if int_id:
                add_increment(int_id)

        if increments:
            # if there is at least one intention -- increment a counter for ALL also
            add_increment(ALL_INTENTIONS.oid)

        query = self.__class__.get_query(
            time_slot = self.time_slot,
            channel   = str(self.channel)
        )
        update = {'$inc': increments}

        if bulk is None:
            # sending a DB request right away
            coll = self.objects.coll
            return coll.update(query, update, upsert=True)
        else:
            # adding a postponed DB request to the bulk set
            return bulk.find(query).upsert().update_one(update)

    def reload(self):
        source = ChannelStats.objects.find_one(
            time_slot = self.time_slot,
            channel   = self.channel
        )

        if source is None:
            LOGGER.warning("ChannelStats.reload() could not find a document for: channel=%s, time_slot=%s", self.channel, self.time_slot)
            #LOGGER.warning("Found instead only:")
            #for s in ChannelStats.objects():
            #    LOGGER.warning('  - %s %s', s.channel, s.time_slot)
        else:
            self.data = source.data

