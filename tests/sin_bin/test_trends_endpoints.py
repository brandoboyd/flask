# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import json
from datetime import timedelta

from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat.utils.timeslot import now, format_date
from solariat_bottle.tests.base import UICase, fake_twitter_url
from solariat_bottle.tests.nlp.test_trends import ChannelTrendsBaseCase

from solariat_bottle.tests.slow.test_conversations import ConversationBaseCase


class FetchMixin(object):
    def _fetch(self, url, **kw):
        resp = self.client.post(url, data=json.dumps(kw), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'], data.get('error'))
        self.assertTrue('list' in data)
        return data['list']


class MultilangMixin(object):
    def setup_posts(self):
        languages = ['en', 'es']
        self.data = []
        self.speech_act_count = 0

        for idx, content in enumerate(self.contents):
            lang = languages[idx % len(languages)]
            post = self._create_db_post(content, _created=now(), lang=lang)
            self.speech_act_count += len(post.speech_acts)
            self.data.append((post, lang))


class SingleLangMixin(object):
    def setup_posts(self):
        for content in self.contents:
            self._create_db_post(
                content  = content,
                _created = now()
            )


class BaseEndpointCase(UICase, FetchMixin):

    def setUp(self):
        UICase.setUp(self)
        self.login()

        self.created_at = now()

        self.created_on_str      = format_date(self.created_at)
        self.one_day_after_str   = format_date(self.created_at + timedelta(days=1))
        self.one_day_before_str  = format_date(self.created_at - timedelta(days=1))
        self.one_week_after_str  = format_date(self.created_at + timedelta(days=7))
        self.one_week_before_str = format_date(self.created_at - timedelta(days=7))

        self.contents = (
            'I need a bike. I like Honda.',                        # needs, likes
            'Can somebody recommend a sturdy laptop?',             # consideration
            'I need an affordabl laptop. And a laptop bag',        # needs
            'Whatever you buy, let it be an Apple laptop',         # recommendation
            'I would like to have a thin and lightweight laptop.', # needs
            'Thank you very much!',                                # gratitude
            'You\'re gonna end up with a broken laptop'            # problem
        )
        self.setup_posts()

    def get_trends(self, **kw):
        return self._fetch('/trends/json', **kw)


class TrendsJsonEndpointCase(BaseEndpointCase, SingleLangMixin):

    def test_basically_works(self):
        # there are trends today
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_on_str,
            'to'         : self.created_on_str,
            'level'      : 'day',
            'topics'     : [{'topic':'laptop', 'topic_type':'node'}],
            'intentions' : ['needs'],
        })
        self.assertTrue(trends)

        # no trends until yesterday
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_week_before_str,
            'to'         : self.one_day_before_str,
            'level'      : 'hour',
            'topics'     : [{'topic':'laptop', 'topic_type':'node'}],
            'intentions' : ['needs'],
        })
        self.assertFalse(trends, trends)

        # no trends for non-existent topic
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_on_str,
            'to'         : self.created_on_str,
            'level'      : 'day',
            'topics'     : [{'topic':'cognitive dissonance', 'topic_type':'node'}],
            'intentions' : ['problem'],
            'plot_type'  : 'sentiment',
            'group_by'   : 'status',
        })
        self.assertFalse(trends, trends)

    def test_no_intentions(self):
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'hour',
            'topics'     : [{'topic':'laptop', 'topic_type':'node'}],
        })
        self.assertTrue(trends)

    def test_no_topics(self):
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_week_before_str,
            'to'         : self.one_week_after_str,
            'level'      : 'month',
            'intentions' : ['needs', 'likes', 'recommendation'],
        })
        self.assertFalse(trends)

    def test_posts_many_topics(self):
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'day',
            'topics'     : [
                {'topic':'laptop', 'topic_type':'node'},
                {'topic':'dog',    'topic_type':'leaf'},
                {'topic':'desert', 'topic_type':'node'},
                {'topic':'bike',   'topic_type':'leaf'},
            ],
            'intentions' : ['needs', 'likes', 'recommendation'],
        })
        self.assertTrue(trends)

    def test_no_agents(self):
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'hour',
            # 'topics'     : [{'topic':'laptop', 'topic_type':'node'}],
            'intentions' : ['needs', 'likes', 'recommendation'],
            'agents'     : None
        })
        self.assertTrue(trends)

    def test_no_statuses(self):
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'hour',
            'topics'     : [{'topic':'laptop', 'topic_type':'node'}],
            'intentions' : ['needs', 'likes', 'recommendation'],
            'statuses'   : None
        })
        self.assertTrue(trends)

    def test_matching_sentiments(self):
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.created_on_str,
            'to'         : self.one_day_after_str,
            'level'      : 'hour',
            'topics'     : [{'topic':'laptop', 'topic_type':'node'}],
            'sentiments' : ['neutral'],
        })
        self.assertTrue(trends)

    def test_nonmatching_sentiments(self):
        """
        Posts, based on setup:

        (u'I need a bike. I like Honda.', Positive),
        (u'Can somebody recommend a sturdy laptop?', Neutral),
        (u'I need an affordabl laptop. And a laptop bag', Neutral),
        (u'Whatever you buy, let it be an Apple laptop', Neutral),
        (u'I would like to have a thin and lightweight laptop.', Neutral),
        (u'Thank you very much!', Positive),
        (u"You're gonna end up with a broken laptop", Negative)
        """
        from solariat_nlp.sentiment import extract_sentiment
        from solariat_bottle.db.post.base import Post
        print [(p.content, extract_sentiment(p.content)['sentiment']) for p in Post.objects()]
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'hour',
            'topics'     : [{'topic':'laptop bag', 'topic_type':'leaf'}],
            'sentiments' : ['neutral'],
            'plot_type'  : 'sentiment',
            'group_by'   : 'status',
        })
        self.assertTrue(trends)  # we have some positive and negative examples

    def test_group_by_intention(self):
        """
        Posts, based on setup:

        (u'I need a bike. I like Honda.', Positive),
        (u'Can somebody recommend a sturdy laptop?', Neutral),
        (u'I need an affordabl laptop. And a laptop bag', Negative),
        (u'Whatever you buy, let it be an Apple laptop', Neutral),
        (u'I would like to have a thin and lightweight laptop.', Negative),
        (u'Thank you very much!', Positive),
        (u"You're gonna end up with a broken laptop", Negative)
        """
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'day',
            'topics'     : [{'topic':'laptop', 'topic_type':'node'}],
            'intentions' : ['needs', 'likes', 'recommendation'],
            'group_by'   : 'intention',
            'plot_type'  : 'sentiment',
        })
        self.assertEqual(len(trends), 2)

    def test_group_by_sentiment(self):
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'day',
            'topics'     : [
                {'topic':'honda',  'topic_type':'node'},
                {'topic':'laptop', 'topic_type':'node'},
                {'topic':'bag',    'topic_type':'node'},
                {'topic':'bike',   'topic_type':'node'},
            ],
            'sentiments' : ['positive', 'negative'],
            'group_by'   : 'sentiment',
            'plot_type'  : 'sentiment',
        })
        self.assertEqual(len(trends), 2)  # (POS + NEG)

        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'day',
            'topics'     : [
                {'topic':'honda',  'topic_type':'node'},
                {'topic':'laptop', 'topic_type':'node'},
                {'topic':'bag',    'topic_type':'node'},
                {'topic':'bike',   'topic_type':'node'},
            ],
            'intentions' : ['needs', 'likes', 'recommendation', 'problem', 'gratitude'],
            'group_by'   : 'sentiment',
            'plot_type'  : 'sentiment',
        })
        self.assertEqual(len(trends), 3)  # (POS + NEG + NEUTRAL)

    def test_group_by_sentiment_plot_by_distribution(self):
        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'day',
            'topics'     : [
                {'topic':'honda',  'topic_type':'node'},
                {'topic':'laptop', 'topic_type':'node'},
                {'topic':'bag',    'topic_type':'node'},
                {'topic':'bike',   'topic_type':'node'},
            ],
            'sentiments' : ['positive', 'negative'],
            'group_by'   : 'sentiment',
            'plot_by'    : 'distribution',
            'plot_type'  : 'sentiment',
        })
        self.assertEqual(len(trends), 2)  # (POS + NEG)

        trends = self.get_trends(**{
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'day',
            'topics'     : [
                {'topic':'honda',  'topic_type':'node'},
                {'topic':'laptop', 'topic_type':'node'},
                {'topic':'bag',    'topic_type':'node'},
                {'topic':'bike',   'topic_type':'node'},
            ],
            'intentions' : ['needs', 'likes', 'recommendation', 'problem', 'gratitude'],
            'group_by'   : 'sentiment',
            'plot_by'    : 'distribution',
            'plot_type'  : 'sentiment',
        })
        self.assertEqual(len(trends), 3)  # (POS + NEG + NEUTRAL)
        for item in trends:
            self.assertEqual(
                len(item['data']), 1,
                'should be 1 data item when plot_by=distribution: %s' % item
            )


class TrendsJsonEndpointMultilang(BaseEndpointCase, MultilangMixin):
    def test_basic(self):
        q = {
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'day',
            'languages'  : [],
        }
        trends = self.get_trends(**q)
        self.assertEqual(trends[0]['count'], self.speech_act_count)

        q['languages'] = ['en', 'es']
        trends = self.get_trends(**q)
        self.assertEqual(trends[0]['count'], self.speech_act_count)

    def test_no_languages_match(self):
        q = {
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'day',
            'languages'  : ['zh', 'ca'],
        }
        trends = self.get_trends(**q)
        self.assertFalse(trends)

    def test_group_by_lang(self):
        q = {
            'channel_id' : str(self.channel.id),
            'from'       : self.one_day_before_str,
            'to'         : self.one_day_after_str,
            'level'      : 'day',
            'topics'     : [
                {'topic':'honda',  'topic_type':'node'},
                {'topic':'laptop', 'topic_type':'node'},
                {'topic':'bag',    'topic_type':'node'},
                {'topic':'bike',   'topic_type':'node'},
            ],
            'languages'  : ['en', 'es'],
            'group_by'   : 'lang',
        }
        trends = self.get_trends(**q)
        self.assertEqual(len(trends), 2)

        q['languages'] = ['en']
        q['intentions'] = ['needs', 'likes', 'recommendation', 'problem', 'gratitude']
        trends = self.get_trends(**q)
        self.assertEqual(len(trends), 1)


class ShortTrendsJsonEndpointCase(ChannelTrendsBaseCase, FetchMixin):
    """Tests for call-volume, missed-calls, response-time, and response-volume.
    """

    def setUp(self):
        super(ShortTrendsJsonEndpointCase, self).setUp()
        # have several posts
        self.login()
        # first 4 from one contact, next 4 from the second
        self.posts = self._create_posts()
        self.assertEqual(len(self.posts), 8)
        self.reply_to_fourth_post(self.posts)

    def get_trends(self, **kw):
        created_at = now()
        one_day_after_str   = format_date(created_at + timedelta(days=1))
        one_day_before_str  = format_date(created_at - timedelta(days=1))
        params = {
            'channel_id' : str(self.inbound.id),
            'from'       : one_day_before_str,
            'to'         : one_day_after_str,
            'level'      : 'hour',
            'topics'     : [{'topic':'laptop', 'topic_type':'node'}],
            'intentions' : ['needs'] or kw['intentions'],
        }
        params.update(kw)
        trends = self._fetch('/trends/json', **params)
        return trends

    def reply_to_fourth_post(self, posts):
        """Reply to a post - fourth posts from the first contact.
        """
        self.reply = self._create_tweet(
            user_profile=self.support,
            content="We are doing our best", 
            channel=self.outbound,
            in_reply_to=posts[3])

    def test_call_volume(self):
        trends = self.get_trends(plot_type='inbound-volume')
        self.assertTrue(trends)
        self.assertEqual(trends[0]['count'], 8)

    def test_missed_calls(self):
        """
        Exsiting data, based on setup:

        (u'@test I need a laptop', [u'States a Need / Want']),                  (x)
        (u'@test I like a laptop', [u'Likes...']),
        (u'@test I need a foo.', [u'States a Need / Want']),                    (x)
        (u'@test Can someone recommend a laptop?', [u'Asks for Something']),    (x)
        """
        trends = self.get_trends(plot_type='missed-posts', intentions=['needs', 'asks', 'problem'])
        self.assertTrue(trends)
        self.assertEqual(trends[0]['count'], 2)

    def test_response_volume(self):
        trends = self.get_trends(plot_type='response-volume')
        self.assertTrue(trends)
        self.assertEqual(trends[0]['count'], 1)

    def test_response_time(self):
        trends = self.get_trends(plot_type='response-time')
        self.assertTrue(trends)
        self.assertTrue(trends[0]['count'] > 0)

    def test_response_time_value(self):
        """Tests that response time is equal to time difference 
        to first post in conversation
        """
        trends = self.get_trends(plot_type='response-time')
        # we reply to 4th post in setUp
        # but by design response time should be time difference to 1st post
        dt = self.reply.created - self.posts[0].created
        self.assertTrue(trends)
        # assertAlmostEqual did not work well here
        # for example case like 0.5, 0.495 was failing
        # giving tollerance of 2%
        self.assertTrue(
            abs(trends[0]['count'] - dt.total_seconds()) / dt.total_seconds() < 0.02)


class ResponseVolumeCase(ConversationBaseCase, FetchMixin):
    """Tests for call-volume, missed-calls, response-time, and response-volume.
    """
    def get_trends(self, **kw):
        created_at = now()
        one_day_after_str   = format_date(created_at + timedelta(days=1))
        one_day_before_str  = format_date(created_at - timedelta(days=1))
        params = {
            'channel_id' : str(self.inbound.id),
            'from'       : one_day_before_str,
            'to'         : one_day_after_str,
            'level'      : 'hour',
            'topics'     : [{'topic':'laptop', 'topic_type':'node'}],
            'intentions' : ['needs'] or kw['intentions'],
        }
        params.update(kw)
        trends = self._fetch('/trends/json', **params)
        return trends

    def _create_post(self, content):
        """
        Creates a post and appends it to ``self.posts``"""

        url = fake_twitter_url(self.user_profile.screen_name)
        self.posts.append(
            self._create_db_post(
                channel=self.inbound,
                content=content,
                demand_matchables=False,
                url=url,
                user_profile=self.user_profile))


    def _reply_to_last_post(self):
        """Reply to last post.
        """
        self.reply = self._create_tweet(
            user_profile=self.support,
            content="We are doing our best", 
            channel=self.outbound,
            in_reply_to=self.posts[-1])

    def setUp(self):
        super(ResponseVolumeCase, self).setUp()

        self.user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name='@customer'))
        self.posts = []
        posts_content = [
            "@test I need a laptop",
            "@test I need another laptop"]

        # have several posts
        self.login()
        # first 4 from one contact, next 4 from the second
        for c in posts_content:
            self._create_post(c)
            self._reply_to_last_post()
        self.assertEqual(len(self.posts), 2)

    def test_simple(self):
        trends = self.get_trends(plot_type='response-volume')
        self.assertTrue(trends)
        self.assertEqual(trends[0]['count'], 2)
