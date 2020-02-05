from datetime import datetime
import logging

import pytz

from solariat_nlp import classify_content
from .base import BaseAPIView, api_request
from solariat.utils.timeslot import utc
from solariat_bottle.db.post.nps import NPSPost, NPSOutcome
from solariat_bottle.db.post.voc import DEFAULT_POST_CONTENT, VOC_DATETIME_FORMAT

DATE_FORMAT = '%d/%m/%Y %H:%M:%S'


class VocView(BaseAPIView):

    endpoint = 'voc'

    @api_request
    def get(self, user, **kwargs):
        assert kwargs.get('survey_id'), kwargs.get('survey_id')
        voc_post = NPSPost.objects.get(survey_response_name=kwargs['survey_id'])
        smart_tags = voc_post.computed_tags
        topics   = []
        for item in classify_content(voc_post.plaintext_content):
            topics.append({
                'intention_type': item['intention_type'],
                'intention_topics': item['intention_topics']
            })
        tags = [ch.title for ch in smart_tags]
        tags = list(set(tags).difference(set(['Passive', 'Promoter', 'Detractor'])))
        data = {
            'survey_id': voc_post.survey_response_name,
            'tags': tags,
            'topics': topics,
        }
        return data

    @api_request
    def post(self, user, **kwargs):
        # convert old request data to new request format
        if 'username' in kwargs:
            kwargs['_nps_type'] = 'score'
            case_number = kwargs.pop('username')
            kwargs['content'] = kwargs.pop('verbatim')
            kwargs['response_type'] = kwargs.pop('response_type')
            kwargs['survey_response_name'] = kwargs.pop('survey_id')
            kwargs['nps_rating'] = 0
            kwargs['case_update_id'] = kwargs.get('Case Update: ID') or kwargs.get('survey_id')
            kwargs['description'] = kwargs.get('Description') or kwargs.get('description')
        else:
            case_number = kwargs.get('Case Number') or kwargs.get('Case: Case Number') or kwargs.get('case_number')
            assert case_number, "'Case Number' is required."

        CustomerProfile = user.account.get_customer_profile_class()
        CustomerProfile.objects.get_or_create(case_number=case_number)

        if 'nps_score' not in kwargs:
            params = dict(case_number=case_number,
                          case_update_id=kwargs['case_update_id'],
                          type=kwargs['response_type'],
                          content=kwargs['content'],
                          description=kwargs['description'],
                          channels=[kwargs['channel']],
                          survey_response_name=kwargs.get('survey_response_name', ''),
                          is_inbound=True)
            try:
                params['_created'] = pytz.utc.localize(datetime.strptime(kwargs['Created Date'], VOC_DATETIME_FORMAT))
            except Exception, err:
                logging.warn(err)
            try:
                params['last_modified'] = pytz.utc.localize(datetime.strptime(kwargs['Last Modified Date'], VOC_DATETIME_FORMAT)),
            except Exception, err:
                logging.warn(err)

            data = NPSPost.objects.create_by_user(user, native_id=params['case_number'] + str(datetime.now()),
                                                  **params)

        else:
            params = dict(_created=utc(datetime.strptime(kwargs['created_at'], DATE_FORMAT)),
                          case_number=case_number,
                          actor_id=case_number,
                          response_type=kwargs['response_type'],
                          score=int(kwargs['nps_score']) if kwargs['nps_score'] else None,
                          content=kwargs['verbatim'] or DEFAULT_POST_CONTENT,
                          survey_response_name=kwargs.get('survey_response_name', ''),
                          channels=[kwargs['channel']],
                          reward_data=kwargs['reward_data'],
                          assigned_tags=kwargs['assigned_tags'],
                          customer_info=kwargs['customer_info'],
                          is_inbound=False)
            data = NPSOutcome.objects.create_by_user(user, **params)

        return data.to_dict()
