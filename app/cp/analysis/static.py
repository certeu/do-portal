"""
    CP Static analysis reports endpoint
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import json
from flask import request, g, current_app
from app.core import ApiResponse
from app.tasks import analysis
from app.cp import cp
from app.models import Sample, Report


@cp.route('/analysis/static/<string:sha256>', methods=['GET'])
def get_cp_analysis(sha256):
    """Return last static analysis report for sample identified by it SHA256.

    Use the reports endpoint instead of this:
        :http:get:`/cp/1.0/reports/(string:sha256)`.

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/static/1eedab2b09a4bf6c87b273305c096f... HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "created": "2016-03-23T16:57:10",
          "id": 18,
          "report": "...",
          "report_parsed": {
            "exif": [
              {
                "Directory": "/srv/doportal/app/static/data/samples",
                "ExifToolVersion": 10.11,
                "FileAccessDate": "2016:03:23 15:46:09+01:00",
                "FileInodeChangeDate": "2016:03:20 16:29:13+01:00",
                "FileModifyDate": "2016:03:19 17:34:12+01:00",
                "FileName": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd3...",
                "FilePermissions": "rw-r--r--",
                "FileSize": "2.2 MB",
                "FileType": "ZIP",
                "FileTypeExtension": "zip",
                "MIMEType": "application/zip",
                "SourceFile": "/srv/doportal/app/static/data/samples/1eeda...",
                "ZipBitFlag": 0,
                "ZipCRC": "0x00000000",
                "ZipCompressedSize": 0,
                "ZipCompression": "None",
                "ZipFileName": "StuxNet/",
                "ZipModifyDate": "2010:10:02 10:54:18",
                "ZipRequiredVersion": 10,
                "ZipUncompressedSize": 0
              }
            ],
            "hex": "...",
            "magic": {
              "mimetype": "application/zip",
              "type": "Zip archive data, at least v1.0 to extract"
            },
            "trID": [
              {
                "description": "ZIP compressed archive (4000/1)",
                "extension": ".ZIP",
                "probability": "100.0%"
              }
            ]
          },
          "type": "Static analysis"
        }

    :param sha256: SHA256 of file

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string created: Date of report
    :>json integer id: Unique ID of analysis
    :>json string report: JSON string of report
    :>json object report_parsed: Report object
    :>json array exif: ExifTool information
    :>json string hex: Hex dump of the first 256 bytes
    :>json object magic: libmagic information about the file
    :>jsonobj string mimetype: File mime type
    :>jsonobj string type: Human readable file type details
    :>json object trID: File information as identified by TrID
    :>jsonobj string description: File description
    :>jsonobj string extention: File extension guess
    :>jsonobj string probability: Probability percentage

    :status 200: Static analysis report
    :status 404: Resource not found
    """
    s = Sample.query.filter_by(sha256=sha256, user_id=g.user.id).first_or_404()
    report = Report.query.filter_by(sample_id=s.id, type_id=1).first_or_404()
    serialized = report.serialize()
    if 'report' in serialized:
        serialized['report_parsed'] = json.loads(serialized['report'])
    return ApiResponse(serialized)


@cp.route('/analysis/static', methods=['POST', 'PUT'])
def add_cp_analysis():
    """Submit files for static analysis

    Files within zip archives will be submited separately.

    This endpoint should be called only after files have been uploaded via
    :http:post:`/cp/1.0/samples`. Also accepts :http:method:`put`.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/analysis/static HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "files": [
            {
              "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc45..."
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
              "created": "2016-03-23T14:19:13",
              "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwkTY40GfAHw7qzLl6EKvwk...",
              "filename": "stux.zip",
              "id": 5,
              "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc4..."
            }
          ],
          "message": "Your files have been submitted for static analysis"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json array files: List of files to scan. Files must be uploaded using
        :http:post:`/cp/1.0/samples`
    :<jsonarr string sha256: SHA256 of file
    :>json array files: List of samples accepted for scanning
    :>jsonarr integer id: Sample unique ID
    :>jsonarr string created: Time of upload
    :>jsonarr string sha256: SHA256 of file
    :>jsonarr string ctph: CTPH (a.k.a. fuzzy hash) of file
    :>jsonarr string filename: Filename (as provided by the client)
    :>json string message: Status message

    :status 202: Files have been accepted for scanning
    :status 400: Bad request
    """
    for f in request.json['files']:
        s = Sample.query.filter_by(
            sha256=f['sha256'], user_id=g.user.id).first()
        if s:
            analysis.static.delay(f['sha256'])
            try:
                for child in s.children:
                    analysis.static.apply_async(args=[child.sha256],
                                                countdown=1)
            except AttributeError as ae:
                current_app.log.error(ae)
    return ApiResponse({
        'files': request.json['files'],
        'message': 'Your files have been submitted for static analysis'
    }, 202)
