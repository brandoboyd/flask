from solariat.db import fields

from solariat_bottle.db.predictors.abc_predictor import ABCPredictor
from solariat_bottle.db.journeys.journey_stage import JourneyStage
from solariat_bottle.db.journeys.journey_type import JourneyType


class JourneyTag(ABCPredictor):
    SMART_TAG_SKIP = -1
    SMART_TAG_APPLY = 1

    collection = 'JourneyTag'

    display_name = fields.StringField(required=True, db_field='dn')
    description = fields.StringField(db_field='desc')
    account_id = fields.ObjectIdField(db_field='aid')
    journey_type_id = fields.ObjectIdField(required=True, db_field='jt')
    tracked_stage_sequences = fields.ListField(fields.ObjectIdField(), db_field='tsseq')    # list of stage_type ids
    tracked_customer_segments = fields.ListField(fields.ObjectIdField(), db_field='tcseq')  # list of customer_segment ids
    nps_range = fields.ListField(fields.NumField(), db_field='npsr')            # [min, max]
    csat_score_range = fields.ListField(fields.NumField(), db_field='csatr')    # [min, max]
    key_smart_tags = fields.ListField(fields.ObjectIdField(), db_field='kstg')
    skip_smart_tags = fields.ListField(fields.ObjectIdField(), db_field='sstg')

    indexes = [('journey_type_id',)]

    def check_preconditions(self, journey):
        if not self.journey_type_id == journey.journey_type_id:
            return False

        if self.tracked_stage_sequences:
            journey_stage_type_ids = set(JourneyStage.objects.get(stage_id).stage_type_id for stage_id in journey.stage_sequence)
            if not journey_stage_type_ids.intersection(self.tracked_stage_sequences):
                return False

        if self.tracked_customer_segments:
            customer_segments = set(journey.customer_segments)
            if not customer_segments.intersection(self.tracked_customer_segments):
                return False

        if self.nps_range and self.nps_range != [0, 0]:
            if not (self.nps_range[0] <= journey.nps <= self.nps_range[1]):
                return False

        if self.csat_score_range and self.csat_score_range != [0, 0]:
            if not (self.csat_score_range[0] <= journey.csat_score <= self.csat_score_range[1]):
                return False

        return True

    def rule_based_match(self, journey):
        # TODO if it returns 0, classifier model would be used which doesn't exist yet
        return 1

    def to_dict(self, fields_to_show=None):
        rv = super(JourneyTag, self).to_dict(fields_to_show)
        if 'packed_clf' in rv:
            del rv['packed_clf']
        rv['tracked_stage_sequences'] = map(str, self.tracked_stage_sequences)
        rv['tracked_customer_segments'] = map(str, self.tracked_customer_segments)
        rv['key_smart_tags'] = map(str, self.key_smart_tags)
        rv['skip_smart_tags'] = map(str, self.skip_smart_tags)
        return rv

    def fits_to_smart_tags(self, smart_tags):
        smt_ids = [smt.id for smt in smart_tags]

        if set(self.skip_smart_tags).intersection(smt_ids):
            return self.SMART_TAG_SKIP

        if (
            set(self.key_smart_tags).intersection(smt_ids) and
            not set(self.skip_smart_tags).intersection(smt_ids)
        ):
            return self.SMART_TAG_APPLY

    @property
    def journey_type(self):
        return JourneyType.objects.get(self.journey_type_id)
