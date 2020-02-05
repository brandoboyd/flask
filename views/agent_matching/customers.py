from flask import jsonify, request

from solariat_bottle.app import app
from solariat_bottle.utils.decorators import login_required

from solariat_bottle.db.events.event import Event


def fit_to_range(value, vmin=0.0, vmax=1.0):
    return max(vmin, min(value, vmax))


@app.route('/customers', methods=['POST'])
@login_required()
def create_customer(user):
    create_data = request.json
    CustomerProfile = user.account.get_customer_profile_class()
    customer = CustomerProfile.objects.create(**create_data)
    return jsonify(ok=True, item=customer.to_dict())


@app.route('/customers', methods=['GET'])
@login_required
def list_customer(user):
    customer_data = request.args

    customer_id = customer_data.get('customer_id')
    actor_counter = customer_data.get('actor_counter')

    CustomerProfile = user.account.get_customer_profile_class()
    if customer_id:
        try:
            return jsonify(ok=True, item=CustomerProfile.objects.get(customer_id).to_dict())
        except CustomerProfile.DoesNotExist:
            return jsonify(ok=True, error='No customer with id=%s found' % customer_id)
    elif actor_counter is not None:
        try:
            return jsonify(ok=True, item=CustomerProfile.objects.find(actor_counter=actor_counter).next().to_dict())
        except StopIteration:
            return jsonify(ok=True, error='No customer with actor_counter=%s found' % actor_counter)
    elif user.account:
        agents_list = [a.to_dict() for a in CustomerProfile.objects.find(account_id=user.account.id)]
        return jsonify(ok=True, list=agents_list)
    else:
        return jsonify(ok=False, error="Either channel or agent_id needs to be provided.")


@app.route('/customer/call', methods=['POST'])
@login_required
def customer_call(user):
    from solariat_bottle.db.predictors.factory import get_agent_matching_predictor

    customer_data = request.json
    customer_id = customer_data.get('customer_id', None)
    CustomerProfile = user.account.get_customer_profile_class()
    AgentProfile = user.account.get_agent_profile_class()

    if customer_id:
        try:
            customer = CustomerProfile.objects.get(customer_id)

            customer_intent = customer_data.get('call_intent', None)
            customer.last_call_intent = [str(customer_intent)]
            customer.save()

            m_e = get_agent_matching_predictor(customer.account_id)

            current_model = m_e.select_model(m_e.models[0])
            if not current_model:
                return jsonify({'ok': False, 'error': 'Agent matching model should be activated'})

            agents = AgentProfile.objects.find(account_id=customer.account_id)

            actions = []
            agents_dict = {}
            for agent in agents:
                agent_data = agent.to_dict()
                agent_data['action_id'] = str(agent.id)
                actions.append(agent_data)
                agents_dict[str(agent.id)] = agent.to_dict()

            context = customer.to_dict()
            score_results = m_e.score(actions, context, model=current_model)
            if 'error' in score_results:
                return jsonify(ok=False, error=score_results['error'])

            scored_agents = []
            selected_agent_id = None
            if score_results:
                selected_agent_id = score_results[0][0]
                for (agent_id, score, ucb_score) in score_results:
                    base_agent_dict = agents_dict[str(agent_id)]
                    base_agent_dict['match_score'] = int(score)
                    base_agent_dict['ucb_score'] = int(ucb_score)
                    if not selected_agent_id:
                        selected_agent_id = agent_id
                    scored_agents.append(base_agent_dict)

            # LOGGER.error("SCORE RESULTS ARE " + str(score_results))
            if selected_agent_id:
                return jsonify(ok=True, **{'selected_agent_id': str(selected_agent_id),
                                           'customer_id': str(customer.id),
                                           'considered_agents': scored_agents})
            else:
                return jsonify(ok=False, error='No agents available')
        except CustomerProfile.DoesNotExist:
            return jsonify(ok=True, error='No customer with id=%s found' % customer_id)
    else:
        return jsonify(ok=False, error="A customer id needs to be provided provided.")


@app.route('/customer/call/rating', methods=['POST'])
@login_required
def customer_call_rating(user):
    from solariat_bottle.db.predictors.factory import get_agent_matching_predictor
    from solariat_bottle.tasks.predictors import retrain_function
    customer_data = request.json
    CustomerProfile = user.account.get_customer_profile_class()
    AgentProfile = user.account.get_agent_profile_class()

    customer_id = customer_data.get('customer_id', None)
    selected_agent_id = customer_data.get('selected_agent_id', None)
    reward_rating = customer_data.get('reward_rating', None)

    if not customer_id:
        return jsonify(ok=True, error="Missing required parameter 'customer_id'")
    if not selected_agent_id:
        return jsonify(ok=True, error="Missing required parameter 'selected_agent_id'")
    if not reward_rating:
        return jsonify(ok=True, error="Missing required parameter 'reward_rating'")

    try:
        customer = CustomerProfile.objects.get(customer_id)
    except CustomerProfile.DoesNotExist:
        return jsonify(ok=True, error='No customer with id=%s found' % customer_id)

    try:
        agent = AgentProfile.objects.get(selected_agent_id)
    except AgentProfile.DoesNotExist:
        return jsonify(ok=True, error='No agent with id=%s found' % selected_agent_id)

    m_e = get_agent_matching_predictor(account_id=customer.account_id)
    reward_rating = int(reward_rating)

    action = agent.to_dict()
    action['action_id'] = str(agent.id)

    context = customer.to_dict()
    m_e.feedback(context, action, reward_rating, skip_training=False)
    retrain_function(m_e, m_e.models)

    return jsonify(ok=True, message="Reward submitted successfully.")

@app.route('/call_intents/json', methods=['GET'])
@login_required
def call_intents(user):
    CustomerProfile = user.account.get_customer_profile_class()
    # cursor = CustomerIntentLabel.objects(account_id=user.account.id)
    # results = sorted([each.to_dict() for each in cursor], key=lambda d: d['intent'])
    # return jsonify(ok=True, list=results)
    # TODO: re-implement to actually return a specific attribute
    return jsonify(ok=True, list=[])

@app.route('/customer_industries/json', methods=['GET'])
@login_required
def customer_industries(user):
    CustomerProfile = user.account.get_customer_profile_class()
    cursor = CustomerProfile.objects.coll.find(account_id=user.account.id).distinct('industry')
    results = sorted(cursor)
    return jsonify(ok=True, list=results)

@app.route('/customer_events/json', methods=['POST'])
@login_required
def customer_events(user):
    customer_data = request.json

    id_lower_bound = customer_data['event_first_id']
    id_upper_bound = customer_data['event_last_id']
    CustomerProfile = user.account.get_customer_profile_class()
    AgentProfile = user.account.get_agent_profile_class()

    results = []
    for each in Event.objects(id__lte=long(id_upper_bound), id__gte=long(id_lower_bound)):
        result = each.to_dict()
        if each.is_inbound:
            result['user'] = CustomerProfile.objects.get(actor_counter=each.customer_id).to_dict()
        else:
            result['user'] = AgentProfile.objects.get(each.actor_id).to_dict()
        results.append(result)
    return jsonify(ok=True, list=results)

@app.route('/customers_distribution/json', methods=['POST'])
@login_required
def customers_distribution(user):
    results = [
        {
          "data": [
            [
              4,
              20
            ]
          ],
          "label": "asks"
        },
        {
          "data": [
            [
              14,
              6
            ]
          ],
          "label": "needs"
        },
        {
          "data": [
            [
              18,
              54
            ]
          ],
          "label": "problem"
        },
        {
          "data": [
            [
              12,
              7
            ]
          ],
          "label": "likes"
        },
        {
          "data": [
            [
              8,
              1
            ]
          ],
          "label": "gratitude"
        },
        {
          "data": [
            [
              2,
              1
            ]
          ],
          "label": "apology"
        },
        {
          "data": [
            [
              20,
              13
            ]
          ],
          "label": "recommendation"
        },
        {
          "data": [
            [
              10,
              60
            ]
          ],
          "label": "junk"
        }
    ]
    return jsonify(ok=True, list=results)
