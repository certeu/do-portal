import ipaddress
from flask import request, redirect, url_for, current_app
from flask_jsonschema import validate
from sqlalchemy.exc import IntegrityError
from app.core import ApiResponse, ApiException
from . import api
from ..import db
from ..models import Organization, Email, ContactEmail


@api.route('/organizations', methods=['GET'])
def get_organizations():
    """Return a list of available organizations

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/organizations HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        API-Authorization: ad6bfbb0df17c1f2a7cbe1548444803d6114b8d877e37dd4fzc

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "organizations": [
            {
              "abbreviation": "ACER",
              "abuse_emails": [
                "stavros.lingris@ec.europa.eu"
              ],
              "asns": [
                5603
              ],
              "contact_emails": [
                {
                  "email": "cert-eu@ec.europa.eu",
                  "cp": 1
                }
              ],
              "fqdns": [
                "acer.europa.eu"
              ],
              "full_name": "Agency for the Cooperation of Energy Regulators",
              "group": {
                "color": "#0033cc",
                "id": 1,
                "name": "Constituents"
              },
              "group_id": 1,
              "id": 232,
              "ip_ranges": [
                "213.250.27.8/29",
                "193.189.171.8/29",
                "193.77.62.16/28"
              ],
              "mail_template": "EnglishReport",
              "mail_times": 10800,
              "old_ID": "17"
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :reqheader API-Authorization: API key. If present authentication and
        authorization will be attempted.
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
    orgs = Organization.query.all()
    return ApiResponse({'organizations': [o.serialize() for o in orgs]})


@api.route('/organizations/<int:org_id>', methods=['GET'])
def get_organization(org_id):
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
          "old_ID": "00"
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
    :>json integer is_sla: Service-level agreement marker

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


@api.route('/organizations/<string:org_abbr>', methods=['GET'])
def get_organization_by_abbr(org_abbr):
    """Return organization identified by
    :attr:`~app.models.Organization.abbreviation`.

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/organization/cert-eu HTTP/1.1
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
          "old_ID": "00"
        }

    :param org_abbr: organization abbreviation

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
    :>json integer is_sla: Service-level agreement marker

    :status 200: Returns organization details object
    :status 404: Resource not found
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    o = Organization.query.filter_by(abbreviation=org_abbr).first_or_404()
    return ApiResponse(o.serialize())


@api.route('/organizations', methods=['POST', 'PUT'])
@validate('organizations', 'add_organization')
def add_organization():
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
    :<json integer group_id: unique ID of the belonging group
    :<json object group: Group information
    :<json array abuse_emails: E-mail addresses
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
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    contact_emails = request.json.pop('contact_emails')
    o = Organization.fromdict(request.json)
    try:
        for e in contact_emails:
            cp = e.get('cp', False)
            o.contact_emails.append(
                ContactEmail(
                    email_=Email(email=e['email']),
                    cp=cp))
    except KeyError as ke:
        current_app.log.warn('No contact emails provided: {}'.format(ke))

    db.session.add(o)
    db.session.commit()
    return ApiResponse(
        {'organization': o.serialize(), 'message': 'Organization added'},
        201,
        {'Location': url_for('api.get_organization', org_id=o.id)})


@api.route('/organizations/<int:org_id>', methods=['PUT'])
@validate('organizations', 'update_organization')
def update_organization(org_id):
    """Update organization details

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/organizations/185 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
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
          "full_name": "Computer Emergency Response Team for EU Institutions",
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
          "is_sla": 1,
          "mail_template": "EnglishReport",
          "mail_times": 3600,
          "old_ID": "00"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
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

    :param org_id: Organization unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :reqheader API-Authorization: API key. If present authentication and
            authorization will be attempted.
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
    :<jsonarr boolean fmb: Functional mailbox flag
    :<json array asns: AS numbers
    :<json array fqdns: List of FQDNs
    :<json array ip_ranges: List of IP ranges used by this organization
    :<json integer is_sla: Service-level agreement marker
    :>json string message: Status message

    :status 200: Organization details were successfully updated
    :status 400: Bad request
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    o = Organization.query.filter(
        Organization.id == org_id
    ).first()
    if not o:
        return redirect(url_for('api.add_organization'))
    contact_emails = request.json.pop('contact_emails', [])
    abuse_emails = request.json.pop('abuse_emails', [])
    o.from_json(request.json)
    for c in o.contact_emails:
        try:
            Email.query.filter_by(email=c.email).delete()
        except IntegrityError as ie:
            #: Key constrain, this email is also used as abuse email
            current_app.log.debug(ie)
            current_app.log.debug(
                'Not deleting {}. '
                'It\'s also used as abuse email'.format(c.email))
    o.contact_emails = []

    for ac in o.abuse_emails:
        try:
            Email.query.filter_by(email=ac).delete()
        except IntegrityError as ie:
            #: Key constrain, this email is also used as contact email
            current_app.log.debug(ie)
            current_app.log.debug(
                'Not deleting {}. '
                'It\'s also used as contact email'.format(ac))
    o.abuse_emails = []

    for ac in abuse_emails:
        o.abuse_emails.append(ac)

    for e in contact_emails:
        cp = e.get('cp', False)
        o.contact_emails.append(
            ContactEmail(
                email_=Email(email=e['email']),
                cp=cp))

    db.session.add(o)
    db.session.commit()
    return ApiResponse({'message': 'Organization saved'})


@api.route('/organizations/<int:org_id>', methods=['DELETE'])
def delete_organization(org_id):
    """Delete organization

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/organizations/67 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Organization deleted"
        }

    :param org_id: Organizations's unique ID.

    :reqheader Accept: Content type(s) accepted by the client
    :reqheader API-Authorization: API key. If present authentication and
            authorization will be attempted.
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Delete status

    :status 200: File was deleted
    :status 404: Resource not found
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    o = Organization.query.filter(
        Organization.id == org_id
    ).first_or_404()

    o.deleted = 1
    db.session.add(o)
    db.session.commit()
    return ApiResponse({'message': 'Organization deleted'})


@api.route('/organizations/query/', methods=['POST'])
def query():
    """

    :status 501: NotImplemented
    :return:
    """
    raise ApiException('Not Implemented', status=501)
    # conditions = request.json['conditions']
    # c = Organization.query.find(**conditions)


@api.route('/organizations/check', methods=['PUT'])
@validate('organizations', 'check')
def check_constituents():
    """Search to which organization does a specific IP address belongs

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/organizations/check HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        [
          "212.8.189.19",
          "1.2.3.4",
          "136.173.80.72"
        ]

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "response": {
            "1.2.3.4": "DUMMY",
            "136.173.80.72": "EP_WiFi",
            "212.8.189.19": "CERT-EU"
          }
        }

    :reqheader Accept: Content type(s) accepted by the client
    :reqheader API-Authorization: API key. If present authentication and
            authorization will be attempted.
    :resheader Content-Type: this depends on `Accept` header or request

    :<jsonarr string ip_address: IP addresses to check
    :>json object response: Dictonary of IP and organization abbreviation

    :status 200: Organizations or empty object
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    rv = {}
    orgs = Organization.query.all()
    if not orgs:
        return ApiResponse({}, 204)
    for o in orgs:
        for cidr in o.ip_ranges:
            cidr_range = ipaddress.ip_network(cidr, strict=False)
            for ip in request.json:
                ipa = ipaddress.ip_address(ip.strip())
                if ipa in cidr_range:
                    rv[ip] = o.abbreviation
    if rv:
        return ApiResponse({'response': rv})
    else:
        return ApiResponse({}, 204)
