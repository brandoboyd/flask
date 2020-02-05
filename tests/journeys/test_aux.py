import unittest
from datetime import timedelta


class TestAggregation(unittest.TestCase):

    def test_agg_with_last(self):
        """Tests $last modifier works as expected"""
        from solariat.db.abstract import Document, fields
        from solariat.utils.timeslot import now

        class Doc(Document):
            journey_id = fields.ObjectIdField()
            created_at = fields.DateTimeField(default=now)
            nps = fields.NumField()
            status = fields.NumField(choices=[0, 1, 2])

        samples = [
            (456, now()-timedelta(minutes=80), 3, 2),
            (456, now()-timedelta(minutes=70), 2, 0),
            (456, now()-timedelta(minutes=99), 5, 0),
            (456, now()-timedelta(minutes=90), 4, 1),

            (123, now()-timedelta(minutes=50), 6, 1),
            (123, now()-timedelta(minutes=80), 3, 2)
        ]
        expected = {
            (456, 2, 0),
            (123, 6, 1)
        }

        for journey_id, created_at, nps, status in samples:
            Doc(journey_id=journey_id, created_at=created_at, nps=nps, status=status).save()

        pipeline = [
            {'$sort': {'created_at': 1}},
            {'$group': {'_id': '$journey_id',
                        'nps': {'$last': '$nps'},
                        'status': {'$last': '$status'}
                        }}
        ]
        res = Doc.objects.coll.aggregate(pipeline)
        assert res['ok'], res
        assert len(res['result']) == len(expected), '%s journeys expected' % len(expected)
        for data in res['result']:
            assert (data['_id'], data['nps'], data['status']) in expected, \
                u"Unexpected aggregation result %s" % unicode(data)

