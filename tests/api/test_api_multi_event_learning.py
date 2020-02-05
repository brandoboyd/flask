import json

from solariat_bottle.tests.base import RestCase
from solariat_bottle.db.channel.web_click import WebClickChannel
from solariat_bottle.db.channel.chat import ChatServiceChannel
from solariat_bottle.db.post.web_clicks import WebClick
from solariat_bottle.db.post.chat import ChatPost
from solariat_bottle.db.predictors.multi_channel_smart_tag import SingleEventTag, MultiEventTag
from solariat_bottle.db.predictors.multi_channel_tag_vectorizer import ChatMessageValidator, WebClickValidator


class MultiEventLearning(RestCase):

    def setUp(self):
        super(MultiEventLearning, self).setUp()
        self.customer_id = None
        self.web_session_id = "test_web_session_id"
        self.web_customer_id = "web_customer_id"
        self.web_click_channel = WebClickChannel.objects.get_or_create(title='WebClickChannel',
                                                                       account=self.user.account)
        self.chat_channel = ChatServiceChannel.objects.get_or_create(title='ChatServiceChannel',
                                                                     account=self.user.account)

    def click_page(self, url, element_html):
        token = self.get_token()
        click_data = dict(channels=[str(self.web_click_channel.id)],
                          session_id=self.web_session_id,
                          url=url,
                          element_html=element_html,
                          token=token,
                          type="web",
                          is_inbound=True,
                          native_id='web_customer_id')
        if self.customer_id is not None:
            click_data['actor_id'] = self.customer_id
        resp = self.client.post('/api/v2.0/events',
                                 data=json.dumps(click_data),
                                 content_type='application/json',
                                 base_url='https://localhost')
        self.assertEqual(resp.status_code, 200, resp.data)
        click_data = json.loads(resp.data)
        self.assertTrue(click_data['ok'])
        self.customer_id = click_data['item']['actor']['id']
        return click_data['item']

    def test_multi_click_events(self):
        self.assertEqual(WebClick.objects.count(), 0)
        self.click_page('test', 'test')
        self.click_page('test2', 'test2')
        self.click_page('test3', 'test3')
        event_json = self.click_page('test4', 'test4')
        self.assertEqual(WebClick.objects.count(), 4)
        last_click = WebClick.objects.get(event_json['id'])
        sequence = WebClick.objects.lookup_history(last_click, lookback_window=30)
        self.assertEqual(len(sequence), 4)

        SingleEventTag.objects.create(account_id=self.account.id,
                                      display_name="Single click, laptop",
                                      channels=[self.web_click_channel.id],
                                      features_metadata={},
                                      acceptance_rule="isinstance(event, WebClick) and 'laptop' in event.url")
        tag1 = MultiEventTag.objects.create(account_id=self.account.id,
                                            display_name="Web Click Tag - No metadata",
                                            channels=[self.web_click_channel.id],
                                            features_metadata={'web': {WebClickValidator.KEY_URL_REGEX: [],
                                                                       WebClickValidator.KEY_ELEMENT_REGEX: []}},
                                            event_lookup_horizon=4)
        regexes = ['search', 'laptop', 'stuff', 'phone']
        tag2 = MultiEventTag.objects.create(account_id=self.account.id,
                                            display_name="Web Click Tag - With metadata",
                                            channels=[self.web_click_channel.id],
                                            features_metadata={'web': {WebClickValidator.KEY_URL_REGEX: regexes,
                                                                       WebClickValidator.KEY_ELEMENT_REGEX: regexes}},
                                            event_lookup_horizon=4)
        # search_url = "http://trololol.com/search"
        # laptop_url = "http://trololol.com/buy/laptops"
        # phone_url = "http://trololol.com/buy/phone"
        # stuff_url = "http://trololol.com/buy/stuff"
        # search_href = "<a href='search()'>Search</a>"
        # laptop_href = "<a href='buyLaptop()'>Buy</a>"
        # phone_href = "<a href='buyPhone()'>Buy</a>"
        # stuff_href = "<a href='buyStuff()'>Buy</a>"

        search_url = "search"
        laptop_url = "laptops"
        phone_url = "phone"
        stuff_url = "stuff"
        search_href = "Search"
        laptop_href = "BuyLaptop"
        phone_href = "BuyPhone"
        stuff_href = "BuyStuff"

        def click_search():
            return self.click_page(search_url, search_href)

        def click_laptop():
            return self.click_page(laptop_url, laptop_href)

        def click_phone():
            return self.click_page(phone_url, phone_href)

        def click_stuff():
            return self.click_page(stuff_url, stuff_href)

        click_stuff()
        click_phone()
        click_stuff()
        click_phone()
        click_stuff()
        click_stuff()
        click_search()
        laptop_event = WebClick.objects.get(click_laptop()['id'])

        print tag1.get_features(laptop_event)
        print tag2.get_features(laptop_event)

        score1 = tag1.score(laptop_event)
        score2 = tag2.score(laptop_event)

        tag1.accept(laptop_event)
        tag2.reject(laptop_event)

        new_score1 = tag1.score(laptop_event)
        new_score2 = tag2.score(laptop_event)

        self.assertTrue(new_score1 > score1)
        self.assertTrue(new_score2 < score2)

        # Now try to learn that tag1 cares about a search followed by a laptop click while
        # tag2 cares about a search followed by a phone click

        click_stuff()
        click_stuff()
        click_stuff()
        click_stuff()
        click_stuff()
        stuff_event = WebClick.objects.get(click_stuff()['id'])
        tag1.reject(stuff_event)
        tag2.accept(stuff_event)

        click_stuff()
        click_phone()
        click_stuff()
        click_phone()
        click_phone()
        stuff_event = WebClick.objects.get(click_stuff()['id'])
        tag1.reject(stuff_event)
        tag2.accept(stuff_event)

        click_stuff()
        click_phone()
        click_stuff()
        click_stuff()
        click_search()
        phone_event = WebClick.objects.get(click_phone()['id'])
        tag1.reject(phone_event)
        tag2.accept(phone_event)

        click_stuff()
        click_stuff()
        click_stuff()
        click_stuff()
        click_search()
        phone_event = WebClick.objects.get(click_phone()['id'])
        tag1.reject(phone_event)
        tag2.accept(phone_event)

        click_stuff()
        click_stuff()
        click_stuff()
        click_phone()
        click_search()
        phone_event = WebClick.objects.get(click_phone()['id'])
        tag1.reject(phone_event)
        tag2.accept(phone_event)

        click_stuff()
        click_phone()
        click_search()
        click_stuff()
        click_stuff()
        click_search()
        laptop_event = WebClick.objects.get(click_laptop()['id'])
        tag1.accept(laptop_event)
        tag2.reject(laptop_event)

        click_stuff()
        click_stuff()
        click_stuff()
        click_stuff()
        click_stuff()
        click_search()
        laptop_event = WebClick.objects.get(click_laptop()['id'])
        tag1.accept(laptop_event)
        tag2.reject(laptop_event)

        click_stuff()
        click_stuff()
        click_phone()
        click_phone()
        click_phone()
        click_search()
        laptop_event = WebClick.objects.get(click_laptop()['id'])
        tag1.accept(laptop_event)
        tag2.reject(laptop_event)


        click_stuff()
        click_stuff()
        click_search()
        click_search()
        click_search()
        click_search()
        laptop_event = WebClick.objects.get(click_laptop()['id'])
        tag1.accept(laptop_event)
        tag2.reject(laptop_event)

        click_stuff()
        click_stuff()
        click_search()
        click_phone()
        click_search()
        laptop_event = WebClick.objects.get(click_laptop()['id'])
        tag1.accept(laptop_event)
        tag2.accept(laptop_event)

        click_stuff()
        click_search()
        click_phone()
        click_search()
        laptop_event = WebClick.objects.get(click_laptop()['id'])
        tag1.accept(laptop_event)
        tag2.accept(laptop_event)
        # Assume we're done with training, lets see some scores

        print "========================= SCORES BELOW ================================="
        expected_low = []
        expected_highs = []
        click_search()
        click_stuff()
        click_search()
        click_stuff()
        click_search()
        stuff_event = WebClick.objects.get(click_stuff()['id'])
        both_indifferent = (tag1.score(stuff_event), tag2.score(stuff_event))
        print both_indifferent
        expected_low.extend(both_indifferent)

        click_stuff()
        click_stuff()
        click_stuff()
        click_stuff()
        click_search()
        laptop_event = WebClick.objects.get(click_laptop()['id'])
        tag1_likes_tag_hates = [tag1.score(laptop_event), tag2.score(laptop_event)]
        print tag1_likes_tag_hates
        expected_low.append(tag1_likes_tag_hates[1])
        expected_highs.append(tag1_likes_tag_hates[0])

        click_stuff()
        click_stuff()
        click_stuff()
        click_stuff()
        click_search()
        phone_event = WebClick.objects.get(click_phone()['id'])
        tag1_hates_tag2_likes = (tag1.score(phone_event), tag2.score(phone_event))
        print tag1_hates_tag2_likes
        expected_low.append(tag1_hates_tag2_likes[0])
        expected_highs.append(tag1_hates_tag2_likes[1])

        click_stuff()
        click_stuff()
        click_search()
        click_phone()
        click_search()
        laptop_event = WebClick.objects.get(click_laptop()['id'])
        both_tag_like = (tag1.score(laptop_event), tag2.score(laptop_event))
        print both_tag_like
        expected_highs.extend(both_tag_like)

        self.assertTrue(sorted(expected_highs)[0] > sorted(expected_low)[-1])