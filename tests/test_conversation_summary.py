import unittest
from datetime import datetime
from solariat_bottle.tests.slow.test_conversations import ConversationBaseCase
from solariat_nlp.conversations.topics import (
    extract_chat_topics, DEFAULT_FREQS, get_flags, DEFAULT_STOPWORDS)
from solariat_nlp.conversations.flags import RED_FLAGS

from solariat_bottle.data.telecom_chats1 import CHATS
from solariat_nlp.conversations.topics import get_topics_simple


def to_session(chat_sample):
    '''
    Converts to a session format based on sample input. This is just a utilitiy
    for parsing the samples, and can be ignored for integration.
    '''
    assert isinstance(chat_sample, dict)

    def parse_message(message):
        for prefix, actor in [("a: ", "Agent"), 
                              ("c: ", "Customer"),
                              ("system: ", "System")]:
            if message.find(prefix) == 0:
                return (actor, message[len(prefix):])

        
    messages = []
    for m in chat_sample['chat_data']:
        actor, message = parse_message(m)
        messages.append( (actor, message, str(datetime.now())) )

    return dict(messages=messages, 
                actors=list(set([ m[0] for m in messages])),
                stopwords=DEFAULT_STOPWORDS)


class ConversationTopicTest(ConversationBaseCase):

    def setUp(self):
        ConversationBaseCase.setUp(self)

    def test_telecom_data(self):
        ''' Topics on telecome chat sessions'''
        from solariat_bottle.data.telecom_chats1 import CHATS
        errors = []
        for session in CHATS:
            errors.extend(self._run_sample(session))

        if errors != []:
            for session_id, expected, actual in errors:   
                print "-------------------"
                print "SESSION ID", session_id
                print "EXPECTED:", expected
                print '"alternate":', actual
            self.assertFalse(True)

    def _run_sample(self, sample):
        EXPECTED = 'alternate'
        session = to_session(sample)
        scored_topics = get_topics_simple(session['messages'])
        topics = [t[0] for t in scored_topics]

        #print "S", scored_topics
        #print "T", topics

        if set(topics) - set(sample[EXPECTED]) != set([]):
            return [( sample['session'], sample[EXPECTED], topics )]
        return []
            
