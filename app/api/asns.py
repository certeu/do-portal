from flask import request, redirect, url_for
from flask_jsonschema import validate
from app.core import ApiResponse
from app import db
from app.models import Asn
from . import api


@api.route('/asns', methods=['GET'])
def get_asns():
    """Return a list of available deliverables

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/asns HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "asns": [
            {
              "asn": 12345,
              "id": 1
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array asns: List of available ASN objects
    :>jsonobj integer id: AS number unique ID
    :>jsonobj integer asn: AS number

    :status 200: Deliverable endpoint found, response may be empty
    :status 404: Not found
    """
    asns = Asn.query.filter().all()
    return ApiResponse({'asns': [a.serialize() for a in asns]})


@api.route('/asns/<int:asn_id>', methods=['GET'])
def get_asn(asn_id):
    """Get deliverable from database

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/asns/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "asn": 12345,
          "id": 1
        }

    :param asn_id: AS number unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: AS number unique ID
    :>json integer asn: AS number

    :status 200: ASN found
    :status 404: Resource not found
    """
    a = Asn.query.get_or_404(asn_id)
    return ApiResponse(a.serialize())


@api.route('/asns', methods=['POST', 'PUT'])
@validate('asns', 'add_asn')
def add_asn():
    """Create new ASN entry

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/asns HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "active": true,
          "organization_id": 1,
          "asn": 12345
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "asn": {
            "asn": 12345,
            "id": 1
          },
          "message": "Asn added"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json integer asn: AS number
    :<json integer organization_id: Unique ID of organizations owning this ASN
        See available organizations at :http:get:`/api/1.0/organizations`
    :<json boolean active: Actively used
    :>jsonobj integer id: Unique ID of new ASN
    :>jsonobj integer asn: AS number
    :>json string message: Status message

    :status 201: ASN successfully saved
    :status 400: Bad request
    """
    a = Asn().from_json(request.json)
    db.session.add(a)
    db.session.commit()
    return ApiResponse(
        {'asn': a.serialize(), 'message': 'Asn added'},
        201,
        {'Location': url_for('api.get_asn', asn_id=a.id)})


@api.route('/asns/<int:asn_id>', methods=['PUT'])
@validate('asns', 'update_asn')
def update_asn(asn_id):
    """Update ASN

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/asns/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "active": true,
          "organization_id": 1,
          "asn": 12344
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Asn saved"
        }

    :param asn_id: ASN unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json integer asn: AS number
    :<json integer organization_id: Unique ID of organizations owning this ASN
        See available organizations at :http:get:`/api/1.0/organizations`
    :<json boolean active: Actively used
    :>json string msg: Status message

    :status 200: ASN was successfully updated
    :status 400: Bad request
    """
    a = Asn.query.filter(
        Asn.id == asn_id
    ).first()
    if not a:
        return redirect(url_for('api.add_asn'))
    a.from_json(request.json)
    db.session.add(a)
    db.session.commit()
    return ApiResponse({'message': 'Asn saved'})


@api.route('/asns/<int:asn_id>', methods=['DELETE'])
def delete_asn(asn_id):
    """Delete deliverable type

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/asns/2 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Asn deleted"
        }

    :param asn_id: ASN unique ID.

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Action status status

    :status 200: ASN was deleted
    :status 404: ASN was not found
    """
    a = Asn.query.filter(
        Asn.id == asn_id
    ).first_or_404()

    a.deleted = 1
    db.session.add(a)
    db.session.commit()
    return ApiResponse({'message': 'Asn deleted'})
