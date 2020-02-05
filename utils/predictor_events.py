import os
import numpy
import pandas

from solariat_bottle.db.predictors.factory import get_or_create

# For trying to GUESS a timestamp
FROM_TS = 946684800 # 01/01/2000
TO_TS = 2524608000  # 01/01/2050


def get_type(pandas_dtype, column_values):
    if pandas_dtype in (object, str, unicode):
        return 'string'
    if pandas_dtype in (float, int, long):
        if max(column_values) < TO_TS and min(column_values) > FROM_TS:
            return 'timestamp'
        return 'integer'
    if pandas_dtype in (bool, ):
        return 'boolean'
    return 'string'


def translate_column(input_col_name):
    return input_col_name.replace(' ', '').replace('-', '').replace('.', '')


def get_data_folder():
    import solariat_bottle.db as db
    bottle_dir = os.path.dirname(os.path.dirname(db.__file__))
    return os.path.join(bottle_dir, 'data', 'v2_data')


def read_file_with_prefix(prefix):
    f_names = os.listdir(get_data_folder())
    for f_n in f_names:
        if f_n.startswith(prefix):
            return os.path.join(get_data_folder(), f_n)


def read_schema(input_file_prefix):
    input_file = read_file_with_prefix(input_file_prefix)
    schemas = []
    dset = pandas.read_csv(input_file, sep='\t')
    for col in dset.columns:
        schemas.append(dict(name=translate_column(col),
                            type=get_type(dset[col].dtype, dset[col].values)))
    return schemas


# class InfomartEvent(Document):
#
#     meta_schema = read_schema('cinfo')
#
#
# class RevenueDeltaEntry(Document):
#
#     meta_schema = read_schema('rev')
#
#
# class NPSEvent(Document):
#
#     meta_schema = read_schema('nps')


def load_raw_data(input_file_prefix, user, channel=None):
    print "Loading raw data!!"
    from solariat_bottle.db.dynamic_classes import InfomartEvent, RevenueEvent, NPSEvent
    class_map = dict(anonymized_infomart=InfomartEvent,
                     anonymized_revenue=RevenueEvent,
                     anonymized_nps=NPSEvent)
    input_file = read_file_with_prefix(input_file_prefix)
    f_data = pandas.read_csv(input_file, sep='\t')
    for _, row_data in f_data.iterrows():
        mongo_data = {}
        if channel:
            mongo_data['channels'] = [channel.id]
        for col_name, col_value in row_data.iteritems():
            if type(col_value) in (str, unicode) or not numpy.isnan(col_value):
                mongo_data[translate_column(col_name)] = col_value
        class_map[input_file_prefix].objects.create_by_user(user, **mongo_data)


# def load_all_files():
    # InfomartEvent.objects.remove(id__ne=1)
    # RevenueDeltaEntry.objects.remove(id__ne=1)
    # NPSEvent.objects.remove(id__ne=1)
    # print InfomartEvent.objects.count()
    # print RevenueDeltaEntry.objects.count()
    # print NPSEvent.objects.count()
    # load_raw_data('cinfo')
    # load_raw_data('rev')
    # load_raw_data('nps')
    # print InfomartEvent.objects.count()
    # print RevenueDeltaEntry.objects.count()
    # print NPSEvent.objects.count()


def push_feedback_data():
    from solariat_bottle.db.user import User
    from solariat_bottle.db.dynamic_classes import InfomartEvent

    user = User.objects.get(email='super_user@solariat.com')
    account = user.account

    i_mart_predictor = get_or_create('Transfer Rate Predictor', str(account.id))
    for imart_entry in list(InfomartEvent.objects()):
        i_mart_predictor.feedback(imart_entry.data,
                                  dict(action_id=imart_entry.EMPLOYEE_ID),
                                  1 if imart_entry.TECHNICAL_RESULT in ('Transferred', 'Conferenced') else 0)


def load_and_push_data(user, account):
    print "Loading and pushing data!"

    from solariat_bottle.db.dynamic_classes import InfomartChannel, RevenueChannel, NPSChannel

    try:
        isc = InfomartChannel.objects.get(account=account,
                                          title="Infomart Channel")
    except InfomartChannel.DoesNotExist:
        isc = InfomartChannel.objects.create_by_user(user,
                                                     account=account,
                                                     title="Infomart Channel")
    load_raw_data('anonymized_infomart', user, isc)

    try:
        rc = RevenueChannel.objects.get(account=account,
                                        title="Revenue Channel")
    except RevenueChannel.DoesNotExist:
        rc = RevenueChannel.objects.create_by_user(user,
                                                   account=account,
                                                   title="Revenue Channel")
    load_raw_data('anonymized_revenue', user, rc)

    try:
        npsc = NPSChannel.objects.get(account=account,
                                      title="NPS Channel")
    except NPSChannel.DoesNotExist:
        npsc = NPSChannel.objects.create_by_user(user,
                                                 account=account,
                                                 title="NPS Channel")
    load_raw_data('anonymized_nps', user, npsc)


# def load_and_push_data():
#     load_all_files()
#     push_feedback_data()
