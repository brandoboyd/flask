#from solariat_bottle.settings       import LOGGER
import json
from solariat.utils.text import force_unicode
from solariat_bottle.api.base       import ModelAPIView, validate_params
from solariat_bottle.db.events.event   import DynamicEvent
from solariat_bottle.db.post.base   import Post
from solariat_bottle.db.post.utils  import factory_by_user
from solariat_bottle.utils.post     import get_service_channel

from solariat_nlp.sentiment import extract_sentiment
from solariat_nlp.sa_labels import SATYPE_ID_TO_NAME_MAP


class PostAPIView(ModelAPIView):
    model = Post
    endpoint = 'posts'
    required_fields = ['channel', 'content']

    def post(self, *args, **kwargs):
        """
        Create a post entity
        Returns a json of semantically enhanced post content

        Sample request:
            curl http://staging.socialoptimizr.com/api/v2.0/posts

            POST Parameters:
                :param token: <Required> - A valid user access token
                :param content: <Required> - The content of the post you want to have analyzed
                :param channel: <Required> - The id of the channel to which we are posting data
                :param format_docs: - boolean, default: true, should apply post to json formatting
                :param return_response: - boolean, default: true, should return created post
                :param add_to_queue: - boolean, default: true, should post be added to queue
                    for further consumption via api/queue
            -----------------------------------------------------------------------------------
            Alternatively:
                :param token: <Required> - A valid user access token
                :param content: <Required> - The content of the post you want to have analyzed
                :param channel: <Required> - The id of the channel to which we are posting data
                :serialized_to_json: - Flag which indicate that posts sends in serialized json form
                :post_object_data: Post object data in serialized form
        Output:
            A dictionary in the fork {'ok': true, 'item': <post json>}
            In case of no matched channels, list will be empty

        Sample valid response:
            HTTP-200
            {
              "item": {
                "content": "Test post",
                "smart_tags": [
                  {
                    "score": 0.5,
                    "uri": "http://127.0.0.1:3031/api/v2.0/smarttags/5411c27a31eddd2b573a98d5",
                    "title": "tag1"
                  },
                  {
                    "score": 0.5,
                    "uri": "http://127.0.0.1:3031/api/v2.0/smarttags/5411c27a31eddd2b573a98d6",
                    "title": "tag2"
                  }
                ],
                "actionability": 0.5,
                "utterances": [
                  {
                    "topic_confidence": 0.7034869070052292,
                    "topic": [
                      "test post"
                    ],
                    "content": "Test post",
                    "type": "Junk",
                    "type_confidence": 1.0
                  }
                ]
              },
              "ok": true
            }


        Missing required parameter:
            HTTP-400
            {
              "code": 113,
              "error": "Required parameter 'channel' not present"
            }
        """
        return self._post(*args, **kwargs)

    @validate_params
    def _create_doc(self, user, *args, **kwargs):
        def parse_bool(val):
            return val in ('', None, True, 'true', 'True', 'y', 'yes')

        add_to_queue = parse_bool(kwargs.pop('add_to_queue', True))
        format_docs = parse_bool(kwargs.pop('format_docs', True))
        return_response = parse_bool(kwargs.pop('return_response', True))
        if {'serialized_to_json', 'post_object_data'} <= set(kwargs.keys()) \
                and parse_bool(kwargs['serialized_to_json']):
            post_kwargs = json.loads(kwargs['post_object_data'])
        else:
            post_kwargs = kwargs
        post_kwargs.setdefault('add_to_queue', add_to_queue)
        post = factory_by_user(user, **post_kwargs)
        if not return_response:
            return {'ok': True}

        if format_docs:
            return self._format_single_doc(post)
        return post

    @staticmethod
    def translate_score(input_score):
        """
        :param input_score: A score between 0 and 1
        :return: A translated score between 0 - 100
        """
        return int(round(input_score * 100))

    @classmethod
    def _format_doc(cls, item, channel=None):
        ''' Format a post ready to be JSONified'''

        if isinstance(item, DynamicEvent):
            return super(PostAPIView, cls)._format_doc(item)

        from solariat_bottle.api.smarttags import SmartTagAPIView
        tag_scores = []
        channel = channel or item.channel

        for tag in item.active_smart_tags:
            if tag not in get_service_channel(channel).inbound_channel.smart_tags:
                continue
            tag_uri = SmartTagAPIView._format_doc(tag)['uri']
            if not tag.match(item):
                tag_scores.append({'name': tag.title,
                                   'confidence': 0,
                                   'uri': tag_uri,
                                   'id': str(tag.id)})
            else:
                tag_scores.append({'name': tag.title,
                                   'confidence': cls.translate_score(tag.channel_filter._predict_fit(item)),
                                   'uri': tag_uri,
                                   'id': str(tag.id)})
        utterances = []
        for s_a in item.speech_acts:
            sentiment_sample = extract_sentiment(s_a['content'])
            utterances.append(dict(
                content=s_a['content'],
                topics=s_a['intention_topics'],
                topic_confidence=cls.translate_score(s_a['intention_topic_conf']),
                intention_type=SATYPE_ID_TO_NAME_MAP[s_a['intention_type_id']].upper(),
                intention_type_confidence=cls.translate_score(s_a['intention_type_conf']),
                sentiment=sentiment_sample['sentiment'].title,
                sentiment_score=cls.translate_score(sentiment_sample['score']),
                sentiment_confidence=cls.translate_score(sentiment_sample['confidence']))
            )
        sentiment_sample = extract_sentiment(item.content)
        # handling matchables

        return dict(id=item.id,
                    content=item.content,
                    smart_tags=tag_scores,
                    actionability=cls.translate_score(channel.channel_filter._predict_fit(item)),
                    utterances=utterances,
                    sentiment=sentiment_sample['sentiment'].title,
                    sentiment_score=cls.translate_score(sentiment_sample['score']),
                    sentiment_confidence=cls.translate_score(sentiment_sample['confidence']))
