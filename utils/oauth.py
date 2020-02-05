import tweepy

from solariat_bottle.settings import get_var, LOGGER, AppException


def to_channel(channel_or_id=None):
    from solariat_bottle.db.channel.base import Channel
    if channel_or_id==None:
        return None
    elif isinstance(channel_or_id, Channel):
        return channel_or_id
    return Channel.objects.get(channel_or_id)


def get_twitter_oauth_credentials(channel_or_id):
    '''
    Obtain app credentials based on the account and access token
    details. We figure that out from the channel if there is one.
    Channel settings over-ride account type defaults
    '''
    channel = to_channel(channel_or_id)
    from solariat_bottle.db.account import AccountType

    # If we have a channel and an account, we can find account
    # specific bindings
    access_token_key = get_var('TWITTER_ACCESS_TOKEN')
    access_token_secret = get_var('TWITTER_ACCESS_TOKEN_SECRET')
    consumer_key = get_var('TWITTER_CONSUMER_KEY')
    consumer_secret = get_var('TWITTER_CONSUMER_SECRET')
    callback_url = get_var('TWITTER_CALLBACK_URL')

    if channel and channel.account:
        try:
            account_type = AccountType.objects.get(name=channel.account.account_type)
        except AccountType.DoesNotExist:
            pass
        else:
            access_token_key = account_type.twitter_access_token_key
            access_token_secret = account_type.twitter_access_token_secret
            consumer_key = account_type.twitter_consumer_key
            consumer_secret = account_type.twitter_consumer_secret
            callback_url = account_type.twitter_callback_url

        if channel.is_authenticated:
            access_token_key = channel.access_token_key
            access_token_secret = channel.access_token_secret

    credentials = [
        consumer_key,
        consumer_secret,
        callback_url,
        access_token_key,
        access_token_secret
    ]
    LOGGER.debug("Credentials are: %s", credentials)
    return tuple(map(str, credentials))


def get_twitter_oauth_handler(channel_or_id=None, callback_url=''):
    '''
    Fetch the OAuth Handler. Encapsulate how we handle this per channel,
    which will determine all the proper keys. The channel account
    type will really drive it.

    Note that we also set the required access token.

    The valid cases for access token arguments:
    1. Both set
    2. Neither set
    '''
    try:

        # Get the auth credentials based on the account type
        (account_consumer_key,
         account_consumer_secret,
         account_callback_url,
         access_token_key,
         access_token_secret) = get_twitter_oauth_credentials(channel_or_id)

        auth = tweepy.OAuthHandler(
                account_consumer_key,
                account_consumer_secret,
                account_callback_url + callback_url #,
                #secure=True
            )

        auth.set_access_token(access_token_key, access_token_secret)

    except KeyError, e:
        raise AppException("App Not correctly configured. %s" % str(e))

    return auth
