# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
import unittest
from unittest import TestCase
from datetime import datetime, timedelta

from bson import ObjectId
from nose.tools import eq_

from solariat_bottle.configurable_apps import APP_GSA
from solariat_nlp.sa_labels import JUNK
from solariat.utils.hidden_proxy import unwrap_hidden
from solariat.utils.timeslot import now, datetime_to_timeslot, utc

from solariat_bottle.db.channel.twitter import KeywordTrackingChannel as KTC, TwitterChannel
from solariat_bottle.db.channel_hot_topics import ChannelHotTopics
from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
from solariat_bottle.db.post.base       import Post, PostMatch
from solariat_bottle.db.channel_stats   import get_levels
from solariat_bottle.db.speech_act      import (
    SpeechActMap, pack_speech_act_map_id, make_objects, fetch_posts)

from solariat_bottle.settings import get_var
from solariat_bottle.utils.post import extract_signature, get_language

from solariat_bottle.tests.base import SA_TYPES, MainCase, UICase, UICaseSimple


class PostCase(MainCase):

    def test_addressee_public(self):
        content = '@screen_name I need a laptop'
        post = self._create_db_post(content)
        self.assertEqual(post.addressee, "@screen_name")
        # Confirm default for native id
        self.assertEqual(post._native_id, str(post.id))

        # If it's not valid then expect None
        content = 'screen_name I need a laptop'

        post = self._create_db_post(content)
        self.assertEqual(post.addressee, None)

        content = '@ screen_name I need a laptop'
        post = self._create_db_post(content)
        self.assertEqual(post.addressee, None)

        content = 'screen_name I @need a laptop'
        post = self._create_db_post(content)
        self.assertEqual(post.addressee, None)

    def test_create_post_no_content(self):
        post = self._create_db_post()
        self.assertEqual(post.plaintext_content, '')
        self.assertEqual(map(unwrap_hidden, post.speech_acts), [dict(content='',
                                                                     intention_type=JUNK.title,
                                                                     intention_type_id=JUNK.oid,
                                                                     intention_topics=[],
                                                                     intention_type_conf=1.0,
                                                                     intention_topic_conf=1.0)])


    def test_addressee_direct(self):
        content = 'I need a laptop @screen_name'
        post = self._create_db_post(
            content=content,
            message_type=1
        )
        self.assertEqual(post.addressee, "@screen_name")

        #Now test some invalid contents and expect None as answer
        # For direct messages addresee is appended as suffix by default
        content = '@screen_name I need a laptop'
        post = self._create_db_post(
            content=content,
            message_type=1
        )
        self.assertEqual(post.addressee, None)

        # If no @ present also invalid
        content = 'I need a laptop screen_name'
        post = self._create_db_post(
            content=content,
            message_type=1
        )
        self.assertEqual(post.addressee, None)

        # Empty @ not valid aswell
        content = 'I need a laptop screen_name @'
        post = self._create_db_post(
            content=content,
            message_type=1
        )
        self.assertEqual(post.addressee, None)

        # Random @ also not valid
        content = 'I need a laptop @screen_name test'
        post = self._create_db_post(
            content=content,
            message_type=1
        )
        self.assertEqual(post.addressee, None)

    def test_post_search(self):
        content = 'I need a bike. I like Honda.'
        post = self._create_db_post(content)

        self.assertEqual(post.addressee, None)

        posts, are_more_posts_available = Post.objects.by_time_point(
            self.channel,
            'honda',
            datetime_to_timeslot(post.created_at, 'hour'))[:]

        self.assertEqual(posts[0].id, post.id)
        #status    = None, # (opt) <code:int> | <name:str> | <list|tuple|set>
        #intention = None, # (opt) <SAType> | <id:int|str> | <name:str> | <list|tuple|set>
        #min_conf  = None, # (opt) <min_confidence:float:0.0..1.0>

    def test_post_search_with_limits(self):
        date_now = now()
        date_now = date_now.replace(minute=10)  # not at x:59:59

        for i in range(0, 20):
            self._create_db_post(content="I need a laptop", _created=date_now + timedelta(milliseconds=i))

        posts, are_more_posts_available = Post.objects.by_time_point(
            self.channel,
            'laptop',
            datetime_to_timeslot(date_now, 'hour'),
            limit=10)[:]
        self.assertEqual(len(posts), 10)

        posts, are_more_posts_available = Post.objects.by_time_point(
            self.channel,
            'laptop',
            datetime_to_timeslot(date_now, 'hour'),
            limit=200)[:]
        self.assertEqual(len(posts), 20)

    def test_new_post_search(self):
        content = 'I need a bike. I like Honda.'
        post = self._create_db_post(content)

        posts = fetch_posts( [self.channel],
                             datetime_to_timeslot(post.created_at, 'hour'),
                             datetime_to_timeslot(post.created_at + timedelta(hours=1), 'hour'),
                             [dict(topic='honda', topic_type='leaf')],
                             [SpeechActMap.ACTIONABLE],
                             intentions=[],
                             min_conf=0.5,
                             agents=[])

        self.assertEqual(len(posts), 1)


    def test_agent_search(self):
        content = 'I need a bike. I like Honda.'
        post = self._create_db_post(content)

        posts = fetch_posts( [self.channel],
                             datetime_to_timeslot(post.created_at, 'hour'),
                             datetime_to_timeslot(post.created_at, 'hour'),
                             [dict(topic='honda', topic_type='leaf')],
                             [SpeechActMap.ACTIONABLE],
                             intentions=[],
                             agents=[10],
                             min_conf=0.5)

        self.assertEqual(len(posts), 0)
        self.assertEqual(SpeechActMap.objects.count(), 2)

        # Now reset with this agent, and into an ACTUAL stats
        post.channel_assignments[str(self.channel.id)] = 'actual'
        SpeechActMap.reset(post, [self.channel], agent=10)

        # Should be the same number of speech act map entries
        self.assertEqual(SpeechActMap.objects.count(), 2)

        # And try again. We should get a hit
        posts = fetch_posts( [self.channel],
                             datetime_to_timeslot(post.created_at, 'hour'),
                             datetime_to_timeslot(post.created_at, 'hour'),
                             [dict(topic='honda', topic_type='leaf')],
                             [SpeechActMap.ACTUAL],
                             intentions=[],
                             agents=[10],
                             min_conf=0.5)

        self.assertEqual(len(posts), 1)

    def test_speech_acts_creation(self):
        content = 'I need a bike. I like Honda.'
        post = self._create_db_post(content)
        self.assertEqual(post.speech_acts[0]['content'], 'I need a bike.')
        self.assertEqual(post.speech_acts[1]['content'], ' I like Honda.')

        # Verify the id for the SpeechActMap, and make sure we can get it.
        sam_id = pack_speech_act_map_id(
            self.channel,
            SpeechActMap.ACTIONABLE,             # status
            datetime_to_timeslot(post.created),  # hour-timeslot of the post
            post,                                # post
            0
        )

        sam = SpeechActMap.objects.get(id=sam_id)
        self.assertTrue(sam)

        self.assertEqual(str(sam.post),  str(post.id))
        self.assertEqual(sam.idx,   0)

        # Verify we can retrieve the speech act objects
        sam_ids = [m.id for m in
                   make_objects(self.channel, post, post.speech_acts, 'highlighted')]

        self.assertEqual(len(sam_ids), 2)

        sams = SpeechActMap.objects(id__in=sam_ids)
        self.assertEqual(len(sams), len(sam_ids))

        sam = [m for m in sams if m.id != sam_id][0]  # we want the other one this time
        self.assertEqual(str(sam.post),  str(post.id))
        self.assertEqual(sam.idx,   1)

    def test_topics_in_speech_acts(self):
        """
        This is related to issue #1623
        https://github.com/solariat/tango/issues/1623

        At some point if post had "DellCares" the keyword "Dell" still will be identified in it.
        """
        content = '#solariat and @some_tag, How can I contact DellCares?'

        # create keyword tracking channel with keyword 'dell'
        keywords = ['dell', '#solariat', '@some_tag']
        channel = KTC.objects.create_by_user(
            self.user, title='Inbound Channel',
            keywords=keywords)

        post = self._create_db_post(content, channel=channel)

        sam_id = pack_speech_act_map_id(
            channel,
            SpeechActMap.ACTIONABLE,             # status
            datetime_to_timeslot(post.created),  # hour-timeslot of the post
            post,                                # post
            0
        )

        sam = SpeechActMap.objects.get(id=sam_id)
        self.assertTrue('#solariat' in sam.to_dict()['topics'])
        self.assertTrue("en",'@some_tag' in sam.to_dict()['topics'])
        self.assertTrue('dellcares' in sam.to_dict()['topics'])
        self.assertFalse('dell' in sam.to_dict()['topics'])

    @unittest.skip('outdated id pattern')
    def test_id_generator(self):
        "test id and shard prefix generation"
        status_id = "1234567890"
        post = self._create_db_post('I need new laptop',
                                    url='https://twitter.com/solariatc/statuses/%s' % status_id)

        self.assertEqual(str(post.id)[0:6], "086579")

    def test_id_bug_for_multiple_terms(self):
        self._create_db_post('I need cell phone coverage.')

    def test_get_punks(self):
        post = self._create_db_post('I need some food')
        self.assertEqual(
            post.get_punks(), ['food'])

    @unittest.skip("Matchables are depricated")
    def test_matchable(self):
        content = 'I need a bike . I like Honda .'
        matchable = self._create_db_matchable(url='google.com',
                                creative='search for bike here')
        post = self._create_db_post(content, demand_matchables=True)
        info = post.to_dict()
        self.assertEqual(
            info['matchables'][0]['id'], str(matchable.id))

    def test_channel_stats(self):
        content = 'I need a bike. I like Honda .'
        # self._create_db_matchable(url='google.com',
        #                         creative='search for bike here')
        post = self._create_db_post(content)
        self.assertTrue(post.id is not None)
        self.assertTrue(Post.objects(channels__in=[self.channel.id]).count(), 1)
        for stats in get_levels(self.channel):
            stats.reload()
            self.assertEqual(
                stats.number_of_posts, 1)
            self.assertEqual(
                stats.feature_counts['2'], 1)
            self.assertEqual(
                stats.feature_counts['4'], 1)

    def test_timeslot_conversion(self):
        past_dt   = now() - timedelta(minutes=7*24*60)
        ts_before = datetime_to_timeslot(past_dt, 'hour')

        post = self._create_db_post(
            _created = past_dt,
            content  = 'i need some carrot'
        )
        ts_after = datetime_to_timeslot(post.created, 'hour')
        self.assertEqual(ts_before, ts_after)

    def test_crud_by_user(self):
        content = 'I need a bike'
        self._create_db_post(content)

    def test_crud(self):
        post = self._create_db_post(
            content='I need a new moto bike',
        )
        self.assertTrue(post.user_tag.startswith('unknown') or post.user_tag.startswith('anonymous'))

        count = Post.objects.find(channels=str(self.channel.id)).count()
        self.assertEqual(count, 1)
        self.assertEqual(Post.objects.get(post.id)['content'],
                         'I need a new moto bike')
        post.delete()
        self.assertEqual(Post.objects(channels__in=[self.channel.id]).count(), 0)

    def test_multilanguage_support(self):
        """Tests that Spanish language is detected correctly.
        """
        post = self._create_db_post(
            content='Necesito una bicicleta nueva moto',
            lang='auto')
        lang_code = Post.objects.get(post.id).language
        # langdetect 'it'
        # langid     'es'
        # cld2       'es'
        self.assertIn(lang_code, [u'es', u'it'])

    def test_different_type_of_creation(self):
        for channel in [self.channel, str(self.channel.id), self.channel.id]:
            self._create_db_post(channel=channel, content='I need some foo')

    @unittest.skip("Matchables and PostMatches are depricated.")
    def test_field(self):
        "Unicode symbol in field is allowed"
        post = self._create_db_post(
            u'i need a good lipstick. any suggestions girls? \U0001f48b')
        post_match = PostMatch.objects.create_by_user(
            self.user, post=post, rejects=[], impressions=[])
        self.assertEqual(post_match.to_dict()['id'],
                         str(post_match.id))

    @unittest.skip("Matchables and PostMatches and Responses are depricated.")
    def test_post_intention_confidence(self):
        self.account.update(selected_app=APP_GSA)
        # Scope is to create post with non 1.0 confidente on intention
        # and test that response has same confidence
        doc = {
            'url'              : self.url,
            'creative'         : 'If you need this shiny iphone just call me',
            'intention_types'  : ['States a Need / Want'],
            'intention_topics' : ['iphone'],
            'channels'         : [ str(self.channel.id) ]
        }
        match_id = self.do_post('matchables', version='v1.2', **doc)['item']['id']
        matchable = Matchable.objects.get(id=match_id)
        matchable.deploy(refresh=True)
        #dummy_filter = {'intention_name__in': ['apology', 'asks', 'checkins', 'gratitude', 'junk', 'likes',
        #                                       'needs', 'offer', 'problem', 'recommendation', 'other']}
        try:
            before = Response.objects()
        except:
            before = []

        post = self._create_db_post(
            content = 'iphone...drains some money in our days'
        )

        self.assertTrue(
            post.intention_confidence < 1.0,
            "Post generated with confidence of 1.0. Need to change content."
        )

        after = Response.objects()
        response = [resp for resp in after if resp.id not in before][0]

        self.assertEqual(
            response.intention_confidence,
            post.intention_confidence,
            "First post and response should have same confidence"
        )


class TestDuplicatePostProcessing(MainCase):

    def setUp(self):

        super(TestDuplicatePostProcessing, self).setUp()

        self.created = now()
        self.url = '%s/posts/%s' % (get_var('HOST_DOMAIN'), str(ObjectId()))
        self.content = "I'm so much want to buy a new laptop"
        self.duplicate_content = "I'm so much want to find a laptop"

        self.channel2 = TwitterChannel.objects.create_by_user(
            self.user, title='TestChannel2',
            type='twitter', intention_types=SA_TYPES)

        self.post = self._create_db_post(
            channels = [self.channel, self.channel2],
            content = self.content,
            url = self.url,
            twitter={"created_at" : "Wed, 06 Aug 2014 18:38:47 +0000", "id" : "497089420017676290"}
        )


        time_slot = datetime_to_timeslot(now(), 'day')
        self.topic = "laptop"

        self.hot_topic_stat = ChannelHotTopics.objects.by_time_span(
            channel = self.channel2,
            from_ts = datetime_to_timeslot(None, 'day'),
        )

        self.topic_trends_stat = ChannelTopicTrends(channel=self.channel2,
                            time_slot=time_slot,
                            topic=self.topic,
                            status=0)


    def test_duplicate_skip(self):
        duplicate_post = self._create_db_post(
            channels = [self.channel, self.channel2],
            content = self.duplicate_content,
            url = self.url,
            twitter={"created_at" : "Wed, 06 Aug 2014 18:38:47 +0000", "id" : "497089420017676290"}
        )

        #There should be just @self.content, because @duplicate_post handling should be skipped and just @self.post returned
        self.assertEqual(duplicate_post.plaintext_content, self.content)
        self.assertEqual(duplicate_post.id, self.post.id)

    def test_duplicate_handle_diff_channels(self):

        channel3 = TwitterChannel.objects.create_by_user(
            self.user, title='TestChannel3',
            type='twitter', intention_types=SA_TYPES)

        duplicate_post = self._create_db_post(
            channels = [self.channel2, channel3],
            content = self.duplicate_content,
            url = self.url,
            twitter={"created_at" : "Wed, 06 Aug 2014 18:38:47 +0000", "id" : "497089420017676290"}
        )

        self.assertEqual(len(duplicate_post.channels), 3)

        time_slot = datetime_to_timeslot(now(), 'day')
        ht_stat = ChannelHotTopics.objects.by_time_span(
            channel = self.channel2,
            from_ts = datetime_to_timeslot(None, 'day'),
        )

        tt_stat = ChannelTopicTrends(channel=self.channel2,
                            time_slot=time_slot,
                            topic=self.topic,
                            status=0)

        self.assertEqual(ht_stat, self.hot_topic_stat)
        self.assertEqual(tt_stat, self.topic_trends_stat)


class TestCommandCase(UICase):
    def test_test_command(self):
        import json
        self.login()
        data = dict(content='i need some foo',
                    lang='en',
                    channel=self.channel_id,
                    message_type=False)
        resp = self.client.post('/commands/create_post',
                                data=json.dumps(data))

        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))
        item = resp['item']
        self.assertEqual(item['content'],
                         'i need some foo')


class TestUtilsCase(TestCase):
    def test_extract_signature(self):

        content = 'I need a bike. I like Honda.'
        signature = extract_signature(content)
        self.assertEqual(signature, None)

        content = 'I need a bike. I like Honda. ^AD'
        signature = extract_signature(content)
        self.assertEqual(signature, '^AD')

        content = 'I need a bike. I like Honda. ^IZ  '
        signature = extract_signature(content)
        self.assertEqual(signature, '^IZ')

        content = 'I need a bike. I like Honda. ^AD Another sentense.'
        signature = extract_signature(content)
        self.assertEqual(signature, None)

        content = 'I need a bike. I like Honda. ^AB ^AD'
        signature = extract_signature(content)
        self.assertEqual(signature, '^AD')

    def test_invalid_text(self):
        post_dict = dict(content='$$$')
        lang = get_language(post_dict)
        self.assertEqual(lang.lang, 'en')

    def test_invalid_utf(self):
        post_dict = dict(content="\xc3\x28")
        lang = get_language(post_dict)
        self.assertEqual(lang.lang, 'en')

    def test_unicode(self):
        post_dict = dict(content=u'\u0938\u0941\u091c\u0928')
        lang = get_language(post_dict)
        self.assertIn(lang.lang, ['ja', 'hi'])


class TestPosts(UICaseSimple):
    """
    Test that asserts any selection of topics facet in Details tab yields some posts
    """

    def setUp(self):
        super(TestPosts, self).setUp()
        self.login()

    def get_post_details(self, default):
        data_dict = {
                "agents": None,
                "channel_id": None,
                "from": None,
                "to": None,
                "level": "hour",
                "intentions": ["apology", "asks", "checkins", "consideration", "discarded", "gratitude",
                               "junk", "likes", "needs", "offer", "problem", "recommendation"],
                "languages": [],
                "last_query_time": None,
                "limit": 15,
                "offset": 0,
                "sort_by": "time",
                "statuses": ["actionable", "actual", "rejected"],
                "thresholds": {"intention": 0, "influence": 0, "receptivity": 0},
                "topics": [],
        }
        data_dict.update(default)
        res = self._post("/posts/json", data_dict)
        return res["list"]

    def test_posts_filtered_by_date(self):
        content = "I need a laptop @screen_name test"
        _from = utc(datetime(2016, 3, 14, 19, 00, 00))
        _to = utc(datetime(2016, 3, 14, 20, 00, 00))

        posts_at = [
                _from - timedelta(seconds=1),   # doesn't lie within 'from/to' range
                _from,                          # 1
                _from + timedelta(seconds=1),   # 2
                _to - timedelta(seconds=1),     # 3
                _to,                            # 'to' in query is open interval
                _to + timedelta(seconds=1),
        ]

        for _created in posts_at:
            post = self._create_db_post(
                    content=content,
                    _created=_created
            )

        posts = self.get_post_details({
            "channel_id": str(self.channel.id),
            "from": _from.strftime("%Y-%m-%d %H:%M:%S"),
            "to":     _to.strftime("%Y-%m-%d %H:%M:%S")
        })
        eq_(len(posts), 3)
