import unittest

from solariat_bottle.tests.base import BaseCase

from solariat_bottle.db.post.base import Post
from solariat_bottle.db.conversation import Conversation

from solariat_bottle.scripts import create_demo_data

@unittest.skip("Deprecated")
class DemoDataScriptCase(BaseCase):

    def test_script_demo_run_fresh_account(self):
        create_demo_data.DEMO_POST_COUNT = 2
        # Nothing is created before running script
        create_demo_data.load_demo_data('QA_CHAN', 'QA_ACC', keep_existing_data=False, full_load=False)
        # Number here should be constant across multiple runs, the entire thing should be deterministic
        self.assertEqual(Post.objects.count(), 2)
        print Conversation.objects.find_one().posts
        self.assertEqual(Conversation.objects.count(), 2)

    def test_script_demo_run_dirty_account(self):
        create_demo_data.DEMO_POST_COUNT = 2
        # We have some account with some data, now we re-ran the script
        create_demo_data.load_demo_data('QA_CHAN', 'QA_ACC', keep_existing_data=False, full_load=False)
        create_demo_data.load_demo_data('QA_CHAN', 'QA_ACC', keep_existing_data=False, full_load=False)

        self.assertEqual(Post.objects.count(), 2)
        print Conversation.objects.find_one().posts
        self.assertEqual(Conversation.objects.count(), 2)

    def test_demo_data_script(self):
        result = create_demo_data.load_demo_data(
            dummy_channel_name="Blue Sky Air Trans",
            dummy_account_name="BlueSkyAirTrans",
            keep_existing_data=False,
            week="last_week",
            full_load=False)
        self.assertTrue(result)

