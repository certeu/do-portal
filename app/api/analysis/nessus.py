"""
    Nessus scan endpoint
    ~~~~~~~~~~~~~~~~~~~~

"""
import json
from flask import request, current_app
from app.core import ApiResponse, ApiPagedResponse
from app.api import api
from app.models import Report, Sample
from app import nessus


@api.route('/analysis/nessus', methods=['GET'])
def get_nessus_scans():
    """Return a paginated list of Nessus scan reports.

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/nessus?page=1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        Link: <.../api/1.0/analysis/nessus?page=1&per_page=20>; rel="First",
              <.../api/1.0/analysis/nessus?page=0&per_page=20>; rel="Last"

        {
          "count": 3,
          "items": [
            {
              "created": "2016-03-21T16:52:52",
              "id": 4,
              "report": "...",
              "type": "Nessus scan"
            },
            {
              "created": "2016-03-21T16:51:49",
              "id": 3,
              "report": "...",
              "type": "Nessus scan"
            },
            {
              "created": "2016-03-20T17:09:03",
              "id": 2,
              "report": "...",
              "type": "Nessus scan"
            }
          ],
          "page": 1
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader Link: Describe relationship with other resources

    :>json array items: Nessus scan reports
    :>jsonarr integer id: Scan unique ID
    :>jsonarr object report: Scan report
    :>json integer page: Current page number
    :>json integer count: Total number of items

    :status 200: Reports found
    :status 404: Resource not found
    """
    return ApiPagedResponse(Report.query.filter_by(type_id=4))


@api.route('/analysis/nessus/<string:sha256>', methods=['GET'])
def get_nessus_scan(sha256):
    s = Sample.query.filter_by(sha256=sha256).first_or_404()
    report = Report.query.filter_by(type_id=4, sample_id=s.id).first_or_404()
    serialized = report.serialize()
    if 'report' in serialized:
        serialized['report_parsed'] = json.loads(serialized['report'])
    return ApiResponse(serialized)


@api.route('/analysis/nessus', methods=['POST', 'PUT'])
def add_nessus_scan():
    scan_uuid = '731a8e52-3ea6-a291-ec0a-d2ff0619c19d7bd788d6be818b65'
    for f in request.json['resource']:
        nessus.api.post('scans', data={'resource': f, 'uuid': scan_uuid})
        pass
    return ApiResponse(
        {
            'files': request.json['resource'],
            'message': 'The resources have been submitted for scanning'
        }, 202)


@api.route('/analysis/nessus/environments')
def get_nessus_environments():
    """Returns a list of available Nessus scanning templates

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/nessus/environments HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "environments": [
            {
              "id": 1,
              "name": "Basic Network Scan",
              "uuid": "731a8e52-3ea6-a291-ec0a-d2ff0619c19d7bd788d6be818b65"
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array environments: Available templates
    :>jsonarr integer id: Template ID
    :>jsonarr string name: Template title
    :>jsonarr string uuid: Universally unique identifier

    :status 200:
    """
    scan_types = nessus.api.get('editor/scan/templates', verify=False)
    envs = []
    i = 0
    for tpl in scan_types['templates']:
        if tpl['uuid'] in current_app.config['REST_CLIENT_NESSUS_TEMPLATES']:
            envs.append({
                'id': i + 1,
                'name': tpl['title'],
                'uuid': tpl['uuid']
            })
    return ApiResponse({'environments': sorted(envs, key=lambda e: e['id'])})
