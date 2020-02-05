import json
from hashlib import sha1

from solariat_bottle.tests.base import RestCase
from solariat_bottle.db.user_profiles.user_profile import UserProfile
from solariat_bottle.db.post.base      import Post
from solariat_bottle.tests.slow.test_conversations import ConversationBaseCase

class AdaptiveLearningCase(ConversationBaseCase, RestCase):

    def test_api_case(self):
        """
        Verify with a test case that when a reply post is submittted 
        to the system via API end point that no update is made to the classifier
        """
        self.inbound.adaptive_learning_enabled = True
        self.inbound.save()
        self.inbound.reload()
        original_clf_hash = sha1(self.inbound.channel_filter.clf.packed_model)
        token             = self.get_token()

        dummy_id = 'dummy_id'
        data = {
            'content': 'Test post',
            'lang'   : 'en',
            'channel': str(self.inbound.id),
            'token'  : token,
            'twitter': {'id': dummy_id}
        }
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(data),
                                content_type='application/json',
                                base_url='https://localhost')
        post_data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(post_data['ok'])

        post = Post.objects(channels=self.inbound.id)[0]
        reply_data = {
            'content': 'Reply post',
            'lang'   : 'en',
            'channel': str(self.outbound.id),
            'token'  : token,
            'user_profile': {'screenname': 'random_screenname'},
            'twitter': {'in_reply_to_status_id': dummy_id, 'id': 'reply_dummy_id'}
        } 
        resp = self.client.post('/api/v2.0/posts',
                                data=json.dumps(reply_data),
                                content_type='application/json',
                                base_url='https://localhost')
        post.reload()
        post_data = json.loads(resp.data)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(post_data['ok'])

        self.inbound.channel_filter.reload()
        latest_clf_hash = sha1(self.inbound.channel_filter.clf.packed_model)
        self.assertNotEqual(original_clf_hash.hexdigest(), latest_clf_hash.hexdigest())

    def test_observation_case(self):
        """
        If we just observe a twitter account (without engaging),
        no classifier model doesn't change
        """
        self.inbound.adaptive_learning_enabled = True
        original_clf_hash = sha1(self.inbound.channel_filter.clf.packed_model)
        self.inbound.save()
        self.inbound.reload()
        self._create_db_post(content="@test I need a laptop", channel=self.inbound)
        self.inbound.channel_filter.reload()
        latest_clf_hash = sha1(self.inbound.channel_filter.clf.packed_model)
        self.assertEqual(original_clf_hash.hexdigest(), latest_clf_hash.hexdigest())

    def test_adaptive_learning_disabled(self):
        """
        If adaptive_learning_enabled == True and reply is posted,
        then classifier model changes
        """
        original_clf_hash, latest_clf_hash = self.__setup_data(
            adaptive_learning_enabled=False, post_status='highlighted') # post_status='discarded' was here before
                                                                        # but I changed it because there are cases
                                                                        # where post can be highlighted even 
                                                                        # with adaptive_learning_enabled=False,
                                                                        # because post can meet rules
        self.assertEqual(original_clf_hash.hexdigest(), latest_clf_hash.hexdigest())

    def test_adaptive_learning_enabled(self):
        """
        If adaptive_learning_enabled == False and reply is posted,
        them classifier model doesn't change
        """
        original_clf_hash, latest_clf_hash = self.__setup_data(
            adaptive_learning_enabled=True, post_status='highlighted')
        self.assertNotEqual(original_clf_hash.hexdigest(), latest_clf_hash.hexdigest())

    def __setup_data(self, adaptive_learning_enabled, post_status):
        self.inbound.adaptive_learning_enabled = adaptive_learning_enabled
        original_clf_hash = sha1(self.inbound.channel_filter.clf.packed_model)
        self.inbound.save()
        self.inbound.reload()
        post = self._create_tweet(
            user_profile=UserProfile.objects.upsert('Twitter', dict(screen_name='customer')),
            channel=self.inbound,
            content="@test I need a laptop")
        self.assertEqual(post.channel_assignments[str(self.inbound.id)], post_status)

        self._create_tweet(
            user_profile=UserProfile.objects.upsert('Twitter', {'screenname': 'customer'}),
            channel=self.outbound,
            content="We have just the one for you.",
            in_reply_to=post)
        post.reload()
        self.assertEqual(post.channel_assignments[str(self.inbound.id)], 'replied')

        self.inbound.channel_filter.reload()
        latest_clf_hash = sha1(self.inbound.channel_filter.clf.packed_model)
        return original_clf_hash, latest_clf_hash



