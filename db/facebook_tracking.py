from solariat.db.abstract import Document, Manager, DBRef, ObjectId
from solariat.db.fields import StringField, NumField, ListField, ReferenceField
from solariat_bottle.db.channel.base import Channel


PAGE, EVENT = 0, 1


def db_ref(object, collection_name=None):
    if isinstance(object, Document):
        if isinstance(object.id, ObjectId):
            return DBRef(object.get_collection_name(), object.id)
    elif isinstance(object, ObjectId) and collection_name is not None:
        return DBRef(collection_name, object)
    else:
        raise TypeError("Can not construct DBRef object from object {} {}". format(type(object), object))


class FacebookTrackingManager(Manager):
    def find_channels(self, object_ids):
        channels = []
        for item in self.find(object_id__in=object_ids):
            channels.extend(item.channels)
        return channels

    def handle_channel_event(self, event, channel, object_ids, object_type):
        """Updates tracking collection when pages/events added or removed from channel"""
        assert event in {"add", "remove"}, "Unexpected event '{}'".format(event)
        assert channel.__class__.__name__ == 'FacebookServiceChannel', "{} is not instance of FacebookServiceChannel".format(channel)
        assert isinstance(object_ids, (list, tuple, set)), "{} is not instance of {}".format(object_ids, (list, tuple, set))
        assert object_type in {PAGE, EVENT}, "Unexpected object type '{}'".format(object_type)

        modifier = {
            "remove": "$pull",
            "add": "$addToSet"
        }[event]

        F = self.doc_class.F
        result = {}
        for object_id in set(object_ids):
            query = {F.object_id: object_id,
                     F.object_type: object_type}
            update = {modifier: {F.channels: db_ref(channel)}}
            result[object_id] = self.coll.find_and_modify(query, update, upsert=True, new=True)

        if event == "remove":
            # remove entries with empty channels list
            for item in self.coll.find({'$or': [{F.channels: {'$eq': []}}, {F.channels: {'$exists': False}}]}):
                self.coll.remove({'_id': item['_id']})
        return result


class FacebookTracking(Document):
    """Holds tracked facebook page and event ids. Used for facebook channels lookup."""
    object_id = StringField()
    object_type = NumField(choices=[PAGE, EVENT])
    channels = ListField(ReferenceField(Channel))

    manager = FacebookTrackingManager
    indexes = ['channels', 'object_id']
