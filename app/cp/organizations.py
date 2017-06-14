from flask import g, request
from flask_jsonschema import validate
from app.core import ApiResponse
from app import db
from app.models import Organization, Permission, ContactEmail, Email
from app.api.decorators import permission_required
from . import cp


@cp.route('/organizations', methods=['GET'])
@permission_required(Permission.ORGADMIN)
def get_cp_organization():
    """Return current_user's organization

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
            "212.8.189.19/28"
          ],
          "mail_template": "EnglishReport",
          "mail_times": 3600,
          "old_ID": "00"
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

    :>json integer id: Organization unique ID
    :>json string abbreviation: Abbreviation of organization
    :>json string full_name: Full official name of organization
    :>json string mail_template: Template used by AbuseHelper
    :>json integer mail_times: E-mailing time interval, in seconds
    :>json string old_ID: ID used in the legacu excel sheet
    :>json integer group_id: unique ID of the belonging group
    :>json object group: Group information
    :>json array abuse_emails: E-mail addresses
    :>json array contact_emails: Contact e-mail addresses
    :>jsonarr string email: E-mail address
    :>jsonarr boolean cp: CP access flag
    :>jsonarr boolean fmb: Functional mailbox marker
    :>json array asns: AS numbers
    :>json array fqdns: List of FQDNs
    :>json array ip_ranges: List of IP ranges used by this organization

    :status 200: Returns organization details object
    :status 404: Resource not found
    """
    org_id = g.user.organization_id or 0
    o = Organization.query.get_or_404(org_id)
    return ApiResponse(o.serialize())


@cp.route('/organizations', methods=['PUT', 'POST'])
@validate('organizations', 'update_organization')
@permission_required(Permission.ORGADMIN)
def update_cp_organization():
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
          "old_ID": "00"
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

        HTTP/1.1 422 UNPROCESSABLE ENTITY
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
    :<json integer group_id: unique ID of the belonging group
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
    org_id = g.user.organization_id or 0
    o = Organization.query.get_or_404(org_id)

    untouchables_ = ['is_sla', 'mail_template', 'group_id', 'old_ID', 'group',
                     'group_id']
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
        cp = e.get('cp', 0)
        fmb = e.get('fmb', 0)
        o.contact_emails.append(
            ContactEmail(
                email_=Email(email=e['email']),
                fmb=fmb,
                cp=cp))

    db.session.add(o)
    db.session.commit()
    return ApiResponse({'message': 'Organization saved'})
