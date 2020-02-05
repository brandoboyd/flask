'''
This should play the same role that speech act plays for posts.

Make it easier to filter responses based on tags assigned and the
date of the latest post with a given tag assignment.

'''
from solariat.db.abstract import Document
from .channel.base import Channel
from solariat.db.fields import (
    NumField, ObjectIdField, StringField,
    ListField, ReferenceField, DateTimeField
)
from solariat.utils.timeslot import datetime_to_timeslot


def _create_response_tag(response, post, tag):
    create_args = dict(response_id=response.id,
                           channel=response.channel.id,
                           post=post.id,
                           tag=tag.id,
                           assignee=response.assignee,
                           post_date=datetime_to_timeslot(post.created_at, 'hour'),
                           status=response.status,
                           intention_name=response.intention_name,
                           intention_confidence=response.intention_confidence,
                           punks=response.punks,
                           starred=response.starred,
                           message_type=response.message_type,
                           relevance=response.relevance,
                           actionability=response.actionability,
                           skipped_list=response.skipped_list)
    r_t = ResponseTag(**create_args)
    r_t.save()

def handle_add_post(response, post):
    """
    Handle the case where a new post is added to a response object.
    """
    for tag in post.accepted_smart_tags:
        # If there is a previous response/tag assignment remove it, since this
        # just became the latest one.
        try:
            r_t = ResponseTag.objects.get(response_id=response.id, tag=tag.id)
            r_t.delete()
        except ResponseTag.DoesNotExist:
            pass
        _create_response_tag(response, post, tag)

def handle_remove_tag(response, post, tag):
    """
    When we remove a tag from a post, if that was the latest one
    then we need to search for a previous one (if exists). Otherwise
    nothing to do.
    """
    try:
        r_t = ResponseTag.objects.get(response_id=response.id, tag=tag.id,
                                      post=post.id)
        r_t.delete()
    except ResponseTag.DoesNotExist:
        pass
    for n_post in reversed(response.posts):
        if tag in n_post.accepted_smart_tags and post != n_post:
            # This is the first post which still has the given `tag`
            # applied to it.
            _create_response_tag(response, n_post, tag)
            break

def handle_add_tag(response, post, tag):
    """
    Whenever a new tag is added to a post from this response, we should
    check if this is a post which is more current than any existing response tags.
    """
    create_r_t = False
    try:
        r_t = ResponseTag.objects.get(response_id=response.id, tag=tag.id)
        if r_t.post_date < datetime_to_timeslot(post.created_at, 'hour'):
            r_t.delete()
            create_r_t = True
    except ResponseTag.DoesNotExist:
        create_r_t = True
    if create_r_t:
        _create_response_tag(response, post, tag)

def upsert_response_tags(response):
    """
    Given a response object, refresh the entire response tag that matches.

    This should be made as efficient as possible. For just destroy everything
    previously created, and recreate new entities if tag are updated.
    """
    from ..utils.post import get_service_channel
    existing = ResponseTag.objects.find(response_id=str(response.id))
    for r_t in existing:
        r_t.delete()

    done_tags = []
    for post in reversed(response.posts):
        for tag in post.accepted_smart_tags:
            if (get_service_channel(Channel.objects.get(tag.parent_channel)) == response.service_channel
                and tag.id not in done_tags):
                done_tags.append(tag.id)
                _create_response_tag(response, post, tag)


class ResponseTag(Document):

    response_id          = StringField(db_field='r_id', required=True)   # This will be the same as the response so we can quickly get them
    channel              = ReferenceField(Channel, db_field='cl')
    post                 = ObjectIdField (db_field='pt',  required=True)
    tag                  = ObjectIdField (db_field='tc',  required=True)
    assignee             = ObjectIdField(db_field='ur')
    post_date            = NumField(db_field='ts',  required=True)
    assignment_expires_at= DateTimeField(db_field='ae')
    status               = StringField(db_field='ss', default='pending')
    intention_name       = StringField(db_field='in')
    skipped_list         = ListField(ObjectIdField(), db_field='sl')
    intention_confidence = NumField(db_field='ic', default=0.0)
    punks                = ListField(StringField(), db_field='ps')
    starred              = ListField(ObjectIdField(), db_field='sd')
    message_type         = NumField(db_field='mtp', default=0)
    relevance            = NumField(db_field='re', default=0.0)
    actionability        = NumField(db_field='ay', default=0.0)

    indexes = [('response_id'), ('tag')]

