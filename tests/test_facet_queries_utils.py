# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from unittest import TestCase

from ..plots.utils import aggregate_results_by_label, merge_two_time_results


class MergeTwoTimeResultsCase(TestCase):
    """ Tests utility function facet_queries.merge_two_time_results() """

    def test_works(self):
        a = dict(label='same', count=1, data=[(11111, 1), (11112, 0)])
        b = dict(label='same', count=2, data=[(11111, 1), (11113, 1)])

        c = merge_two_time_results(a, b)

        self.assertEqual(c['count'], a['count']+b['count'])
        self.assertEqual(c['data'],  [[11111, 2], [11112, 0], [11113, 1]])


class AggregateResultsByLabelCase(TestCase):
    """ Tests utility function facet_queries.aggregate_results_by_label() """

    def test_works(self):
        a = dict(label='label1', count=1, data=[(11111, 1), (11112, 0)])
        b = dict(label='label1', count=2, data=[(11111, 1), (11113, 1)])
        c = dict(label='label2', count=4, data=[(11110, 2), (11112, 2)])

        results = aggregate_results_by_label([a, b, c], 'time')

        self.assertEqual(len(results), 2)

        ab_, c_ = results

        self.assertEqual(ab_['count'], a['count']+b['count'])
        self.assertEqual(ab_['data'],  [[11111, 2], [11112, 0], [11113, 1]])

        self.assertEqual(c_['count'],  c['count'])
        self.assertEqual(c_['data'],   [(11110, 2), (11112, 2)])


# TODO: add tests for facet_queries.get_agents()
# TODO: add tests for facet_queries.get_statuses()

