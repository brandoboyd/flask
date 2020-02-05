# from solariat.utils.parsers.base_parser import BASIC_FUNCS
from copy import deepcopy

BASIC_FUNCS = [
    'int(<value>)',
    'pow(<value>, <value>)',
    'log(<value>)',
    'str(<value>)',
    'aggregate(<input_sequence>, <field_name>, <aggregate_function>)']


def get_standard_functions():
    return deepcopy(BASIC_FUNCS)


def get_journey_expression_functions():
    res = deepcopy(get_standard_functions())
    return res


def get_journey_expression_context():
    from solariat_bottle.db.journeys.customer_journey import CustomerJourney
    funcs = CustomerJourney.get_properties()
    return funcs


def get_stage_context():
    return deepcopy(get_journey_expression_context())


def get_dataset_functions():
    res = deepcopy(get_standard_functions())
    res.append("numeric_range(<field_name>, <list_of_limits>, <list_of_labels>)")
    return res

