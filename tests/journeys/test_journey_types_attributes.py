import datetime
import json

import mock
from nose.tools import eq_

from solariat.utils.timeslot import now
from solariat.utils.parsers.exceptions import ExpressionCompilationError
from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType
from solariat_bottle.db.journeys.journey_stage import JourneyStage
from solariat_bottle.db.journeys.customer_journey import CustomerJourney
from solariat_bottle.db.events.event import Event
from solariat_bottle.tests.base import UICaseSimple
from solariat_bottle.tests.base import setup_customer_schema, setup_agent_schema
from solariat_bottle.tasks.journeys import process_event_batch

#def add_attr(objects, attr, skip=True):
#    total = 0
#    for obj in objects:
#        if not hasattr(obj, attr):
#            if skip:
#                continue
#            else:
#                raise AttributeError(" type object %r has no attribute %r" % (type(obj), attr))
#        total += getattr(obj, attr)
#    return total
#
#register_operator('sum', add_attr)


class AttributeTestCase(UICaseSimple):
    def make_journey_type(self, schema):
        return JourneyType.objects.create(display_name="Purchasing",
                                          account_id=str(self.account.id),
                                          journey_attributes_schema=schema)

    def make_customer_journey(self, schema, **kwargs):
        jt = self.make_journey_type(schema)
        setup_customer_schema(self.user)
        CustomerProfile = self.account.get_customer_profile_class()

        customer = CustomerProfile.objects.create(id='cust001')
        cj = CustomerJourney.objects.create(journey_type_id=str(jt.id),
                                            account_id=str(self.account.id),
                                            customer_id=str(customer.id),
                                            journey_attributes_schema=schema,
                                            **kwargs)

        jst = JourneyStageType.objects.create(display_name="Querying",
                                              account_id=str(self.account.id),
                                              journey_type_id=str(jt.id))
        jt.available_stages = [jst]
        jt.save()
        return cj

    def create_event(self):
        event = mock.create_autospec(Event)
        event.created_at = now() + datetime.timedelta(days=1) #- datetime.timedelta(days=1)  # make it lesser than cj.last_updated so as to make cj.received_event_from_past True why?!?!
        event.datetime_from_id = event.created_at

        CustomerProfile = self.account.get_customer_profile_class()
        cf = mock.create_autospec(CustomerProfile)
        cf.assigned_segments = [123]
        event.customer_profile.return_value = cf

        return event


class JourneyTypesAttributesCase(AttributeTestCase):

    def test_example_schema(self):
        schema = [
                {'name': 'cost', 'type': 'integer', 'field_expr': "sum(events, 'cost', skip=True)"},
                {'name': 'nps', 'type': 'integer', 'field_expr': "sum(events, 'nps', skip=True)"},
                {'name': 'roi', 'type': 'integer', 'field_expr': "journey_attributes.nps/journey_attributes.csat_score"}
        ]
        jt = self.make_journey_type(schema)

    def test_failing_schema(self):
        bad_schema = [{'name': 'cost', 'type': 'integer', 'field_expr': "sum(events, 'cost', skip=True"}]
        try:
            jt = self.make_journey_type(bad_schema)
            self.fail("Should fail because trailing brace is missing from the schema expression")
        except ExpressionCompilationError, err:
            pass

        # deferred setting of journey_attributes_schema
        jt = JourneyType.objects.create(display_name="test_schema",
                                        account_id=str(self.account.id))
        try:
            jt.journey_attributes_schema = bad_schema
            self.fail("Should fail because trailing brace is missing from the schema expression")
        except ExpressionCompilationError, err:
            pass


class CustomerJourneyCase(AttributeTestCase):

    def test_simple_work_flow(self):
        schema = [
                {'name': 'cost', 'type': 'integer', 'field_expr': "sum(events, 'cost', skip=True)"},
                {'name': 'nps', 'type': 'integer', 'field_expr': "sum(events, 'nps', skip=True)"},
                {'name': 'roi', 'type': 'integer', 'field_expr': "journey_attributes.nps/journey_attributes.csat_score"}
        ]
        cj = self.make_customer_journey(schema)

    def test_use_journey_attr(self):
        schema = [{'label': 'ROI', 'name': 'roi', 'type': 'integer', 'field_expr': "journey_attributes.nps/journey_attributes.csat_score"}]
        cj = self.make_customer_journey(schema,
                                        journey_attributes=dict(
                                            nps=6,
                                            csat_score=3),
                                        last_updated=now(),
                                       )
        event = self.create_event()
        event.channels = [1]
        cj.process_event(event, object(), None, None)
        eq_(cj.journey_attributes, {'roi': 2})

    def test_use_current_event_attr(self):
        schema = [{'label': 'ROI', 'name': 'roi', 'type': 'integer', 'field_expr': "current_event.nps/journey_attributes.csat_score"}]
        cj = self.make_customer_journey(schema,
                                        journey_attributes=dict(
                                            csat_score=3),
                                        last_updated=now(),
                                       )
        event = self.create_event()
        event.channels = [1]
        event.nps = 6
        event.save()
        cj.process_event(event, object(), None, None)
        eq_(cj.journey_attributes, {'roi': 2})

    def test_use_all_contexts(self):
        schema = [{'label': 'ROI', 'name': 'roi', 'type': 'integer', 'field_expr': "current_event.nps/journey_attributes.csat_score + int(current_stage)"}]
        cj = self.make_customer_journey(schema,
                                        journey_attributes=dict(
                                            csat_score=3),
                                        last_updated=now(),
                                       )
        cj.stage_sequences = dict(default=['4'])
        event = self.create_event()
        event.channels = [1]
        event.nps = 21
        cj.process_event(event, object(), None, None)
        eq_(cj.journey_attributes, {'roi': 11})
