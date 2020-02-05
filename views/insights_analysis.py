import json
from flask import jsonify, request

from solariat.utils.timeslot import datetime_to_timestamp_ms, timestamp_ms_to_timeslot, timeslot_to_datetime
from solariat_bottle.app import app
from solariat_bottle.settings import LOGGER
from solariat_bottle.db.insights_analysis import InsightsAnalysis
from solariat_bottle.utils.decorators import login_required
from datetime import datetime

ACTION_STOP = 'stop'
ACTION_RESTART = 'restart'

@app.route('/analyzers/<analyzer_id>', methods=['GET', 'DELETE'])
@login_required()
def get_insight(user, analyzer_id):
    if not analyzer_id:
        return jsonify(ok=True, error="missing parameter analyzer_id")
    if request.method == 'DELETE':
        removed = InsightsAnalysis.objects.remove(id=analyzer_id)
        LOGGER.info("Removing analysis finished successfully: " + str(removed))
        return jsonify(ok=True if removed['ok'] else False, message="Successfully removed %s analysis." % removed['n'])
    else:
        try:
            return jsonify(ok=True, item=InsightsAnalysis.objects.get(analyzer_id).to_dict())
        except InsightsAnalysis.DoesNotExist, ex:
            return jsonify(ok=False, error="No Analysis found with id = %s" % analyzer_id)


@app.route('/analyzers/<analyzer_id>/<action>', methods=['POST'])
@login_required()
def insights_action(user, analyzer_id, action):
    if not analyzer_id:
        return jsonify(ok=True, error="missing parameter analyzer_id")
    if action not in (ACTION_RESTART, ACTION_STOP):
        return jsonify(ok=False, error="Unknown action %s. Should be from %s" % (action, (ACTION_RESTART, ACTION_STOP)))

    try:
        analysis = InsightsAnalysis.objects.get(analyzer_id)
    except InsightsAnalysis.DoesNotExist:
        return jsonify(ok=False, error="No Analysis found with id=%s" % analyzer_id)
    if action == ACTION_STOP:
        analysis.stop()
    if action == ACTION_RESTART:
        analysis.restart()
    return jsonify(ok=True)


@app.route('/analyzers', methods=['GET', 'POST'])
@login_required()
def insights(user):
    '''
    End point for launching analysis. Will create InsightsAnalsyis
    object on the fly and return an id.
    '''
    account_id = user.account.id
    application = user.account.selected_app
    if request.method == 'POST':
        data = request.json

        if 'account_id' not in data:
            data['account_id'] = account_id
        try:
            if data['metric_values'] == ['False'] or data['metric_values'] == ['True']:
                data['metric_values'] = ['true', 'false']
            data['analyzed_metric'] = data['analyzed_metric']
            data['created_at'] = datetime_to_timestamp_ms(datetime.now())
            data['user'] = user.id
            if not isinstance(data['metric_values'], list):
                return jsonify(ok=False, error="Expected metric values as a list")
            if not data['metric_values']:
                return jsonify(ok=True,
                               error='Missing required parameter metric values. Got value: %s' % data['metric_values'])
            if type(data['metric_values'][0]) not in (str, unicode):
                data['metric_values'] = [json.dumps(metric) for metric in data['metric_values']]

            analysis = InsightsAnalysis.objects.create(**data)
            analysis.start()
            return jsonify(ok=True, item=analysis.to_dict())
        except Exception, ex:
            import traceback
            traceback.print_exc()
            return jsonify(ok=False, error=str(ex))
    return jsonify(ok=True, list=[insight.to_dict() for
                                  insight in InsightsAnalysis.objects.find(account_id=account_id,
                                                                           application=application)])




