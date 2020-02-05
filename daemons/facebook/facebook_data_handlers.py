import json
from abc import ABCMeta, abstractmethod
from solariat_bottle.settings import LOGGER
from solariat_bottle.utils.facebook_extra import permalink_comment, permalink_post

class __BaseFBDataHandler():

    __metaclass__ = ABCMeta

    def update_with_user_profile(self, data_item, sender_id, driver):

        user_profile = driver.get_object(sender_id)
        data_item['user_profile'] = {}
        if 'name' in user_profile:
            data_item['user_profile']['user_name'] = user_profile['name']
        if 'username' in user_profile:
            data_item['user_profile']['id'] = user_profile['username']
        picture = driver.get_object(sender_id + '/picture')
        if picture and picture['data'] and not picture.get('is_silhouette', False):
            data_item['user_profile']['profile_image_url'] = picture['url']
        if 'location' in user_profile:
            if isinstance(user_profile['location'], dict):
                if 'city' in user_profile['location']:
                    data_item['user_profile']['location'] = user_profile['location']['city']
                elif 'country' in user_profile['location']:
                    data_item['user_profile']['location'] = user_profile['location']['country']
            elif isinstance(user_profile['location'], basestring):
                    data_item['user_profile']['location'] = user_profile['location']

    def update_with_channels(self, data_item, sender_id, outbound_ids, matched_channels):

        if sender_id in outbound_ids:
            # If the sender is the same as the authenticated user, it's an outbound post
            service_chns = [str(c.outbound_channel.id) for c in matched_channels if c.outbound_channel]
        else:
            # Otherwise we have an inbound post.
            service_chns = [str(c.inbound_channel.id) for c in matched_channels if c.inbound_channel]

        data_item['channels'] = service_chns

    def prepare(self, data, target_id, channel, driver):

        matched_channels = [channel]

        if not matched_channels:
            LOGGER.warn('Matched channels for %s EnterpriseFacebookChannel not found', channel.id)

        outbound_ids = []
        if channel.facebook_handle_id:
            outbound_ids.append(str(channel.facebook_handle_id))
        if channel.facebook_page_ids:
            outbound_ids.extend(channel.facebook_page_ids)


        post_fields = {}
        post_fields.update(self.handle(data, target_id))
        sender_id = post_fields.pop('sender_id')
        self.update_with_channels(post_fields, sender_id, outbound_ids, matched_channels)
        self.update_with_user_profile(post_fields, sender_id, driver)

        return post_fields


    @abstractmethod
    def handle(self, data, target_id):
        '''place data handling logic there'''


class _PostHandler(__BaseFBDataHandler):

    def handle(self, data, target_id):

        post_fields = {}
        status_id = str(data['id'])
        post_fields['id'] = status_id
        post_fields['url'] = permalink_post(status_id)
        post_fields['facebook'] = {'_wrapped_data': json.dumps(data)}
        post_fields['facebook']['target_id'] = str(target_id)
        if data['type'] in ('photo', 'video'):
            post_fields['facebook']['attachments'] = True
        post_fields['facebook']['created_at'] = data['created_time']
        post_fields['content'] = data.get('message') if 'message' in data else data.get('link')
        if not post_fields['content']:
            raise Exception("No content found for message id=%s. Cannot create post!" % status_id)
        post_fields['facebook']['facebook_post_id'] = status_id

        if 'from' in data:
            sender_id = data['from']['id']
        else:
            raise Exception("Not possible to define who is sender")

        post_fields['sender_id'] = sender_id
        post_fields['comments'] = data.get('comments', {'data':[]}).get('data')
        return post_fields


class _CommentHandler(__BaseFBDataHandler):

    def handle(self, data, target_id):

        post_fields = {}
        comment_id = str(data['id'])
        post_fields['facebook'] =  {'_wrapped_data': json.dumps(data)}

        if '_' not in comment_id:
            comment_id = '%s_%s' % (target_id, comment_id)

        post_fields['url'] = permalink_comment(target_id, comment_id)

        post_fields['facebook']['target_id'] = str(target_id)
        post_fields['facebook']['created_at'] = data['created_time']
        post_fields['facebook']['facebook_post_id'] = comment_id
        post_fields['content'] = data.get('message')
        if not post_fields['content']:
            raise Exception("No content found for comment id=%s. Cannot create post!" % comment_id)
        post_fields['facebook']['in_reply_to_status_id'] = target_id

        if 'parent' in data:
            # This is on second level comment e.g. comment to a comment
            # For facebook bot at least, not sure if same case here
            post_fields['facebook']['root_post'] = post_fields['facebook']['in_reply_to_status_id']
            post_fields['facebook']['in_reply_to_status_id'] = data['parent'].get('id', target_id)
            post_fields['facebook']['second_level_reply'] = True

        if 'from' in data:
            sender_id = data['from']['id']
        else:
            raise Exception("Not possible to define who is sender")

        post_fields['sender_id'] = sender_id
        return post_fields


class _PrivateMessageHandler(__BaseFBDataHandler):

    def handle(self, data, target_id):

        post_fields = {}
        message_id = str(data['id'])
        post_fields['id'] = message_id
        post_fields['url'] = 'http://www.facebook.com' #need to rework in future, but for current moment not clear how to create direct link to pm
        post_fields['facebook'] =  {'_wrapped_data': json.dumps(data)}
        post_fields['facebook']['facebook_post_id'] = message_id

        post_fields['facebook']['target_id'] = str(target_id)
        if 'attachments' in data:
            post_fields['facebook']['attachments'] = True
        post_fields['facebook']['created_at'] = data['created_time']
        post_fields['content'] = data.get('message') if 'message' in data else data.get('link')
        post_fields['facebook']['conversation_id'] = data['conversation_id']
        post_fields['facebook']['page_id'] = data['page_id']

        if 'root_post' in data:
            post_fields['facebook']['in_reply_to_status_id'] = data['root_post']

        if 'from' in data:
            sender_id = data['from']['id']
        else:
            raise Exception("Not possible to define who is sender")

        post_fields['sender_id'] = sender_id
        return post_fields


class _DefaultHandler(__BaseFBDataHandler):

    def handle(self, data, target_id):
        return data


class FBDataHandlerFactory(object):

    POST = 'post'
    COMMENT = 'comment'
    DEFAULT = 'default'
    PM = 'private_message'

    __mapping ={
        POST: _PostHandler(),
        COMMENT: _CommentHandler(),
        PM: _PrivateMessageHandler(),
        DEFAULT: _DefaultHandler()
    }

    @classmethod
    def get_instance(cls, selector):
        return cls.__mapping[selector]

