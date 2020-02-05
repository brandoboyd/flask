# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_nlp.sa_labels import SATYPE_NAME_TO_ID_MAP, ALL_SATYPES

from ..utils.id_encoder import (
    TOPIC_WIDTH,
    get_topic_hash, get_channel_num,
    get_status_code, get_intention_id, get_post_hash,
    pack_components, unpack_components,
    pack_stats_id, unpack_stats_id, revert_pack_components
)
from solariat.utils.timeslot import Timeslot
from solariat.db.abstract import Document
from solariat.db.fields import BytesField, NumField
from ..db.speech_act  import (SpeechActMap,
    pack_speech_act_map_id, unpack_speech_act_map_id)
from .base import TestCase, BaseCase, GhostPost

class IdEntity(Document):
    id    = BytesField(db_field='_id', unique=True, required=True)
    count = NumField()

class TimeSlotBytesId(Document):
    id = BytesField(db_field='_id', unique=True, required=True)
    time_slot = NumField()
    dummy = NumField()

class TimeSlotIntegerId(Document):
    id = NumField(db_field='_id', unique=True, required=True)
    time_slot = NumField()
    dummy = NumField()


class MongoIntegrationTestCase(BaseCase):
    def test_mongo_stats_id(self):
        original = (
            15,             # channel_num
            "Hello World",  # topic
            2,              # status code
            999999          # timeslot
        )
        st_id = pack_stats_id(*original)

        self.assertTrue(st_id > 0)
        IdEntity(id=str(st_id), count=10).save()
        self.assertEqual(IdEntity.objects.count(), 1)
        self.assertEqual(IdEntity.objects(id=str(st_id)).count(), 1)

    def test_mongo_speech_act_map_id(self):
        sam_id = pack_speech_act_map_id(
            1234,                      # channel_id
            2,                          # status
            12345,                      # timeslot
            98765,                      # post
        )
        self.assertTrue(sam_id > 0)
        IdEntity(id=str(sam_id), count=10).save()
        self.assertEqual(IdEntity.objects.count(), 1)


class IDEncoderTestCase(BaseCase):

    def test_get_topic_hash(self):
        hashed = get_topic_hash("Hello world")
        self.assertTrue(len(bin(hashed)) < 2 + (1<<TOPIC_WIDTH))

        self.assertEqual(get_topic_hash(123456), 123456)
        self.assertEqual(get_topic_hash(None),   0)

    def test_get_channel_num(self):
        # by number
        self.assertTrue(get_channel_num(15) == 15)
        # by channel
        self.assertTrue(get_channel_num(self.channel) == self.channel.counter)
        # by object-id
        self.assertTrue(get_channel_num(self.channel.id) == self.channel.counter)

    def test_get_status_code(self):
        # by code
        self.assertTrue(get_status_code(3) == 3)
        # by str representation of code
        self.assertTrue(get_status_code('2') == 2)
        # by name
        for name, code in SpeechActMap.STATUS_MAP.items():
            self.assertTrue(get_status_code(name)         == code)
            self.assertTrue(get_status_code(name.upper()) == code)

    def test_get_intention_id(self):
        # by id
        self.assertTrue(get_intention_id(3) == 3)
        # by str representation of id
        self.assertTrue(get_intention_id('2') == 2)
        # by name
        for name, oid in SATYPE_NAME_TO_ID_MAP.items():
            self.assertTrue(get_intention_id(name)         == int(oid))
            self.assertTrue(get_intention_id(name.upper()) == int(oid))
        # by SAType instance
        for satype in ALL_SATYPES:
            self.assertTrue(get_intention_id(satype) == int(satype.oid))

    def test_pack_unpack_components(self):
        big_value  = 12345678901234567890
        widths     = (3, 7, 5, 11, 1, 23)
        components = [(big_value, w) for w in widths]

        packed = pack_components(*components)
        self.assertTrue(len(bin(packed)) <= sum(w for _,w in components) + 2)

        masked   = tuple((val & ((1L<<w)-1)) for val,w in components)
        unpacked = unpack_components(packed, *widths)
        self.assertEqual(masked, unpacked)

    def test_reversed_packing(self):
        #01 11 <=> 11 10 = 14
        self.assertEquals(revert_pack_components((1, 2), (3, 2)), 14L)
        # 100101 1110 <=> 0111 101001 = 489
        self.assertEquals(revert_pack_components((37, 6), (14, 4)), 489L)

    def test_pack_unpack_stats_id(self):
        original = (
            1234,   # channel_num
            987654,  # topic_hash
            2,       # status code
            1122334  # timeslot
        )
        st_id    = pack_stats_id(*original)
        unpacked = unpack_stats_id(st_id)

        self.assertEqual(original, unpacked)

        ts = Timeslot('2013-04-22 21:40')
        original = (
            self.channel,   # channel
            "Hello World",  # topic
            'accepted',     # status
            ts              # timeslot
        )
        st_id    = pack_stats_id(*original)
        unpacked = unpack_stats_id(st_id)

        self.assertEqual(original[0].counter,          unpacked[0])
        self.assertEqual(get_topic_hash(original[1]),  unpacked[1])
        self.assertEqual(get_status_code(original[2]), unpacked[2])
        self.assertEqual(original[3].timeslot,         unpacked[3])


    def test_pack_unpack_speech_act_map_id(self):
        original = (
            1234,   # channel_id
            2,       # status
            987654,  # timeslot
            557799,  # post_hash
        )

        sam_id   = pack_speech_act_map_id(*original)
        unpacked = unpack_speech_act_map_id(sam_id)
        self.assertEqual(original, unpacked)

        post = GhostPost()
        original = (
            1234,                    # channel_id
            2,                        # status
            987654,                   # timeslot
            post,                     # post
            0
        )

        sam_id   = pack_speech_act_map_id(*original)
        unpacked = unpack_speech_act_map_id(sam_id)

        self.assertEqual(original[:2],                  unpacked[:2])
        self.assertEqual(get_post_hash(original[3], 0), unpacked[3])


class RangeQueriesTest(TestCase):
    def test_integer_id(self):
        def make_id_ts_left(time_slot, dummy):
            components = (
                (time_slot, 22),
                (dummy, 42),

            )
            id_ = pack_components(*components)
            return id_

        def make_id_ts_right(time_slot, dummy):
            components = (
                (dummy, 42),
                (time_slot, 22)
            )
            id_ = pack_components(*components)
            return id_

        TimeSlotIntegerId.objects.coll.remove()
        from solariat.utils.timeslot import datetime_to_timeslot, parse_date_interval, timedelta, timeslot_to_datetime
        start_date, end_date = parse_date_interval('02/21/2013', '05/21/2013')
        step = timedelta(hours=24)
        dates = []
        while start_date < end_date:
            dates.append(start_date)
            start_date += step
        assert len(dates) == 90

        data = enumerate(dates[::-1], start=100)

        for dummy, date in data:
            dummy %= 5
            time_slot = datetime_to_timeslot(date)
            id_ = make_id_ts_left(time_slot, dummy)
            doc = TimeSlotIntegerId(id=id_, time_slot=time_slot, dummy=dummy)
            doc.save()
        #print list(TimeSlotIntegerId.objects.coll.find())

        #fetch interval
        start_date, end_date = parse_date_interval('03/21/2013', '04/21/2013')
        #start_dummy = 0
        #end_dummy = (1L << 41) - 1
        start_id = make_id_ts_left(datetime_to_timeslot(start_date, 'hour'), 0)
        end_id = make_id_ts_left(datetime_to_timeslot(end_date, 'hour'), 0)
        # print start_id.bit_length()
        # print end_id.bit_length()
        for doc in TimeSlotIntegerId.objects(id__gte=start_id, id__lte=end_id):
            print timeslot_to_datetime(doc.time_slot)
            self.assertGreaterEqual(doc.time_slot, datetime_to_timeslot(start_date, 'hour'))
            self.assertLessEqual(doc.time_slot, datetime_to_timeslot(end_date, 'hour'))

        #raise
