#from solariat_bottle.settings               import LOGGER
from datetime import datetime
from solariat_bottle.api.base import BaseAPIView, ReadOnlyMixin
from solariat_bottle.api.base import api_request, _get_request_data

from solariat_nlp.languages import LangComponentFactory


class TaggerAPIView(BaseAPIView, ReadOnlyMixin):

    endpoint = 'tagger/submit'

    @api_request
    def post(self, user, *args, **kwargs):
        """
        The tagger is a low level service that returns a Part-of-speech tagged sequence of tokens
        form a given set of input documents.

        Parameters:
            :param token: <Required> - A valid user access token
            :param samples: <Required> - A list of samples that need to be analyzed
            :param lang: <Optional> - the samples ISO language code, default 'en'

        Sample request:
            curl http://staging.socialoptimizr.com/api/v2.0/tagger/submit

            POST parameters:
                {
                    'token': '11dsa23ssaeqsad11321',
                    'samples': ['I need good headphones.', 'Ipod headphones are so crappy.']
                }

        Sample response:
            {
              "ok": true,
              "list": [
                [
                  [
                    "i",
                    "PRP"
                  ],
                  [
                    "need",
                    "VBP"
                  ],
                  [
                    "good",
                    "JJ"
                  ],
                  [
                    "headphones",
                    "NNS"
                  ],
                  [
                    ".",
                    "."
                  ]
                ],
                [
                  [
                    "ipod",
                    "NN"
                  ],
                  [
                    "headphones",
                    "NNS"
                  ],
                  [
                    "are",
                    "VBP"
                  ],
                  [
                    "so",
                    "RB"
                  ],
                  [
                    "crappy",
                    "JJ"
                  ],
                  [
                    ".",
                    "."
                  ]
                ]
              ]
            }

        """
        res = []
        start_time = datetime.utcnow()
        samples = _get_request_data().get('samples', [])
        lang = _get_request_data().get('lang', 'en')
        provider = LangComponentFactory.resolve(lang, 'en')
        chunker = provider.get_chunker()
        for sample in samples:
            res.append(chunker.tag_content(sample))
        return {"list": res,
                'latency': (datetime.utcnow() - start_time).total_seconds()}

