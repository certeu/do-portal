import datetime
from flask import request, redirect, url_for, g
from flask_jsonschema import validate
from app.core import ApiResponse
from app import db
from app.models import Vulnerability, Tag
from app.tasks.vulnerabilities import check_patched
from . import api


@api.route('/vulnerabilities', methods=['GET'])
def get_vulnerabilities():
    """Return a paginated list of available vulnerabilities

    For vulnerability details see
      :http:get:`/api/1.0/vulnerabilities/(int:vuln_id)`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/vulnerabilities HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "vulnerabilities": [
            {
              "check_string": "--></script><script>alert('Patatas')</script>",
              "constituent": "CERT-EU",
              "do": "Test Account",
              "id": 1,
              "reported": "2016-06-14T21:03:36",
              "request_method": "GET",
              "rtir_id": 24285,
              "types": [
                "XSS",
                "CSRF"
              ],
              "updated": "2016-06-14T21:03:36",
              "url": "https://webgate.ec.europa.eu/europeaid/online-servic"
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array items: List of available vulnerabilities
    :>jsonarr integer id: Vulnerability unique ID
    :>jsonarr string url: Vulnerable URL
    :>jsonarr string check_string: Vulnerability check
    :>jsonarr string constituent: Affected constituent abbreviation
    :>jsonarr string do: Dutty officer
    :>jsonarr string reported: Report date
    :>jsonarr string request_method: ``GET``, ``POST`` or ``PUT``
    :>jsonarr string rtir_id: RTIR investigation ID
    :>jsonarr array types: One or more vulnerability types
    :>jsonarr array updated: Last updated (last checked) date

    :status 200: Vulnerabilities list
    :status 404: Not found
    """
    vulns = Vulnerability.query.all()
    return ApiResponse({'vulnerabilities': [v.serialize() for v in vulns]})


@api.route('/vulnerabilities/<int:vuln_id>', methods=['GET'])
def get_vulnerability(vuln_id):
    """Return vulnerability identified by `vuln_id`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/vulnerabilities/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "check_string": "--></script><script>alert('Patatas')</script>",
          "constituent": "CERT-EU",
          "do": "Test Account",
          "id": 1,
          "reported": "2016-06-14T21:03:36",
          "request_method": "GET",
          "rtir_id": 24285,
          "types": [
            "XSS",
            "CSRF"
          ],
          "updated": "2016-06-14T21:03:36",
          "url": "https://webgate.ec.europa.eu/europeaid/online-servic"
        }

    :param vuln_id: vulnerability unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: Vulnerability unique ID
    :>json string url: Vulnerable URL
    :>json string check_string: Vulnerability check
    :>json string constituent: Affected constituent abbreviation
    :>json string do: Dutty officer
    :>json string reported: Report date
    :>json string request_method: ``GET``, ``POST`` or ``PUT``
    :>json string rtir_id: RTIR investigation ID
    :>json array types: One or more vulnerability types
    :>json array updated: Last updated (last checked) date

    :status 200: Returns vulnerability details object
    :status 404: Resource not found
    """
    vuln = Vulnerability.query.get_or_404(vuln_id)
    return ApiResponse(vuln)


@api.route('/vulnerabilities', methods=['POST', 'PUT'])
@validate('vulnerabilities', 'add_vulnerability')
def add_vulnerability():
    """Add new vulnerability

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/vulnerabilities HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "check_string": "--></script><script>alert('Patatas')</script>",
          "url": "https://webgate.ec.europa.eu/europeaid/online-services...",
          "organization_id": 12,
          "reporter_name": "Eric Clapton",
          "reporter_email": "eric@clapton.com",
          "rtir_id": 24285,
          "type": ["asda", "asdasd"]
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json
        Location: https://do.cert.europa.eu/api/1.0/vulnerabilities/1

        {
          "message": "Vulnerability added",
          "vulnerability": {
            "check_string": "--></script><script>alert('Patatas')</script>",
            "constituent": "CERT-EU",
            "do": "Test Account",
            "id": 1,
            "reported": "2016-06-14T21:03:36",
            "request_method": "GET",
            "rtir_id": 24285,
            "types": [
              "XSS",
              "CSRF"
            ],
            "updated": "2016-06-14T21:03:36",
            "url": "https://webgate.ec.europa.eu/europeaid/online-services..."
          }
        }

    **Example validation error**:

    .. sourcecode:: http

        HTTP/1.0 422 UNPROCESSABLE ENTITY
        Content-Type: application/json

        {
          "message": "'reporter_name' is a required property",
          "validator": "required"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader Location: URL of newly created resource

    :<json string url: Vulnerable URL
    :<json string check_string: Vulnerability check
    :<json string organization_id: Organization unique ID.
        Get unique IDs from :http:get:`/api/1.0/organizations`.
    :<json string reported: Report date
    :<json string request_method: ``GET``, ``POST`` or ``PUT``.
        Defaults to ``GET``.
    :<json string rtir_id: RTIR investigation ID
    :<json array types: One or more vulnerability types

    :>json object vulnerability: New vulnerability object
    :>json string message: Status message

    :status 200: Vulnerability was successfully added
    :status 422: Request could not be processed
    """
    list_types = []
    if 'types' in request.json:
        json_types = request.json.pop('types')
        for vtype in json_types:
            if Tag.query.filter_by(name=vtype).first():
                list_types.append(Tag.query.filter_by(name=vtype).first())
            else:
                list_types.append(Tag(name=vtype))

    v = Vulnerability.fromdict(request.json)
    if list_types:
        v.labels_ = list_types
    v.user_id = g.user.id
    db.session.add(v)
    db.session.commit()
    return ApiResponse(
        {
            'vulnerability': v.serialize(),
            'message': 'Vulnerability added'
        }, 201, {
            'Location': url_for('api.get_vulnerability', vuln_id=v.id)
        })


@api.route('/vulnerabilities/<int:vuln_id>', methods=['PUT'])
@validate('vulnerabilities', 'update_vulnerability')
def update_vulnerability(vuln_id):
    """Update vulnerability details

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/vulnerabilities/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "reporter_name": "Test updated"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Vulnerability saved"
        }

    **Example validation error**:

    .. sourcecode:: http

        HTTP/1.0 422 UNPROCESSABLE ENTITY
        Content-Type: application/json

        {
          "message": "'reporter_name' is a required property",
          "validator": "required"
        }

    :param vuln_id: Vulnerability unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string url: Vulnerable URL
    :<json string check_string: Vulnerability check
    :<json string organization_id: Organization unique ID.
        Get unique IDs from :http:get:`/api/1.0/organizations`.
    :<json string reported: Report date
    :<json string request_method: ``GET``, ``POST`` or ``PUT``.
        Defaults to ``GET``.
    :<json string rtir_id: RTIR investigation ID
    :<json array types: One or more vulnerability types

    :>json string message: Status message

    :status 200: Vulnerability was successfully added
    :status 422: Request could not be processed
    """
    vuln = Vulnerability.get(vuln_id)
    if not vuln:
        return redirect(url_for('api.add_vulnerability'))

    list_types = []
    if 'types' in request.json:
        json_types = request.json.pop('types')
        for vtype in json_types:
            if Tag.query.filter_by(name=vtype).first():
                list_types.append(Tag.query.filter_by(name=vtype).first())
            else:
                list_types.append(Tag(name=vtype))

    vuln.from_json(request.json)
    vuln.labels_ = list_types
    db.session.add(vuln)
    db.session.commit()
    return ApiResponse({'message': 'Vulnerability saved'})


@api.route('/vulnerabilities/<int:vuln_id>', methods=['DELETE'])
def delete_vulnerability(vuln_id):
    """Delete vulnerability

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/vulnerabilities/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Vulnerability deleted"
        }

    :param vuln_id: Vulnerability unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Status message

    :status 200: Vulnerability was deleted
    :status 400: Bad request
    """
    g = Vulnerability.query.get_or_404(vuln_id)

    g.deleted = 1
    db.session.add(g)
    db.session.commit()
    return ApiResponse({'message': 'Vulnerability deleted'})


@api.route('/vulnerabilities/test/<int:vuln_id>', methods=['GET'])
def test_vulnerability(vuln_id):
    """Test vulnerability

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/vulnerabilities/test/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Vulnerability tested"
        }

    :param vuln_id: Vulnerability unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Status message

    :status 200: Vulnerability was tested
    :status 400: Bad request
    """
    g = Vulnerability.query.get_or_404(vuln_id)
    g.tested = datetime.datetime.now()
    rc, status_code = check_patched(g.request_method, g.url, g.request_data,
                                    g.check_string)

    if rc == 1:
        g.patched = datetime.datetime.now()
    elif rc == 0:
        g.patched = None

    g.request_response_code = status_code

    db.session.add(g)
    db.session.commit()

    return ApiResponse({'message': 'Vulnerability Tested'})


@api.route('/vulnerabilities/changestatus/<int:vuln_id>', methods=['GET'])
def changestatus_vulnerability(vuln_id):
    """Change vulnerability status

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/vulnerabilities/changestatus/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Vulnerability tested"
        }

    :param vuln_id: Vulnerability unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Status message

    :status 200: Vulnerability was tested
    :status 400: Bad request
    """
    g = Vulnerability.query.get_or_404(vuln_id)

    if g.patched is None:
        g.patched = datetime.datetime.now()
    else:
        g.patched = None

    db.session.add(g)
    db.session.commit()

    return ApiResponse({'message': 'Vulnerability patch status changed'})
