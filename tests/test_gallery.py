import json
from nose.tools import eq_, assert_in

from solariat_bottle.tests.base import UICaseSimple
from solariat_bottle.db.dashboard import insert_default_dashboard_types
from solariat_bottle.db.gallery import Gallery, WidgetModel, insert_prebuilt_galleries


class GalleryViewTest(UICaseSimple):

    def setUp(self):
        super(GalleryViewTest, self).setUp()
        db_types = insert_default_dashboard_types()
        self.db_types_name2id = {each.type: str(each.id) for each in db_types}

        self.login()

    def _create(self, data):
        resp = self.client.post('/gallery', data=json.dumps(data))
        return resp

    def test_create(self):
        data = dict(
                dashboard_type = self.db_types_name2id['journeys'],
        )
        resp = self._create(data)

        eq_(resp.status_code, 201)
        eq_(Gallery.objects.count(), 1)

        data = json.loads(resp.data)
        eq_(data['ok'], True)
        for each in ['id', 'dashboard_type', 'widget_models', 'created']:
            assert_in(each, data['data'])

    def test_read_many(self):
        for db_type in self.db_types_name2id:
            data = dict(
                    dashboard_type = self.db_types_name2id[db_type],
            )
            self._create(data)

        resp = self.client.get('/gallery')
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        galleries = data['data']

        eq_(len(galleries), len(self.db_types_name2id))

        for gallery in galleries:
            for each in ['id', 'dashboard_type', 'widget_models', 'created']:
                assert_in(each, gallery)

    def test_read_single(self):
        data = dict(
                dashboard_type = self.db_types_name2id['journeys'],
        )
        resp = self._create(data)
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        gallery_id = data['data']['id']

        resp = self.client.get('/gallery/' + gallery_id)
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        eq_(gallery_id, data['data']['id'])

        for each in ['id', 'dashboard_type', 'widget_models', 'created']:
            assert_in(each, data['data'])
        eq_(data['data']['widget_models'], [])

    def test_read_single_with_widget_model(self):
        data = dict(
                dashboard_type = self.db_types_name2id['journeys'],
        )
        resp = self._create(data)
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        gallery_id = data['data']['id']

        # Create a widget model
        create_data = dict(
                title = 'First Journey Widget',
                settings = {
                    'request_url': '/journeys/plot',
                },
        )
        resp = self.client.post('/gallery/%s/widget_models' % gallery_id, data=json.dumps(create_data))
        data = json.loads(resp.data)
        eq_(data['ok'], True)

        resp = self.client.get('/gallery/' + gallery_id)
        data = json.loads(resp.data)
        eq_(data['ok'], True)

        for k, v in create_data.items():
            eq_(data['data']['widget_models'][0][k], v)

    def test_get_gallery_by_type(self):
        galleries = insert_prebuilt_galleries()
        self.gallery_type2id = {each.dashboard_type.type: str(each.id) for each in galleries}
        gallery_id = self.gallery_type2id['journeys']

        # Create a widget model
        create_data = dict(
                title = 'First Journey Widget',
                settings = {
                    'request_url': '/journeys/plot',
                },
        )
        resp = self.client.post('/gallery/%s/widget_models' % gallery_id, data=json.dumps(create_data))
        data = json.loads(resp.data)
        eq_(data['ok'], True)

        params = dict(dashboard_type=self.db_types_name2id['journeys'])
        resp = self.client.get('/gallery', data=json.dumps(params))
        data = json.loads(resp.data)
        eq_(data['ok'], True)

        eq_(len(data['data']), 1)

    def test_update(self):
        data = dict(
                dashboard_type = self.db_types_name2id['journeys'],
        )
        resp = self._create(data)
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        gallery_id = data['data']['id']

        resp = self.client.put('/gallery/' + gallery_id, data=json.dumps(data))
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        eq_(gallery_id, data['data']['id'])

        for each in ['id', 'dashboard_type', 'widget_models', 'created']:
            assert_in(each, data['data'])

    def test_delete(self):
        data = dict(
                dashboard_type = self.db_types_name2id['journeys'],
        )
        resp = self._create(data)
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        gallery_id = data['data']['id']

        resp = self.client.delete('/gallery/' + gallery_id)
        eq_(resp.data, '')
        eq_(Gallery.objects.count(), 0)


class WidgetModelViewTest(UICaseSimple):

    def setUp(self):
        super(WidgetModelViewTest, self).setUp()
        db_types = insert_default_dashboard_types()
        self.db_types_name2id = {each.type: str(each.id) for each in db_types}

        galleries = insert_prebuilt_galleries()
        self.gallery_type2id = {each.dashboard_type.type: str(each.id) for each in galleries}

        self.login()

    def _create(self, gallery_id, data):
        resp = self.client.post('/gallery/%s/widget_models' % gallery_id, data=json.dumps(data))
        return resp

    def test_create(self):
        create_data = dict(
                title = 'First Journey Widget',
                description = '',
                settings = {
                    'extra_settings': {
                        'x-axis_label': 'Time Series',
                        'y-axis_label': 'NPS Count',
                    },
                    'request_url': '/journeys/plot',
                },
        )
        resp = self._create(self.gallery_type2id['journeys'], create_data)
        data = json.loads(resp.data)
        eq_(data['ok'], True)

        eq_(resp.status_code, 201)
        eq_(WidgetModel.objects.count(), 1)
        eq_(str(Gallery.objects.get(self.gallery_type2id['journeys']).widget_models[0].id), data['data']['id'])

        for each in ['id', 'title', 'description', 'settings', 'created']:
            assert_in(each, data['data'])

        eq_(data['data']['settings'], create_data['settings'])

    def test_read_many(self):
        total_to_insert = 10
        for i in xrange(total_to_insert):
            create_data = dict(
                    title = '#%d Journey Widget' % (i+1),
                    settings = {
                        'request_url': '/journeys/plot',
                    },
            )
            self._create(self.gallery_type2id['journeys'], create_data)

        resp = self.client.get('/gallery/%s/widget_models' % self.gallery_type2id['journeys'])
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        widget_models = data['data']

        eq_(len(widget_models), total_to_insert)
        eq_(len(Gallery.objects.get(self.gallery_type2id['journeys']).widget_models), total_to_insert)

    def test_read_single(self):
        create_data = dict(
                title = 'First Journey Widget',
                settings = {
                    'request_url': '/journeys/plot',
                },
        )
        resp = self._create(self.gallery_type2id['journeys'], create_data)
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        widget_model_id = data['data']['id']

        resp = self.client.get('/gallery/%s/widget_models/%s' %
                (self.gallery_type2id['journeys'], widget_model_id))
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        eq_(widget_model_id, data['data']['id'])
        eq_(len(Gallery.objects.get(self.gallery_type2id['journeys']).widget_models), 1)

    def test_update(self):
        create_data = dict(
                title = 'First Journey Widget',
                settings = {
                    'request_url': '/journeys/plot',
                },
        )
        resp = self._create(self.gallery_type2id['journeys'], create_data)
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        widget_model_id = data['data']['id']

        updated_title = data['title'] = 'journeys optimization'
        resp = self.client.put('/gallery/%s/widget_models/%s' %
                (self.gallery_type2id['journeys'], widget_model_id),
                data=json.dumps(data)
        )
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        eq_(widget_model_id, data['data']['id'])
        eq_(updated_title, data['data']['title'])

    def test_delete(self):
        create_data = dict(
                title = 'First Journey Widget',
                settings = {
                    'request_url': '/journeys/plot',
                },
        )
        resp = self._create(self.gallery_type2id['journeys'], create_data)
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        widget_model_id = data['data']['id']

        eq_(WidgetModel.objects.count(), 1)
        eq_(len(Gallery.objects.get(self.gallery_type2id['journeys']).widget_models), 1)

        resp = self.client.delete('/gallery/%s/widget_models/%s' %
                (self.gallery_type2id['journeys'], widget_model_id))
        eq_(resp.data, '')

        eq_(WidgetModel.objects.count(), 0)
        eq_(len(Gallery.objects.get(self.gallery_type2id['journeys']).widget_models), 0)


class InstantiateWidgetModelViewTest(UICaseSimple):

    def setUp(self):
        super(InstantiateWidgetModelViewTest, self).setUp()
        db_types = insert_default_dashboard_types()
        self.db_types_name2id = {each.type: str(each.id) for each in db_types}

        galleries = insert_prebuilt_galleries()
        self.gallery_type2id = {each.dashboard_type.type: str(each.id) for each in galleries}

        self.login()

    def test_add_to_dashboard(self):
        # create a widget_model
        create_data = dict(
                title = 'First Journey Widget',
                settings = {
                    'request_url': '/journeys/plot',
                },
        )
        gallery_id = self.gallery_type2id['journeys']
        resp = self.client.post('/gallery/%s/widget_models' % gallery_id, data=json.dumps(create_data))
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        widget_model_id = data['data']['id']

        # get the first dashboard
        resp = self.client.get('/dashboards')
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        dashboard_id = data['data'][0]['id']

        data = {'dashboard_id': dashboard_id}
        resp = self.client.put('/instantiate_widget_models/%s' % widget_model_id, data=json.dumps(data))
        data = json.loads(resp.data)
        eq_(data['ok'], True)
        dashboard = data['data']
        eq_(len(dashboard['widgets']), 1)

        widget_id = dashboard['widgets'][0]
        resp = self.client.get('/dashboard/%s/widget' % widget_id)
        data = json.loads(resp.data)
        eq_(data['ok'], True)

        actual_data = {
                'title': data['item']['title'],
                'request_url': data['item']['request_url'],
        }
        expected_data = {
                'title': create_data['title'],
                'request_url': create_data['settings']['request_url'],
        }
        eq_(actual_data, expected_data)
