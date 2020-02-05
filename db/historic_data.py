""" Specific models required in order to make loading historic data for a given channel easier """
import json
from solariat.exc.base import AppException
from solariat_bottle.tasks.facebook import fb_process_subscription
from solariat_bottle.tasks.twitter import tw_process_historic_subscription
from solariat_bottle.db.channel.facebook import FacebookServiceChannel

from solariat.db import fields
from solariat.db.abstract import Document
from solariat_bottle.daemons.helpers import datasift_to_post_dict, \
    twitter_dm_to_post_dict, twitter_status_to_post_dict
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.utils.stateful import TaskState
from werkzeug.utils import cached_property


SUBSCRIPTION_PENDING = 'pending'
SUBSCRIPTION_CREATED = 'created'
SUBSCRIPTION_RUNNING = 'running'
SUBSCRIPTION_FINISHED = 'finished'
SUBSCRIPTION_ERROR = 'error'
SUBSCRIPTION_STOPPED = 'stopped'
SUBSCRIPTION_WAITING_LIMITS_RESET = 'waiting_limits_reset'

STATUS_CHOICES = (SUBSCRIPTION_CREATED, SUBSCRIPTION_PENDING, SUBSCRIPTION_RUNNING,
                  SUBSCRIPTION_FINISHED, SUBSCRIPTION_ERROR, SUBSCRIPTION_STOPPED,
                  SUBSCRIPTION_WAITING_LIMITS_RESET)

STATUS_ACTIVE = {SUBSCRIPTION_CREATED, SUBSCRIPTION_PENDING, SUBSCRIPTION_RUNNING,
                 SUBSCRIPTION_WAITING_LIMITS_RESET}
STATUS_RESUMABLE = {SUBSCRIPTION_ERROR, SUBSCRIPTION_STOPPED}


class BaseHistoricalSubscription(Document):
    collection = 'BaseHistoricalSubscription'
    allow_inheritance = True

    channel_id = fields.ObjectIdField(db_field='cid')
    status = fields.StringField(db_field='sts', choices=STATUS_CHOICES)
    from_date = fields.DateTimeField(db_field='fd')
    to_date = fields.DateTimeField(db_field='td')
    created_by = fields.ReferenceField('User', db_field='cb')

    indexes = [('channel_id',)]

    def __repr__(self):
        return "<Historic subscription: id:%s, status:%s, from_date:%s, to_date:%s>" % (
            self.id, self.status, self.from_date, self.to_date
        )

    @cached_property
    def channel(self):
        return Channel.objects.find_one(self.channel_id)

    @cached_property
    def service_channel(self):
        from solariat_bottle.utils.post import get_service_channel

        if not self.channel:
            return None

        return get_service_channel(self.channel)

    @cached_property
    def outbound_channel(self):
        if not self.channel:
            return None

        try:
            return self.channel.get_outbound_channel(self.created_by)
        except AppException:
            return None

    def is_active(self):
        return self.status in STATUS_ACTIVE

    def get_progress(self):
        pass

    @property
    def is_stoppable(self):
        return False

    @property
    def is_resumable(self):
        return False

    def to_dict(self, fields2show=None):
        doc = super(BaseHistoricalSubscription, self).to_dict(fields2show)
        doc.update({"type": self.__class__.__name__,
                    "is_active": self.is_active(),
                    "is_stoppable": self.is_stoppable,
                    "progress": self.get_progress()})
        return doc

    @classmethod
    def validate_recovery_range(cls, from_date, to_date):
        pass


class TwitterRestHistoricalSubscription(BaseHistoricalSubscription):

    def process(self):
        if not self.channel:
            from solariat_bottle.settings import LOGGER

            LOGGER.error("Subscription %s: channel is broken" % self)
            return None

        # tw_process_historic_subscription.ignore(self)
        tw_process_historic_subscription(self)

    def is_active(self):
        return self.status in STATUS_ACTIVE

    @property
    def is_stoppable(self):
        return True

    @property
    def is_resumable(self):
        return self.status in STATUS_RESUMABLE

    def stop(self):
        self.update(status=SUBSCRIPTION_STOPPED)
        return True

    def get_progress(self):
        """result = {
            'status': SUBSCRIPTION_RUNNING,
            'fetchers': {
                'progress': 85,
                'items': [
                    {
                        'type': DM_REQUEST,
                        'filters': {},
                        'progress': 15,
                        'posts': 286,
                    },
                    {
                        'type': SEARCH_REQUEST,
                        'filters': {'keywords': ['one', 'two'], lang='en'},
                        'progress': 0,
                        'posts': 0,
                    },
                    {
                        'type': SEARCH_REQUEST,
                        'filters': {'keywords': ['one', 'two'], lang='und'},
                        'progress': 0,
                        'posts': 0,
                    },
                    {
                        'type': USER_REQUEST,
                        'filters': {'user_id': 'somename'},
                        'progress': 0,
                        'posts': 0,
                    },
                ]
            }
            'loader': {
                'progress': 0,
                'queued': 41,
                'processed': 45,
                'total': 160,
            }
        }"""
        from solariat_bottle.daemons.twitter.historics.historic_loader import HistoricLoader

        items = []
        progress = 0.0
        state_docs = TaskState.objects.coll.find({
            'params.subscription_id': self.id,
            'params.req_type': {'$exists': True},
        })
        for state_doc in state_docs:
            state = state_doc['state']
            params = state_doc['params']
            filters = {f:params[f] for f in ('lang', 'keywords', 'user_id') if f in params}
            items.append({
                'type': params['req_type'],
                'filters': filters,
                'progress': state.get('progress', 0),
                'posts': state.get('posts', 0),
            })
            progress += state.get('progress', 0)

        if progress > 0:
            progress /= state_docs.count()

        loader_state_doc = TaskState.objects.coll.find_one({
            'params.subscription_id': self.id,
            'params._class_': HistoricLoader.get_stateful_cls(),
        })
        loader_state = loader_state_doc and loader_state_doc['state']

        result = {
            'status': self.status,
            'fetchers': {
                'progress': round(progress),
                'items': items,
            },
            'loader': loader_state,
        }
        return result

    @classmethod
    def validate_recovery_range(cls, from_date, to_date):
        # Twitter Search API allows to send any since and until,
        # but indexes only 6-9 recent days.
        from solariat.utils.timeslot import now
        one_hour_sec = 60 * 60
        max_days = 31
        if (now() - from_date).total_seconds() > max_days * 24 * one_hour_sec:
            return "'From' date must not be earlier than %s days ago" % max_days


class FacebookHistoricalSubscription(BaseHistoricalSubscription):

    finished = fields.ListField(fields.StringField())    # Id's of objects (pages, events, groups) which already
                                                                 # handled
    actionable = fields.ListField(fields.StringField())  # id's of objects, who still need to be handled

    @property
    def _handler(self):
        return fb_process_subscription

    def get_progress(self):

        total_count = len(self.finished) + len(self.actionable)
        return round(len(self.finished)/float(total_count), 2) if total_count > 0 else 0

    def get_history_targets(self):

        channel = self.channel
        targets = [channel.facebook_handle_id]

        for page in channel.facebook_page_ids:
            targets.append(page)

        for event in channel.tracked_fb_event_ids:
            targets.append(event)

        for group in channel.tracked_fb_group_ids:
            targets.append(group)

        return targets


class HistoricalSubscriptionFactory(object):
    __mapping = {}
    __mapping[FacebookServiceChannel.__name__] = FacebookHistoricalSubscription
    __mapping[TwitterServiceChannel.__name__] = TwitterRestHistoricalSubscription

    @classmethod
    def resolve(cls, channel):
        return cls.__mapping.get(channel.__class__.__name__, None)


class QueuedHistoricData(Document):
    DATASIFT_DEFAULT = 0
    TWITTER_API_DM = 1
    SOLARIAT_POST_DATA = 2
    TWITTER_API_PUBLIC = 3

    DATA_FORMATS = (DATASIFT_DEFAULT, TWITTER_API_DM, SOLARIAT_POST_DATA)

    subscription = fields.ReferenceField(BaseHistoricalSubscription, db_field='sub')
    timestamp = fields.NumField(db_field='tsp')
    post_data = fields.StringField(db_field='pd')
    post_data_format = fields.NumField(choices=DATA_FORMATS,
                                       default=DATASIFT_DEFAULT, db_field='fmt')

    indexes = [('subscription', 'timestamp')]

    @property
    def solariat_post_data(self):
        data = json.loads(self.post_data)
        transform = {
            self.SOLARIAT_POST_DATA: lambda x: x,
            self.DATASIFT_DEFAULT: datasift_to_post_dict,
            self.TWITTER_API_DM: twitter_dm_to_post_dict,
            self.TWITTER_API_PUBLIC: twitter_status_to_post_dict
        }[self.post_data_format]
        try:
            data = transform(data)
        except KeyError:
            data['_transform_error'] = True
        return data
