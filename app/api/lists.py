#: all our lists are one-way
#: http://grokbase.com/t/python/mailman-users/0295zewgte/is-one-way-possible
import os
from urllib.error import HTTPError
from io import BytesIO

from flask import request, redirect, url_for, current_app
from flask_jsonschema import validate
from flask_gnupg import fetch_gpg_key, get_keyid
from app.core import ApiResponse, ApiException
from . import api
from .emails import send_email
from ..models import MailmanList, MailmanDomain
from werkzeug.utils import secure_filename
from app import gpg


@api.route('/lists', methods=['GET'])
def get_lists():
    """Return the available distribution lists
    For group details see :http:get:`/api/1.0/lists/(string:list_id)`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/lists HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "lists": [
            {
              "fqdn_listname": "constituents@lists.cert.europa.eu",
              "id": "constituents.lists.cert.europa.eu",
              "members": [
                {
                  "email": "alex@cert.europa.eu"
                },
              ],
              "name": "Constituents",
              "description": "aka List 1",
              "settings": {
                "acceptable_aliases": [],
                "admin_immed_notify": true,
                "admin_notify_mchanges": false,
                "administrivia": true,
                "advertised": true,
                "allow_list_posts": true,
                "anonymous_list": false,
                "archive_policy": "public",
                "autorespond_owner": "none",
                "autorespond_postings": "none",
                "autorespond_requests": "none",
                "autoresponse_grace_period": "90d",
                "autoresponse_owner_text": "",
                "autoresponse_postings_text": "",
                "autoresponse_request_text": "",
                "bounces_address": "constituents-bounces@lists.cert.europa.eu",
                "collapse_alternatives": true,
                "convert_html_to_plaintext": false,
                "created_at": "2015-10-29T16:29:56.521055",
                "default_member_action": "defer",
                "default_nonmember_action": "hold",
                "description": "aka List 1",
                "digest_last_sent_at": null,
                "digest_size_threshold": 30.0,
                "display_name": "Constituents",
                "filter_content": false,
                "first_strip_reply_to": false,
                "fqdn_listname": "constituents@lists.cert.europa.eu",
                "http_etag": "\"7cfc1e2e61929ce5a6444c5d17d70aa8dd45c1cb\"",
                "include_rfc2369_headers": true,
                "join_address": "constituents-join@lists.cert.europa.eu",
                "last_post_at": null,
                "leave_address": "constituents-leave@lists.cert.europa.eu",
                "list_name": "constituents",
                "mail_host": "lists.cert.europa.eu",
                "next_digest_number": 1,
                "no_reply_address": "noreply@lists.cert.europa.eu",
                "owner_address": "constituents-owner@lists.cert.europa.eu",
                "post_id": 1,
                "posting_address": "constituents@lists.cert.europa.eu",
                "posting_pipeline": "default-posting-pipeline",
                "reply_goes_to_list": "no_munging",
                "reply_to_address": "",
                "request_address": "constituents-request@lists.cert.europa.eu",
                "scheme": "http",
                "send_welcome_message": false,
                "subject_prefix": "[Constituents] ",
                "subscription_policy": "moderate",
                "volume": 1,
                "web_host": "lists.cert.europa.eu",
                "welcome_message_uri": "mailman:///welcome.txt"
              }
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array lists: Available distribution lists

    :status 200: Lists found
    :status 204: The request succeeded, no lists where found
    :status 404: Not found
    """
    lists = []
    mailman_lists = sorted(MailmanList.query.all(),
                           key=lambda l: l.fqdn_listname)
    if not mailman_lists:
        return {}, 204
    for l in mailman_lists:
        members = []
        for m in l.members:
            members.append({'email': m.email})
        lists.append({
            'id': l.list_id,
            'name': l.display_name,
            'description': l.settings.get('description', 'N/A'),
            'fqdn_listname': l.fqdn_listname,
            'settings': dict(l.settings),
            'members': members
        })
    return ApiResponse({'lists': lists})


@api.route('/lists/<string:list_id>', methods=['GET'])
def get_list(list_id):
    """Return details about a distribution list identified by `list_id`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/lists/constituents.lists.cert.europa.eu HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "fqdn_listname": "constituents@lists.cert.europa.eu",
          "id": "constituents.lists.cert.europa.eu",
          "members": [],
          "name": "Constituents",
          "description": "aka List 1",
          "settings": {
            "acceptable_aliases": [],
            "admin_immed_notify": true,
            "admin_notify_mchanges": false,
            "administrivia": true,
            "advertised": true,
            "allow_list_posts": true,
            "anonymous_list": false,
            "archive_policy": "public",
            "autorespond_owner": "none",
            "autorespond_postings": "none",
            "autorespond_requests": "none",
            "autoresponse_grace_period": "90d",
            "autoresponse_owner_text": "",
            "autoresponse_postings_text": "",
            "autoresponse_request_text": "",
            "bounces_address": "constituents-bounces@lists.cert.europa.eu",
            "collapse_alternatives": true,
            "convert_html_to_plaintext": false,
            "created_at": "2015-10-29T16:29:56.521055",
            "default_member_action": "defer",
            "default_nonmember_action": "hold",
            "description": "aka List 1",
            "digest_last_sent_at": null,
            "digest_size_threshold": 30.0,
            "display_name": "Constituents",
            "filter_content": false,
            "first_strip_reply_to": false,
            "fqdn_listname": "constituents@lists.cert.europa.eu",
            "http_etag": "\"7cfc1e2e61929ce5a6444c5d17d70aa8dd45c1cb\"",
            "include_rfc2369_headers": true,
            "join_address": "constituents-join@lists.cert.europa.eu",
            "last_post_at": null,
            "leave_address": "constituents-leave@lists.cert.europa.eu",
            "list_name": "constituents",
            "mail_host": "lists.cert.europa.eu",
            "next_digest_number": 1,
            "no_reply_address": "noreply@lists.cert.europa.eu",
            "owner_address": "constituents-owner@lists.cert.europa.eu",
            "post_id": 1,
            "posting_address": "constituents@lists.cert.europa.eu",
            "posting_pipeline": "default-posting-pipeline",
            "reply_goes_to_list": "no_munging",
            "reply_to_address": "",
            "request_address": "constituents-request@lists.cert.europa.eu",
            "scheme": "http",
            "send_welcome_message": false,
            "subject_prefix": "[Constituents] ",
            "subscription_policy": "moderate",
            "volume": 1,
            "web_host": "lists.cert.europa.eu",
            "welcome_message_uri": "mailman:///welcome.txt"
          }
        }

    :param list_id: list ID, e.g. constituents.lists.cert.europa.eu

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string id: Distribution list ID
    :>json string fqdn_listname: Full list name, usually its email address
    :>json string name: Distribution list name
    :>json array members: Array of subscribers to this list
    :>json object settings: Distribution list settings

    :status 200: Returns group details object
    :status 404: Resource not found
    """
    l = MailmanList.get(fqdn_listname=list_id)
    members = []
    for m in l.members:
        member = {
            'email': m.email,
            'gpg_keyid': get_keyid(m.email)
        }
        members.append(member)
    return ApiResponse({
        'id': l.list_id,
        'name': l.display_name,
        'description': l.settings.get('description', 'N/A'),
        'fqdn_listname': l.fqdn_listname,
        'settings': dict(l.settings),
        'members': members
    })


@api.route('/lists', methods=['POST', 'PUT'])
@validate('lists', 'add_list')
def add_list():
    """Add new distribution list
    See the sample response JSON object for all available settings

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/lists HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "active": true,
          "name": "Test",
          "description": "Test Description"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "list": {
            "fqdn_listname": "test@lists.cert.europa.eu",
            "id": "test.lists.cert.europa.eu",
            "name": "Test",
            "description": "Test Description",
            "settings": {
              "acceptable_aliases": [],
              "admin_immed_notify": true,
              "admin_notify_mchanges": false,
              "administrivia": true,
              "advertised": true,
              "allow_list_posts": true,
              "anonymous_list": false,
              "archive_policy": "public",
              "autorespond_owner": "none",
              "autorespond_postings": "none",
              "autorespond_requests": "none",
              "autoresponse_grace_period": "90d",
              "autoresponse_owner_text": "",
              "autoresponse_postings_text": "",
              "autoresponse_request_text": "",
              "bounces_address": "test-bounces@lists.cert.europa.eu",
              "collapse_alternatives": true,
              "convert_html_to_plaintext": false,
              "created_at": "2015-11-27T17:26:33.734199",
              "default_member_action": "accept",
              "default_nonmember_action": "accept",
              "description": "Test Description",
              "digest_last_sent_at": null,
              "digest_size_threshold": 30.0,
              "display_name": "Test",
              "filter_content": false,
              "first_strip_reply_to": false,
              "fqdn_listname": "test@lists.cert.europa.eu",
              "http_etag": "\"4ccc9930805687341d8bf6b5f6dfe461b0c3e21e\"",
              "include_rfc2369_headers": true,
              "join_address": "test-join@lists.cert.europa.eu",
              "last_post_at": null,
              "leave_address": "test-leave@lists.cert.europa.eu",
              "list_name": "test",
              "mail_host": "lists.cert.europa.eu",
              "next_digest_number": 1,
              "no_reply_address": "noreply@lists.cert.europa.eu",
              "owner_address": "test-owner@lists.cert.europa.eu",
              "post_id": 1,
              "posting_address": "test@lists.cert.europa.eu",
              "posting_pipeline": "default-posting-pipeline",
              "reply_goes_to_list": "no_munging",
              "reply_to_address": "",
              "request_address": "test-request@lists.cert.europa.eu",
              "scheme": "http",
              "send_welcome_message": false,
              "subject_prefix": "[Test] ",
              "subscription_policy": "confirm",
              "volume": 1,
              "web_host": "lists.cert.europa.eu",
              "welcome_message_uri": "mailman:///welcome.txt"
            }
          },
          "message": "List added"
        }

    .. warning:: Validation of requst data doesn't work

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string name: List name
    :<json boolean active: Active
    :<json array members: Array of subscribers to this list,
        must be known e-mails
    :<json object settings: Distribution list settings
    :>json string id: Distribution list ID
    :>json string fqdn_listname: Full list name, usually its email address
    :>json string name: Distribution list name
    :>json array members: Array of subscribers to this list
    :>json object settings: Distribution list settings
    :>json string message: Status message

    :status 201: Distribution list was created
    :status 400: Bad request
    """
    req = request.json
    domain = MailmanDomain.get(
        mail_host=current_app.config['MAILMAN_DOMAIN'])
    nlist = domain.create_list(secure_filename(req['name']))
    nlist.add_owner(current_app.config['MAILMAN_ADMIN'])
    list_settings = nlist.settings
    list_settings.update({
        'description': req['description'],
        'advertised': True,
        'send_welcome_message': False,
        'default_member_action': 'accept',
        'default_nonmember_action': 'accept',
        'include_rfc2369_headers': False,
        'reply_goes_to_list': 'explicit_header',
        'header_uri': '',
        'footer_uri': ''
    })
    list_settings.save()
    return ApiResponse({
        'list': {
            'id': nlist.list_id,
            'name': nlist.display_name,
            'description': nlist.settings.get('description', 'N/A'),
            'fqdn_listname': nlist.fqdn_listname,
            'settings': dict(nlist.settings)
        },
        'message': 'List added'
    }, 201, {'Location': url_for('api.get_list', list_id=nlist.list_id)})


@api.route('/lists/<list_id>', methods=['PUT'])
@validate('lists', 'update_list')
def update_list(list_id):
    """Update distribution list settings

    **Example request**:

        .. sourcecode:: http

            PUT /api/1.0/lists/test.lists.cert.europa.eu HTTP/1.1
            Host: do.cert.europa.eu
            Accept: application/json
            Content-Type: application/json

            {
              "fqdn_listname": "test@lists.cert.europa.eu",
              "id": "test.lists.cert.europa.eu",
              "members": [],
              "name": "Test update",
              "description": "Test Description",
              "settings": {
                "acceptable_aliases": [],
                "admin_immed_notify": true,
                "admin_notify_mchanges": false,
                "administrivia": true,
                "advertised": true,
                "allow_list_posts": true,
                "anonymous_list": false,
                "archive_policy": "public",
                "autorespond_owner": "none",
                "autorespond_postings": "none",
                "autorespond_requests": "none",
                "autoresponse_grace_period": "90d",
                "autoresponse_owner_text": "",
                "autoresponse_postings_text": "",
                "autoresponse_request_text": "",
                "bounces_address": "test-bounces@lists.cert.europa.eu",
                "collapse_alternatives": true,
                "convert_html_to_plaintext": false,
                "created_at": "2015-11-27T17:26:33.734199",
                "default_member_action": "accept",
                "default_nonmember_action": "accept",
                "description": "Test Description",
                "digest_last_sent_at": null,
                "digest_size_threshold": 30,
                "display_name": "Test",
                "filter_content": false,
                "first_strip_reply_to": false,
                "fqdn_listname": "test@lists.cert.europa.eu",
                "http_etag": "\"89ac10f0224394b76afc7219263fef8dad8a109f\"",
                "include_rfc2369_headers": true,
                "join_address": "test-join@lists.cert.europa.eu",
                "last_post_at": null,
                "leave_address": "test-leave@lists.cert.europa.eu",
                "list_name": "test",
                "mail_host": "lists.cert.europa.eu",
                "next_digest_number": 1,
                "no_reply_address": "noreply@lists.cert.europa.eu",
                "owner_address": "test-owner@lists.cert.europa.eu",
                "post_id": 1,
                "posting_address": "test@lists.cert.europa.eu",
                "posting_pipeline": "default-posting-pipeline",
                "reply_goes_to_list": "no_munging",
                "reply_to_address": "",
                "request_address": "test-request@lists.cert.europa.eu",
                "scheme": "http",
                "send_welcome_message": false,
                "subject_prefix": "[Test] ",
                "subscription_policy": "confirm",
                "volume": 1,
                "web_host": "lists.cert.europa.eu",
                "welcome_message_uri": "mailman:///welcome.txt"
              }
            }

        **Example response**:

        .. sourcecode:: http

            HTTP/1.0 200 OK
            Content-Type: application/json

            {
              "message": "List saved"
            }

        **Example validation error**:

        .. sourcecode:: http

            HTTP/1.0 400 BAD REQUEST
            Content-Type: application/json

            {
              "message": "'name' is a required property",
              "validator": "required"
            }

    .. warning:: Validation of requst data doesn't work

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :param list_id: list ID, e.g. constituents.lists.cert.europa.eu

    :<json string id: Distribution list ID
    :<json string fqdn_listname: Full list name, usually its email address
    :<json string name: Distribution list name
    :<json array members: Array of subscribers to this list
    :<json object settings: Distribution list settings
    :>json string message: Status message

    :status 200: Distribution list was updated
    :status 400: Bad request
    """
    try:
        l = MailmanList.get(fqdn_listname=list_id)
    except HTTPError as fof:
        current_app.log.error(fof)
        return redirect(url_for('api.add_list'))

    list_settings = l.settings
    new_settings = dict(l.settings)
    new_settings.update(request.json['settings'])

    for k in new_settings.keys():
        list_settings[k] = new_settings[k]
    list_settings['header_uri'] = ''
    list_settings['footer_uri'] = ''
    l.settings.save()
    return ApiResponse({'message': 'List saved'})


@api.route('/lists/<list_id>/unsubscribe', methods=['PUT'])
def unsubscribe_list(list_id):
    """Unsubscribe email(s) from distribution list

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/lists/certs.lists.cert.europa.eu/unsubscribe HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        [
          "some@mail.com",
          "other@mail.com"
        ]

    .. todo:: PUT an object instead of an array

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "List saved"
        }

    :param list_id: Distribution list ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<jsonarr string emails: E-mails for mass-unsubscribe
    :>json string message: Status message

    :status 200: Distribution list was updated
    :status 400: Bad request
    """
    l = MailmanList.get(fqdn_listname=list_id)
    if type(request.json) is str:
        data = [request.json]
    else:
        data = request.json
    for email in data:
        l.unsubscribe(email.lower())
    return ApiResponse({'message': 'List saved'})


@api.route('/lists/<list_id>/subscribe', methods=['PUT'])
def subscribe_list(list_id):
    """Subscribe email(s) to distribution list

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/lists/certs.lists.cert.europa.eu/subscribe HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "emails": [
            "some@mail.com",
            "other@mail.com"
          ]
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "List saved"
        }

    :param list_id: Distribution list ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json array emails: E-mails for mass-subscription
    :>json string message: Status message

    :status 200: Group was deleted
    :status 400: Bad request
    """
    l = MailmanList.get(fqdn_listname=list_id)
    try:
        data = [request.json['email']]
    except (KeyError, TypeError) as ke:
        current_app.log.info(ke)
        data = request.json['emails']
    for email in data:
        try:
            l.subscribe(address=email.lower(),
                        pre_verified=True, pre_confirmed=True)
            fetch_gpg_key(
                email.lower(), current_app.config['GPG_KEYSERVERS'][0])
        except HTTPError as he:
            raise ApiException(email.lower() + ': ' + he.msg.decode(), he.code)
    return ApiResponse({'message': 'List saved'})


@api.route('/lists/<list_id>', methods=['DELETE'])
def delete_list(list_id):
    """Delete distribution list

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/lists/test.lists.cert.europa.eu HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "List deleted"
        }

    :param list_id: List ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Status message

    :status 200: List was deleted
    """
    nlist = MailmanList.get_or_404(fqdn_listname=list_id)
    nlist.delete()
    return ApiResponse({'message': 'List deleted'})


@api.route('/lists/post', methods=['POST'])
@validate('lists', 'post')
def post_message():
    """Send email to mailing list. If ``encrypted`` is set to ``True``
    the message body and all attachments will be encrypted with the public
    keys of all list members

    .. todo::

        Add icons:
        https://twitter.com/JZdziarski/status/753223642297892864

    Files in response.json.files are assumed uploaded via
    :http:post:`/api/1.0/upload`

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/lists/post HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

        {
          "files": [
            "targets.txt"
          ],
          "list_id": "certs.lists.cert.europa.eu",
          "subject": "zZz",
          "encrypt": false,
          "content": "ž"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Email has been sent."
        }

    .. warning:: There is no error checking

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string list_id: Distribution list ID
    :<json string subject: E-mail subject
    :<json string content: E-mail content
    :<json array files: Files to attach
    :>json string message: Status message

    :status 200: Email successfully sent
    :status 400: Bad request
    :status 500: Error processing the request
    """
    msg = request.json
    files = msg.get('files', None)
    encrypted = msg.get('encrypted', None)
    list_ = MailmanList.get(fqdn_listname=msg['list_id'])
    if encrypted:
        enc = _encrypt(BytesIO(msg['content'].encode('utf-8')),
                       list_=list_, always_trust=True)
        if not enc.ok:
            raise ApiException('Could not encrypt message content. '
                               'Please make sure you have all the keys.')
        content = enc.data.decode()
        attachedfiles = []
        if files:
            for file in files:
                file_path = os.path.join(
                    current_app.config['APP_UPLOADS'], file)
                with open(file_path, 'rb') as fb:
                    outfile = file_path + '.asc'
                    cipherfile = _encrypt(fb, list_, output=outfile,
                                          always_trust=True)
                    if cipherfile.ok:
                        attachedfiles.append(file + '.asc')
    else:
        content = msg['content']
        attachedfiles = files
    send_email(
        'noreply@lists.cert.europa.eu', [list_.fqdn_listname], msg['subject'],
        content, attach=attachedfiles
    )
    return ApiResponse({'message': 'Email has been sent.'})


@api.route('/lists/<list_id>/check_gpg', methods=['GET'])
def check_gpg(list_id):
    """Try to encrypt a message to all members of `list_id`.

    .. note:: The GPG client only returns errors about the last recipient

    :param list_id: List FQDN name. E.g. ``certs.lists.cert.europa.eu``

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/lists/certs.lists.cert.euroap.eu/check_gpg HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Sample data successfuly encrypted for this list"
        }

    **Example errpr response**:

    .. sourcecode:: http

        HTTP/1.0 400 BAD REQUEST
        Content-Type: application/json

        {
          "message": "Your message can not be encrypted for all the members of
                this list",
          "stderr": "gpg: zzz@zzz.zzz: skipped: No public key
                    [GNUPG:] INV_RECP 1 zzz@zzz.zzz
                    gpg: [stdin]: encryption failed: No public key"
        }

    .. note:: stderr contains information only about the last recipient

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Status message
    :>json string stderr: STDERR

    :status 200: Email successfully sent
    :status 400: An error has occured while trying to encrypt

    """
    l = MailmanList.get(fqdn_listname=list_id)
    emails = [m.email for m in l.members]
    if not emails:
        raise ApiException('This list has no members.')
    enc = gpg.gnupg.encrypt('test', emails, always_trust=True)
    if enc.ok:
        return ApiResponse({'message': 'Test successful.'})

    raise ApiException('Your message can not be encrypted for all '
                       'the members of this list ' + enc.stderr)


def _encrypt(fileobj=None, list_=None, **kwargs):
    """

    :param data:
    :param dlist:
    :return:
    """
    emails = [m.email for m in list_.members]
    return gpg.gnupg.encrypt_file(fileobj, emails, **kwargs)
