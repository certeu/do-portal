from flask import g
from app.core import ApiResponse, ApiPagedResponse
from . import cp
from app.models import Vulnerability


@cp.route('/vulnerabilities', methods=['GET'])
def get_vulnerabilities():
    """Return a paginated list of available vulnerabilities
    For vulnerability details see
    :http:get:`/api/1.0/vulnerabilities/(int:vuln_id)`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/vulnerabilities HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        Link: <.../api/1.0/analysis/av?page=1&per_page=20>; rel="First",
              <.../api/1.0/analysis/av?page=1&per_page=20>; rel="Last"

        {
          "count": 1,
          "items": [
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
          ],
          "page": 1
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader Link: Describe relationship with other resources

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
    :>json integer page: Current page number
    :>json integer count: Total number of items

    :status 200: Vulnerabilities list
    :status 404: Not found
    """

    return ApiPagedResponse(
        Vulnerability.query.filter_by(organization_id=g.user.organization_id))


@cp.route('/vulnerabilities/<int:vuln_id>', methods=['GET'])
def get_vulnerability(vuln_id):
    """Return vulnerability identified by `vuln_id`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/vulnerabilities/1 HTTP/1.1
        Host: cp.cert.europa.eu
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
    vuln = Vulnerability.query.\
        filter_by(id=vuln_id, organization_id=g.user.organization_id).\
        first_or_404()
    return ApiResponse(vuln)
