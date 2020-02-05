from datetime import datetime

from solariat.db import fields
from .user     import User
from solariat.db.abstract import Document, Manager


class TaskMessageManager(Manager):

    def create_message(self, user, content, message_type):
        message = TaskMessage(**{'user':str(user.id), 'content':content, 'type':message_type})
        message.save()
        return message

    def create_error(self, user, content):
        return self.create_message(user, content, 'error')

    def create_info(self, user, content):
        return self.create_message(user, content, 'info')


class TaskMessage(Document):
    '''
    Internal Structure representing the integartion
    data structure with a data stream provider.
    '''
    _created = fields.DateTimeField(db_field='ca', default=datetime.now())
    content = fields.StringField(db_field='ct', required=True)
    type = fields.StringField(db_field='tp', required=True)
    user = fields.ListField(fields.ReferenceField(User))

    manager = TaskMessageManager

    def add_item(self):
        ''' Increment counters'''
        self._update_item(1)

    def remove_item(self):
        ''' Decrement counters or remove if empty '''
        if self.entry_count >= 2:
            self._update_item(-1)
        else:
            self.delete()

    def set_datasift_hash(self, datasift_hash):
        " set atomically datasift hash and update last_sync "

        return self.objects.coll.find_and_modify(
            query={'_id': self.id},
            update={'$set': {
                self.fields['datasift_hash'].db_field: datasift_hash,
                self.fields['last_sync'].db_field: datetime.now()}},
            new=True)
