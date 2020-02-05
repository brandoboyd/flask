
import json
import urllib
import requests

from solariat_bottle.settings import get_var


def generate_shortened_url(long_url, access_token=False):
    """Generate bitly url, see
    code.google.com/p/bitly-api/wiki/ApiDocumentation#/v3/shorten

    """

    params = dict(longUrl=long_url)
    if access_token:
        params['access_token'] = access_token
    else:
        params['login']  = get_var('BITLY_LOGIN')
        params['apiKey'] = get_var('BITLY_KEY')

    if get_var('BITLY_DOMAIN'):
        params['domain'] = get_var('BITLY_DOMAIN')

    url = "%sshorten?%s" % (get_var('BITLY_BASE_URL'), urllib.urlencode(params))
    resp = requests.get(url)

    if not resp.status_code == 200:
        raise RuntimeError("Could not get shorten url, %s" % resp.headers)

    result = resp.json()

    try:
        return result['data']['url']
    except (KeyError, TypeError):
        raise RuntimeError("Could not get shorten %s, %s" % (long_url, result))
