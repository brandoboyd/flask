from solariat_bottle.plots.utils import aggregate_results_by_label
from solariat_nlp.sentiment import get_sentiment_by_intention


res = {'list': [{'count': 15, 'level': 'hour',
           'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0], [1371783600000, 0], [1371787200000, 0],
                    [1371790800000, 1], [1371794400000, 1], [1371798000000, 1], [1371801600000, 0], [1371805200000, 2],
                    [1371808800000, 0], [1371812400000, 7], [1371816000000, 3], [1371819600000, 0], [1371823200000, 0],
                    [1371826800000, 0], [1371830400000, 0], [1371834000000, 0], [1371837600000, 0], [1371841200000, 0],
                    [1371844800000, 0], [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]], 'label': 'asks'},
          {'count': 5, 'level': 'hour',
           'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0], [1371783600000, 0], [1371787200000, 0],
                    [1371790800000, 0], [1371794400000, 0], [1371798000000, 0], [1371801600000, 0], [1371805200000, 1],
                    [1371808800000, 0], [1371812400000, 1], [1371816000000, 3], [1371819600000, 0], [1371823200000, 0],
                    [1371826800000, 0], [1371830400000, 0], [1371834000000, 0], [1371837600000, 0], [1371841200000, 0],
                    [1371844800000, 0], [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]], 'label': 'needs'},
          {'count': 24, 'level': 'hour',
           'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0], [1371783600000, 0], [1371787200000, 0],
                    [1371790800000, 0], [1371794400000, 1], [1371798000000, 1], [1371801600000, 1], [1371805200000, 3],
                    [1371808800000, 7], [1371812400000, 6], [1371816000000, 5], [1371819600000, 0], [1371823200000, 0],
                    [1371826800000, 0], [1371830400000, 0], [1371834000000, 0], [1371837600000, 0], [1371841200000, 0],
                    [1371844800000, 0], [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]],
           'label': 'problem'}, {'count': 8, 'level': 'hour',
                                 'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0],
                                          [1371783600000, 0], [1371787200000, 0], [1371790800000, 0],
                                          [1371794400000, 1], [1371798000000, 3], [1371801600000, 0],
                                          [1371805200000, 1], [1371808800000, 0], [1371812400000, 3],
                                          [1371816000000, 0], [1371819600000, 0], [1371823200000, 0],
                                          [1371826800000, 0], [1371830400000, 0], [1371834000000, 0],
                                          [1371837600000, 0], [1371841200000, 0], [1371844800000, 0],
                                          [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]],
                                 'label': 'likes'}, {'count': 5, 'level': 'hour',
                                                     'data': [[1371772800000, 0], [1371776400000, 0],
                                                              [1371780000000, 0], [1371783600000, 0],
                                                              [1371787200000, 0], [1371790800000, 0],
                                                              [1371794400000, 0], [1371798000000, 0],
                                                              [1371801600000, 1], [1371805200000, 0],
                                                              [1371808800000, 1], [1371812400000, 2],
                                                              [1371816000000, 1], [1371819600000, 0],
                                                              [1371823200000, 0], [1371826800000, 0],
                                                              [1371830400000, 0], [1371834000000, 0],
                                                              [1371837600000, 0], [1371841200000, 0],
                                                              [1371844800000, 0], [1371848400000, 0],
                                                              [1371852000000, 0], [1371855600000, 0]],
                                                     'label': 'gratitude'}, {'count': 1, 'level': 'hour',
                                                                             'data': [[1371772800000, 0],
                                                                                      [1371776400000, 0],
                                                                                      [1371780000000, 0],
                                                                                      [1371783600000, 0],
                                                                                      [1371787200000, 0],
                                                                                      [1371790800000, 0],
                                                                                      [1371794400000, 0],
                                                                                      [1371798000000, 0],
                                                                                      [1371801600000, 0],
                                                                                      [1371805200000, 0],
                                                                                      [1371808800000, 0],
                                                                                      [1371812400000, 0],
                                                                                      [1371816000000, 1],
                                                                                      [1371819600000, 0],
                                                                                      [1371823200000, 0],
                                                                                      [1371826800000, 0],
                                                                                      [1371830400000, 0],
                                                                                      [1371834000000, 0],
                                                                                      [1371837600000, 0],
                                                                                      [1371841200000, 0],
                                                                                      [1371844800000, 0],
                                                                                      [1371848400000, 0],
                                                                                      [1371852000000, 0],
                                                                                      [1371855600000, 0]],
                                                                             'label': 'apology'},
          {'count': 6, 'level': 'hour',
           'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0], [1371783600000, 0], [1371787200000, 0],
                    [1371790800000, 1], [1371794400000, 0], [1371798000000, 1], [1371801600000, 1], [1371805200000, 0],
                    [1371808800000, 1], [1371812400000, 2], [1371816000000, 0], [1371819600000, 0], [1371823200000, 0],
                    [1371826800000, 0], [1371830400000, 0], [1371834000000, 0], [1371837600000, 0], [1371841200000, 0],
                    [1371844800000, 0], [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]],
           'label': 'recommendation'}, {'count': 11, 'level': 'hour',
                                        'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0],
                                                 [1371783600000, 0], [1371787200000, 0], [1371790800000, 0],
                                                 [1371794400000, 0], [1371798000000, 0], [1371801600000, 1],
                                                 [1371805200000, 4], [1371808800000, 3], [1371812400000, 1],
                                                 [1371816000000, 2], [1371819600000, 0], [1371823200000, 0],
                                                 [1371826800000, 0], [1371830400000, 0], [1371834000000, 0],
                                                 [1371837600000, 0], [1371841200000, 0], [1371844800000, 0],
                                                 [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]],
                                        'label': 'junk'}], 'ok': True, 'level': 'hour'}


after = {'list': [{'count': 24, 'level': 'hour',
           'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0], [1371783600000, 0], [1371787200000, 0],
                    [1371790800000, 0], [1371794400000, 1], [1371798000000, 1], [1371801600000, 1], [1371805200000, 3],
                    [1371808800000, 7], [1371812400000, 6], [1371816000000, 5], [1371819600000, 0], [1371823200000, 0],
                    [1371826800000, 0], [1371830400000, 0], [1371834000000, 0], [1371837600000, 0], [1371841200000, 0],
                    [1371844800000, 0], [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]],
           'label': 'negative'}, {'count': 38, 'level': 'hour',
                                  'data': [(1371772800000, 0), (1371776400000, 0), (1371780000000, 0),
                                           (1371783600000, 0), (1371787200000, 0), (1371790800000, 0),
                                           (1371794400000, 0), (1371798000000, 0), (1371801600000, 1),
                                           (1371805200000, 4), (1371808800000, 3), (1371812400000, 1),
                                           (1371816000000, 2), (1371819600000, 0), (1371823200000, 0),
                                           (1371826800000, 0), (1371830400000, 0), (1371834000000, 0),
                                           (1371837600000, 0), (1371841200000, 0), (1371844800000, 0),
                                           (1371848400000, 0), (1371852000000, 0), (1371855600000, 0),
                                           (1371772800000, 0), (1371776400000, 0), (1371780000000, 0),
                                           (1371783600000, 0), (1371787200000, 0), (1371790800000, 1),
                                           (1371794400000, 0), (1371798000000, 1), (1371801600000, 1),
                                           (1371805200000, 0), (1371808800000, 1), (1371812400000, 2),
                                           (1371816000000, 0), (1371819600000, 0), (1371823200000, 0),
                                           (1371826800000, 0), (1371830400000, 0), (1371834000000, 0),
                                           (1371837600000, 0), (1371841200000, 0), (1371844800000, 0),
                                           (1371848400000, 0), (1371852000000, 0), (1371855600000, 0),
                                           (1371772800000, 0), (1371776400000, 0), (1371780000000, 0),
                                           (1371783600000, 0), (1371787200000, 0), (1371790800000, 0),
                                           (1371794400000, 0), (1371798000000, 0), (1371801600000, 0),
                                           (1371805200000, 0), (1371808800000, 0), (1371812400000, 0),
                                           (1371816000000, 1), (1371819600000, 0), (1371823200000, 0),
                                           (1371826800000, 0), (1371830400000, 0), (1371834000000, 0),
                                           (1371837600000, 0), (1371841200000, 0), (1371844800000, 0),
                                           (1371848400000, 0), (1371852000000, 0), (1371855600000, 0),
                                           (1371772800000, 0), (1371776400000, 0), (1371780000000, 0),
                                           (1371783600000, 0), (1371787200000, 0), (1371790800000, 1),
                                           (1371794400000, 1), (1371798000000, 1), (1371801600000, 0),
                                           (1371805200000, 3), (1371808800000, 0), (1371812400000, 8),
                                           (1371816000000, 6), (1371819600000, 0), (1371823200000, 0),
                                           (1371826800000, 0), (1371830400000, 0), (1371834000000, 0),
                                           (1371837600000, 0), (1371841200000, 0), (1371844800000, 0),
                                           (1371848400000, 0), (1371852000000, 0), (1371855600000, 0)],
                                  'label': 'neutral'}, {'count': 13, 'label': 'positive',
                                                        'data': [(1371772800000, 0), (1371776400000, 0),
                                                                 (1371780000000, 0), (1371783600000, 0),
                                                                 (1371787200000, 0), (1371790800000, 0),
                                                                 (1371794400000, 1), (1371798000000, 3),
                                                                 (1371801600000, 1), (1371805200000, 1),
                                                                 (1371808800000, 1), (1371812400000, 5),
                                                                 (1371816000000, 1), (1371819600000, 0),
                                                                 (1371823200000, 0), (1371826800000, 0),
                                                                 (1371830400000, 0), (1371834000000, 0),
                                                                 (1371837600000, 0), (1371841200000, 0),
                                                                 (1371844800000, 0), (1371848400000, 0),
                                                                 (1371852000000, 0), (1371855600000, 0)],
                                                        'level': 'hour'}], 'ok': True, 'level': 'hour'}

e = [{'count': 24, 'label': 'negative',
      'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0], [1371783600000, 0], [1371787200000, 0],
               [1371790800000, 0], [1371794400000, 1], [1371798000000, 1], [1371801600000, 1], [1371805200000, 3],
               [1371808800000, 7], [1371812400000, 6], [1371816000000, 5], [1371819600000, 0], [1371823200000, 0],
               [1371826800000, 0], [1371830400000, 0], [1371834000000, 0], [1371837600000, 0], [1371841200000, 0],
               [1371844800000, 0], [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]], 'level': 'hour'},
     {'count': 38, 'label': 'neutral',
      'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0], [1371783600000, 0], [1371787200000, 0],
               [1371790800000, 2], [1371794400000, 1], [1371798000000, 2], [1371801600000, 2], [1371805200000, 7],
               [1371808800000, 4], [1371812400000, 11], [1371816000000, 9], [1371819600000, 0], [1371823200000, 0],
               [1371826800000, 0], [1371830400000, 0], [1371834000000, 0], [1371837600000, 0], [1371841200000, 0],
               [1371844800000, 0], [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]], 'level': 'hour'},
     {'count': 13, 'level': 'hour',
      'data': [[1371772800000, 0], [1371776400000, 0], [1371780000000, 0], [1371783600000, 0], [1371787200000, 0],
               [1371790800000, 0], [1371794400000, 1], [1371798000000, 3], [1371801600000, 1], [1371805200000, 1],
               [1371808800000, 1], [1371812400000, 5], [1371816000000, 1], [1371819600000, 0], [1371823200000, 0],
               [1371826800000, 0], [1371830400000, 0], [1371834000000, 0], [1371837600000, 0], [1371841200000, 0],
               [1371844800000, 0], [1371848400000, 0], [1371852000000, 0], [1371855600000, 0]], 'label': 'positive'}]

def test():
    for it in res['list']:
        it['label'] = get_sentiment_by_intention(it['label'])
    print res['list']
    print aggregate_results_by_label(res['list'], 'time')


if __name__ == '__main__':
    test()