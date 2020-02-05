import json

from solariat_bottle.tests.base import UICaseSimple
from solariat_bottle.commands.configure import DeleteChannel
from solariat_bottle.db.channel.base import ServiceChannel
from solariat_bottle.db.dashboard import DashboardType, Dashboard


class AccountActionsTest(UICaseSimple):
    
    def _check_widgets(self, expected_widgets):

        blank_dashboard_type = DashboardType.objects.get(type='blank')
        blank_dashboard = Dashboard.objects.get_by_user(self.user, type_id=blank_dashboard_type.id)
        for w in expected_widgets:
            w['dashboard_id'] = str(blank_dashboard.id)

        actual_widgets_set = set(str(each) for each in blank_dashboard.widgets)
        expected_widgets_set = set(each['id'] for each in expected_widgets)
        self.assertSetEqual(expected_widgets_set, actual_widgets_set)

        resp = self.client.get('/dashboard/list')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertEqual(len(resp['list']), len(expected_widgets))
        new_list = resp['list']
        for idx in xrange(len(new_list)):
            expected = sorted(expected_widgets, key=lambda x: x['order'])[idx]
            actual = sorted(new_list, key=lambda x: x['order'])[idx]
            self.assertDictEqual(expected, actual)

    def _assert_not_ok(self, resp):
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])
    
    def test_dashboard_setup(self):
        self.login()

        widgets = [{'title': 'widget1', 'order': 0, 'dummy': 0},
                   {'title': 'widget2', 'order': 1, 'dummy': 1},
                   {'title': 'widget3', 'order': 2, 'dummy': 2}, ]
        # First create a bunch of widgets
        for data in widgets:
            resp = self.client.post('/dashboard/new', data=json.dumps(data),
                                    content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            resp = json.loads(resp.data)
            self.assertTrue(resp['ok'])
            data['id'] = resp['item']['id']
            
        # Now create another widget with no order and check we get incremented order
        new_widget = {'title': 'widget4', 'dummy': 4}
        resp = self.client.post('/dashboard/new', data=json.dumps(new_widget),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        new_widget['id'] = resp['item']['id']
        computed_order = int(resp['item']['order'])
        self.assertEqual(computed_order, 3)
        new_widget['order'] = computed_order
        widgets.append(new_widget)
        self._check_widgets(widgets)

        # Test editing some settings of a widget
        widgets[2]['dummy'] = 'new_dummy'
        self.client.post('/dashboard/' + widgets[2]['id'] + '/update',
                         data=json.dumps(widgets[2]),
                         content_type='application/json')
        self._check_widgets(widgets)

        # Test if we just edit title and pass no settings
        self.client.post('/dashboard/' + widgets[2]['id'] + '/update',
                         data=json.dumps({'title': widgets[2]['title']}),
                         content_type='application/json')
        self._check_widgets(widgets)
        
        # Test widget reordering
        widgets[0]['order'] = 3
        widgets[1]['order'] = 0
        widgets[2]['order'] = 2
        widgets[3]['order'] = 1
        self.client.post(
            '/dashboard/reorder', content_type='application/json',
            data=json.dumps(
                {widget['id']: widget['order'] for widget in widgets}
            ))
        self._check_widgets(widgets)

        # Remove a widget, check that it's no longer returned
        self.client.delete('/dashboard/' + widgets[3]['id'] + '/remove',
                           content_type='application/json')
        widgets = widgets[:3]
        self._check_widgets(widgets)

        # Remove a widget, that does not exist
        resp = self.client.delete('/dashboard/101/remove',
                                  content_type='application/json')
        self._assert_not_ok(resp)

        # Update a widget that does not exist
        resp = self.client.post('/dashboard/102/update',
                                data=json.dumps({'title': widgets[2]['title']}),
                                content_type='application/json')
        self._assert_not_ok(resp)

        # Reorder non existing widget
        resp = self.client.post(
            '/dashboard/reorder', content_type='application/json',
            data=json.dumps({103: 0})
        )
        self._assert_not_ok(resp)

    def test_channel_deletion(self):
        self.login()

        """ Test that when a chanel is deleted, all it's corresponding widgets are also removed. """
        s_c = ServiceChannel.objects.create_by_user(self.user, title="Test Channel")
        s_c.status = 'Suspended'
        s_c.save()
        widgets = [{'title': 'widget1', 'order': 0, 'settings': {'channel_id': str(s_c.inbound)}},   # Part of inbound
                   {'title': 'widget2', 'order': 0, 'settings': {'channel_id': str(s_c.outbound)}},  # Part of outbound
                   {'title': 'widget3', 'order': 0, 'settings': {'channel_id': str(s_c.id)}},        # Part of service
                   {'title': 'widget4', 'order': 0}]
        for data in widgets:
            resp = self.client.post('/dashboard/new', data=json.dumps(data),
                                    content_type='application/json')
            self.assertEqual(resp.status_code, 200)
            resp = json.loads(resp.data)
            self.assertTrue(resp['ok'])
            data['id'] = resp['item']['id']
        self._check_widgets(widgets)
        # print "Status of the current channel is " + str(s_c.status)
        # Delete the service channel, expect only one widget remains (first 3 would get removed)
        DeleteChannel(channels=[s_c]).update_state(self.user)

        resp = self.client.get('/dashboard/list')
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertEqual(len(resp['list']), 1)
        returned_widget = resp['list'][0]
        self.assertEqual(returned_widget['title'], 'widget4')



