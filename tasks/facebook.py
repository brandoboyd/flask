'''
Contains all the tasks that are specific to facebook.
'''
from __future__ import absolute_import
import os
import json
import traceback

from datetime import datetime, timedelta
from dateutil import parser

from solariat.utils.text import force_bytes
from solariat_bottle.tasks.exceptions import FacebookCommunicationException
from solariat.utils.timeslot import utc
from solariat_bottle.utils import facebook_driver
from solariat_bottle.utils.facebook_driver import FacebookDriver, get_page_id, \
    get_page_id_candidates

from solariat_bottle.workers import io_pool
from solariat_bottle.settings import FB_DATA_PULL_INTERVAL_MIN, FB_PM_PULL_INTERVAL_MIN, FACEBOOK_API_VERSION

logger = io_pool.logger
# --- IO-worker initialization ----

TYPE_POST = 'Post'
TYPE_COMMENT = 'Comment'
DEFAULT_FB_VERSION = FACEBOOK_API_VERSION

@io_pool.prefork  # IO-workers will run this before forking
def pre_import_facebook():
    """ Master init
        Pre-importing heavy modules with many dependencies here
        to benefit from the Copy-on-Write kernel optimization.
    """
    logger.info('pre-importing facebook dependencies')

    import facebook
    import solariat_bottle.utils.facebook_extra

    assert hasattr(facebook, 'GraphAPI')
    assert hasattr(facebook, 'GraphAPIError')

    # to disable a pyflakes warnings
    del facebook
    del solariat_bottle

# --- Facebook tasks ---


def get_facebook_api(channel, token=None, version=DEFAULT_FB_VERSION):
    if token is None:
        __check_access_token(channel)
    token = token or channel.facebook_access_token
    return facebook_driver.GraphAPI(token, version=version, channel=channel)


def get_page_based_api(post, user_api=None):
    """
    Try to get API for page / event if we can infer based on target id (page_id or event_id)
    Otherwise default to user
    """
    from solariat_bottle.db.post.facebook import FacebookPost

    channels = post.service_channels
    if not channels:
        from solariat_bottle.db.post.facebook import lookup_facebook_channels
        channels = lookup_facebook_channels(post.native_data)
        if not channels:
            logger.warning(u"get_page_based_api: No active channels for post %s" % post)
    post_type = post.wrapped_data['source_type']
    if post_type == 'PM':
        return user_api

    source_id_candidates = get_page_id_candidates(post)

    def find_token_for_source_id(channels, source_ids):
        source_ids = set(map(str, source_ids))
        from solariat_bottle.db.channel.facebook import FacebookServiceChannel

        for channel in channels:
            assert isinstance(channel, FacebookServiceChannel), "%s is not instance of %s" % (channel, FacebookServiceChannel)

            for fb_object in channel.all_facebook_pages + channel.all_fb_events:
                if isinstance(fb_object, dict) and 'access_token' in fb_object and 'id' in fb_object \
                        and str(fb_object['id']) in source_ids:
                    return channel, fb_object['access_token']
        raise FacebookCommunicationException(
            "No token found in channels %s for source ids %s" % (channels, source_ids))

    try:
        channel, token = find_token_for_source_id(channels, source_id_candidates)
    except Exception, ex:
        logger.warning("No page/event token found for target %s. Exception: %s. Defaulting to user API." % (post, ex))
    else:
        return facebook_driver.GraphAPI(token, version=DEFAULT_FB_VERSION, channel=channel)

    return user_api


def __check_access_token(channel):
    from solariat_bottle.tasks.exceptions import FacebookConfigurationException
    if not channel.facebook_access_token:
        error = "You have no access token on channel %s. Please login throgh GSA APP." % channel.title
        raise FacebookConfigurationException(error)

@io_pool.task
def fb_like_post(channel, object_id, delete=False):
    """ Like / unlike a post given the post id """
    import facebook
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException, FacebookConfigurationException
    from solariat_bottle.db.post.facebook import FacebookPost

    try:
        graph = get_facebook_api(channel)
        try:
            post = FacebookPost.objects.get(_native_id=str(object_id))
            post.user_liked = False if delete in (True, 'true', 'True', 1) else True
            post.save()
            graph = get_page_based_api(post, graph)
        except FacebookPost.DoesNotExist:
            pass

        facebook_post_id = object_id

        logger.warning("Got like/unlike request to object_id=%s with delete=%s" % (object_id, delete))
        if delete in (True, 'true', 'True', 1):
            result = graph.put_object(facebook_post_id, "likes", method="delete")
        else:
            result = graph.put_object(facebook_post_id, "likes")

        return dict(id=facebook_post_id, ok=result.get("success", False))

    except facebook.GraphAPIError, exc:
        def _get_error_code(exc):
            try:
                return exc.code
            except AttributeError:
                try:
                    ex_data = json.loads(exc.message)
                except ValueError:
                    return -1
                else:
                    return ex_data.get('code', -1)

        if _get_error_code(exc) == 100:
            # This is raised if we try to unlike a post that was already unliked.
            # Since we don't keep these things in sync on our side, we need to make sure we
            # just gracefully handle this since we don't care about it
            pass
        else:
            raise FacebookCommunicationException(exc.message)
    except FacebookConfigurationException:
        raise
    except Exception as exc:
        logger.error("Exception: %s, Channel: %s, Object_id: %s" % (exc, channel, object_id))
        raise FacebookCommunicationException(exc.message)

@io_pool.task
def fb_get_comments_for_post(channel, post_id, limit=None, offset=None, since=None, until=None, order='ASC'):
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException, FacebookConfigurationException

    params = {}
    if since:
        params['since'] = since
    if until:
        params['until'] = until
    if limit:
        params['limit'] = limit
    if offset:
        params['offset'] = offset

    comments_fields = "attachment,can_comment,can_remove," \
                      "comment_count,created_time,from,id," \
                      "like_count,message,message_tags,parent,user_likes,likes"
    params['fields'] = comments_fields + ",comments{" + comments_fields + "}"

    try:
        graph = get_facebook_api(channel)
        comments_data = graph.request(post_id + '/comments', params)
        return comments_data.get("data", [])
    except FacebookConfigurationException:
        raise
    except Exception as exc:
        log_channel_error(channel, logger)
        logger.error(exc)
        raise FacebookCommunicationException(exc.message)


@io_pool.task
def fb_count_comments(post_id):
    from solariat_bottle.db.post.facebook import FacebookPost
    post = FacebookPost.objects.get(post_id)
    try:
        graph = get_page_based_api(post)
    except Exception, ex:
        logger.error("Failed to get an API for post %s. Trace: %s" % (str(post), ex))
        return None
    if graph:
        fb_data = graph.request(post.wrapped_data['id'] + '/comments?summary=true')
        return fb_data.get('summary', {}).get('total_count', None)
    else:
        return None


@io_pool.task
def fb_share_post(channel, post_url):
    """ Share a post url on own timeline """
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException, FacebookConfigurationException
    try:
        graph = get_facebook_api(channel)
        data = {'link': post_url}
        result = graph.request('/me/feed', post_args=data)
        return dict(id=result['id'])
    except FacebookConfigurationException:
        raise
    except Exception as exc:
        log_channel_error(channel, logger)
        logger.error(exc)
        raise FacebookCommunicationException(exc.message)


@io_pool.task
def fb_channel_user(channel):
    """ Share a post url on own timeline """
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException, FacebookConfigurationException
    try:
        return channel.facebook_me()
    except FacebookConfigurationException:
        raise
    except Exception as exc:
        log_channel_error(channel, logger)
        logger.error(exc)
        raise FacebookCommunicationException(exc.message)


@io_pool.task
def fb_get_channel_description(channel):
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException, FacebookConfigurationException
    from solariat_bottle.utils.post import get_service_channel
    channel_info = {
        'user': [],
        'pages': [],
        'events': []
    }

    def pick_user_for_channel(ch):
        from solariat_bottle.db.user import User

        user = None
        for user in User.objects.find(accounts__in=[ch.account.id], is_superuser=False):
            if user.is_admin:
                return user
        return user

    service_channel = get_service_channel(channel)
    if not service_channel:
        raise FacebookConfigurationException(
            "No service channel was found for channel: " + str(channel))

    try:
        cached_info = service_channel.channel_description
        if cached_info:
            return cached_info

        graph = get_facebook_api(service_channel)
        user_info = graph.get_object('me')

        picture = graph.get_object('me/picture')
        if picture:
            user_info['pic_url'] = picture.get('url')
        #friends = graph.get_object('me/friends')
        #user_info['friend_count'] = str(friends.get('summary', {}).get('total_count', 0))
        channel_info['user'] = user_info

        for page_id in service_channel.facebook_page_ids:
            try:
                page_info = graph.get_object(page_id)
            except (facebook_driver.facebook.GraphAPIError, FacebookCommunicationException) as exc:
                if 'does not exist' in exc.message:
                    logger.info("%s facebook page %s does not exist. Removing from channel" % (channel, page_id))
                    service_channel.remove_facebook_page({'id': page_id, 'name': page_id}, pick_user_for_channel(service_channel))
                else:
                    raise exc
            else:
                picture = graph.get_object(page_id + '/picture')
                if picture:
                    url = picture.get('url')
                    page_info['pic_url'] = url
                channel_info['pages'].append(page_info)

        for event_id in service_channel.tracked_fb_event_ids:
            try:
                event_info = graph.get_object(event_id)
            except (facebook_driver.facebook.GraphAPIError, FacebookCommunicationException) as exc:
                if 'does not exist' in exc.message:
                    logger.info("%s facebook event %s does not exist. Removing from channel" % (channel, event_id))
                    service_channel.untrack_fb_event({'id': event_id, 'name': event_id}, pick_user_for_channel(service_channel))
                else:
                    raise exc
            else:
                picture = graph.get_object(event_id + '/picture')
                if picture:
                    url = picture.get('url')
                    event_info['pic_url'] = url
                channel_info['events'].append(event_info)
        service_channel.channel_description = channel_info

        return channel_info
    except FacebookConfigurationException:
        raise
    except Exception as exc:
        log_channel_error(service_channel, logger)
        logger.error(traceback.format_exc())
        raise FacebookCommunicationException(exc.message)


@io_pool.task
def fb_edit_publication(channel, object_id, message):
    """ Edit a comment with a new message """
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException, FacebookConfigurationException
    from solariat_bottle.db.post.facebook import FacebookPost
    try:
        graph = get_facebook_api(channel)
        try:
            post = FacebookPost.objects.get(_native_id=str(object_id))
            graph = get_page_based_api(post, graph)
        except FacebookPost.DoesNotExist:
            pass
        data = {'message': message}
        result = graph.request(object_id, post_args=data)
        # Another quirk from facebook, where this returns a boolean instead of a json (might be problem with
        # facebook sdk wrapper) For now just hack around it
        if result in (True, False):
            return dict(ok=result, id=object_id)
        else:
            return dict(ok=result.get("success", False), id=object_id)
    except FacebookConfigurationException:
        raise
    except Exception as exc:
        log_channel_error(channel, logger)
        logger.error(exc)
        raise FacebookCommunicationException(exc.message)


@io_pool.task
def fb_put_comment(channel, object_id, message):
    """put comment to some object"""
    # func = lambda: get_facebook_api(channel).put_comment(object_id, message.encode('utf-8', 'replace'))
    # return __try_execute_safely(func, 5, 3600)

    from solariat_bottle.settings import LOGGER
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException
    from solariat_bottle.db.post.facebook import FacebookPost
    try:
        fb_post = FacebookPost.objects.get(_native_id=str(object_id))
    except FacebookPost.DoesNotExist:
        LOGGER.warning("No mapping post for native_id=%s was found. Defaulting to posting comment as user." % object_id)
    else:
        try:
            return fb_comment_by_page(fb_post, object_id, message)
        except (FacebookCommunicationException, facebook_driver.facebook.GraphAPIError) as exc:
            if '#1705' in str(exc):  # GraphAPIError: (#1705) There was an error posting to this wall
                LOGGER.info("Failed sending comment to post %s with error %s" % (object_id, str(exc)))
                if fb_post.is_second_level_reply:
                    try:
                        object_id = fb_post.wrapped_data['parent_id']
                    except KeyError:
                        LOGGER.error("Can't find parent for comment %s" % fb_post)
                        raise exc
                    LOGGER.info("Sending comment to parent %s of initial post %s %s" % (object_id, fb_post, fb_post.native_id))
                    return fb_comment_by_page(fb_post, object_id, message)
            raise exc

    try:
        return get_facebook_api(channel).put_comment(object_id, force_bytes(message, 'utf-8', 'replace'))
    except Exception, ex:
        LOGGER.error("Failure posting comment to facebook. Exc: %s,  Channel: %s, Object_id: %s, Message: %s" % (
            ex, channel, object_id, message))
        raise FacebookCommunicationException(ex.message)


@io_pool.task
def fb_put_comment_by_channel(channel, object_id, message):

    from solariat_bottle.settings import LOGGER
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException

    try:
        return get_facebook_api(channel).put_comment(object_id, force_bytes(message, 'utf-8', 'replace'))
    except Exception, ex:
        LOGGER.error("Failure posting comment to facebook. Exc: %s,  Channel: %s, Object_id: %s, Message: %s" % (
            ex, channel, object_id, message
                                                                                                                ))
        raise FacebookCommunicationException(ex.message)

@io_pool.task
def fb_private_message(channel, pmthread_id, message):
    import facebook
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException
    from solariat_bottle.utils.post import get_service_channel
    fb_service_channel = get_service_channel(channel)

    try:
        graph = get_facebook_api(channel)
        # We don't know based on a thread id which page we should answer from. No better solution
        # right now than to just try to reply from all pages and see which one we can reply from first
        errors = []

        try:
            # First try to reply as individual, this will fail since most PMs are to pages and we won't
            # have permission as user to reply to them
            return graph.request("%s/messages" % pmthread_id, post_args={"message": message})
        except facebook.GraphAPIError, ex:
            errors.append(ex)

        accounts_data = fb_service_channel.all_facebook_pages
        if not accounts_data:
            accounts_data = graph.request('/me/accounts')['data']
            fb_service_channel.update(all_facebook_pages=accounts_data)

        for account in accounts_data:
            # Now try to find page from which to reply since we don't have anything but post id
            page_graph = facebook_driver.GraphAPI(account.get('access_token', ''), channel=channel)
            try:
                return page_graph.request("%s/messages" % pmthread_id, post_args={"message": message})
            except facebook.GraphAPIError, ex:
                errors.append(ex)
        raise FacebookCommunicationException("Could not send direct message to thread %s. Attempt errors: %s." %
                                             (pmthread_id, errors))
    except Exception as exc:
        logger.error("Failure posting PM. Exc: %s, Channel: %s, PM_Thread: %s, Message: %s" % (
            exc, channel, pmthread_id, message
        ))
        raise FacebookCommunicationException(exc.message)

@io_pool.task
def fb_change_object_visibility(channel, object_id, object_type, visibility):
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException, FacebookConfigurationException
    from solariat_bottle.db.post.facebook import FacebookPost
    try:
        graph = get_facebook_api(channel)
        try:
            post = FacebookPost.get_by_native_id(str(object_id))
            graph = get_page_based_api(post, graph)
        except FacebookPost.DoesNotExist:
            pass

        if object_type == TYPE_POST:
            allowed_values = ("starred", "hidden", "normal")
            if visibility not in allowed_values:
                raise FacebookCommunicationException("Only allowed visibility values for statuses are %s" %
                                                     allowed_values)
            result = graph.request(object_id, post_args={"timeline_visibility": visibility})
            success = result.get('success', False)
            return dict(ok=success, id=object_id)
        elif object_type == TYPE_COMMENT:
            allowed_values = ("private", "hidden", "normal")
            if visibility not in allowed_values:
                raise FacebookCommunicationException("Only allowed visibility values for comments are %s" %
                                                     allowed_values)
            if visibility == "private":
                post_data = {"is_private": True}
            elif visibility == "hidden":
                post_data = {"is_hidden": True}
            else:
                post_data = {"is_private": False}
            result = graph.request(object_id, post_args=post_data)
            success = result.get('success', False)
            return dict(ok=success, id=object_id)
        else:
            raise FacebookCommunicationException("Unknown object type %s. Only <Post, Comment> allowed." % object_type)
        # Facebook being annoying as usual.
        # if result in (True, False):
        #     return dict(ok=result)
        # else:
        #     return result
        return dict(id=object_id)
    except FacebookConfigurationException, ex:
        er = "Failure in change object visibility. Exc: %s, Channel: %s, Object_id: %s, Object_type: %s, Visibility: %s"
        logger.error(er % (ex, channel, object_id, object_type, visibility))
        raise
    except Exception as exc:
        er = "Failure in change object visibility. Exc: %s, Channel: %s, Object_id: %s, Object_type: %s, Visibility: %s"
        logger.error(er % (exc, channel, object_id, object_type, visibility))
        raise FacebookCommunicationException(exc.message)

@io_pool.task
def fb_put_post(channel, target_id, message, picture_name=None, media=None, link=None, link_description=None):
    """ Send post to a user feed or a page feed """
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException
    from solariat_bottle.tasks.twitter import get_file_from_media
    from solariat_bottle.utils.post import get_service_channel

    api = get_facebook_api(channel)
    service_channel = get_service_channel(channel)
    if service_channel:
        possible_targets = service_channel.all_fb_events + service_channel.facebook_pages
        matched_targets = [target for target in possible_targets if target['id'] == target_id]
        if matched_targets:
            token = matched_targets[0]['access_token']
            api = get_facebook_api(channel, token=token)

    if media:
        filename, f = get_file_from_media(media)

        kwargs = dict()
        if message:
            kwargs['caption'] = message
        # if target_id:
        #     kwargs['target_id'] = target_id
        photo = api.put_photo(f, album_path=target_id + "/photos", **kwargs)
        # attachment_data['link'] = picture_info['link']
        if f:
            try:
                f.close()
                os.unlink(f.name)
            except IOError:
                pass
        return photo
    else:
        attachment_data = {}
        if link:
            # attachment_data['link'] = link
            attachment_data["picture"] = link
            if link_description:
                attachment_data['description'] = link_description

        try:
            result = api.put_wall_post(force_bytes(message, 'utf-8', 'replace'),
                                       profile_id=target_id,
                                       attachment=attachment_data)
            return result
        except Exception, ex:
            er = "Failure on posting to facebook. Channel: %s, Target: %s, Message: %s, Pic_N: %s, Pic_B: %s, Link: %s"
            logger.error(er % (channel, target_id, message, picture_name, media, link))
            raise FacebookCommunicationException(ex.message)


@io_pool.task
def fb_delete_object(channel, target_id):
    """ Delete object (post/comment) """
    # func = lambda: get_facebook_api(channel).delete_object(target_id)
    # return __try_execute_safely(func, 5, 3600)
    #try:
    import facebook
    try:
        token = __get_token_for_item(channel, target_id)
        graph = get_facebook_api(channel, token=token)
        graph.timeout = 100
        graph.delete_object(target_id)
        return dict(id=target_id)
    except Exception, ex:
        err = "Failure on deleting object. Channel: %s, Target: %s"
        logger.error(err % (channel, target_id))
        raise FacebookCommunicationException(ex.message)

@io_pool.task
def fb_get_object(channel, object_id, token):
    """ Delete object (post/comment) """
    try:
        graph = get_facebook_api(channel, token=token)
        graph.timeout = 100
        graph.get_object(object_id)
        return dict(id=object_id)
    except Exception, ex:
        err = "Failure on getting object. Channel: %s, Target: %s"
        logger.error(err % (channel, object_id))
        raise FacebookCommunicationException(ex.message)

@io_pool.task(timeout=1000)
def fb_get_latest_pm(channel, page_id, user):

    def action(since, until):
        fb_get_private_messages(channel, page_id, user, since, until)

    __execute_with_md_update(channel, page_id, action, FB_PM_PULL_INTERVAL_MIN)


@io_pool.task(timeout=1000)
def fb_get_latest_posts(channel, target, user):

    def action(since, until):
        fb_get_post_comments(channel, user, target, since, until)

    __execute_with_md_update(channel, target, action, FB_DATA_PULL_INTERVAL_MIN)


@io_pool.task(timeout=100)
def fb_get_history_data_for(channel, target, user, since, until):

    fb_get_post_comments(channel, user, target, since, until)


@io_pool.task(timeout=1000)
def fb_get_history_pm(channel, target, user, since, until):

    fb_get_private_messages(channel, target, user, since, until)


@io_pool.task(timeout=100)
def fb_get_comments_for(channel, target, user, since):

    from solariat_bottle.db.post.utils import factory_by_user
    from solariat_bottle.daemons.facebook.facebook_data_handlers import FBDataHandlerFactory
    from solariat_bottle.daemons.facebook.facebook_history_scrapper import FacebookHistoryScrapper

    puller = FacebookHistoryScrapper(channel, user=user)
    comments = puller.get_comments(target, since=since)['data']

    for comment in comments:
        comment = puller.handle_data_item(data=comment,
                                          handler=FBDataHandlerFactory.get_instance(FBDataHandlerFactory.COMMENT),
                                          target_id=target)
        factory_by_user(user, sync=True, **comment)


@io_pool.task
def fb_answer_pm(post, message):

    """
    1. Read conversation id from post
    2. Get token for the page
    3. Send POST request to <conversation_id>/messages
    """

    channels = post.service_channels
    page_id = post.native_data['page_id']

    #this is not safe, but according system logic this data should be in the system, if not - it will be good to
    #get exception there, it will means that data is corrupted
    channel = [ch for ch in channels if (hasattr(ch, 'facebook_page_ids') and page_id in ch.facebook_page_ids)][0]
    token = [page for page in channel.facebook_pages if page['id'] == page_id][0]['access_token']

    driver = FacebookDriver(token, channel=channel)
    conversation = post.native_data['conversation_id']
    path = str(conversation) + '/messages'
    driver.post(path, {"message": force_bytes(message, 'utf-8', 'replace')})

@io_pool.task
def fb_comment_by_page(post, respond_to, message):
    driver = get_page_based_api(post)
    return driver.request(respond_to + "/comments", post_args={"message": force_bytes(message, 'utf-8', 'replace')})


def fb_get_private_messages(channel, page_id, user, since, until):

    from solariat_bottle.db.post.utils import factory_by_user
    from solariat_bottle.daemons.facebook.facebook_data_handlers import FBDataHandlerFactory
    from solariat_bottle.daemons.facebook.facebook_history_scrapper import FacebookHistoryScrapper

    puller = FacebookHistoryScrapper(channel, user=user)
    message_threads = puller.get_page_private_messages(page_id, since, until)['data']

    for thread in message_threads:

        if 'messages' in thread and thread['messages']['data']:

            data = thread['messages']['data'][::-1] #get array of messages in reversed order
            root_message_id = data[0]['id']

            if thread['id'] in channel.tracked_fb_message_threads_ids:
                check = lambda msg, since : utc(parser.parse(msg['created_time'])) > utc(since)
                messages_to_handle = [msg for msg in data if check(msg, since)]
            else:
                channel.tracked_fb_message_threads_ids.append(thread['id'])
                channel.save()
                messages_to_handle = data

            conversation_id = thread['id']
            for msg in messages_to_handle:
                if msg['id'] != root_message_id:
                    msg['root_post'] = root_message_id
                msg['conversation_id'] = conversation_id
                msg['page_id'] = page_id
                msg = puller.handle_data_item(msg, FBDataHandlerFactory.get_instance(FBDataHandlerFactory.PM), thread['id'])
                factory_by_user(user, sync=True, **msg)


def fb_get_post_comments(channel, user, target, since, until):

    from solariat_bottle.db.post.utils import factory_by_user
    from solariat_bottle.daemons.facebook.facebook_data_handlers import FBDataHandlerFactory
    from solariat_bottle.daemons.facebook.facebook_history_scrapper import FacebookHistoryScrapper

    puller = FacebookHistoryScrapper(channel, user)
    new_posts = puller.get_posts(since=since, until = until, target=target)

    for post in new_posts['data']:
        #avoid handling posts with no data useful to parsing
        if 'message' not in post and 'link' not in post:
            continue

        try:
            post = puller.handle_data_item(data=post,
                                           handler=FBDataHandlerFactory.get_instance(FBDataHandlerFactory.POST),
                                           target_id=target)
        except Exception, ex:
            logger.error(ex)
            continue
        comments = post.pop('comments', [])
        factory_by_user(user, sync=True, **post)

        for comment in comments:
            post_id = post['id']
            try:
                comment = puller.handle_data_item(data=comment,
                                                  handler=FBDataHandlerFactory.get_instance(FBDataHandlerFactory.COMMENT),
                                                  target_id=post_id)
            except Exception, ex:
                logger.error(ex)
                continue
            factory_by_user(user, sync=True, **comment)


def __get_token_for_item(channel, object_id):

    from solariat_bottle.settings import LOGGER
    from solariat_bottle.tasks.exceptions import FacebookCommunicationException
    from solariat_bottle.db.post.facebook import FacebookPost
    from solariat_bottle.db.channel.facebook import EnterpriseFacebookChannel
    try:

        if isinstance(channel, EnterpriseFacebookChannel):
            from solariat_bottle.utils.post import get_service_channel
            channel = get_service_channel(channel)

        fb_post = FacebookPost.objects.get(_native_id=str(object_id))
        post_type = fb_post.wrapped_data['source_type']
        source_ids = set(map(str, get_page_id_candidates(fb_post)))

        try:
            if post_type == 'Event':
                token = [event for event in channel.all_fb_events if str(event['id']) in source_ids][0]['access_token']
            else:
                token = [page for page in channel.facebook_pages if str(page['id']) in source_ids][0]['access_token']
        except Exception, ex:
            LOGGER.error("Failed to get page access token for object_id=%s and channel=%s" % (object_id, channel))
            token = channel.facebook_access_token
        return token
    except Exception, ex:
        LOGGER.error("Fail when trying to get token for object. Exc: %s,  Channel: %s, Object_id: %s," % (
            ex, channel, object_id))
        raise ex


#TODO: Possibly rewrite to decorator. Need to think and discuss
def __try_execute_safely(to_execute, max_tries, timeout):

    import facebook
    result = None
    for num in xrange(max_tries):  # max re-tries
        try:
            result = to_execute()
        except Exception as exc:
            logger.error(exc)

            if isinstance(exc, facebook.GraphAPIError) and \
               str(exc) == 'Error validating application.':
                raise Exception(exc)

            io_pool.tools.sleep(timeout)  # wait
            continue                   # re-try
        else:
            break
    return result


def __execute_with_md_update(channel, target, task, interval):

    target_md = channel.pull_activity_md.get(target, None)

    if target_md is None:
        target_md = {
            'start_tracking': datetime.utcnow(),
            'last_run': datetime.utcnow() - timedelta(minutes=interval)
        }
        channel.pull_activity_md[target] = target_md

    since = target_md['last_run']
    until = datetime.utcnow()

    task(since, until)

    channel.pull_activity_md[target]['last_run'] = until
    channel.save()


@io_pool.task
def fb_process_subscription(subscription):

    from solariat_bottle.daemons.facebook.facebook_historics import FacebookSubscriber
    from solariat_bottle.settings import LOGGER
    from solariat_bottle.db.historic_data import SUBSCRIPTION_FINISHED
    from time import sleep

    fb_subscriber = FacebookSubscriber(subscription=subscription)
    fb_subscriber.start_historic_load()

    # We only know the entire data load finished as soon as both the DM subscription
    # and the datasift subscription finised
    sub_finished = False
    start_time = datetime.now()
    LOGGER.info("Subscription %s started at %s." % (subscription.id, start_time))
    while not sub_finished:
        ds_alive = fb_subscriber.get_status() != SUBSCRIPTION_FINISHED
        LOGGER.info("Subscription %s; running: %s; Ellapsed time: %s" % (
                    subscription.id, ds_alive, datetime.now() - start_time))
        if ds_alive:
            sleep(60)
        else:
            sub_finished = True
    LOGGER.info("Subscription %s finish processing data after %s." % (subscription.id, datetime.now() - start_time))

def log_channel_error(channel, logger):
    logger.error("Error occurred for chanel name: %s, id: %s" % (channel.title, channel.id))
