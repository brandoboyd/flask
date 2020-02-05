# coding=utf-8

import unittest

from .base import BaseCase

from solariat_bottle.db.filters import FilterTranslator


class FiltersTestCase(BaseCase):

    filter_equivalents = [
        ('(EN_VO>=10) & (ROG_CXCARE_SERV_CBL>=25)',
         {'$and': [{'EN_VO': {'$gte': 10}},
                   {'ROG_CXCARE_SERV_CBL': {'$gte': 25}}]}),

        ('(EN_VO>=25) & (ROG_T1_TV>=19)',
         {'$and': [{'EN_VO': {'$gte': 25}},
                   {'ROG_T1_TV': {'$gte': 19}}]}),

        ('(EN_VO>=25) & (ROG_BSD_WIR_MSD>=25)',
         {'$and': [{'EN_VO': {'$gte': 25}},
                   {'ROG_BSD_WIR_MSD': {'$gte': 25}}]}),

        ('(ROG_CXCARE_SERV_WIR>=15 | ROG_CXCARE_LOY_WIR>=15) & (FR_VO>=25)',
         {'$and': [{'$or': [{'ROG_CXCARE_SERV_WIR': {'$gte': 15}},
                            {'ROG_CXCARE_LOY_WIR': {'$gte': 15}}]},
                   {'FR_VO': {'$gte': 25}}]}),

        ('(FR_VO>=10) & (FDO_GENINQ>=19)',
         {'$and': [{'FR_VO': {'$gte': 10}},
                   {'FDO_GENINQ': {'$gte': 19}}]}),

        ('(EN_VO>=9) & (ROG_CXCARE_LOY_CNSL>=19 | ROG_CXCARE_SERV_CNSL>=19)',
         {'$and': [{'EN_VO': {'$gte': 9}},
                   {'$or': [{'ROG_CXCARE_LOY_CNSL': {'$gte': 19}},
                            {'ROG_CXCARE_SERV_CNSL': {'$gte': 19}}]}]}),

        ('(FDO_GENINQ>=19 | FDO_EHO>=19 | FDO_EHO_SMPHN>=19) & (FR_VO>=10)',
         {'$and': [{'$or': [{'FDO_GENINQ': {'$gte': 19}},
                            {'FDO_EHO': {'$gte': 19}},
                            {'FDO_EHO_SMPHN': {'$gte': 19}}]},
                   {'FR_VO': {'$gte': 10}}]})
    ]

    def test_filter_parsing(self):
        for input_string, mongo_query in self.filter_equivalents:
            actual_query = FilterTranslator(input_string).get_mongo_query()
            self.assertDictEqual(actual_query, mongo_query)


