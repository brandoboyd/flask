# from nose.tools import eq_
# from solariat_bottle.configurable_apps import CONFIGURABLE_APPS
# from solariat_bottle.tests.base import BaseCase
# from solariat_bottle.db.events.event import Event
#
#
# class CustomerSegmentTest(BaseCase):
#
#     def setUp(self):
#         super(CustomerSegmentTest, self).setUp()
#
#     def test_evaluate_customer_segments(self):
#         self.account.update(available_apps=CONFIGURABLE_APPS)
#         cs = CustomerSegment.objects.create_by_user(self.user,
#                 account_id = self.account.id,
#                 display_name = 'Nepalese origin',
#                 locations = ['kathmandu', 'lalitpur', 'banepa'],
#                 age_range = [20, 35],
#                 account_balance_range = [1000, 2000],
#                 num_calls_range = [10, 20],
#         )
#
#         customer = CustomerProfile.objects.create_by_user(self.user,
#                 first_name = 'Sujan',
#                 last_name = 'Shakya',
#                 sex = 'M',
#                 location = 'lalitpur',
#                 age = 30,
#                 account_balance = 1500,
#                 num_calls = 15,
#         )
#         event = Event.objects.create_by_user(self.user,
#                 channels = [self.channel.id],
#                 actor_id = customer.id,
#                 is_inbound = True,
#         )
#         customer.reload()
#         eq_(customer.assigned_segments, [cs.id])
