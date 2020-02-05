from datetime import datetime

from solariat_bottle.db.channel.base import Channel
from solariat_bottle.db.events.event import Event
from solariat_bottle.utils.predictor_events import read_schema

from solariat.utils.timeslot import datetime_to_timestamp
from solariat_bottle.utils.id_encoder import pack_components


def register_dynamic_classes():

    meta_definitions = {'Infomart': {'type': 'csv',
                                     'file_pattern': 'anonymized_infomart',
                                     'id_pattern': [{'name': 'INTERACTION_ID',
                                                     'type': 'long',
                                                     'bits': 33},
                                                    {'name': 'START_TS',
                                                     'type': 'timestamp',
                                                     'format': "%d/%m/%Y %I:%M:%S %p",
                                                     'bits': 30}]},
                        'Revenue': {'type': 'csv',
                                    'file_pattern': 'anonymized_revenue',
                                    'id_pattern': [{'name': 'MAX_of_session_objid',
                                                    'type': 'long',
                                                    'bits': 29},
                                                   {'name': 'MAX_of_session_objid',
                                                    'type': 'timestamp',
                                                    'format': "%d/%m/%Y %I:%M:%S %p",
                                                    'bits': 34}]},
                        'NPS': {'type': 'csv',
                                'file_pattern': 'anonymized_nps',
                                'id_pattern': [{'name': 'INTERACTION_ID',
                                                'type': 'long',
                                                'bits': 29},
                                               {'name': 'START_TS',
                                                'type': 'timestamp',
                                                'format': '%d-%m-%y',
                                                'bits': 34}]}}

    def register_id_func(class_object, id_pattern):

        def make_id(cls, kw):
            components = []
            for id_part in id_pattern:
                if id_part['type'] == 'long':
                    value = long(kw[id_part['name']])
                elif id_part['type'] == 'timestamp':
                    value = datetime_to_timestamp(datetime.strptime(kw[id_part['name']], "%d/%m/%Y %I:%M:%S %p"))
                else:
                    value = str(kw[id_pattern['name']])
                components.append((value, id_part['bits']))
            return pack_components(*components)

        class_object.make_id = classmethod(make_id)

    def register_platform(class_object, platform_name):
        def platform(self):
            return platform_name
        class_object.platform = property(platform)

    for c_name, c_metadata in meta_definitions.iteritems():
        newclass = type(c_name + 'Event', (Event, ), {})

        if c_metadata['type'] == 'csv':
            newclass.meta_schema = read_schema(c_metadata['file_pattern'])

        register_id_func(newclass, c_metadata['id_pattern'])
        register_platform(newclass, c_name)
        globals()[c_name + 'Event'] = newclass

        newclass_channel = type(c_name + 'Channel', (Channel, ), {})
        register_platform(newclass_channel, c_name)
        globals()[c_name + 'Channel'] = newclass_channel


# get_class(name, account)

register_dynamic_classes()