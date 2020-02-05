import json

from solariat_bottle.db.channel.base import SmartTagChannel
from solariat_bottle.db.channel.twitter import TwitterServiceChannel
from solariat_bottle.db.post.base import Post
from solariat_bottle.tests.base import RestCase


class APIFeedbackCase(RestCase):
    def get_post_by_content(self, content):
        # since content is encrypted, scan all posts
        post = [p for p in Post.objects() if p.content == content][0]
        return post

    def test_tag_happy_flow_data(self):
        tschn1 = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        st = SmartTagChannel.objects.create_by_user(self.user,
                                                    parent_channel=tschn1.inbound_channel.id,
                                                    title='tag1',
                                                    status='Active')
        token = self.get_token()
        happy_flow_data = {
            'content': 'This is a test post! Testing feedback.',
            'token': token
        }
        previous_tag_score = 0
        happy_flow_data['channel_id'] = str(st.id)
        resp = self.client.post('/api/v2.0/add_tag',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['smart_tags'][0]['confidence']
        self.assertTrue(tag_score > previous_tag_score, "%s > %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        post = self.get_post_by_content('This is a test post! Testing feedback.')
        del happy_flow_data['content']
        happy_flow_data['post_id'] = post.id
        resp = self.client.post('/api/v2.0/add_tag',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['smart_tags'][0]['confidence']
        self.assertTrue(tag_score > previous_tag_score, "%s > %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        del happy_flow_data['post_id']
        happy_flow_data['content'] = 'This is a test post! Testing feedback.'
        resp = self.client.post('/api/v2.0/add_tag',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['smart_tags'][0]['confidence']
        self.assertTrue(tag_score > previous_tag_score, "%s > %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        resp = self.client.post('/api/v2.0/add_tag',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['smart_tags'][0]['confidence']
        self.assertTrue(tag_score > previous_tag_score, "%s > %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        resp = self.client.post('/api/v2.0/remove_tag',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['smart_tags'][0]['confidence']
        self.assertTrue(tag_score < previous_tag_score, "%s < %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        resp = self.client.post('/api/v2.0/remove_tag',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['smart_tags'][0]['confidence']
        self.assertTrue(tag_score < previous_tag_score, "%s < %s" % (tag_score, previous_tag_score))

    def test_channel_flow_data(self):
        tschn1 = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        tschn1 = tschn1.inbound_channel
        token = self.get_token()
        happy_flow_data = {
            'content': 'This is a test post! Testing feedback.',
            'token': token
        }
        previous_tag_score = 0
        happy_flow_data['channel_id'] = str(tschn1.id)
        resp = self.client.post('/api/v2.0/accept_post',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')

        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['actionability']
        self.assertTrue(tag_score > previous_tag_score, "%s > %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        post = self.get_post_by_content('This is a test post! Testing feedback.')
        del happy_flow_data['content']
        happy_flow_data['post_id'] = str(post.id)
        resp = self.client.post('/api/v2.0/accept_post',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['actionability']
        self.assertTrue(tag_score == previous_tag_score, "%s = %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        del happy_flow_data['post_id']
        happy_flow_data['content'] = 'This is a test post! Testing feedback.'
        resp = self.client.post('/api/v2.0/accept_post',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['actionability']
        self.assertTrue(tag_score > previous_tag_score, "%s > %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        resp = self.client.post('/api/v2.0/accept_post',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['actionability']
        self.assertTrue(tag_score > previous_tag_score, "%s > %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        resp = self.client.post('/api/v2.0/reject_post',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['actionability']
        self.assertTrue(tag_score < previous_tag_score, "%s < %s" % (tag_score, previous_tag_score))
        previous_tag_score = tag_score

        resp = self.client.post('/api/v2.0/reject_post',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        tag_score = post_data['item']['actionability']
        self.assertTrue(tag_score < previous_tag_score, "%s < %s" % (tag_score, previous_tag_score))

    def test_invalid_methods(self):
        tschn1 = TwitterServiceChannel.objects.create_by_user(self.user, title='TSC')
        st = SmartTagChannel.objects.create_by_user(self.user,
                                                    parent_channel=tschn1.inbound_channel.id,
                                                    title='tag1',
                                                    status='Active')
        token = self.get_token()
        happy_flow_data = {
            'content': 'This is a test post! Testing feedback.',
            'token': token
        }
        resp = self.client.get('/api/v2.0/reject_post',
                               data=json.dumps(happy_flow_data),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 405)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 135)
        resp = self.client.put('/api/v2.0/reject_post',
                               data=json.dumps(happy_flow_data),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 405)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 135)
        resp = self.client.delete('/api/v2.0/reject_post',
                                  data=json.dumps(happy_flow_data),
                                  content_type='application/json',
                                  base_url='https://localhost')
        self.assertEqual(resp.status_code, 405)
        resp_data = json.loads(resp.data)
        self.assertEqual(resp_data['code'], 135)
