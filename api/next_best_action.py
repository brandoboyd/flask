# from solariat_bottle.api.base import BaseAPIView, api_request
# from solariat_bottle.db.next_best_action.actions import Action
# from solariat_bottle.db.post.web_clicks import WebClick
# from solariat_bottle.db.post.chat import ChatPost
# from solariat_bottle.db.agent_matching.profiles.customer_profile import CustomerProfile
# # from solariat_bottle.db.next_best_action.controller import NextBestActionEngine
#
#
# class NextBestActionAPIView(BaseAPIView):
#
#     endpoint = 'next_best_action'
#     commands = ['feedback', "query"]
#
#     MOCK_ACTIONS = [{'id': 1, 'name' :"Offer chat with: 'Hey buddy, you need any help?'"},
#                     {'id': 2, 'name' :"Offer chat with: 'Sooooomewhere, over the rainbow, we'll finish the demo"},
#                     {'id': 3, 'name' : "Popup tooltip: You seem lost, here's some guidance!"},
#                     {'id': 4, 'name' : "Do nothing"}]
#
#     @classmethod
#     def register(cls, app):
#         """ Chat API allows for extra commands, like 'summary' and 'session' """
#         view_func = cls.as_view(cls.endpoint)
#
#         url = cls.get_api_url('<command>')
#         app.add_url_rule(url, view_func=view_func, methods=["POST", ])
#
#     def post(self, command=None, *args, **kwargs):
#         if command in self.commands:
#             meth = getattr(self, '_' + command)
#             return meth(*args, **kwargs)
#         return super(NextBestActionAPIView, self).post(*args, **kwargs)
#
#     @api_request
#     def _feedback(self, user, *args, **kwargs):
#         assert 'action_id' in kwargs and 'event_id' in kwargs and 'score' in kwargs and 'customer_id' in kwargs, \
#         "Required fields are 'action_id', 'event_id', 'customer_id', and 'score'"
#         # This would be feedback loop
#         try:
#             if kwargs['event_type'] == 'chat':
#                 event = ChatPost.objects.get(kwargs['event_id'])
#             elif kwargs['event_type'] == 'web':
#                 event = WebClick.objects.get(kwargs['event_id'])
#         except ChatPost.DoesNotExist:
#             return dict(ok=False, error="No event with id = %s" % kwargs['event_id'])
#         try:
#             customer = CustomerProfile.objects.get(kwargs['customer_id'])
#         except CustomerProfile.DoesNotExist:
#             return dict(ok=False, error="No customer with id = %s" % kwargs['customer_id'])
#
#         reward = kwargs.get('score')
#         action = Action.objects.get(kwargs['action_id'])
#
#         classifier = NextBestActionEngine.upsert(account_id=customer.account_id)
#         model = kwargs.get('model', kwargs.get('model_id'))
#         return classifier.feedback(event, customer, action, reward, model=model)
#
#     @api_request
#     def _query(self, user, *args, **kwargs):
#         assert kwargs.get('event_id') and kwargs.get('event_type') and kwargs.get('customer_id'), \
#             "Required fields are 'customer_id', 'event_id' and 'event_type', got %s" % kwargs
#         try:
#             if kwargs['event_type'] == 'chat':
#                 event = ChatPost.objects.get(kwargs['event_id'])
#             elif kwargs['event_type'] == 'web':
#                 event = WebClick.objects.get(kwargs['event_id'])
#         except ChatPost.DoesNotExist:
#             return dict(ok=False, error="No event with id = %s" % kwargs['event_id'])
#         try:
#             customer = CustomerProfile.objects.get(kwargs['customer_id'])
#         except CustomerProfile.DoesNotExist:
#             return dict(ok=False, error="No customer with id = %s" % kwargs['customer_id'])
#
#         classifier = NextBestActionEngine.upsert(account_id=customer.account_id)
#         model = kwargs.get('model', kwargs.get('model_id'))
#         return classifier.search(event, customer, model=model)
#
