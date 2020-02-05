# NPS Post type

from solariat_bottle.settings import LOGGER, AppException
from solariat.db import fields
from solariat_bottle.db.channel.base import SmartTagChannel, Channel
from solariat_bottle.db.post.base import Post, PostManager

DEFAULT_POST_CONTENT          = 'No Comment Provided'
VOC_DATETIME_FORMAT           = "%Y-%m-%d %H:%M:%S"
ACCEPTED_RESPONSE_TYPE_VALUES = ['Promoter', 'Passive', 'Detractor']


class VOCPostManager(PostManager):
    '''The VOC Manager of Posts'''

    def create_by_user(self, user, **kw):
        '''Wrapper of the default post creation behaviour.  Auto-assign the respective NPS
        classifier SmartTagChannel after creation.'''
        safe_create = kw.pop('safe_create', False)
        if not safe_create:
            raise AppException("Use db.post.utils.factory_by_user instead")

        channels = Channel.objects.find(id__in=kw['channels'])[:]
        content = kw.get('content', '')
        if content == '':
            kw['content'] = DEFAULT_POST_CONTENT

        LOGGER.debug("Creating VOC Post: {}".format(kw))
        if not "response_type" in kw:
            raise RuntimeError("No response_type for voc post")

        # handling response_type
        response_type = kw.get('response_type')
        if response_type not in ACCEPTED_RESPONSE_TYPE_VALUES:
            raise ValueError("invalid response_type: Expected %s, got: [%s]" % (ACCEPTED_RESPONSE_TYPE_VALUES, response_type))

        nps_channels = [ch.classifiers[response_type] for ch in channels if ch.type_name == "VOC"]

        post = super(VOCPostManager, self).create_by_user(user=user, safe_create=True, **kw)
        # Add the post to the respective NPS Classifier for all channels
        [post.handle_add_tag(user, SmartTagChannel.objects.get(nps_ch), filter_others=False) for nps_ch in nps_channels]
        return post


class VOCPost(Post):

    response_type = fields.StringField(db_field='rt', required=True)
    survey_id = fields.StringField(db_field='sd', required=True)
    manager = VOCPostManager
    

    @property
    def platform(self):
        return 'VOC'

    @property
    def post_type(self):
        return 'private'

    @property
    def _message_type(self):
        return 1

    @property
    def view_url_link(self):
        return "View the Comment"

