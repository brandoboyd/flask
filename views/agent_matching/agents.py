from flask import jsonify, request

from solariat_bottle.app import app
from solariat_bottle.utils.decorators import login_required


@app.route('/agents', methods=['POST'])
@login_required()
def create_agent(user):
    create_data = request.json
    AgentProfile = user.account.get_agent_profile_class()
    agent = AgentProfile.objects.create(**create_data)
    return jsonify(ok=True, item=agent.to_dict())


@app.route('/agents', methods=['GET'])
@login_required
def list_agents(user):
    agent_data = request.args
    AgentProfile = user.account.get_agent_profile_class()
    
    agent_id = agent_data.get('agent_id', None)
    if agent_id:
        try:
            return jsonify(ok=True, item=AgentProfile.objects.get(agent_id).to_dict())
        except AgentProfile.DoesNotExist:
            return jsonify(ok=True, error='No agent with id=%s found' % agent_id)
    elif user.account:
        agents_list = [a.to_dict() for a in AgentProfile.objects.find(account_id=user.account.id)]
        return jsonify(ok=True, list=agents_list)
    else:
        return jsonify(ok=False, error="Either channel or agent_id needs to be provided.")
