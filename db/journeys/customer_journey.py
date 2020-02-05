import itertools
from copy import deepcopy
from bson import ObjectId

from solariat.db import fields
from solariat.db.fields import EventIdField
from solariat.db.abstract import SonDocument
from solariat.utils.parsers.base_parser import BaseParser

from solariat.utils.timeslot import utc
from solariat_bottle.db.events.event import Event, DynamicEvent
from solariat_bottle.db.auth import AuthDocument, AuthManager
from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType
from solariat_bottle.db.journeys.journey_stage import JourneyStage
from solariat_bottle.db.account import Account


PLATFORM_STRATEGY = 'By platform'
EVENT_STRATEGY = 'By event type'
STAGE_INDEX_SEPARATOR = '__'
# TODO: These are hardcoded, will need to think of a dynamic way of defining them
STRATEGY_DEFAULT = 'default'
STRATEGY_PLATFORM = 'platform'
STRATEGY_EVENT_TYPE = 'event_type'


def assert_eq(first, second, msg):
    assert first == second, msg


class EventSequenceStatsMixin(object):

    account_id = fields.ObjectIdField(db_field='aid')
    channels = fields.ListField(fields.ObjectIdField(), db_field='chs')
    stage_sequence_names = fields.ListField(fields.StringField(), db_field='sseqnm')
    status = fields.NumField(db_field='ss', choices=JourneyStageType.STATUSES, default=JourneyStageType.IN_PROGRESS)
    smart_tags = fields.ListField(fields.ObjectIdField(), db_field='sts')
    journey_tags = fields.ListField(fields.ObjectIdField(), db_field='jts')
    journey_type_id = fields.ObjectIdField(db_field='jt')
    journey_attributes = fields.DictField(db_field='jyas')

    def __get_journey_type(self):
        if hasattr(self, '_f_journey_type'):
            return self._f_journey_type
        else:
            self._f_journey_type = JourneyType.objects.get(self.journey_type_id)
            return self._f_journey_type

    def __set_journey_type(self, journey_type):
        self._f_journey_type = journey_type

    journey_type = property(__get_journey_type, __set_journey_type)

    @classmethod
    def translate_static_key_name(cls, key_name):
        # translate any static key, leave anything else the same
        if key_name == cls.status.db_field:
            return 'status'
        return key_name

    @classmethod
    def translate_static_key_value(cls, key_name, key_value):
        # translate any static key, leave anything else the same
        if key_name == cls.status.db_field:
            return JourneyStageType.STATUS_TEXT_MAP[key_value]
        return key_value

    @property
    def full_journey_attributes(self):
        # Dynamic defined plus any static defined attributes worth considering in facets or analysis
        from copy import deepcopy
        base_attributes = deepcopy(self.journey_attributes)
        base_attributes['status'] = self.status
        return base_attributes


    @property
    def account(self):
        # TODO Check this for performance. Should cache.
        return Account.objects.get(self.account_id)

        event_id = EventIdField().to_mongo(event_id)
        event_id = EventIdField().to_mongo(event_id)

class CustomerJourneyManager(AuthManager):

    def create(self, *args, **kwargs):
        jt = JourneyType.objects.get(kwargs['journey_type_id'])
        kwargs['journey_attributes_schema'] = jt.journey_attributes_schema
        return super(CustomerJourneyManager, self).create(*args, **kwargs)


class CustomerJourney(AuthDocument, EventSequenceStatsMixin):

    FEAT_TYPE = 'type'
    FEAT_LABEL = 'label'
    FEAT_EXPR = 'field_expr'
    FEAT_NAME = 'name'

    collection = "CustomerJourney"
    manager = CustomerJourneyManager

    stage_name = fields.StringField(db_field='fs')      # stage_name of current_stage

    # Dict in the form:
    # <strategy_type> : <list of index__stage_name>. strategy_type can be for now (default, platform, event_type)
    stage_sequences = fields.DictField(db_field='sseq')
    # Dict in the form
    # index__stage_name: {actual attributes computed for this specific stage}
    stage_information = fields.DictField(db_field='si')

    customer_id = fields.BaseField(db_field='ci')   # dynamic profiles may use custom id type
    customer_name = fields.StringField(db_field='cn')   # Just for quick access w/o extra db call

    agent_ids = fields.ListField(fields.ObjectIdField(), db_field='ag')
    agent_names = fields.ListField(fields.StringField(), db_field='ans')    # Just for quick access w/o extra db calls

    journey_tags = fields.ListField(fields.ObjectIdField(), db_field='jts')
    channels = fields.ListField(fields.ObjectIdField(), db_field='chls')

    last_updated = fields.DateTimeField(db_field='lu')

    # time spent by events in each stage-eventtype status
    node_sequence = fields.ListField(fields.DictField(), db_field='nds')
    node_sequence_agr = fields.ListField(fields.StringField(), db_field='ndsn')

    # time spent by events in each stage-eventtype status
    journey_attributes_schema = fields.ListField(fields.DictField(), db_field='jas')
    first_event_date = fields.DateTimeField(db_field='fed')
    last_event_date = fields.DateTimeField(db_field='led')

    indexes = [('journey_type_id', 'journey_tags'), ('journey_attributes', ),
               ('journey_type_id', 'channels'),
               ('customer_id',),
               ('agent_ids',)]

    parsers_cache = dict()

    @classmethod
    def to_mongo(cls, data, fill_defaults=True):
        """
        Same as super method, except parser.evaluate is skipped (would be called in process_event)
        """
        return super(CustomerJourney, cls).to_mongo(data, fill_defaults=fill_defaults, evaluate=False)

    @classmethod
    def metric_label(cls, metric, param, value):
        # from solariat_bottle.db.predictors.customer_segment import CustomerSegment
        if param == 'status':
            value = JourneyStageType.STATUS_TEXT_MAP[value]
        if param == 'journey_type_id':
            value = JourneyType.objects.get(value).display_name

        #value = value[0] if type(value) in [list, tuple] and value else value if value is not None else 'N/A'
        if value is None:
            value = 'N/A'

        return str(value)

    def ui_repr(self):
        base_repr = "Status: %s; Start date: %s; End date: %s;" % (self.status, self.first_event_date,
                                                                   self.last_event_date)
        if self.customer_name:
            base_repr += " Customer: %s;" % self.customer_name
        if self.agent_names:
            base_repr += " Agents: %s;" % self.agent_names
        return base_repr

    def to_dict(self, *args, **kwargs):
        # from solariat_bottle.db.predictors.customer_segment import CustomerSegment
        base_dict = super(CustomerJourney, self).to_dict()
        base_dict['agents'] = map(str, self.agents)
        base_dict['channels'] = map(str, self.channels)
        base_dict['smart_tags'] = map(str, self.smart_tags)
        base_dict['journey_tags'] = map(str, self.journey_tags)
        base_dict['status'] = JourneyStageType.STATUS_TEXT_MAP[self.status]
        base_dict['string_repr'] = self.ui_repr()
        base_dict['journey_attributes'] = self.journey_attributes

        return base_dict

    def handle_add_tag(self, tag_id):
        tag_id = ObjectId(tag_id)
        self.update(addToSet__smart_tags=tag_id)

    def handle_remove_tag(self, tag_id):
        tag_id = ObjectId(tag_id)
        self.update(pull__smart_tags=tag_id)

    def apply_schema(self, expression, context):
        hash_key = str(expression) + '__'.join(context)
        if hash_key in CustomerJourney.parsers_cache:
            parser = CustomerJourney.parsers_cache[hash_key]
        else:
            parser = BaseParser(expression, context.keys())
            CustomerJourney.parsers_cache[hash_key] = parser

        try:
            value = parser.evaluate(context)
        except TypeError:
            value = None
        return value

    def process_event(self, event, customer, agent, journey_stage_type):
        self._current_event = event
        received_event_from_past = False

        created_at = utc(event.created_at)
        last_updated = utc(self.last_updated) if self.last_updated else None

        if last_updated and created_at < last_updated:
            # log.error("=========RECEIVED EVENT FROM THE PAST %s %s < last updated %s" % (
            #     event, event.created_at, self.last_updated))
            received_event_from_past = True

        # IMPORTANT: No mongo calls should be done here at all!
        if agent:
            if agent.id not in self.agent_ids:
                self.agent_ids.append(agent.id)
                # TODO: This needs to be enforced on profile dynamic classes as a separate specific
                # column (can be optional)
                self.agent_names.append(str(agent))
        # TODO: Same as for agent profile, this needs to be set on dynamic class level
        self.customer_name = str(customer)
        if event.channels[0] not in self.channels:
            self.channels.append(event.channels[0])
        if not received_event_from_past:
            if journey_stage_type:
                self.status = journey_stage_type.status
            self.last_event_date = event.created_at
            self.last_updated = event.created_at
            # TODO: This whole strategy switch will need to be changed to be defined somehow on journey level
            # TODO: ISSSUE for the last stage the information is not copied. Will need to do this on journey closure.
            for strategy in [STRATEGY_DEFAULT, STRATEGY_PLATFORM, STRATEGY_EVENT_TYPE]:
                self.check_for_stage_transition(strategy, event, journey_stage_type)

            schema_computed_attributes = dict()
            # All of these need to be returned directly from customer data (no extra mongo calls!)
            expression_context = dict(agents=self.agents,
                                      customer_profile=self.customer_profile,
                                      current_event=event,
                                      event_sequence=self.event_sequence,
                                      current_stage=self.current_stage,
                                      previous_stage=self.previous_stage,
                                      stage_sequence=self.stage_sequence)
            # for k in self.field_names:
            #     expression_context[k] = getattr(self, k)
            # adding func with @property decorator to context
            for key in CustomerJourney.get_properties():
                expression_context[key] = getattr(self, key)

            for schema_entry in self.journey_attributes_schema:
                expression = schema_entry[self.FEAT_EXPR]
                f_name = schema_entry[self.FEAT_NAME]
                schema_computed_attributes[f_name] = self.apply_schema(expression, expression_context)
                expression_context[f_name] = schema_computed_attributes[f_name]
            self.journey_attributes = schema_computed_attributes

            if self.status in [JourneyStageType.COMPLETED, JourneyStageType.TERMINATED]:
                self.node_sequence_agr = []
                for i, item in enumerate(self.node_sequence):
                    key, value = item.items()[0]
                    self.node_sequence_agr.append(key)

    @classmethod
    def get_properties(cls):
        """ returns all list of member funcs decorated with @property """
        from copy import deepcopy
        base = deepcopy(cls.field_names)
        base = [field for field in base if field not in ('is_archived', '_t', 'acl', 'match_expression',
                                                         'journey_type_id', 'display_name', 'account_id',
                                                         'id', 'available_stages')]
        base.extend([name for name, value in vars(cls).items() if isinstance(value, property)])
        return base

    @property
    def CONSTANT_DATE_NOW(self):
        # For being picked up by context
        from datetime import datetime
        return datetime.now()

    @property
    def CONSTANT_ONE_DAYS(self):
        from datetime import timedelta
        return timedelta(hours=24)

    @property
    def CONSTANT_ONE_HOUR(self):
        from datetime import timedelta
        return timedelta(hours=1)

    def check_for_stage_transition(self, strategy, event, journey_stage_type):
        current_stage = self.get_current_stage(strategy)
        if strategy == STRATEGY_DEFAULT:
            new_stage = journey_stage_type.display_name if journey_stage_type else current_stage
        elif strategy == STRATEGY_EVENT_TYPE:
            new_stage = journey_stage_type.display_name + ':' + str(event.event_type) if journey_stage_type else current_stage
        elif strategy == STRATEGY_PLATFORM:
            new_stage = journey_stage_type.display_name + ':' + event.platform if journey_stage_type else current_stage
        if new_stage != current_stage:
            stage_index = self.get_current_index(strategy)
            new_stage_value = STAGE_INDEX_SEPARATOR.join([new_stage, str(stage_index + 1)])
            if current_stage is not None:
                full_stage_name = STAGE_INDEX_SEPARATOR.join([current_stage, str(stage_index)])
                self.stage_information[full_stage_name] = self.compute_stage_information(strategy)
            self.stage_sequences[strategy] = self.stage_sequences.get(strategy, []) + [new_stage_value]
            if strategy == STRATEGY_DEFAULT:
                self.stage_name = journey_stage_type.display_name
                self.stage_sequence_names.append(new_stage)
        if strategy == STRATEGY_EVENT_TYPE:
            if current_stage is None and new_stage is None:
                return
            # TODO: This is still kind of hard coded for MPC
            if new_stage != current_stage:
                self.node_sequence.append({new_stage: 1})
            else:
                self.node_sequence[-1][new_stage] += 1

    def compute_stage_information(self, strategy):
        info = dict()
        for key, val in self.journey_attributes.iteritems():
            info[key] = val
        info['end_date'] = self.last_event_date
        if len(self.stage_sequences.get(strategy, [])) <= 1:
            info['start_date'] = self.first_event_date
        else:
            info['start_date'] = self.stage_information[self.stage_sequences[strategy][-2]]['end_date']
        return info

    def close_journey(self):
        for strategy in [STRATEGY_DEFAULT, STRATEGY_PLATFORM, STRATEGY_EVENT_TYPE]:
            current_stage = self.get_current_stage(strategy)
            stage_index = self.get_current_index(strategy)
            if current_stage is not None:
                full_stage_name = STAGE_INDEX_SEPARATOR.join([current_stage, str(stage_index)])
                self.stage_information[full_stage_name] = self.compute_stage_information(strategy)
        self.save()

    def get_current_stage(self, strategy_type):
        if not self.stage_sequences.get(strategy_type):
            return None
        else:
            return self.stage_sequences.get(strategy_type)[-1].split(STAGE_INDEX_SEPARATOR)[0]

    def get_current_index(self, strategy_type):
        if not self.stage_sequences.get(strategy_type):
            return -1
        else:
            return int(self.stage_sequences.get(strategy_type)[-1].split(STAGE_INDEX_SEPARATOR)[1])

    def stage_sequence_by_strategy(self, strategy):
        return [val.split(STAGE_INDEX_SEPARATOR)[0] for val in self.stage_sequences[strategy]]

    def __get_agents(self):
        if hasattr(self, '_agents'):
            return self._agents
        else:
            self._agents = self.account.get_agent_profile_class().objects.find(id__in=self.agent_ids)[:]
            return self._agents

    def __set_agents(self, agents):
        self._agents = agents

    agents = property(__get_agents, __set_agents)

    def __get_customer_profile(self):
        if hasattr(self, '_customer_profile'):
            return self._customer_profile
        else:
            self._customer_profile = self.account.get_customer_profile_class().objects.get(self.customer_id)
            return self._customer_profile

    def __set_customer_profile(self, customer_profile):
        self._customer_profile = customer_profile

    customer_profile = property(__get_customer_profile, __set_customer_profile)

    def __get_current_event(self):
        if hasattr(self, '_current_event'):
            return self._current_event
        else:
            self._current_event = self.event_sequence[-1] if self.event_sequence else None
            return self._current_event

    def __set_current_event(self, event):
        self._current_event = event

    current_event = property(__get_current_event, __set_current_event)

    def __get_event_sequence(self):
        if hasattr(self, '_event_sequence'):
            return self._event_sequence
        else:
            from solariat_bottle.db.account import Account
            account = Account.objects.get(self.account_id)
            CustomerProfile = account.get_customer_profile_class()
            try:
                customer = CustomerProfile.objects.get(self.customer_id)
            except CustomerProfile.DoesNotExist:
                self._event_sequence = []
                return self._event_sequence

            if self.first_event_date and self.last_event_date:
                events = Event.objects.events_for_actor(
                    self.first_event_date, self.last_event_date, customer.actor_num)[:]

                self._event_sequence = events
                return self._event_sequence
                # event_type_ids = [x.event_type for x in events]
                # event_types = EventType.objects(id__in=event_type_ids)[:]
                # event_type_map = {str(x.id): x.name for x in event_types}
                # return [event_type_map[x.event_type] for x in events]
            self._event_sequence = []
            return self._event_sequence

    def __set_event_sequence(self, event_sequence):
        self._event_sequence = event_sequence

    event_sequence = property(__get_event_sequence, __set_event_sequence)

    @property
    def current_stage(self):
        if len(self.stage_sequences.get(STRATEGY_DEFAULT, [])) == 0:
            return None
        else:
            last_stage = self.stage_sequences[STRATEGY_DEFAULT][-1].split(STAGE_INDEX_SEPARATOR)[0]
            return last_stage

    @property
    def nps(self):
        nps1 = self.journey_attributes.get('nps')
        event = self.current_event

        from solariat_bottle.db.post.nps import NPSOutcome
        if isinstance(event, NPSOutcome):
            nps2 = self.current_event.score
        else:
            nps2 = None
        return max(nps1, nps2)

    @staticmethod
    def nps_value_to_label(value):
        if value is None:
            return 'n/a'
        elif 0 <= value <= 6:
            return 'detractor'
        elif value in (7, 8):
            return 'passive'
        elif value in (9, 10):
            return 'promoter'
        else:
            raise Exception("invalid nps value (%r given)" % value)

    @property
    def nps_category(self):
        # from solariat_bottle.views.facets import nps_value_to_label
        if self.nps == 'N/A':
            return 'N/A'
        else:
            return self.nps_value_to_label(self.nps)

    @property
    def previous_stage(self):
        if self.current_stage is None:
            return None

        if len(self.stage_sequences.get(STRATEGY_DEFAULT, [])) <= 1:
            return None
        else:
            last_stage = self.stage_sequences[STRATEGY_DEFAULT][-2].split(STAGE_INDEX_SEPARATOR)[0]
            return last_stage

    @property
    def stage_sequence(self):
        if len(self.stage_sequences.get(STRATEGY_DEFAULT, [])) == 0:
            return []
        else:
            return [val.split(STAGE_INDEX_SEPARATOR)[0] for val in self.stage_sequences[STRATEGY_DEFAULT]]

    @property
    def first_event(self):
        event_sequence = self.event_sequence
        if event_sequence:
            return event_sequence[0]
        else:
            return None

    @property
    def is_abandoned(self):
        if self.status == JourneyStageType.TERMINATED:
            return 1
        else:
            return 0

    @property
    def days(self):
        if self.first_event_date and self.last_event_date:
            return (utc(self.last_event_date) - utc(self.first_event_date)).days
        else:
            return None
