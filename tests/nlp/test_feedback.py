# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import json

from solariat_bottle.db.post.base import PostUserFeedback
from solariat_bottle.db.roles import AGENT

from solariat_bottle.tests.base     import UICase, BaseCase


class FeedbackTest(BaseCase):
    def setUp(self):
        BaseCase.setUp(self)
        content = 'I need a bike . I like Honda .'
        self._create_db_post(
            channel=self.channel,
            content="I need a new laptop")
        self.post = self._create_db_post(
            channel=self.channel,
            content=content)
        self._create_db_post(
            channel=self.channel,
            content="Can somebody recommend a good pair of jeans?")
        #from solariat_bottle.db.speech_act import make_id
        self.speech_act_id = 'EECACDEECACDEECACDEECACD'  #make_id(self.post.id, 0, 0)

    def test_vote_for_intention(self):
        speech_act_id = self.speech_act_id

        value = self.post.get_vote_for(self.user, speech_act_id, intention='needs')
        self.assertEqual(value, 0)

        self.post.set_vote_for(self.user, 1, speech_act_id, intention='needs')
        self.post.save()
        self.post.reload()

        value = self.post.get_vote_for(self.user, speech_act_id, intention='needs')
        self.assertEqual(value, 1)

        self.post.set_vote_for(self.user, -1, speech_act_id, intention='needs')
        self.post.save()
        self.post.reload()

        value = self.post.get_vote_for(self.user, speech_act_id, intention='needs')
        self.assertEqual(value, -1)

        uf = PostUserFeedback.objects.find(
            user=self.user.id,
            post=self.post.id,
            speech_act_id=speech_act_id,
            vote_kind=PostUserFeedback.INTENTION,
            content='needs').sort(**{'last_modified': -1})[0]
        self.assertEqual(uf.vote, -1)


    def test_vote_for_topic(self):
        speech_act_id = self.speech_act_id

        value = self.post.get_vote_for(self.user, speech_act_id, topic='bike')
        self.assertEqual(value, 0)

        self.post.set_vote_for(self.user, 1, speech_act_id, topic='bike')
        self.post.save()
        self.post.reload()

        value = self.post.get_vote_for(self.user, speech_act_id, topic='bike')
        self.assertEqual(value, 1)
        uf = PostUserFeedback.objects.get(
            user=self.user.id,
            post=self.post.id,
            speech_act_id=speech_act_id,
            vote_kind=PostUserFeedback.TOPIC,
            content='bike')
        self.assertEqual(uf.vote, 1)

        self.post.set_vote_for(self.user, -1, speech_act_id, topic='honda')
        self.post.save()
        self.post.reload()
        uf = PostUserFeedback.objects.get(
            user=self.user.id,
            post=self.post.id,
            speech_act_id=speech_act_id,
            vote_kind=PostUserFeedback.TOPIC,
            content='honda')
        self.assertEqual(uf.vote, -1)

        value = self.post.get_vote_for(self.user, speech_act_id, topic='honda')
        self.assertEqual(value, -1)

        #test unicode topic
        self.post.set_vote_for(self.user, 1, speech_act_id, topic=u'honda')
        self.post.save()
        self.post.reload()

        value = self.post.get_vote_for(self.user, speech_act_id, topic=u'honda')
        self.assertEqual(value, 1)

        value = self.post.get_vote_for(self.user, speech_act_id, topic='honda')
        self.assertEqual(value, 1)

        self.assertEqual(self.post.get_vote_for(self.user, speech_act_id, topic=u"hönda"), 0)

    def assertDictsEqual(self, expected_dict, d):
        for k, v in expected_dict.iteritems():
            self.assertTrue(k in d)
            if isinstance(v, dict):
                self.assertDictsEqual(expected_dict[k], d[k])
            else:
                self.assertEqual(expected_dict[k], d[k])

    def test_user_feedback_dict_structure(self):
        def replace_dots(s):
            return s.replace('.', '')

        speech_act_id = self.speech_act_id
        user2 = self._create_db_user('user2test@solariat.com', roles=[AGENT])
        self.post.set_vote_for(self.user, -1, speech_act_id, topic='honda')
        self.post.set_vote_for(user2, 1, speech_act_id, topic='honda')
        self.post.set_vote_for(user2, 1, speech_act_id, topic='bike')
        self.post.set_vote_for(self.user, -1, speech_act_id, intention='needs')
        self.post.save()
        self.post.reload()

        expected_dict = {
            "%s" % self.user.id : {
                'intention' : {replace_dots(self.speech_act_id+'::needs'): -1},
                'topic'     : {replace_dots(self.speech_act_id+'::honda'): -1}
            },
            "%s" % user2.id    : {
                'topic' : {
                    replace_dots(self.speech_act_id+'::honda') : 1,
                    replace_dots(self.speech_act_id+'::bike')  : 1
                }
            }
        }

        self.assertDictsEqual(expected_dict, self.post.user_feedback)


class FeedbackEndpointTest(UICase):
    def setUp(self):
        UICase.setUp(self)
        self.login()

        self._create_db_post(
            channel=self.channel,
            content="I need a new laptop"
        )
        self._create_db_post(
            channel=self.channel,
            content="Can somebody recommend a good pair of jeans?"
        )
        self.post = self._create_db_post(
            channel=self.channel,
            content='I need a bike . I like Honda .'
        )
        self.speech_act_id = 0

    def test_feedback_post(self):
        #Test vote for topic
        data = json.dumps(
            dict(
                post_id       = self.post.id,
                topic         = 'bike',
                vote          = 1,
                speech_act_id = self.speech_act_id)
            )
        resp = self.client.post('/feedback/json',
            data         = data,
            content_type = 'application/json'
        )
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)

        self.assertTrue(resp['ok'], resp.get('error'))
        self.post.reload()
        self.assertEquals(self.post.get_vote_for(self.user, self.speech_act_id, topic='bike'), 1)

        #Test already voted
        data = json.dumps(dict(
            post_id       = str(self.post.id),
            topic         = 'bike',
            vote          = 1,
            speech_act_id = self.speech_act_id
        ))
        resp = self.client.post(
            '/feedback/json',
            data         = data,
            content_type = 'application/json'
        )
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])
        self.assertEqual(resp.get('error'), "You have already voted.")

        #Test vote for undefined topic
        data = json.dumps(dict(
            post_id       = str(self.post.id),
            speech_act_id = self.speech_act_id,
            topic         = 'UndefinedTopic111',
            vote          = 1
        ))
        resp = self.client.post(
            '/feedback/json',
            data         = data,
            content_type = 'application/json'
        )
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])
        self.assertEquals(resp.get('error'), "Topic not found.")

        #Test vote for intention
        data = json.dumps(dict(
            post_id       = str(self.post.id),
            intention     = 'needs',
            speech_act_id = self.speech_act_id,
            vote          = -1
        ))
        resp = self.client.post(
            '/feedback/json',
            data         = data,
            content_type = 'application/json'
        )
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertTrue(resp['ok'], resp.get('error'))
        self.post.reload()
        self.assertEquals(self.post.get_vote_for(self.user, self.speech_act_id, intention='needs'), -1)

        #Test vote for undefined intention
        data = json.dumps(dict(
            post_id       = str(self.post.id),
            intention     = 'WrongIntention123',
            speech_act_id = self.speech_act_id,
            vote          = -1
        ))
        resp = self.client.post(
            '/feedback/json',
            data         = data,
            content_type = 'application/json'
        )
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])
        self.assertEqual(resp.get('error'), 'Intention not found.')

        #Test no speech_act_id
        data = json.dumps(dict(
            post_id       = str(self.post.id),
            intention     = 'needs',
            speech_act_id = "",
            vote          = -1
        ))
        resp = self.client.post(
            '/feedback/json',
            data         = data,
            content_type = 'application/json'
        )
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])
        self.assertEqual(resp.get('error'), 'Speech act idx is missing')

        #Test erroneous vote value
        err_vote = "123"
        data = json.dumps(dict(
            post_id       = str(self.post.id),
            intention     = 'needs',
            speech_act_id = self.speech_act_id,
            vote          = err_vote
        ))
        resp = self.client.post(
            '/feedback/json',
            data         = data,
            content_type = 'application/json'
        )
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.data)
        self.assertFalse(resp['ok'])
        self.assertEqual(resp.get('error'), 'Vote must be -1 or 1, got %s' % err_vote)

