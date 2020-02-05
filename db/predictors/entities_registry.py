class EntitiesRegistry(object):

    def __init__(self):
        # ENTRIES (each import refer to the current file through factory.py, so importing inside of method)
        from solariat_bottle.db.post.facebook import FacebookPost
        from solariat_bottle.db.post.twitter import TwitterPost
        from solariat_bottle.db.dynamic_classes import RevenueEvent, InfomartEvent, NPSEvent
        from solariat_bottle.db.predictors.base_predictor import PredictorTrainingData

        self.models = {
            'FacebookPost': FacebookPost,
            'TwitterPost': TwitterPost,
            'InfomartEvent': InfomartEvent,
            'RevenueEvent': RevenueEvent,
            'PredictorTrainingData': PredictorTrainingData
        }

    def get_all_entries(self):
        all_entries = self.models.keys()
        return all_entries

    def generate_expression_context(self, predictor, expression):
        """Need to register all the entries that might be used for context of expressions
           For example, from_ts=None, to_ts=None,
           'collect(InfomartEvent)' -> 'collect(predictor, from_ts, to_ts, InfomartEvent)'
           'int(123.3)' -> 'int(123.3)'
        """
        expression_context = dict()

        if any(word in expression for word in ['union(', 'collect(']):
            expression_context.update({
                'predictor': predictor,
                'from_dt': predictor.from_dt,
                'to_dt': predictor.to_dt,
            })
            expression_context.update(self.models)
            expression = expression.replace('(', '(predictor, from_dt, to_dt, ')

        return dict(expression=expression, context=expression_context)

    def get_entry_fields(self, entry):
        _entry_cls = self.models[entry]()
        return _entry_cls.field_names

