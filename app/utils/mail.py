import os
from mimetypes import MimeTypes
from flask import current_app, render_template
from flask_mail import Message
from .. import mail
from threading import Thread


def send_async_email(app, msg):
    with app.app_context():
        app.log.debug(msg)
        mail.send(msg)


def send_email(subject, recipients, template, **kwargs):
    if not isinstance(recipients, list):
        recipients = list(recipients)

    msg = Message(
        subject,
        reply_to=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=recipients)

    msg.body = render_template(template + '.txt', **kwargs)
    #    msg.html = render_template(template + '.html', **kwargs)

    attachments = kwargs.get('attachments', [])
    mimes = MimeTypes()
    for file in attachments:
        path_ = os.path.join(current_app.config['APP_UPLOADS'], file)
        with current_app.open_resource(path_) as fp:
            mime = mimes.guess_type(fp.name)
            msg.attach(path_, mime[0], fp.read())

    app = current_app._get_current_object()
    t = Thread(target=send_async_email, args=[app, msg])
    t.start()
    return t
