import json
from nose.tools import eq_, assert_in

from solariat.db import fields
from solariat_bottle.tests.base import UICaseSimple
from solariat_bottle.db.dashboard import Dashboard, insert_default_dashboard_types
from solariat_bottle.configurable_apps import APP_JOURNEYS


class DashboardTest(UICaseSimple):

    def setUp(self):
        super(DashboardTest, self).setUp()
        db_types = insert_default_dashboard_types()
        self.db_types_name2id = {each.type: str(each.id) for each in db_types}
        self.login()
        self.account.selected_app = APP_JOURNEYS
        self.account.save()

    def _create(self, data):
        resp = self.client.post('/dashboards', data=json.dumps(data))
        return resp

    def test_create(self):
        data = dict(
                type_id = self.db_types_name2id['journeys'],
                title = 'journeys'
        )
        resp = self._create(data)

        eq_(resp.status_code, 201)
        eq_(Dashboard.objects.count(), 1)

        d = Dashboard.objects.find_by_user(self.user).next()
        eq_(d.owner, self.user)

        data = json.loads(resp.data)
        eq_(data['ok'], True)
        for each in ['id', 'title', 'widgets']:
            assert_in(each, data['data'])

    def test_read_many(self):
        titles = ['journeys', 'advisors', 'conversation']
        for title in titles:
            data = dict(
                    type_id = self.db_types_name2id['journeys'],
                    title = title
            )
            self._create(data)

        resp = self.client.get('/dashboards')
        data = json.loads(resp.data)
        dashboards = data['data']

        eq_(len(dashboards), len(titles))

        for dashboard in dashboards:
            for each in ['id', 'title', 'widgets']:
                assert_in(each, dashboard)

    def test_read_single(self):
        data = dict(
                type_id = self.db_types_name2id['journeys'],
                title = 'journeys'
        )
        resp = self._create(data)
        data = json.loads(resp.data)
        dashboard_id = data['data']['id']

        resp = self.client.get('/dashboards/' + dashboard_id)
        data = json.loads(resp.data)
        eq_(dashboard_id, data['data']['id'])

        for each in ['id', 'title', 'widgets']:
            assert_in(each, data['data'])

    def test_update(self):
        data = dict(
                type_id = self.db_types_name2id['journeys'],
                title = 'journeys'
        )
        resp = self._create(data)
        data = json.loads(resp.data)
        dashboard_id = data['data']['id']

        updated_title = data['title'] = 'journeys optimization'
        # use self user for now as we don't have another user
        updated_shared_to = data['shared_to'] = [str(self.user.id)]

        resp = self.client.put('/dashboards/' + dashboard_id, data=json.dumps(data))
        data = json.loads(resp.data)
        eq_(dashboard_id, data['data']['id'])
        eq_(updated_title, data['data']['title'])
        eq_(updated_shared_to, data['data']['shared_to'])
        eq_(updated_title, Dashboard.objects.get().title)
        eq_(fields.ObjectId(updated_shared_to[0]), Dashboard.objects.get().shared_to[0])

        for each in ['id', 'title', 'widgets']:
            assert_in(each, data['data'])

    def test_delete(self):
        data = dict(
                type_id = self.db_types_name2id['journeys'],
                title = 'journeys'
        )
        resp = self._create(data)
        data = json.loads(resp.data)
        dashboard_id = data['data']['id']

        resp = self.client.delete('/dashboards/' + dashboard_id)
        eq_(resp.data, '')
        eq_(Dashboard.objects.count(), 0)

    def test_copy_dashboard(self):
        create_data = dict(
                type_id = self.db_types_name2id['journeys'],
                title = 'journeys'
        )
        resp = self._create(create_data)
        resp_data = json.loads(resp.data)
        dashboard_id = resp_data['data']['id']

        copy_data = dict(
                title = 'journeys copy',
                description = 'Dashboard copied from %s' % dashboard_id
        )

        copy_resp = self.client.post('/dashboards/%s/copy' % dashboard_id, data=json.dumps(copy_data))
        copy_resp_data = json.loads(copy_resp.data)
        eq_(copy_resp_data['data']['title'], copy_data['title'])
        eq_(copy_resp_data['data']['description'], copy_data['description'])
