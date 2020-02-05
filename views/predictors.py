import re
from datetime import datetime
from copy import deepcopy
from flask import request, render_template

from solariat_bottle.app import app
from solariat.db import fields
from solariat.utils.timeslot import parse_datetime, datetime_to_timestamp_ms, timestamp_to_datetime
# from solariat_bottle.db.predictors.models.base import PredictorModel
from solariat.utils.timeslot import parse_date_interval
from solariat.utils.parsers.base_parser import BaseParser
from solariat_bottle.db.dynamic_classes import InfomartEvent
from solariat_bottle.db.predictors.models.linucb import LinUCBPredictorModel
from solariat_bottle.utils.decorators import login_required
from solariat_bottle.db.predictors.base_predictor import BasePredictor, CompositePredictor, \
    PredictorConfigurationConversion, TYPE_BOOLEAN, TYPE_NUMERIC, \
    NAME_BOOLEAN_PREDICTOR, NAME_NUMERIC_PREDICTOR, NAME_COMPOSITE_PREDICTOR
from solariat_bottle.db.predictors.operators import UNIQ_OPERATORS, DB_OPERATORS, OPERATOR_REGISTRY
from solariat_bottle.db.predictors.entities_registry import EntitiesRegistry
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.views import jsonify_response as jsonify
from solariat_bottle.views.base import BaseView, HttpResponse, AppException
from solariat_bottle.api.exceptions import ResourceDoesNotExist


MAX_FACET_CARDINALITY = 10


@app.route('/<any(predictors):page>')
@login_required()
def predictors_handler(user, page, filter_by=None, id=None):
    return render_template("/predictors/%s.html" % page,
                           user=user,
                           section=page,
                           top_level=page)


@app.route('/predictors/partials/<page>')
@login_required()
def predictors_partials_handler(user, page):
    return render_template("/predictors/partials/%s.html" % page,
                           user=user,
                           top_level=page)


@app.route('/predictors/json', methods=['GET', 'POST'])
@login_required()
def predictors_get_post(user):
    if request.method == 'GET':
        # return list of predictors with or without aggregate data

        created_query = {}
        from_date = parse_datetime(request.args.get('from'))
        to_date = parse_datetime(request.args.get('to'))

        if bool(from_date) != bool(to_date):
            return jsonify(ok=False, error="Both 'from' and 'to' required.")

        if from_date:
            created_query['created_at__gte'] = from_date
            created_query['created_at__lt'] = to_date

        predictors = [each for each in BasePredictor.objects.find_by_user(user, account_id=user.account.id, **created_query).sort(name=1)]
        predictors_json = []

        for predictor in predictors:
            json_dict = predictor.to_dict()
            if not json_dict['is_composite']:
                json_dict['training_data_length'] = predictor.train_set_length#predictor.training_data_class.objects(predictor_id=predictor.id).count()
                if predictor.reward_type == TYPE_BOOLEAN:
                    tp = fp = tn = fn = 0
                    auc_scores = []
                    for md in predictor.models:
                        tp += md.true_positives
                        fp += md.false_positives
                        fn += md.false_negatives
                        tn += md.true_negatives
                        if md.auc is not None:
                            auc_scores.append(md.auc)

                    precision = 0.0
                    if tp or fp:
                        precision = tp / float(tp + fp)

                    recall = 0.0
                    if tp or fn:
                        recall = tp / float(tp + fn)

                    json_dict['performance_metrics'] = "Precision: %.2f;  Recall: %.2f, TP: %s, FP: %s, FN: %s, TN: %s" % (
                        precision, recall, tp, fp, fn, tn)
                    json_dict['predictor_type'] = NAME_BOOLEAN_PREDICTOR
                    json_dict['avg_quality'] = dict(measure='AUC', score="%.2f" % (float(sum(auc_scores)) / max(len(auc_scores), 1)))
                elif predictor.reward_type == TYPE_NUMERIC:
                    total_n_scores = 0
                    total_avg_error = 0
                    rmse_scores = []
                    for md in predictor.models:
                        avg_error = md.avg_error
                        n_scores = md.nr_scores
                        if md.rmse is not None:
                            rmse_scores.append(md.rmse)

                        if n_scores:
                            total_avg_error = (total_avg_error * total_n_scores +
                                               avg_error * n_scores) / float(total_n_scores + n_scores)
                            total_n_scores += n_scores
                    json_dict['performance_metrics'] = "Avg Error: %.2f;  Number of Predictions: %s" % (total_avg_error,
                                                                                                      total_n_scores)
                    json_dict['predictor_type'] = NAME_NUMERIC_PREDICTOR
                    json_dict['avg_quality'] = dict(measure='RMSE', score="%.2f" % (float(sum(rmse_scores)) / max(len(rmse_scores), 1)))
            else:
                json_dict['predictor_type'] = NAME_COMPOSITE_PREDICTOR
            # json_dict.update(groupped.get(json_dict['id'], {}))
            last_run = predictor.get_last_run()
            json_dict.update(last_run=last_run and datetime_to_timestamp_ms(last_run))
            predictors_json.append(json_dict)
        return jsonify(ok=True, list=predictors_json)

    elif request.method == 'POST':
        # create new predictor
        data = request.json
        predictor_type = data.pop('predictor_type', None)
        data['account_id'] = user.account.id
        if predictor_type != BasePredictor.TYPE_COMPOSITE:
            #print data, predictor_type,  PREDICTORS_TYPE_TO_CLASS_MAP[predictor_type]
            try:
                native_attrs = {}
                for key, value in data.viewitems():
                    if key in BasePredictor.fields:
                        if isinstance(getattr(BasePredictor, key), fields.DateTimeField) and int(value):
                            value = datetime.utcfromtimestamp(value)

                        native_attrs[key] = value
                obj = BasePredictor.objects.create_by_user(user, **native_attrs)
            except Exception, err:
                LOGGER.exception('')
                return jsonify(ok=False, error=str(err))
            else:
                return jsonify(ok=True, obj=obj.to_dict())
        else:
            try:
                # These fields are not used by composite predictor
                data.pop('from_dt', None)
                data.pop('to_dt', None)
                data.pop('reward', None)
                obj = CompositePredictor.objects.create_by_user(user, **data)
            except Exception, err:
                LOGGER.exception('')
                return jsonify(ok=False, error=str(err))
            else:
                return jsonify(ok=True, obj=obj.to_dict())

#temporary stub
def get_class(account, dataset_name):
    return InfomartEvent

@app.route('/predictors/expressions/dataset_fields', methods=['POST'])
@login_required
def predictor_dataset_fields(user):
    data = request.json
    dataset_name = data['dataset_name']
    try:
        klass = get_class(user.account, dataset_name)
        dataset_fields = [{'name': k, 'type': v.__class__.__name__} for k, v in klass.fields.items()]
        dataset_name = klass.__name__
        return jsonify(ok=True, dataset_name=dataset_name, dataset_fields=dataset_fields)
    except Exception, ex:
        LOGGER.exception(ex)
        return jsonify(ok=False, error='Error occured: %s' % ex)


@app.route('/predictors/expressions/metadata', methods=['POST'])
@login_required
def predictor_expressions_metadata(user):
    data = request.json
    metadata = None
    for k in data.keys():
        assert k in ['collections', 'expression_type', 'suggestion_type'], "%r is not the valid request parameter" % k
    expression_type = data.get('expression_type')
    assert expression_type in ['feedback_model', 'reward', 'action_id'], "%r is not the valid expression type" % expression_type
    suggestion_type = data.get('suggestion_type')

    try:
        entities_registry = EntitiesRegistry()
        if expression_type == 'feedback_model':
            if suggestion_type and suggestion_type == 'operators':
                metadata = DB_OPERATORS.keys()
            else:
                metadata = entities_registry.get_all_entries()
        elif expression_type == 'reward':
            metadata = [dict(collection=collection,
                             fields=entities_registry.get_entry_fields(collection))
                        for collection in data.get('collections')]
        elif expression_type == 'action_id':
            metadata = UNIQ_OPERATORS.keys()
        return jsonify(ok=True, metadata=metadata)
    except Exception, ex:
        LOGGER.exception(ex)
        return jsonify(ok=False, error='Invalid expression parameters')


# get, post, or delete an predictor
@app.route('/predictors/<predictor_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def predictors_get_post_delete(user, predictor_id):
    predictor = BasePredictor.objects.get(account_id=user.account.id, id=predictor_id)

    if request.method == 'GET':
        # retrieve for editing
        return jsonify(ok=True, predictor=predictor.to_dict())

    elif request.method == 'POST':
        # update exiting predictor
        data = request.json
        if data.get('predictor_type') == BasePredictor.TYPE_COMPOSITE:
            predictor = CompositePredictor.objects.get(predictor_id)
        restricted_fields = {'_t', 'account_id', 'acl', 'predictor_num', 'counter', 'id', 'packed_clf',
                             'is_reward_editable', 'groups', 'models_count', 'predictors', 'predictor_names',
                             'is_composite', 'status', 'sync_status'}
        for k, v in data.items():
            if k in restricted_fields:
                continue
            if k not in predictor.fields:
                continue
            # assert k in predictor.fields, "%r is not an attribute of BasePredictor" % k
            if isinstance(getattr(predictor.__class__, k), fields.DateTimeField) and v is not None and str(v).isdigit():
                v = datetime.utcfromtimestamp(int(v))

            reset_done = False
            # Ignore any features with no label
            if k in ('context_features_schema', 'action_features_schema'):
                v = [val for val in v if val.get(predictor.FEAT_LABEL)]
                if not predictor.schema_equals(getattr(predictor, k), v) and not reset_done:
                    predictor.full_data_reset()
                    reset_done = True

            if k in ('metric', 'action_id_expression'):
                if getattr(predictor, k) != v and not reset_done:
                    predictor.full_data_reset()
                    reset_done = True

            setattr(predictor, k, v)
        try:
            predictor.save()
            return jsonify(ok=True, predictor=predictor.to_dict())
        except Exception, ex:
            LOGGER.exception('')
            return jsonify(ok=False, error=str(ex))

    elif request.method == 'DELETE':
        predictor.delete()
        return jsonify(ok=True)

@app.route('/predictors/<predictor_id>/search', methods=['GET', 'POST'])
@login_required
def predictors_data_search(user, predictor_id):
    predictor = BasePredictor.objects.get(account_id=user.account.id, id=predictor_id)
    params = request.json
    context_row = params.get('context_row')
    prefixes = dict()

    for key, val in context_row.iteritems():
        key = key.replace('ACT:', '').replace('CTX:', '')
        prefixes[key] = val
    context_row = prefixes

    context = dict()
    for key, val in context_row.iteritems():
        if key in predictor.context_feature_names:
            context[key] = val
    ActionClass = predictor.get_action_class()

    # select last trainted model instead of predictor.models[0]
    def srt(m1, m2):
        if m1.last_run == m2.last_run:
            return 0
        if m1.last_run is None:
            return 1
        elif m2.last_run is None:
            return -1
        else:
            return -1 if m1.last_run > m2.last_run else 1

    models = sorted([m for m in predictor.models if m.is_active], cmp=srt)
    if not models:
        return jsonify(ok=False, error="There are no active models.")
    current_model = predictor.select_model(models[0])

    actions = []
    agents_dict = {}
    for agent in ActionClass.objects():
        agent_data = agent.to_dict()
        agent_data['action_id'] = str(agent.id)
        for schema_feat in predictor.action_features_schema:
            f_type = schema_feat[predictor.FEAT_TYPE]
            expression = schema_feat[predictor.FEAT_EXPR]
            f_name = schema_feat[predictor.FEAT_LABEL]

            if f_type == predictor.TYPE_EXPR:
                expr_context = agent_data.keys()
                expr_context.extend(context.keys())
                expr_context.append('interaction_context')
                parser = BaseParser(expression, expr_context)
                try:
                    eval_context = agent_data
                    eval_context.update(context)
                    eval_context['interaction_context'] = deepcopy(eval_context)
                    value = parser.evaluate(eval_context)
                    agent_data[f_name] = value
                except Exception, ex:
                    print "Failed to evaluate expression. " + str(ex)
        actions.append(agent_data)
        agents_dict[str(agent.id)] = agent_data

    try:
        score_results = predictor.score(actions, context, model=current_model)
    except Exception as ex:
        LOGGER.error('ORIGIN ERROR:', exc_info=True)
        if 'not aligned:' in str(ex):
            return jsonify(ok=False, error="Model feature space has changed. "
                                           "Please retrain your model.")
        else:
            return jsonify(ok=False, error="Unexpected error: %s. In case you changed your model "
                                           "since last trained, please retrain." % str(ex))
    score_results = sorted(score_results, key=lambda x: -x[1])
    if 'error' in score_results:
        return jsonify(ok=False, error=score_results['error'])

    scored_agents = []
    selected_agent_id = None
    if score_results:
        selected_agent_id = score_results[0][0]
        for (agent_id, score, ucb_score) in score_results:
            base_agent_dict = agents_dict[str(agent_id)]
            base_agent_dict['match_score'] = "%.2f" % float(score)
            base_agent_dict['ucb_score'] = "%.2f" % float(ucb_score)
            if not selected_agent_id:
                selected_agent_id = agent_id
            scored_agents.append(base_agent_dict)
    if selected_agent_id:
        context_options = dict()
        for ctx_key in context:
            if 'ctx-' + ctx_key in predictor.cardinalities:
                n_options = predictor.cardinalities['ctx-' + ctx_key]
                if 0 < len(n_options) < 20:
                    context_options[ctx_key] = n_options
        return jsonify(ok=True, **{'selected_agent_id': str(selected_agent_id),
                                   'context': context,
                                   'context_options': context_options,
                                   'action_schema': predictor.action_feature_names,
                                   'context_schema': predictor.context_feature_names,
                                   'metric_name': predictor.metric,
                                   'considered_agents': scored_agents[:25] + scored_agents[-25:] if len(scored_agents) > 50 else scored_agents})
    else:
        return jsonify(ok=False, error='No agents available')

@app.route('/predictors/<predictor_id>/data/json', methods=['GET', 'POST'])
@login_required
def predictors_data_list(user, predictor_id):
    predictor = BasePredictor.objects.get(account_id=user.account.id, id=predictor_id)

    params = request.json
    limit = params.get('limit', 50)
    offset = params.get('offset', 0)

    if 'from' in params and 'to' in params:
        from_date = params.pop('from')
        to_date = params.pop('to') or from_date
        params['from_dt'], params['to_dt'] = parse_date_interval(from_date, to_date)

    data_list = predictor.training_data_class.objects.by_time_point(predictor.id,
                                                                    offset=offset,
                                                                    limit=limit,
                                                                    from_date=params.get('from_dt'),
                                                                    to_date=params.get('to_dt'),
                                                                    params=params)
    schema = []
    schema.extend([val[predictor.FEAT_LABEL] for val in predictor.context_features_schema])
    schema.extend([val[predictor.FEAT_LABEL] for val in predictor.action_features_schema])
    schema.append(predictor.metric)

    results = []
    for entry in data_list:
        row_entry = dict()
        for key, val in entry.context.iteritems():
            row_entry[key] = val if type(val) in (
                str, unicode, float, int, long, bool, list) else str(val)
        for key, val in entry.action.iteritems():
            row_entry[key] = val if type(val) in (
                str, unicode, float, int, long, bool, list) else str(val)
        row_entry[predictor.metric] = entry.reward

        for key in schema:
            if key not in row_entry:
                row_entry[key] = None

        results.append(row_entry)
    pagination_parameters = {
        'limit': params['limit'],
        'offset': params['offset'] + len(results),
        'more_data_available': len(data_list) == limit,
    }

    # This would come from predictor
    pagination_parameters['schema'] = schema

    return jsonify(ok=True, list=results, **pagination_parameters)

@app.route('/predictors/expressions/validate', methods=['POST'])
@login_required
def validate_predictor_expression(user):
    data = request.json
    _expression = data.get('expression')
    try:
        # first, check syntax of expression with Abstract Syntax Tree
        parser = BaseParser(_expression)
        parser.compile()
        # then check if operators are registered
        operators = re.findall(r'\w+(?=\()', _expression)  # returns words before parenthesis

        if operators:
            invalid_operators = filter(lambda x: x not in OPERATOR_REGISTRY.keys(), operators)
            if invalid_operators:
                return jsonify(ok=False, error='Invalid %s operator' % ', '.join(invalid_operators))
        # TODO: add more validation cases, in case of operator's parameters existence and data type etc.
        return jsonify(ok=True)
    except Exception, ex:
        LOGGER.exception('')
        return jsonify(ok=False, error=str(ex))


@app.route('/predictors/<id>/detail', methods=['GET'])
@login_required
def predictor_detail(user, id):
    predictor = BasePredictor.objects.get_by_user(user, account_id=user.account.id, id=id)
    data = predictor.to_dict()

    data['context_features'] = []
    data['action_features']  = []
    _get = request.args.get

    for_facets = request.args.get('facets')

    model = _get('model', _get('model_id'))

    context_features = predictor.context_features_schema
    action_features = predictor.action_features_schema

    if model:
        predictor.set_model(model)

    for feature in context_features:
        feature_dict = {
            'feature'       : feature[predictor.FEAT_LABEL],
            'type'          : feature[predictor.FEAT_TYPE],
            'description'   : ""
        }
        if for_facets:
            facet_values = get_facet_values(predictor.CTX_PREFIX + feature[predictor.FEAT_LABEL], predictor)
            if facet_values:
                feature_dict['values'] = facet_values
                data['context_features'].append(feature_dict)
        else:
            data['context_features'].append(feature_dict)

    for feature in action_features:
        feature_dict = {
            'feature'       : feature[predictor.FEAT_LABEL],
            'type'          : feature[predictor.FEAT_TYPE],
            'description'   : ""
        }
        if for_facets:
            facet_values = get_facet_values(predictor.ACT_PREFIX + feature[predictor.FEAT_LABEL], predictor)
            if facet_values:
                feature_dict['values'] = facet_values
                data['action_features'].append(feature_dict)
        else:
            data['action_features'].append(feature_dict)

    active_models = []
    models_data = []
    for model in predictor.model_class.objects(predictor=predictor):
        model_instance, model_data = predictor.as_model_and_data(model)
        models_data.append(model_data)
    data['models_data'] = models_data
    for model in data['models_data']:
        if predictor.model_class.objects.get(model.model_id).was_active:
            active_models.append(model)
        else:
            continue
    data['models_data'] = active_models
    return jsonify(**data)


def get_facet_values(feature, predictor):
    possible_values = predictor.cardinalities.get(feature, [])
    return possible_values if len(possible_values) <= MAX_FACET_CARDINALITY else []


# template for creating new predictor or editing exiting predictor
@app.route('/predictors/default-template')
@login_required
def get_predictor_types(user):
    res = PredictorConfigurationConversion.python_to_json(user.account.account_metadata.predictors_configuration.copy())
    res['types'] = [x['predictor_type'] for x in res.values()]
    res['reward_types'] = BasePredictor.reward_types()
    res['model_types'] = BasePredictor.model_types()
    return jsonify(ok=True, template=res)


# commands to reset and retrain from predictors list page
@app.route('/predictors/command/<action>/<predictor_id>', methods=['POST', 'GET'])
@login_required
def do_action_classifier(user, action, predictor_id):
    predictor = BasePredictor.objects.get_by_user(user, account_id=user.account.id, id=predictor_id)
    if action == 'reset':
        predictor.reset()
    elif action == 'retrain':
        from solariat_bottle.tasks import predictor_model_retrain_task
        feedback_count = predictor.train_set_length#.training_data_class.objects(predictor_id=predictor.id).count()
        if feedback_count > 0:
            # predictor_model_retrain_task(predictor)
            predictor_model_retrain_task.async(predictor)
        else:
            return jsonify(ok=False, error="No feedback data for predictor %s, nothing to train on." % predictor_id)
    elif action == 'generate_data':
        import json
        request_data = json.loads(request.data)
        if 'from_dt' in request_data:
            from_dt = timestamp_to_datetime(request_data['from_dt'])
            predictor.from_dt = from_dt
        if 'to_dt' in request_data:
            to_dt = timestamp_to_datetime(request_data['to_dt'])
            predictor.to_dt = to_dt
        predictor.save()
        from solariat_bottle.tasks import predictor_model_upsert_feedback_task
        predictor_model_upsert_feedback_task.async(predictor)
        return jsonify(ok=True, message="Started generation of predictor data.", status=predictor.STATUS_GENERATING)
        # predictor.retrain()
    elif action == 'purge_data':
        import json
        request_data = json.loads(request.data)
        if 'from_dt' in request_data:
            from_dt = timestamp_to_datetime(request_data['from_dt'])
            predictor.from_dt = from_dt
        if 'to_dt' in request_data:
            to_dt = timestamp_to_datetime(request_data['to_dt'])
            predictor.to_dt = to_dt
        predictor.save()
        removed_items = predictor.reset_training_data()
        return jsonify(ok=True, message="Removed %s total items" % removed_items, status=predictor.status)
    elif action == 'check_status':
        return jsonify(ok=True, message=predictor.info_message, status=predictor.status)
    else:
        assert "Only actions 'reset' and 'retrain' are supported. Given %r' % action"

    return jsonify(ok=True)


# template for creating new predictor or editing exiting predictor
@app.route('/predictors/rewards')
@login_required
def get_predictor_rewards(user):
    from solariat_nlp.bandit.models import REWARDS
    return jsonify(ok=True, rewards=REWARDS)


class PredictorModelView(BaseView):
    url_rules = [
        ('/predictors/<predictor_id>/models/<id_>', ['GET', 'POST', 'PUT', 'DELETE']),
        ('/predictors/<predictor_id>/models', ['GET', 'POST']),
        ('/predictors/<predictor_id>/models/<id_>/<action>', ['POST'])
    ]

    accepted_fields = ['context_features', 'action_features', 'weight', 'train_data_percentage',
                       'predictor_id', 'id', 'is_active', 'is_locked',
                       'display_name', 'description', 'model_type', 'min_samples_thresould',
                       'with_deactivated', 'with_inactive', 'hard', 'task_data', 'action']

    def dispatch_request(self, *args, **kwargs):
        try:
            user = kwargs['user']
            self.predictor = BasePredictor.objects.get_by_user(user,
                                                               account_id=user.account.id,
                                                               id=kwargs.pop('predictor_id'))
        except BasePredictor.DoesNotExist:
            raise ResourceDoesNotExist("Predictor not found")

        kwargs.update(self.get_parameters())
        return super(PredictorModelView, self).dispatch_request(*args, **kwargs)

    def get_parameters(self):
        data = super(PredictorModelView, self).get_parameters()
        return {name: value for name, value in data.iteritems() if name in self.accepted_fields}

    @property
    def model(self):
        return LinUCBPredictorModel

    def dispatch_action(self, model_id, action_name, **data):
        from solariat_bottle.tasks import predictor_model_retrain_task
        model = self.predictor.get_model(model_id)
        if not model:
            raise ResourceDoesNotExist('No found')

        resp = {"action": action_name}
        if action_name == 'reset':
            models = self.predictor.reset_model(model)
            resp['list'] = [model.to_json() for model in models]
        elif action_name == 'train':
            feedback_count = self.predictor.train_set_length#.training_data_class.objects(predictor_id=self.predictor.id).count()
            if feedback_count > 0:
                predictor_model_retrain_task.async(self.predictor, model=model)
                # predictor_model_retrain_task(self.predictor, model=model)
                # models = self.predictor.retrain(model=model, create_new_model_version=False)
                resp['list'] = [model.to_json() for model in self.predictor.models]
            else:
                raise AppException("Please generate data for predictor first")
        elif action_name == 'copy':
            self.predictor.clone_model(model)
            resp['list'] = [model.to_json() for model in self.predictor.models]
        elif action_name == 'retrain':
            feedback_count = self.predictor.train_set_length#.training_data_class.objects(predictor_id=self.predictor.id).count()
            if feedback_count > 0:
                predictor_model_retrain_task.async(self.predictor, model=model)
                # predictor_model_retrain_task(self.predictor, model=model)
                resp['list'] = [model.to_json() for model in self.predictor.models]
            else:
                raise AppException("Please generate data for predictor first")
        elif action_name == 'purgeFeedback':
            removed_items = self.predictor.training_data_class.objects.remove(id__ne=None)
            resp['message'] = "Removed %s items" % removed_items
        elif action_name == 'upsertFeedback':
            from solariat_bottle.tasks import predictor_model_upsert_feedback_task
            predictor_model_upsert_feedback_task.async(self.predictor)
            resp['list'] = [model.to_json() for model in self.predictor.models]
            # predictor.retrain()
        elif action_name == 'activate':
            next_state = model.state.try_change(action_name)
            self.predictor.is_locked = True
            self.predictor.save()
            if next_state:
                model.update(state=next_state)
                model.was_active = True
                model.save()
                self.predictor.add_model(model)
        elif action_name == 'deactivate':
            next_state = model.state.try_change(action_name)
            if next_state:
                model.update(state=next_state)
                # setting status to INACTIVE **not** required because del_model does does so.
                ok, error = self.predictor.del_model(model)
                if not ok:
                    raise AppException(error)
        return HttpResponse(resp)

    def post(self, **data):
        predictor = self.predictor

        if 'id_' in data:
            data['id'] = data.pop('id_')
        if 'action' in data:
            if 'id' not in data:
                raise AppException("No model id was provided for action=%s" % data['action'],
                                   http_code=400)
            return self.dispatch_action(data['id'], data['action'])

        kwargs = data.copy()
        ctx_features = [feat[BasePredictor.FEAT_LABEL] if isinstance(feat, dict) else feat for feat in
                        data['context_features']]
        act_features = [feat[BasePredictor.FEAT_LABEL] if isinstance(feat, dict) else feat for feat in
                        data['action_features']]
        kwargs['context_features'] = [x for x in predictor.context_features_schema
                                      if x[BasePredictor.FEAT_LABEL] in ctx_features]
        kwargs['action_features'] = [x for x in predictor.action_features_schema
                                     if x[BasePredictor.FEAT_LABEL] in act_features]

        print kwargs
        instance, created = self.predictor.create_update_model(kwargs)
        return HttpResponse(instance, status=201 if created else 200)

    def _with_stats(self, models):
        models_json = [item.to_json() for item in models]
        for item in models_json:
            item['training_data_length'] = item['n_rows'] #self.predictor.training_data_class.objects.count(
                #predictor_id=item['predictor'])
        # groupped_stats = aggregate_predictor_stats(self.predictor.id, None, None, by_models=True)
        default_stats = {}  # groupped_stats.get('None', {})
        return models_json

    def get(self, id_=None, **data):
        if id_:
            instance = self.predictor.get_model(dict(id=id_))
            if instance:
                res = instance.to_dict()
                res['description'] = instance.description
                res['reward'] = instance.reward
                res['action_features'] = instance.action_features
                res['context_features'] = instance.context_features
                res['min_samples_thresould'] = instance.min_samples_thresould
                res['is_locked'] = instance.state.is_locked
                res = {k: v for k, v in res.items() if k in self.accepted_fields}
                return res
            else:
                raise ResourceDoesNotExist('Not found')
        else:
            if data.get('with_inactive', data.get('with_deactivated')):
                result = self.model.objects(predictor=self.predictor)[:]
            else:
                result = self.model.objects(id__in=[x.model_id for x in self.predictor.models_data])
        return self._with_stats(result)

    def put(self, id_, **data):
        try:
            model = LinUCBPredictorModel.objects.get(id_)
        except LinUCBPredictorModel.DoesNotExist:
            return jsonify(ok=False, error="No model found for id=%s." % id_)

        if model not in self.predictor.models:
            return jsonify(ok=False, error='Model %s not part of models for predictor %s' % (model, self.predictor))

        for attr_name, attr_value in data.iteritems():
            if attr_name in model.fields.keys() or (not model.is_locked and attr_name in {'action_features', 'context_features'}):
                setattr(model, attr_name, attr_value)
        model.save()

        return model.to_json()

    def delete(self, id_, hard=False):
        is_ok, error_message = self.predictor.del_model(dict(id=id_), hard=hard)
        if not is_ok:
            return dict(ok=False, error=error_message)
        return dict(ok=True)


PredictorModelView.register(app)
