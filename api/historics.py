import requests
from solariat_bottle import settings
from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.settings import get_var

import solariat_bottle.api.exceptions as exc
from solariat_bottle.api.base import ModelAPIView, api_request
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.historic_data import (SUBSCRIPTION_CREATED, STATUS_ACTIVE, HistoricalSubscriptionFactory, \
                                              BaseHistoricalSubscription)
from solariat_bottle.utils.post import get_service_channel
from solariat.utils.timeslot import now, parse_datetime
import time, datetime


class HistoricsAPIView(ModelAPIView):

    model = BaseHistoricalSubscription
    endpoint = 'historics'
    required_fields = ['channel', 'content']

    def get_channel(self, user, params):
        channel_id = params.get('channel', params.get('channel_id', None))
        try:
            channel = Channel.objects.get(channel_id)
        except Channel.DoesNotExist:
            raise exc.ResourceDoesNotExist("No channel exists for id=%s" % channel_id)

        if not channel.can_edit(user):
            # Access to create subscription is restricted to users with edit access on the channel
            exc_err = "User %s does not have access to create a new subscription for channel %s." % (user.email,
                                                                                                     channel)
            raise exc.AuthorizationError(exc_err)
        return channel

    def get_subscription(self, user, params):
        id_ = params.get('_id', params.get('id'))
        try:
            subscription = BaseHistoricalSubscription.objects.get(id_)
        except BaseHistoricalSubscription.DoesNotExist:
            raise exc.ResourceDoesNotExist("No subscription exists with id=%s" % id_)

        channel = subscription.channel
        if not channel:
            raise exc.ResourceDoesNotExist("There is no channel for this subscription")

        if not channel.can_edit(user):
            raise exc.AuthorizationError("User %s does not have access to subscription %s." %
                                         (user.email, subscription))
        return subscription

    @api_request(allow_basic_auth=True)
    def get(self, user, *args, **kwargs):
        """
        :param id: OPTIONAL, the id of the subscription you want details to

        :returns If id is passed in, the json format of the desired subscription, otherwise a list
                 with all the subscription the user has access to.

        Sample responses:

            Generic GET:
            {
              "items": [
                {
                  "status": "created",
                  "channel_id": "541aebcb31eddd1f678c2426",
                  "from_date": 1404388800,
                  "to_date": 1405252800,
                  "datasift_historic_id": null,
                  "datasift_push_id": null,
                  "id": "541aebcb31eddd1f678c242a"
                },
                {
                  "status": "created",
                  "finished": [],
                  "actionable": [],
                  "channel_id": "541aebcb31eddd1f678c242b",
                  "from_date": 1404388800,
                  "to_date": 1405252800,
                  "id": "541aebcb31eddd1f678c242e"
                }
              ],
              "ok": true
            }

            Specific GET:
            {
              "item": {
                "status": "created",
                "channel_id": "541aebcb31eddd1f678c2426",
                "from_date": 1404388800,
                "to_date": 1405252800,
                "datasift_historic_id": null,
                "datasift_push_id": null,
                "id": "541aebcb31eddd1f678c242a"
              },
              "ok": true
            }

        """
        if 'id' in kwargs or '_id' in kwargs:
            subscription = self.get_subscription(user, kwargs)
            return dict(ok=True, item=subscription.to_dict())

        elif 'channel' in kwargs or 'channel_id' in kwargs:
            channel = self.get_channel(user, kwargs)
            sc = get_service_channel(channel)
            subscriptions = BaseHistoricalSubscription.objects(channel_id=sc.id).sort(id=-1)[:10]

            return dict(ok=True,
                        items=[sub.to_dict() for sub in subscriptions],
                        has_active=any(s.is_active() for s in subscriptions))
        else:
            # List all subscriptions this user has access to
            accessible_channels = Channel.objects.find_by_user(user)
            editable_channels = [c.id for c in accessible_channels if c.can_edit(user)]
            available_subscriptions = BaseHistoricalSubscription.objects.find(channel_id__in=editable_channels)[:]
            return dict(ok=True, items=[sub.to_dict() for sub in available_subscriptions])

    @api_request(allow_basic_auth=True)
    def put(self, user, *args, **kwargs):
        if 'action' not in kwargs:
            raise exc.InvalidParameterConfiguration("Parameter 'action' is required")

        action = kwargs.get('action')
        if action not in {'stop', 'resume'}:
            raise exc.ValidationError("Invalid 'action' value")

        subscription = self.get_subscription(user, kwargs)

        if action == 'resume':
            if not subscription.is_resumable:
                return dict(ok=False, error="Subscription can not be resumed")
            subscription.process()
            return dict(ok=True, message="Subscription has been resumed", details=subscription.to_dict())

        elif action == 'stop':
            if not subscription.is_stoppable:
                return dict(ok=False, error="Subscription can not be stopped")
            try:
                result = subscription.stop()
            except Exception as e:
                error = unicode(e)
                if 'Datasift returned error' in error:
                    error = error[-error.rfind('Datasift returned error'):]
                raise exc.AppException(error)
            else:
                return dict(ok=True, message="Subscription has been stopped", details=result)

    @api_request(allow_basic_auth=True)
    def post(self, user, *args, **kwargs):
        """
        :param channel: REQUIRED, the id of the channel we want to create a historic load for
        :param from_date: REQUIRED, the start date of the load, format is '%d.%m.%Y-%H:%M:%S'
        :param to_date: REQUIRED, the end date of the load, format is '%d.%m.%Y-%H:%M:%S'

        :returns A json response, format: {ok=<True|False>, error="", item=subscription.json}

        Sample response (Twitter):
            {
              "ok": true,
              "subscription": {
                "status": "created",
                "channel_id": "541aec9731eddd1fc4507853",
                "from_date": 1404388800,
                "to_date": 1405252800,
                "datasift_historic_id": null,
                "datasift_push_id": null,
                "id": "541aec9731eddd1fc4507857"
              }
            }

        Sample response (Facebook):
            {
              "ok": true,
              "subscription": {
                "status": "created",
                "finished": [],
                "actionable": [],
                "channel_id": "541aeccd31eddd1fec5b2059",
                "from_date": 1404388800,
                "to_date": 1405252800,
                "id": "541aeccd31eddd1fec5b205c"
              }
            }
        """
        if 'channel' not in kwargs:
            exc_err = "Parameter 'channel' is required in order to create subscription."
            raise exc.InvalidParameterConfiguration(exc_err)

        channel = self.get_channel(user, kwargs)
        if 'from_date' not in kwargs:
            raise exc.InvalidParameterConfiguration("Parameter 'from_date' required")
        if 'to_date' not in kwargs:
            raise exc.InvalidParameterConfiguration("Parameter 'to_date' required")

        from_date = parse_datetime(kwargs['from_date'])
        to_date = parse_datetime(kwargs['to_date'])

        if from_date >= to_date:
            raise exc.InvalidParameterConfiguration("'From' date must be less than 'To' date")

        type = kwargs.get('type', '')
        if type == 'event' and not channel.tracked_fb_event_ids:
            raise exc.InvalidParameterConfiguration("No Events set, canceling recovery.")

        sc = get_service_channel(channel)

        if not isinstance(sc, FacebookServiceChannel):
            subscription_cls = HistoricalSubscriptionFactory.resolve(sc)
            if subscription_cls is None:
                raise exc.InvalidParameterConfiguration("Could not infer a service channel for channel %s" %
                                                        (channel.title + '<' + channel.__class__.__name__ + '>'))
            error = subscription_cls.validate_recovery_range(from_date, to_date)
            if error:
                raise exc.InvalidParameterConfiguration(error)

            if not kwargs.pop('force', False) and subscription_cls.objects.find_one(
                    channel_id=sc.id, status__in=STATUS_ACTIVE):
                raise exc.ForbiddenOperation("The recovery process is already in progress for this channel")

            subscription = subscription_cls.objects.create(
                created_by=user,
                channel_id=sc.id,
                from_date=from_date,
                to_date=to_date,
                status=SUBSCRIPTION_CREATED)
            if not get_var('APP_MODE') == 'test':
                subscription.process()

            return dict(ok=True, subscription=subscription.to_dict())
        else:
            if isinstance(kwargs['from_date'], int) and isinstance(kwargs['to_date'], int):
                from_date_str = int(kwargs['from_date'])/1000
                to_date_str = int(kwargs['to_date'])/1000
            else:
                from_date_str = from_date.strftime("%s")
                to_date_str = to_date.strftime("%s")

            url = "%s?token=%s&channel=%s&since=%s&until=%s&type=%s" % \
                  (settings.FBOT_URL + '/json/restore', settings.FB_DEFAULT_TOKEN, sc.id, from_date_str, to_date_str, type)

            from solariat_bottle.tasks import async_requests
            async_requests.ignore('get', url, verify=False, timeout=None)
            return dict(ok=True)

