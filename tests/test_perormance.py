from .base import MainCase
from solariat_nlp import extract_intentions
from datetime import datetime

class PostCase(MainCase):

    def test_speech_acts_creation(self):
        intentions = extract_intentions('I need a bike . I like Honda .')
        t = datetime.now()

        for i in range(0,100):
            intentions = extract_intentions('I need a bike . I like Honda . %d' % i)


        print "Finished in", datetime.now() - t


