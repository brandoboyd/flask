import unittest
import time

from pymongo.errors import DuplicateKeyError

from solariat_bottle          import settings
from solariat_bottle.settings import get_var, LOGGER

from solariat.db.abstract import Document
from solariat.db.fields import NumField

from solariat.utils.timeslot import datetime_to_timeslot, now

from solariat_bottle.tests.base import MainCase


class Transactional(object):
    version = NumField(db_field='_v')

    def upsert(self):
        _v = Transactional.version.db_field
        find_query = self._query
        find_query.pop(_v, None)

        def get_current_version():
            doc = self.objects.coll.find_one({"_id": find_query["_id"]})

            if doc:
                version = doc[_v]
            else:
                version = 1

            if get_var('_TEST_TRANSACTION_FAILURE'):
                time.sleep(1)
            return version


        if hasattr(self, '_upsert_data'):
            update_query = self._upsert_data
            if "$inc" in update_query:
                #if there are other $inc queries - add version as another value
                update_query["$inc"][_v] = 1
            else:
                update_query["$inc"] = {_v: 1}
        else:
            update_query = {"$inc": {_v: 1}}

        tries_counter = 15  #must be >= number of simultaneous processes
        while tries_counter:
            version = get_current_version()
            find_query[_v] = version

            LOGGER.error("Tries count %s", tries_counter)
            try:
                self.objects.coll.update(find_query, update_query, upsert=True, w=1)  #safe=True
            except DuplicateKeyError, e:
                #log error
                LOGGER.error("%s\nfind query=%s\nupdate query=%s", e, find_query, update_query)
                time.sleep(0.5)
            except Exception, e:
                LOGGER.error("Exception: %s", e)
            else:
                break
            tries_counter -= 1

@unittest.skip("proc_num = 1000 takes about 30 sec. test should pass.")
class OptimisticTransaction(MainCase):
    @unittest.skip('')
    def test_fields_inherited(self):

        class Base(Document):
            version = NumField(db_field='v')

        class Child(Base):
            field1 = NumField()

        self.assertIn('version', Child().fields)

        #test mixins
        class Transactional(object):
            version = NumField()

        class Doc(Document, Transactional):
            field1 = NumField()

        self.assertIn('version', Doc().fields)


    def test_transaction(self):
        from solariat_bottle.db.channel_topic_trends import ChannelTopicTrends as T_ChannelTopicTrends
        #
        # class T_ChannelTopicTrends(ChannelTopicTrends, Transactional):
        #     def upsert(self, w=1):
        #         return Transactional.upsert(self)

        time_slot = datetime_to_timeslot(now(), 'month')
        topic = 'laptop'
        from itertools import cycle
        colliding_topics = [
            "oldie", "bt subscribers",
            "pisces woman", "layman"]
        gen_colliding_topics = cycle(colliding_topics)

        status = 0

        def incr_task(topic):
            T_ChannelTopicTrends.increment(channel=self.channel,
                                           time_slot=time_slot,
                                           topic=topic,
                                           status=status,
                                           intention_ids=[1],
                                           inc_dict={'topic_count': 1})
            return True

        # get_var('_TEST_TRANSACTION_FAILURE') = True
        settings.DEBUG      = True
        settings.USE_CELERY = False

        from multiprocessing import Process

        proc_num = 100
        processes = [Process(target=incr_task, args=(gen_colliding_topics.next(),)) for i in range(proc_num)]
        for proc in processes:
            proc.start()
        for proc in processes:
            proc.join()

        for topic in colliding_topics:
            colliding_topics.index(topic)
            doc = T_ChannelTopicTrends(
                channel   = self.channel,
                time_slot = time_slot,
                topic     = topic,
                status    = status
            )
            doc.reload()
            self.assertEqual(doc.filter(intention=1, is_leaf=True)[0].topic_count, proc_num / len(colliding_topics))
            self.assertTrue(doc.version > 1)


if __name__ == '__main__':
    unittest.main()
