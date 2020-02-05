import json
from optparse import Values
import unittest
from kafka.common import KafkaMessage
from mock import MagicMock, Mock
from solariat_bottle.daemons.twitter.stream.base import kafka_serializer
from solariat_bottle.daemons.twitter.stream.base.kafka_handler import KafkaHandler
from solariat_bottle.tests.base import BaseCase
from solariat_bottle.daemons.twitter.kafka_consumer import KafkaMessagesConsumer
from solariat_bottle.daemons.helpers import FeedApiPostCreator

class TestUnitKafkaConsumer(BaseCase):

    def setUp(self):
        super(TestUnitKafkaConsumer, self).setUp()
        bot_options = Values()
        bot_options.kafkatopic = 'test_topic'
        bot_options.kafkagroup = 'test_group'
        bot_options.broker = 'test_broker'
        bot_options.username = 'test'
        self.kafkaHandler = KafkaHandler(options=bot_options)
        self.kafkaHandler.handle_create_post = MagicMock()
        self.kafkaHandler.on_event_handler = MagicMock()

        self.KafkaMessagesConsumer = KafkaMessagesConsumer(bot_options, self.kafkaHandler, Mock())

    def test_call_handler_on_task(self):
        message = dict()
        message['task'] = 'sometask'
        message['username'] = 'someusername'
        message['kwargs'] = 'somekwargs'
        self.KafkaMessagesConsumer.consumer = [KafkaMessage('some_topic', 'some_partition', 'some_offset', 'some_key', kafka_serializer.serialize(message))]

        self.KafkaMessagesConsumer.run()

        self.assertTrue(self.kafkaHandler.handle_create_post.called, 'kafka handler should receive message')

    # @unittest.skip("while develop")
    def test_call_handler_on_event(self):
        message = dict()
        message['event'] = 'testevent'
        message['stream_data'] = 'teststreamdata'
        self.KafkaMessagesConsumer.consumer = [KafkaMessage('some_topic', 'some_partition', 'some_offset', 'some_key', kafka_serializer.serialize(message))]

        self.KafkaMessagesConsumer.run()

        self.assertTrue(self.kafkaHandler.on_event_handler.called, 'kafka handler should receive message')


class TestIntegrationKafkaConsumer(BaseCase):

    def setUp(self):
        bot_options = Values()
        bot_options.kafkatopic = 'test_topic'
        bot_options.kafkagroup = 'test_group'
        bot_options.broker = 'test_broker'
        self.kafkaHandler = KafkaHandler(options=bot_options)
        self.KafkaMessagesConsumer = KafkaMessagesConsumer(bot_options, self.kafkaHandler, Mock())

    def test_public_message(self):

#region messageCreation
        message = dict()

        kwargs = dict()
        kwargs['post_creator'] = FeedApiPostCreator
        kwargs['password'] = "test123"
        kwargs['multiprocess_concurrency'] = 0
        kwargs['url'] = "http://127.0.0.1:3031"

        task = json.loads('''{"contributors": null, "truncated": false,
        "text": "#euggetangotest 9", "is_quote_status": false, "in_reply_to_status_id": null,
        "id": 660428793367130112, "favorite_count": 0, "source": "<a href='http://twitter.com' rel='nofollow'>Twitter Web Client</a>",
        "retweeted": false, "coordinates": null, "timestamp_ms": "1446293469169",
        "in_reply_to_screen_name": null, "in_reply_to_user_id": null, "retweet_count": 0, "id_str": "660428793367130112",
        "favorited": false, "geo": null, "in_reply_to_user_id_str": null,
        "lang": "und", "created_at": "Sat Oct 31 12:11:09 +0000 2015", "filter_level": "low", "in_reply_to_status_id_str": null,
        "place": null }''')
        task['entities'] = json.loads('''{"user_mentions": [], "symbols": [], "hashtags": [{"indices": [0, 15], "text": "getangotest"}], "urls": []}''')
        task['user'] = json.loads('''{"follow_request_sent": null, "profile_use_background_image": true, "id": 3940663,
        "verified": false, "profile_image_url_https": "https://abs.twimg.com/sticky/default_profile_images/default_profile_2_normal.png",
        "profile_sidebar_fill_color": "DDEEF6", "is_translator": false, "geo_enabled": false, "profile_text_color": "333333",
        "followers_count": 1, "protected": false, "location": null, "default_profile_image": true, "id_str": "306253",
        "utc_offset": null, "statuses_count": 167, "description": null, "friends_count": 0, "profile_link_color": "0084B4",
        "profile_image_url": "http://abs.twimg.com/sticky/default_profile_images/default_profile_2_normal.png", "notifications": null,
        "profile_background_image_url_https": "https://abs.twimg.com/images/themes/theme1/bg.png", "profile_background_color": "C0DEED",
        "profile_background_image_url": "http://abs.twimg.com/images/themes/theme1/bg.png", "screen_name": "test_ge", "lang": "en",
        "profile_background_tile": false, "favourites_count": 0, "name": "GE Test", "url": null, "created_at":
        "Mon Oct 12 21:35:08 +0000 2015", "contributors_enabled": false, "time_zone": null, "profile_sidebar_border_color":
        "C0DEED", "default_profile": true, "following": null, "listed_count": 0}''')

        message['kwargs'] = kwargs
        message['task'] = task
        message['username'] = 'super_user@solariat.com'
#endregion

        self.KafkaMessagesConsumer.consumer = [KafkaMessage('some_topic', 0, 0, None, kafka_serializer.serialize(message))]

        self.KafkaMessagesConsumer.run()

    def test_private_message(self):

#region messageCreation
        message = dict()

        kwargs = dict()
        kwargs['post_creator'] = FeedApiPostCreator
        kwargs['password'] = "test123"
        kwargs['multiprocess_concurrency'] = 0
        kwargs['url'] = "http://127.0.0.1:3031"

        task = json.loads('''{"contributors": null, "truncated": false, "text":
         "@test_ge #sometext 454", "is_quote_status": false, "in_reply_to_status_id": null, "id": 125125224,
         "favorite_count": 0, "source": "<a href='http://twitter.com' rel='nofollow'>Twitter Web Client</a>", "retweeted":
         false, "coordinates": null, "timestamp_ms": "1446311725370", "in_reply_to_screen_name": "test_ge", "in_reply_to_user_id":
         3940625663, "retweet_count": 0, "id_str": "660505365424037889", "favorited": false, "geo": null, "in_reply_to_user_id_str": "123123",
         "lang": "und", "created_at": "Sat Oct 31 17:15:25 +0000 2015", "filter_level": "low", "in_reply_to_status_id_str": null, "place": null}''')
        task['entities'] = json.loads('''{"user_mentions": [{"indices": [0, 8],
         "screen_name": "test_ge", "id": 3940625663, "name": "GE Test", "id_str": "124124"}], "symbols": [], "hashtags":
         [{"indices": [9, 24], "text": "euggetangotest"}], "urls": []}''')
        task['user'] = json.loads('''{"follow_request_sent":
         null, "profile_use_background_image": true, "id": 205189715, "verified": false, "profile_image_url_https":
         "https://abs.twimg.com/sticky/default_profile_images/default_profile_3_normal.png", "profile_sidebar_fill_color":
         "DDEEF6", "is_translator": false, "geo_enabled": false, "profile_text_color": "333333", "followers_count": 0, "protected":
         false, "location": null, "default_profile_image": true, "id_str": "205189715", "utc_offset": null, "statuses_count": 9,
         "description": null, "friends_count": 0, "profile_link_color": "0084B4", "profile_image_url":
         "http://abs.twimg.com/sticky/default_profile_images/default_profile_3_normal.png", "notifications": null,
         "profile_background_image_url_https": "https://abs.twimg.com/images/themes/theme1/bg.png", "profile_background_color":
         "C0DEED", "profile_background_image_url": "http://abs.twimg.com/images/themes/theme1/bg.png", "screen_name":
         "somename", "lang": "en", "profile_background_tile": false, "favourites_count": 0, "name": "EVG", "url": null,
         "created_at": "Wed Oct 20 10:09:01 +0000 2010", "contributors_enabled": false, "time_zone": null, "profile_sidebar_border_color":
         "C0DEED", "default_profile": true, "following": null, "listed_count": 0}''')

        message['kwargs'] = kwargs
        message['task'] = task
        message['username'] = 'super_user@solariat.com'
#endregion

        self.KafkaMessagesConsumer.consumer = [KafkaMessage('some_topic', 0, 0, None, kafka_serializer.serialize(message))]

        self.KafkaMessagesConsumer.run()



    def test_event(self):

#region messageCreation
        message = json.loads('''{"stream_data": {"channel_id": null, "screen_name": "test_ge"}, "event": {"source":
        {"follow_request_sent": false, "profile_use_background_image": true, "id": 4353464, "verified": false,
        "profile_image_url_https": "https://abs.twimg.com/sticky/default_profile_images/default_profile_3_normal.png",
        "profile_sidebar_fill_color": "DDEEF6", "is_translator": false, "geo_enabled": false, "profile_text_color": "333333",
        "followers_count": 0, "protected": false, "location": null, "default_profile_image": true, "id_str":
        "205189715", "lang": "en", "utc_offset": null, "statuses_count": 9, "description": null, "friends_count": 0,
        "profile_link_color": "0084B4", "profile_image_url": "http://abs.twimg.com/sticky/default_profile_images/default_profile_3_normal.png",
        "notifications": false, "profile_background_image_url_https": "https://abs.twimg.com/images/themes/theme1/bg.png",
        "profile_background_color": "C0DEED", "profile_background_image_url": "http://abs.twimg.com/images/themes/theme1/bg.png",
        "screen_name": "super-account", "is_translation_enabled": false, "profile_background_tile": false, "favourites_count": 0,
        "name": "Evgeny", "url": null, "created_at": "Wed Oct 20 10:09:01 +0000 2010", "contributors_enabled": false,
        "time_zone": null, "profile_sidebar_border_color": "C0DEED", "default_profile": true, "following": false, "listed_count": 0},
        "created_at": "Sat Oct 31 21:00:45 +0000 2015", "event": "follow", "target": {"follow_request_sent": false,
        "profile_use_background_image": true, "id": 32463246, "verified": false, "profile_image_url_https":
        "https://abs.twimg.com/sticky/default_profile_images/default_profile_2_normal.png", "profile_sidebar_fill_color":
        "DDEEF6", "is_translator": false, "geo_enabled": false, "profile_text_color": "333333", "followers_count": 1, "protected":
        false, "location": null, "default_profile_image": true, "id_str": "23463246", "lang": "en", "utc_offset": null,
        "statuses_count": 167, "description": null, "friends_count": 1, "profile_link_color": "0084B4", "profile_image_url":
        "http://abs.twimg.com/sticky/default_profile_images/default_profile_2_normal.png", "notifications": false,
        "profile_background_image_url_https": "https://abs.twimg.com/images/themes/theme1/bg.png", "profile_background_color":
        "C0DEED", "profile_background_image_url": "http://abs.twimg.com/images/themes/theme1/bg.png", "screen_name":
        "test_ge", "is_translation_enabled": false, "profile_background_tile": false, "favourites_count": 0, "name":
        "GE Test", "url": null, "created_at": "Mon Oct 12 21:35:08 +0000 2015", "contributors_enabled": false, "time_zone": null,
        "profile_sidebar_border_color": "C0DEED", "default_profile": true, "following": false, "listed_count": 1}}}''')
#endregion

        self.KafkaMessagesConsumer.consumer = [KafkaMessage('some_topic', 0, 0, None, kafka_serializer.serialize(message))]

        self.KafkaMessagesConsumer.run()