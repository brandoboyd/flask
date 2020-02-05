import requests
import threading
import time
from collections import deque
from Queue import Empty
from solariat_bottle.daemons.exc import ApplicationError, FeedAPIError, \
    InfrastructureError, UnauthorizedRequestError
from solariat_bottle.settings import LOGGER, get_var


class RequestsClient(object):
    """FeedAPI http client"""

    authtoken = None
    authtoken_expired = set()
    lock = threading.Lock()

    def __init__(self, options=None, sleep_timeout=30, user_agent='FeedApi'):
        self.headers = {}
        self.new_session()
        self.sleep_timeout = sleep_timeout
        self.user_agent = user_agent
        self.options = options
        self.headers = {'Content-Type': 'application/json',
                        'User-Agent': self.user_agent}

    def get_authtoken(self, expired=None):
        with self.lock:
            if expired is None:
                self.__class__.authtoken_expired = set()
                if self.__class__.authtoken:
                    return self.__class__.authtoken
                return self.__gen_authtoken()

            if expired not in self.__class__.authtoken_expired:
                self.__class__.authtoken_expired.add(expired)
                return self.__gen_authtoken()
            return self.__class__.authtoken

    def __gen_authtoken(self):
        post_data = {
            'username': self.options.username,
            'password': self.options.password,
        }
        #url = '/api/v1.2/authtokens'
        url = '/api/%s/authenticate' % get_var('API_VERSION')

        while True:
            try:
                url_str = '%s%s' % (self.options.url, url)
                LOGGER.debug('Trying to authenticate using url: %s %s', url_str, self.options)
                response = self.post(
                    url_str,
                    json=post_data,
                    headers={'Content-Type': 'application/json',
                             'User-Agent': self.user_agent})
                LOGGER.debug('Got auth token: %s' % response)
            except FeedAPIError as err:
                LOGGER.warning(err, exc_info=True)
                time.sleep(self.sleep_timeout)
            else:
                if not ('token' in response or 'item' in response):
                    LOGGER.error("Bad auth response %s", response)
                    time.sleep(self.sleep_timeout)
                    continue

                if 'item' in response:
                    response = response['item']

                try:
                    authtoken = response['token'].encode('utf-8')
                except KeyError:
                    LOGGER.exception(response)
                    time.sleep(self.sleep_timeout)
                else:
                    self.__class__.authtoken = authtoken
                    return authtoken

    def new_session(self):
        self.session = requests.Session()
        self.session.headers = self.headers

    def post(self, url, data=None, json=None, **kwargs):
        from requests.compat import json as json_lib

        try:
            response = self.session.request(
                'POST', url, data=data, json=json,
                stream=False,  # return connection to pool not waiting for response
                **kwargs)
        except requests.ConnectionError as e:
            self.new_session()
            raise InfrastructureError(unicode(e))

        if response.status_code == 401:
            raise UnauthorizedRequestError(response.text)

        if response.status_code != 200:
            raise InfrastructureError(u"HTTP status: {} Response: {}".format(
                response.status_code, response.text))

        try:
            data = response.json()
        except (TypeError, json_lib.JSONDecodeError):
            raise ApplicationError(u"Bad response: {}".format(response.text))
        else:
            if not data.get('ok'):
                raise ApplicationError(data.get('error', 'Unknown Error'))
        return data

    def api_posts(self, post_data=None, number_of_retries=None):
        api_url = '/api/%s/posts' % get_var('API_VERSION')

        payload = {"serialized_to_json": True,
                   "return_response": False,
                   "post_object_data": post_data,
                   "channel": 'no',
                   "content": 'no'}
        url = '%s%s' % (self.options.url, api_url)
        return self.post_authenticated(url, json=payload, number_of_retries=number_of_retries)

    def apply_token(self, url, post_data, authtoken):
        if not ('token' in url or (post_data and 'token' in post_data)):
            return '%s?token=%s' % (url, authtoken)
        return url

    def post_authenticated(self, url, json=None, number_of_retries=None):
        assert self.options and self.options.username and self.options.password

        authtoken = None
        expired = None

        while True:
            if not authtoken:
                authtoken = self.get_authtoken(expired)
                expired = None
            auth_url = self.apply_token(url, json, authtoken)
            try:
                return self.post(auth_url, json=json)
            except ApplicationError as err:
                if str(err) == 'Auth token %s is expired' % authtoken:
                    LOGGER.info(err)
                    expired = authtoken
                    authtoken = None
                else:
                    LOGGER.exception(err)
                    break
            except UnauthorizedRequestError as err:
                LOGGER.warning(err, exc_info=True)
                expired = authtoken
                authtoken = None
            except InfrastructureError as err:
                LOGGER.exception(err)
                if number_of_retries is None:
                    time.sleep(self.sleep_timeout)
                elif isinstance(number_of_retries, int) and number_of_retries > 0:
                    number_of_retries -= 1
                else:
                    break


class FeedApiThread(threading.Thread):
    """FeedApi implementation with injectable http client,
    compatible with daemons.feedapi_old.FeedAPI
    """
    _client = None

    @property
    def client(self):
        if self._client is None:
            _client = RequestsClient(self.options, self.sleep_timeout, self.user_agent)
            self._client = _client
        return self._client

    _counter = 0
    QUIT = object()

    def __init__(self, args=(), kwargs=None):

        self.__class__._counter += 1
        threading.Thread.__init__(self, name='FeedAPI-%d' % self._counter)
        if kwargs is None:
            kwargs = {}
        self.task_queue = args[0]
        self.options = args[1]
        self.user_agent = kwargs.get('User-Agent', self.name)
        self.sleep_timeout = 30
        self._busy = False
        self._elapsed_times = deque([], 25)
        self._stopped = threading.Event()

    def stop(self):
        self._stopped.set()

    def stopped(self):
        return self._stopped.isSet()

    def run(self):
        post_data = None
        start_time = time.time()
        wait_timeout = 0.1 if get_var('ON_TEST') else 30

        while not self.stopped():
            try:
                post_data = self.task_queue.get(block=True, timeout=wait_timeout)
            except Empty:
                self.stop()
                self._busy = False
                break
            start_time = time.time()
            if post_data is self.QUIT or post_data is None or post_data == 'QUIT':
                LOGGER.debug('received QUIT signal')
                self.task_queue.task_done()
                break

            self._busy = True
            self.client.api_posts(post_data)
            self.task_queue.task_done()
            self._elapsed_times.append(time.time() - start_time)
            self._busy = False

    @property
    def average_processing_time(self):
        size = len(self._elapsed_times)
        if size > 0:
            return sum(self._elapsed_times) / (size * 1.0)
        else:
            return -1

    def is_busy(self):
        return self._busy
