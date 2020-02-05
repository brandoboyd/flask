import re
from collections import defaultdict

from solariat.db import fields
from solariat.db.abstract import KEY_NAME, KEY_TYPE
from solariat_bottle.utils.schema import get_journey_expression_functions
from solariat_bottle.utils.schema import get_standard_functions
from solariat_bottle.utils.schema import get_stage_context
from solariat.utils.parsers.base_parser import BaseParser, register_operator
from solariat.utils.timeslot import now
from solariat_bottle.db.auth import ArchivingAuthDocument, ArchivingAuthManager
from solariat_bottle.db.events.event_type import BaseEventType
from solariat_bottle.db.journeys.journey_stage import JourneyStage
from solariat_bottle.db.schema_based import SchemaBased


STATUS_ONGOING = 'ongoing'
STATUS_FINISHED = 'finished'
STATUS_ABANDONED = 'abandoned'
STATUS_CLOSED = 'closed'

KEY_CARDINALITY_COUNT = 'count'
KEY_CARDINALITY_TYPE = 'type'
KEY_CARDINALITY_VALUES = 'values'
KEY_CARDINALITY_DISPLAY_COUNT = 'display_count'


def attr_regex_match(event, attr_name, regex):
    if not hasattr(event, attr_name):
        return False

    attr_value = getattr(event, attr_name)
    if not attr_value:
        return False
    if regex in attr_value or re.match(regex, attr_value):
        return True
    else:
        return False
register_operator("match_regex", attr_regex_match)


class JourneyStageTypeManager(ArchivingAuthManager):

    def create(self, *args, **kwargs):
        journey_stage_type = super(JourneyStageTypeManager, self).create(*args, **kwargs)
        return journey_stage_type


class JourneyStageType(ArchivingAuthDocument):
    """
    Just act as a model class for all specific stage instances for a given JourneyType
    """
    COMPLETED = 1   # for any terminal states that are good
    TERMINATED = 2  # termination without completion
    IN_PROGRESS = 0
    CLOSED = 3

    STATUSES = {IN_PROGRESS, COMPLETED, TERMINATED, CLOSED}
    STATUS_TEXT_MAP = {
        COMPLETED: STATUS_FINISHED,
        TERMINATED: STATUS_ABANDONED,
        IN_PROGRESS: STATUS_ONGOING,
        CLOSED: STATUS_CLOSED
    }
    TEXT_STATUS_MAP = {v: k for k, v in STATUS_TEXT_MAP.items()}

    manager = JourneyStageTypeManager
    collection = "JourneyStageType"
    allow_inheritance = True

    display_name = fields.StringField(required=True, db_field='dn')
    account_id = fields.ObjectIdField(db_field='aid')
    journey_type_id = fields.ObjectIdField(db_field='jt')
    status = fields.NumField(db_field='ss', choices=STATUSES)
    journey_index = fields.NumField(db_field='ji', default=-1)      # If there is some default logical order, this will hold it
    event_types = fields.ListField(fields.StringField())
    match_expression = fields.StringField()

    parsers_cache = dict()

    @property
    def status_text(self):
        return self.STATUS_TEXT_MAP.get(self.status, 'unknown')

    @status_text.setter
    def status_text(self, value):
        if value in self.STATUS_TEXT_MAP:
            self.status = value
        elif value in self.TEXT_STATUS_MAP:
            self.status = self.TEXT_STATUS_MAP[value]

    @property
    def available_stages(self):
        return JourneyStage.objects.find(stage_type=self.id)

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

    @classmethod
    def get_properties(cls):
        """ returns all list of member funcs decorated with @property """
        from copy import deepcopy
        base = deepcopy(cls.field_names)
        base.extend([name for name, value in vars(cls).items() if isinstance(value, property)])
        return base

    def evaluate_event(self, event, customer_profile, event_sequence):
        hash_key = str(self.match_expression)
        if hash_key in JourneyType.parsers_cache:
            parser = JourneyType.parsers_cache[hash_key]
        else:
            base_context = ['event', 'current_event', 'customer_profile', 'event_sequence']
            base_context.extend(JourneyStageType.get_properties())
            parser = BaseParser(self.match_expression, base_context)
            JourneyType.parsers_cache[hash_key] = parser

        expression_context = {'event': event,
                              'current_event': event,
                              'None': None,
                              'customer_profile': customer_profile,
                              'event_sequence': event_sequence}
        for key in JourneyStageType.get_properties():
            expression_context[key] = getattr(self, key)
        return parser.evaluate(expression_context)

    def remove(self):
        self.objects.remove(self.id)

    def to_json(self, fields_to_show=None):
        data = super(JourneyStageType, self).to_json(fields_to_show)
        data['status_text'] = self.status_text
        return data

    def get_event_types(self):
        # TODO: change to use names
        return BaseEventType.objects(id__in=self.event_types)[:]

    def get_expression_context(self):
        context = ['event_sequence', 'event', 'customer_profile', 'current_event']
        context.extend(JourneyStageType.get_properties())
        context = [field for field in context if field not in ('is_archived', '_t', 'acl', 'match_expression',
                                                               'journey_type_id', 'display_name', 'account_id',
                                                               'id', 'available_stages')]
        return dict(
            event_types=[x.display_name for x in self.get_event_types()],
            functions=get_journey_expression_functions(),
            context=context
        )

    def to_dict(self, fields_to_show=None):
        d = super(JourneyStageType, self).to_dict(fields_to_show)
        d['expression_context'] = self.get_expression_context()
        d['event_types'] = [et.to_dict() for et in self.get_event_types()]
        return d


JourneyStageTypeEmbed = fields.EmbeddedDocumentField(JourneyStageType)


class JourneyTypeManager(ArchivingAuthManager):

    def create(self, *args, **kwargs):
        journey_type = super(JourneyTypeManager, self).create(*args, **kwargs)
        return journey_type


class JourneyType(ArchivingAuthDocument):

    allow_inheritance = True
    collection = 'JourneyType'

    manager = JourneyTypeManager

    display_name = fields.StringField(db_field='dn')
    description = fields.StringField(db_field='desc')
    account_id = fields.ObjectIdField(db_field='aid')
    available_stages = fields.ListField(JourneyStageTypeEmbed, db_field='as')
    journey_attributes_schema = fields.ListField(fields.DictField(), db_field='jas')
    journey_attributes_cardinalities = fields.DictField()
    mcp_settings = fields.ListField(fields.DictField(), db_field='mcps')
    journeys_num = fields.NumField(db_field='jn', default=0)
    created_at = fields.DateTimeField(default=now, db_field='ct')
    updated_at = fields.DateTimeField(default=now, db_field='ut')

    stage_key = 'stage'
    event_key = 'event'
    events_key = 'events'

    parsers_cache = dict()

    def __setattr__(self, k, v):
        # TODO: set journey_attributes_context_vars below class definition, but cyclic import won't allow
        from solariat_bottle.db.journeys.customer_journey import CustomerJourney
        JourneyType.journey_attributes_context_vars = (
            [JourneyType.stage_key, JourneyType.event_key, JourneyType.events_key] +
            CustomerJourney.field_names + CustomerJourney.get_properties() )

        schema_field_name = JourneyType.journey_attributes_schema.db_field
        if k == 'data' and schema_field_name in v:
            schema = v[schema_field_name]
        elif k == 'journey_attributes_schema':
            schema = v
        else:
            schema = None

        if schema:
            # schema is a meta schema for CustomerJourney, test if expression defined in the schema compiles successfully
            for d in schema:
                BaseParser(d['field_expr'], [])#JourneyType.journey_attributes_context_vars)

        return super(JourneyType, self).__setattr__(k, v)

    def get_journey_attributes_cardinalities(self):
        from copy import deepcopy
        dynamic_attributes = deepcopy(self.journey_attributes_cardinalities)
        if 'status' not in dynamic_attributes:
            dynamic_attributes['status'] = {KEY_CARDINALITY_COUNT: 3,
                                            KEY_CARDINALITY_TYPE: u'string',
                                            KEY_CARDINALITY_DISPLAY_COUNT: 3,
                                            KEY_CARDINALITY_VALUES: [STATUS_ONGOING,
                                                                     STATUS_FINISHED,
                                                                     STATUS_ABANDONED]}
        return dynamic_attributes

    def get_journey_type_attributes(self):
        # Wrapper to access journey schema along with any static fields that are worth
        # considering for facets or analysis
        return [attr['name'] for attr in self.journey_attributes_schema] + ['ss']   # Journey status, static attribute

    def compute_cardinalities(self):
        from solariat_bottle.db.journeys.customer_journey import CustomerJourney
        unique_values = defaultdict(lambda: dict(count=0, display_count=0, type=None, values=set()))

        threshold = SchemaBased.MAX_CARDINALITY_TO_STORE
        schema_types = {col['name']: col[KEY_TYPE] for col in self.journey_attributes_schema}

        # TODO For scalability, use mongodb distinct to compute unique values
        F = CustomerJourney.F
        for doc in CustomerJourney.objects.coll.find({F.journey_type_id: self.id}, {F.journey_attributes: 1}):
            for key, value in doc[F.journey_attributes].iteritems():
                #if col not in possible_columns:
                #    continue

                if unique_values[key][KEY_CARDINALITY_COUNT] > threshold:
                    # column's cardinality is over MAX_CARDINALITY_TO_STORE threshold
                    continue

                unique_values[key][KEY_CARDINALITY_TYPE] = schema_types[key]
                if isinstance(value, list):
                    for v in value:
                        unique_values[key][KEY_CARDINALITY_VALUES].add(v)
                else:
                    unique_values[key][KEY_CARDINALITY_VALUES].add(value)
                count = unique_values[key][KEY_CARDINALITY_COUNT] = len(unique_values[key][KEY_CARDINALITY_VALUES])

                if count > threshold:
                    del unique_values[key][KEY_CARDINALITY_VALUES]
                    count = '%d +' % threshold

                unique_values[key][KEY_CARDINALITY_DISPLAY_COUNT] = count

        # convert set to list
        for key, info in unique_values.iteritems():
            if info[KEY_CARDINALITY_COUNT] == 0:
                del info[KEY_CARDINALITY_VALUES]
            elif KEY_CARDINALITY_VALUES in info:
                info[KEY_CARDINALITY_VALUES] = list(info[KEY_CARDINALITY_VALUES])

        self.update(journey_attributes_cardinalities=unique_values)

    def find_stage(self, id_):
        stages = self.available_stages
        if id_ is None:
            return stages
        else:
            for s in stages:
                if str(s.id) == str(id_):
                    return s
            else:
                return None

    def remove(self):
        super(JourneyType, self).remove()
        for stage in self.available_stages:
            stage.remove()

    def remove_stage(self, id_):
        stage = self.find_stage(id_)
        if not stage:
            return "Not found"
        else:
            self.available_stages.remove(stage)
            self.update(pull__available_stages=JourneyStageTypeEmbed.to_mongo(stage),
                updated_at=now())
            stage.remove()

    def create_update_stage(self, stage):
        assert isinstance(stage, JourneyStageType), type(stage)
        assert stage.display_name

        if stage.id:
            # update - remove by id and add new one
            s = self.find_stage(stage.id)
            if s:
                self.available_stages.remove(s)
                # self.update(pull__available_stages=JourneyStageTypeEmbed.to_mongo(s))
            else:
                return None, 'Not found'

        if stage.display_name not in map(lambda s: s.display_name, self.available_stages):
            is_new = not stage.id
            stage.account_id = self.account_id
            stage.journey_type_id = self.id
            stage.save()

            if not is_new:
                # self.available_stages.remove(s)
                self.update(pull__available_stages=JourneyStageTypeEmbed.to_mongo(s))
            self.available_stages.append(stage)
            self.update(addToSet__available_stages=JourneyStageTypeEmbed.to_mongo(stage),
                updated_at=now())

            error = None
        else:
            error = u"Stage with name '%s' already exists" % stage.display_name
        return stage, error

    def get_expression_context(self):
        stages = [x.display_name for x in self.available_stages]
        funcs = get_journey_expression_functions()
        return {
            "context": get_stage_context(),
            "stages": stages,
            "stage_statuses": JourneyStageType.STATUS_TEXT_MAP.values(),
            "functions": funcs
        }

    def to_dict(self, fields_to_show=None):
        d = super(JourneyType, self).to_dict(fields_to_show)
        d['expression_context'] = self.get_expression_context()
        return d


