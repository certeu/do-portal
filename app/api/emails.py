import os
from mimetypes import MimeTypes
from flask import request, redirect, url_for, abort, current_app
from flask_jsonschema import validate
from flask_mail import Message
from .. import db, mail
from ..models import Email, MailmanUser
from .decorators import json_response
from . import api

#: the /emails endpoint is deprecated
#: all maillist endpoints are forwarded to mailman3


@api.route('/emails', methods=['GET'])
@json_response
def get_emails():
    """Return a list of emails know by Mailman

    .. todo:: Merge with all other emails

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/emails HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "emails": [
            {
              "email": "zzz@zzz.zzz"
            },
            {
              "email": "alex@cert.europa.eu"
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array emails: List of available E-mail objects
    :>jsonobj string email: E-mail address

    :status 200: Deliverable endpoint found, response may be empty
    :status 404: Not found
    """
    emails = []
    users = MailmanUser.query.all()
    for u in users:
        user_emails = [{'email': str(address)} for address in u.addresses]
        emails += user_emails
    return {'emails': emails}


@api.route('/emails/<int:email_id>', methods=['GET'])
@json_response
def get_email(email_id):
    abort(404)
    e = Email.query.get_or_404(email_id)
    return e.serialize()


@api.route('/emails', methods=['POST', 'PUT'])
@validate('emails', 'add_email')
@json_response
def add_email():
    abort(404)
    e = Email().from_json(request.json)
    db.session.add(e)
    db.session.commit()
    return {'email': e.serialize(), 'message': 'Email added'}


@api.route('/emails/<int:email_id>', methods=['PUT'])
@validate('emails', 'update_email')
@json_response
def update_email(email_id):
    e = Email.query.filter(Email.id == email_id, Email.deleted == 0).first()
    if not e:
        return redirect(url_for('api.add_email'))
    e.from_json(request.json)
    db.session.add(e)
    db.session.commit()
    return {'message': 'Email saved'}


@api.route('/emails/<int:email_id>', methods=['DELETE'])
@json_response
def delete_email(email_id):
    e = Email.query.filter(Email.id == email_id, Email.deleted == 0).first()
    if not e:
        return {'message': 'No such email'}, 404
    e.deleted = 1
    db.session.add(e)
    db.session.commit()
    return {'message': 'Email deleted'}


def send_email(sender,
               recipients,
               subject,
               text_body,
               html_body=None,
               attach=None):
    msg = Message(subject, reply_to=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attach:
        mimes = MimeTypes()
        for file in attach:
            path_ = os.path.join(current_app.config['APP_UPLOADS'], file)
            with current_app.open_resource(path_) as fp:
                mime = mimes.guess_type(fp.name)
                msg.attach(file, mime[0], fp.read())
    mail.send(msg)
