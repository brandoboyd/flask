'''
Defines the state update model for a conversation

'''
from datetime import datetime as dt
from operator import xor
import numpy as np
import re

from solariat_nlp.utils import inversed_dict
from solariat_nlp.sentiment import extract_sentiment
from solariat_bottle.db.conversation_trends import ConversationQualityTrends

from solariat.utils import timeslot
from ..db.channel.base import Channel
from solariat.db.abstract import fields, Document, SonDocument
from solariat_nlp.sa_labels import (
    ASKS, NEEDS, RECOMMENDATION, LIKES, PROBLEM, 
    APOLOGY, GRATITUDE, HELP, CHECKIN, JUNK, ALL_INTENTIONS,
    SATYPE_ID_TO_NAME_MAP
)
from ..db.speech_act   import SpeechActMap as sam

from inspect                import isfunction

'''
Conversations have discrete status. These would be used for
prioritization purposes potentially. They would also be used
as part of the state vector for a conversation, and for eventual scoring.
'''

INITIAL   = 0 # Some Default Value. May be unnecessary
REJECTED  = 1 # If the initial post is rejected, the conversation will be too
WAITING   = 3 # The contact has not been replied to at all.
ENGAGED   = 4 # The brand has engaged the initial post, initiative with the contact
HOLDING   = 5 # The contact is waiting on the brand, but the brand had engaged at least once.
DROPPED   = 6 # The conversation had begun, but the brand left the contact hanging.
MISSED    = 7 # The brand never engaged, after timeout
COMPLETED = 8 # Successful termination


STATUS_MAP = {
    "initial"   : INITIAL,
    "rejected"  : REJECTED,
    "waiting"   : WAITING,
    "engaged"   : ENGAGED,
    "holding"   : HOLDING,
    "dropped"   : DROPPED,
    "missed"    : MISSED,
    "completed" : COMPLETED,
}

STATUS_LABELS = inversed_dict(STATUS_MAP)

# All the final statuses for a conversation.
TERMINAL_STATUSES = [DROPPED, MISSED, COMPLETED, REJECTED]

COMPLETION_MAP = {
    WAITING  : MISSED,
    ENGAGED  : COMPLETED,
    HOLDING  : DROPPED,
}

# A time stamp indicator for NEVER happened
NEVER = timeslot.UNIX_EPOCH

# Speakers
BRAND     = 'brand'
CONTACT   = 'contact'


class StateVector(SonDocument):
    time_stamp = fields.DateTimeField(db_field='ts', required=True)

    # Discrete status value from Conversation Model
    status     = fields.NumField(db_field='ss', required=True)

    # The resulting estimate of satisfaction of the contact. Want this to be improving!
    satisfaction  = fields.NumField(db_field='se', default=0.0)

    ###### Features of Interest ###########################################
    # These can be expanded as needed. Idea is that we will track the state
    # elements that help discriminate reasonable score updates with each event

    # Contact Stats.
    contact_post_count_total = fields.NumField(db_field='ct', default=0)
    contact_post_count_last  = fields.NumField(db_field='cl', default=0)
    contact_post_ts          = fields.DateTimeField(db_field='cs', default=NEVER)

    # Brand Stats
    brand_post_count_total   = fields.NumField(db_field='bt', default=0)
    brand_post_count_last    = fields.NumField(db_field='bl', default=0)
    brand_post_ts            = fields.DateTimeField(db_field='ls', default=NEVER)
    intentions               = fields.ListField(fields.NumField(), db_field='in', default=[])
    speaker                  = fields.StringField(db_field='s', default=None)

    # The direction of the last post
    direction                = fields.StringField(db_field='d', default="UNNOWN") 

    @property
    def key(self):
        ''' The key is based only on time. They should be unique in a conversation. '''
        return "%d:%d:%d:%d:%d" % (
            self.time_stamp.year,
            self.time_stamp.month,
            self.time_stamp.day,
            self.time_stamp.hour,
            self.time_stamp.second)

    @property
    def next_speaker(self):
        ''' Prediction for next speaker '''
        assert self.status not in TERMINAL_STATUSES

        if self.status in [WAITING, HOLDING]:
            return BRAND

        return CONTACT

    def __str__(self):
        return "%d:%s" % (
            self.status,
            self.key)

    def __eq__(self, other):
        if other and isinstance(other, StateVector):
            '''
            Had to resort to this string based comparison because the
            date time check was failing for reasons I got fed up trying
            to figure out!
            '''
            return self.key == other.key

        return False

    def is_valid(self):
        '''
        Validation criteria for the state vector. Can add to this...
        '''
        # It is not a valid state if it is in the initial category. This is because
        # we will only be creating a conversation with a post, and we should always
        # be able to determine one of the alternate states based on that.
        if self.status == INITIAL:
            return False

        return xor(self.brand_post_count_last == 0 and self.contact_post_count_last == 0,
                   xor(self.brand_post_count_last > 0, self.contact_post_count_last > 0))

    @classmethod
    def default(cls, status=INITIAL):
        return cls(status=status, time_stamp=timeslot.now())

    def get_intention_key(self):
        if self.status in TERMINAL_STATUSES:
            key = "TERMINATED"
        elif self.intentions:
            key = tuple(SATYPE_ID_TO_NAME_MAP[str(x)] for x in self.intentions)
            key = " ".join(key)
            key = "%s:%s:%s:%s" % (self.direction, self.speaker, key, STATUS_LABELS[self.status])
            key = key.upper()
        else:
            key = ""
        return key

def make_post_vector(post, sc):
    '''
    This is a simple version. As we refine the model to exploit other features we
    can do better.
    '''
    pv = post.to_dict()
    pv['created'] = post.created
    # Speaker
    pv['speaker'] = CONTACT if post.is_inbound else BRAND

    # Post Status
    if pv['speaker'] == BRAND:
        pv['actionable'] = False
    else:
        pv['actionable'] = sam.STATUS_MAP[post.get_assignment(sc.inbound_channel)] \
            in [sam.ACTIONABLE, sam.ACTUAL]

    pv['post_content'] = post.plaintext_content
    pv['direction'] = sc.find_direction(post)
    return pv

class Policy(object):
    ''' Encodes the policy details for the conversation model '''

    no_of_days = 1    

    def should_be_terminated(self, current_state, time_stamp):
        '''
        Test if this conversation should be terminated. This is
        typically going to just be a time out. For now will use
        a 24 hour day. But in reality, if it matters to anyone, we can
        accomodate business hours, and even conside the current state
        of the conversation, last post etc. to draw conversations to a
        close more quickly
        '''
        assert time_stamp >= current_state.time_stamp, "We should not be looking historically"
        elapsed_time = time_stamp - current_state.time_stamp
        return elapsed_time.days >= self.no_of_days

    def get_final_state(self, current_state, time_stamp):
        ''' For now we can ignore the time stamp '''
        assert current_state.status in COMPLETION_MAP, \
            'Must have missed a transition: %s' % STATUS_LABELS[current_state.status]
        return StateVector(status=COMPLETION_MAP[current_state.status], time_stamp=time_stamp)

    def update_state_with_post(self, current_state, post_vector):
        ''' The main update logic for a new post in the conversation. '''

        # Initialize the new state
        new_state = StateVector(status=current_state.status, time_stamp=post_vector['created'])
        if post_vector['speaker'] == BRAND:
            # Reset contact counts that are not defaults
            new_state.contact_post_count_total = current_state.contact_post_count_total
            new_state.contact_post_ts          = current_state.contact_post_ts

            # Set counts for brand
            new_state.brand_post_count_total   += 1
            new_state.brand_post_count_last    += 1
            new_state.brand_post_ts            =  new_state.time_stamp

            # Set the status
            new_state.status                   = ENGAGED
        else:
            # Reset brand counts that are not defaults
            new_state.brand_post_count_total = current_state.contact_post_count_total
            new_state.brand_post_ts          = current_state.contact_post_ts

            # Set counts for brand
            new_state.brand_post_count_total   += 1
            new_state.brand_post_count_last    += 1
            new_state.brand_post_ts            =  new_state.time_stamp

            # Set the status
            if post_vector['actionable'] and current_state.status in [ENGAGED, HOLDING]:
                new_state.status = HOLDING
            else:
                new_state.status = WAITING

        new_state.intentions = [int(sa["intention_type_id"]) for sa in post_vector["speech_acts"]]
        new_state.speaker    = post_vector['speaker']
        new_state.direction  = post_vector['direction']
        new_state.satisfaction  = self.calc_satisfaction(current_state,
                                                  new_state,
                                                  post_vector)
        return new_state

    def calc_satisfaction(self, csm, new_state, post_vector):
        '''
        Here lies the meat of any policy. Need a baseline implemnetation
        of this.
        '''
        return csm.state.satisfaction

    def calc_score(self, state_history):
        '''
        Computes the score for the conversation based on the state history. The
        resulting number is in the range [1, 5]. Think of a 5 star rating system.
        '''
        return 0.0


# PARAMS for Weighting expections of Contact

WORST     = -1.0
TERRIBLE  = -0.75
BAD       = -0.5
NEGATIVE  = -0.1
EXPECTING = -0.1
NEUTRAL   =  0.0
POSITIVE  =  0.25
GOOD      =  0.5
GREAT     =  0.75
BEST      =  0.9

URGENT_RESPONSE_REQUIRED = -1.0
RESPONSE_REQUIRED        = -0.5
RESPONSE_DESIRED         =  0.5
CONTACT_ANSWERED         =  1.0


SENTIMENT =  lambda ps, cs: ps

RULES = (

        # Initial Conditions
        (("", "DIRECT:CONTACT:.*(ASKS|NEEDS|PROBLEM).*"),      URGENT_RESPONSE_REQUIRED),
        (("", "MENTIONED:CONTACT:.*(PROBLEM).*"),   URGENT_RESPONSE_REQUIRED),
        (("", "MENTIONED:CONTACT:.*(ASKS|NEEDS).*"),   RESPONSE_REQUIRED),
        (("", "(DIRECT|MENTIONED):CONTACT:.*(APOLOGY|RECOMMENDATION).*"),       RESPONSE_REQUIRED),
        (("", "(DIRECT|MENTIONED):CONTACT:.*(APOLOGY|RECOMMENDATION).*"),       RESPONSE_REQUIRED),
        (("", "(DIRECT|MENTIONED):CONTACT:.*(LIKES).*"),    RESPONSE_DESIRED),
        (("", ".*CONTACT.*"),               NEUTRAL),
        (("", ".*BRAND:.*"),                POSITIVE),

        # A grateful contact is always good
        ((".*ENGAGED",  ".*CONTACT:.*(GRATITUDE|LIKES).*"), GOOD),

        # If they get helped out by another contact, that is good also
        ((".*CONTACT:.*(RECOMMENDATION|OFFER).*",  ".*CONTACT:.*(GRATITUDE|LIKES).*"), GOOD),

        # Any issues by a contact are bad
        ((".*",  ".*CONTACT:.*(ASKS|NEEDS|PROBLEM).*"),  BAD),

        # General Contact / Contact Interaction
        ((".*CONTACT:.*(ASKS|NEEDS|PROBLEM).*",  ".*CONTACT:.*(RECOMMENDATION|OFFER).*"),  CONTACT_ANSWERED),
        ((".*CONTACT:.*",  ".*CONTACT:.*"), NEUTRAL),
        
        # BRAND RESPONSES

        # It is great for a brand to respond with a recommendation or offer of help when faced with an issue
        ((".*CONTACT:.*(PROBLEM).*", ".*BRAND:APOLOGY.*(RECOMMENDATION|OFFER|ASKS).*"), BEST),
        ((".*CONTACT:.*(PROBLEM).*", ".*BRAND:.*(RECOMMENDATION|OFFER|ASKS).*"), GREAT),
        ((".*CONTACT:.*(ASKS|NEEDS).*", ".*BRAND:.*(RECOMMENDATION|OFFER|ASKS).*"), GREAT),

        # Responding vacuously to an issue is not so hot
        ((".*CONTACT:.*(ASKS|NEEDS|PROBLEM).*", ".*BRAND:LIKES"), POSITIVE),
        ((".*CONTACT:.*(ASKS|NEEDS|PROBLEM).*", ".*BRAND:GRATITUDE"), POSITIVE),

        # Engaging in banter is also a great thing to show you are listening
        ((".*CONTACT:.*(LIKES|GRATITUDE).*", ".*BRAND:.*(GRATITUDE|GRATITUDE).*"), GREAT),

        # Defaults
        ((".*CONTACT:.*",  ".*BRAND:.*"), GOOD),
        ((".*BRAND:.*",    ".*BRAND:.*"), POSITIVE),
        
        # Termination
        # If the brand is left hanging after reaching out, it is bad
        ((".*BRAND:.*(ASKS).*", "TERMINATED"), BAD),
        ((".*BRAND:.*(OFFER).*", "TERMINATED"), BAD),
        ((".*BRAND:.*(APOLOGY).*", "TERMINATED"), NEGATIVE),

        (("(MENTIONED|DIRECT).*CONTACT:.*LIKES.*WAITING", "TERMINATED"), NEUTRAL),
        (("(MENTIONED|DIRECT).*CONTACT:.*WAITING", "TERMINATED"), BAD),
        ((".*CONTACT:.*(LIKES|GRATITUDE).*:ENGAGED", "TERMINATED"), GREAT),
        ((".*CONTACT:.*(PROBLEM).*:ENGAGED", "TERMINATED"), BAD),
 
        # Default Handling
        (("",        ".*"), NEUTRAL),
        ((".*",      ".*"), NEUTRAL),
        )


# Impacts
def NEGATIVE_IMPACT  (impact): return impact < 0
def LOW_IMPACT       (impact): return 0 <= impact <= 0.25
def MEDIUM_IMPACT    (impact): return 0.25 < impact < 1.0
def HUGE_IMPACT      (impact): return impact >= 1

# Outcomes
def TERRIBLE_OUTCOME (outcome): return outcome < -0.5
def BAD_OUTCOME      (outcome): return -0.5 <= outcome < 0
def POSITIVE_OUTCOME (outcome): return 0 <= outcome <= 0.25
def GOOD_OUTCOME     (outcome): return 0.25 < outcome <= 0.75
def GREAT_OUTCOME    (outcome): return outcome > 0.75

# Catch All
def OTHERWISE        (outcome): return True

SCORING_MATRIX = [
    [NEGATIVE_IMPACT, [ (TERRIBLE_OUTCOME, 1), (BAD_OUTCOME, 1), (OTHERWISE, 2) ]],
    [LOW_IMPACT,      [ (TERRIBLE_OUTCOME, 1), (BAD_OUTCOME, 2), (POSITIVE_OUTCOME, 3),  (GOOD_OUTCOME, 3), (GREAT_OUTCOME, 4)]],
    [MEDIUM_IMPACT,   [ (TERRIBLE_OUTCOME, 2), (BAD_OUTCOME, 2), (POSITIVE_OUTCOME, 3),  (GOOD_OUTCOME, 4), (GREAT_OUTCOME, 4)]],
    [HUGE_IMPACT,     [ (POSITIVE_OUTCOME, 4), (GOOD_OUTCOME, 4), (GREAT_OUTCOME, 5)]],
    ]

class SimplePolicy(Policy):

    # possible intentions for rule creation:
    # recommendation, offer, junk, asks, all, problem, 
    # needs, discarded, likes, checkins, apology, gratitude

    RULES = RULES
    RULES_STATS = [list(i) for i in zip([x[0] for x in RULES], [0]*len(RULES))]

    def __init__(self, *args, **kwargs):
        super(SimplePolicy, self).__init__(*args, **kwargs)

    @classmethod
    def reset_rules_stats(cls):
        cls.RULES_STATS = [[k, 0] for k, v in cls.RULES_STATS]


    def _get_post_intention_key(self, post_vector):
        post_key       = " ".join((SATYPE_ID_TO_NAME_MAP[x["intention_type_id"]] for x in post_vector["speech_acts"]))
        post_key       = "%s:%s:%s" % (post_vector['direction'], post_vector["speaker"], post_key)
        post_key       = post_key.upper()
        return post_key

    def _get_impact_coef(self, rule_key, post_sentiment, current_state):
        impact            = dict(self.RULES)[rule_key]
        impact_coef       = None
        if isfunction(impact) and post_sentiment is not None and current_state is not None:
            impact_coef = impact(post_sentiment, current_state)
        elif isinstance(impact, (int, float)):
            impact_coef = impact
        else:
            raise Exception("unexpected impact type %s %s" % (impact, type(impact)))
        return impact_coef


    def calc_satisfaction(self, current_state, new_state, post_vector):
        post_sentiment    = extract_sentiment(post_vector["content"])
        post_sentiment    = post_sentiment["sentiment"].weight*post_sentiment["score"]
        # post_sentiment    = post_sentiment[0].weight*post_sentiment[1]
        post_key          = self._get_post_intention_key(post_vector)
        current_state_key = current_state.get_intention_key()    
        print "----------------------------------------------------"
        print "--> %-30s: %s" % ("actual post",   post_vector["post_content"])
        key               = self._get_lookup_table_key(current_state_key, post_key)
        impact_coef       = self._get_impact_coef(key, post_sentiment, current_state)
        delta             = abs(np.copysign(1, impact_coef) - current_state.satisfaction)
        satisfaction      = current_state.satisfaction + delta * impact_coef

        self._update_key_counter(key)

        print "--> %-30s: %s" % ("post_speaker",   post_vector["speaker"])
        print "--> %-30s: %s" % ("lookup_key",     str(key))
        print "--> %-30s: %s" % ("impact_coef",    impact_coef)
        print "--> %-30s: %s" % ("impact",         satisfaction - current_state.satisfaction)
        print "--> %-30s: %s" % ("post_sentiment", post_sentiment)
        print "--> %-30s: %s" % ("old_satisfaction",  current_state.satisfaction)
        print "--> %-30s: %s" % ("new_satisfaction",  satisfaction)

        return satisfaction

    def calc_final_satisfaction(self, current_state, new_state):
        key = self._get_lookup_table_key(
            current_state.get_intention_key(),
            new_state.get_intention_key()
        )
        impact_coef = self._get_impact_coef(
            key, 
            post_sentiment=None, 
            current_state=current_state
        )
        delta        = abs(np.copysign(1, impact_coef) - current_state.satisfaction)
        satisfaction = current_state.satisfaction + delta * impact_coef
        self._update_key_counter(key)
        print "--> %-30s: %s" % ("impact_coef",    impact_coef)
        print "--> %-30s: %s" % ("impact",         satisfaction - current_state.satisfaction)
        print "--> %-30s: %s" % ("lookup_key",     str(key))
        print "--> %-30s: %s" % ("old_satisfaction",  current_state.satisfaction)
        print "--> %-30s: %s" % ("new_satisfaction",  satisfaction)
        return satisfaction

    def _update_key_counter(self, key):
        for i, (rule, value) in enumerate(SimplePolicy.RULES_STATS):
            if rule == key:
                SimplePolicy.RULES_STATS[i][1] += 1
                break

    def _get_lookup_table_key(self, current_state_key, new_state_key):
        print "--> %-30s: %s" % ("current_state_key", current_state_key)
        print "--> %-30s: %s" % ("new_state_key",     new_state_key)
        key = None
        for rule_key, value in self.RULES:
            if (re.compile("^%s$" % rule_key[0]).match(current_state_key) 
                and re.compile("^%s$" % rule_key[1]).match(new_state_key)
            ):
                key = rule_key
                break
        assert key is not None, (current_state_key, new_state_key)
        return key

    def _calc_exact_score(self, state_history):
        ''' Final scoring considers:
         * The initial state of the contact
         * The final state of the contact
         * The improvement in that state
        '''
        final_value   = state_history[-1].satisfaction
        return final_value
        initial_value = state_history[1].satisfaction
        delta         =  final_value - initial_value

        print "Initial", initial_value
        print "Final  ", final_value
        print "Delta  ", delta

        # The score is a weighted sum of impact and outcome, scaled
        # in the range [1, 4]. This is simpler than a scoring matrix, though
        # not as fun to implement :-)
        w1 = (delta + 2.0) / 4
        w2 = (final_value + 1.0) /2
        score = 1 + (0.25 * w1 + 0.75*w2) * 4
        return score

        for row in SCORING_MATRIX:
            if row[0](delta):
                for col in row[1]:
                    if col[0](final_value):
                        print "HIT WITH (%s, %s)" % (row[0].__name__, col[0].__name__)
                        return col[1]

        assert False, "Scoring Matrix is incomplete for (%.2f, %.2f)" % (delta, final_value)

    def calc_scores(self, state_history):
        result = {}
        result["quality_score"]      = self._calc_exact_score(state_history)
        result["quality_score_rounded"] = int(round(result["quality_score"]))
        result["quality_star_score"] = self._calc_quality_star_score(state_history)
        result["quality_label"]      = self._calc_quality_label(result["quality_score"])
        result["customer_satisfaction"] = self._calc_customer_satisfaction(state_history)

        return result

    def _calc_customer_satisfaction(self, state_history):
        i = -1
        last_customer_state = state_history[i]
        while last_customer_state.speaker != 'contact':
            i = i - 1
            last_customer_state = state_history[i]
        return min(last_customer_state.satisfaction, state_history[-1].satisfaction)

    def _calc_quality_star_score(self, state_history):
        final_value   = state_history[-1].satisfaction
        initial_value = state_history[1].satisfaction
        delta         = final_value - initial_value
        if delta < 0:
            delta = 0
        # The score is a weighted sum of impact and outcome, scaled
        # in the range [1, 4]. This is simpler than a scoring matrix, though
        # not as fun to implement :-)
        w1 = (delta + 2.0) / 4
        w1 = np.sign(delta) * w1
        w2 = (final_value + 1.0) /2
        score = 1 + (0.25 * w1 + 0.75*w2) * 4
        return int(round(score))

    def _calc_quality_label(self, quality_score):
        return ConversationQualityTrends.CATEGORY_MAP_INVERSE[int(quality_score)+1]

    def get_final_state(self, current_state, time_stamp):
        state = super(SimplePolicy, self).get_final_state(current_state, time_stamp)
        state.satisfaction = current_state.satisfaction
        return state

# A Map for binding policies to state machines if we want to plug in variants.
POLICY_MAP = {}

class ConversationStateMachine(Document):
    '''
    The conversation state machine integrates the logic for modeling dialogs
    and assessing call quality. The basic idea is that it captures a sequence
    of state changes.
    '''

    ''' Primitives for state handling '''
    def _get_state(self):
        if self.state_history == []:
            return StateVector.default()
        return self.state_history[-1]

    def _set_state(self, state_vector):
        assert state_vector.is_valid(), state_vector.status
        self.state_history.append(state_vector)

    channel           = fields.ReferenceField(Channel, db_field='cl', required=False)
    state_history     = fields.ListField(fields.EmbeddedDocumentField(StateVector), db_field='h')
    policy_name       = fields.StringField(db_field='py', default="DEFAULT")
    state             = property(_get_state, _set_state)
    quality_score     = fields.NumField(db_field='qy', default=0.0)

    @property
    def policy(self):
        return POLICY_MAP.get(self.policy_name, SimplePolicy())

    @property
    def terminated(self):
        return self.state.status in TERMINAL_STATUSES

    @property
    def next_speaker(self):
        ''' Prediction of who should speak next '''
        return self.state.next_speaker

    def handle_clock_tick(self, time_stamp=None):
        '''
        Clock tick events sent to govern termination of in-progress
        conversations
        '''
        if time_stamp == None:
            time_stamp = dt.now()
        # time_stamp = timeslot.utc(time_stamp)

        # If terminated there is nothing to do
        if self.terminated: 
            return

        # Should be later than the last state update
        assert time_stamp >= self.state.time_stamp

        # If we can terminate, do so. Termination will change the state. But
        # we will ignore it if it does not impact termination. In the future we
        # could change this to update the state incrementally and trigger
        # an alert of some kind.
        if self.policy.should_be_terminated(self.state, time_stamp) == True:
            current_state           = self.state
            new_state               = self.policy.get_final_state(self.state, time_stamp)
            new_state.satisfaction  = self.policy.calc_final_satisfaction(current_state, new_state)
            self.state              = new_state
            result                  = self.policy.calc_scores(self.state_history)
            self.quality_score      = result["quality_score"]
            self.quality_score_rounded = result["quality_score_rounded"]
            self.quality_star_score = result["quality_star_score"]
            self.quality_label      = result["quality_label"]
            self.customer_satisfaction = result["customer_satisfaction"]

    def handle_post(self, post=None, vector=None):
        if post:
            s = "HANDLE POST: %s" % post.content
            print s.encode("utf-8")
        vector = make_post_vector(post, self.channel) if post else vector
        self.state = self.policy.update_state_with_post(self.state, vector)
        # self.save()

    def save(self, **kw):
        assert False, "Lets try to apply CSM without saving CSM entities to mongodb"
        assert self.state_history != [], "Must have a state"
        assert self.state.status != INITIAL
        super(ConversationStateMachine, self).save(**kw)

    def handle_conversation(self, conversation, time_stamp=None):
        for post in conversation.query_posts():
            self.handle_post(post)
        self.handle_clock_tick(time_stamp=time_stamp)

    def get_conversation_quality(self, conversation, time_stamp=None):
        self.handle_conversation(conversation, time_stamp)
        return self.get_quality_label()

    def get_quality_label(self):
        """ At this point we know the conversation score (in range [-1, 1]),
        this function should map the score to verbose value
        """
        assert self.terminated
        return ConversationQualityTrends.CATEGORY_MAP_INVERSE[int(self.quality_score)+1]



