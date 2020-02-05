from solariat.metacls import Memoized
from solariat_bottle.tasks.twitter import twitter_stream_event_handler
from solariat_bottle.daemons.helpers import PostCreator, FeedApiPostCreator, KafkaFeedApiPostCreator, KafkaPostCreator


class KafkaPostCreatorMemo(object):
    __metaclass__ = Memoized

    def __init__(self, username, kwargs):
        creator_classname = kwargs.pop('post_creator', PostCreator.__name__)
        if creator_classname == PostCreator.__name__:
            self.instance = KafkaPostCreator(username, kwargs)
        elif creator_classname == FeedApiPostCreator.__name__:
            self.instance = KafkaFeedApiPostCreator(username, kwargs)
        else:
            raise AttributeError("Unknown PostCreator class %s" % creator_classname)

    def run(self, task):
        return self.instance.run(task)


class KafkaHandler(object):
    def __init__(self, options):
        self.kwargs = {}
        self.username = None

        for param in ['user_agent', 'url', 'password']:
            val = getattr(options, param, None)
            if val:
                self.kwargs[param] = val
        if getattr(options, 'username', None):
            self.username = options.username

    def handle_create_post(self, task, username, kwargs):
        # override incoming kwargs with values from config
        kwargs.update(self.kwargs)
        if self.username:
            username = self.username

        post_creator = KafkaPostCreatorMemo(username, kwargs)
        post_creator.run(task)

    def on_event_handler(self, event, stream_data):
        twitter_stream_event_handler(event, stream_data)

