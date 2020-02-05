from datetime import datetime
from solariat_nlp import classify_content
from .base import BaseAPIView, api_request
from solariat.utils.timeslot import utc
from solariat_bottle.db.post.nps import NPSPost, NPSOutcome
from solariat_bottle.db.user_profiles.nps_profile import NPSProfile

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class NpsView(BaseAPIView):

    endpoint = 'nps'

    @api_request
    def get(self, user, **kwargs):
        assert kwargs.get('native_id'), kwargs.get('native_id')
        nps_post = NPSOutcome.get_by_native_id(kwargs.get('native_id'))
        smart_tags = nps_post.accepted_smart_tags
        topics = []
        for item in classify_content(nps_post.plaintext_content):
            topics.append({
                'intention_type': item['intention_type'],
                'intention_topics': item['intention_topics']
            })
        tags = [ch.title for ch in smart_tags]
        tags = list(set(tags).difference(set(['Passive', 'Promoter', 'Detractor'])))
        data = {
            'survey_id': nps_post.native_id,
            'tags': tags,
            'topics': topics,
        }
        return data

    @api_request
    def post(self, user, **kwargs):
        profile_data = kwargs.pop('nps_profile')
        nps_profile = NPSProfile.objects.get_or_create(**profile_data)
        if 'actor_id' not in kwargs:
            # TODO: Why anonymous customer profile created here?
            CustomerProfile = user.account.get_customer_profile_class()
            customer_profile = CustomerProfile(account_id=user.account.id)
            customer_profile.add_profile(nps_profile)
            # customer_profile = nps_profile.customer_profile
            kwargs['actor_id'] = customer_profile.id

        kwargs['is_inbound'] = True
        kwargs['_created'] = utc(
            datetime.strptime(kwargs['_created'], DATE_FORMAT))

        if 'score' not in kwargs:
            kwargs.pop('response_type')
            data = NPSPost.objects.create_by_user(user, **kwargs)
        else:
            data = NPSOutcome.objects.create_by_user(
                user, user_profile=nps_profile, **kwargs)
        return data.to_dict()



