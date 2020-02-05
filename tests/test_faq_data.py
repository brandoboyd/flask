import json
import time

import os
import solariat_bottle
from solariat_bottle.tests.base import RestCase

from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.faq import FAQ, DbBasedSE1, FAQDocumentInfo
from solariat_bottle.db.channel.faq import FAQChannel
from solariat_bottle.db.post.faq_query import FAQQueryEvent
from solariat_bottle.data.telecom_faq_data import TELECOM_DATA


FAQ_DATA = [
    {
      "answer": "The Groupon Reserve discount applies to the entire bill, including alcohol, except in certain cities where prohibited. Please carefully review the Fine Print for all applicable restrictions.",
      "question": "Is alcohol discounted when I make a reservation using Reserve?", 
      "id": "groupon_201", 
      "queries": [
        "Why I did not get a discount on alcohol when I made a restaurant reservation with Groupon Reserve?", 
        "Does the Groupon Reserve discount apply to all food and drinks I order?", 
        "Does the discount apply to all alcoholic beverages including beer and wine?", 
        "If the discount does not apply to wine are we permitted to bring our own?", 
        "Can I use groupon reserve for alcohol?"
      ]
    }, 
    {
      "answer": "There is no need to call ahead. Once you click \"Book Reservation,\" your reservation information will be sent to the restaurant for you. Just arrive at the restaurant on time for your reservation, make sure your server knows you made the reservation with Groupon Reserve, and at the end of the meal your bill will show the Reserve discount. We recommend printing your\u00a0confirmation\u00a0and\u00a0having it handy, just in case.",
      "question": "Do I need to call to confirm the restaurant reservation I made using Groupon Reserve?", 
      "id": "groupon_202", 
      "queries": [
        "Should I inform the restaurant of my reservation time in advance?", 
        "Who do I call in order to secure my reservation?", 
        "What is the procedure for reservation verification with groupon reserve?", 
        "Should I call to confirm our reservation?", 
        "Who do I contact to make sure my reservation got through?"
      ]
    }, 
    {
      "answer": "Absolutely not! You simply receive a discount on your bill when you've finished your meal.",
      "question": "Is there a fee for using Reserve to book a restaurant reservation?", 
      "id": "groupon_200", 
      "queries": [
        "Will I be charged for booking a reservation through groupon?", 
        "I won't get additional charges for making the reservation, right?", 
        "Do you charge extra for making reservations right on Groupon Reserve?", 
        "Do I have to pay in full before presenting the Groupon at the restaurant?", 
        "Will the restaurant charge me in advance for a reservation?"
      ]
    }, 
    {
      "answer": "After purchasing certain products from Groupon merchants through Groupon Goods or another Groupon platform, you may receive a unique, time-limited, alphanumeric code (\u0093redemption code\u0094) listed on your voucher. You'll redeem your code through the merchant's site to receive your purchased goods by following the instructions under \u0093How to use this,\u0094 printed on your Groupon.",
      "question": "What are redemption codes and how do they work?", 
      "id": "groupon_206", 
      "queries": [
        "How do I redeem a redemption code?", 
        "Do I always receive a redemption code when I purchase through Groupon Goods?", 
        "What are the codes I received and how do I use them?", 
        "Can you explain the procedure for redeeming?", 
        "Where can I find rules for how to use the redemption codes?"
      ]
    }
]


class FAQTest(RestCase):

    def _check_doc_info_counts(self):
        doc_info = FAQDocumentInfo.objects.get(channel=self.channel)
        self.assertDictEqual(doc_info.stemmer, {u'a': u'a', u'code': u'code', u'discounted': u'discount',
                                                u'alcohol': u'alcohol', u'restaurant': u'restaurant', u'there': u'the',
                                                u'groupon': u'groupon', u'to': u'to', u'codes': u'code',
                                                u'call': u'call', u'they': u'the', u'need': u'need',
                                                u'reservation': u'reservation', u'the': u'the', u'made': u'made',
                                                u'discount': u'discount', u'reserve': u'reserve'})
        self.assertDictEqual(doc_info.query_df, {u'and': 1, u'code': 1, u'is': 2, u'groupon': 1, u'are': 1, u'using': 3,
                                                 u'need': 1, u'what': 1, u'fee': 1, u'alcohol': 1, u'for': 1,
                                                 u'confirm': 1, u'make': 1, u'when': 1, u'to': 2, u'book': 1,
                                                 u'call': 1, u'?': 4, u'restaurant': 2, u'do': 2, u'how': 1,
                                                 u'reservation': 3, u'a': 2, u'made': 1, u'redemption': 1,
                                                 u'discount': 1, u'i': 2, u'work': 1, u'the': 3, u'reserve': 3})
        self.assertDictEqual(doc_info.answer_df, {u'a': 1, u'made': 1, u'alcohol': 1, u'restaurant': 1, u'groupon': 1,
                                                  u'discount': 2, u'code': 2, u'call': 1, u'need': 1, u'reservation': 1,
                                                  u'the': 4, u'to': 1, u'reserve': 2})
        self.assertEqual(doc_info.query_count, 24)

    def _index_refresh(self):
        FAQ.es_collection.index.refresh()
        time.sleep(0.1)

    def _search(self, happy_flow_data):
        # self._index_refresh()
        resp = self.client.post('/api/v2.0/faq/search',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        return post_data['list']

    def test_faq_data_search(self):
        """ Just test basic functionality on a db level. API 
        requests will go through more extensive functionality """
        all_entries = FAQ.objects.text_search(channel=self.channel, search_text="")
        self.assertEqual(len(all_entries), 0)

        entries = []
        for faq in FAQ_DATA:
            entry = FAQ.objects.create_by_user(self.user,
                                               channel=self.channel,
                                               question=faq['question'],
                                               answer=faq['answer'],
                                               queries=faq['queries'])
            entries.append(entry)

        self._check_doc_info_counts()

        all_entries = FAQ.objects.text_search(self.channel, "")

        self.assertEqual(len(all_entries), 4)

        seo = DbBasedSE1(self.channel)
        search_result = FAQ.objects.text_search(self.channel, "How do I redeem a redemption code?")
        self.assertEqual(str(search_result[0]['id']), str(entries[3].id))

        all_should_match = "Can I call for a discount on groupon or to make some reservation?"
        search_result = FAQ.objects.text_search(channel=self.channel, search_text=all_should_match)
        self.assertEqual(len(search_result), 4)

    def test_api_version(self):
        """
        Test FAQ interaction through the API.

        TODO: [ml] this one fails randomly
        nosetests test_facet_queries_utils.py test_faq_data.py
        """
        # Clear any ES data
        self.assertEqual(FAQQueryEvent.objects.count(), 0)
        token = self.get_token()
        self.channel = FAQChannel.objects.create(title="FAQ Chanel")
        happy_flow_data = {
            'channel': str(self.channel.id),
            'token': token
        }
        # Just load up existing data
        for faq in FAQ_DATA:
            happy_flow_data['question'] = faq['question']
            happy_flow_data['answer'] = faq['answer']
            happy_flow_data['queries'] = faq['queries']
            resp = self.client.post('/api/v2.0/faq',
                                    data=json.dumps(happy_flow_data),
                                    content_type='application/json',
                                    base_url='https://localhost')
            self.assertEqual(resp.status_code, 200)
            post_data = json.loads(resp.data)
            self.assertTrue(post_data['ok'])
        # Check that the counts in db match
        self._check_doc_info_counts()
        # Check that we have 4 available entries in ES
        all_entries = FAQ.objects.text_search(self.channel, "")
        self.assertEqual(len(all_entries), 4)
        # Just do a search for one of the queries that would match only it's answer
        # seo = DbBasedSE1(self.channel)
        # search_result = seo.search("How do I redeem a redemption code?", limit=10)
        # self.assertEqual(len(search_result), 1)
        # Now create a query that based on the topics should be a partial match to all FAQ's
        all_should_match = "Can I call for a discount on groupon or to make some reservation?"
        # search_result = seo.search(all_should_match, limit=10)
        # self.assertEqual(len(search_result), 4)
        # Search the same thing from the API, results should be the same
        happy_flow_data = {
            'channel': str(self.channel.id),
            'token': token,
            'query': all_should_match
        }
        result_list = self._search(happy_flow_data)
        self.assertEqual(len(result_list), 4)
        # Update one of the entries to test PUT request
        best_match = result_list[0]
        happy_flow_data = {
            'id': best_match['id'],
            'token': token,
            'question': best_match['question'] + ' UPDATED',
            'answer': best_match['answer'] + ' UPDATED'
        }
        resp = self.client.put('/api/v2.0/faq',
                               data=json.dumps(happy_flow_data),
                               content_type='application/json',
                               base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        # Re-run the same query, check that we get the updated FAQ
        happy_flow_data = {
            'channel': str(self.channel.id),
            'token': token,
            'query': all_should_match
        }
        result_list = self._search(happy_flow_data)
        new_best_match = result_list[0]
        self.assertEqual(best_match['id'], new_best_match['id'])
        self.assertEqual(best_match['question'] + ' UPDATED', new_best_match['question'])
        self.assertEqual(best_match['answer'] + ' UPDATED', new_best_match['answer'])
        # Do a train now using the query we've been searching for. We expect relevance to increase.
        happy_flow_data = {
            'token': token,
            'faq_id': best_match['id'],
            'query': all_should_match,
            'value': 1
        }
        resp = self.client.post('/api/v2.0/faq/train',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])
        # Re-run seach
        happy_flow_data = {
            'channel': str(self.channel.id),
            'token': token,
            'query': all_should_match
        }
        result_list = self._search(happy_flow_data)
        new_best_match = result_list[0]
        # Relevance should be increased and new query should be in FAQ feedback
        self.assertTrue(
            new_best_match['relevance'] > best_match['relevance'], '%s > %s' % (
                new_best_match['relevance'],
                best_match['relevance']))
        
        faq = FAQ.objects.get(new_best_match['id'])
        for entry in faq.feedback:
            if entry['query'] == all_should_match and entry['is_relevant'] == 1:
                break
        else:
            self.fail("%s was not found in feedback %s" % (all_should_match, faq.feedback))
        # Delete the best match then re-run the search, should get only 3 entries
        happy_flow_data = {
            'id': best_match['id'],
            'token': token,
        }
        resp = self.client.delete('/api/v2.0/faq',
                                  data=json.dumps(happy_flow_data),
                                  content_type='application/json',
                                  base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        happy_flow_data = {
            'channel': str(self.channel.id),
            'token': token,
            'query': all_should_match
        }
        result_list = self._search(happy_flow_data)
        self.assertEqual(len(result_list), 3)

        # Create a FAQ for some other channel that should be a perfect match, check that we channel filter properly
        other_channel = Channel.objects.create_by_user(self.user, title='Some other channel')
        doc_info_before = FAQDocumentInfo.objects.get(channel=self.channel)
        FAQ.objects.create_by_user(self.user,
                                   channel=other_channel,
                                   question=all_should_match,
                                   answer=all_should_match,
                                   queries=all_should_match)
        doc_info_after = FAQDocumentInfo.objects.get(channel=self.channel)
        self.assertDictEqual(doc_info_before.stemmer, doc_info_after.stemmer)
        self.assertDictEqual(doc_info_before.query_df, doc_info_after.query_df)
        self.assertDictEqual(doc_info_before.answer_df, doc_info_after.answer_df)
        self.assertEqual(doc_info_before.query_count, doc_info_after.query_count)
        new_result_list = self._search(happy_flow_data)
        self.assertEqual(len(new_result_list), 3)
        self.assertEqual([res['answer'] for res in new_result_list],
                         [res['answer'] for res in result_list])

        # Now do a search for the other channel
        happy_flow_data['channel'] = str(other_channel.id)
        new_result_list = self._search(happy_flow_data)
        self.assertEqual(len(new_result_list), 1)
        self.assertEqual(new_result_list[0]['answer'], all_should_match)
        self.assertEqual(FAQQueryEvent.objects.count(), 6)

    def test_faq_telecom_data(self):
        self.assertEqual(FAQQueryEvent.objects.count(), 0)
        self.channel = FAQChannel.objects.create(title="FAQ Chanel")
        token = self.get_token()
        # Just load up existing data
        happy_flow_data = {
            'channel': str(self.channel.id),
            'token': token
        }

        for faq in TELECOM_DATA['docs']:
            happy_flow_data['question'] = faq['question']
            happy_flow_data['answer'] = faq['answer']
            happy_flow_data['queries'] = faq['queries']
            resp = self.client.post('/api/v2.0/faq',
                                    data=json.dumps(happy_flow_data),
                                    content_type='application/json',
                                    base_url='https://localhost')
            self.assertEqual(resp.status_code, 200)
            post_data = json.loads(resp.data)
            self.assertTrue(post_data['ok'])

        # Check that we have 4 available entries in ES
        all_entries = FAQ.objects.text_search(self.channel, "")
        self.assertEqual(len(all_entries), 22)
        # Just do a search for one of the queries that would match only it's answer
        # seo = DbBasedSE1(self.channel)
        match_question = "I want a new bundle for my phone, which one is the best?"
        # search_result = seo.search(match_question, limit=10)
        # self.assertEqual(len(search_result), 10)
        # Search the same thing from the API, results should be the same
        happy_flow_data = {
            'channel': str(self.channel.id),
            'token': token,
            'query': match_question
        }
        result_list = self._search(happy_flow_data)
        # import ipdb; ipdb.set_trace()
        self.assertTrue(len(result_list)>0)

        relevancy_list = [r['relevance'] for r in result_list]
        best_match, worst_match = result_list[0], result_list[-1]
        happy_flow_data = {
            'token': token,
            'faq_id': best_match['id'],
            'query': match_question,
            'value': 1
        }
        resp = self.client.post('/api/v2.0/faq/train',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])

        happy_flow_data = {
            'token': token,
            'faq_id': worst_match['id'],
            'query': match_question,
            'value': 0
        }
        resp = self.client.post('/api/v2.0/faq/train',
                                data=json.dumps(happy_flow_data),
                                content_type='application/json',
                                base_url='https://localhost')
        self.assertEqual(resp.status_code, 200)
        post_data = json.loads(resp.data)
        self.assertTrue(post_data['ok'])

        happy_flow_data = {
            'channel': str(self.channel.id),
            'token': token,
            'query': match_question
        }
        result_list = self._search(happy_flow_data)
        self.assertTrue(len(result_list)>0)
        new_relevancy_list = [r['relevance'] for r in result_list]

        self.assertTrue(relevancy_list[0] < new_relevancy_list[0])
        self.assertTrue(relevancy_list[-1] > new_relevancy_list[-1])

