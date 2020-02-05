from datetime import datetime
from solariat.exc.base import AppException
import solariat_bottle.api.exceptions as exc
from solariat_bottle.settings import LOGGER
from solariat_bottle.api.base import ModelAPIView, api_request
from solariat_bottle.db.predictors.factory import create_agent_matching_predictor_for_testing
from solariat_bottle.db.predictors.base_predictor import BasePredictor
from solariat.utils.parsers.base_parser import BaseParser
from solariat_bottle.utils.views import parse_bool

BATCH_KEY = 'batch_data'

KEY_CONTEXT = 'context'
KEY_ACTION = 'action'
KEY_ACTIONS = 'actions'
KEY_ACTION_FILTERS = 'action_filters'
KEY_ACTION_ID = 'action_id'
KEY_MODEL = 'model_id'
KEY_REWARD = 'reward'
KEY_P_SCORE = 'p_score'

ERR_MSG_MISSING_FIELD = "Missing required field %s"
ERR_MSG_INVALID_JSON = "Invalid value for field '%s'. Expecting JSON, got %s instead"
ERR_MSG_MISSING_ACTION_ID = "Missing required field 'action_id' for action JSON=%s"
ERR_MSG_INVALID_ACTIONS = "Invalid value for parameter='actions'. Expecting a list of JSON."
ERR_MSG_NO_PREDICTOR = "No predictor found with id=%s"
ERR_MSG_NO_ACCESS = "You do not have access to predictor with id=%s."
ERR_MSG_NO_PREDICTOR_ID = "You need to provide a predictor id for scoring or feedback commands."


class PredictorsAPIView(ModelAPIView):
    model = BasePredictor
    endpoint = 'predictors'
    commands = ['score', 'feedback', 'testpredictor', 'reset']

    _parsers_cache = dict()

    @classmethod
    def register(cls, app):
        """ Queue API allows for extra commands, like 'fetch' and 'confirm' """
        url = cls.get_api_url()
        view_func = cls.as_view(cls.endpoint)
        app.add_url_rule(url, view_func=view_func, methods=['GET',])
        app.add_url_rule(cls.get_api_url('<_id>'),
                         view_func=view_func,
                         methods=['GET'])

        url = cls.get_api_url('<predictor_id>/<command>')
        app.add_url_rule(url, view_func=view_func, methods=["POST", "GET"])

    @classmethod
    def _format_doc(cls, item):
        """ Format a post ready to be JSONified. API spec:

                id [string]: the id of the predictor
                type [string]: the type of the predictor
                description [string]: any description you added to the predictor
                uri [string]: the URL for this specific predictor
        """
        return dict(name=item.name,
                    type=item.predictor_type,
                    id=str(item.id),
                    uri=cls._resource_uri(item))

    def get_validated_context(self, predictor, kwargs):
        """
        Validate context and convert its keys.
        Keys in context are case insensitive, all the keys in the context dictionary are converted into an upper case
        """
        context_lower_mappings = dict()
        for ctx_key in predictor.context_feature_names:
            context_lower_mappings[ctx_key.lower()] = ctx_key
        if KEY_CONTEXT not in kwargs:
            raise exc.InvalidParameterConfiguration(ERR_MSG_MISSING_FIELD % KEY_CONTEXT)
        context = kwargs[KEY_CONTEXT]
        if not isinstance(context, dict):
            raise exc.InvalidParameterConfiguration(ERR_MSG_INVALID_JSON % (KEY_CONTEXT, context))
        updated_context = {}
        for k, v in context.iteritems():
            if k.lower() not in context_lower_mappings:
                continue
            updated_context[context_lower_mappings[k.lower()]] = v
        return updated_context

    def validate_action(self, action_json):
        if not isinstance(action_json, dict):
            raise exc.InvalidParameterConfiguration(ERR_MSG_INVALID_JSON % (KEY_ACTION, action_json))
        if KEY_ACTION_ID not in action_json:
            raise exc.InvalidParameterConfiguration(ERR_MSG_MISSING_ACTION_ID % action_json)

    def score(self, user, predictor, *args, **kwargs):
        result = self._score(user, predictor, *args, **kwargs)
        if kwargs.get("format_as_map", False):
            agent_score_map = {}
            for item in result['list']:
                agent_score_map[item['native_id']] = item['score']
            result['list'] = agent_score_map
        return result

    def _score(self, user, predictor, *args, **kwargs):
        if predictor.account_id != user.account.id:
            raise exc.InvalidParameterConfiguration(ERR_MSG_NO_ACCESS % predictor.id)
        if KEY_ACTIONS not in kwargs and KEY_ACTION_FILTERS not in kwargs:
            raise exc.InvalidParameterConfiguration(ERR_MSG_MISSING_FIELD % (KEY_ACTIONS + ' or ' + KEY_ACTION_FILTERS))
        if KEY_ACTIONS in kwargs:
            unprocessed_actions = kwargs[KEY_ACTIONS]
            if not isinstance(unprocessed_actions, list):
                raise exc.InvalidParameterConfiguration()
            for action in unprocessed_actions:
                self.validate_action(action)
        else:
            filter_query = kwargs[KEY_ACTION_FILTERS]
            query, _ = predictor.construct_filter_query(filter_query,
                                                        context=predictor.get_action_class().fields.keys())
            # query['account_id'] = predictor.account_id
            actions = predictor.get_action_class().objects.coll.find(query)

            unprocessed_actions = []
            for action in actions:
                attached_data = action
                if predictor.action_id_expression in action:
                    attached_data[KEY_ACTION_ID] = action[predictor.action_id_expression]
                else:
                    attached_data[KEY_ACTION_ID] = str(action['_id'])
                unprocessed_actions.append(attached_data)

            for action in unprocessed_actions:
                self.validate_action(action)

        action_lower_mappings = dict()
        for act_key in predictor.action_feature_names:
            action_lower_mappings[act_key.lower()] = act_key
        processed_actions = []
        action_id_mapping = dict()
        for action in unprocessed_actions:
            processed_action = {KEY_ACTION_ID: action[KEY_ACTION_ID]}
            action_id_mapping[action[KEY_ACTION_ID]] = action
            for k, v in action.iteritems():
                if k.lower() not in action_lower_mappings:
                    continue
                processed_action[action_lower_mappings[k.lower()]] = v
            processed_actions.append(processed_action)

        context = self.get_validated_context(predictor, kwargs)
        #import pdb; pdb.set_trace()

        score_start = datetime.utcnow()
        try:
            results = predictor.score(processed_actions, context)
        except AppException, ex:
            return dict(ok=False, error=str(ex))
        formatted_results = []

        score_expression = predictor.score_expression
        if score_expression:
            if str(predictor.id) in self._parsers_cache:
                parser = self._parsers_cache[str(predictor.id)]
            else:
                parser = BaseParser(score_expression, [])
                self._parsers_cache[str(predictor.id)] = parser

        warning = None
        for (action_id, score, ucb_score) in results:
            if score_expression:
                action_context = action_id_mapping[action_id]
                action_context.update(context)
                action_context[KEY_P_SCORE] = score

                try:
                    score = parser.evaluate(action_context)
                    ucb_score = score
                except Exception, ex:
                    warning = "Failed to compute predicted score based on defined expression %s. Error: %s" % (score_expression,
                                                                                                               ex)

            base_agent_dict = dict(id=action_id)
            base_agent_dict['estimated_reward'] = float(score)
            base_agent_dict['score'] = round(ucb_score, 2)
            base_agent_dict['native_id'] = action_id
            # try:
            #     entity = predictor.get_action_class().objects.get(action_id)
            #     base_agent_dict['native_id'] = entity.data.get("employeeId")
            # except predictor.get_action_class().DoesNotExist:
            #     base_agent_dict['native_id'] = None
            formatted_results.append(base_agent_dict)

        if score_expression:
            formatted_results = sorted(formatted_results, key=lambda x: -x['score'])

        latency = (datetime.utcnow() - score_start).total_seconds()
        result = {'list': formatted_results,
                  'predictor': predictor.name,
                  'predictor_id': predictor.id,
                  'model': predictor.model.display_name if predictor.model else 'Composite',
                  'model_id': predictor.model.id if predictor.model else None,
                  'latency': latency}
        if warning:
            result['warning'] = warning

        return result

    def feedback(self, user, predictor, *args, **kwargs):
        if predictor.account_id != user.account.id:
            raise exc.InvalidParameterConfiguration(ERR_MSG_NO_ACCESS % predictor.id)
        context = self.get_validated_context(predictor, kwargs)
        if KEY_ACTION not in kwargs:
            raise exc.InvalidParameterConfiguration(ERR_MSG_MISSING_FIELD % KEY_ACTION)

        if KEY_ACTION_ID in kwargs[KEY_ACTION] and len(kwargs[KEY_ACTION]) == 1:
            # We only got id of action, check if present in db
            try:
                action = predictor.get_action_class().objects.get(kwargs[KEY_ACTION][KEY_ACTION_ID])
            except predictor.get_action_class().DoesNotExist:
                action = None
            # lets try to get action by native_id
            try:
                action = predictor.get_action_class().objects.get(native_id=kwargs[KEY_ACTION][KEY_ACTION_ID])
            except predictor.get_action_class().DoesNotExist:
                pass
            # if there is an action lets use it
            if action is not None:
                attached_data = action.data or {}
                kwargs[KEY_ACTION].update(attached_data)
                # We didn't find it, nothing to do

        self.validate_action(kwargs[KEY_ACTION])
        model = kwargs.get(KEY_MODEL, None)

        if KEY_REWARD not in kwargs:
            raise exc.InvalidParameterConfiguration(ERR_MSG_MISSING_FIELD % KEY_REWARD)

        score_start = datetime.utcnow()
        skip_training = parse_bool(kwargs.get('skip_training', True))
        predictor.feedback(context, kwargs[KEY_ACTION], float(kwargs['reward']), model=model, skip_training=skip_training)
        latency = (datetime.utcnow() - score_start).total_seconds()
        return {'latency': latency}

    @api_request
    def post(self, user, predictor_id=None, command=None, *args, **kwargs):
        if predictor_id is None:
            return dict(ok=False, error=ERR_MSG_NO_PREDICTOR_ID)
        try:
            predictors = BasePredictor.objects(id=predictor_id, account_id=str(user.account.id))[:]
            if len(predictors) == 0:
                predictor = None
            elif len(predictors) == 1:
                predictor = predictors[0]
            else:
                return dict(ok=False, error="Expecting only one predictor or no predictors, got: %s" % predictors)
        except BasePredictor.DoesNotExist:
            predictor = None
        if command != 'testpredictor' and predictor is None:
            return dict(ok=False, error=ERR_MSG_NO_PREDICTOR % str(predictor_id))
        if command in self.commands:
            if command == 'score':
                return self.score(user, predictor, *args, **kwargs)
            if command == 'feedback':
                return self.feedback(user, predictor, *args, **kwargs)
            if command == 'testpredictor':
                return self.testpredictor(user, predictor, predictor_id, *args, **kwargs)
            if command == 'reset':
                return self.reset(user, predictor, *args, **kwargs)
        return self._post(*args, **kwargs)

    @api_request
    def get(self, user, **kwargs):
        account_id = user.account.id
        if 'id' in kwargs or '_id' in kwargs:
            predictor_id = kwargs.get('id', kwargs.get('_id'))
            try:
                predictor = BasePredictor.objects.get(predictor_id)
                if predictor.account_id != account_id:
                    raise exc.InvalidParameterConfiguration(ERR_MSG_NO_ACCESS % predictor_id)
                return dict(ok=True, item=self._format_doc(predictor))
            except BasePredictor.DoesNotExist:
                raise exc.InvalidParameterConfiguration(ERR_MSG_NO_PREDICTOR % predictor_id)
        kwargs['account_id'] = account_id
        return dict(ok=True, list=[self._format_doc(ag) for ag in BasePredictor.objects.find(**kwargs)])

    def testpredictor(self, user, predictor, predictor_id, **kwargs):
        lookup_map = kwargs['lookup_map']
        LOGGER.info("CREATING PREDICTOR: type: %s; value: %s" % (type(lookup_map), lookup_map))
        if not predictor:
            predictor = create_agent_matching_predictor_for_testing(user.account.id, predictor_id)
        predictor.lookup_map = {str([agent_id, sorted([(item[0].upper(), item[1]) for item in context.items()])]): score
                                for ((agent_id, context), score) in lookup_map}
        _, context = lookup_map[0][0]
        predictor.context_feature_names = [item.upper() for item in context.keys()]
        predictor.name = kwargs.get("name", "TestPredictor")
        predictor.save()
        return {"status": "ok", "data": {"predictor_id": str(predictor.id)}}

    def reset(self, user, predictor, **kwargs):
        try:
            predictor.reset()
            return {"status": "ok"}
        except:
            return {"status": "error"}



