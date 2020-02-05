
import pytz

from .event import Event, EventManager
from datetime import datetime as dt, timedelta
from solariat.db import fields
from solariat_bottle.db.user_profiles.call_profile import CallProfile


class CallEventManager(EventManager):

    def create(self, _id=None, *args, **kw):
        if kw.get('_created'):
            kw['_created'] = dt.strptime(kw['_created'], '%Y-%m-%d %H:%M:%S') + timedelta(days=12*30+15)
            kw['_created'] = pytz.utc.localize(kw['_created'])
            print '-->', kw['_created']
        return super(CallEventManager, self).create(_id=None, *args, **kw)


class CallEvent(Event):

    collection = 'Post'
    manager = CallEventManager
    PROFILE_CLASS = CallProfile

    call_duration = fields.NumField(db_field='cn')  
    catmap = fields.StringField(db_field='cp')  # Sample Valuse: '', 'ENQUIRE_CreditManagement', 'CALLBACK_ACB_A_NOANSWER', 'REPORT_FAULT_Number', 'ENQUIRE_MailBox', 'NO_INPUT_Detected'
    custtype = fields.StringField(db_field='ce')  # Sample values: HOME, BUSINESS, NOT, WHOLESALE; Mostly empty
    servtype = fields.StringField(db_field='se')  # Sample values: INTERNET, MOBILE, FIXED, PAYTV, WIRELESS, ADSL, CABLE, BROADBAND, WIFI, ADSL, DIALUP, CABLE,
    transfer_type = fields.StringField(db_field='te') # Samples values: CTI, ABANDON, HANGUP, CTI_S/S
    sn_segment = fields.StringField(db_field='st') # Samples values: '', Business, Industry, PlatinumConsumer, BusinessCross, Wholesale, Corporate, Test
    sn_contact_reason = fields.StringField(db_field='') # Samples values: 'RequestUsage', 'RequestHelpTcom', 'EnquireExistingComplaint', 'EnquirePlan', 'AssignPlantTCS', 'EscalateInternal717', 'RequestGlobalRoaming'
    sn_contact_type = fields.StringField(db_field='') # Samples values:  'Direct', '', 'Outbound', 'Transfer'
    # call_start_time_melb = fields.StringField(db_field='') # Samples values:  '2014-08-11 13:03:27', '2014-08-25 17:32:55', '2014-08-11 13:03:24'
    sn_service = fields.StringField(db_field='') # Samples values:  '', 'BigpondMusic', 'FoxtelMobile', 'FoxtelBusiness', 'Internet', 'Test', 'ISDN', 'Fax', 'NextG', 'Prepaid', 'DisabilityPhone', 'NextGWirelessLink'
    od_apptag = fields.StringField(db_field='') # Samples values: '', 'enquire-MESSAGE_SERVICES', 'reportFault-PHONE', 'enquire-WAKE_UP_CALL', 'enquire-NBN', 'upgrade-MOBILE_PHONE', 'enquire-BILL', 'enquire-WIRELESS_NETWORK', 'disconnect-INTERNET'
    balance_at_call = fields.NumField(db_field='') # Samples values: '', '360.07', '360.05', '360.04', '360.03', '360.02', '360.01'
    sec_description = fields.StringField(db_field='') # Samples values: '', 'MCO - Broadband faults', 'NEI - Rental lines', 'NHA - General enquiry', '583 - Payphone', 'NHN - Mobile credit', 'N49 - Chk number', 'TSR - Telstra Shop 3 Faults', 'NNJ - Lost phone', 'NEH - Refunds', '359 - Err at Bill/Account', 'ND3 - Account details'



