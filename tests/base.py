import mock
import os
import facebook
import multiprocessing
import random
import requests
from solariat_bottle.tasks.facebook import fb_put_comment
import string
import json
import urllib
from itertools import cycle
from unittest import TestCase
from datetime import timedelta, datetime

from solariat.db.mongo       import get_connection, setup_db_connection
from solariat.utils.timeslot import now
from solariat.decorators     import run_once

from solariat_bottle              import settings
from solariat_bottle.settings     import LOGGER, get_var
from solariat_bottle.utils import facebook_driver
from solariat_bottle.utils.logger import get_tango_handler
from solariat_bottle.tasks        import io_pool
from solariat_bottle.jobs.manager import manager, jobs_config

from solariat_bottle.tests import TEST_DB, SA_TYPES
from solariat_bottle.app import get_api_url
from solariat_bottle.api import base
from solariat_bottle.db.account import Account
from solariat_bottle.db.api_auth import ApplicationToken
from solariat_bottle.db.events.event_type import StaticEventType
from solariat_bottle.db.channel.twitter import TwitterChannel
from solariat_bottle.db.user import User, set_user
from solariat_bottle.scripts import indexctl
from solariat_bottle.scripts.reset_stats import do_it

from solariat_bottle.utils.pricing_packages import ensure_pricing_packages
from solariat_pool.db_utils import COLLECTION_NAME as RPC_COLLECTION

# register end-points
from solariat_bottle import commands, views, restapi
base, commands, views, restapi  # to disable pyflakes warnins

from ..integration.angel import restapi
restapi  # to disable pyflakes warning

from solariat_bottle.db.roles import ADMIN

# For schema manipulation for default schema for agent and customer
from solariat.db.abstract import (
    ObjectId, DBRef,
    KEY_NAME, KEY_TYPE, KEY_EXPRESSION, TYPE_INTEGER,
    TYPE_STRING, TYPE_BOOLEAN, TYPE_LIST, TYPE_DICT, TYPE_TIMESTAMP, TYPE_OBJECT, TYPE_REFERENCE)
from solariat_bottle.schema_data_loaders.base import SchemaProvidedDataLoader


def get_schema_config(data):
    """Returns schema config from sample data"""
    TYPE_MAP = {
        float: TYPE_INTEGER,
        int: TYPE_INTEGER,
        long: TYPE_INTEGER,
        str: TYPE_STRING,
        unicode: TYPE_STRING,
        dict: TYPE_DICT,
        list: TYPE_LIST,
        bool: TYPE_BOOLEAN,
        ObjectId: TYPE_OBJECT,
        DBRef: TYPE_REFERENCE
    }

    schema = []
    for field, value in data.viewitems():
        schema.append({
            KEY_NAME: field,
            KEY_TYPE: TYPE_MAP.get(type(value), TYPE_STRING),
            # KEY_EXPRESSION: field,
        })
    return schema


def setup_customer_schema(user, extra_schema=[]):
    from solariat_bottle.db.schema_based import KEY_IS_ID

    schema = list()
    schema.extend(extra_schema)
    schema.append({
        KEY_NAME: 'phone',
        KEY_TYPE: TYPE_STRING,
        KEY_IS_ID: True,
        # KEY_EXPRESSION: 'phone',
        })
    try:
        schema_entity = user.account.customer_profile.create(user, SchemaProvidedDataLoader(schema))
        schema_entity.update_schema(schema_entity.discovered_schema)
    except:
        schema_entity = user.account.customer_profile._get()
        schema_entity.update_schema(schema)
    schema_entity.apply_sync()
    schema_entity.accept_sync()


def setup_agent_schema(user, extra_schema=[]):
    from solariat_bottle.db.schema_based import KEY_IS_ID

    schema = list()
    schema.extend(extra_schema)
    schema.append({
        KEY_NAME: 'name',
        KEY_TYPE: TYPE_STRING,
        # KEY_EXPRESSION: 'name',
        })
    schema.append({
        KEY_NAME: 'skills',
        KEY_TYPE: TYPE_DICT,
        # KEY_EXPRESSION: 'skills',
        })
    schema.append({
        KEY_NAME: 'attached_data',
        KEY_TYPE: TYPE_DICT,
        # KEY_EXPRESSION: 'skills',
        })
    schema.append({
        KEY_NAME: 'date_of_birth',
        KEY_TYPE: TYPE_STRING,
        # KEY_EXPRESSION: 'date_of_birth',
        })
    schema.append({
        KEY_NAME: 'date_of_hire',
        KEY_TYPE: TYPE_STRING,
        # KEY_EXPRESSION: 'date_of_hire',
        })
    schema.append({
        KEY_NAME: 'gender',
        KEY_TYPE: TYPE_STRING,
        # KEY_EXPRESSION: 'gender',
        })
    schema.append({
        KEY_NAME: 'location',
        KEY_TYPE: TYPE_STRING,
        # KEY_EXPRESSION: 'location',
        })
    schema.append({
        KEY_NAME: 'native_id',
        KEY_TYPE: TYPE_STRING,
        # KEY_EXPRESSION: 'native_id',
        })
    schema.append({
        KEY_NAME: 'id',
        KEY_TYPE: TYPE_OBJECT,
        KEY_IS_ID: True,
        # KEY_EXPRESSION: 'id',
        })
    schema.append({
        KEY_NAME: 'on_call',
        KEY_TYPE: TYPE_BOOLEAN,
    })
    try:
        schema_entity = user.account.agent_profile.create(user, SchemaProvidedDataLoader(schema))
        schema_entity.update_schema(schema_entity.discovered_schema)
    except:
        schema_entity = user.account.agent_profile._get()
        schema_entity.update_schema(schema)
    schema_entity.apply_sync()
    schema_entity.accept_sync()

@run_once
def init_task_pool():
    from solariat_bottle.tasks import io_pool
    io_pool.initialize()

def more_like_post(post, channel):
    from ..utils.post import more_like_post as mlp
    return [p for p in mlp(post, channel)
            if p.id != post.id]


def content_gen(keywords=[], base_content=""):
    #keywords = ['test', '#test', 'Test', '#teST']
    keyword = cycle(keywords)

    while True:
        content = base_content or ''.join(random.choice(string.ascii_letters) for i in xrange(40))
        if not keywords:
            yield content
        else:
            yield "%s %s" % (content, keyword.next())


def fake_status_id():
    return "fake%s" % random.random()


def fake_twitter_url(screen_name='screen_name', status_id=None):
    status_id = status_id or fake_status_id()
    url = "http://twitter.com/%s/statuses/%s" % (screen_name, status_id)
    return url


def datasift_date_format(d):
    from solariat_bottle.db.post.twitter import DATE_FORMAT

    return d.strftime(DATE_FORMAT) + ' +0000'


class GhostPost(object):
    def __init__(self, channels=None, content=None, speech_acts=None, status='assigned'):
        if channels == None:
            channels = []
        if content == None:
            content = 'Nothing doing'
        if speech_acts == None:
            speech_acts = []

        from datetime import datetime
        self.created             = datetime.now()
        self.created_at          = self.created
        self.channels            = channels
        self.content             = content
        self.speech_acts         = speech_acts
        self.channel_assignments = {}
        self.id = str(self.created)

        for channel in channels:
            self.channel_assignments[str(channel)] = status


@run_once
def reset_db():
    # Run this once so that collections are totally reset and indexes applied
    setup_db_connection({"DB_NAME": TEST_DB, "TEST_DB_NAME": TEST_DB})
    db = get_connection()

    for coll_name in db.collection_names():
        if coll_name != RPC_COLLECTION and not coll_name.startswith('system.'):
            coll = db[coll_name]
            coll.drop()

    LOGGER.info("Creating indexes...")
    indexctl.put_indexes([], True)

class BaseCase(TestCase):

    def setUp(self):
        assert get_var('APP_MODE') == 'test', \
            "Attempt to run test in '{}' app mode.".format(get_var('APP_MODE'))

        reset_db()

        self.db = get_connection()

        for coll_name in self.db.collection_names():
            if coll_name != RPC_COLLECTION and not coll_name.startswith('system.'):
                coll = self.db[coll_name]
                if coll.options().get('capped'):
                    coll.drop()
                else:
                    if coll_name.startswith('dataset') or coll_name.startswith('agent_profile') or coll_name.startswith('customer'):
                         # Drop custom collections
                        coll.drop()
                    elif coll.count():
                        # Remove rows
                        coll.remove({})

        settings.DEBUG             = False
        settings.ON_TEST           = True
        settings.EVENT_LOG_ENABLED = False
        settings.TESTING           = True
        settings.SECRET_KEY = os.urandom(32).encode('base64')  # test session
        settings.INBOUND_SPAM_LIMIT = 30
        settings.ENFORCE_API_HTTPS = True
        settings.HOST_DOMAIN       = "http://127.0.0.0:3031"

        # reinitialize mail sender to pick up testing config
        from solariat_bottle.app import app, MAIL_SENDER
        MAIL_SENDER.init_app(app)

        if os.environ.get('ACTOR_NUM_OVERFLOW'):
            from solariat_bottle.db.sequences import NumberSequences
            NumberSequences.objects.coll.find_and_modify(
                {'name': 'ActorCounter'},
                {'$set': {'_next': 2 ** 24}},
                upsert=True,
                new=True)
        # make sure persistent <User> instance don't have any cached refs
        get_tango_handler().user.clear_ref_cache()

        init_task_pool()

        ensure_pricing_packages()
        self.account = Account.objects.create(name="TEST-ACCOUNT")
        self.email = 'nobody@solariat.com'
        self.password = '12345'
        self.user = self._create_db_user(
            email    = self.email,
            password = self.password,
            account  = self.account,
            roles    = [ADMIN],
        )
        self._create_static_events(self.user)
        self.channel = TwitterChannel.objects.create_by_user(
            self.user, title='TestChannel_Old',
            type='twitter', intention_types=SA_TYPES)

        self.channel.add_perm(self.user)
        self._post_last_created = now()
        set_user(self.user)

    def tearDown(self):
        if get_var('TEST_STAT_RESET', False):
            to_date = now()
            from_date = to_date - timedelta(days=90)
            exceptions = get_var('EXCEPTED_RESET_CASES', [])
            test_name = self.__class__.__name__ + '.' + self._testMethodName
            if test_name not in exceptions:
                try:
                    for account in Account.objects():
                        do_it(test_mode=True, raise_on_diffs=True, account_name=account.name,
                              to_date=to_date, from_date=from_date)
                except Exception, ex:
                    self.fail(ex)
        TestCase.tearDown(self)

    patches = {}

    @classmethod
    def setUpClass(cls):
        super(BaseCase, cls).setUpClass()

        patch_module_methods = [
            # remote calls to Twitter
            ('solariat_bottle.tasks.twitter', ['tw_count']),
            # remote calls to Fbot
            ('solariat_bottle.utils.facebook_extra', ['reset_fbot_cache']),
            ('solariat_bottle.db.channel.base', ['reset_fbot_cache'])
        ]
        for module_name, methods in patch_module_methods:
            module = __import__(module_name, fromlist=[module_name.rsplit('.', 1)[1]])
            for method in methods:
                patcher = mock.patch.object(module, method)
                patcher.start()
                cls.patches[module_name + '.' + method] = patcher

    @classmethod
    def tearDownClass(cls):
        for patcher in cls.patches.viewvalues():
            patcher.stop()
        super(BaseCase, cls).tearDownClass()

    @property
    def channel_id(self):
        "Return str of self.channel.id"
        return str(self.channel.id)

    def assertIn(self, candidate, items):
        self.assertTrue(candidate in items)

    def assertNotIn(self, candidate, items):
        self.assertFalse(candidate in items)

    def _create_db_user(self, email='nobody@solariat.com',
                        password='12345',
                        account=None,
                        roles=None,
                        **kw):
        if roles is None and not kw.get('is_superuser', False):
            raise RuntimeError("A user without a single role should never exist!")

        from ..db.user import User
        from ..db.account import Account

        u = User.objects.create(email=email,
                                password=password,
                                user_roles=roles,
                                **kw)
        if account:
            if isinstance(account, basestring):
                account = Account.objects.get_or_create(name=account)
            account.add_perm(u)
        return u

    def _create_static_events(self, user):
        return StaticEventType.generate_static_event_types(user)

    def _create_db_landing_page(self, url):
        from ..db.lpage import LandingPage, WeightedContentField
        return LandingPage.objects.create_by_user(
            self.user,
            url=url,
            weighted_fields = [WeightedContentField(
                    name=url, value=url)]
            )


    def _create_db_post(self,
                        content=None,
                        channel=None,
                        channels=None,
                        demand_matchables=False, **kw):
        from ..db.post.utils import factory_by_user
        from solariat.utils.hidden_proxy import unwrap_hidden

        if channel is None:
            channel = self.channel
        if channels is None:
            channels = [channel]

        from solariat_bottle.db.channel.base import Channel
        if not isinstance(channel, Channel):
            channel = Channel.objects.get(channel)

        if 'lang' not in kw or not kw['lang']:
            # posts are english by default;
            # Note: set lang=auto for autodetect
            kw['lang'] = 'en'

        user = kw.pop('user', None) or self.user
        if not ('_created' in kw or
                ('twitter' in kw and 'created_at' in kw['twitter']) or
                ('facebook' in kw and 'created_at' in kw['facebook'])):
            _created = now()
            minimal_interval = timedelta(milliseconds=1)
            if _created - self._post_last_created < minimal_interval:
                _created = self._post_last_created = _created + minimal_interval
            kw['_created'] = _created
        if content:
            kw['content'] = unwrap_hidden(content)
        post = factory_by_user(user, channels=channels, **kw)

        return post

    def _create_tweet(self,
                      content,
                      channel=None,
                      channels=None,
                      demand_matchables=False,
                      in_reply_to=None,
                      **kw):
        from solariat.utils import timeslot

        status_id = fake_status_id()
        post_data = {
            'twitter': {
                'id': status_id,
                'created_at': kw.get('_created', None) or timeslot.now(),
                'text': content
            }
        }
        post_data.update(kw)
        if in_reply_to and hasattr(in_reply_to, 'native_id'):
            post_data['twitter']['in_reply_to_status_id'] = in_reply_to.native_id
        return self._create_db_post(content,
                                    channel=channel,
                                    channels=channels,
                                    demand_matchables=demand_matchables,
                                    **post_data)

    def setup_jobs_transport(self, transport):
        LOGGER.debug("Updating jobs transport from {} to {}".format(jobs_config.transport, transport))
        jobs_config.transport = transport
        manager._configure(jobs_config, drop_registry_cache=False)
        LOGGER.debug("Registered Jobs after update:\n{}".format(manager.registry.registry))
        return manager


class RestCase(BaseCase):
    "Case for testing REST API"

    app_key = None
    version = None  # Set the API version for the whole test case

    def setUp(self):
        BaseCase.setUp(self)

        from solariat_bottle.app import app
        self.client = app.test_client()

        self.auth_token = self.get_token()

    def get_token(self, email=None, password=None):
        if not email or (email and not password):
            email = self.email
            password = self.password
        user = User.objects.get(email=email)
        self._create_app_key(user)
        post_data = {'username': email, 'password': password, 'api_key': self.app_key}
        resp = self.client.post("/api/%s/authenticate" % get_var('API_VERSION'),
                                data=json.dumps(post_data),
                                content_type="application/json",
                                base_url='https://localhost')
        data = json.loads(resp.data)
        self.assertTrue('token' in data, "Got auth response data: " + str(data))
        return data['token']

    def _create_app_key(self, user=None):
        # We don't want to do this through the API for now. No use case for that
        if not user:
            user = User.objects.get(email=self.email)
        if self.app_key is None:
            key = ApplicationToken.objects.request_by_user(user, app_type=ApplicationToken.TYPE_ACCOUNT)
            key.status = ApplicationToken.STATUS_VALID
            key.save()
            self.app_key = key.app_key

    def _handle_http_response(self, response):
        "JSON decode, raise RuntimError if any issue"
        try:
            resp = json.loads(response.data)
            if not resp.get('ok', None):
                LOGGER.error(resp.get('error', 'unknown error'))
            return resp
        except ValueError:
            LOGGER.error( "Could not decode %s" % response.data)
            return {'ok': False}

    def _get_version(self, version=None):
        return version or self.version or get_var('API_VERSION')

    def do_get(self, path, version=None, **kw):
        "Emulate GET request"

        kw['token'] = self.auth_token

        path = get_api_url(path, version=self._get_version(version=version))
        if '?' in path:
            path += '&'
        else:
            path +='?'
        base_url = kw.pop('base_url', 'https://localhost')
        path += urllib.urlencode(kw)

        LOGGER.debug(
            "Performing GET with %s" % path)

        return self._handle_http_response(
            self.client.get(path, base_url=base_url))

    def do_post(self, path,  wrap_response=True, version=None, **kw):
        "Emulate POST request"
        path = get_api_url(path, version=self._get_version(version)) + '?token=%s' % self.auth_token
        base_url = kw.pop('base_url', 'https://localhost')
        data = json.dumps(kw)

        LOGGER.debug("Performing POST to %s with %s" % (path, data))
        response = self.client.post(path, data=data, base_url=base_url, content_type='application/json')
        if wrap_response:
            return self._handle_http_response(response)
        else:
            return response

    def do_put(self, path,  version=None, **kw):
        "Emulate POST request"
        path = get_api_url(path, version=self._get_version(version)) + '?token=%s' % self.auth_token
        base_url = kw.pop('base_url', 'https://localhost')
        data = json.dumps(kw)

        LOGGER.debug(
            "Performing PUT to %s with %s" % (
                path, data))

        return self._handle_http_response(
            self.client.put(
                path,
                data=data,
                base_url=base_url,
                content_type='application/json'))

    def do_delete(self, path, wrap_response=True, version=None, **kw):
        "Emulate DELETE"
        path = get_api_url(path, version=self._get_version(version)) + '?token=%s' % self.auth_token
        base_url = kw.pop('base_url', 'https://localhost')
        data = json.dumps(kw)

        LOGGER.debug(
            "Performing DELETE to %s with %s" % (
                path, data))

        response = self.client.delete(
            path,
            data=data,
            base_url=base_url,
            content_type='application/json')

        if wrap_response:
            return self._handle_http_response(response)
        else:
            return response


class MainCaseSimple(RestCase):
    "RestCase.  NO ES indexes setup"
    def setUp(self):
        RestCase.setUp(self)

        self.url = 'http://www.solariat.com'

        settings.MATCHABLE_INDEX_NAME    = 'test_matchableer'
        settings.MATCHABLE_DOCUMENT_NAME = 'test_matchable'


class MainCase(RestCase):
    "RestCase + ES indexes setup"
    def setUp(self):
        RestCase.setUp(self)

        self.url = 'http://www.solariat.com'

class UIMixin(object):

    def login(self, email=None, password=None, user=None):
        user  = user  or self.user
        email = email or user.email
        password = password or '12345'
        return  self.client.post('/login',
                                 data = dict(email=email, password=password),
                                 follow_redirects = True)

    def logout(self):
        return self.client.get('/logout',
                               follow_redirects = True)

    def _get(self, url, data_dict, expected_result=True, expected_code=200):
        return self._submit('GET', url, data_dict, expected_result, expected_code)

    def _post(self, url, data_dict, expected_result=True, expected_code=200):
        return self._submit('POST', url, data_dict, expected_result, expected_code)

    def _delete(self, url, data_dict, expected_result=True, expected_code=200):
        return self._submit('DELETE', url, data_dict, expected_result, expected_code)

    def _put(self, url, data_dict, expected_result=True, expected_code=200):
        return self._submit('PUT', url, data_dict, expected_result, expected_code)

    def _submit(self, method, url, data_dict, expected_result=True, expected_code=200):
        if method  == 'GET':
            resp = self.client.get(url,
                                   data=json.dumps(data_dict),
                                   content_type='application/json')
        elif method  == 'POST':
            resp = self.client.post(url,
                                    data=json.dumps(data_dict),
                                    content_type='application/json')
        elif method  == 'PUT':
            resp = self.client.put(url,
                                    data=json.dumps(data_dict),
                                    content_type='application/json')
        else:
            resp = self.client.delete(url,
                                      data=json.dumps(data_dict),
                                      content_type='application/json')

        self.assertEqual(resp.status_code, expected_code)
        data = json.loads(resp.data)
        self.assertEqual(data['ok'], expected_result, resp.data)
        return data


class UICaseSimple(MainCaseSimple, UIMixin):
    "WEB UI test. NO ES indexes setup"
    def setUp(self):
        MainCaseSimple.setUp(self)


class UICase(MainCase, UIMixin):
    "WEB UI test"
    def setUp(self):
        MainCase.setUp(self)


class FacebookAccessException(Exception):
    pass


class BaseFacebookIntegrationTest(BaseCase):

    app_id = "1436996019897694"
    app_secret = "8cbdb2ba7cd4e0c6a597e63a44ed0044"
    app_token = ('%s|%s') % (app_id, app_secret)
    permissions = 'publish_actions,read_stream'
    _test_users_url = "https://graph.facebook.com/v2.2/%s/accounts/test-users?permissions=%s&access_token=%s" % \
               (app_id, permissions, "%s|%s"%(app_id, app_secret))

    @classmethod
    def setUpClass(cls):
        super(BaseFacebookIntegrationTest, cls).setUpClass()
        cls.__users = None
        response = requests.get(cls._test_users_url).json()

        if 'error' in response:
            raise FacebookAccessException(response['error'])

        existing_users = response['data']
        if existing_users:
            cls.__default_user = existing_users[0]
        else:
            data = dict(permissions=cls.permissions,
                        installed=True,
                        access_token="%s|%s" % (cls.app_id, cls.app_secret))
            cls.__default_user = requests.post(cls._test_users_url,
                                               data=json.dumps(data)).json()
        cls.__data_to_delete = []

    def _get_app_token(self):
        return  self.app_token

    def _get_second_id_part(self, id):
        return id.split('_')[1]

    def _get_object(self, user, id):
        graph = facebook_driver.GraphAPI(user['access_token'], version='2.2')
        return graph.get_object(id)

    def _get_test_users(self):
        url =  "https://graph.facebook.com/v2.2/%s/accounts/test-users?access_token=%s" % \
               (self.app_id, self._get_app_token())

        if self.__users is None:
            self.__users = (requests.get(url)).json()['data']

        return self.__users

    def _get_all_posts(self, user, target):
        graph = facebook_driver.GraphAPI(user['access_token'])
        posts = graph.get_object('%s/posts' % target)['data']
        return posts

    @classmethod
    def create_new_user(cls):
        data = dict(permissions=['publish_actions', 'read_stream'],
                    installed=True,
                    access_token="%s|%s" % (cls.app_id, cls.app_secret))
        user = requests.post("https://graph.facebook.com/v2.2/%s/accounts/test-users" % cls.app_id,
                             data=data).json()
        LOGGER.info("Created user " + str(user))
        return user

    @classmethod
    def remove_fb_user(cls, user):
        requests.delete('https://graph.facebook.com/v2.2/%s/accounts/test-users?access_token=%s&uid=%s'
                        %(cls.app_id, cls.app_token, user['id']))
        #remove user
        requests.delete("https://graph.facebook.com/v2.0/%s?access_token=%s"
                        %(user['id'], cls.app_token))

    @property
    def default_user(self):
        return self.__default_user

    def post_to_user(self, user):
        graph = facebook_driver.GraphAPI(user['access_token'])
        default_data = "this is just a test post which is made at %s" % datetime.utcnow()
        post = graph.put_wall_post(default_data)
        self.__data_to_delete.append((user['access_token'], post))
        return post

    def comment_post(self, user, post):
        default_data = "this is just a test comment which is made at %s" % datetime.utcnow()
        # Hack in order to post from passed in user
        assert self.channel.facebook_access_token
        previous_token = self.channel.facebook_access_token
        self.channel.facebook_access_token = user['access_token']
        self.channel.save()
        comment = fb_put_comment(self.channel, post['id'], default_data)
        self.channel.facebook_access_token = previous_token
        self.channel.save()
        return comment

    # Re-using same user, no need to delete / recreate each time
    # @classmethod
    # def tearDownClass(cls):
    #     if cls.__default_user is not None:
    #         id = cls.__default_user['id']
    #         #dissassociate user form app
    #         requests.delete('https://graph.facebook.com/v2.0/%s/accounts/test-users?access_token=%s&uid=%s'
    #                         %(cls.app_id, cls.app_token, id))
    #         #remove user
    #         requests.delete("https://graph.facebook.com/v2.0/%s?access_token=%s"
    #                         %(cls.__default_user['id'], cls.app_token))


class ProcessPool(object):
    def __init__(self, proc_num=multiprocessing.cpu_count()):
        self.proc_num = proc_num

    def map(self, f, iterables, proc_num=None):
        nprocs = proc_num or self.proc_num
        q_in = multiprocessing.Queue(1)
        q_out = multiprocessing.Queue()

        def fun(f, q_in, q_out):
            while True:
                i, x = q_in.get()
                if i is None:
                    break
                q_out.put((i, f(x)))

        proc = [multiprocessing.Process(
            target=fun,
            args=(f, q_in, q_out)) for _ in range(nprocs)]
        for p in proc:
            p.daemon = True
            p.start()

        sent = [q_in.put((i, x)) for i, x in enumerate(iterables)]
        [q_in.put((None, None)) for _ in range(nprocs)]
        res = [q_out.get() for _ in range(len(sent))]
        [p.join() for p in proc]
        return [x for i, x in sorted(res)]
