from datetime import datetime
from mock import patch, Mock
from solariat_bottle.daemons.facebook.facebook_historics import FacebookSubscriber
from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.db.historic_data import FacebookHistoricalSubscription, SUBSCRIPTION_CREATED, SUBSCRIPTION_FINISHED, \
    SUBSCRIPTION_RUNNING
from solariat_bottle.tests.base import BaseCase


class TestFbHistorySubscription(BaseCase):

    def setUp(self):
        BaseCase.setUp(self)

        self.channel = FacebookServiceChannel.objects.create_by_user(self.user, title='sf1',
                                                             account=self.user.account)

        self.channel.facebook_handle_id = "this is fake id"
        self.channel.facebook_access_token = "fake token"
        self.channel.tracked_fb_event_ids = ['fake_e1', 'fake_e2']
        self.channel.tracked_fb_group_ids = ['fake_g1', 'fake_g2']
        self.channel.facebook_page_ids = ['fake_p1', 'fake_p2']
        self.channel.save()
        self.subscr = FacebookHistoricalSubscription.objects.create(channel_id=self.channel.id,
                                                                  from_date=datetime(year=2008, month=7, day=3),
                                                                  to_date=datetime(year=2012, month=7, day=3),
                                                                  status=SUBSCRIPTION_CREATED)

    @patch('solariat_bottle.daemons.facebook.facebook_historics.fb_get_history_pm')
    @patch('solariat_bottle.daemons.facebook.facebook_historics.fb_get_history_data_for')
    def test_run_subscription(self, comment_mock, pm_mock):

        comment_mock.sync = Mock()
        pm_mock.sync = Mock()

        subscriber = FacebookSubscriber(self.subscr, self.user)
        self.assertEqual(subscriber.subscription.status, SUBSCRIPTION_CREATED)
        self.assertEqual(subscriber.subscription.get_progress(), 0)

        subscriber.start_historic_load()

        self.assertEqual(subscriber.subscription.status, SUBSCRIPTION_FINISHED)
        self.assertEqual(comment_mock.sync.call_count, 7)
        self.assertEqual(pm_mock.sync.call_count, 2)
        self.assertEqual(subscriber.subscription.get_progress(), 1.)

    def test_run_multiple_subscriptions(self):
        subscr1 = FacebookHistoricalSubscription.objects.create(channel_id=self.channel.id,
                                                                from_date=datetime(year=2008, month=7, day=3),
                                                                to_date=datetime(year=2012, month=7, day=3),
                                                                status=SUBSCRIPTION_RUNNING)

        subscr2 = FacebookHistoricalSubscription.objects.create(channel_id=self.channel.id,
                                                                from_date=datetime(year=2008, month=7, day=3),
                                                                to_date=datetime(year=2012, month=7, day=3),
                                                                status=SUBSCRIPTION_CREATED)

        subscriber = FacebookSubscriber(subscr1, self.user)
        self.assertFalse(subscriber.start_historic_load())