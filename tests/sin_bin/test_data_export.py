from solariat_bottle.app import MAIL_SENDER as mail

from solariat_bottle.tests.base import BaseCase, UICase
from solariat_bottle.db.data_export import DataExport, DataExportMailer, hash_dict
from solariat_bottle.views.facets import ExportPostsView
from solariat.utils.timeslot import now, timedelta


REQUEST_SAMPLE = {
    "agents": [],
    "channel_id": "54771137e252a51c3dd55d7d",
    "intentions": ["apology", "asks", "checkins", "gratitude", "junk", "likes",
                   "needs", "offer", "problem", "recommendation"],
    "sentiments": None, "topics": [], "statuses": None,
    "plot_type": "response-time",
    "sort_by": "time",
    "thresholds": {"intention": 0},
    "from": "2014-12-11 00:00:00",
    "to": "2014-12-12 23:59:59",
    "level": "day",
    "languages": ["English"],
    "offset": 0, "limit": 15, "last_query_time": None}


class ExportCollectionCase(BaseCase):
    def test_create_and_find(self):
        input_filters = {'channel_id': 'CHANNEL_ID',
                         'from': '2014-01-01',
                         'to': '2014-01-02',
                         'level': 'hour'}
        item = DataExport.objects.create_by_user(
            self.user, input_filter=input_filters)
        self.assertEqual(item.created_by, self.user)
        self.assertEqual(set(item.recipients), set([self.user]))
        self.assertEqual(item.account, self.user.current_account)

        self.assertEqual(item.state, DataExport.State.CREATED)
        self.assertEqual(item.input_filter_hash, hash_dict(item.input_filter))

        by_filter = DataExport.objects.find_one_by_user(
            self.user, input_filter=item.input_filter)
        self.assertEqual(by_filter.id, item.id)
        self.assertIsNone(DataExport.objects.find_one_by_user(
            self.user, input_filter={}))

    def test_change_state(self):
        item = DataExport.objects.create_by_user(self.user)
        with self.assertRaises(AssertionError):
            item.change_state(DataExport.State.FETCHING)
            item.change_state(DataExport.State.SENDING)

        item.reload()
        self.assertEqual(item.state, DataExport.State.FETCHING)
        item.change_state(DataExport.State.GENERATING)

        self.assertEqual(len(item.states_log), 2)
        item.reload()

        self.assertEqual(item.states_log[0]['from'], DataExport.State.CREATED)
        self.assertEqual(item.states_log[0]['to'], DataExport.State.FETCHING)

        self.assertEqual(item.states_log[1]['from'], DataExport.State.FETCHING)
        self.assertEqual(item.states_log[1]['to'], DataExport.State.GENERATING)

    def test_process_task(self):
        view = ExportPostsView()
        view.user = self.user

        with mail.app.test_request_context(), mail.record_messages() as outbox:
            item = DataExport.objects.create_by_user(
                self.user, input_filter=REQUEST_SAMPLE, state=DataExport.State.FETCHED)

            request_params = REQUEST_SAMPLE.copy()
            request_params['channel_id'] = str(self.channel.id)
            request_params = view.validate_params(request_params)
            view.postprocess_params(request_params)
            item.process(self.user, request_params)

            self.assertEqual(len(outbox), 1)
            msg = outbox[0]
            self.assertEqual(msg.subject, DataExportMailer.EMAIL_SUBJECT)
            self.assertEqual(len(msg.attachments), 1)
            msg_body_marker = "Attached is the file you requested to have exported from Genesys Social Analytics"
            self.assertTrue(msg.body.startswith(msg_body_marker))
            self.assertIn(msg_body_marker, msg.html)


class ExportUIHandler(UICase):

    def setUp(self):
        super(ExportUIHandler, self).setUp()
        self.url = ExportPostsView.url_rule
        self.login()
        self.setup_posts()

    def setup_posts(self):
        self.created_at = now()
        self.created_at_str = self.created_at.strftime('%Y-%m-%d %H:%M:%S')

        base_tweet = self._create_tweet('parent tweet', _created=self.created_at - timedelta(milliseconds=1))
        n = 0
        for content in (
            'I need a bike. I like Honda.',
            'Can somebody recommend a sturdy laptop?',
            'I need an affordabl laptop. And a laptop bag',
            'Whatever you buy, let it be an Apple laptop',
            'I would like to have a thin and lightweight laptop.'
        ):
            self._create_tweet(content=content,
                               _created=self.created_at + timedelta(milliseconds=n),
                               in_reply_to=base_tweet)
            n += 1

    def do_export_request(self, parameters):
        resp = self._post(self.url, parameters)
        return resp

    def test_export_analytics(self):
        with mail.record_messages() as outbox:
            resp = self.do_export_request({
                'channel_id' : str(self.channel.id),
                'from'       : self.created_at_str,
                'to'         : (self.created_at + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'topics'     : [{'topic': 'laptop', 'topic_type': 'node'}],
                'intentions' : [],
                'thresholds' : dict(intention=.1),
                'statuses'   : ['actionable']
            })
            self.assertEqual(resp['message'], ExportPostsView.SUCCESS_MSG_TPL % self.user.email)
            self.assertTrue({'id', 'input_filter_hash', 'state', 'created_at'} < set(resp['task']), resp)
            msg = outbox[0]
            at = msg.attachments[0]
            self.assertTrue(at)
        self.assertEqual(DataExport.objects.count(), 1)
        export_item = DataExport.objects.get()
        self.assertEqual(export_item.state, DataExport.State.SUCCESS)