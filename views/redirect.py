""" Redirect service """

from flask import redirect, abort, jsonify, request
from solariat_bottle.app import app
from ..db.post.base import Post, PostMatch, PostClick
from ..utils.views import get_doc_or_error
from ..utils.redirect import fetch_url, add_sourcing_params
from ..db.channel_stats import post_clicked

@app.route('/redirect/<postmatch_id>/<matchable_id>')
def do_redirect(postmatch_id, matchable_id):
    "Store click info and redirect to landing page url"

    abort(404)

    postmatch = get_doc_or_error(PostMatch, postmatch_id)
    matchable = get_doc_or_error(Matchable, matchable_id)

    url = fetch_url(matchable.creative)
    if not url:
        abort(404)

    # Prepend the protocol if none present
    if not url.find('http') == 0:
        url = 'http://' + url

    # Do the click
    PostClick(
        post=postmatch.post,
        matchable=matchable,
        redirect_url=url
    ).save()

    # Update channel stats
    post_clicked(postmatch.post, matchable)

    return redirect(add_sourcing_params(url))

@app.route('/redirects/post_view', methods=['GET'])
def post_view():
    """
    In case the post does not have an url, compute it and store it for future use.
    Finally, redirect to the posts url.
    """
    post_id = request.args.get('post_id', False)
    if not post_id:
        return jsonify(ok=False, error="No post id for redirect.")
    post = Post.objects.get(id=post_id)
    if not post.url:
        post.set_url()
    return redirect(post.url)
