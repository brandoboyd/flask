# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import json
import os
import unittest
from os.path         import dirname, join
from datetime        import timedelta
from collections     import OrderedDict

from solariat_bottle.tests.nlp.test_csm_base import CSMBase
from solariat_bottle.db import conversation_state_machine as csm

from solariat_bottle.tests.base import fake_twitter_url
from solariat.utils.signed_pickle import signed_pickle


@unittest.skip("We don't use CSM; skipping this test for now; agogolev;")
class ConversationSTMPolicyCase(CSMBase):
    '''
    Tests a Conversation STM Policy on a set of reference conversation examples
    '''

    filenames = [
        "ref_conversations.pkl",
        "steve_conversations.json",
    ]

    def setUp(self):
        super(ConversationSTMPolicyCase, self).setUp()
        csm.POLICY_MAP['DEFAULT'] = csm.SimplePolicy()
        fake_twitter_url(self.contact_screen_name)
        fake_twitter_url(self.brand_screen_name)

    def test_reference_examples(self):
        """ Feeds posts of reference conversations comparing results to a baseline.

            First, it loads up post data of the human labelled reference convesation set
            (solariat_bottle/data/ref_conversations.pkl)

            Next, it goes through the conversations one-by-one and feeds their posts
            to a Conversation STM (each time a fresh state machine instance) comparing
            resulting labels to the reference ones.

            Then it saves the results (solariat_bottle/tests/conversation-stm.out.pkl)
            so that a developer can promote the file to be a new base-line (by renaming
            the file to conversation-stm-baseline.out.pkl, committing and pushing to the
            repo).

            And finally, it compares results to the base-line results
            (conversation-stm-baseline.out.pkl) and outputs differences and statistics
            as a nice human-readable table.
        """
        #{ --- prepare data ---
        csm.SimplePolicy.reset_rules_stats()
        conversations = []
        for filename in self.filenames:
            conv_path = os.path.realpath(join(dirname(__file__), '../..', 'data', filename))
            with open(conv_path, 'rb') as f:
                convs = json.loads(f.read()) if filename.endswith(".json") else signed_pickle.load(f)
            conversations += convs

        #{ --- feed posts to STMs ---
        passed, failed = OrderedDict(), OrderedDict()

        print '\n{typ:#^80}'.format(typ=' ConversationStateMachine Policy (FAILED) ')

        post_count = 0
        cumulative_error = 0.0
        conversation_count = 0
        for conv, labels, posts, channel_usernames in conversations:
            conversation_count += 1
            stm = self._new_stm(channel_usernames=channel_usernames)

            for post in posts:
                speaker = csm.BRAND if post['route'] == 'outbound' else csm.CONTACT
                post = self._apply_post(speaker, post['t'])
                stm.handle_post(post)
  
            # Now apply the clock tick
            print "TERMINATION: "
            stm.handle_clock_tick(stm.state.time_stamp+timedelta(days=1))

            result = dict(
                conv=conv,
                # labels=labels,
                posts=posts,
                expected=int(labels['label']),
                actual=stm.quality_star_score
            )
            stm.delete()  # cleanup

            if result['expected'] == result['actual']:
                passed[conv['id']] = result
                res_str = "PASS"
            else:
                failed[conv['id']] = result
                res_str = "FAIL"
                cumulative_error += abs(result['expected'] - result['actual'])

            print '\n{all:02d} ({num:02d}): CONVERSATION {conv[id]}:'.format(all=post_count,
                                                                             num=len(failed), 
                                                                             conv=conv)
            # for post in result['posts']:
            #     text = post['t'].replace('&amp;', '&').replace('\n',' ').encode('UTF-8', 'replace')
            #     print '     - {0}'.format(text)
            print '    expected: {expected}, got: {actual}  (%s)'.format(**result) % res_str
            print '-'*70+'\n'
            post_count += 1

        #}
        #{ --- save results ---
        out_path = join(dirname(__file__), 'conversation-stm.out.pkl')

        with file(out_path, 'wb') as out:
            signed_pickle.dump(dict(passed=passed, failed=failed), out)

        #}
        #{ --- compare results to baseline ---
        base_path = os.path.realpath(join(dirname(__file__), 'conversation-stm-baseline.out.pkl'))
        base_results = {}

        with file(base_path, 'rb') as base:
            base_results = signed_pickle.load(base)

        base_passed = base_results.get('passed', {})  # {<conv_id>: <result_dict>}
        base_failed = base_results.get('failed', {})  # {<conv_id>: <result_dict>}

        became_passed = []
        became_failed = []

        for key, this_res in passed.iteritems():
            if key in base_failed:
                this_res['base'] = base_failed[key]['actual']
                became_passed.append(this_res)

        for key, this_res in failed.iteritems():
            if key in base_passed:
                this_res['base'] = base_passed[key]['actual']
                became_failed.append(this_res)
        #}
        #{ -- print changes --
        if became_passed:
            print '\n{typ:^^80}'.format(typ=' ConversationStateMachine Policy (now PASSED) ')
            for num, res in enumerate(became_passed, 1):
                print '\n{num:02d}. CONVERSATION {conv[id]}:'.format(num=num, conv=res['conv'])
                for post in res['posts']:
                    text = post['t'].replace('&amp;', '&').replace('\n', ' ').encode(
                        'UTF-8', 'replace')
                    print '     - {0}'.format(text)
                print '    output: {base} -> {actual}  (PASS)'.format(**res)

        if became_failed:
            print '\n{typ:.^80}'.format(typ=' ConversationStateMachine Policy (now FAILED) ')
            for num, res in enumerate(became_failed, 1):
                print '\n{num:02d}. CONVERSATION {conv[id]}:'.format(num=num, conv=res['conv'])
                for post in res['posts']:
                    text = post['t'].replace('&amp;', '&').replace('\n', ' ').encode(
                        'UTF-8', 'replace')
                    print '     - {0}'.format(text)
                print '    output: {base} -> {actual}  (FAIL)'.format(**res)
        #}
        #}

        #{ --- print stats ---
        
        line = (
            '{:-^13s}-+-{:-^6s}-+-{:-^5s}-+-{:-^6s}-+-{:-^5s}-+-{:-^6s}-+-{:-^5s}-+-{:-^6s}-+-{:-^5s}'  # noqa
        ).format('', '', '', '', '', '', '', '', '')
        print

        # -- header --
        print '{0:-^{1}}'.format('', len(line))
        print '{title: ^{line_len}}'.format(
            title=' ConversationStateMachine Policy ',
            line_len=len(line)
        )
        print line
        print (
            '{:13s} | {:^6s} | {:^5s} | {:^6s} | {:^5s} | {:^6s} | {:^5s} | {:^6s} | {:^5s}'
        ).format(
            '', 'PASSED', '%', 'FAILED', '%', 'F->P', '%', 'P->F', '%'
        )
        print line

        # -- body --
        passed_num = len(passed)
        failed_num = len(failed)
        became_passed_num = len(became_passed)
        became_failed_num = len(became_failed)
        total_num = passed_num + failed_num

        print (
            '{title: >13s} | '
            '{passed_num: >6d} | {passed_per: >5.1f} | '
            '{failed_num: >6d} | {failed_per: >5.1f} | '
            '{became_passed_num: >6d} | {became_passed_per: >5.1f} | '
            '{became_failed_num: >6d} | {became_failed_per: >5.1f}'
        ).format(
            title='CONVERSATIONS',
            passed_num=passed_num,
            failed_num=failed_num,
            became_passed_num=became_passed_num,
            became_failed_num=became_failed_num,
            passed_per=passed_num * 100. / total_num,
            failed_per=failed_num * 100. / total_num,
            became_passed_per=became_passed_num * 100. / total_num,
            became_failed_per=became_failed_num * 100. / total_num,
        )

        print line

        net_gain = len(became_passed) - len(became_failed)
        self._print_rules_stats()

        print '\nnet_gain  = %d' % net_gain
        print '\navg_error = %0.2f' % (cumulative_error * 1.0 / conversation_count)
        #}

        #self.assertTrue(net_gain >= 0, 'this model performs worse (net_gain=%u)' % net_gain)

