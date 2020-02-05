import uuid
import pytz
from bson.code import Code

from solariat_bottle.settings import LOGGER
from solariat.utils.parsers.base_parser import BaseParser, register_operator, CUSTOM_OPERATORS
from solariat_bottle.utils.id_encoder import USER_NUM_WIDTH, pack_event_id


PREDICTOR_TRAINING_BATCH_SIZE = 100


def _get_id_query(from_dt, to_dt, model):
    # although USER_NUM_WIDTH is defined as 30 in utils/id_encoder.py, value greater or equal to 20 will raise
    # OverflowError: MongoDB can only handle up to 8-byte ints
    USER_NUM_WIDTH = 20
    min_actor_num = 0
    max_actor_num = (1 << USER_NUM_WIDTH) - 1

    from_dt = from_dt.replace(tzinfo=pytz.UTC)
    to_dt = to_dt.replace(tzinfo=pytz.UTC)

    min_id = pack_event_id(min_actor_num, from_dt)
    max_id = pack_event_id(max_actor_num, to_dt)

    query = {
            '_id': {'$gte': min_id, '$lte': max_id},
            '_t': model.__name__,
    }

    return query


# EXPRESSIONS
def collect_collection(predictor, from_dt, to_dt, coll):
    LOGGER.debug("Running collect_collection for predictor %s", predictor.name)

    query = _get_id_query(from_dt, to_dt, coll)
    LOGGER.debug("Query for collecting data: %s" % query)
    cursor = coll.objects.coll.find(query)
    predictor.insert_training_data_batch(cursor)
    LOGGER.debug("Collected #%d training data for predictor %s", cursor.count(), predictor.name)


def union_collection(predictor, from_dt, to_dt, left_coll, right_coll, left_key, right_key, drop_temp_coll=True):
    """
    Uses mongodb map_reduce to join documents from left_coll and right_coll matched by
    left_key on left_coll and right_key on right_coll.
    Document fields from right_coll will overwrite document fields from left_coll

    In case of error, temp collection will be dropped, even if drop_temp_coll is False
    """

    LOGGER.debug("Running union_collection for predictor %s", predictor.name)

    # temporary mongodb collection
    joined_coll_name = 'union_collection_%s' % str(uuid.uuid1()).replace('-', '_')

    _db_left_key = left_coll.F(left_key)
    _db_right_key = right_coll.F(right_key)

    left_mapper = Code("""
        function () {
           // TODO: only emit fields required for context, currently all fields in document are emitted by 'this'
           emit(this.%s, this);
        }
    """ % _db_left_key)

    right_mapper = Code("""
        function () {
           // TODO: only emit fields required for context, currently all fields in document are emitted by 'this'
           emit(this.%s, this);
        }
    """ % _db_right_key)

    reducer = Code("""
        function(key, values) {
            // con: when value of left_key or right_key is not unique in their respective collections,
            // reducer will run, setting this __joined = true, even when left_coll & right_coll don't 'match'
            var result = {__joined: true};

            values.forEach(function (value) {
                // to confirm: we don't need to check hasOwnProperty?
                for (k in value) {
                    result[k] = value[k];
                }
            });

            return result;
        }
    """)

    left_query = _get_id_query(from_dt, to_dt, left_coll)
    right_query = _get_id_query(from_dt, to_dt, right_coll)

    db = right_coll.objects.coll.database

    data_count = [0]

    def gen_joined_data():
        for each in db[joined_coll_name].find({'value.__joined': True}):
            data_count[0] += 1
            yield each['value']

    try:
        # right_coll first because its data dict needs to 'update' data dict from left_coll
        right_coll.objects.coll.map_reduce(right_mapper, reducer, joined_coll_name, query=right_query)

        # left_coll: data dict from left_coll appears first in reducer's values Array
        left_coll.objects.coll.map_reduce(left_mapper, reducer, {'reduce': joined_coll_name}, query=left_query)

        context_generator = gen_joined_data()
        predictor.insert_training_data_batch(context_generator)
    except Exception, err:
        # won't fail even if joined_coll_name doesn't exist
        db[joined_coll_name].drop()
        raise

    if drop_temp_coll:
        db[joined_coll_name].drop()
    else:
        return db[joined_coll_name]

    LOGGER.debug("Collected #%d training data for predictor %s", data_count[0], predictor.name)


def is_in(value, container):
    return value in container


def attribute_val(itx_context, value):
    if isinstance(itx_context, dict):
        return itx_context.get(value)
    else:
        return getattr(itx_context, value)


# operators registry
UNIQ_OPERATORS = {
    'isin': is_in
}
UNIQ_OPERATORS.update(CUSTOM_OPERATORS)
DB_OPERATORS = {
    'union': union_collection,
    'collect': collect_collection,
    'attribute_value': attribute_val,
}
OPERATOR_REGISTRY = dict(UNIQ_OPERATORS, **DB_OPERATORS)
