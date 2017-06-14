"""
    Sample analysis reports
    ~~~~~~~~~~~~~~~~~~~~~~~


"""
import json
from app.core import ApiResponse, ApiPagedResponse
from app.models import Report, Sample
from . import api


@api.route('/reports', methods=['GET'])
def get_reports():
    """Return a paginated list of malware analysis reports

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/reports HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        DO-Page-Next: null
        DO-Page-Prev: null
        DO-Page-Current: 1
        DO-Page-Item-Count: 17

        {

          "count": 17,
          "next": null,
          "page": 1,
          "prev": null,
          "reports": [
            {
              "created": "2016-03-20T17:09:03",
              "id": 2,
              "report": "...",
              "type": "Static analysis"
            },
            {
              "created": "2016-03-20T16:58:17",
              "id": 1,
              "report": "...",
              "type": "AntiVirus scan"
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader DO-Page-Next: Next page URL
    :resheader DO-Page-Prev: Previous page URL
    :resheader DO-Page-Curent: Current page number
    :resheader DO-Page-Item-Count: Total number of items

    :>json array items: List of current page of reports
    :>jsonarr integer id: Report unique ID
    :>jsonarr string report: JSON string of report
    :>jsonarr string created: Report date
    :>jsonarr string type: Type of report. On of: Static analysis,
        AntiVirus scan, Dynamic analysis

    :status 200: IP ranges endpoint found, response may be empty
    :status 404: Not found
    """
    return ApiPagedResponse(Report.query)


@api.route('/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):
    """Return analysis report identified by :attr:`app.models.Report.report_id`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/reports/16 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "created": "2016-03-23T15:22:37",
          "id": 16,
          "report": "...",
          "type": "Static analysis"
        }

    :param report_id: Report unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>jsonarr integer id: Report unique ID
    :>jsonarr string report: JSON string of report
    :>jsonarr string created: Report date
    :>jsonarr string type: Type of report. On of: Static analysis,
        AntiVirus scan, Dynamic analysis

    :status 200: Returns report object
    :status 404: Resource not found
    """
    i = Report.query.get_or_404(report_id)
    return ApiResponse(i.serialize())


@api.route('/reports/<string:sha256>', methods=['GET'])
def get_sample_report(sha256):
    """Return last analysis report for sample identified by
        :attr:`app.models.Sample.sha256`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/reports/1eedab2b09a4bf6c87b273305c096fa2f5977cc1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "reports": [
            {
              "created": "2016-03-23T15:24:22",
              "id": 17,
              "report": "...",
              "report_parsed": {
                "exif": [
                  {
                    "...",
                    "ExifToolVersion": 10.11,
                    "..."
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
          ]
        }

    :param sha256: SHA256 of file

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array reports: Reports
    :>jsonarr integer id: Report unique ID
    :>jsonarr string report: JSON string of report
    :>jsonarr string report_parsed: Parsed report
    :>jsonarr string created: Report date
    :>jsonarr string type: Type of report. On of: Static analysis,
        AntiVirus scan, Dynamic analysis

    :status 200: Returns report object
    :status 404: Resource not found
    """
    sample = Sample.query.filter_by(sha256=sha256).first_or_404()
    reports = []
    static = Report.query.filter_by(sample_id=sample.id, type_id=1).first()
    av = Report.query.filter_by(sample_id=sample.id, type_id=2).first()
    for report in static, av:
        serialized = report.serialize()
        if 'report' in serialized:
            serialized['report_parsed'] = json.loads(serialized['report'])
        reports.append(serialized)
    return ApiResponse({'reports': reports})
