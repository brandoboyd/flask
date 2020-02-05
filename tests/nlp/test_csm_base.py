# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import unittest
from datetime                  import timedelta

from solariat.utils            import timeslot

from solariat_bottle.tests.base                     import fake_twitter_url
from solariat_bottle.tests.slow.test_conversations  import ConversationBaseCase
from solariat_bottle.db                      import conversation_state_machine as csm
from solariat_bottle.db.conversation         import Conversation
from solariat_bottle.db.user_profiles.user_profile import UserProfile


class PluginTester(csm.Policy):
    ''' Just for testing '''

    def should_be_terminated(self, current_state, time_stamp):
        return False


class CSMBase(ConversationBaseCase):
    '''
    Testing the functionality to estimate the final state of a conversation by incrementally
    estimating the impact to state with each post.
    '''

    def setUp(self):
        super(CSMBase, self).setUp()

        csm.POLICY_MAP['DEFAULT'] = csm.SimplePolicy()
        self.csm = csm.ConversationStateMachine(channel=self.sc)
        self.ts = timeslot.now()

        # Basic one and make sure it is persisted and retrieved
        sv = csm.StateVector(status=csm.INITIAL, time_stamp=self.ts)
        self.assertEqual(self.csm.state, sv)

        # Should be initially empty in state history. Do not store initial state as it is just
        # a place holder until a real initial state is assigned.
        self.assertEqual(len(self.csm.state_history), 0)

        self.csm.state = csm.StateVector.default(status=csm.WAITING)
        # self.csm.save()

        # Contact Setup
        self.contact_screen_name = '@contact'
        self.contact_user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=self.contact_screen_name))

        # Brand Setup
        self.brand_screen_name = '@brand'
        self.brand_user_profile = UserProfile.objects.upsert('Twitter', dict(screen_name=self.brand_screen_name))
        self.sc.add_username(self.brand_screen_name)

    def _apply_post(self, speaker, content):
        if speaker == csm.CONTACT:
            url = fake_twitter_url(self.contact_screen_name)
            return self._create_db_post(
                channel=self.sc.inbound,
                content=content,
                demand_matchables=False,
                url=url,
                user_profile=self.contact_user_profile)
        else:
            url = fake_twitter_url(self.brand_screen_name)
            return self._create_db_post(
                channel=self.sc.outbound,
                content="%s %s" % (self.contact_screen_name, content),
                url=url,
                user_profile=self.brand_user_profile)

    def _apply_dialog(self, listofposts):
        """
        accepts list of posts in the format (post_content, speaker)
        """
        for i in range(len(listofposts)):
            post = self._apply_post(listofposts[i][0], listofposts[i][1] )
            self.csm.handle_post(post)
            # Now apply the clock tick
        print "HANDLE TERMINATION"
        self.csm.handle_clock_tick(self.csm.state.time_stamp 
                                            + timedelta(days=1))
        self.assertTrue(self.csm.terminated)
        return self.csm.quality_star_score

    def _new_stm(self, channel_usernames):  #{
        stm = csm.ConversationStateMachine(channel=self.sc)
        for un in stm.channel.usernames:
            stm.channel.del_username(un)
        for un in channel_usernames:
            stm.channel.add_username(un)
        stm.state = csm.StateVector.default(status=csm.WAITING)
        # stm.save()

        return stm
    #}

    def _print_rules_stats(self):
        print "\n\n RULES STATS:"
        for k, v in csm.SimplePolicy.RULES_STATS:
            print "{:-<80s}: {:d}".format(k, v)


@unittest.skip('We are not using CSM anywhere and I do not want to support it all the time without clear goal. Alex G.')
class CSMTest(CSMBase):

    def test_post_vectorization(self):
        ''' Test function to determine who the speaker is.'''

        post = self._apply_post(csm.CONTACT, "I need a foo. Does anyone have a foo?")
        self.assertEqual(csm.make_post_vector(post, self.sc)['speaker'],
                         csm.CONTACT)
        self.assertFalse(csm.make_post_vector(post, self.sc)['actionable'])

        post = self._apply_post(csm.BRAND, "I can help you with that")
        self.assertEqual(csm.make_post_vector(post, self.sc)['speaker'],
                         csm.BRAND)
        self.assertFalse(csm.make_post_vector(post, self.sc)['actionable'])

        # Try direct case
        post = self._apply_post(csm.CONTACT, "%s I need a foo. Does anyone have a foo?" % self.brand_screen_name)
        self.assertEqual(len(Conversation.objects()), 1)
        conv = Conversation.objects()[0]

        # Now try direct
        self.assertTrue(csm.make_post_vector(post, self.sc)['actionable'])

    def test_state_vector_handling(self):
        ''' Simple state vector handling '''

        # Set another and verify different. This will add another state, making
        # It the most recent, and then it will persist the state machine by default
        stm  = self._new_stm(["@brand"])
        post = self._apply_post(csm.CONTACT, "I hate haters")
        stm.handle_post(post)
        self.assertEqual(stm.state.status, csm.WAITING)
        self.assertEqual(len(self.csm.state_history), 1)

        # Invalid state vector. Should not be allowed to assign
        sv = csm.StateVector.default()
        sv.brand_post_count_last   = 1
        sv.contact_post_count_last = 1
        try:
            self.csm.state = sv
            self.assertFalse(True, "Should never get here.")
        except:
            pass

    def test_termination(self):
        ''' Test of default (and simple) termination handling '''
        stm  = self._new_stm(["@brand"])
        self.assertEqual(len(stm.state_history), 1)
        
        post = self._apply_post(csm.CONTACT, "I hate haters")
        stm.handle_post(post)
        self.assertFalse(stm.terminated)
        self.assertEqual(len(stm.state_history), 2)
        current_time = stm.state.time_stamp
        
        # A short elapsed time will not terminate.
        stm.handle_clock_tick(current_time + timedelta(hours=2))
        self.assertFalse(stm.terminated)

        # A longer one will terminate. If it does transition, we
        # will update the score.
        stm.handle_clock_tick(current_time + timedelta(days=2))
        self.assertTrue(stm.terminated)
        self.assertEqual(len(stm.state_history), 3)

    def test_policy_plugin(self):
        ''' Just a trivial test to ensure we can over-ride '''
        csm.POLICY_MAP['DEFAULT'] = PluginTester()
        self.csm.handle_clock_tick(self.csm.state.time_stamp + timedelta(days=1))
        self.assertFalse(self.csm.terminated)

    def test_state_counts(self):
        ''' Make sure brand and post counts and time stamps updated corrrectly.'''
        pass

    def test_status_transitions(self):
        ''' Verify the proper status transitions '''
        pass

    def test_handle_post_after_reject(self):
        '''
        Rejected should not be a terminated state maybe.
        Or at least we should allow exiting from it.
        '''
        pass

    def test_final_scoring(self):
        '''
        Verify the logic for final score assignment on termination
        '''
        pass



@unittest.skip('We are not using CSM anywhere and I do not want to support it all the time without clear goal. Alex G.')
class PolicyVerify(CSMBase):
    """
    The input is a list of posts, with time stamps etc
    The output to verify in each cases is final satisfaction, and score
    This class implements proper handling for some of the obvious policy cases
    """

    def test_policy_final_state(self):
        """
        Test final policy state of a post
        """
        policy_vec  = csm.SimplePolicy()
        current_state = csm.StateVector( status = csm.ENGAGED, time_stamp = timeslot.now())

        final_state = policy_vec.get_final_state( current_state, timeslot.now())
        self.assertEqual(current_state, final_state)

    def test_update_state_with_post(self):
        post = self._apply_post(csm.CONTACT,  "I need a foo. Does anyone have a foo?")
        policy_vec  = csm.SimplePolicy()
        current_state = csm.StateVector( status = csm.ENGAGED, time_stamp = timeslot.now())
        post_vector = csm.make_post_vector(post, self.sc)
        new_state = policy_vec.update_state_with_post(current_state, post_vector)
        self.assertNotEqual(current_state, new_state)

    def test_satisfaction_update(self):
        post = self._apply_post(csm.CONTACT,  "This is ridiculous.. I am furious now")
        policy_vec  = csm.SimplePolicy()
        current_state = csm.StateVector( status = csm.ENGAGED, time_stamp = timeslot.now())
        post_vector = csm.make_post_vector(post, self.sc)
        new_state = policy_vec.update_state_with_post(current_state, post_vector)

    def test_post_list(self):
        postlist = [(csm.CONTACT, "@brand I need some information.. You are not being very helpful.."),
                    (csm.BRAND, "Thank you sir for getting in touch with us.")]
        score = self._apply_dialog(postlist)
        # Here we can check increment or decrement of score
        self.assertTrue(score > 1)
        self.assertEqual(self.csm.state.status, csm.COMPLETED)
       
    def test_post_noreply(self):
        postlist = [(csm.CONTACT, "@brand This is super frustrating.. I have beein tryin to make it work but it doesnt.."),        
                    (csm.CONTACT, "@brand This is ridiculous.. I hae followed all the instructions in the manual.. #pissed"),
                    (csm.CONTACT, "I have no idea why they cannot take care of issue")]
        score = self._apply_dialog(postlist)
        self.assertTrue(abs(score - 1) < 1) # It should be lame! 

    # def test_post_brandterminate(self):

    #     postlist = [(csm.CONTACT, "@brand This is super frustrating.. I have beein tryin to make it work but it doesnt.."),        
    #                 (csm.BRAND, "Sir, Can you please try rebooting the system?"),
    #                 (csm.CONTACT, "@brand That was it.. Now it is working.. Thanks a lot for your help. I love it..!")]
                    
    #     score = self._apply_dialog(postlist)
    #     self.assertEqual(score, 0.0) # This should be one.. 
    #     self.assertEqual(self.csm.state.status, csm.COMPLETED)

def _get_report(df):
    df["error"]     = df["predicted_score"]-df["true_score"]
    df["abs_error"] = df["error"].apply(abs)
    report = '\n\n' + classification_report(df["true_score"], df["predicted_score"])
    report += '\n'
    report += '\n MEAN ERROR: %s' % df["abs_error"].mean()
    report += '\n MAX  ERROR: %s' % df["abs_error"].max()
    report += '\n MIN  ERROR: %s' % df["abs_error"].min()
    return report



