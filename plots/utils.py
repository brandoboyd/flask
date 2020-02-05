'''
Any utilites that are related to different plots.
'''
from itertools import groupby
from operator  import itemgetter, add

from solariat.utils.iterfu import merge


def merge_two_time_results(a, b):
    """ Merges two results of plot_by=time aggregation
        a & b -> c
    """
    assert a['label'] == b['label']
    merged = merge(a['data'], b['data'])
    data   = []
    for tstamp,group in groupby(merged, itemgetter(0)):
        count = reduce(add, (x[1] for x in group))
        data.append([tstamp, count])
    c = a.copy()
    c['count'] += b['count']
    c['data']   = data
    return c


def merge_two_distribution_results(a, b):
    """ Merges two results of plot_by=distribution aggregation
        a & b -> c
    """
    c = a.copy()
    c['data'][0][1] = a['data'][0][1] + b['data'][0][1]
    assert len(c['data']) == 1
    return c


def aggregate_results_by_label(items, plot_by):
    """ Re-aggregates result items by label
        (assuming labels have been replaced)
    """
    get_label = lambda x: x['label']

    grouped = groupby(sorted(items, key=get_label), get_label)
    results = []

    for idx, (_,group) in enumerate(grouped, 1):
        if plot_by == 'time':
            merged = reduce(merge_two_time_results, group)
        else:
            merged = reduce(merge_two_distribution_results, group)
            merged['data'][0][0] = idx * 2  # rewrite indexes
        results.append(merged)

    return results

