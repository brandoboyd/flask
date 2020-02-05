from solariat.db import fields

from solariat.db.abstract import Manager
from solariat.exc.base import AppException
from solariat_bottle.db.predictors.abc_predictor import ABCPredictor


class JourneyStageManager(Manager):

    def create(self, **kw):
        from solariat_bottle.db.journeys.customer_journey import CustomerJourney
        journey_id = kw['journey_id']
        customer_journey = CustomerJourney.objects.get(journey_id)
        journey_type = customer_journey.journey_type
        if not kw['stage_type_id'] or journey_type.find_stage(kw['stage_type_id']) is None:
            raise AppException("No stage %s exists in journey type %s" % (kw['stage_type_id'],
                                                                          journey_type.display_name))
        return super(JourneyStageManager, self).create(**kw)


class JourneyStage(ABCPredictor):

    collection = 'JourneyStage'
    manager = JourneyStageManager

    journey_id = fields.ObjectIdField(db_field='jo')
    stage_type_id = fields.ObjectIdField(db_field='st')    # Will be reference to a JourneyStageType
    stage_name = fields.StringField(db_field='sn')

    effort_info = fields.DictField(db_field='ef')   # Embedded doc with any effort info we're going to track
    reward_info = fields.DictField(db_field='ri')   # Embedded doc with any reward info we're going to track

    start_date = fields.DateTimeField(db_field='sd')
    end_date = fields.DateTimeField(db_field='ed')
    last_updated = fields.DateTimeField(db_field='lu')  # We're probably going to want to know when was the last even from this stage directly
    last_event = fields.EventIdField(db_field='le')    # Keep track of the event itself

    def check_preconditions(self, event):
        if hasattr(event, 'stage_id') and event.stage_id:
            # If 'stage_id' exists on event, and it's not None, that will be a precondition and acceptance rule
            return str(self.id) == event.stage_id
        if hasattr(event, 'journeys') and event.journeys:
            # If a specific set of journeys was passed with the event, the journey for this stage
            return self.journey_id in event.journeys
        return True

    def rule_based_match(self, object):
        if hasattr(object, 'stage_id') and object.stage_id:
            # If 'stage_id' exists on event, and it's not None, that will be a precondition and acceptance rule
            return str(self.id) == object.stage_id
        return False

    def process_event(self, event):
        update_dict = dict(set__last_event=event.data['_id'],
                           set__last_updated=event.datetime_from_id)

        self.update(**update_dict)

    def get_journey_stage_type(self):
        from solariat_bottle.db.journeys.journey_type import JourneyStageType
        return JourneyStageType.objects.get(self.stage_type_id)

