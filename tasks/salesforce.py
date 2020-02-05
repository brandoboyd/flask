# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

import json
import requests

from solariat_bottle.settings import AppException, get_var
from solariat_bottle.workers  import io_pool

from .utils import truncate


logger = io_pool.logger


class SalesforceException(AppException):
    pass


# --- IO-worker initialization ----

@io_pool.prefork  # IO-workers will run this before forking
def pre_import_salesforce():
    """ Master init
        Pre-importing heavy modules with many dependencies here
        to benefit from the Copy-on-Write kernel optimization.
    """
    logger.info('pre-importing salesforce dependencies')

    import solariat_bottle.db.account

    # to disable a pyflakes warnings
    del solariat_bottle


# --- SalesForce tasks ---

@io_pool.task
def sf_create_case(conversation, sf_access_token, instance_url):
    """
    Create case on Salesforce that will correspond to conversation using input sf_access_token.

    :param conversation: a Conversation object that does not have Case created for it (no external_id).
    :param sf_access_token: the access token that will be used to post the results.
    """
    from solariat_bottle.db.account import AccessTokenExpired

    if not instance_url or not sf_access_token:
        logger.error("SFDC account is not authorized. Instance url is: %s and access token is %s" % (
                                                                str(instance_url), str(sf_access_token)))
    headers = { 'X-PrettyPrint' : '1',
                'Authorization' : 'Bearer %s' % sf_access_token,
                "Content-Type": "application/json"
                }
    case_resource = '/services/data/v28.0/sobjects/Case/'
    case_url = instance_url + case_resource
    # The Origin for a Case should be the platform for the service channel for the conversation,
    # and the Subject can be the content of the first Post from the conversation.
    first_post = conversation.POST_CLASS.objects.get(id=conversation.posts[0])
    # subject either a string of topics or, if empty, the first post content
    subject = first_post.plaintext_content

    # truncate if necessary
    solariat_id = truncate(str(conversation.id), 'text', 32)
    subject = truncate(subject, 'text', 255)
    description = truncate(' '.join(first_post.topics).strip(), 'text', 32000)

    sfdc_prefix = get_var('SFDC_MANAGE_PACKAGE_PREFIX')

    data = {
        "Origin" : conversation.service_channel.platform,
        sfdc_prefix + "SolariatId__c" : solariat_id,
        "Subject" : subject,
        "Description" : description,
    }

    try:
        resp = requests.post(case_url, data=json.dumps(data), headers=headers)
    except requests.exceptions.ConnectionError:
        raise SalesforceException("Error while connecting to Salesforce")

    if resp.status_code != 201:
        if resp.status_code == 401:
            raise AccessTokenExpired("Invalid or expired token.")
        logger.error(resp.json()[0].get('message', "Sync to salesforce failed for unknown reason."))
    sf_response = resp.json()
    if isinstance(sf_response, list):
        # sf_response is a dict within a list when this is a duplicate post
        message = sf_response[0].get('message', '')
        message = 'Error occured while posting to Salesforce. {}'.format(message)
        logger.error(message)
        raise SalesforceException(message)
    if not sf_response.get('success', False):
        raise AppException(str(sf_response.get('errors', 'An error occured while posting to Salesforce.')))

    case_id = sf_response['id']
    conversation.set_external_id(case_id)
    sf_sync_conversation(conversation, sf_access_token, instance_url)
    return True

@io_pool.task
def sf_close_conversation(conversation):
    """
    Closes conversation on Salesforce side.
    For this we need to patch `Status_in_Social_Optimizr__c` field.
    """
    from solariat_bottle.db.account import AccessTokenExpired

    if not conversation.service_channel.account.account_type == 'Salesforce':
        raise SalesforceException("The account type of this conversation channel is not Salesforce")

    access_token = conversation.service_channel.account.access_token
    instance_url = conversation.service_channel.account.sf_instance_url
    if not instance_url or not access_token:
        logger.error("SFDC account is not authorized. Instance url is: %s and access token is %s" % (
                                                                str(instance_url), str(access_token)))

    headers = {
        'X-PrettyPrint' : '1',
        'Authorization' : 'Bearer %s' % access_token,
        "Content-Type"  : "application/json"
    }

    case_resource = '/services/data/v28.0/sobjects/Case/{}'.format(conversation.external_id)
    case_url = instance_url + case_resource
    print 'Closing case_resource: ', case_resource

    sfdc_prefix = get_var('SFDC_MANAGE_PACKAGE_PREFIX', '')

    data = {
        sfdc_prefix + "Status_in_Social_Optimizr__c": "Closed"
    }

    resp = requests.patch(case_url, data=json.dumps(data), headers=headers)

    # 204 status code means that request went through, but no body was necessary to return
    # this is what Salesforce returns for succesful PATCH request above

    if resp.status_code != 204:
        if resp.status_code == 401:
            # Invalid or expired token, refresh it and try again
            conversation.service_channel.account.refresh_access_token()
            resp = requests.patch(case_url, data=json.dumps(data), headers=headers)

    if resp.status_code == 401:
        raise AccessTokenExpired("Invalid or expired token.")

    # set external_id to None if Case with this id does not exist
    if resp.status_code == 404:
        conversation.external_id = None
        conversation.save()
        raise Exception("Case does not exist. `external_id` is set to `None`.")

    if resp.status_code != 204:
        error_message = "An error occured while posting to Salesforce. "
        error_message += "Response code is: {}".format(resp.status_code)
        logger.error(error_message)
        raise Exception(error_message)

    return True

@io_pool.task
def sf_sync_conversation(conversation, sf_access_token, instance_url):
    """
    Sync up the posts of a conversation to SalesForce.

    NOTE: This expects that the Case for the conversation object
          exists and that it is stored on the conversation object.

    :param conversation:    a Conversation object which already has
                            a Case created on salesforce.
    :param sf_access_token: the access token that will be used to
                            post the results.
    """
    from solariat_bottle.db.account import AccessTokenExpired

    if not instance_url or not sf_access_token:
        logger.error("SFDC account is not authorized. Instance url is: %s and access token is %s" % (
                                                                str(instance_url), str(sf_access_token)))
    unsynced_posts = conversation.unsynced_posts()
    headers = {
        'X-PrettyPrint' : '1',
        'Authorization' : 'Bearer %s' % sf_access_token,
        "Content-Type"  : "application/json"
    }
    sfdc_prefix = get_var('SFDC_MANAGE_PACKAGE_PREFIX')
    url = instance_url + '/services/data/v28.0/sobjects/{}Post__c'.format(sfdc_prefix)

    for post_id in unsynced_posts:
        post = conversation.POST_CLASS.objects.get(id=post_id)

        tags_str = '; '.join([t.title for t in post.accepted_smart_tags]).strip()
        # replace 'junk' with 'other', make intentions lowercase
        intentions_list = post.intention_types
        intentions_str = '; '.join(
            ['other' if 'junk' in x.lower() else x.lower() for x in intentions_list]
        ).strip()
        topics_str = '; '.join(post.topics).strip()
        location = post.user_profile.location
        if location is None:
            location = ''
        profile_image_url = post.user_profile.profile_image_url
        if profile_image_url is None:
            profile_image_url = ''
        klout_score = post.user_profile.klout_score
        if klout_score is None:
            klout_score = ''

        # truncate if necessary
        solariat_id       = truncate(str(post_id),   'text',     128)
        message           = truncate(post.plaintext_content,   'text',     255)
        tags_str          = truncate(tags_str,       'list_str', (100, 40))
        intentions_str    = truncate(intentions_str, 'list_str', (100, 40))
        topics_str        = truncate(topics_str,     'list_str', (100, 40))
        contact_id        = "{}_{}".format(
            conversation.service_channel.platform,
            post.user_profile.user_id
        )
        contact_id        = truncate(contact_id, 'text', 32)
        contact_name      = truncate(post.user_profile.user_name, 'text', 80)
        location          = truncate(location, 'text', 80)
        # if it is longer, replace with ''
        profile_image_url = truncate(profile_image_url, 'text', 255, '')
        klout_score       = truncate(str(klout_score), 'number', 3, '')

        data = json.dumps({
            sfdc_prefix + 'SolariatId__c'      : solariat_id,
            sfdc_prefix + 'Case__c'            : conversation.external_id,
            sfdc_prefix + 'Message__c'         : message,
            sfdc_prefix + 'Tags__c'            : tags_str,
            sfdc_prefix + 'Intentions__c'      : intentions_str,
            sfdc_prefix + 'Topics__c'          : topics_str,
            sfdc_prefix + 'contactId__c'       : contact_id,
            sfdc_prefix + 'contactName__c'     : contact_name,
            sfdc_prefix + 'Location__c'        : location,
            sfdc_prefix + 'profileImageUrl__c' : profile_image_url,
            sfdc_prefix + 'Klout_Score__c'     : klout_score,
        })

        sf_response = requests.post(url, data=data, headers=headers)
        if sf_response.status_code != 201:
            if sf_response.status_code == 401:
                raise AccessTokenExpired("Invalid or expired token.")
            logger.error(sf_response.json()[0].get('message', "Sync to salesforce failed for unknown reason."))
        logger.debug("Synced up post : %s" + post.plaintext_content)  # TODO [encrypt]: logging post content

        conversation.last_synced_post = post.id
        conversation.save()

    return True

