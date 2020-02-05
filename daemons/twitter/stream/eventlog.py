from solariat.metacls import Singleton
from solariat.utils.timeslot import now, timedelta

DEFAULTS = dict(
    UserStreamDbEvents=dict(
        events='twsbot_events',
        messages='twsbot_messages',
        status='twsbot_status'
    ),
    PublicStreamDbEvents=dict(
        events='twsbot_pub_events',
        messages='twsbot_pub_messages',
        status='twsbot_pub_status'
    )
)


class Events(object):
    """
    OFFLINE     the userstream has been stopped due to reconnect or bot stop
    KEEP_ALIVE  userstream received message
    ONLINE      userstream connected
    SUSPEND     userstream removed because of channel deactivation
    """
    EVENT_OFFLINE = -1
    EVENT_KEEP_ALIVE = 0
    EVENT_ONLINE = 1
    EVENT_SUSPEND = 2


class InMemEvents(Events):
    def __init__(self):
        self.events = []
        self.messages = []

    def add_message(self, username, message, timestamp):
        self.messages.append((username, message, timestamp))

    def add_event(self, evt_type, username, timestamp, status_id):
        self.events.append((evt_type, username, timestamp, status_id))

    def last_offline(self, username):
        online_events = filter(lambda e: e[1] == username and e[0] == self.EVENT_OFFLINE, self.events)
        if online_events:
            from operator import itemgetter
            return sorted(online_events, key=itemgetter(2))[-1]


class DbEvents(Events):
    __metaclass__ = Singleton

    def __init__(self):
        import pymongo
        from solariat.db.mongo import get_connection

        collection_names = DEFAULTS.get(self.__class__.__name__)
        conn = get_connection()
        self.MESSAGES_COLLECTION = collection_names['messages']
        self.EVENTS_COLLECTION = collection_names['events']
        self.STATUS_COLLECTION = collection_names['status']

        self.messages_coll = conn[self.MESSAGES_COLLECTION]
        self.events_coll = conn[self.EVENTS_COLLECTION]
        self.status_coll = conn[self.STATUS_COLLECTION]
        self.events_coll.create_index(
            [("t", pymongo.DESCENDING),
             ("u", pymongo.ASCENDING),
             ("m", pymongo.ASCENDING)], background=True)

    def add_message(self, reference, message, timestamp):
        ref_id = self.get_ref_id(reference)
        self.messages_coll.insert({"u": ref_id, "m": message, "t": timestamp})

    def add_event(self, evt_type, reference, timestamp, status_id):
        ref_id = self.get_ref_id(reference)
        self.events_coll.insert({"u": ref_id, "m": evt_type, "t": timestamp, "s": status_id})

    def add_bot_status(self, bot_status):
        self.status_coll.insert(bot_status)

    @classmethod
    def get_ref_id(cls, ref):
        from solariat.db.fields import BytesField

        if isinstance(ref, long):
            ref_id = BytesField().to_mongo(ref)
        elif hasattr(ref, 'id'):
            ref_id = ref.id
        else:
            ref_id = ref
        return ref_id

    def last_online(self, reference):
        """Returns the last event for stream
        referenced by username or stream ref
        if it's not SUSPEND, otherwise None.

        If the last event is ONLINE or KEEP_ALIVE,
        then bot was probably killed with SIGKILL.
        """
        def event_tuple(item):
            if not item:
                return None
            return item['m'], item['u'], item['t'], item['s']

        last_event = None
        ref_id = self.get_ref_id(reference)
        query = {"t": {"$gt": now() - timedelta(hours=1)},
                 "u": ref_id}
        for item in self.events_coll.find(query).sort([("t", -1), ("_id", -1)]).limit(1):
            if item['m'] != Events.EVENT_SUSPEND:
                last_event = item
        return event_tuple(last_event)


class UserStreamDbEvents(DbEvents):
    pass


class PublicStreamDbEvents(DbEvents):
    pass