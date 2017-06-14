from flask import request, redirect, url_for
from flask_jsonschema import validate
from app import db
from app.core import ApiResponse
from app.models import Fqdn
from . import api


@api.route('/fqdns', methods=['GET'])
def get_fqdns():
    """Return a list of available `fully qualified domain names
    <https://en.wikipedia.org/wiki/Fully_qualified_domain_name>`_

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/fqdns HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "fqdns": [
            {
              "fqdn": "cert.europa.eu",
              "id": 1
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array fqdns: List of available fully qualified domain name objects
    :>jsonobj integer id: FQDN unique ID
    :>jsonobj integer fqdn: Fully qualified domain name

    :status 200: Deliverable endpoint found, response may be empty
    :status 404: Not found
    """
    fqdns = Fqdn.query.filter(
        Fqdn.deleted == 0).all()
    return ApiResponse({'fqdns': [f.serialize() for f in fqdns]})


@api.route('/fqdns/<int:fqdn_id>', methods=['GET'])
def get_fqdn(fqdn_id):
    """Get `fully qualified domain name
    <https://en.wikipedia.org/wiki/Fully_qualified_domain_name>`_

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/fqdns/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "fqdn": "cert.europa.eu",
          "typosquats": [
            {
              "dns_a": "103.224.182.240",
              "dns_ns": "ns2.above.com",
              "fqdn": "cert.europai.eu",
              "id": 2,
              "updated": "2016-11-04T15:22:39"
            }
          ],
          "id": 1
        }

    :param fqdn_id: FQDN unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: FQDN unique ID
    :>json string fqdn: `fully qualified domain name
      <https://en.wikipedia.org/wiki/Fully_qualified_domain_name>`_
    :>json array typosquats: List of typosquats discovered

    :status 200: FQDN found
    :status 404: Resource not found
    """
    f = Fqdn.query.get_or_404(fqdn_id)
    return ApiResponse(f.serialize())


@api.route('/fqdns/<string:fqdn>', methods=['GET'])
def get_fqdn_by_name(fqdn):
    """Get `fully qualified domain name
    <https://en.wikipedia.org/wiki/Fully_qualified_domain_name>`_

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/fqdns/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "fqdn": "cert.europa.eu",
          "typosquats": [
              {
                "dns_a": "103.224.182.240",
                "dns_ns": "ns2.above.com",
                "fqdn": "cert.europai.eu",
                "id": 2,
                "updated": "2016-11-04T15:22:39"
              }
            ],
          "id": 1
        }

    :param fqdn: FQDN

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: FQDN unique ID
    :>json string fqdn: `fully qualified domain name
      <https://en.wikipedia.org/wiki/Fully_qualified_domain_name>`_
    :>json array typosquats: List of typosquats discovered

    :status 200: FQDN found
    :status 404: Resource not found
    """
    f = Fqdn.query.filter_by(fqdn=fqdn).first_or_404()
    return ApiResponse(f.serialize())


@api.route('/fqdns', methods=['POST', 'PUT'])
@validate('fqdns', 'add_fqdn')
def add_fqdn():
    """Add fully qualified domain name

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/fqdns HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "active": true,
          "organization_id": 1,
          "fqdn": "cert.europa.eu"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "fqdn": {
            "fqdn": "cert.europa.eu",
            "id": 1
          },
          "message": "Fqdn added"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string fqdn: fully qualified domain name
    :<json integer organization_id: Unique ID of organization
        See available organizations at :http:get:`/api/1.0/organizations`
    :<json boolean active: Actively used
    :>jsonobj integer id: Unique ID of newly added fully qualified domain name
    :>jsonobj string fqdn: fully qualified domain name
    :>json string message: Status message

    :status 201: FQDN successfully saved
    :status 400: Bad request
    """
    f = Fqdn().from_json(request.json)
    db.session.add(f)
    db.session.commit()
    return ApiResponse(
        {'fqdn': f.serialize(), 'message': 'Fqdn added'},
        201,
        {'Location': url_for('api.get_fqdn', fqdn_id=f.id)})


@api.route('/fqdns/<int:fqdn_id>', methods=['PUT'])
@validate('fqdns', 'update_fqdn')
def update_fqdn(fqdn_id):
    """Update `fully qualified domain names
    <https://en.wikipedia.org/wiki/Fully_qualified_domain_name>`_

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/fqdns/2 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "fqdn": "cert.europa.net",
          "id": 2,
          "active": true
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Fqdn saved"
        }

    :param fqdn_id: FQDN unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string fqdn: fully qualified domain name
    :<json integer organization_id: Unique ID of organization
        See available organizations at :http:get:`/api/1.0/organizations`
    :<json boolean active: Actively used
    :>jsonobj integer id: Unique ID of newly added fully qualified domain name
    :>jsonobj string fqdn: fully qualified domain name
    :>json string message: Status message

    :status 200: FQDN was successfully updated
    :status 400: Bad request
    """
    f = Fqdn.query.filter(
        Fqdn.id == fqdn_id
    ).first()
    if not f:
        return redirect(url_for('api.add_fqdn'))
    f.from_json(request.json)
    db.session.add(f)
    db.session.commit()
    return ApiResponse({'message': 'Fqdn saved'})


@api.route('/fqdns/<int:fqdn_id>', methods=['DELETE'])
def delete_fqdn(fqdn_id):
    """Delete `fully qualified domain names
    <https://en.wikipedia.org/wiki/Fully_qualified_domain_name>`_

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/fqdns/2 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Fqdn deleted"
        }

    :param fqdn_id: FQDN unique ID.

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Action status status

    :status 200: FQDN was deleted
    :status 404: FQDN was not found
    """
    f = Fqdn.query.filter(
        Fqdn.id == fqdn_id
    ).first_or_404()

    f.deleted = 1
    db.session.add(f)
    db.session.commit()
    return ApiResponse({'message': 'Fqdn deleted'})
