# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from datetime import timedelta
from itertools import cycle
import json

from solariat.utils          import timeslot
from solariat.utils.lang.support import Lang

from solariat_nlp.sa_labels import SATYPE_NAME_TO_ID_MAP
from solariat.utils.timeslot import datetime_to_timeslot, parse_date, Timeslot
from solariat_bottle.settings         import LOGGER
from solariat_bottle.utils.id_encoder import ALL_TOPICS
from solariat_bottle.db.channel.twitter      import TwitterServiceChannel
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends
from solariat_bottle.db.roles                import AGENT
from solariat_bottle.db.channel_trends       import ChannelTrends
from .base import UICase, datasift_date_format, fake_status_id


need    = int(SATYPE_NAME_TO_ID_MAP['needs'])
problem = int(SATYPE_NAME_TO_ID_MAP['problem'])
like    = int(SATYPE_NAME_TO_ID_MAP['likes'])


class TopicCountPlotDataCase(UICase):
    def setUp(self):
        super(TopicCountPlotDataCase, self).setUp()
        self.login()
        self.start_date = timeslot.parse_date('04/24/2013')
        self.end_date   = timeslot.parse_date('04/25/2013')
        self.level      = 'hour'

        timeline = []

        start_date = timeslot.parse_date('04/24/2013')
        while start_date < self.end_date:
            timeline.append(start_date)
            start_date += timeslot.timedelta(seconds=60*60*2)  #every 2 hours

        self.time_slots = map(lambda d: datetime_to_timeslot(d, 'hour'), timeline)

        contents = cycle([
            'I need a laptop',                          #laptop, need (intention id=2)
            'My laptop is not working out for me:(',    #laptop, problem (intention id=3)

            'I need a display',                         #display, need
            'My display is not working out for me:(',   #display, problem
        ])
        posts = []

        for _created in timeline:
            post = self._create_db_post(contents.next(), _created=_created)
            #print post.speech_acts
            posts.append(post)

    def _assert_time(self, data, features):
        for item in features:
            # verify items count by group
            self.assertEqual(len(filter(lambda x:x['_id']['grp']==item, data)), 12 / len(features))
            # verify 'count' - topics count
            self.assertEqual(sum(map(lambda x:x['count'], filter(lambda x:x['_id']['grp']==item, data))), 12 / len(features))

    def _assert_distribution(self, data, features):
        for item in features:
            # verify items count by group
            self.assertEqual(len(filter(lambda x:x['_id']['grp']==item, data)), 1)
            # verify 'count'
            self.assertEqual(filter(lambda x:x['_id']['grp']==item, data)[0]['count'], 12 / len(features))

    def test_topic_counts(self):
        base_filters = dict(
            channel       = self.channel,
            from_ts       = Timeslot(self.start_date, self.level),
            to_ts         = Timeslot(self.end_date,   self.level),
            topic_pairs   = [('laptop', True), ('display', True)],
            intentions    = ['likes', 'needs', 'recommendation', 'problem'],
            statuses      = [0, 1, 2, 3],
            plot_type     = 'topics',
            no_transform  = True)

        # Expected list of dicts
        # For time line
        # {'_id': {'grp': <group_by>, 'ts': <timestamp>}, 'count': 1}
        #
        # For distribution
        # {'_id': {'grp': <group_by>}, 'count': <total_count>}

        # plot_by = time
        # group_by = topic
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'topic',
            plot_by  = 'time',
            **base_filters)
        # verify time_slots
        self.assertEqual(set(map(lambda x:x['_id']['ts'], data)), set(self.time_slots))
        self._assert_time(data, ['laptop', 'display'])

        # plot_by = distribution
        # group_by = topic
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'topic',
            plot_by  = 'distribution',
            **base_filters)
        self._assert_distribution(data, ['laptop', 'display'])

        # plot_by = time
        # group_by = intention
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'intention',
            plot_by  = 'time',
            **base_filters)
        # verify time_slots
        self.assertEqual(set(map(lambda x:x['_id']['ts'], data)), set(self.time_slots))
        self._assert_time(data, [need, problem])

        # plot_by = distribution
        # group_by = intention
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'intention',
            plot_by  = 'distribution',
            **base_filters)
        self._assert_distribution(data, [need, problem])

        # plot_by = time
        # group_by = status
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'status',
            plot_by  = 'time',
            **base_filters)

        status = 1
        # verify time_slots
        self.assertEqual(set(map(lambda x:x['_id']['ts'], data)), set(self.time_slots))
        self._assert_time(data, [status])

        # plot_by = distribution
        # group_by = status
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'status',
            plot_by  = 'distribution',
            **base_filters)
        self._assert_distribution(data, [status])

        #test __ALL_topics__ case
        base_filters.pop('topic_pairs')

        # plot_by = time
        # group_by = topic
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'topic',
            plot_by  = 'time',
            **base_filters)

        # verify time_slots
        self.assertEqual(set(map(lambda x:x['_id']['ts'], data)), set(self.time_slots))
        self._assert_time(data, [ALL_TOPICS])

        # plot_by = distribution
        # group_by = topic
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'topic',
            plot_by  = 'distribution',
            **base_filters)
        self._assert_distribution(data, [ALL_TOPICS])

        # plot_by = time
        # group_by = intention
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'intention',
            plot_by  = 'time',
            **base_filters)

        # verify time_slots
        self.assertEqual(set(map(lambda x:x['_id']['ts'], data)), set(self.time_slots))
        self._assert_time(data, [need, problem])

        # plot_by = distribution
        # group_by = intention
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'intention',
            plot_by  = 'distribution',
            **base_filters)
        self._assert_distribution(data, [need, problem])

        # plot_by = time
        # group_by = status
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'status',
            plot_by  = 'time',
            **base_filters)

        status = 1
        # verify time_slots
        self.assertEqual(set(map(lambda x:x['_id']['ts'], data)), set(self.time_slots))
        self._assert_time(data, [status])

        # plot_by = distribution
        # group_by = status
        data = ChannelTopicTrends.objects.by_time_span(
            group_by = 'status',
            plot_by  = 'distribution',
            **base_filters)
        self._assert_distribution(data, [status])

    def test_topics_counts_ui(self):
        """
        Verify endpoint returns the same result after transform.
        """
        post_params = {
            "channel_id" : str(self.channel.id),
            "from"       : self.start_date.strftime('%m/%d/%Y'),
            "to"         : self.end_date.strftime('%m/%d/%Y'),
            "level"      : self.level,
            "intentions" : ['likes', 'needs', 'recommendation', 'problem'],
            "topics"     : [{"topic": "laptop", "topic_type": "node"}, {"topic": "display", "topic_type": "node"}],
            "statuses"   : ["actionable", "actual", "potential", "rejected"],
            "group_by"   : "topic",
            "plot_by"    : "time",
            "plot_type"  : "sentiment",
        }

        # group by = topic
        # plot by  = time
        resp = self.client.post('/trends/json', data=json.dumps(post_params), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])

        for item in resp['list']:
            self.assertIn(item['label'], ['laptop', 'display'])
            self.assertEqual(item['count'], 6)


class ReportsPlotDataCase(UICase):
    def setUp(self):
        super(ReportsPlotDataCase, self).setUp()
        self.login()
        
        self.sc = TwitterServiceChannel.objects.create_by_user(self.user,
                                                        title='Service Channel')
        LOGGER.debug(self.sc.acl)
        self.inbound = self.sc.inbound_channel
        self.outbound = self.sc.outbound_channel

        posts_num = 12  # 6 inbound, 3 * 2 outbound for agents ^A1 ^A2
        now    = parse_date('05/04/2013')
        period = (now - timedelta(days=1), now)
        self.start_date, self.end_date = period
        self.level = 'hour'

        period_sec = (period[1] - period[0]).total_seconds()

        incr = int(period_sec / posts_num)
        assert incr == 7200, "Expected delay is 2 hours"
        self.avg_rt = incr / 3600

        created_dates = [period[0] + timedelta(seconds=i*incr) for i in range(posts_num)]
        self.time_slots = map(lambda d: datetime_to_timeslot(d, 'hour'), created_dates)
        created_dates = map(datasift_date_format, created_dates)

        #Users taking part in conversation
        screen_names = ['Customer', 'Support']

        user_profiles = [UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
                         for screen_name in screen_names]

        channels = {'Customer': self.inbound,
                    'Support': self.outbound}

        self.agents = []
        self.sc.add_username('@Support')
        self.agents.append(self._make_agent('agent_1@test.test', '^A1', '@support'))
        self.agents.append(self._make_agent('agent_2@test.test', '^A2', '@support'))


        def get_post_data(i):
            conversation = [
                # agent 1 with laptops
                "I need a laptop.",                         # 00 needs
                "Try this one. ^A1",                        # 02
                "This laptop is not working out for me.",   # 04 problem
                "Try another one. ^A1",                     # 06
                "I like my laptop",                         # 08 likes
                "Check out our laptops. ^A1",               # 10

                # agent 2 with displays
                "I need a display.",                        # 12 needs
                "Try this one. ^A2",                        # 14
                "This display is not working out for me.",  # 16 problem
                "Try another one. ^A2",                     # 18
                "I like my display",                        # 20 likes
                "Check out our displays. ^A2",              # 22
            ]

            profile = user_profiles[i % len(screen_names)]
            created_at = created_dates[i]
            channel = channels.get(profile.screen_name)
            content = conversation[i]
            return channel, profile, created_at, content


        i = 0
        reply_to = None
        first_post = None

        while i < posts_num:
            channel, profile, created_at, content = get_post_data(i)

            twitter_data = {'twitter':
                                {'id': fake_status_id(),
                                 'created_at': created_at}
                            }
            if reply_to:
                twitter_data['twitter']['in_reply_to_status_id'] = reply_to

            post = self._create_db_post(
                channel=channel,
                content=content,
                user_profile=profile,
                **twitter_data)

            if not first_post:
                first_post = post

            post.reload()
            reply_to = post.native_id
            i += 1

    def _make_agent(self, email, signature, screen_name):
        user = self._create_db_user(email=email, password='1', account=self.account, roles=[AGENT])
        user.account = self.account
        user.signature = signature
        user.user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=screen_name))
        user.save()
        return user

    def _assert_time(self, data, features, seconds=False):
        def avg(lst):
            return sum(lst) / len(lst)

        for item in features:
            # verify items count by group
            self.assertEqual(len(filter(lambda x:x['_id']['grp']==item, data)), 6 / len(features))
            # verify 'count' - average response time
            self.assertEqual(avg(map(lambda x:x['count'], filter(lambda x:x['_id']['grp']==item, data))),
                             self.avg_rt * (seconds * 3600) + self.avg_rt * (not seconds))

    def _assert_distribution(self, data, features):
        for item in features:
            # verify items count by group
            self.assertEqual(len(filter(lambda x:x['_id']['grp']==item, data)), 1)
            # verify 'count'
            self.assertEqual(filter(lambda x:x['_id']['grp']==item, data)[0]['count'], self.avg_rt)

    def test_response_time_report(self):
        # TODO: dudarev: this report is now using ChannelTrends, this test needs to be re-written
        agent_ids = [u.agent_id for u in self.agents]

        base_filters = dict(
            channel       = self.sc.inbound_channel,  #inbound of service channel
            from_ts       = datetime_to_timeslot(self.start_date, self.level),
            to_ts         = datetime_to_timeslot(self.end_date,   self.level),
            statuses      = [3],
            agents        = self.agents,
            plot_type     = 'response-time',
            no_transform  = True)

        # Total posts 12
        # replied 6

        # GROUP BY AGENT
        # plot_by = time
        # group_by = agent
        data = ChannelTrends.objects.by_time_span(
            group_by = 'agent',
            plot_by  = 'time',
            **base_filters)
        self.assertEqual(set(map(lambda x:x['_id']['ts'], data)), set(self.time_slots[::2]))
        self._assert_time(data, agent_ids, seconds=True)

        # plot_by = distribution
        # group_by = agent
        data = ChannelTrends.objects.by_time_span(
            group_by = 'agent',
            plot_by  = 'distribution',
            **base_filters)

        self._assert_distribution(data, agent_ids)

        # GROUP BY HOURS
        # plot_by = distribution
        # group_by = time
        data = ChannelTrends.objects.by_time_span(
            group_by = 'time',
            plot_by  = 'distribution',
            **base_filters)
        self.assertEqual(data[0]['_id']['grp'], self.avg_rt)  # group by 2.0
        self.assertEqual(data[0]['count'], 6)  # for all 6 responses

        # GROUP BY LANG
        # plot_by = distribution
        lang_ids = [Lang.EN, Lang.ES]
        data = ChannelTrends.objects.by_time_span(
            group_by = 'lang',
            plot_by  = 'distribution',
            **base_filters)
        self.assertEqual(data[0]['_id']['grp'], Lang.ALL)
        self.assertAlmostEqual(data[0]['count'], self.avg_rt)  # for all 6 responses

        data = ChannelTrends.objects.by_time_span(
            group_by = 'lang',
            plot_by  = 'distribution',
            languages= lang_ids,
            **base_filters)

        self.assertEqual(data[0]['_id']['grp'], Lang.EN)  # all responses are in english
        self.assertAlmostEqual(data[0]['count'], self.avg_rt)

        # plot_by = time
        data = ChannelTrends.objects.by_time_span(
            group_by = 'lang',
            plot_by  = 'time',
            **base_filters)
        self._assert_time(data, [Lang.ALL], seconds=True)

        data = ChannelTrends.objects.by_time_span(
            group_by = 'lang',
            plot_by  = 'time',
            languages= lang_ids,
            **base_filters)
        self._assert_time(data, [Lang.EN], seconds=True)
