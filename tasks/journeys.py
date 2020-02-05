import pymongo
from datetime import datetime
from collections import defaultdict
from solariat.utils.timeslot import utc

from solariat_bottle.settings import LOGGER
from solariat_bottle.db.events.event import Event
from solariat_bottle.db.account import Account
from solariat_bottle.utils.id_encoder import unpack_event_id, pack_event_id
from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType
from solariat_bottle.db.journeys.customer_journey import CustomerJourney


def process_event_batch(account_id, batch_size):
    start_time = datetime.now()
    # TODO: Once it works, break this up in specific sub-calls to make code more readable.
    account = Account.objects.get(account_id)
    CustomerProfile = account.get_customer_profile_class()
    AgentProfile = account.get_agent_profile_class()
    # TODO: account_id should be used for account specific collections
    customer_event_map = defaultdict(list)
    journey_event_map = defaultdict(list)

    customer_profile_map = dict()
    agent_profile_map = dict()
    journey_type_map = dict()
    num_to_id_customer = dict()
    customer_id_to_num = dict()

    for journey_type in JourneyType.objects.find(account_id=account_id):
        journey_type_map[journey_type.display_name] = journey_type

    agent_ids = set()
    # TODO: After account specific collection is done this should work just fine / uncomment
    # event_batch = Event.objects.find(_was_processed=False).sort(_created=1)[:batch_size]
    event_batch = Event.objects.find(
        channels__in=[c.id for c in account.get_current_channels()],
        _was_processed=False).sort(_created=1)[:batch_size]

    if not event_batch:
        print "No new events found"
        return
    for event in event_batch:
        actor_num, _ = unpack_event_id(event.id)
        agent_id = None
        if not event.is_inbound:
            agent_id = event.actor_id
            agent_ids.add(agent_id)
        customer_event_map[actor_num].append((event, agent_id))

    all_customers = CustomerProfile.objects.find(actor_num__in=customer_event_map.keys())[:]
    for customer in all_customers:
        customer_profile_map[customer.actor_num] = customer
        num_to_id_customer[customer.actor_num] = customer.id
        customer_id_to_num[customer.id] = customer.actor_num
    all_active_journeys = CustomerJourney.objects.find(account_id=account.id,
                                                       customer_id__in=num_to_id_customer.values(),
                                                       status=JourneyStageType.IN_PROGRESS)[:]

    event_sequence_query = []
    for journey in all_active_journeys:
        journey._event_sequence = []
        journey_event_map[journey.customer_id].append(journey)
        for agent in journey.agent_ids:
            agent_ids.add(agent)

        actor_num = customer_id_to_num[journey.customer_id]
        id_lower_bound = pack_event_id(actor_num, utc(journey.first_event_date))
        id_upper_bound = pack_event_id(actor_num, utc(journey.last_event_date))
        event_sequence_query.append({'_id': {'$gte': id_lower_bound, '$lte': id_upper_bound}})

    actor_id_events = defaultdict(list)
    if event_sequence_query:
        all_required_events = Event.objects.find(**{'$or': event_sequence_query})[:]
        for event in sorted(all_required_events, key=lambda x: x.created_at):
            actor_num, _ = unpack_event_id(event.id)
            customer_id = num_to_id_customer[actor_num]
            for journey in journey_event_map[customer_id]:
                if utc(journey.first_event_date) <= utc(event.created_at) <= utc(journey.last_event_date):
                    journey._event_sequence.append(event)
            actor_id_events[customer_id].append(event)

    all_agents = AgentProfile.objects.find(id__in=agent_ids)[:]
    for agent in all_agents:
        agent_profile_map[agent.id] = agent
    print "Finished loading all the required data in " + str(datetime.now() - start_time)
    start_time = datetime.now()
    # All ongoing journeys for this customers are considered. For all of the customers that don't have any active
    # journeys we need to figure out what new type to start. If
    for customer_num, customer_events in customer_event_map.iteritems():
        # TODO: If we need to, this would be a point where we can split based on customer id
        if customer_num not in customer_profile_map:
            continue    # Events from different account. Will be fixed by account specific collections
        customer = customer_profile_map[customer_num]
        for (event, agent) in customer_events:
            event._was_processed = True
            actor_num, _ = unpack_event_id(event.id)
            customer_id = num_to_id_customer[actor_num]
            journey_candidates = journey_event_map[customer.id]

            direct_mappings = dict()
            for mapping in event.journey_mapping:
                journey_type_name, journey_stage_name = mapping.split('__')
                direct_mappings[journey_type_name] = journey_stage_name

            for journey_type in journey_type_map.values():
                found_journey_stage = None
                if journey_type.display_name in direct_mappings:
                    found_journey_stage = [stage for stage in journey_type.available_stages if
                                           stage.display_name == direct_mappings[journey_type.display_name]][0]
                else:
                    for journey_stage in journey_type.available_stages:
                        if journey_stage.evaluate_event(event, customer, actor_id_events.get(customer_id, [])):
                            found_journey_stage = journey_stage
                            break

                found_match = False
                # First step is to try and find it in existing journeys
                for journey in journey_candidates:
                    # All the currently in progress or completed journeys that are matched to same stage
                    if journey.journey_type_id == journey_type.id: # and (journey.status == JourneyStageType.IN_PROGRESS or
                                                                   #    journey.f_current_stage == found_journey_stage):
                        found_match = True
                        journey.agents = [agent_profile_map[a_id] for a_id in journey.agent_ids]
                        journey.customer_profile = customer
                        journey.current_event = event
                        journey.journey_type = journey_type

                        journey.process_event(event, customer, agent_profile_map[agent] if agent else None,
                                              found_journey_stage)
                        journey.event_sequence = journey.event_sequence + [event]

                if found_journey_stage:
                    # If we didn't find any match in existing journeys, create a new one. We create it in memory
                    # So as to not do any extra mongo calls.
                    if not found_match:
                        journey = CustomerJourney(customer_id=customer.id,
                                                  journey_type_id=journey_type.id,
                                                  first_event_date=event.created_at,
                                                  account_id=account_id,
                                                  status=JourneyStageType.IN_PROGRESS,
                                                  node_sequence=[],
                                                  node_sequence_agr=[],
                                                  journey_attributes_schema=journey_type.journey_attributes_schema)
                        journey._event_sequence = []
                        journey_candidates.append(journey)
                        journey.agents = [agent_profile_map[a_id] for a_id in journey.agent_ids]
                        journey.customer_profile = customer
                        journey.current_event = event
                        journey.journey_type = journey_type

                        journey.process_event(event, customer, agent_profile_map[agent] if agent else None,
                                              found_journey_stage)
                        journey.event_sequence = journey.event_sequence + [event]    # TODO: As it is, it will still be one call per journey
                        journey_type.journeys_num += 1

    print "Finished computing journey info in " + str(datetime.now() - start_time)
    start_time = datetime.now()
    # Upsert all journeys, all customer profiles, all agent profiles, all events
    if all_agents:
        bulk_agents = AgentProfile.objects.coll.initialize_unordered_bulk_op()
        for agent in all_agents:
            bulk_agents.find({"_id": agent.id}).upsert().update({'$set': agent.data})
        bulk_agents.execute()

    if all_customers:
        bulk_customers = CustomerProfile.objects.coll.initialize_unordered_bulk_op()
        for customer in all_customers:
            bulk_customers.find({"_id": customer.id}).upsert().update({'$set': customer.data})
        bulk_customers.execute()

    if event_batch:
        bulk_events = Event.objects.coll.initialize_unordered_bulk_op()
        for event in event_batch:
            bulk_events.find({"_id": event.id}).upsert().update({'$set': event.data})
        bulk_events.execute()

    if journey_event_map.values():
        bulk_journeys = CustomerJourney.objects.coll.initialize_unordered_bulk_op()
    have_journeys = False
    for customer_journeys in journey_event_map.values():
        for journey in customer_journeys:
            have_journeys = True
            if journey.id:
                bulk_journeys.find({"_id": journey.id}).upsert().update({'$set': journey.data})
            else:
                bulk_journeys.insert(journey.data)
    if have_journeys:
        bulk_journeys.execute()
    else:
        print "No journeys to upsert"

    print "Finished all the bulk inserts in " + str(datetime.now() - start_time)

    for journey_type in journey_type_map.values():
        journey_type.compute_cardinalities()
        journey_type.update(journeys_num=journey_type.journeys_num)

    # # TODO: This needs to be handled based on some rules we enforce or let the user define.
    # for journey in CustomerJourney.objects():
    #     if journey.status == JourneyStageType.IN_PROGRESS:
    #         journey.close_journey()
