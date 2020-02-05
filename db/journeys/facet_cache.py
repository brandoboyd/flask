
import json 

from hashlib import md5
from datetime import datetime

from solariat.db import fields
from solariat_bottle.db.auth import AuthDocument
from solariat_bottle.settings import get_var

from functools import wraps


def facet_cache_decorator(page_type):
    def decorator_func(compute_data_func):
        @wraps(compute_data_func)
        def wrapped(*args, **kwargs):
            assert kwargs
            params = kwargs['params']
            _self_ = args[0]
            account_id = _self_.user.account.id
            hashcode, cache = FacetCache.get_cache(params, account_id, page_type)
            if params['force_recompute']:
                data = compute_data_func(*args, **kwargs)
                FacetCache.upsert_cache_record(hashcode, data, page_type, account_id)
            else:
                if cache:
                    data = json.loads(cache.value)
                    data['is_up_to_date'] = cache.is_up_to_date()
                else:
                    data = compute_data_func(*args, **kwargs)
                    FacetCache.upsert_cache_record(hashcode, data, page_type, account_id)

            return data
        return wrapped
    return decorator_func


class FacetCache(AuthDocument):

    collection = "FacetCache"

    hashcode = fields.StringField(db_field='hc', required=True)
    page_type = fields.StringField(db_field='pe', required=True)
    account_id = fields.ObjectIdField(db_field='aid', required=True)
    value = fields.StringField(db_field='ve', required=True)
    created_at = fields.DateTimeField(db_field='ct', required=True)

    def is_up_to_date(self):
        delta = datetime.now() - self.created_at
        return delta.total_seconds() < get_var('MONGO_CACHE_EXPIRATION')  # 30 mins

    @classmethod
    def upsert_cache_record(cls, hashcode, data, page_type, account_id):
        now = datetime.now()
        if 'time_stats' in data:
            del data['time_stats']
        if 'pipelines' in data:
            del data['pipelines']
        cache_records = FacetCache.objects(hashcode=hashcode, account_id=account_id, page_type=page_type)
        cache_records_num = cache_records.count()
        if cache_records_num >= 2:
            raise Exception('Too many cache records')
        elif cache_records_num == 1:
            cache = cache_records[0]
            cache.value = json.dumps(data)
            cache.created_at = datetime.now()
            cache.save()
        else:
            cache = FacetCache(
                hashcode=hashcode,
                value=json.dumps(data),
                account_id=account_id,
                page_type=page_type,
                created_at=now)
            cache.save()

    @classmethod
    def get_cache(cls, params, account_id, page_type):
        hash_arg = params.copy()
        # import ipdb; ipdb.set_trace()
        for field in ['force_recompute', 'range_alias']:
            if field in hash_arg:
                del hash_arg[field]
        hashcode = md5(str(hash_arg)).hexdigest()
        cache_candidates = FacetCache.objects(
            hashcode=hashcode,
            account_id=account_id,
            page_type=page_type)
        if not cache_candidates:
            return hashcode, None
        elif 1 == len(cache_candidates):
            return hashcode, cache_candidates[0]
        else:
            for cache in cache_candidates:
                cache.remove()
            return hashcode, None
            # raise Exception('Too many FacetCache records found for given params: %s' % hash_arg)


