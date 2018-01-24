from flask import g, abort, request, redirect, url_for
from flask_jsonschema import validate
from app.core import ApiResponse
from app import db
from app.models import Organization, ContactEmail, Email
# using it soon from app.api.decorators import permission_required
# from app.models import Organization, ContactEmail, Email
from app.api.decorators import json_response
from . import cp


@cp.route('/organizations', methods=['GET'])
# XXX @permission_required(Permission.ORGADMIN)
def get_cp_organizations():
    """Return current_user's organization
## obviously a new method to check permissions and create a json_response
## @json_response
## def get_cp_organizations():
## >>>>>>> topic-postgres

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/organizations HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "organizations": [
            {
              "abbreviation": "CERT-EU",
              "abuse_emails": ["cert-eu@ec.europa.eu"],
              "asns": [5400],
              "child_organizations": [
                201,
                203
              ],
              "contact_emails": [
                {
                  "email": "cert-eu@ec.europa.eu",
                  "cp": true
                }
              ],
              "fqdns": ["cert.europa.eu"],
              "full_name": "Computer Emergency Response Team for EU...",
              "group": {
                "color": "#0033cc",
                "id": 1,
                "name": "Constituents"
              },
              "group_id": 1,
              "id": 185,
              "ip_ranges": [
                "212.8.189.19/28"
              ],
              "mail_template": "EnglishReport",
              "mail_times": 3600,
              "old_ID": "00",
              "parent_org_id": 95
            }
          ]
        }

    **Example error response**:

    .. sourcecode:: http

        HTTP/1.0 404 NOT FOUND
        Content-Type: application/json

        {
          "message": "Resource not found",
          "status": "not found"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array organizations: List of available organization objects

    For organization details: :http:get:`/api/1.0/organizations/(int:org_id)`

    :status 200: Organizations endpoint found, response may be empty
    :status 404: Not found
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    orgs = g.user.get_organizations()
    return ApiResponse({'organizations': [o.serialize() for o in orgs]})


#    return ApiResponse(o.serialize())


@cp.route('/organizations/<int:org_id>', methods=['GET'])
# @json_response
def get_cp_organization(org_id):
    """Return organization identified by ``org_id``

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/organization/44 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "abbreviation": "CERT-EU",
          "abuse_emails": [
            "stavros.lingris@ec.europa.eu"
          ],
          "asns": [
            5400
          ],
          "contact_emails": [
            {
              "email": "cert-eu@ec.europa.eu",
              "cp": true
            }
          ],
          "fqdns": [
            "cert.europa.eu"
          ],
          "full_name": "Computer Emergency Response Team for EU Institutio...",
          "group": {
            "color": "#0033cc",
            "id": 1,
            "name": "Constituents"
          },
          "group_id": 1,
          "id": 185,
          "ip_ranges": [
            "212.8.189.19/28"
          ],
          "is_sla": 1,
          "mail_template": "EnglishReport",
          "mail_times": 3600,
          "old_ID": "00",
          "parent_org_id": 95
        }

    :param org_id: organization unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :reqheader API-Authorization: API key. If present authentication and
            authorization will be attempted.
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: Organization unique ID
    :>json string abbreviation: Abbreviation of organization
    :>json string full_name: Full official name of organization
    :>json string mail_template: Template used by AbuseHelper
    :>json integer mail_times: E-mailing time interval, in seconds
    :>json string old_ID: ID used in the legacu excel sheet
    :>json integer group_id: Unique ID of the belonging group
    :>json object group: Group information
    :>json array abuse_emails: E-mail addresses
    :>json array contact_emails: Contact e-mail addresses
    :>jsonarr string email: E-mail address
    :>jsonarr boolean cp: CP access flag
    :>jsonarr boolean fmb: Functional mailbox marker
    :>json array asns: AS numbers
    :>json array fqdns: List of FQDNs
    :>json array ip_ranges: List of IP ranges used by this organization
    :>json integer is_sla: Service-level agreement marker
    :>json integer parent_org_id: Parent organization ID

    :status 200: Returns organization details object
    :status 404: Resource not found
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    o = Organization.query.get_or_404(org_id)
    return ApiResponse(o.serialize())


"""
@cp.route('/organizations', methods=['PUT', 'POST'])
@validate('organizations', 'update_organization')
@permission_required(Permission.ORGADMIN)
def update_cp_organization():
    if not g.user.may_handle_organization(o):
        abort(403)
    return ApiResponse(o.serialize())
    # return o.serialize()
"""


@cp.route('/organizations', methods=['POST'])
@validate('organizations', 'add_cp_organization')
@json_response
def add_cp_organization():
    """Add new organization
    When adding a new organization only the full name and abbreviation are
    required.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/organizations HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "abbreviation": "BEREC1",
          "abuse_emails": [
            "stavros.lingris@ec.europa.eu"
          ],
          "asns": [
            8194
          ],
          "contact_emails": [
            {
              "email": "berec@berec.europa.eu",
              "cp": true
            }
          ],
          "fqdns": [
            "berec.europa.eu"
          ],
          "full_name": "New Body of European Regulators for Electronic...",

          "group_id": 1,
          "ip_ranges": [
            "212.70.173.66/32",
            "212.70.173.67/32",
            "212.70.173.68/32"
          ],
          "mail_template": "EnglishReport",
          "mail_times": 3600,
          "old_ID": "64"
          "parent_org_id": 95
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "message": "Organization saved"
        }

    **Example validation error**:

    .. sourcecode:: http

        HTTP/1.0 400 BAD REQUEST
        Content-Type: application/json

        {
          "message": "'abbreviation' is a required property",
          "validator": "required"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :reqheader API-Authorization: API key. If present authentication and
            authorization will be attempted.
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string abbreviation: Abbreviation of organization
    :<json string full_name: Full official name of organization
    :<json string mail_template: Template used by AbuseHelper.
      Default is EnglishReport
    :<json integer mail_times: E-mailing time interval, in seconds.
       Default is 3600
    :<json string old_ID: ID used in the legacu excel sheet
    :<json integer group_id: Unique ID of the belonging group
    :<json object group: Group information
    :<json array abuse_emails: E-mail addresses
    :<json array contact_emails: Contact e-mail addresses
    :<jsonarr string email: E-mail address
    :<jsonarr boolean cp: CP access flag
    :<jsonarr boolean fmb: Functional mailbox marker
    :<json array asns: AS numbers
    :<json array fqdns: List of FQDNs
    :<json array ip_ranges: List of IP ranges used by this organization
    :<json integer parent_org_id: Parent organization ID
    :>json string message: Status message
    :>json integer id: organization ID

    :status 200: Organization details were successfully updated
    :status 400: Bad request
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    o = Organization.fromdict(request.json)

    parent_org = Organization.query.get(o.parent_org_id)
    if not parent_org or not g.user.may_handle_organization(parent_org):
        abort(403)

    try:
        contact_emails = request.json.pop('contact_emails')
        for e in contact_emails:
            cp = e.get('cp', False)
            o.contact_emails.append(
                ContactEmail(email_=Email(email=e['email']), cp=cp))
    except KeyError as ke:
        print('No contact emails provided: {}'.format(ke))

    db.session.add(o)
    db.session.commit()
    return {'organization': o.serialize(),
            'message': 'Organization added'}, 201, \
           {'Location': url_for('cp.get_cp_organization', org_id=o.id)}


@cp.route('/organizations/<int:org_id>', methods=['PUT'])
@validate('organizations', 'update_cp_organization')
# @permission_required(Permission.ORGADMIN)
# @json_response
def update_cp_organization(org_id):
    """Update organization details

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/organizations HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "abbreviation": "CERT-EU",
          "abuse_emails": ["cert-eu@ec.europa.eu"],
          "asns": [5400],
          "contact_emails": [
            {
              "email": "cert-eu@ec.europa.eu",
              "cp": true
            }
          ],
          "fqdns": ["cert.europa.eu"],
          "full_name": "Computer Emergency Response Team for EU...",
          "group": {
            "color": "#0033cc",
            "id": 1,
            "name": "Constituents"
          },
          "group_id": 1,
          "id": 185,
          "ip_ranges": [
            "212.8.189.16/28"
          ],
          "mail_template": "EnglishReport",
          "mail_times": 3600,
          "old_ID": "00",
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.1 200 OK
        Content-Type: application/json

        {
          "message": "Organization saved"
        }

    **Example validation error**:

    .. sourcecode:: http

        HTTP/1.0 400 BAD REQUEST
        Content-Type: application/json

        {
          "message": "'abbreviation' is a required property",
          "validator": "required"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json integer id: Unique ID of organization
    :<json string abbreviation: Abbreviation of organization
    :<json string full_name: Full official name of organization
    :<json string mail_template: Template used by AbuseHelper
    :<json integer mail_times: E-mailing time interval, in seconds
    :<json string old_ID: ID used in the legacu excel sheet
    :<json integer group_id: Unique ID of the belonging group
    :<json object group: Group information
    :<json array abuse_emails: E-mail addresses used to send abuse information
    :<json array contact_emails: Contact e-mail addresses
    :<jsonarr string email: E-mail address
    :<jsonarr boolean cp: CP access flag
    :<jsonarr boolean fmb: Functional mailbox marker
    :<json array asns: AS numbers
    :<json array fqdns: List of FQDNs
    :<json array ip_ranges: List of IP ranges used by this organization
    :>json string message: Status message

    :status 200: Organization details were successfully updated
    :status 400: Bad request
    :status 422: Validation error
    """
    o = Organization.query.filter(Organization.id == org_id).first()
    if not o:
        return redirect(url_for('cp.add_cp_organization'))

    if not g.user.may_handle_organization(o):
        abort(403)

    untouchables_ = [
        'is_sla', 'mail_template', 'group_id', 'old_ID', 'group', 'group_id'
    ]
    for k in untouchables_:
        request.json.pop(k, None)

    contact_emails = request.json.pop('contact_emails', [])
    abuse_emails = request.json.pop('abuse_emails', [])
    o.from_json(request.json)
    o.contact_emails = []
    o.abuse_emails = []

    for ac in abuse_emails:
        o.abuse_emails.append(ac)

    for e in contact_emails:
        cp = e.get('cp', False)
        fmb = e.get('fmb', False)
        o.contact_emails.append(
            ContactEmail(email_=Email(email=e['email']), fmb=fmb, cp=cp))

    db.session.add(o)
    db.session.commit()
    return ApiResponse({'message': 'Organization saved'})
    # return {'message': 'Organization saved'}


@cp.route('/organizations/<int:org_id>', methods=['DELETE'])
@json_response
def delete_cp_organization(org_id):
    """Delete organization

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/organizatoins/2 HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Organization deleted"
        }

    :param org_id: Unique ID of the organization

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Action status status

    :status 200: Organization was deleted
    :status 404: Organization was not found
    """
    o = Organization.query.filter(Organization.id == org_id).first_or_404()

    if not g.user.may_handle_organization(o):
        abort(403)

    o.mark_as_deleted()
    db.session.add(o)
    db.session.commit()
    return {'message': 'Organization deleted'}
