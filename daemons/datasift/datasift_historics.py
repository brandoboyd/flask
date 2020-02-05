"""
Handles running a data subscription for datasift. The details of this are:

http://dev.datasift.com/docs/historics/steps

Basic steps are:

1. Compile a CSDL based on keywords / usernames
2. Hit the /historics/prepare endpoint in the Historics API with the CSDL from step 1 along with start/end dates
3. Hit the /push/create endpoint with the id returned from step 2, this actually creates the subscription
4. Hit the /historics/start endpoint to actually start the subscription

"""

import json
import urllib
import requests
from solariat_bottle.daemons.base import BaseHistoricSubscriber

from solariat_bottle.settings import LOGGER, get_var
from solariat_bottle.db.historic_data import (
    SUBSCRIPTION_FINISHED, SUBSCRIPTION_RUNNING, SUBSCRIPTION_PENDING,
    SUBSCRIPTION_CREATED, SUBSCRIPTION_ERROR, SUBSCRIPTION_STOPPED)
from solariat_bottle.scripts.datasift_sync2 import (
    datasift_compile, get_csdl_data, generate_csdl, log_csdl)
from solariat.utils.lang.support import get_lang_code, LANG_MAP


DATASIFT_ENDPOINT = get_var('DATASIFT_HISTORICS_ENDPOINT') or get_var('HOST_DOMAIN') + '/datasift'


def list_subscriptions():
    """
    List all subscriptions we have on datasift for this given host domain.
    :returns A list with all the datasift subscription in the form of a dictionaries.

    Example subscription: {u'created_at': 1407414962,
                           u'end': None,
                           u'hash': u'2bb5c8a645c444c2351c',
                           u'hash_type': u'historic',
                           u'id': u'8d3047e3cc7090887f7db3e2b470318d',
                           u'last_request': None,
                           u'last_success': None,
                           u'lost_data': False,
                           u'name': u'data_recovery',
                           u'output_params': {u'delivery_frequency': 30,
                                              u'format': u'json',
                                              u'method': u'post',
                                              u'url': u'http://50.56.112.111:3031/datasift',
                                              u'verify_ssl': u'False'},
                           u'output_type': u'http',
                           u'remaining_bytes': None,
                           u'start': 1407414962,
                           u'status': u'active',
                           u'user_id': 2490}
    """
    params = {'username': get_var('DATASIFT_USERNAME'),
              'api_key': get_var('DATASIFT_API_KEY')}
    resp = requests.get(get_var('DATASIFT_BASE_URL') + "/v1/push/get", urllib.urlencode(params))
    try:
        data = resp.json()
    except ValueError:
        raise Exception(resp)
    valid_subscriptions = []
    for entry in data.get('subscriptions', []):
        if get_var('HOST_DOMAIN') in entry.get('output_params', {}).get('url'):
            valid_subscriptions.append(entry)
    return valid_subscriptions


def clear_subscriptions():
    """
    Clear all subscriptions we have on datasift for this given host domain.
    """
    params = {'username': get_var('DATASIFT_USERNAME'),
              'api_key': get_var('DATASIFT_API_KEY')}
    existing_subs = list_subscriptions()
    for subscription in existing_subs:
        params['id'] = subscription['id']
        requests.get(get_var("DATASIFT_BASE_URL") + "/v1/push/delete", urllib.urlencode(params))


def if_datasift_historic_id(method):
    def inner_method(self, *args, **kwargs):
        if not self.subscription.datasift_historic_id:
            LOGGER.warning("Subscription %s does not have a historic id stored." % self.subscription)
            return False
        return method(self, *args, **kwargs)
    return inner_method


class DatasiftHistoricSubscriber(BaseHistoricSubscriber):

    def __init__(self, subscription, language=None):
        """
        A historic data subscriber specific for datasift.

        :param subscription: A SocialAnalytics subscription. We need to store the actual datasift
        subscription id so we can match posts passed in by datasift to the callback to a given subscription
        on our side.
        :param language: this is some CSDL specific entry.
        """
        self.subscription = subscription
        self.from_date = subscription.from_date
        self.to_date = subscription.to_date
        self.language = language

    @property
    def channel(self):
        return self.subscription.service_channel

    def compute_csdl(self):
        """
        For the given subscription/channel, compute and compile the datasift CSDL we are going to use to
        create the actual datasift description.

        :returns A complied hash of the CSDL computed for the given subscription/channel
        """
        csdl_data = get_csdl_data([self.channel.inbound_channel, self.channel.outbound_channel])
        lang_code = get_lang_code(self.language)
        if lang_code not in LANG_MAP:
            lang_code = None
        csdl_string = generate_csdl(*csdl_data, language=lang_code)
        datasift_response = datasift_compile(csdl_string)
        LOGGER.info(u"%s.compute_csdl: %s" % (
            self.__class__.__name__,
            log_csdl(csdl_data, csdl_string, datasift_response)))
        return datasift_response

    def __request(self, url, params):
        """
        A generic request for datasift
        :param params: The request parameters
        :param url: The url of the request
        :return: The response of the request
        """
        params.update({
            "username": get_var('DATASIFT_USERNAME'),
            "api_key": get_var('DATASIFT_API_KEY')})

        base_url = get_var('DATASIFT_BASE_URL')
        if not url.startswith(base_url):
            url = base_url + url

        try:
            resp = requests.get(url, urllib.urlencode(params))
            LOGGER.debug(u"url: %s\nparams: %s\nresponse: %s" % (url, params, resp))
        except:
            error_msg = "Error requesting '%s' with params '%s'" % (url, params)
            LOGGER.exception(error_msg)
            raise Exception(error_msg)
        else:
            try:
                data = resp.json()
            except:
                if resp:
                    LOGGER.info(u"Datasift response: %s" % resp)
                return resp
            else:
                if 'error' in data:
                    LOGGER.error(
                        "Datasift returned error '%s'\n"
                            "url: %s\nparams: %s" % (data['error'], url, params))
                    raise Exception(data['error'])
        return data

    @property
    def datasift_subscription_name(self):
        return "data_recovery_%s" % self.subscription.id

    def prepare_subscription_data(self, CSDL):
        """ Prepare the subsciption through the appropriate datasift API call.
        Requires at minimum a start date, end date and csdl along with the credentials.

        :param CSDL: The compiled CSDL required to start a datasift subscription

        :returns The subscription ID from datasift
        """
        from solariat.utils.timeslot import datetime_to_timestamp

        params = {"start": datetime_to_timestamp(self.from_date),
                  "end": datetime_to_timestamp(self.to_date),
                  "hash": CSDL,
                  "name": self.datasift_subscription_name,
                  "sources": 'twitter'}
        data = self.__request("/v1/historics/prepare", params)

        self.subscription.update(datasift_historic_id=data['id'])
        return data['id']

    @if_datasift_historic_id
    def subscribe_historics_data(self):
        """Next step in datasift subscription is to push create
        the actual subscription using the push/create endpoint.
        """
        params = {'historics_id': self.subscription.datasift_historic_id,
                  'name': self.datasift_subscription_name,
                  'output_type': 'http',
                  'output_params.format': 'json',
                  'output_params.method': 'post',
                  'output_params.url': DATASIFT_ENDPOINT,
                  'output_params.delivery_frequency': 60,
                  'output_params.verify_ssl': False}
        data = self.__request("/v1/push/create", params)
        # At this point, subscription is already pending and we have a datasift id.
        self.subscription.update(datasift_push_id=data['id'],
                                 status=SUBSCRIPTION_PENDING)

    @if_datasift_historic_id
    def pause_subscription(self):
        """Pause a datasift subscription."""
        params = {"id": self.subscription.datasift_historic_id}
        return self.__request("/v1/historics/pause", params)

    @if_datasift_historic_id
    def resume_subscription(self):
        """Resume a datasift subscription."""
        params = {"id": self.subscription.datasift_historic_id}
        return self.__request("/v1/historics/resume", params)

    @if_datasift_historic_id
    def stop_subscription(self):
        """Stop a datasift subscription."""
        sub = self.subscription
        historics_result = self.__request("/v1/historics/stop", {"id": sub.datasift_historic_id})
        push_result = None
        if sub.datasift_push_id:
            push_result = self.__request("/v1/push/stop", {"id": sub.datasift_push_id})
        return {"stopped": {"historics": historics_result, "push": push_result}}

    @if_datasift_historic_id
    def start_subscription(self):
        """Start the historics recovery query."""
        params = {"id": self.subscription.datasift_historic_id}
        self.__request("/v1/historics/start", params)
        self.subscription.update(status=SUBSCRIPTION_RUNNING)

    @if_datasift_historic_id
    def get_subscription_status(self):
        """Check what the status of our historics query is using the datasift API.

         :returns A dictionary entry with the global status of the subscription and a list
          with status for individual chunks.
        """
        params = {"id": self.subscription.datasift_historic_id}
        return self.__request("/v1/historics/get", params)

    def get_status(self):
        """ :return: The status of the current runner, based on the equivalent datasift status. """
        self.subscription.reload()
        if self.subscription.status in {SUBSCRIPTION_STOPPED, SUBSCRIPTION_ERROR}:
            return self.subscription.status

        status_data = self.get_subscription_status()
        LOGGER.info(status_data)
        if status_data is None or status_data is False:
            return SUBSCRIPTION_PENDING

        if status_data['status'] in ('init', 'queued', 'running'):
            chunks = ['status:' + str(dt['status']) + ', progress:' + str(dt['progress']) for dt in
                      status_data.get('chunks', [])]
            LOGGER.info("Query status is %s. Data chunks status are (%s)." % (status_data['status'], chunks))

            self.subscription.update(status_data_historics=status_data,
                                     status=SUBSCRIPTION_RUNNING)
            return SUBSCRIPTION_RUNNING

        self.subscription.update(status_data_historics=status_data,
                                 status=SUBSCRIPTION_FINISHED)
        return SUBSCRIPTION_FINISHED

    def __start_historic_load(self):
        """
        Go through all the required steps in order to create a datasift subscription.

        1. Compile a CSDL based on keywords / usernames
        2. Hit the /historics/prepare endpoint in the Historics API with the CSDL from step 1 along with start/end dates
        3. Hit the /push/create endpoint with the id returned from step 2, this actually creates the subscription
        4. Hit the /historics/start endpoint to actually start the subscription
        """
        try:
            csdl_data = self.compute_csdl()
            self.prepare_subscription_data(csdl_data['hash'])
            self.subscribe_historics_data()
            self.start_subscription()
        except Exception as e:
            LOGGER.exception('__start_historic_load')
            self.subscription.update(
                status=SUBSCRIPTION_ERROR,
                status_data_historics={"exception": unicode(e)})

    def start_historic_load(self):
        """
        Start a datasift historic load. Take into account the status of the subscription on our side.
        """
        if self.subscription.status == SUBSCRIPTION_PENDING:
            LOGGER.warning("Starting a pending subscription.")
            self.start_subscription()
        elif self.subscription.status == SUBSCRIPTION_CREATED:
            LOGGER.info("Starting new datasift subscription.")
            self.__start_historic_load()
            LOGGER.info("Historic load started successfully.")
        else:
            LOGGER.warning("This current subscription already has status: %s. Cannot start again." %
                           self.subscription.status)
            return False
