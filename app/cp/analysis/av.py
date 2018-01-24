"""
    CP AV scan reports endpoint
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import json
from flask import request, current_app, g
from app.core import ApiResponse
from app.cp import cp
from app.models import Report, Sample
from app.tasks import analysis
from app.utils.avscanlib import Scanner


@cp.route('/analysis/av/<string:sha256>', methods=['GET'])
def get_cp_av_scan(sha256):
    """Return last antivirus scan report for sample identified by its SHA256.

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/av/1eedab2b09a4bf6c87b273305c096fa2f5... HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "created": "2016-03-20T16:58:17",
          "id": 1,
          "report": "...",
          "report_parsed": {
            "ClamAV": {...},
            "F-Prot": {...},
            "SAVAPI": {}
          },
          "type": "AntiVirus scan"
        }

    :param sha256: SHA256 of file

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: Scan unique ID
    :>json string created: Scan time
    :>json string report: Antivirus scan report
    :>json string report_parsed: Parsed antivirus scan report

    :status 200: Scan report found
    :status 404: Resource not found
    """
    s = Sample.query.filter_by(sha256=sha256, user_id=g.user.id).first_or_404()
    report = Report.query.filter_by(type_id=2, sample_id=s.id).first_or_404()
    serialized = report.serialize()
    if 'report' in serialized:
        serialized['report_parsed'] = json.loads(serialized['report'])
    return ApiResponse(serialized)


@cp.route('/analysis/av', methods=['POST', 'PUT'])
def add_cp_av_scan():
    """Submit files for antivirus scanning.

    This endpoint should be called only after files have been uploaded via
    :http:post:`/cp/1.0/samples`. Also accepts :http:method:`put`.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/analysis/av HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "files": [
            {
              "created": "2016-03-21T16:52:46",
              "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwkTY40GfAHw7qzLl6EKvwk...",
              "filename": "stux.zip",
              "id": 3,
              "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc4..."
            }
          ]
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "files": [
            {
              "created": "2016-03-21T16:52:46",
              "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwkTY40GfAHw7qzLl6EKvwk...",
              "filename": "stux.zip",
              "id": 3,
              "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc45..."
            }
          ],
          "message": "Your files have been submitted for AV scanning"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json array files: List of files to scan
    :<jsonarr integer id: Sample unique ID
    :<jsonarr string created: Time of upload
    :<jsonarr string sha256: SHA256 of file
    :<jsonarr string ctph: CTPH (a.k.a. fuzzy hash) of file
    :<jsonarr string filename: Filename (as provided by the client)
    :>json array files: List of samples accepted for scanning
    :>jsonarr integer id: Sample unique ID
    :>jsonarr string created: Time of upload
    :>jsonarr string sha256: SHA256 of file
    :>jsonarr string ctph: CTPH (a.k.a. fuzzy hash) of file
    :>jsonarr string filename: Filename (as provided by the client)
    :>json string message: Status message

    :status 200: Files accepted for scanning
    :status 400: Bad request
    """
    for f in request.json['files']:
        analysis.multiavscan.delay(f['sha256'])
        s = Sample.query. \
            filter_by(sha256=f['sha256'], user_id=g.user.id). \
            first_or_404()
        try:
            for child in s.children:
                analysis.multiavscan.delay(child.sha256)
        except AttributeError as ae:
            current_app.log.info(ae)
    return ApiResponse(
        {
            'files': request.json['files'],
            'message': 'Your files have been submitted for AV scanning'
        }, 202)


@cp.route('/analysis/av/engines')
def get_cp_av_engines():
    """Return the list of active AV engines

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/av/engines HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "engines": [
            "F-Prot",
            "ESET",
            "F-Secure",
            "SAVAPI",
            "ClamAV"
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array engines: List of available scanning engines

    :status 200:
    :status 400: Bad request
    """
    av = Scanner(current_app.config['AVSCAN_CONFIG'])
    return ApiResponse({'engines': av.engines})
