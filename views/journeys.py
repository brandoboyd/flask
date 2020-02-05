import datetime
import itertools
from flask import render_template, jsonify, request
from solariat_bottle.db.post.chat import ChatPost

from solariat.utils import timeslot
from solariat.utils.timeslot import utc, parse_date_interval, now
from solariat_bottle.app import app
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.db.channel.base import SmartTagChannel, Channel
from solariat_bottle.db.journeys.customer_journey import CustomerJourney, STRATEGY_DEFAULT, STAGE_INDEX_SEPARATOR
from solariat_bottle.db.journeys.journey_type import JourneyType, JourneyStageType
from solariat_bottle.db.journeys.journey_stage import JourneyStage
from solariat_bottle.db.events.event import Event
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.utils.views import jsonify_response

DEFAULT_PAGE_SIZE = 20


@app.route('/omni/<any(agents, customers):page>')  # /omni/agents, /omni/customers
@app.route('/omni/<any(agents, customers):page>/<filter_by>/<id>')  # /omni/agents/customer/123456789, /omni/customers/agent/987654321
@login_required()
def omni_agents_handler(user, page, filter_by=None, id=None):
    return render_template("/omni/%s.html" % page,
        user = user,
        section = page,
        top_level = page,
        mongo_id = id or ''
    )


@app.route('/omni/<any(journeys):page>')
@login_required()
def omni_journeys_handler(user, page, filter_by=None, id=None):
    return render_template("/omni/%s.html" % page,
        user = user,
        section = page,
        top_level = page,
        mongo_id = id or ''
    )

@app.route('/omni/partials/<section>/<page>')
@login_required()
def omi_partials_handler(user, page, section):
    return render_template("/omni/partials/%s/%s.html" % (section, page),
        user = user,
        section = page,
        top_level = page
    )


@app.route('/omni/<path:path>')
@login_required
def omni_interceptor(user, path):
    from solariat_bottle.settings import LOGGER

    LOGGER.info("TODO: return template for %s" % path)
    return path


def compute_customer_timeline(customer, from_dt, to_dt):
    def _get_platform(event):
        platform = event._t[0]
        if platform.endswith('Post') and platform != 'Post':
            platform = platform[:-len('Post')]
        return platform

    timeline_data = []
    for monthly_slot in reversed(list(timeslot.gen_timeslots(from_dt, to_dt, 'month'))):
        _month_start, _month_end = timeslot.Timeslot(monthly_slot).interval
        _month_events_count = Event.objects.range_query_count(from_dt, to_dt, customer)

        if not _month_events_count:
            continue

        if _month_start.month == to_dt.month:
            month_label = 'This Month'
        elif _month_start.month == to_dt.month - 1:
            month_label = 'Last Month'
        else:
            month_label = _month_start.strftime('%B')

        timeline_data.append([month_label, []])

        for daily_slot in reversed(list(timeslot.gen_timeslots(from_dt, to_dt, 'day'))):
            _day_start, _day_end = timeslot.Timeslot(daily_slot).interval
            _day_events = list(Event.objects.range_query(max(utc(from_dt), _day_start), min(utc(to_dt), _day_end), customer))

            if not _day_events:
                continue

            day_label = _day_start.strftime('%b %d')
            timeline_data[-1][-1].append([day_label, []])

            grouper = itertools.groupby(_day_events, _get_platform)
            for platform, platform_events in grouper:
                _events = list(platform_events)
                event_interval_ids = (str(_events[0].id), str(_events[-1].id))
                timeline_data[-1][-1][-1][-1].append((platform, len(_events), event_interval_ids))
    return customer, timeline_data


@app.route('/omni/journeys/<journey_id>/smart_tags', methods=['POST', 'GET', 'DELETE'])
@login_required()
def process_journey_tags(user, journey_id):
    data = _get_request_data()
    try:
        journey = CustomerJourney.objects.get(journey_id)
    except CustomerJourney.DoesNotExist:
        return jsonify(ok=True, error="No journey with id=%s was found" % journey_id)
    if request.method == 'POST':
        journey.handle_add_tag(data.get('tag_id'))
        return jsonify(ok=True)
    elif request.method == 'DELETE':
        journey.handle_remove_tag(data.get('tag_id'))
        return jsonify(ok=True)
    elif request.method == 'GET':
        return jsonify(ok=True, list=[tag.to_dict() for tag in SmartTagChannel.objects(id__in=journey.smart_tags)])
    return jsonify(ok=False, error="Unsupported method " + str(request.method))


@app.route("/journey/<journey_id>/stages")
@login_required()
def journey_information(user, journey_id):
    #TODO: THIS CODE IS BOGUS AS IT USES HARD CODED INFORATION
    journey = CustomerJourney.objects.get(journey_id)
    CustomerProfile = user.account.get_customer_profile_class()
    try:
        customer = CustomerProfile.objects.get(journey.customer_id)
        customer_info = customer.to_dict()
    except CustomerProfile.DoesNotExist:
        profile_schema = user.account.customer_profile._get()
        customer = profile_schema.get_data_class().objects.get(journey.customer_id)
        customer_info = customer.to_dict()

    stages_info = []
    for stage_info in journey.stage_sequences[STRATEGY_DEFAULT]:
        if stage_info in journey.stage_information:
            end_date = str(journey.stage_information[stage_info]['end_date'])
        else:
            end_date = str(now())
        stages_info.append(dict(stageName=stage_info.split(STAGE_INDEX_SEPARATOR)[0],
                                id=stage_info,
                                endDate=end_date))

    stages_info[0]['startDate'] = str(journey.first_event_date)
    for idx, stage_info in enumerate(stages_info[1:]):
        stage_info['startDate'] = stages_info[idx]['endDate']

    journey_info = dict(id=str(journey.id),
                        type=JourneyType.objects.get(journey.journey_type_id).display_name,
                        status=JourneyStageType.STATUS_TEXT_MAP[journey.status],
                        startDate=str(journey.first_event_date),
                        endDate=str(journey.last_event_date),
                        smartTags=[tag.title for tag in SmartTagChannel.objects(id__in=journey.smart_tags)],
                        stages=stages_info)
    return jsonify(ok=True, item=dict(customer=customer_info,
                                      journey=journey_info))


@app.route('/customer/journeys', methods=['POST'])
@login_required()
def customer_journeys(user):
    data = _get_request_data()
    customer_id = data['customer_id']
    from_ = data['from']
    to_ = data['to']

    from_dt, to_dt = parse_date_interval(from_, to_)
    F = CustomerJourney.F

    CustomerProfile = user.account.get_customer_profile_class()
    try:
        profile = CustomerProfile.objects.get(customer_id)
    except CustomerProfile.DoesNotExist:
        profile_schema = user.account.customer_profile._get()
        profile = profile_schema.get_data_class().objects.get(customer_id)

    journeys = CustomerJourney.objects.coll.find({
        F.customer_id: profile.id,
        #F.start_date: {'$gte': from_dt, '$lte': to_dt}
    }, {F.id: 1, F.journey_type_id: 1, F.first_event_date: 1, F.last_event_date: 1})

    journeys_info = []
    for j in journeys:
        journeys_info.append({
            'id': str(j[F.id]),
            'journey_type': JourneyType.objects.get(j[F.journey_type_id]).display_name,
            'start_date': j[F.first_event_date].isoformat(),
            'end_date': j[F.last_event_date].isoformat(),
            'typeId': str(j[F.journey_type_id])
        })

    return jsonify(ok=True, journeys=journeys_info)


@app.route('/journey/<journey_id>/<stage_id>/events')
@login_required()
def journey_stage_events(user, journey_id, stage_id):

    def _get_platform(event):
        platform = event._t[0]
        if platform.endswith('Post') and platform != 'Post':
            platform = platform[:-len('Post')]
        return platform

    data = _get_request_data()
    current_page = data.get('page', 0)
    current_page_size = data.get('page_size', DEFAULT_PAGE_SIZE)

    journey = CustomerJourney.objects.get(journey_id)
    CustomerProfile = user.account.get_customer_profile_class()
    customer = CustomerProfile.objects.get(journey.customer_id)
    if stage_id in journey.stage_information:
        end_date = journey.stage_information[stage_id]['end_date']
        start_date = journey.stage_information[stage_id]['start_date']
    else:
        end_date = datetime.datetime.utcnow()
        start_date = journey.first_event_date
    events = list(Event.objects.range_query(
        start_date, end_date, customer,
        skip=current_page * current_page_size,
        limit=current_page_size))

    if len(events) < current_page_size:
        # Reached the end
        next_page = -1
    else:
        next_page = current_page + 1
    events_info = []

    grouper = itertools.groupby(events, _get_platform)
    for platform, platform_events in grouper:
        _events = list(platform_events)
        agents = []
        channels = []
        content = []

        for event in _events:
            if event.is_inbound is False:
                agents.append(event.actor)
            channels.extend([chan.title for chan in Channel.objects(id__in=event.channels)])
            filters = {}
            if isinstance(event, ChatPost):
                filters['include_summary'] = False
            base_dict = event.to_dict(**filters)
            base_dict['computed_tags'] = event.json_computed_tags
            base_dict['journey_tags'] = event.journey_tags
            base_dict.pop('_computed_tags')
            base_dict.pop('actor', None)
            base_dict.pop('_reply_context', None)
            content.append(base_dict)

        events_info.append(dict(stageId=str(stage_id),
                                platform=platform,
                                messagesCount=len(_events),
                                agents=[a.agent_full_name for a in set(agents)],
                                channels=list(set(channels)),
                                content=content))

    return jsonify_response(ok=True, item=dict(
        nextPage=next_page,
        pageSize=current_page_size,
        events=events_info))


@app.route('/journeys/<journey_id>')
@login_required()
def customer_journey_timeline(user, journey_id):
    journey = CustomerJourney.objects.get(journey_id)
    CustomerProfile = user.account.get_customer_profile_class()
    customer = CustomerProfile.objects.get(journey.customer_id)
    from_dt = journey.first_event_date
    to_dt = journey.last_event_date
    customer, timeline_data = compute_customer_timeline(customer, from_dt, to_dt)
    return render_template("/omni/customer-profile.html",
                           user=user,
                           section="customers",
                           top_level="customers",
                           customer=customer,
                           timeline_data=timeline_data)


@app.route('/omni/journeys/<journey_id>/json')
@login_required()
def customer_journey_timeline_json(user, journey_id):
    journey = CustomerJourney.objects.get(journey_id)
    CustomerProfile = user.account.get_customer_profile_class()
    customer = CustomerProfile.objects.get(journey.customer_id)
    from_dt = journey.first_event_date
    to_dt = journey.last_event_date
    customer, timeline_data = compute_customer_timeline(customer, from_dt, to_dt)
    return jsonify(ok=True, item=dict(customer=customer.to_dict(), timeline_data=timeline_data))


@app.route('/omni/customer_timeline/<customer_id>/json')
@login_required()
def customer_profile_json(user, customer_id):
    CustomerProfile = user.account.get_customer_profile_class()
    customer = CustomerProfile.objects.get(customer_id)
    now = datetime.datetime.utcnow()

    today = datetime.datetime(now.year, now.month, now.day)
    from_dt = datetime.datetime(today.year, 1, 1)
    to_dt = today
    customer, timeline_data = compute_customer_timeline(customer, from_dt, to_dt)
    return jsonify(ok=True, item=dict(customer=customer.to_dict(), timeline_data=timeline_data))


@app.route('/omni/customer/<id>')
@login_required()
def customer_profile(user, id):
    CustomerProfile = user.account.get_customer_profile_class()
    customer = CustomerProfile.objects.get(id)

    now = datetime.datetime.utcnow()
    today = datetime.datetime(now.year, now.month, now.day)
    from_dt = datetime.datetime(today.year, 1, 1)
    to_dt = today
    customer, timeline_data = compute_customer_timeline(customer, from_dt, to_dt)
    return render_template("/omni/customer-profile.html",
                           user=user,
                           section="customers",
                           top_level="customers",
                           customer=customer,
                           timeline_data=timeline_data)


@app.route('/journey')
@app.route('/journey/agents')
@app.route('/journey/customers')
@login_required()
def journey_demo_handler(user, id=None):
    return render_template("/journey/demo-index.html",
        user = user
    )

@app.route('/journey/agent/<id>')
@login_required()
def agent_dashboard_handler(user, id=None):
    return render_template("/journey/agents-desktop-new.html",
        user = user,
        agent_id = id
    )



@app.route('/journey/supervisor')
@app.route('/journey/supervisor/<id>')

@login_required()
def supervisor_dashboard_handler(user, id=None):
    return render_template("/journey/supervisor-index.html",
        user = user
    )
