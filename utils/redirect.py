
import re
import urllib
import urlparse
from flask import request
from ..utils.bitly import generate_shortened_url

_url_fetch_regex = re.compile(r'\b(https?://|www\.)\S+\w')

def fetch_url(creative):
    " fetch first url from creative "

    m = _url_fetch_regex.search(creative)
    if m:
        return m.group()
    return None

def add_sourcing_params(url, postmatch_id):
    "Add params to indicate it is from solariat"

    ROUTING_PARAMS = {
        'utm_source': 'solariat',
        'solariat_id': postmatch_id
    }

    split_res = urlparse.urlsplit(url)
    if split_res.scheme == '' and split_res.netloc == '':
        split_res = urlparse.urlsplit('http://' + url)

    url_params = urlparse.parse_qs(split_res.query, True)
    url_params.update(ROUTING_PARAMS)
    return urlparse.urlunsplit((split_res.scheme, split_res.netloc,
        split_res.path, urllib.urlencode(url_params, True), split_res.fragment))

def gen_creative(matchable, postmatch):
    "Return creative from matchable with replaced url"

    landing_page = fetch_url(matchable.creative)
    if landing_page:
        url = generate_shortened_url(add_sourcing_params(landing_page, str(postmatch.id)))
        #url = gen_redirect_url(postmatch, matchable)
        return _url_fetch_regex.sub(url, matchable.creative, count=1)
    return matchable.creative

def gen_redirect_url(postmatch, matchable):
    "Make url for redirect"

    if 'localhost' in request.host_url: 
        # bit.ly fails with localhost
        host_url = 'http://127.0.0.1'
    else:
        host_url = request.host_url

    long_url = "%sredirect/%s/%s" % (host_url, postmatch.id, matchable.id)

    return generate_shortened_url(long_url,
               postmatch.channel.bitly_access_token)
