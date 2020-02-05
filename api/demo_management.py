from solariat_bottle.api.base import BaseAPIView, api_request


class DemoManagementAPIView(BaseAPIView):

    endpoint = 'demo'
    commands = ['reset', "reload", 'save']

    @classmethod
    def register(cls, app):
        """ Chat API allows for extra commands, like 'summary' and 'session' """
        view_func = cls.as_view(cls.endpoint)

        url = cls.get_api_url('<command>')
        app.add_url_rule(url, view_func=view_func, methods=["POST", ])

    def post(self, command=None, *args, **kwargs):
        if command in self.commands:
            meth = getattr(self, '_' + command)
            return meth(*args, **kwargs)
        return super(DemoManagementAPIView, self).post(*args, **kwargs)

    @api_request
    def _reset(self, user, *args, **kwargs):
        from solariat_bottle.db.predictors.abc_predictor import ABCPredictor
        for predictor in ABCPredictor.objects():
            predictor.packed_clf = None
            predictor.save()

        from solariat_bottle.db.predictors.base_predictor import BasePredictor
        for predictor in BasePredictor.objects.find(name__in=['Agent Matching Predictor',
                                                        'Alert Supervisor Decision',
                                                        'Chat Engagement Decision']):
            predictor.reset_fresh()
        # This would be feedback loop
        return dict(ok=True)

    @api_request
    def _reload(self, user, *args, **kwargs):
        from solariat_bottle.scripts.data_load.demo_helpers.save_load_db import load_db
        load_db()
        return dict(ok=True)

    @api_request
    def _save(self, user, *args, **kwargs):
        from solariat_bottle.scripts.data_load.demo_helpers.save_load_db import save_db
        from solariat_bottle.app import app
        app.logger.info("Saving DB State...")
        save_db()
        app.logger.info("Save Completed Successfully...")
        return dict(ok=True)
