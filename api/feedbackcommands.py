from solariat_bottle.api.base import ModelAPIView, api_request
from solariat_bottle.api.posts import PostAPIView
import solariat_bottle.api.exceptions as exc

from solariat.utils.timeslot import now
from solariat_bottle.db.api_feedback_command import FeedbackAPICommand
from solariat_bottle.db.channel.base import Channel, SmartTagChannel
from solariat_bottle.db.post.base import Post
from solariat_bottle.db.post.utils import factory_by_user


class FeedbackMixin():
    """
    Endpoint to provide feedback regarding Post object scores for classifiers like SmartTags or Actionability


    Parameters:
            :param token: <Required> - A valid user access token
            :param channel_id: <Required> - The channel id or smart tag id for which we are providing feedback
            :param content: <option> - The content for which you want to provide feedback. If passed in instead
                                       of `post_id` a new Post instance will be created. Either this or `post_id`
                                       if required.
            :param post_id: <optional> - The post_id for which you want to provide feedback. If passed in instead
                                         if `content` an existing Post insance will be used. This takes prioirty
                                         over `content` if both are passed in. At least one needs to be passed in.

        Output:
            Identical to the one returned by /api/v2.0/posts

        Sample requests:
            curl http://staging.socialoptimizr.com/api/v2.0/add_tag
            curl http://staging.socialoptimizr.com/api/v2.0/remove_tag
            curl http://staging.socialoptimizr.com/api/v2.0/accept_post
            curl http://staging.socialoptimizr.com/api/v2.0/reject_post
    """

    def _preprocess_params(self, user, **kwargs):
        if 'channel_id' not in kwargs:
            raise exc.InvalidParameterConfiguration("Required parameter 'Perform' missing.")

        if 'content' not in kwargs and 'post_id' not in kwargs:
            raise exc.InvalidParameterConfiguration("Either parameter 'content' or 'post_id' required in POST fields.")

        try:
            self.channel = Channel.objects.get(kwargs['channel_id'])
        except Channel.DoesNotExist:
            raise exc.ResourceDoesNotExist("No channel found with id=%s" % kwargs['channel_id'])

        if kwargs.get('post_id', False):
            post = Post.objects.get(kwargs['post_id'])
        elif kwargs.get('content', False):
            target_channel = self.channel.id if not isinstance(self.channel, SmartTagChannel) else \
                             self.channel.parent_channel
            post = factory_by_user(user, channels=[target_channel], content=kwargs['content'])
        else:
            raise Exception("Either post_id or content should be passed")
        return post


class AddTagAPIView(FeedbackMixin, ModelAPIView):

    model = FeedbackAPICommand
    endpoint = 'add_tag'

    @api_request
    def post(self, user, **kwargs):
        post_object = self._preprocess_params(user, **kwargs)
        if not post_object.get_assignment(self.channel, tags=True) == 'starred':
            # Check if tag is already added, in that case skip this to avoid overfitting
            post_object.handle_add_tag(self.user, self.channel)
            FeedbackAPICommand.objects.create(user=user,
                                              timestamp=now(),
                                              channel_id=str(self.channel.id),
                                              command=FeedbackAPICommand.ADD_TAG)
        return dict(item=PostAPIView._format_doc(post_object))

    @classmethod
    def register(cls, app):
        view_func = cls.as_view('add_tag')
        app.add_url_rule(cls.get_api_url(), view_func=view_func, methods=["POST", "GET", "PUT", "DELETE"])


class RemoveTagAPIView(FeedbackMixin, ModelAPIView):

    model = FeedbackAPICommand
    endpoint = 'remove_tag'

    @api_request
    def post(self, user, **kwargs):
        post_object = self._preprocess_params(user, **kwargs)
        if not post_object.get_assignment(self.channel, tags=True) == 'rejected':
            # Check if tag is already removed, in that case skip this to avoid overfitting
            post_object.handle_remove_tag(self.user, self.channel)
            FeedbackAPICommand.objects.create(user=user,
                                              timestamp=now(),
                                              channel_id=str(self.channel.id),
                                              command=FeedbackAPICommand.REMOVE_TAG)
        return dict(item=PostAPIView._format_doc(post_object))

    @classmethod
    def register(cls, app):
        view_func = cls.as_view('remove_tag')
        app.add_url_rule(cls.get_api_url(), view_func=view_func, methods=["POST", "GET", "PUT", "DELETE"])


class AcceptPostAPIView(FeedbackMixin, ModelAPIView):

    model = FeedbackAPICommand
    endpoint = 'accept_post'

    @api_request
    def post(self, user, **kwargs):
        post_object = self._preprocess_params(user, **kwargs)
        if not post_object.get_assignment(self.channel) == 'starred':
            # Check if post is already accepted, in that case skip this to avoid overfitting
            post_object.handle_accept(self.user, self.channel)
            FeedbackAPICommand.objects.create(user=user,
                                              timestamp=now(),
                                              channel_id=str(self.channel.id),
                                              command=FeedbackAPICommand.ACCEPT_POST)
        return dict(item=PostAPIView._format_doc(post_object))

    @classmethod
    def register(cls, app):
        view_func = cls.as_view('accept_post')
        app.add_url_rule(cls.get_api_url(), view_func=view_func, methods=["POST", "GET", "PUT", "DELETE"])


class RejectPostAPIView(FeedbackMixin, ModelAPIView):

    model = FeedbackAPICommand
    endpoint = 'reject_post'

    @api_request
    def post(self, user, **kwargs):
        post_object = self._preprocess_params(user, **kwargs)
        if not post_object.get_assignment(self.channel) == 'rejected':
            # Check if post is already rejected, in that case skip this to avoid overfitting
            post_object.handle_reject(self.user, self.channel)
            FeedbackAPICommand.objects.create(user=user,
                                              timestamp=now(),
                                              channel_id=str(self.channel.id),
                                              command=FeedbackAPICommand.REJECT_POST)
        return dict(item=PostAPIView._format_doc(post_object))

    @classmethod
    def register(cls, app):
        view_func = cls.as_view('reject_post')
        app.add_url_rule(cls.get_api_url(), view_func=view_func, methods=["POST", "GET", "PUT", "DELETE"])

