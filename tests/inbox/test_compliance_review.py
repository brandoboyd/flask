"""
Tests for outbound responses review workflow.
"""
import unittest
import json

from solariat_bottle.tests.base import fake_status_id, UICase

from solariat_bottle.db.channel.twitter import EnterpriseTwitterChannel as ETC
from solariat_bottle.db.channel.twitter import KeywordTrackingChannel as KTC
from solariat_bottle.db.roles import AGENT

@unittest.skip("Responses and Inbox are deprecated now")
class EngageUITest(UICase):
    def setUp(self):
        UICase.setUp(self)
        self.login()
        #self.user.is_superuser = False
        #self.user.save()

        self.outbound = ETC.objects.create_by_user(
            self.user, title='Compliance Review Outbound',
            access_token_key='dummy_key',
            access_token_secret='dummy_secret')

        self.account.outbound_channels = {'Twitter':str(self.outbound.id)}
        self.account.save()

        self.channel = KTC.objects.create_by_user(
            self.user, title='Inbound Channel',
            keywords=['foo'])

        self.matchable = self._create_db_matchable('there is some foo')

        # Create another user and grant them access
        self.team_user = self._create_db_user(account=self.account,
                                              email='team_member@solariat.com',
                                              password='12345', roles=[AGENT])

        post = self._create_db_post(
            'I need some foo', 
            demand_matchables=True,
            twitter= {'id': fake_status_id()})

        self.response = Response.objects.upsert_from_post(post)

        self.assertEqual(self.response.channel, self.channel)

        self.outbound.review_outbound = True
        self.outbound.save()
        review_team = self.outbound.get_review_team()
        review_team.add_user(self.team_user)
        self.outbound.add_perm(self.team_user)

    def _reset_review_team(self, members):
        review_team = self.outbound.get_review_team()
        review_team.members = members
        review_team.save()

    def test_auto_review(self):
        '''
        For the case where the user is a reviewer
        '''
        self._reset_review_team([self.user])
        creative = "U could find some foo there"
        data = dict(creative=creative, response=str(self.response.id),
                    latest_post=str(self.response.post.id))
        resp = self.client.post('/commands/custom_response',
            data=json.dumps(data))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.assertFalse('item' in resp, resp)

    def test_custom_response(self):
        creative = "U could find some foo there"
        data = dict(creative=creative, response=str(self.response.id),
                    latest_post=str(self.response.post.id))
        resp = self.client.post('/commands/custom_response',
            data=json.dumps(data))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.assertEqual(resp['item']['status'], 'review-post', resp['item']['status'])
        self.response.reload()
        # Verify the matchable has switched correctly
        self.assertEqual(self.response.matchable.creative, creative)

        # And of course - the right status
        self.assertEqual(self.response.status, 'review-post')

        #post with review team member
        self.login(self.team_user.email)
        resp = self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(self.response.id), str(self.response.matchable.id), str(self.response.post.id)))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])

        post_match = PostMatch.objects.find_one(post=self.response.post)
        self.assertTrue(post_match)
        self.assertEqual(post_match.impressions[0].id,
            self.response.matchable.id)
        self.assertEqual(post_match.status, 'approved')

    def test_retweet(self):
        resp = self.client.post('/commands/retweet_response',
            data='{"response":"%s"}' % str(
                self.response.id))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.assertEqual(resp['item']['status'], 'review-retweet')
        self.response.reload()
        self.assertEqual(self.response.status, 'review-retweet')

        #post with review team user
        self.login(self.team_user.email)

        #do not allow to reply
        resp = self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(self.response.id), str(self.response.matchable.id), str(self.response.post.id)))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.assertFalse('item' in resp)
        self.response.reload()
        self.assertEqual(self.response.status, 'review-retweet')

        #test can not skip
        resp = self.client.post('/commands/skip_response',
            data='{"responses": ["%s"]}' % str(
                self.response.id))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.response.reload()
        self.assertEqual(self.response.status, 'review-retweet')

        resp = self.client.post('/commands/retweet_response',
            data='{"response":"%s"}' % str(
                self.response.id))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.response.reload()
        self.assertEqual(self.response.status, 'retweeted')

    def test_post(self):
        resp = self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(self.response.id), str(self.response.matchable.id), str(self.response.post.id)))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.assertEqual(resp['item']['status'], 'review-post')
        self.response.reload()

        self.assertEqual(self.response.status, 'review-post')

        #post with review team member
        self.login(self.team_user.email)

        #test retweet is not allowed
        resp = self.client.post('/commands/retweet_response',
            data='{"response":"%s"}' % str(
                self.response.id))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.assertFalse('item' in resp)
        self.response.reload()
        self.assertEqual(self.response.status, 'review-post')

        #test can not skip
        resp = self.client.post('/commands/skip_response',
            data='{"responses": ["%s"]}' % str(
                self.response.id))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.response.reload()
        self.assertEqual(self.response.status, 'review-post')

        resp = self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(self.response.id), str(self.response.matchable.id), str(self.response.post.id)))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.response.reload()
        self.assertEqual(self.response.status, 'posted')

        post_match = PostMatch.objects.find_one(post=self.response.post)
        self.assertTrue(post_match)
        self.assertEqual(post_match.impressions[0].id, self.response.matchable.id)
        self.assertEqual(post_match.status, 'approved')

        # Make sure the user_profile is updated
        #outbound = self.user.get_outbound_channel(self.response.post.channel.platform)
        self.assertTrue(self.response.user_profile.has_history(self.outbound))
        self.assertEqual(self.response.channel, self.outbound)
        self.assertTrue(self.response.user_profile.has_history(self.outbound),
                        self.response.user_profile.engaged_channels)

    def _fetch_responses(self, channel):
        filters = {'channel_id': str(channel.id),
                       'intentions': ['asks','consideration','needs','likes','problem'],
                       'visibility': {"starred":False,
                                      "rejected":False,
                                      "pending":True,
                                      "forwarded":False,
                                      "posted":True,
                                      "retweeted":True,
                                      "filtered":False,
                                      "skipped":False,
                                      "review":True}}




        resp = self.client.post('/responses/json',
            data=json.dumps(filters),
            content_type='application/json')

        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['ok'])
        self.assertTrue('list' in data)
        return data['list']

    def test_response_visibility(self):
        """
        self.user - who posted
        self.team_user - allowed for review
        """
        self.outbound.review_team.del_user(self.user, 'rw')

        #user posts response
        resp = self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(self.response.id), str(self.response.matchable.id), str(self.response.post.id)))
        self.assertEqual(resp.status_code, 200)

        #check the response channel changed to outbound
        self.response.reload()
        self.assertEqual(self.response.channel, self.outbound)
        #check user can not see response under the outboud channel,
        #since he is not in review team
        self.assertFalse(self.response.can_view(self.user))  #test acl
        resp = self._fetch_responses(self.outbound)  #test ui call
        self.assertEqual(len(resp), 0)
        #response should be neither in inbound channel
        resp = self._fetch_responses(self.channel)
        self.assertEqual(len(resp), 0)

        #login with team user for review
        self.login(self.team_user.email)
        #check team_user can see the response in outbound channel
        resp = self._fetch_responses(self.outbound)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0]['id'], str(self.response.id))

        #post the response by reviewer
        resp = self.client.post('/commands/post_response',
            data='{"response":"%s","matchable":"%s","latest_post":"%s"}' % (
                str(self.response.id), str(self.response.matchable.id), str(self.response.post.id)))
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'])
        self.response.reload()
        self.assertEqual(self.response.status, 'posted')

        #verify reviewer still sees the response
        return

        # TODO: FIX THIS> See inbox query
        resp = self._fetch_responses(self.outbound)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0]['id'], str(self.response.id))

        #login back with initial sender
        self.login(self.user.email)

        #now we should see the response again in outbound channel
        resp = self._fetch_responses(self.outbound)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0]['id'], str(self.response.id))

        self.response.reload()
        self.assertTrue(self.response.can_view(self.user))
