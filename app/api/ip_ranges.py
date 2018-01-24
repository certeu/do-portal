"""
    IP ranges endpoint module
    ~~~~~~~~~~~~~~~~~~~~~~~~~

"""
from flask import request, redirect, url_for
from flask_jsonschema import validate
from app import db
from app.core import ApiResponse
from app.models import IpRange
from . import api


@api.route('/ip_ranges', methods=['GET'])
@api.route('/ip-ranges', methods=['GET'])
def get_ip_ranges():
    """Return IP ranges

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/ip-ranges HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "ip_ranges": [
            {
              "id": 1,
              "ip_range": "158.168.149.0/24"
            },
            {
              "id": 2,
              "ip_range": "158.168.148.0/24"
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array ip_ranges: List of IP ranges
    :>jsonarr integer id: IP range unique ID
    :>jsonarr string ip_range: CIDR IP range

    :status 200: IP ranges endpoint found, response may be empty
    :status 404: Not found
    """
    ips = IpRange.query.all()
    return ApiResponse({'ip_ranges': [r.serialize() for r in ips]})


@api.route('/ip_ranges/<int:range_id>', methods=['GET'])
@api.route('/ip-ranges/<int:range_id>', methods=['GET'])
def get_ip_range(range_id):
    """Return IP range identified by `range_id`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/ip-ranges/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "id": 1,
          "ip_range": "158.168.149.0/24"
        }

    :param range_id: IP range unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: IP range unique ID
    :>json string ip_range: CIDR IP range

    :status 200: Returns IP range details object
    :status 404: Resource not found
    """
    ip_range = IpRange.query.get_or_404(range_id)
    return ApiResponse(ip_range)


@api.route('/ip_ranges', methods=['POST', 'PUT'])
@api.route('/ip-ranges', methods=['POST', 'PUT'])
@validate('ip_ranges', 'add_ip_range')
def add_ip_range():
    """Add new IP range. Accepts :http:method:`POST` or :http:method:`PUT`.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/ip-ranges HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "active": true,
          "organization_id": 60,
          "ip_range": "1.2.3.4/24"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json
        Location: /api/1.0/ip-ranges/1

        {
          "ip_range": {
            "id": 323,
            "ip_range": "1.2.3.4/24"
          },
          "message": "IP range added"
        }

    **Example validation error**:

    .. sourcecode:: http

        HTTP/1.0 400 BAD REQUEST
        Content-Type: application/json

        {
          "message": "'name' is a required property",
          "validator": "required"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string ip_range: CIDR IP range
    :<json integer organization_id: Organization ID
    :<json boolean active: Active
    :>json object ip_range: New CIDR IP range object
    :>jsonobj integer id: IP range unique ID
    :>jsonobj string ip_range: CIDR IP range
    :>json string message: Status message

    :status 200: CIDR IP range was successfully added
    :status 400: Bad request
    """
    i = IpRange().from_json(request.json)
    db.session.add(i)
    db.session.commit()
    return ApiResponse({
        'ip_range': i.serialize(),
        'message': 'IP range added'
    }, 201, {
        'Location': url_for('api.get_ip_range', range_id=i.id)
    })


@api.route('/ip_ranges/<int:range_id>', methods=['PUT'])
@api.route('/ip-ranges/<int:range_id>', methods=['PUT'])
@validate('ip_ranges', 'update_ip_range')
def update_ip_range(range_id):
    """Update IP range

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/ip-ranges HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "active": true,
          "organization_id": 60,
          "ip_range": "1.2.3.4/16"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "IP range saved"
        }

    :param range_id: IP range unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string ip_range: CIDR IP range
    :<json integer organization_id: Organization ID
    :<json boolean active: Active
    :>json string message: Status message

    :status 200: IP range was successfully updated
    :status 400: Bad request
    """
    i = IpRange.query.filter(IpRange.id == range_id).first()
    if not i:
        return redirect(url_for('api.add_ip_range'))
    i.from_json(request.json)
    db.session.add(i)
    db.session.commit()
    return ApiResponse({'message': 'IP range saved'})


@api.route('/ip_ranges/<int:range_id>', methods=['DELETE'])
@api.route('/ip-ranges/<int:range_id>', methods=['DELETE'])
def delete_ip_range(range_id):
    """Delete IP range

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/ip-ranges/324 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "IP range deleted"
        }

    :param range_id: IP range ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Status message

    :status 200: IP range was deleted
    :status 400: Bad request
    """
    i = IpRange.query.filter(IpRange.id == range_id).first_or_404()

    i.deleted = 1
    db.session.add(i)
    db.session.commit()
    return ApiResponse({'message': 'IP range deleted'})
