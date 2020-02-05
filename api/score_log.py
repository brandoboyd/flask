from solariat.db.mongo import get_connection
from .base import BaseAPIView, api_request
from solariat_bottle.db.predictors.base_predictor import BasePredictor


DEFAULT_COLLECTION = "scorelog_default_nopredictor"
KEY_PREDICTOR = "prrPredictor"


class ScoreLogView(BaseAPIView):

    endpoint = 'score_log'

    @api_request
    def get(self, user, **kwargs):
        db = get_connection()
        predictor_name = kwargs.get(KEY_PREDICTOR)
        if predictor_name:
            warning = ""
            try:
                bp = BasePredictor.objects.get(name=predictor_name, account_id=user.account.id)
            except BasePredictor.DoesNotExist:
                return dict(ok=False, error="No predictor found for name=%s in account %s" % (predictor_name,
                                                                                              user.account.name))
            collection = db[bp.log_collection_name()]
        else:
            collection = db[DEFAULT_COLLECTION]
            warning = "No predictor id was provided. Searching in default scorelog collection."
        docs = [doc for doc in collection.find(kwargs)]
        [doc.pop('_id') for doc in docs]
        result = dict(ok=True, list=docs)
        if warning:
            result['warning'] = warning
        return result

    @api_request
    def post(self, user, **kwargs):
        db = get_connection()
        predictor_name = kwargs.get(KEY_PREDICTOR)
        if predictor_name:
            warning = ""
            try:
                bp = BasePredictor.objects.get(name=predictor_name, account_id=user.account.id)
            except BasePredictor.DoesNotExist:
                return dict(ok=False, error="No predictor found for name=%s in account %s" % (predictor_name,
                                                                                              user.account.name))
            collection = db[bp.log_collection_name()]
        else:
            collection = db[DEFAULT_COLLECTION]
            warning = "No predictor id was provided. Logged to default scorelog collection."
        result = collection.insert(kwargs)
        result = dict(ok=True, message="Log insert completed. Result: %s" % result)
        if warning:
            result['warning'] = warning
        return result