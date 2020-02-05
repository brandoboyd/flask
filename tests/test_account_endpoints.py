# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
from solariat_bottle.configurable_apps import CONFIGURABLE_APPS
from solariat_bottle.db.account import Package, AccountEvent
from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.roles import STAFF

from .base import UICaseSimple


class LockedAccountCase(UICaseSimple):
    def setUp(self):
        super(LockedAccountCase, self).setUp()

        self.user.user_roles = [STAFF]
        self.user.save()
        self.login()
        self.lock_account()
        self.assertEqual(AccountEvent.objects().count(), 2)

    def lock_account(self):
        data = self._post('/account/lock', dict(id=str(self.user.account.id)))
        self.assertEqual(data['ok'], True)

    def unlock_account(self):
        data = self._post('/account/unlock', dict(id=str(self.user.account.id)))
        self.assertEqual(data['ok'], True)

    def assert_lock_error(self, data):
        self.assertEqual(data['ok'], False, data)
        self.assertTrue('Account is locked' in data['error'], data['error'])


class AccountEndpointCase(LockedAccountCase):
    def test_new_fields(self):
        # testing that list view has necessary fields
        data = self._get('/accounts/json', {})
        self.assertEqual(data['ok'], True)
        account_data = data['data'][0]
        self.assertTrue('updated_at' in account_data)
        self.assertTrue('is_locked' in account_data)

    def test_account_delete(self):
        endpoint = '/accounts/json?id=%s' % self.account.id

        data = self._delete(endpoint, {}, expected_result=False)
        self.assert_lock_error(data)

        self.unlock_account()
        data = self._delete(endpoint, {}, expected_result=False)
        self.assertEqual(data['error'], "Can't delete current account.")

    def test_account_configured_apps(self):
        self.assertEqual(self.account.selected_app, self.account.DEFAULT_APP_KEYS[0])
        self.assertEqual(len(self.account.available_apps), len(self.account.DEFAULT_APPS))

        self.unlock_account()
        update_data = {'configured_apps': CONFIGURABLE_APPS.keys()[:2],
                       'selected_app': CONFIGURABLE_APPS.keys()[0],
                       'name': self.user.account.name,
                       'id': str(self.account.id)}
        endpoint = '/accounts/json'

        # and try to update
        data = self._put(endpoint, update_data)
        self.account.reload()

        self.assertEqual(self.account.selected_app, CONFIGURABLE_APPS.keys()[0])
        self.assertEqual(len(self.account.available_apps), 2)

        # Now try to update, invalid selected_app
        update_data = {'selected_app': CONFIGURABLE_APPS.keys()[0] + 'invalid',
                       'name': self.user.account.name,
                       'id': str(self.account.id)}
        # Note: disabled due to commit eef4f0188cc53a7addb64cfed533f40c73a900b0
        # self._put(endpoint, update_data, expected_result=False)
        # self.account.reload()
        # self.assertEqual(self.account.selected_app, CONFIGURABLE_APPS.keys()[0])

        # Try to set some configured apps that are invalid
        update_data = {'configured_apps': ['invalid_app1', 'invalid_app2', 'invalid_app3'],
                       'name': self.user.account.name,
                       'id': str(self.account.id)}
        self._put(endpoint, update_data, expected_result=False)
        self.account.reload()
        self.assertEqual(len(self.account.available_apps), 2)

    def test_account_update(self):
        old_account_name = self.user.account.name
        new_account_name = "locking test"
        account_update_data = {
            'name': new_account_name,
            'package': str(Package.objects()[0].name),
            'id': str(self.user.account.id),
        }
        endpoint = '/accounts/json'

        # and try to update
        data = self._put(endpoint, account_update_data, expected_result=False)
        self.assert_lock_error(data)
        self.assertEqual(AccountEvent.objects().count(), 2)

        # unlock account
        self.unlock_account()
        self.assertEqual(AccountEvent.objects().count(), 3)

        # and try to update
        data = self._put('/accounts/json', account_update_data)
        self.user.account.reload()
        self.assertEqual(self.user.account.name, new_account_name)
        self.assertEqual(AccountEvent.objects().count(), 4)

        # now lets get all account events
        request_data = dict(
            id=str(self.user.account.id),
            limit=1
        )
        events = []
        while True:
            resp = self._post('/account/events', request_data)
            events.extend(resp['data'])
            request_data.update(cursor=resp['cursor'])
            if not resp['cursor']:
                break

        self.assertEqual(len(events), 4)
        # events are in decreasing order of 'created_at'
        last_account_event = events[0]
        self.assertTrue('name' in last_account_event['new_changed_fields'])
        self.assertTrue('name' in last_account_event['old_changed_fields'])
        self.assertTrue('package' in last_account_event['new_changed_fields'])
        self.assertTrue('package' in last_account_event['old_changed_fields'])


class ChannelStatusEndpointCase(LockedAccountCase):
    def setUp(self):
        super(ChannelStatusEndpointCase, self).setUp()

        self.channel_update_data = dict(channels=[self.channel_id])

    def test_channel_deactivate(self):
        endpoint = '/commands/suspend_channel'

        data = self._post(endpoint, self.channel_update_data, False)
        self.assert_lock_error(data)

        self.unlock_account()
        data = self._post(endpoint, self.channel_update_data)
        self.channel.reload()
        self.assertEqual(self.channel.status, 'Suspended')

    def test_channel_activate(self):
        endpoint = '/commands/activate_channel'

        self.channel.status = 'Suspended'
        self.channel.save()

        data = self._post(endpoint, self.channel_update_data, False)
        self.assert_lock_error(data)

        self.unlock_account()
        data = self._post(endpoint, self.channel_update_data)
        self.channel.reload()
        self.assertEqual(self.channel.status, 'Active')

    def test_channel_delete(self):
        endpoint = '/commands/delete_channel'

        data = self._post(endpoint, self.channel_update_data, False)
        self.assert_lock_error(data)

        self.unlock_account()
        data = self._post(endpoint, self.channel_update_data)
        self.channel.reload()
        self.assertEqual(self.channel.status, 'Archived')


class ChannelEndpointCase(LockedAccountCase):
    def setUp(self):
        super(ChannelEndpointCase, self).setUp()

    def test_channel_update(self):
        old_channel_title = self.channel.title
        new_channel_title = 'locking_test'
        channel_update_data = {
            'title': new_channel_title,
            'channel_id': self.channel_id,
        }
        endpoint = '/configure/channel_update/json'

        data = self._post(endpoint, channel_update_data, False)
        self.assert_lock_error(data)

        self.unlock_account()
        data = self._post(endpoint, channel_update_data)
        self.channel.reload()
        self.assertEqual(self.channel.title, new_channel_title)

    def test_channel_add(self):
        new_channel_data = {
                'title': 'FBS',
                'type': 'facebookservice',
                'description': 'fbs desc',
        }
        endpoint = '/configure/channels/json'

        data = self._post(endpoint, new_channel_data, False)
        self.assert_lock_error(data)

        self.unlock_account()
        data = self._post(endpoint, new_channel_data)
        latest_channel = list(Channel.objects.find())[-1]
        self.assertEqual(latest_channel.title, '%s Outbound' % new_channel_data['title'])
