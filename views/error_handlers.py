"""
This file should contain any kind of specific global error handlers
we want to user.
"""
from flask import render_template, request, jsonify

from solariat_bottle.app import app
from solariat_bottle.utils.mailer import error_notifier_500


def get_system_info():
    """ Return a string representation of the request context and app settings.
    """
    system_info = "<br/><b>Application settings which were used:</b><br/>"
    for key, val in app.config.iteritems():
        system_info += "<p>%s : %s</p>" % (key, val)
    system_info += "<br/>"
    system_info += "<br/><b>Some request information:</b><br/>"
    system_info += "<p>%s : %s<p>" % ('url', request.url)
    system_info += "<p>%s : %s<p>" % ('endpoint', request.endpoint)
    system_info += "<p>%s : %s<p>" % ('data', request.data)
    system_info += "<p>%s : %s<p>" % ('view_args', request.view_args)
    return system_info


@app.errorhandler(403)
def forbidden_access(ex):
    """ Access a page that is forbidden to you """
    return render_template('error_pages/403.html'), 403


@app.errorhandler(404)
def page_not_found(ex):
    """ Access a page that does not exist """
    return render_template('error_pages/404.html'), 404


@app.errorhandler(410)
def resource_deleted(ex):
    """ Access a resource that no longer exists """
    return render_template('error_pages/410.html'), 410


@app.errorhandler(500)
def internal_error(ex):
    app.logger.error("A disturbance in the force, there was!")
    error_notifier_500(subject="SEVERE: Internal server error in production!",
                       raised_exception=ex,
                       system_info=get_system_info())
    if request.is_xhr:
        return jsonify(ok=False, error=str(ex))
    else:
        return render_template('error_pages/500.html')
