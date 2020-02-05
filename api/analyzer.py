#from solariat_bottle.settings               import LOGGER
from datetime import datetime
from solariat_bottle.api.base import BaseAPIView, ReadOnlyMixin
from solariat_bottle.api.base import api_request, _get_request_data

from solariat_nlp.sentiment import extract_sentiment
from solariat_nlp.sa_labels import SATYPE_ID_TO_NAME_MAP
from solariat_bottle.db.classifiers import AuthTextClassifier


class AnalyzerAPIView(BaseAPIView, ReadOnlyMixin):

    endpoint = 'analyzer/submit'

    @api_request
    def post(self, user, *args, **kwargs):
        """
        The analyzer conducts comprehensive semantic analysis of submitted content and returns the
        full complement of semantic enrichment.

        Parameters:
            :param token: <Required> - A valid user access token
            :param samples: <Required> - A list of samples that need to be analyzed

        Sample request:
            curl http://staging.socialoptimizr.com/api/v2.0/analyzer/submit

            POST parameters:
                {
                    'token': '11dsa23ssaeqsad11321',
                    'samples': ["iPod headphones are so crap. Can anyone recommend me some good headphones?"]
                }

        Sample response:
            {
              "ok": true,
              "list": [
                {
                  "latency": 0,
                  "classifier_scores": {
                    "54293a0b31eddd0fdd5dec95": 0.5
                  },
                  "sentiment_score": -100.0,
                  "sentiment": "Negative",
                  "utterances": [
                    {
                      "intention_type": "PROBLEM",
                      "sentiment": "Negative",
                      "topics": [
                        "ipod headphones"
                      ],
                      "content": "iPod headphones are so crap.",
                      "topic_confidence": 0.9157022010159953,
                      "sentiment_weight": -100.0,
                      "intention_type_confidence": 100.0
                    },
                    {
                      "intention_type": "ASKS",
                      "sentiment": "Neutral",
                      "topics": [
                        "headphones"
                      ],
                      "content": "Can anyone recommend me some good headphones?",
                      "topic_confidence": 0.9876543209876544,
                      "sentiment_weight": 0,
                      "intention_type_confidence": 100.0
                    }
                  ]
                }
              ]
            }
        """
        res = []
        samples = _get_request_data().get('samples', [])
        classifiers = [x for x in AuthTextClassifier.objects.find_by_user(user)]
        start_time = datetime.now()
        for sample in samples:
            item               = {}
            sample_sentiment   = extract_sentiment(sample)
            item['utterances'] = []
            item['sentiment']  = sample_sentiment['sentiment'].title
            item['sentiment_score']  = int(round(sample_sentiment['sentiment'].weight * 100))
            item['sentiment_confidence'] = int(round(sample_sentiment['confidence'] * 100))
            for sa in sample_sentiment['sas']:
                sa_item = {}
                sa_item['content'] = sa['content']
                sa_item['topics']  = sa['intention_topics']
                sa_item['intention_type']   = SATYPE_ID_TO_NAME_MAP[sa['intention_type_id']].upper()
                sa_item['topic_confidence'] = int(round(sa['intention_topic_conf'] * 100))
                sa_item['sentiment']        = sa['sentiment'].title
                sa_item['sentiment_score'] = int(round(sa['sentiment'].weight * 100))
                sa_item['sentiment_confidence'] = int(round(sa['sentiment_confidence']) * 100)
                sa_item['intention_type_confidence'] = int(round(sa['intention_type_conf'] * 100))
                item['utterances'].append(sa_item)
            item['classifiers'] = {}
            for clf in classifiers:
                item['classifiers'][str(clf.id)] = int(round(clf.predict(sample) * 100))
            res.append(item)
        return {"list": res,
                'latency': (datetime.now() - start_time).total_seconds()}

