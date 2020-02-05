# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from unittest import TestCase

from ..utils.stats import remove_zero_counts


class UtilsStatsTestCase(TestCase):
    def test_remove_zero_counts(self):
        """
        Test function that removes items that have count equal to zero from the list.
        """
        # all zero
        res= {u'ok': 1.0, u'result': [{u'count': 0, u'_id': {u'grp': 2}}, {u'count': 0, u'_id': {u'grp': 8}}]}
        res['result'] = remove_zero_counts(res['result'])
        self.assertEqual(len(res['result']), 0)

        # one zero
        res= {u'ok': 1.0, u'result': [{u'count': 1, u'_id': {u'grp': 2}}, {u'count': 0, u'_id': {u'grp': 8}}]}
        res['result'] = remove_zero_counts(res['result'])
        self.assertEqual(len(res['result']), 1)

        # none is zero
        res= {u'ok': 1.0, u'result': [{u'count': 1, u'_id': {u'grp': 2}}, {u'count': 2, u'_id': {u'grp': 8}}]}
        res['result'] = remove_zero_counts(res['result'])
        self.assertEqual(len(res['result']), 2)

    def test_do_not_remove_if_no_count(self):
        """
        `remove_zero_count` should not remove items if they do not have count.
        """
        # one item with count
        res= {u'ok': 1.0, u'result': [{u'_id': {u'grp': 2}}, {u'count': 0, u'_id': {u'grp': 8}}]}
        res['result'] = remove_zero_counts(res['result'])
        self.assertEqual(len(res['result']), 1)

        # no items with count
        res= {u'ok': 1.0, u'result': [{u'_id': {u'grp': 2}}, {u'_id': {u'grp': 8}}]}
        res['result'] = remove_zero_counts(res['result'])
        self.assertEqual(len(res['result']), 2)
