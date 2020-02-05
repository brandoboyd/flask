#!/usr/bin/env python2.7

from solariat.mail import Message
from solariat_bottle.app import app, MAIL_SENDER
from flask import request

mail_tpl = """
Name:    %s
Email:   %s
Company: %s
Twitter: %s
Phone:   %s
Message: %s
"""

@app.route('/mailform', methods = ['POST'])
def mail_form():
    msg = Message(subject="contact form", recipients=["sales@socialoptimizr.com"])
    msg.body = mail_tpl % (
        request.form.get('name'),
        request.form.get('email'),
        request.form.get('company'),
        request.form.get('twitter'),
        request.form.get('phone'),
        request.form.get('message')
    )
    MAIL_SENDER.send(msg)
    return "mail was sent successfully"
