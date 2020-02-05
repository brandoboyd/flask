from collections import defaultdict

from mock import patch

from solariat_bottle.db.channel.facebook import FacebookServiceChannel

from solariat_bottle.tests.base import UICaseSimple
from solariat_bottle.db.facebook_tracking import FacebookTracking, PAGE, EVENT


class TestFacebookTracking(UICaseSimple):
    will = {
        "updated_time": "2016-06-21T11:28:40 +0000",
        "user_name": "Will Login Dingleman",
        "link": "https://www.facebook.com/app_scoped_user_id/138144799912356/",
        "last_name": "Dingleman", "id": "138144799912356",
        "middle_name": "Login", "first_name": "Will"}

    lisa = {
        "user_name": "Lisaband",
        "profile_image_url": "https://scontent.xx.fbcdn.net/1.png",
        "id": "998309733582959"}

    page_id = "998309733582959"
    posts_data = [
        # public message sample
        {"page_id": "998309733582959_1083835218363743",
         "facebook_post_id": "1083835218363743_1083838538363411",
         "_wrapped_data": {"can_hide": 0, "can_remove": 0, "user_likes": 1,
                           "visibility": "Normal", "created_by_admin": True, "is_hidden": False,
                           "created_at": "2016-08-01T18:15:31 +0000", "source_type": "Page",
                           "message": "Lisa comment  #2", "type": "Comment",
                           "can_comment": 0, "can_like": 0,
                           "parent_id": "998309733582959_1083835218363743",
                           "from": lisa,
                           "id": "1083835218363743_1083838538363411",
                           "source_id": "998309733582959_1083835218363743"},
         "in_reply_to_status_id": "998309733582959_1083835218363743",
         "created_at": "2016-08-01T18:15:31 +0000",
         "root_post": "998309733582959_1083835218363743", "second_level_reply": False},

        # private message sample
        {u'facebook_post_id': u'm_mid.1467235850858:01c50ea51006e38449', u'_wrapped_data': {
            u'from': lisa,
            u'source_type': u'PM', u'created_by_admin': True,
            u'created_at': u'2016-06-29T21:30:50 +0000',
            u'inbox_url': u'https://www.facebook.comnull',
            u'to': will,
            u'source_id': u't_mid.1467235818867:fb0791a508db32a096',
            u'message': u'Hello', u'type': u'pm',
            u'id': u'm_mid.1467235850858:01c50ea51006e38449'},
         u'created_at': u'2016-06-29T21:30:50 +0000',
         u'in_reply_to_status_id': u'm_mid.1467235818867:fb0791a508db32a096',
         u'root_post': u'm_mid.1467235818867:fb0791a508db32a096',
         u'conversation_id': u't_mid.1467235818867:fb0791a508db32a096',
         u'page_id': page_id}
    ]

    def test_facebook_tracking_manager(self):
        facebook_page_ids = ["998309733582959", "297414983930888"]
        tracked_fb_event_ids = ["123456", "789012"]
        facebook_handle_id = facebook_page_ids[0]

        ch_params = dict(facebook_handle_id=facebook_handle_id,
                         facebook_page_ids=facebook_page_ids,
                         tracked_fb_event_ids=tracked_fb_event_ids,
                         posts_tracking_enabled=True)
        fbs1 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS1', **ch_params)
        fbs2 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS2', **ch_params)

        invalid_parameters = [
            (("suspend", fbs1, [], PAGE), "Unexpected event 'suspend'"),
            (("add", self, [], PAGE), "{} is not instance of FacebookServiceChannel".format(self)),
            (("add", fbs1, fbs1.id, PAGE), "{} is not instance of (<type 'list'>, <type 'tuple'>, <type 'set'>)".format(fbs1.id)),
            (("add", fbs1, fbs1.facebook_page_ids, -123), "Unexpected object type '-123'")
        ]

        for params, error in invalid_parameters:
            with self.assertRaises(AssertionError) as exc:
                FacebookTracking.objects.handle_channel_event(*params)
            self.assertEqual(str(exc.exception), error)

        # cleanup all tracked objects
        FacebookTracking.objects.coll.remove()

        valid_parameters = [
            ("add", fbs1, fbs1.facebook_page_ids, PAGE),
            ("add", fbs1, fbs1.tracked_fb_event_ids, EVENT),
            ("add", fbs2, fbs2.facebook_page_ids, PAGE),
            ("add", fbs2, fbs2.tracked_fb_event_ids, EVENT),
            ("remove", fbs1, fbs1.facebook_page_ids, PAGE),
            ("remove", fbs1, fbs1.tracked_fb_event_ids, EVENT),
            ("remove", fbs2, fbs2.facebook_page_ids, PAGE),
            ("remove", fbs2, fbs2.tracked_fb_event_ids, EVENT)
        ]

        expected_objects = defaultdict(list)
        for params in valid_parameters:
            self._handle_channel_event(expected_objects, params)
            FacebookTracking.objects.handle_channel_event(*params)
            self.assertEqual(self._get_tracking_items(), expected_objects)

            for (object_id, _), channels in expected_objects.viewitems():
                assert channels
                self.assertEqual(set(FacebookTracking.objects.find_channels([object_id])), set(channels))

    @staticmethod
    def _get_tracking_items():
        result = defaultdict(list)
        for tracking_item in FacebookTracking.objects():
            object_id, object_type, channels = tracking_item.object_id, tracking_item.object_type, tracking_item.channels
            result[(object_id, object_type)].extend(channels)
        return result

    @staticmethod
    def _handle_channel_event(expected_objects, params):
        event, channel, object_ids, object_type = params
        for object_id in object_ids:
            if event == 'add':
                expected_objects[(object_id, object_type)].append(channel)
            elif event == 'remove':
                try:
                    expected_objects[(object_id, object_type)].remove(channel)
                except (KeyError, IndexError):
                    pass
                else:
                    if not expected_objects[(object_id, object_type)]:
                        del expected_objects[(object_id, object_type)]
        return expected_objects

    @patch("solariat_bottle.db.channel.facebook.update_page_admins")
    @patch("solariat_bottle.db.channel.facebook.unsubscribe_realtime_updates")
    @patch("solariat_bottle.db.channel.facebook.subscribe_realtime_updates")
    def test_channel_updates_ui(self, *patched_methods):
        self.login()
        facebook_page_ids = ["998309733582959", "297414983930888"]
        tracked_fb_event_ids = ["123456", "789012"]
        facebook_handle_id = facebook_page_ids[0]

        ch_params = dict(facebook_handle_id=facebook_handle_id,
                         facebook_page_ids=facebook_page_ids,
                         tracked_fb_event_ids=tracked_fb_event_ids,
                         status='Suspended',
                         posts_tracking_enabled=True)

        fbs1 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS1', **ch_params)
        fbs2 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS2')

        FacebookTracking.objects.coll.remove()
        expected_objects = defaultdict(list)
        self.assertEqual(self._get_tracking_items(), expected_objects)

        import json
        def post_commands(command_name, channel):
            data = {'channels': [str(channel.id)]}
            resp = self.client.post(
                '/commands/%s' % command_name,
                data=json.dumps(data), content_type='application/json')
            return resp

        def channel_items(action, object_type, object_id, channel):
            data = {object_type: {'id': object_id, 'name': object_id}}
            request_call = {"add": self.client.post, "remove": self.client.delete}[action]
            resp = request_call(
                "/channels/%s/fb/%s" % (channel.id, object_type),
                data=json.dumps(data), content_type='application/json')
            response = json.loads(resp.data)
            print response
            return response

        def Activate(channel):
            return lambda: post_commands('activate_channel', channel)

        def Suspend(channel):
            return lambda: post_commands('suspend_channel', channel)

        def Archive(channel):
            return lambda: post_commands('delete_channel', channel)

        def AddPage(channel, page_id):
            return lambda: channel_items("add", "pages", page_id, channel)

        def RemovePage(channel, page_id):
            return lambda: channel_items("remove", "pages", page_id, channel)

        def AddEvent(channel, event_id):
            return lambda: channel_items("add", "events", event_id, channel)

        def RemoveEvent(channel, event_id):
            return lambda: channel_items("remove", "events", event_id, channel)

        test_steps = [
            [
                Activate(fbs1),
                ("add", fbs1, fbs1.facebook_page_ids, PAGE),
                ("add", fbs1, fbs1.tracked_fb_event_ids, EVENT),
            ],
            [
                Suspend(fbs1),
                ("remove", fbs1, fbs1.facebook_page_ids, PAGE),
                ("remove", fbs1, fbs1.tracked_fb_event_ids, EVENT),
            ],
            [
                Activate(fbs1),
                ("add", fbs1, fbs1.facebook_page_ids, PAGE),
                ("add", fbs1, fbs1.tracked_fb_event_ids, EVENT),
            ],

            [
                Archive(fbs1),
                ("remove", fbs1, fbs1.facebook_page_ids, PAGE),
                ("remove", fbs1, fbs1.tracked_fb_event_ids, EVENT),
            ],

            # channel2
            [
                Activate(fbs2)
            ],
            [
                AddPage(fbs2, facebook_page_ids[0]),
                ("add", fbs2, [facebook_page_ids[0]], PAGE)
            ],
            [
                AddEvent(fbs2, tracked_fb_event_ids[0]),
                ("add", fbs2, [tracked_fb_event_ids[0]], EVENT)
            ],
            [
                RemovePage(fbs2, facebook_page_ids[0]),
                ("remove", fbs2, [facebook_page_ids[0]], PAGE)
            ],
            [
                RemoveEvent(fbs2, tracked_fb_event_ids[0]),
                ("remove", fbs2, [tracked_fb_event_ids[0]], EVENT)
            ],

            [
                AddPage(fbs2, facebook_page_ids[1]),
                ("add", fbs2, [facebook_page_ids[1]], PAGE)
            ]
        ]

        for num, step in enumerate(test_steps):
            for action in step:
                if isinstance(action, tuple):
                    self._handle_channel_event(expected_objects, action)
                else:
                    action()
            db_objects = self._get_tracking_items()
            self.assertEqual(db_objects, expected_objects,
                             msg="Failed on step #{}\n{} != {}".format(num + 1, db_objects, expected_objects))

    def test_channel_assignment_on_post_creation(self):
        facebook_page_ids = ["998309733582959", "297414983930888"]
        tracked_fb_event_ids = ["123456", "789012"]
        facebook_handle_id = facebook_page_ids[0]

        ch_params = dict(facebook_handle_id=facebook_handle_id,
                         facebook_page_ids=facebook_page_ids,
                         tracked_fb_event_ids=tracked_fb_event_ids,
                         posts_tracking_enabled=True)

        fbs1 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS1')
        fbs2 = FacebookServiceChannel.objects.create_by_user(self.user, title='FBS2', **ch_params)

        for post_native_data in self.posts_data:
            post = self._create_db_post(
                post_native_data['_wrapped_data']['message'],
                channel=fbs1,
                facebook=post_native_data)
            # Although we passed channel=fbs1 to _create_db_post the eventually assigned channel
            # should be fbs2 since only that one has been tracking facebook page id from post data
            self.assertTrue(set(post.channels) & {fbs2.inbound, fbs2.outbound})
            self.assertEqual(post.service_channels, [fbs2])
