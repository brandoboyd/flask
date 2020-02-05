import unittest

from solariat.db.abstract import Document, fields

from .base import MainCase, fake_status_id
from solariat.utils.timeslot import now, TIMESLOT_EPOCH, timedelta

from solariat_bottle.utils.id_encoder import unpack_event_id

from solariat_bottle.db.user import User
from solariat_bottle.db.roles import STAFF
from solariat_bottle.db.events.event import Event
# from solariat_bottle.db.events.predictor import CSMPredictor
# from solariat_bottle.db.events.predictor import GeneralPredictor

from solariat_bottle.db.post.chat import ChatPost
from solariat_bottle.db.post.twitter import datetime_to_string
from solariat_bottle.db.post.utils import factory_by_user

from solariat_bottle.db.conversation import Conversation
from solariat_bottle.db.channel.chat import ChatServiceChannel as CSC
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.user_profiles.chat_profile import ChatProfile
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.tests.base import setup_customer_schema, setup_agent_schema, get_schema_config


class BaseEventCase(MainCase):

    def setUp(self):
        super(BaseEventCase, self).setUp()
        setup_agent_schema(self.user)
        setup_customer_schema(self.user, get_schema_config({'first_name': 'name'}))

        self.sc       = TwitterServiceChannel.objects.create_by_user(self.user, title='test chat service channel')
        self.sc.add_username('@test_username')
        self.customer = self._create_customer('Chat', 'JoeCustomer1')
        self.customer2 = self._create_customer('Chat', 'JoeCustomer2')
        self.brand    = self._create_agent('agent@genesys.com')
        AgentProfile = self.account.get_agent_profile_class()
        self.agent_profile = AgentProfile()
        self.agent_profile.save()
        self.chat_profile = ChatProfile.objects.create(native_id='BogdanNeacsa')
        self.customer.add_profile(self.chat_profile)
        # assert self.chat_profile.customer_profile.id, self.chat_profile.customer_profile.id
        # self.chat_profile.save()
        self.support_up = UserProfile.objects.upsert('Twitter', dict(screen_name='support@enterprise.com'))
        self.customer_up = UserProfile.objects.upsert('Twitter', dict(screen_name='customer@enterprise.com'))
        self.customer_up2 = UserProfile.objects.upsert('Twitter', dict(screen_name='customer2@enterprise.com'))
        self.customer_up3 = UserProfile.objects.upsert('Twitter', dict(screen_name='customer3@enterprise.com'))
        self.customer.actor_num
        self.customer2.actor_num

    def _create_customer(self, type_, name):
        CustomerProfile = self.account.get_customer_profile_class()
        actor = CustomerProfile(first_name=name)
        actor.save()
        return actor

    def _create_agent(self, email):
        AgentProfile = self.account.get_agent_profile_class()
        agent = AgentProfile.objects.create(account_id=self.account.id)
        return agent
        user = self._create_db_user(email=email, password='pass', account=self.account, roles=[STAFF])
        user.account = self.account
        user.save()
        self.sc.add_agent(user)
        self.sc.add_perm(user)
        self.sc.inbound_channel.add_perm(user)
        self.sc.inbound_channel.add_perm(user)
        return user


class EventCase(BaseEventCase):

    def _create_event_sequence(self, length, brand_involved=False, customer=None):
        '''
        Create an event sequence with length of events for this customer. If brand
        is involved then the events toggle between inbound and outbound.
        '''
        events = []
        customer = self.customer if customer is None else customer

        # Set the user in thread local storage
        from solariat_bottle.db.user import set_user
        set_user(self.user)

        for i in range(length):
            kw = {}
            if brand_involved:
                kw['is_inbound'] = True if i % 2 == 0 else False
                if i % 2 == 0:
                    kw['actor_id'] = customer.id
                else:
                    kw['actor_id'] = self.brand.id
                    kw['parent_event'] = event
                kw['channels'] = [self.sc.inbound] if i % 2 == 0 else [self.sc.outbound]
            else:
                kw['actor_id'] = customer.id
                kw['is_inbound'] = True
                kw['channels'] = [self.sc.inbound]

            event = Event.objects.create_by_user(user=self.user, **kw)
            events.append(event)
        return events

    def test_event_id_updates(self):
        class Foo(Event):
            field = fields.StringField()
            _parent_post = fields.ReferenceField('Foo', db_field='pfoo')

        foo = Foo.objects.create(_id=2 ** 66, field='test', actor_id=self.customer.actor_num)

        self.assertEqual(Foo.objects.count(), 1)
        foo.field = 'test2'
        foo.save()

        self.assertEqual(Foo.objects.count(), 1)
        foo = Foo.objects.get(2 ** 66)
        foo.field = 'test3'
        foo.save()

        foo.reload()
        self.assertEqual(foo.field, 'test3')

        foo2 = Foo.objects.create(_id=2 ** 66 + 1,
                                  field='test2',
                                  actor_id=self.customer.actor_num,
                                  _parent_post=foo)
        self.assertEqual(Foo.objects.count(), 2)
        foo2 = Foo.objects.get(2 ** 66 + 1)
        self.assertEqual(foo2.field, 'test2')
        self.assertEqual(foo2._parent_post.field, 'test3')

        foo3 = Foo.objects.create(_id=200,
                                  field='test4',
                                  actor_id=self.customer.actor_num)



    def test_customer_events(self):
        events = self._create_event_sequence(length=3)
        for event in events:
            self.assertTrue(event.actor_id, self.customer.id)
        events = [x for x in Event.objects()]
        # self.assertEqual(len(events), 3)
        for e in events:
            unpacked_actor_num, unpacked_created_at = unpack_event_id(e.id)
            self.assertEqual(e.actor.actor_num, unpacked_actor_num)
            self.assertEqual(e.created_at, unpacked_created_at)

    def test_conversation(self):
        '''
        Generate an evenet sequence as a conversation and make sure it
        has customers and agents.
        '''
        CustomerProfile = self.account.get_customer_profile_class()
        AgentProfile = self.account.get_customer_profile_class()
        events = self._create_event_sequence(length=7, brand_involved=True)

        # TODO: Figure out why it is necessary to convert these to strings. It appears to be the same
        # class but a direct comparison with isinstance does not work. Could be a limitation of the
        # dynamic class structure.
        self.assertTrue( str(type(events[0].actor)) == str(CustomerProfile),
                        "%s %s is not instance of %s" % (type(events[0].actor), events[0].actor, CustomerProfile))
        self.assertEqual(Event.objects(is_inbound=True).count(), 4)
        self.assertEqual(Event.objects(is_inbound=False).count(), 3)

    def test_several_event_episodes(self):
        # create event sequences
        event_sequence1 = self._create_event_sequence(length=7, brand_involved=True)
        event_sequence2 = self._create_event_sequence(length=5, brand_involved=True)
        event_sequence3 = self._create_event_sequence(length=9, brand_involved=True)

    def test_range_query(self):
        start_dt = now()
        self._create_event_sequence(length=2, brand_involved=True, customer=self.customer2)
        self._create_event_sequence(length=3, brand_involved=True, customer=self.customer)
        self._create_event_sequence(length=2, brand_involved=True, customer=self.customer2)
        self._create_event_sequence(length=7, brand_involved=True, customer=self.customer)
        self._create_event_sequence(length=2, brand_involved=True, customer=self.customer2)
        end_dt = now()

        count = Event.objects.range_query_count(start=start_dt, end=end_dt, customer=self.customer)
        self.assertEqual(count, 10)

        count = Event.objects.range_query_count(start=start_dt, end=end_dt, customer=self.customer2)
        self.assertEqual(count, 6)


class IdOverflowEventCase(EventCase):
    """Runs all tests from EventCase with big actor_num values"""
    def setUp(self):
        super(IdOverflowEventCase, self).setUp()
        from solariat_bottle.utils.id_encoder import EVENT_TIMESTAMP_WIDTH
        mongo_max_int_size = 64
        max_actor_num_bits = mongo_max_int_size - EVENT_TIMESTAMP_WIDTH
        overflow_num = 1 << max_actor_num_bits

        self.customer.update(actor_num=overflow_num + 1)
        self.customer2.update(actor_num=overflow_num + 2)
        self.brand.update(actor_num=overflow_num + 3)
        self.agent_profile.update(actor_num=overflow_num + 4)
        self.chat_profile.update(actor_num=overflow_num + 5)
        self.support_up.update(actor_num=overflow_num + 6)
        self.customer_up.update(actor_num=overflow_num + 7)
        self.customer_up2.update(actor_num=overflow_num + 8)
        self.customer_up3.update(actor_num=overflow_num + 9)

        self.small_int_customer = UserProfile.objects.upsert('Twitter', dict(screen_name='small_int_customer@enterprise.com'))
        self.small_int_customer.update(actor_num=42)

    def test_mongo_int(self):
        class A(Document):
            id = fields.CustomIdField()
        a = A(id=2**63 - 1)
        a.save()
        a.reload()
        self.assertEqual(a.id, 2**63 - 1)

        with self.assertRaises(Exception):
            a = A(id=2 ** 63)
            a.save()
            a.reload()

    def test_conversation_post_ids(self):
        customer_post = self._create_tweet(
            'Hi, I need a laptop battery',
            channels=[str(self.sc.inbound)],
            user_profile=self.customer
        )
        brand_post = self._create_tweet(
            channels=[str(self.sc.outbound)],
            content='Hey, we will ship new battery to you asap',
            user_profile=self.agent_profile,
            actor_id=self.agent_profile.id,
            is_inbound=False,
            in_reply_to=customer_post
        )
        mixed_customer_post = self._create_tweet(
            'Reply',
            channels=[str(self.sc.inbound)],
            user_profile=self.small_int_customer,
            in_reply_to=customer_post
        )
        self.assertEqual(Conversation.objects().count(), 1)
        conv = Conversation.objects.get()
        self.assertEqual(list(conv.posts), [customer_post.id, brand_post.id, mixed_customer_post.id])

        # verify Conversation.add_posts
        conv.add_posts_safe([mixed_customer_post])
        self.assertEqual(list(conv.posts), [customer_post.id, brand_post.id, mixed_customer_post.id])

        another_post = self._create_tweet(
            'Post 2',
            channels=[str(self.sc.inbound)],
            user_profile=self.small_int_customer,
        )
        conv.add_posts_safe([another_post])
        self.assertEqual(list(conv.posts),
                         [customer_post.id, brand_post.id, mixed_customer_post.id, another_post.id])

        # verify Conversation.objects.lookup_conversations
        for post in [customer_post, brand_post, mixed_customer_post]:
            for by_contact in [True, False]:
                self.assertEqual([conv], Conversation.objects.lookup_conversations(self.sc, [post], contacts=by_contact))

    def test_post_reference_field(self):
        customer_post = self._create_tweet(
            'Hi, I need a laptop battery',
            channels=[str(self.sc.inbound)],
            user_profile=self.customer
        )
        customer_post_2 = self._create_tweet(
            'Again',
            channels=[str(self.sc.inbound)],
            user_profile=self.customer
        )
        customer_post._parent = customer_post_2
        customer_post.save()
        customer_post.reload()
        self.assertEqual(customer_post._parent.id, customer_post_2.id)


class NegativeTimeslotCase(BaseEventCase):
    def test_facebook_post(self):
        updated_at = now().replace(microsecond=0)
        created_at = TIMESLOT_EPOCH - timedelta(days=300)

        content = 'post image caption'
        status_id = "12345678901_123456789101"
        from solariat_bottle.db.channel.facebook import FacebookServiceChannel
        data = {'content': content,
                'channels': [FacebookServiceChannel.objects.create_by_user(self.user, title='Fb')],
                'user_profile': {'user_name': 'fb_test_user'},
                'facebook': {
                    'facebook_post_id': status_id,
                    'text': content,
                    'created_at': str(created_at),
                    '_wrapped_data': {
                        'type': 'status', 'source_id': 'fake', 'source_type': 'event',
                        'created_at': str(created_at),
                        'updated_time': str(updated_at)
                    }
                }
                }

        post1 = self._create_db_post(**data)
        actor_id, creation_time = unpack_event_id(post1.id)
        self.assertEqual(post1.created_at.replace(microsecond=0), updated_at)
        self.assertEqual(creation_time.replace(microsecond=0), updated_at)

    def test_twitter_post(self):
        created_at = TIMESLOT_EPOCH - timedelta(minutes=1)
        content = 'tweet content'
        status_id = fake_status_id()

        data = {'content': content,
                'channels': [self.channel],
                'user_profile': {'user_name': 'test_user'},
                'twitter': {
                    'id': status_id,
                    'created_at': str(created_at),
                    'text': content
                }
                }
        post1 = self._create_db_post(**data)
        actor_id, creation_time = unpack_event_id(post1.id)
        self.assertEqual(post1.created_at.replace(microsecond=0), now().replace(microsecond=0))
        self.assertTrue(
            now() - timedelta(seconds=1) <= creation_time <= now() + timedelta(seconds=1),
            creation_time)


@unittest.skip
class PostEventCase(BaseEventCase):

    def setUp(self):
        super(PostEventCase, self).setUp()
        self.sc = CSC.objects.create_by_user(
            self.user,
            title='test chat service channel')

    def test_workflow(self):
        """
        Testing Predictive Matching coupled with Conversation State Machine
        """
        # creating three posts
        customer_post = factory_by_user(
            self.user,
            channels=[str(self.sc.inbound)],
            content='Hi, I need a laptop battery',
            user_profile=self.chat_profile.customer_profile,
            extra_fields={'chat': {'session_id': 'test_sessin_id'}})
        brand_post = factory_by_user(
            self.user,
            channels=[str(self.sc.outbound)],
            content='Hey, we will ship new battery to you asap',
            actor_id=self.agent_profile.id,
            is_inbound=False,
            extra_fields={'chat': {
                'session_id': 'test_sessin_id',
                'in_reply_to_status_id': customer_post.id}})
        customer_post2 = factory_by_user(
            self.user,
            channels=[str(self.sc.inbound)],
            content="Thank you! That's very nice!",
            user_profile=self.customer,
            extra_fields={'chat': {
                'session_id': 'test_sessin_id',
                'in_reply_to_status_id': brand_post.id}})
        self.assertEqual(Conversation.objects().count(), 1)

        # applying predictor to the given event sequence
        # predictor = CSMPredictor(name='test chat predictor')
        # events = [x for x in ChatPost.objects()]
        # self.assertEqual(len(events), 3)
        # res = predictor.predict(events)
        # self.assertTrue(res in [1, 2, 3, 4]) # check that outcome is equal to one of possible labels


@unittest.skip('solariat_bottle.db.events.predictor.GeneralPredictor is obsolete')
class GeneralPredictorCase(BaseEventCase):
    """
    Testing general PostEvent event with GeneralPredictor predictor
    """

    CONTENT = [
        ("Customer", "Hi, I need a laptop battery"),
        ("Brand", "We willsend you new one"),
        ("Customer", "It's urgent"),
        ("Brand", "Ok, we'll send it to you today"),
        ("Customer", "Thank you"),
        ("Brand", "you're welcome"),
    ]*3

    def setUp(self):
        super(GeneralPredictorCase, self).setUp()

        self.customer2 = UserProfile.objects.upsert('Chat', dict(screen_name='JoeCustomer2'))
        self.customer2.save()

        self.customer3 = UserProfile.objects.upsert('Chat', dict(screen_name='JoeCustomer3'))
        self.customer3.save()

    def _create_event_sequence(self, customer_up, length=5):
        kw = { 'user': self.user}
        events = []
        post   = None
        for i in range(length):
            status_id = fake_status_id()
            if 0 == i%2:
                channel = self.sc.inbound_channel
                user_profile = customer_up
            else:
                channel = self.sc.outbound_channel
                user_profile = self.support_up
            if post is not None:
                twitter_data = {'twitter': {
                        'in_reply_to_status_id': post.extra_fields['twitter']['id'],
                        'id': status_id }}
            else:
                twitter_data = {'twitter': {'id': status_id}}
            post = factory_by_user(
                self.user,
                channels=[str(channel.id)],
                content=self.CONTENT[i][1],
                user_profile=user_profile,
                **twitter_data)
            events.append(post)
        return events

    def test_event(self):
        # testing PostEvent creation
        customer_post = factory_by_user(
            self.user,
            channels=[self.sc.inbound],
            content='Hi, I need a laptop battery',
            user_profile=self.customer_up
        )

    def test_workflow(self):
        # create event sequences
        self.customer2 = self._create_customer('Chat', 'JoeCustomer2')
        self.customer3 = self._create_customer('Chat', 'JoeCustomer3')

        event_sequence1 = self._create_event_sequence(length=3, customer_up=self.customer_up)
        self.assertEqual(Conversation.objects().count(), 1)

        event_sequence2 = self._create_event_sequence(length=7, customer_up=self.customer_up2)
        self.assertEqual(Conversation.objects().count(), 2)
        event_sequence_test = self._create_event_sequence(length=9, customer_up=self.customer_up3)
        self.assertEqual(Conversation.objects().count(), 3)

        # train predictor with two event sequences
        predictor = GeneralPredictor(name='GeneralPredictor')
        predictor.train([event_sequence1, event_sequence2], [0, 1])
        # test predictions
        self.assertTrue(predictor.predict(event_sequence_test)[0] in [0, 1])
        self.assertEqual(predictor.predict(event_sequence1)[0], 0)
        self.assertEqual(predictor.predict(event_sequence2)[0], 1)

        # testing CSM predictor too
        predictor = CSMPredictor(name='CSMPredictor')
        predictor.predict(event_sequence_test)


class DuplicatesTest(MainCase):
    def get_user_profile(self, platform='Twitter', profile={'user_name': 'test'}):
        # customer_profile = CustomerProfile()
        # customer_profile.save()
        # user_profile = UserProfile.objects.upsert(
        #     platform, profile,
        #     _customer_profile=customer_profile,
        #     _agent_profile=None)
        # return user_profile
        return profile

    def test_base_event(self):
        ts = now()
        data = {'content': 'Test event at %s' % ts,
                '_created': ts,
                'user_profile': self.get_user_profile(),
                'channels': [self.channel],
                'twitter': {'id': 'sfq9wq98r8823yq9f'}}
        post1 = self._create_db_post(**data)
        self.assertEqual(post1.native_id, 'sfq9wq98r8823yq9f')
        post2 = self._create_db_post(**data)
        self.assertEqual(post1.id, post2.id)

    def test_twitter_event(self):
        ts = datetime_to_string(now())
        content = 'tweet content'
        status_id = fake_status_id()

        data = {'content': content,
                'channels': [self.channel],
                'user_profile': self.get_user_profile(),
                'twitter': {
                    'id': status_id,
                    'created_at': ts,
                    'text': content
                    }
                }
        # tweets with the same id and created date should not duplicate
        post1 = self._create_db_post(**data)
        post2 = self._create_db_post(**data)
        self.assertEqual(post1.id, post2.id)

        # tweets with the same created date and different id should be separated
        data['twitter']['id'] = fake_status_id()
        post3 = self._create_db_post(**data)
        self.assertNotEqual(post2.id, post3.id)

    def test_facebook_event(self):
        ts = str(now())
        content = 'tweet content'
        status_id = "12345678901_123456789101"
        from solariat_bottle.db.channel.facebook import FacebookServiceChannel
        data = {'content': content,
                'channels': [FacebookServiceChannel.objects.create_by_user(self.user, title='Fb')],
                'user_profile': self.get_user_profile('Facebook'),
                'facebook': {
                    'facebook_post_id': status_id,
                    'created_at': ts,
                    'text': content,
                    '_wrapped_data':{'type':'status', 'source_id':'fake', 'source_type':'event'
                                                      }

                    }
                }
        # posts with the same id and created date should not duplicate
        post1 = self._create_db_post(**data)
        post2 = self._create_db_post(**data)
        self.assertEqual(post1.id, post2.id)

        # posts with the same created date and different id should be separated. This is a test of the use
        # of fine-grain resolution
        data['facebook']['facebook_post_id'] = fake_status_id()
        post3 = self._create_db_post(**data)
        self.assertNotEqual(post2.id, post3.id)

    #@unittest.skip("Run this distinct - should pass. In batch run fails with pebble PoolError: Unexpected error within the Pool")
    @unittest.skip("ProcessPool conflicts with gevent")
    def test_race_condition(self):
        ts = datetime_to_string(now())
        content = 'tweet content'
        status_id = fake_status_id()

        data = {'content': content,
                'channels': [self.channel],
                'user_profile': self.get_user_profile(),
                'twitter': {
                    'id': status_id,
                    'created_at': ts,
                    'text': content
                    }
                }

        def gen_data(n_same_id=5, n_different_id=5):
            """Creates posts with the same creation date
             `n_same_id` posts with same id should not duplicate
             `n_different_id` posts should be separate"""
            for i in xrange(n_same_id):
                yield data

            for i in xrange(n_different_id):
                new_data = data.copy()
                new_data['twitter'] = data['twitter'].copy()
                new_data['twitter']['id'] = fake_status_id()
                print "USING ID  " + str(new_data['twitter']['id'])
                yield new_data

        def create_tweet(data):
            post = None
            try:
                post = self._create_db_post(sync=True, **data)
            except:
                import logging
                logging.exception(data)
            finally:
                return post

        from solariat_bottle.tests.base import ProcessPool

        pool = ProcessPool(8)
        n_different_id = 20
        posts = pool.map(create_tweet, gen_data(n_same_id=10, n_different_id=n_different_id))
        post_ids = set(p.id for p in posts)
        native_ids = set(p.native_id for p in posts)
        print len(native_ids), native_ids
        self.assertEqual(len(post_ids), n_different_id + 1, "Expected %s different ids, but got %s." % (n_different_id + 1, len(post_ids)))
