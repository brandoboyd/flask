from itsdangerous import URLSafeSerializer, BadSignature
from flask import abort, render_template

from ..app import app
from solariat_bottle.settings import get_var
from solariat_bottle.db.channel.base import SmartTagChannel


@app.route('/unsubscribe/tag/<email_tag_id>', methods=['GET'])
def unsubscribe_from_tag_alerts(email_tag_id):
    s = URLSafeSerializer(get_var('UNSUBSCRIBE_KEY'), get_var('UNSUBSCRIBE_SALT'))
    try:
        user_email, tag_id = s.loads(email_tag_id)
    except BadSignature:
        abort(404)

    t = SmartTagChannel.objects.get(id=tag_id)
    t.alert_emails = list(set(t.alert_emails).difference(set([user_email])))

    # deactivate alert if no one is subscribing to alert email
    if not t.alert_emails:
        t.alert_is_active = False

    t.save()
    return render_template("/unsubscribe_tag.html",
                           tag_title=t.title,
                           tag_id=str(t.id))
