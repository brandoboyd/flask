'''
Utilitary methods for facebook interaction.
'''
from __future__ import absolute_import

import facebook
from solariat_bottle import settings

from solariat_bottle.settings import LOGGER
import json
import urllib
from solariat_bottle.utils import facebook_driver


def reset_fbot_cache(channel):
    from solariat_bottle.tasks import async_requests
    import requests
    url = "%s?token=%s&channel=%s" % (settings.FBOT_URL + '/json/resetchannel', settings.FB_DEFAULT_TOKEN, channel)
    try:
        async_requests.ignore('get', url, verify=False, timeout=None)
    except requests.ConnectionError:
        LOGGER.warning('Cannot reset fbot channel cache: ', exc_info=True)


def subscribe_realtime_updates(items):
    for item in items:
        if 'access_token' in item:
            G = facebook_driver.GraphAPI(item['access_token'])
            path = "/%s/subscribed_apps" % item['id']
            G.request(G.version + '/' + path, method='POST')
        else:
            # TODO: Define what to do in that case
            pass


def unsubscribe_realtime_updates(pages):
    for page in pages:
        G = facebook_driver.GraphAPI(page['access_token'])
        try:
            G.delete_object('%s/subscribed_apps' % page['id'])
        except facebook.GraphAPIError as e:
            LOGGER.error(e)


def get_page_admins(page):
    api = facebook_driver.GraphAPI(page['access_token'])
    try:
        res = api.get_object('/%s/roles' % page['id'])
    except facebook.GraphAPIError as e:
        LOGGER.error(e)
        return None

    return res['data']


def update_page_admins(channel, page):
    admins = get_page_admins(page)
    if admins:
        channel.page_admins[page['id']] = admins
        channel.objects.coll.update({'_id': channel.id}, {'$set': {'page_admins.%s' % page['id']: admins}})


def permalink_post(page_post_id):
    (page_id, post_id) = page_post_id.split('_', 1)
    return "https://www.facebook.com/%s/posts/%s" % (page_id, post_id)


def permalink_comment(page_id, post_comment_id):
    (post_id, comment_id) = post_comment_id.split('_', 1)
    qs = urllib.urlencode({
        'id': page_id,
        'story_fbid': post_id,
        'comment_id': comment_id})

    return "https://www.facebook.com/permalink.php?%s" % qs


def check_channel_token_valid(channel):
    """
    Make sure the token we have stored for :param channel: is still valid. Otherwise
    flash error messages to users with access to channel and raise error.
    """
    from solariat_bottle.db.user import User
    from solariat_bottle.db.message_queue import TaskMessage
    from solariat_bottle.tasks.exceptions import FacebookConfigurationException

    def __patch_msg(input_error):
        input_error += "Please renew access by a new login to your facebook credentials. "
        input_error += "If you don't have required credentials please contact your administrator. "
        input_error += "The account will be missing new entries for facebook until this is done."
        return input_error

    if channel.facebook_access_token:
        api = facebook_driver.GraphAPI(channel.facebook_access_token, channel=channel)
        try:
            api.get_object('/me/accounts')
            return True
        except facebook.GraphAPIError, ex:
            error = json.loads(ex.message)
            if error['code'] == 190:
                subcode = error.get('subcode', -1)
                if subcode == 458:
                    error_msg = "Facebook access for channel %s has been revoked. " % channel.title
                    error_msg = __patch_msg(error_msg)
                elif subcode == 460:
                    error_msg = "Facebook token for channel %s no longer valid due to facebook password change. " % channel.title
                    error_msg = __patch_msg(error_msg)
                elif subcode == 463:
                    error_msg = "Facebook token for channel %s has expired. " % channel.title
                    error_msg = __patch_msg(error_msg)
                elif subcode == 467:
                    error_msg = "Facebook token for channel %s is invalid. " % channel.title
                    error_msg = __patch_msg(error_msg)
                else:
                    error_msg = error["message"]
                if subcode > 0:
                    for user in User.objects(account=channel.account):
                        TaskMessage.objects.create_error(user=user,
                                                         content=error_msg)
                raise
            else:
                raise
    else:
        error_msg = "Facebook channel %s is not logged into facebook." % channel.title
        error_msg = __patch_msg(error_msg)
        for user in User.objects(account=channel.account):
            TaskMessage.objects.create_error(user=user,
                                             content=error_msg)
        raise FacebookConfigurationException(error_msg)


def check_account_tokens_valid(account):
    """
    Make sure all the EnterpriseFacebookChannel entities from :param account: that are
    still active have a valid access token attached.
    """
    from solariat_bottle.db.channel.facebook import EnterpriseFacebookChannel
    for channel in EnterpriseFacebookChannel.objects(account=account, status="Active"):
        check_channel_token_valid(channel)
