"""Sending msg with user_tag to monitoring channel """

import unittest
from solariat_bottle.tests.base import RestCase
from solariat_bottle.db.channel.base import MonitoringChannel


@unittest.skip('we dont use api v1.2 anymore')
class UserTagCase(RestCase):

    def test_post(self):
        self.channel = MonitoringChannel.objects.create_by_user(
            self.user, type='monitoring', title='TestMe')

        resp = self.do_post('posts', version='v1.2',
                            **{
            "content": """RT @CollabNet: RT @thetasgroup: At Dreamforce we'll bepartying with @marketo @Zuora @XactlyCorp @insideview  @toatech
@CollabNet You're invited too!...""", 
            "speech_acts": [
                    {"content": """RT @CollabNet : RT @ thetasgroup : At Dreamforce we ' ll be partying with @marketo @ Zuora @ XactlyCorp @ insideview @ toatech @ CollabNet You' re invited too !...""", 
                     "intention_type_conf": 0.027061411331069096, 
                     "intention_type": "DISCARDED",
                     "intention_topic_conf": 0, 
                     "intention_topics": [],
                     "intention_type_id": "5"}],
            "user_tag": "ZuoraGeek",
            "channel": self.channel_id})
        self.assertTrue(resp['ok'], resp.get('error'))
