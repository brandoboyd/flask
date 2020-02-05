from solariat_bottle.tests.base import BaseCase
from solariat_bottle.db.sequences import NumberSequences, AutoIncrementField
from solariat.db.abstract import Document


class TestNumberSequences(BaseCase):
    def test_advance(self):
        config = {'SEQUENCE 1': 1,
                  'SEQUENCE 2': 2,
                  'SEQUENCE 3': 3}
        for seq_name, inc_count in config.viewitems():
            value = 0
            for i in range(inc_count):
                value = NumberSequences.advance(seq_name=seq_name)
            self.assertEqual(value, inc_count)
        self.assertTrue(set(config) <= set(NumberSequences.objects.coll.distinct('name')))

    def test_auto_increment_field(self):
        class A(Document):
            counter1 = AutoIncrementField('COUNTER_1')
            counter2 = AutoIncrementField('COUNTER_2')
            counter2_dup = AutoIncrementField('COUNTER_2')

        a = A()
        self.assertEqual((a.counter1, a.counter2, a.counter2_dup), (1, 2, 1))
        a.save()
        self.assertEqual((a.counter1, a.counter2, a.counter2_dup), (1, 2, 1))
        a.reload()
        self.assertEqual((a.counter1, a.counter2, a.counter2_dup), (1, 2, 1))
        A().save()
        a.reload()
        self.assertEqual((a.counter1, a.counter2, a.counter2_dup), (1, 2, 1))

        b = A()
        self.assertEqual((b.counter1, b.counter2, b.counter2_dup), (3, 6, 5))

        c = A.objects.create()
        self.assertEqual((c.counter1, c.counter2, c.counter2_dup), (4, 8, 7))
        c.reload()
        self.assertEqual((c.counter1, c.counter2, c.counter2_dup), (4, 8, 7))
        c = A.objects.get(counter1=4)
        self.assertEqual((c.counter1, c.counter2, c.counter2_dup), (4, 8, 7))
