from flask import jsonify

from ..app import app
from ..db.message_queue import TaskMessage
from ..utils.decorators import login_required


@app.route('/error-messages/count', methods=['POST', 'GET'])
@login_required
def count_task_messages(user):
    return jsonify(
        {'ok': True, 'count': TaskMessage.objects(user=user).count()})


@app.route('/error-messages/json', methods=['POST', 'GET'])
@login_required
def list_task_messages(user):
    result = []
    pending_messages = TaskMessage.objects.find(user=user)
    for message in pending_messages:
        result.append({'message': message.content, 'type': message.type})
        TaskMessage.objects.remove(message.id)
    return jsonify({'ok': True, 'data': result})
