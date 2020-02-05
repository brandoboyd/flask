import math
import time
import functools
import itertools
from datetime import datetime, timedelta
from random import randrange

import mock
from nose.tools import eq_, raises

from solariat_bottle.tests.base import MainCaseSimple
from solariat_bottle.db.channel.facebook import FacebookChannel
from solariat_bottle.db.post.facebook import FacebookPost
from solariat_bottle.db.post.twitter import TwitterPost
from solariat_bottle.db.predictors.base_predictor import BasePredictor
from solariat_bottle.db.predictors.operators import union_collection, PREDICTOR_TRAINING_BATCH_SIZE
from solariat_bottle.db.predictors.factory import create_agent_matching_predictor
from solariat_bottle.db.predictors.models.linucb import ModelState
from solariat.utils.timeslot import now as get_now
from solariat_bottle.utils.id_encoder import USER_NUM_WIDTH, pack_event_id


def gen_random_id(dt):
    # actor_num greater or equal to 1<<21 will raise "OverflowError: MongoDB can only handle up to 8-byte ints"
    USER_NUM_WIDTH = 20
    random_actor_num = randrange(0, 1<<USER_NUM_WIDTH)

    _id = pack_event_id(random_actor_num, dt)
    return _id


class PredictorFetchTest(MainCaseSimple):
    def setUp(self):
        MainCaseSimple.setUp(self)


class PredictorUnionTest(MainCaseSimple):
    def setUp(self):
        MainCaseSimple.setUp(self)
        self.tw_channel = self.channel
        self.fb_channel = FacebookChannel.objects.create_by_user(self.user, title='TestFBChannel', type='facebook')

    def test_join(self):
        now = get_now()
        from_dt = now - timedelta(days=1)
        to_dt = now
        mock_predictor = mock.create_autospec(BasePredictor)
        mock_predictor.name = "Social Media Predictor"

        fb1 = FacebookPost(actor_id=11, channels=[self.fb_channel.id], content='Yesterday, I hated facebook', comment_count=1)
        fb1.id = gen_random_id(now - timedelta(seconds=randrange(86400)))
        fb1.save()

        fb2 = FacebookPost(actor_id=12, channels=[self.fb_channel.id], content='Today, I hate facebook', comment_count=2)
        fb2.id = gen_random_id(now - timedelta(seconds=randrange(86400)))
        fb2.save()

        fb3 = FacebookPost(actor_id=13, channels=[self.fb_channel.id], content='Tomorrow, I will hate facebook', comment_count=3)
        fb3.id = gen_random_id(now - timedelta(seconds=randrange(86400)))
        fb3.save()

        tw1 = TwitterPost(actor_id=11, channels=[self.tw_channel.id], content='Yesterday, I loved twitter')
        tw1.id = gen_random_id(now - timedelta(seconds=randrange(86400)))
        tw1.save()

        tw2 = TwitterPost(actor_id=12, channels=[self.tw_channel.id], content='Today, I love twitter')
        tw2.id = gen_random_id(now - timedelta(seconds=randrange(86400)))
        tw2.save()

        tw3 = TwitterPost(actor_id=14, channels=[self.tw_channel.id], content='Tomorrow, I will love twitter')
        tw3.id = gen_random_id(now - timedelta(seconds=randrange(86400)))
        tw3.save()

        class IteratorOfDictContaining(list):
            def __eq__(self, other):
                other = list(other)
                assert len(self) == len(other), "Expected length = %d, Actual length = %d" % (len(self), len(other))
                for expected_dict, actual_dict in itertools.izip(self, other):
                    eq_(expected_dict, {k:v for k,v in actual_dict.iteritems() if k in expected_dict})
                return True

        temp_coll = union_collection(mock_predictor, from_dt, to_dt, FacebookPost, TwitterPost, left_key='actor_id', right_key='actor_id', drop_temp_coll=False)
        F = FacebookPost.F
        try:
            mock_predictor.insert_training_data_batch.assert_called_with(
                    IteratorOfDictContaining([
                        # check that union coll contains only common documents, and right_coll (TwitterPost) overwrites fields in left_coll (FacebookPost)
                        {F.actor_id: 11, F.channels: tw1.channels, F.content: tw1.data['ct'], F.comment_count: fb1.comment_count},
                        {F.actor_id: 12, F.channels: tw2.channels, F.content: tw2.data['ct'], F.comment_count: fb2.comment_count},
                    ])
            )
        finally:
            if temp_coll:
                temp_coll.drop()

    def test_drop_temp_coll_when_error(self):
        now = get_now()
        from_dt = now - timedelta(days=1)
        to_dt = now
        predictor = mock.create_autospec(BasePredictor)
        predictor.name = "Social Media Predictor"
        right_coll = TwitterPost

        # mock left_coll so that union_collection will fail right after temp collection is created
        left_coll = mock.create_autospec(FacebookPost)
        left_coll.__name__ = 'non_existing_coll'
        left_coll.objects.coll.map_reduce = None

        @raises(TypeError)
        def try_to_run_union():
            union_collection(predictor, from_dt, to_dt, left_coll, right_coll, left_key='actor_id', right_key='actor_id')

        try_to_run_union()

        db = TwitterPost.objects.coll.database
        collection_names = db.collection_names()
        union_collections = [each for each in collection_names if each.startswith('union_collection_')]
        # drop union_collections
        [db[each].drop() for each in union_collections]

        assert union_collections == [], ("Temporary collection %s after failure of 'union' operation was not dropped. "
                "But I've deleted it for you." % union_collections)

    def tearDown(self):
        MainCaseSimple.tearDown(self)

        #BasePredictor.objects.coll.drop()
        # this will drop all posts
        FacebookPost.objects.coll.remove({})
        # this will drop all channels
        FacebookChannel.objects.coll.drop()


#predictor = create_agent_matching_predictor(
#        self.account.id,
#        state=ModelState(status=ModelState.STATUS_ACTIVE, state=ModelState.CYCLE_NEW)
#)
#predictor.name = "Agent Matcher"
#predictor.save()
