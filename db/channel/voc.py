from .base import ChannelManager, Channel, SmartTagChannel, ServiceChannel, ServiceChannelManager
from solariat.db import fields

from solariat_nlp.sentiment import POSITIVE, NEGATIVE, NEUTRAL, translate_sentiments_to_intentions
from solariat_nlp.sa_labels import SATYPE_ID_TO_TITLE_MAP

def _map_voc_classifiers_to_intentions(classifier):
    return map(lambda x: SATYPE_ID_TO_TITLE_MAP[x], translate_sentiments_to_intentions([classifier.name]))

VOC_CLASSIFIERS = {
                   'Promoter' : POSITIVE, 
                   'Detractor': NEGATIVE,
                   'Passive'  : NEUTRAL
                  }


class VOCChannelManager(ChannelManager):
    def create(self, **kw):
        kw.update(dict(adaptive_learning_enabled=False))
        return super(VOCChannelManager, self).create(**kw)


class VOCServiceChannelManager(ServiceChannelManager):
    def create(self, **kw):
        kw.update(dict(adaptive_learning_enabled=False))
        return super(ServiceChannelManager, self).create(**kw)

    def create_by_user(self, user, **kw):
        channel = ChannelManager.create_by_user(self, user, 
                                                adaptive_learning_enabled=False, **kw)
        classifiers  = {}
        # Create the automated smart tags: Promoter, Passive, Detractor for this channel
        for tag_name, sentiment_type in VOC_CLASSIFIERS.items():
            stc = SmartTagChannel.objects.create_by_user(
                user,
                title=tag_name,
                description="%s VOC Classifier"%(tag_name),
                parent_channel=channel.inbound_channel.id,
                account=channel.account,
                keywords='DS9R9RKVDC9^&*(V9FD9ACCF90CV99VF',
                #intention_types=_intention_type_names_for_sentiment(sentiment_type),
                status='Active',
                adaptive_learning_enabled=False)
            classifiers[tag_name] = stc.id
        channel.classifiers = classifiers
        channel.save()
        return channel


class VOCChannel(Channel):
    manager = VOCChannelManager

    @property
    def type_name(self):
        return "VOC"

    @property
    def type_id(self):
        return 10

    @property
    def platform(self):
        return "VOC"

    def apply_filter(self, item):
        '''Force all VOC Posts to be actionable, always?'''
        return 'actionable', self


class VOCServiceChannel(VOCChannel, ServiceChannel):

    classifiers = fields.DictField(db_field="cz")

    manager = VOCServiceChannelManager

    @property
    def InboundChannelClass(self):
        return InboundVOCChannel

    @property
    def OutboundChannelClass(self):
        return OutboundVOCChannel

    @property
    def platform(self):
        return "VOC"

    def add_perm(self, user, group=None, to_save=True):
        super(VOCServiceChannel, self).add_perm(user, group, to_save)
        for cls in SmartTagChannel.objects.find(id__in=self.classifiers.values()):
            cls.add_perm(user, group, to_save)

    def post_received(self, post):
        # For now skip this, we don't know if / what we want to process here
        return

    def find_direction(self, post):
        # For now just assume all posts are actionable if posted in one
        # of the channels.
        return 'direct'


class InboundVOCChannel(VOCChannel):

    @property
    def classifiers(self):
        return self.get_service_channel().classifiers

    def get_service_channel(self):
        return VOCServiceChannel.objects.get(self.parent_channel)


class OutboundVOCChannel(VOCChannel):

    @property
    def classifiers(self):
        return self.get_service_channel().classifiers

    def get_service_channel(self):
        return VOCServiceChannel.objects.get(self.parent_channel)
