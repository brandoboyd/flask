from datetime import timedelta
from mock import patch

from solariat_bottle.db.historic_data import BaseHistoricalSubscription
from solariat_bottle.db.historic_data import FacebookHistoricalSubscription, TwitterRestHistoricalSubscription
from solariat_bottle.db.user import User
from solariat_bottle.db.channel.twitter import TwitterServiceChannel, EnterpriseTwitterChannel
from solariat_bottle.db.channel.facebook import FacebookServiceChannel

from solariat_bottle.tests.base import RestCase
from solariat.utils.timeslot import now

format_date = lambda d: d.strftime("%m/%d/%Y %H:%M:%S")


class APIHistoricsCase(RestCase):
    def setUp(self):
        super(APIHistoricsCase, self).setUp()

        from solariat_bottle.tests.test_configure import FakeTwitterAPI
        from solariat_bottle.tasks import twitter

        self.stored_api_getter = twitter.get_twitter_api
        twitter.get_twitter_api = lambda *args, **kwargs: FakeTwitterAPI()

    def tearDown(self):
        from solariat_bottle.tasks import twitter
        twitter.get_twitter_api = self.stored_api_getter

    @patch("solariat_bottle.api.historics.requests")
    def test_create_happy_flow_data(self, fb_req):
        self.assertEqual(FacebookHistoricalSubscription.objects.count(), 0)
        self.assertEqual(TwitterRestHistoricalSubscription.objects.count(), 0)
        tschn1 = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        token = self.get_token()
        happy_flow_data = {
            'force': True,
            'token': token,
            'channel': str(tschn1.id),
            'from_date': format_date(now() - timedelta(days=2)),  # '07/03/2014 12:00:00',
            'to_date': format_date(now())  # '07/13/2014 12:00:00'
        }
        resp = self.do_post('historics', **happy_flow_data)
        # Just a check that we don't change API structure w/o noticing
        datasift_sub_data = resp['subscription']
        for key in ("status", "channel_id", "from_date", "to_date", "id"):  # "datasift_historic_id", "datasift_push_id",
            self.assertTrue(key in datasift_sub_data)

        self.assertEqual(FacebookHistoricalSubscription.objects.count(), 0)
        self.assertEqual(TwitterRestHistoricalSubscription.objects.count(), 1)

        fbsch1 = FacebookServiceChannel.objects.create_by_user(self.user, title='FSC')
        happy_flow_data['channel'] = str(fbsch1.id)
        self.do_post('historics', **happy_flow_data)

        # assert fb_req.call_count == 1

        happy_flow_data = {
            'token': token,
        }
        resp = self.do_get('historics', **happy_flow_data)
        self.assertEqual(len(resp['items']), 1)

        happy_flow_data['id'] = datasift_sub_data['id']
        resp = self.do_get('historics', **happy_flow_data)
        self.assertDictEqual(resp["item"], datasift_sub_data)


    def test_channel_subscriptions(self):
        sc = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        token = self.get_token()
        data = {
            'force': True,
            'token': token,
            'channel': str(sc.id),
            'from_date': format_date(now() - timedelta(days=2)),  #'07/03/2014 12:00:00',
            'to_date': format_date(now())  # '07/13/2014 12:00:00'
        }
        self.do_post('historics', **data)
        resp = self.do_post('historics', **data)
        self.assertTrue(resp['subscription']['is_stoppable'])

        resp = self.do_put('historics/%(id)s' % resp['subscription'], action='stop')
        self.assertEqual(resp['message'], 'Subscription has been stopped')

        resp = self.do_get('historics', **data)
        self.assertTrue(resp['has_active'])

        for sub in resp['items']:
            self.do_put('historics/%(id)s' % sub, action='stop')

        resp = self.do_get('historics', **data)
        self.assertFalse(resp['has_active'])
        self.assertEqual(len(resp['items']), 2)

    def test_errors(self):
        token = self.get_token()
        sc = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')

        cases = [
            ({'token': token,
              'channel': str(self.channel.id),
              'from_date': '07/03/2014 12:00:00',
              'to_date': '07/13/2014 12:00:00'
             },
             "Could not infer a service channel for channel TestChannel_Old<TwitterChannel>"),

            ({'token': token,
              'channel': str(sc.id),
              'to_date': '07/03/2014 12:00:00',
              'from_date': '07/03/2014 12:00:00'
             }, "'From' date must be less than 'To' date"),

            ({'token': token,
              'channel': str(sc.id),
              'to_date': format_date(now()),
              'from_date': format_date(now() - timedelta(days=32))
             }, "'From' date must not be earlier than 31 days ago"),

            # Datasift restrictions
            # ({'token': token,
            #   'channel': str(sc.id),
            #   'to_date': format_date(now()),
            #   'from_date': format_date(now() - timedelta(hours=3))
            #  }, "'To' date must be at least one hour in the past"),

            # ({'token': token,
            #   'channel': str(sc.id),
            #   'to_date': format_date(now() - timedelta(hours=1)),
            #   'from_date': format_date(now() - timedelta(days=31))
            #  }, "Time range must be less than 30 days"),
        ]
        for (post_data, error_message) in cases:
            post_data.update(force=True)
            resp = self.do_post('historics', **post_data)
            self.assertDictEqual(resp,
                                 {"code": 113,
                                  "ok": False,
                                  "error": error_message})

        BaseHistoricalSubscription.objects.remove(channel_id=sc.id)
        # try submit twice
        post_data = {
            'force': False,
            'token': token,
            'channel': str(sc.id),
            'from_date': format_date(now() - timedelta(days=1)),
            'to_date': format_date(now())
        }
        resp = self.do_post('historics', **post_data)
        self.assertTrue(resp['ok'])
        resp = self.do_post('historics', **post_data)
        error_message = 'The recovery process is already in progress for this channel'
        self.assertDictEqual(resp,
                                 {"code": 134,
                                  "ok": False,
                                  "error": error_message})
