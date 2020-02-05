#!/usr/bin/python2.7
import sys
import json
import time
import urllib
from optparse import OptionParser

import facebook

from solariat_bottle.db.channel.facebook import FacebookServiceChannel, EnterpriseFacebookChannel

from solariat_bottle.settings import LOGGER, LOG_LEVEL, DB_NAME_MAP
from solariat_bottle.daemons.base import BaseExternalBot
from solariat_bottle.utils import facebook_driver
from solariat_bottle.utils.logger import setup_logger
from solariat_bottle.utils.facebook_extra import permalink_post, permalink_comment, check_channel_token_valid

PORT = 8081
VERIFY_TOKEN = 'token'

start_time = int(time.time())


class FacebookClient():

    def __init__(self, bot_instance):
        self.bot_instance = bot_instance

    @staticmethod
    def permalink_post(page_post_id):
        permalink_post(page_post_id)

    @staticmethod
    def permalink_comment(page_id, post_comment_id):
        permalink_comment(page_id, post_comment_id)

    @staticmethod
    def permalink_reply(page_id, post_comment_id, post_reply_id):

        (_, comment_id) = post_comment_id.split('_', 1)
        (post_id, reply_id) = post_reply_id.split('_', 1)

        qs = urllib.urlencode({
            'id': page_id,
            'story_fbid': post_id,
            'comment_id': comment_id,
            'reply_comment_id': reply_id})

        return "https://www.facebook.com/permalink.php?%s" % qs

    @staticmethod
    def get_facebook_channel(page_id):
        return EnterpriseFacebookChannel.objects.find_one(
                                                    status='Active',
                                                    facebook_page_ids=page_id)

    @staticmethod
    def get_service_channels(page_id):
        return FacebookServiceChannel.objects.find(status='Active',
                                                   facebook_page_ids=page_id)[:]


class FacebookBot(BaseExternalBot):

    def __init__(self, username, lockfile, concurrency=1, heartbeat=60):
        super(FacebookBot, self).__init__(username=username,
                                          lockfile=lockfile,
                                          concurrency=concurrency,
                                          name=self.__class__.__name__)
        self.client = FacebookClient(self)
        self.heartbeat = heartbeat

    def run(self):
        self._running = True
        while not self.stopped():
            LOGGER.info("Facebook Bot Heartbeat")
            time.sleep(self.heartbeat)

    def stop(self):
        super(FacebookBot, self).stop()

    def facebook_user_match(self, G, user1_id, user2_id):
        # So since the switch to 2.0 facebook intorduced app scoped users and user ids
        # but they failed to introduce them to realtime updates as of yet (open bug)
        # So we have to try our best to match a non app scope user id with a original user id for now
        if user1_id is None or user2_id is None:
            return False

        print "Matching user %s against %s" % (user1_id, user2_id)
        if str(user1_id) == str(user2_id):
            return True

        user1 = G.get_object(str(user1_id))
        user2 = G.get_object(str(user2_id))

        # It seems that (At least for now) the link even for original user is app scoped (wtf facebook?!?!)
        if user1.get('link', 1) == user2.get('link', 2):
            return True

        # Another alternative is to use first, last and middle name along with updated at values as reference
        for key in ('first_name', 'last_name', 'middle_name', 'updated_time'):
            if user1.get(key) != user2.get(key):
                return False
        else:
            return True

        return False


    @staticmethod
    def process_comment(G, page_id, change, attachments_ids):
        """
        :param G: A facebook Graph object already logged in properly
        :param page_id: The page on which the comment was issued
        :param change: The post dictionary with the change received from facebook
        :param attachments_ids: Any attachments that were received with the inbound data flow (since we can
                                 get multiple streams at once)
        :return: A dictionary object with app specific data
        """
        post_fields = {}

        comment_id = str(change['value']['comment_id'])
        post_fields['facebook'] = {}
        if 'parent_id' in change['value']:
            # This is for first level comments. We figure out parent id based
            # on the parent post.
            parent_id = str(change['value']['parent_id'])
            # Seems like facebook w/o any notice changed the way they send the parent id for first level comments
            # This is just so legacy posts also work as expected
            if page_id not in parent_id:
                parent_id = '%s_%s' % (page_id, parent_id)
            post_fields['facebook']['in_reply_to_status_id'] = parent_id
            post_fields['url'] = FacebookClient.permalink_reply(page_id, parent_id, comment_id)
            if parent_id in attachments_ids:
                post_fields['facebook']['attachments'] = True
        else:
            post_fields['url'] = FacebookClient.permalink_comment(page_id, comment_id)

        comment = G.get_object(comment_id, fields='can_remove,can_hide,can_comment,can_like,attachment,comment_count,created_time,from,is_hidden,like_count,message,message_tags,object,parent,user_likes')
        post_fields['facebook']['_wrapped_data'] = json.dumps(comment)
        print "Got comment: " + str(comment)
        if 'parent' in comment and comment['parent']:
            # Only in case of replies to comments will this be present
            parent_id = comment['parent']['id']
            post_fields['facebook']['root_post'] = post_fields['facebook']['in_reply_to_status_id']
            post_fields['facebook']['in_reply_to_status_id'] = parent_id
            post_fields['facebook']['second_level_reply'] = True

        post_fields['facebook']['page_id'] = str(page_id)
        post_fields['facebook']['created_at'] = comment['created_time']
        post_fields['facebook']['facebook_post_id'] = comment_id
        post_fields['content'] = comment['message']

        if 'sender_id' in change['value']:
            sender_id = str(change['value']['sender_id'])
        else:
            raise Exception("sender_id not defined")

        post_fields['sender_id'] = sender_id
        return post_fields

    @staticmethod
    def process_status_update(G, page_id, change, attachments_ids):
        """
        :param G: A facebook Graph object already logged in properly
        :param page_id: The page on which the comment was issued
        :param change: The post dictionary with the change received from facebook
        :param attachments_ids: Any attachments that were received with the inbound data flow (since we can
                                 get multiple streams at once)
        :return: A dictionary object with app specific data
        """
        post_fields = {}
        status_id = str(change['value']['post_id'])
        status = G.get_object(status_id, fields="timeline_visibility,actions,application,call_to_action,caption,child_attachments,comments_mirroring_domain,coordinates,created_time,description,expanded_height,expanded_width,feed_targeting,from,full_picture,height,icon,id,is_hidden,is_popular,is_published,link,message,message_tags,name,object_id,parent_id,picture,place,privacy,promotion_status,properties,scheduled_publish_time,shares,source,status_type,story,story_tags,subscribed,targeting,to,type,updated_time,via,width,with_tags,attachments,insights,likes")
        print "Got status update: " + str(status)

        post_fields['url'] = FacebookClient.permalink_post(status_id)
        post_fields['facebook'] = {'_wrapped_data': json.dumps(status)}
        post_fields['facebook']['page_id'] = str(page_id)
        if status_id in attachments_ids:
            post_fields['facebook']['attachments'] = True
        post_fields['facebook']['created_at'] = status['created_time']
        post_fields['content'] = status['message']

        if 'sender_id' in change['value']:
            sender_id = str(change['value']['sender_id'])
        else:
            raise Exception("sender_id not defined")

        post_fields['sender_id'] = sender_id
        return post_fields

    @staticmethod
    def process_post(G, page_id, change, attachments_ids):
        post_fields = {}
        if '_' in str(change['value']['post_id']):
            page_post_id = str(change['value']['post_id'])
        else:
            page_post_id = '%s_%s' % (page_id, str(change['value']['post_id']))

        fb_post_json = G.get_object(page_post_id, fields="timeline_visibility,actions,application,call_to_action,caption,child_attachments,comments_mirroring_domain,coordinates,created_time,description,expanded_height,expanded_width,feed_targeting,from,full_picture,height,icon,id,is_hidden,is_popular,is_published,link,message,message_tags,name,object_id,parent_id,picture,place,privacy,promotion_status,properties,scheduled_publish_time,shares,source,status_type,story,story_tags,to,type,targeting,updated_time,via,width,with_tags,attachments,insights,likes")
        print "Got post: " + str(fb_post_json)

        post_fields['url'] = FacebookClient.permalink_post(page_post_id)
        post_fields['facebook'] = {'_wrapped_data': json.dumps(fb_post_json)}
        post_fields['facebook']['page_id'] = str(page_id)
        if page_post_id in attachments_ids:
            post_fields['facebook']['attachments'] = True
        if 'place' in fb_post_json:
            post_fields['facebook']['location'] = True
        post_fields['facebook']['created_at'] = fb_post_json['created_time']
        post_fields['facebook']['facebook_post_id'] = fb_post_json['id']
        post_fields['content'] = fb_post_json['message']

        if 'sender_id' in change['value']:
            sender_id = str(change['value']['sender_id'])
        else:
            res = G.get_object(page_post_id)
            sender_id = str(res['from']['id'])

        post_fields['sender_id'] = sender_id
        return post_fields

    def post_received(self, post_field):
        """ Expose post_received functionality mainly for testing purposes. Could also use
         it for loading post data directly through bot in case of historics / load_data scripts """
        post_field = json.loads(post_field)
        print "Received " + str(post_field)
        if post_field['object'] == 'page':

            for entry in post_field['entry']:

                page_id = str(entry['id'])

                efc_channel = FacebookClient.get_facebook_channel(page_id)
                if not efc_channel:
                    LOGGER.warn('Active EnterpriseFacebookChannel not found for page_id %s', page_id)
                    break
                check_channel_token_valid(efc_channel)

                matched_chanels = FacebookClient.get_service_channels(page_id)
                if not matched_chanels:
                    LOGGER.warn('Active FacebookServiceChannel not found for page_id %s', page_id)
                    break

                G = facebook_driver.GraphAPI(efc_channel.facebook_access_token, channel=efc_channel)

                oubound_ids = []
                if efc_channel.facebook_handle_id:
                    oubound_ids.append(str(efc_channel.facebook_handle_id))
                oubound_ids.extend([str(u_id) for u_id in efc_channel.facebook_account_ids])

                attachments_ids = []
                for change in entry['changes']:
                    if change['value']['item'] in ('photo',):
                        attachments_ids.append(change['value'].get('post_id', None))

                for change in entry['changes']:

                    post_fields = {}

                    if change['field'] == 'feed':

                        if change['value']['item'] == 'comment':
                            post_fields.update(self.process_comment(G=G,
                                                                    page_id=page_id,
                                                                    change=change,
                                                                    attachments_ids=attachments_ids))
                        if change['value']['item'] == 'status':
                            post_fields.update(self.process_status_update(G=G,
                                                                          page_id=page_id,
                                                                          change=change,
                                                                          attachments_ids=attachments_ids))
                        if change['value']['item'] in ('post', 'photo'):
                            post_fields.update(self.process_post(G=G,
                                                                 page_id=page_id,
                                                                 change=change,
                                                                 attachments_ids=attachments_ids))
                        sender_id = post_fields.pop('sender_id', None)
                        if change['value']['item'] in ('comment', 'status', 'post', 'photo'):
                            service_chns = []
                            for candidate in matched_chanels:
                                if (sender_id in oubound_ids or sender_id in candidate.facebook_page_ids or
                                        self.facebook_user_match(G, sender_id, efc_channel.facebook_handle_id)):
                                # If the sender is the same as the authenticated user, it's an outbound post
                                    service_chns.append(str(candidate.outbound_channel.id))
                                else:
                                    # Otherwise we have an inbound post.
                                    service_chns.append(str(candidate.inbound_channel.id))

                            post_fields['channels'] = service_chns
                            user_profile = G.get_object(sender_id)

                            post_fields['user_profile'] = {'platform_data': user_profile}
                            if 'name' in user_profile:
                                post_fields['user_profile']['user_name'] = user_profile['name']
                            if 'username' in user_profile:
                                post_fields['user_profile']['id'] = user_profile['username']
                            picture = G.get_object(sender_id + '/picture')
                            if picture and picture['data'] and not picture.get('is_silhouette', False):
                                post_fields['user_profile']['profile_image_url'] = picture['url']
                            if 'location' in user_profile:
                                if isinstance(user_profile['location'], dict):
                                    if 'city' in user_profile['location']:
                                        post_fields['user_profile']['location'] = user_profile['location']['city']
                                    elif 'country' in user_profile['location']:
                                        post_fields['user_profile']['location'] = user_profile['location']['country']
                                elif isinstance(user_profile['location'], basestring):
                                        post_fields['user_profile']['location'] = user_profile['location']
                            print "Pushed " + str(post_fields)
                            self.post_queue.put(post_fields)


def main(bot_options):
    fb_bot = FacebookBot(username=bot_options.username,
                         lockfile=bot_options.lockfile,
                         concurrency=bot_options.concurrency)
    fb_bot.start()
    fb_bot.join()


if __name__ == "__main__":
    parser = OptionParser(usage="Usage: %prog [options]")
    parser.add_option('--url',
                      action='store',
                      type='string',
                      default='http://127.0.0.1:3031',
                      help="[default: %default]")
    parser.add_option('--callback_url',
                      action='store',
                      type='string',
                      default='http://127.0.0.1:3031',
                      help="[default: %default]")
    parser.add_option('--username', action='store', type='string')
    parser.add_option('--password', action='store', type='string')
    parser.add_option(
                     '--concurrency',
                     metavar = 'N',
                     action  = 'store',
                     type    = 'int',
                     default = 4,
                     help    = "number of post-creating threads [default: %%default]"
    )
    parser.add_option('--lockfile',
                      action='store',
                      type='string',
                      default='/tmp/facebook_bot2.lock',
                      help="[default: %default]")
    parser.add_option('--mode',
                      action='store',
                      type='string',
                      default='dev',
                      help="mode: %s [default: %%default]" % ', '.join(DB_NAME_MAP))
    (options, args) = parser.parse_args()

    if not (options.username and options.password):
        parser.print_help()
        sys.exit(1)

    LOG_FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
    setup_logger(LOGGER, level=LOG_LEVEL, format=LOG_FORMAT, patch_logging=True)

    main(options)
