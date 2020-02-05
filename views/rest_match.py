"""
Specific endpoints for searching best matches and training for the task before hand.
"""
from flask import jsonify

from solariat_bottle.app import app, get_api_url
from solariat_bottle.utils.request import _get_request_data
from solariat_bottle.db.matchable import Matchable, BenchmarkQuestion, BenchmarkTraining
from solariat_bottle.db.post.utils import factory_by_user
from solariat_bottle.tasks.commands import reset_channel_data
from solariat_bottle.utils.decorators import login_required

from solariat_bottle.settings import get_var


@app.route(get_api_url('search', version='v1.2'), methods=['POST'])
@login_required()
def search_match(user):
    data = _get_request_data()
    BenchmarkQuestion.objects.create(received_data=data)    # For internal book-keeping
    post_content = data['post_content']
    channel_id = data['channel_id']
    post = factory_by_user(user, content=post_content, channel=channel_id)
    return jsonify(ok=True, items=sorted([{'creative': _d['creative'],
                                           'relevance': _d['relevance'],
                                           'id': _d['id']} for _d in post._get_matchable_dicts()[0]],
                                         key=lambda x: -x['relevance']))


@app.route(get_api_url('clear_matches', version='v1.2'), methods=['POST'])
@login_required()
def clear_matches(user):
    data = _get_request_data()
    channel_id = data['channel_id']
    if get_var('ON_TEST'):
        reset_channel_data.sync(channel_id)
    else:
        reset_channel_data.ignore(channel_id)
    return jsonify(ok=True, message="Task for channel reset was started.")

