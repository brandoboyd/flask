# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_nlp.sa_labels import SATYPE_TITLE_TO_ID_MAP, ALL_INTENTIONS
from solariat_nlp.utils.topics import get_largest_subtopics

from solariat.db import fields
from solariat.utils.timeslot import datetime_to_timeslot
from .channel_hot_topics import ChannelHotTopics


def update_stats(response):
    if not response or not response.post:
        return

    channels = list(response.post.channels)

    if response.channel:
        channels.append(response.channel.id)

    for channel_id in set(channels):
        _update_stats(response, channel_id)

def _update_stats(response, channel_id, n=1):
    #TODO: FIX
    return
    post = response.post
    timeslots = dict(
        (level, datetime_to_timeslot(post.created, level))
        for level in ('day','month')
    )

    def increment(topic, intention_id, is_leaf=True):
        """ Recursively increments stats for topic and all its parents
        """
        for level, timeslot in timeslots.items():
            ResponseTermStats.increment(
                channel_id   = channel_id,
                topic        = topic,
                intention_id = intention_id,
                timeslot     = timeslot,
                is_leaf      = is_leaf,
                response     = response,
                n            = n
            )

        # recursive calls to also update parent stats
        for term in get_largest_subtopics(topic):
            assert term, 'topic=%r, term=%r' % (topic, term)
            increment(term, intention_id, is_leaf=False)


    for sa in response.post.speech_acts:
        if sa['intention_type'] == 'DISCARDED':
            continue
        intention_id = SATYPE_TITLE_TO_ID_MAP[sa['intention_type']]

        for topic in sa['intention_topics']:
            assert topic
            increment(topic, intention_id, is_leaf=True)


class ResponseTermStats(ChannelHotTopics):
    post           = fields.ObjectIdField(db_field="pt")
    response_types = fields.ListField(fields.StringField(), db_field="rt")

    @classmethod
    def increment(cls, channel_id=None, topic=None, intention_id=None, timeslot=None,
                  is_leaf=True, response=None, n=1, **kw):
        #TODO: FIX
        return
        hashed_parents = map(hash, get_largest_subtopics(topic))

        # --- ALL intentions stats ---
        stats = cls.objects.find_one(
            time_slot    = timeslot,
            channel      = channel_id,
            intention_id = ALL_INTENTIONS.oid,
            topic        = topic,
        )
        if not stats:
            stats = cls.objects.create(
                time_slot      = timeslot,
                channel        = channel_id,
                intention_id   = ALL_INTENTIONS.oid,
                topic          = topic,
                hashed_parents = hashed_parents,
                post           = response.post.id,
                response_types = response.get_filter_types(),
            )
        stats.inc_term_count(n=n)
        if is_leaf:
            stats.inc_topic_count(n=n)
        stats.upsert()

        # --- intention stats ---
        stats = cls.objects.find_one(
            time_slot    = timeslot,
            channel      = channel_id,
            intention_id = intention_id,
            topic        = topic,
        )
        if not stats:
            stats = cls.objects.create(
                time_slot      = timeslot,
                channel        = channel_id,
                intention_id   = intention_id,
                topic          = topic,
                hashed_parents = hashed_parents,
                post           = response.post.id,
                response_types = response.get_filter_types(),
            )
        stats.inc_term_count(n=n)
        if is_leaf:
            stats.inc_topic_count(n=n)
        stats.upsert()

        return stats

