from flask import g, request
from flask_jsonschema import validate
from app import db
from app.models import Country
from app.api.decorators import json_response
from . import cp


@cp.route('/countries', methods=['GET'])
@json_response
def get_cp_countries():
    """Return countries

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/countries HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "countries": [
            {
              "id": 23,
              "cc": "AT",
              "name": "Austria"
            },
            {
              "id": 24,
              "cc": "JP",
              "name": "Japan"
            },
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
    :resheader Content-Type: This depends on `Accept` header or request

    :>json array organizations: List of available membership country objects

    For details: :http:get:`/api/1.0/countries/(int:country_id)`

    :status 200: Country endpoint found, response may be empty
    :status 404: Not found
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    countries = Country.query.all()
    return {'countries': [c.serialize() for c in countries]}


@cp.route('/countries/<int:country_id>', methods=['GET'])
@json_response
def get_cp_country(country_id):
    """Return country identified by ``country_id``

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/countries/23 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "id": 23,
          "cc": "AT",
          "name": "Austria"
        },

    :param country_id: Membership role unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :reqheader API-Authorization: API key. If present authentication and
            authorization will be attempted.
    :resheader Content-Type: This depends on `Accept` header or request

    :>json integer id: Membership role unique ID
    :>json string cc: Country code
    :>json string name: Country name

    :status 200: Returns membership role details object
    :status 404: Resource not found
    :status 401: Authorization failure. The client MAY repeat the request with
        a suitable API-Authorization header field. If the request already
        included Authorization credentials, then the 401 response indicates
        that authorization has been refused for those credentials.
    :status 403: Access denied. Authorization will not help and the request
        SHOULD NOT be repeated.
    """
    c = Country.query.get_or_404(country_id)
    return c.serialize()
