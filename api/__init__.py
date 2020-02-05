
def register_views():
    from solariat_bottle.app import app
    from solariat_bottle.api.agents import AgentsAPIView
    from solariat_bottle.api.posts import PostAPIView
    from solariat_bottle.api.authtokens import AuthTokenAPIView
    from solariat_bottle.api.smarttags import SmartTagAPIView
    from solariat_bottle.api.channels import ChannelAPIView
    from solariat_bottle.api.channelcommands import ChannelActivateAPIView, ChannelDeleteAPIView, ChannelSuspendAPIView
    from solariat_bottle.api.classifiers import ClassifiersAPIView
    from solariat_bottle.api.faq import FAQAPIView
    from solariat_bottle.api.feedbackcommands import (AddTagAPIView, AcceptPostAPIView, RejectPostAPIView,
                                                      RemoveTagAPIView)
    from solariat_bottle.api.historics import HistoricsAPIView
    from solariat_bottle.api.analyzer import AnalyzerAPIView
    from solariat_bottle.api.tagger import TaggerAPIView
    from solariat_bottle.api.queue import QueueAPIView
    from solariat_bottle.api.rpc import RPCAPIView
    from solariat_bottle.api.nps import NpsView
    from solariat_bottle.api.events import EventAPIView
    from solariat_bottle.api.customers import CustomersAPIView
    from solariat_bottle.api.chat import ChatAPIView
    from solariat_bottle.api.demo_management import DemoManagementAPIView
    from solariat_bottle.api.predictors import PredictorsAPIView
    from solariat_bottle.api.stubs.facebook import FacebookStub
    from solariat_bottle.api.backdoor import BackdoorAPIView
    from solariat_bottle.api.voc import VocView
    from solariat_bottle.api.score_log import ScoreLogView


    API_VIEWS = [AgentsAPIView,
                 AuthTokenAPIView,
                 PostAPIView,
                 PredictorsAPIView,
                 SmartTagAPIView,
                 ChannelAPIView,
                 ChannelActivateAPIView,
                 ChannelDeleteAPIView,
                 ChannelSuspendAPIView,
                 ClassifiersAPIView,
                 HistoricsAPIView,
                 AddTagAPIView,
                 AcceptPostAPIView,
                 RejectPostAPIView,
                 RemoveTagAPIView,
                 QueueAPIView,
                 RPCAPIView,
                 TaggerAPIView,
                 AnalyzerAPIView,
                 FAQAPIView,
                 EventAPIView,
                 CustomersAPIView,
                 ChatAPIView,
                 DemoManagementAPIView,
                 FacebookStub,
                 NpsView,
                 BackdoorAPIView,
                 VocView,
                 ScoreLogView
                 ]

    for view in API_VIEWS:
        view.register(app)
