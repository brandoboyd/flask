import json
import os
import unittest

from pprint import pprint
from time import sleep

from datetime import datetime, timedelta
from solariat_bottle.configurable_apps import CONFIGURABLE_APPS, APP_JOURNEYS
from solariat.tests.base import LoggerInterceptor
from solariat_bottle.tests.base import UICaseSimple

from solariat_bottle.scripts.data_load.utils import setup_account, remove_account
from solariat_bottle.db.user import set_user
from solariat_bottle.db.events.event import Event
from solariat_bottle.db.channel.base import Channel

import solariat_bottle.scripts.data_load.samples as samples

class DataLoaderCase(UICaseSimple):

    def setUp(self):
        super(DataLoaderCase, self).setUp()
        set_user(self.user)
        self.user.is_superuser = True
        self.user.save()

    def test_account_setup(self):
        ''' Setup and clear account data'''
        account = setup_account(samples.sample1)

        # Set it again - should throw an error
        try:
            account = setup_account(samples.sample1)
            failed = True
        except Exception, e:
            failed = False

        self.assertFalse(failed)

        # Confirm results with agents loaded
        self.assertEqual(account.get_agent_profile_class().objects.count(), 2);
        self.assertEqual(account.get_customer_profile_class().objects.count(), 3);

        # Now remove it - and it should work. Make a remove idempotent
        remove_account(samples.sample1)
        remove_account(samples.sample1)
        account = setup_account(samples.sample1)
        self.assertEqual(account.name, samples.sample1.ACCOUNT)

    def test_event_linking(self):
        ''' Load dynamic events and have them link together in a sequence'''
        from solariat.utils.timeslot import utc, now
        from solariat_bottle.db.post.twitter import TwitterPost
        from solariat_bottle.db.post.facebook import FacebookPost
        from solariat_bottle.db.channel.facebook import FacebookChannel
        from solariat_bottle.db.channel.twitter import TwitterChannel
        from solariat_bottle.tasks import create_post

        start = utc(now())
        one_sec = timedelta(seconds=1)

        account = setup_account(samples.sample2)

        # Get the customer for whom we expect the events to be linked.
        CustomerProfile = account.get_customer_profile_class()
        customer = CustomerProfile.objects.get(customer_id='c_1')
        self.assertEqual(customer.first_name, 'Jane')

        channels = [c.id for c in Channel.objects(account=account)]

        # Should be 5 events in all
        self.assertEqual(Event.objects.count(), 5)
        events = Event.objects(channels__in=channels)[:]
        self.assertEqual(len(events), 5)

        # lets check event linking with other entities
        tw_channel = TwitterChannel.objects.create_by_user(
            self.user,
            title='TestTWChannel',
            type='twitter')
        fb_channel = FacebookChannel.objects.create_by_user(
            self.user,
            title='TestFBChannel',
            type='facebook')

        # link twitter post to dynamic customer profile c_1
        tw_post_data = {
            'channels': [tw_channel.id],
            'content': "hi! I'd like to order new bike",
            'user_profile': {
                'user_id': 'c_1', # link to CustomerProfile with id=c_1
                'name': 'Jane Tw',
            },
            'twitter': {
                'id': '80001000',
            }
        }
        # link twitter post to dynamic customer profile c_2
        fb_post_data = {
            'channels': [fb_channel.id],
            'content': 'I love fb',
            'user_profile': {
                'user_id': 'c_2', # link event to CustomerProfile id=c_2
                'name': 'John FB',
            },
            'facebook': {
                'facebook_post_id': '1234-1234',
            }
        }

        tw_post = create_post(self.user, sync=True, **tw_post_data)
        fb_post = create_post(self.user, sync=True, **fb_post_data)
        end = now() + one_sec  # because of added padding while created event_id,
                               # we could reach next second

        self.assertEqual(Event.objects.count(), 7)

        # check linking: request sequences by 2 different customers
        customer.reload()
        customer2 = CustomerProfile.objects.get('c_2')
        c1_events = list(Event.objects.range_query(start, end, customer))
        c2_events = list(Event.objects.range_query(start, end, customer2))

        # import ipdb; ipdb.set_trace()
        self.assertEqual(len(c1_events), 4)
        self.assertEqual({e.platform for e in c1_events}, {'ET1', 'ET2', TwitterPost.platform})

        self.assertEqual(len(c2_events), 3)
        self.assertEqual({e.platform for e in c2_events}, {'ET2', FacebookPost.platform})

        tw_profile = customer.linked_profiles[0]
        fb_profile = customer2.linked_profiles[0]

        self.assertEqual(tw_profile.native_id, tw_post_data['user_profile']['user_id'])
        self.assertEqual(fb_profile.native_id, fb_post_data['user_profile']['user_id'])

        # new non-dynamic post which doesn't has corresponding id for customer profile
        create_post(self.user, sync=True, **{
            'channels': [tw_channel.id],
            'content': "another twitter post",
            'user_profile': {
                'user_id': 'new_customer',
                'name': 'New Twitter',
            },
            'twitter': {
                'id': '80003874',
            }
        })
        end = now() + one_sec  # because of added padding while created event_id,
                               # we could reach next second

        # we must still have 4 posts (with 1 twitter post) by c_1 customer
        self.assertEqual(Event.objects.range_query_count(start, end, customer), 4)

        # check for new customer created with twitter linked profile
        new_customer = CustomerProfile.objects.get('new_customer')
        self.assertIsNotNone(new_customer)
        self.assertIsInstance(new_customer.linked_profiles[0], TwitterPost.PROFILE_CLASS)

        # check we can find our last twitter event in range query
        new_customer_events = Event.objects.range_query_count(start, end, new_customer)
        self.assertEqual(new_customer_events, 1)

        # Cleanup
        remove_account(samples.sample2)
