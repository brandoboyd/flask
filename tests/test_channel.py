from solariat_bottle.db.user_profiles.base_platform_profile import UserProfile
from .base import BaseCase, SA_TYPES

from ..db.channel.base import Channel
from ..db.channel.twitter import (UserTrackingChannel, TwitterServiceChannel,
                                  EnterpriseTwitterChannel)
from ..db.channel.facebook import EnterpriseFacebookChannel as EFC, FacebookServiceChannel
from ..db.roles import AGENT, ADMIN

from solariat.db import fields

from solariat_bottle.tasks import postprocess_new_post


class ChannelCase(BaseCase):
    def setUp(self):
        BaseCase.setUp(self)

    def test_title_required(self):
        self.assertRaises(
            fields.ValidationError,
            Channel.objects.create,
            description='foo')

    def test_creation(self):
        channel = Channel.objects.create(
            title='Foo',
            description='bar',
            moderated_relevance_threshold=0.5)
        self.assertEqual(
            channel.moderated_relevance_threshold, 0.5)
        self.assertEqual(
            channel.auto_reply_intention_threshold, 1.0)
        self.assertEqual(channel.counter, Channel.objects.count())

    def test_delete(self):
        channel = Channel.objects.create(title='Foo')
        self.assertEqual(
            Channel.objects.count(), 2)
        channel.delete()
        self.assertEqual(
            Channel.objects.count(), 1)

    def test_class_hierarchy(self):
        self.user.account = None
        self.user.is_superuser = True
        self.user.save()
        channel = EFC.objects.create_by_user(self.user, title='facebook test')

        self.assertEqual(Channel.objects.get_by_user(self.user, id=channel.id).__class__.__name__,
                         'EnterpriseFacebookChannel')

        self.assertEqual(list(Channel.objects.find_by_user(self.user, id=channel.id))[0].__class__.__name__,
                         'EnterpriseFacebookChannel')


class DirectMessageChannelResolveTest(BaseCase):
    def test_twitter_direct_message_handle(self):
        """
        Test that a given channel has or doesn't have permissions to a given
        twitter handle depending on the configurations on the account.
        """
        from ..db.channel.twitter import EnterpriseTwitterChannel
        ChannelCls = EnterpriseTwitterChannel

        testing_handle = 'some_twitter_handle'

        sc = TwitterServiceChannel.objects.create_by_user(
            self.user,
            account=str(self.account.id),
            title="Test Service Channel")

        tracking_channel = sc.outbound_channel
        self.assertEqual(tracking_channel.account, self.user.account)

        # No outbound channel configured for the account, so should fail
        self.assertFalse(tracking_channel.has_private_access(testing_handle, testing_handle),
                         "No outbound is configured for Twitter, no access should be given.")

        self.assertEqual(self.user.get_outbound_channel("Twitter"), None)

        # Set for account and check defaults
        outbound_channel = ChannelCls.objects.create_by_user(
            self.user, title='Outbound1',
            type='twitter', intention_types=SA_TYPES,
            account=str(self.account.id))
        outbound_channel.status = 'Active'
        outbound_channel.save()
        self.account.outbound_channels[outbound_channel.platform] = outbound_channel.id
        self.account.save()

        self.assertEqual(self.user.get_outbound_channel("Twitter").id,
                         outbound_channel.id)
        self.assertFalse(tracking_channel.has_private_access(testing_handle, testing_handle),
                         "Outbound channel has no handle configured.")
        self.assertFalse(outbound_channel.has_private_access(testing_handle, testing_handle),
                         "Outbound channel has no handle configured.")

        # Assume we would have configured the twitter handle
        outbound_channel.twitter_handle = testing_handle
        outbound_channel.save()

        self.assertTrue(tracking_channel.has_private_access(testing_handle, testing_handle),
                        "All conditions should be met at this point.")
        self.assertTrue(outbound_channel.has_private_access(testing_handle, testing_handle),
                        "All conditions should be met at this point.")

        new_user = self._create_db_user(email='new_db_user@test.com', password='password',
                                        roles=[AGENT])
        sc.add_perm(new_user)
        sc.del_perm(self.user)
        self.assertFalse(tracking_channel.has_private_access(testing_handle, testing_handle),
                         "Tracking channel no longer has same permissions. Access should be denied.")
        self.assertTrue(outbound_channel.has_private_access(testing_handle, testing_handle),
                        "All conditions should be met at this point.")
        outbound_channel.add_perm(new_user)
        self.assertTrue(tracking_channel.has_private_access(testing_handle, testing_handle),
                        "All conditions should be met at this point.")
        self.assertTrue(outbound_channel.has_private_access(testing_handle, testing_handle),
                        "All conditions should be met at this point.")

        outbound_channel.status = 'Suspended'
        outbound_channel.save()
        self.assertFalse(tracking_channel.has_private_access(testing_handle, testing_handle),
                         "Outbound channel is not active at this point.")
        self.assertFalse(outbound_channel.has_private_access(testing_handle, testing_handle),
                         "Outbound channel is not active at this point.")

        outbound_channel.status = 'Active'
        outbound_channel.save()
        self.assertTrue(tracking_channel.has_private_access(testing_handle, testing_handle),
                        "All conditions should be met at this point.")
        self.assertTrue(outbound_channel.has_private_access(testing_handle, testing_handle),
                        "All conditions should be met at this point.")

    def setup_channels(self, brand_name, user=None, user2=None):
        user = user or self.user
        channel = TwitterServiceChannel.objects.create_by_user(user, title='TSC-' + brand_name)
        channel.inbound_channel.add_perm(user)
        channel.add_keyword('carrot')
        channel.add_username(brand_name)
        user2 = user2 or user
        dispatch_channel = EnterpriseTwitterChannel.objects.create_by_user(
            user2,
            title='ETC-' + brand_name,
            twitter_handle=brand_name,
            access_token_key='nonempty',
            access_token_secret='nonempty')
        return channel, dispatch_channel

    def test_multiple_channels(self):
        # 2 pair of channels
        # 2 admins with different reply channel
        acct = 'TestAccount'
        su = self._create_db_user('su@test.test', account=acct, is_superuser=True)
        brand_one = 'test_brand_one'
        brand_two = 'test_brand_two'

        admin1 = self._create_db_user('admin1@test.test', account=acct, roles=[ADMIN])
        admin2 = self._create_db_user('admin2@test.test', account=acct, roles=[ADMIN])
        sc1, rc1 = self.setup_channels(brand_one, su, admin2)
        sc2, rc2 = self.setup_channels(brand_two, admin1, su)

        admin1.set_outbound_channel(rc1)
        admin2.set_outbound_channel(rc2)

        sender_name = None
        assert sc1.inbound_channel.has_private_access(sender_name, brand_one)
        assert sc1.inbound_channel.has_private_access(sender_name, brand_two)

        assert sc2.inbound_channel.has_private_access(sender_name, brand_one)
        assert sc2.inbound_channel.has_private_access(sender_name, brand_two)

        rcp_name = 'test_recipient'
        assert sc1.outbound_channel.has_private_access(brand_one, rcp_name)
        assert sc1.outbound_channel.has_private_access(brand_two, rcp_name)

        assert sc2.outbound_channel.has_private_access(brand_one, rcp_name)
        assert sc2.outbound_channel.has_private_access(brand_two, rcp_name)


class PersonalDataRemovalTest(ChannelCase):
    def test_personal_data_removal(self):
        ch = FacebookServiceChannel.objects.create_by_user(self.user, title='Fb', remove_personal=True)

        wrapped = dict(type="pm", source_id="fakeid", source_type="page", page_id="12345")
        fb = dict(_wrapped_data=wrapped, facebook_post_id="12345_54321", conversation_id="888")
        post = self._create_db_post(content='Test fb post', channel=ch, facebook=fb)

        # make sure personal data gets cleaned
        assert post.content == 'The content of this message was deleted'
        assert post.actor_id == UserProfile.anonymous_profile().id
