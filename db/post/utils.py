'''
Any utility functions related strictly to posts.
'''
from solariat_bottle.db.post.nps      import NPSOutcome
from solariat_bottle.db.post.twitter  import TwitterPost
from solariat_bottle.db.post.facebook import FacebookPost
from solariat_bottle.db.post.chat     import ChatPost
from solariat_bottle.db.post.email    import EmailPost
from solariat_bottle.db.post.base     import Post
from solariat_bottle.db.post.voice import VoicePost
from solariat_bottle.tasks            import create_post
from solariat_bottle.db.post.faq_query import FAQQueryEvent
from solariat_bottle.db.post.web_clicks import WebClick
from solariat_bottle.db.post.branch import BranchEvent
from solariat_bottle.db.dynamic_classes import InfomartEvent, RevenueEvent, NPSEvent
from solariat_bottle.db.events.event_type import BaseEventType
from solariat_bottle.db.user import get_user


class VolumeThresholdError(Exception):
    pass

POST_PLATFORM_MAP = {
    'Twitter'  : TwitterPost,
    'Facebook' : FacebookPost,
    'VOC'      : NPSOutcome,
    'Chat'     : ChatPost,
    'Email'    : EmailPost,
    'Web'      : WebClick,
    'FAQ'      : FAQQueryEvent,
    'Branch'   : BranchEvent,
    'Voice'    : VoicePost,
    'Imart'    : InfomartEvent,
    'Revenue'  : RevenueEvent,
    'NPS'      : NPSEvent,
     None      : Post
}


def get_platform_class(platform, event_type=None):
    # TODO: make platform name static!
    platform = platform or ''
    klass = POST_PLATFORM_MAP.get(platform.title())
    klass = klass or POST_PLATFORM_MAP.get(platform.upper())

    # search for a proper dynamic event class
    if not klass and event_type:
        if not isinstance(event_type, BaseEventType):
            user = get_user()
            event_type = BaseEventType.find_one_by_user(user, platform=platform, name=event_type)
        klass = event_type.get_data_class() if event_type else None

    return klass or Post


def factory_by_user(user, sync=False, **kw):
    """ Creates a proper platform Post given a user and post components.

        Notice: this is just a thin wrapper for a sync call of the create_post task.

        Special args:

        sync - <bool:default=False> forces synchronous postprocessing
    """
    return create_post.sync(user, sync=sync, **kw)

# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0
