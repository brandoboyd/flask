from solariat_bottle.db.conversation import Conversation
from solariat_bottle.db.post.facebook import FacebookPost
from solariat_bottle.db.channel.facebook import FacebookServiceChannel
from solariat_bottle.tasks.scheduled.base import BaseScheduledTask
from datetime import timedelta
from solariat_bottle.tasks.facebook import fb_get_latest_pm, fb_get_latest_posts, fb_get_comments_for
from solariat_bottle.settings import FB_PM_PULL_INTERVAL_MIN, FB_DATA_PULL_INTERVAL_MIN, FB_UPDATE_CONV_MIN


class FBPrivateMessagePullTask(BaseScheduledTask):

    @classmethod
    def instance(cls):
        return cls._resolve(interval=timedelta(minutes=FB_PM_PULL_INTERVAL_MIN))

    @classmethod
    def should_do(cls, user):

        targets = cls.__get_targets()
        for target in targets:
            try:
                fb_get_latest_pm.sync(target[0], target[1], user)
            except Exception, e:
                cls._log_ex("Exception occurred during %s execution"%cls.__name__, e)

    @classmethod
    def __get_targets(cls):
        channels = FacebookServiceChannel.objects.find(status='Active')
        targets = []
        for channel in channels:
            for page_id in channel.facebook_page_ids:
                targets.append((channel, page_id))

        return targets

class FBPostCommentsPullTask(BaseScheduledTask):

    @classmethod
    def instance(cls):

        return cls._resolve(interval=timedelta(minutes=FB_DATA_PULL_INTERVAL_MIN))

    @classmethod
    def should_do(cls, user):

        targets = cls.__get_targets()
        for target in targets:
            try:
                fb_get_latest_posts.sync(target[0], target[1], user)
            except Exception, e:
                cls._log_ex("Exception occurred during %s execution"%cls.__name__, e)


    @classmethod
    def __get_targets(cls):

        channels = FacebookServiceChannel.objects.find(status='Active')
        targets = []
        for channel in channels:

            for id in channel.tracked_fb_event_ids:
                targets.append((channel, id))

            for id in channel.tracked_fb_group_ids:
                targets.append((channel, id))

        return targets


class FBCheckConversationUpdate(BaseScheduledTask):

    @classmethod
    def instance(cls):

        return cls._resolve(interval=timedelta(minutes=FB_UPDATE_CONV_MIN))


    @classmethod
    def should_do(cls, user):

        targets = cls.__get_targets()
        for target in targets:
            try:
                fb_get_comments_for.sync(target[0], target[1], user, target[2])
            except Exception, e:
                cls._log_ex("Exception occurred during %s execution"%cls.__name__, e)


    @classmethod
    def __get_targets(cls):

        channels = FacebookServiceChannel.objects.find(status='Active')
        targets = []
        provider = Conversation.objects
        for channel in channels:
            conversations = provider.find(channel=channel.id, is_closed=False)
            for conversation in conversations:
                if conversation.posts:
                    try:
                        post = FacebookPost.objects.get(conversation.posts[0])
                        target_id = post.native_id
                        if cls.__is_valid_target(target_id):
                            targets.append((channel, target_id, conversation.last_modified))
                        else:
                            cls._log_warn("Corrupted or test id detected for channel: %s, post: %s" %
                                          (channel.id, conversation.posts[0]))
                    except Exception, e:
                        cls._log_ex("Error occurred", e)
        return targets

    @classmethod
    def __is_valid_target(cls, target):
        min_post_length = 14
        return len(target) > min_post_length

