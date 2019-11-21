"""
    FireEye analysis endpoint
    ~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import hashlib
import json
import os

from flask import request, current_app, g, session, abort
from flask_jsonschema import validate
from app.core import ApiResponse
from app import fireeye, db, ApiException
from app.api import api
from app.models import Sample, Report


_STATUS_DONE = "DONE"
_STATUS_IN_PROGRESS = "IN PROGRESS"


def _abort_not_found():
    abort(404)


def _get_token_header(token):
    headers = {
        'X-FeApi-Token': token
    }
    return headers


def _get_api_token_from_session():
    return session.get('FE_API_TOKEN', None)


def _get_headers():
    return _get_token_header(_get_api_token_from_session())


def _get_submission_status(submission_id):
    try:
        return fireeye.submission_status(submission_id, headers=_get_headers())
    except Exception as err:
        current_app.log.error(err)
        raise ApiException("Failed to get status from FireEye AX")


def _get_submission_result(submission_id):
    params = {
        'info_level': 'extended'
    }
    try:
        return fireeye.submission_results(submission_id, headers=_get_headers(), params=params)
    except Exception as err:
        current_app.log.error(err)
        raise ApiException("Failed to get result from FireEye AX")


def _get_sample_by_id_and_sha256(sample_id, sample_sha256, only_current_user=False):
    if only_current_user:
        sample_query = Sample.query.filter_by(id=sample_id, sha256=sample_sha256, user_id=g.user.id)
    else:
        sample_query = Sample.query.filter_by(id=sample_id, sha256=sample_sha256)

    sample = sample_query.one_or_none()
    if sample is None:
        _abort_not_found()
    return sample


def _get_all_reports_by_sample_id(sample_id):
    return Report.query.filter_by(sample_id=sample_id, type_id=3).all()


def _get_report_by_id_and_sha256(report_id, sample_sha256, only_current_user=False):
    report = Report.query.filter_by(id=report_id, type_id=3).one_or_none()
    if report is None:
        _abort_not_found()

    _ = _get_sample_by_id_and_sha256(report.sample_id, sample_sha256, only_current_user=only_current_user)

    return report


def process_get_fireeye_report(sha256, rid, only_current_user=False):
    report = _get_report_by_id_and_sha256(rid, sha256, only_current_user=only_current_user)

    serialized_report = report.report
    if serialized_report is None:
        _abort_not_found()

    deserialized_report = json.loads(serialized_report)

    env = deserialized_report['env']
    submission_id = deserialized_report['submission_id']

    result = _get_submission_result(submission_id)

    report = {
        'env': env,
        'result': result
    }

    results = [report]

    return ApiResponse({'results': results})


@api.route('/analysis/fireeye/report/<string:sha256>/<int:rid>', methods=['GET'])
def get_fireeye_report(sha256, rid):
    return process_get_fireeye_report(sha256, rid, only_current_user=False)


def process_get_fireeye_analysis(sha256, sid, only_current_user=False):
    sample = _get_sample_by_id_and_sha256(sid, sha256, only_current_user=only_current_user)
    reports = _get_all_reports_by_sample_id(sample.id)

    results = []

    for report in reports:
        serialized_report = report.report
        if serialized_report is not None:
            deserialized_report = json.loads(serialized_report)

            env = deserialized_report['env']
            submission_id = deserialized_report['submission_id']
            list_id = deserialized_report.get('list_id')
            status = _STATUS_IN_PROGRESS

            if list_id is not None:
                submission_status = _get_submission_status(list_id)
                if submission_status['status'] == 'Submission Done':
                    status = _STATUS_DONE
            else:
                submission_status = _get_submission_status(submission_id)
                if submission_status['submissionStatus'] == 'Done':
                    status = _STATUS_DONE

            status = {
                'env': env,
                'report_id': report.id,
                'submission_status': status
            }

            results.append(status)

    return ApiResponse({'statuses': results})


@api.route('/analysis/fireeye/<string:sha256>/<int:sid>', methods=['GET'])
def get_fireeye_analysis(sha256, sid):
    """Return FireEye Sandbox dynamic analysis for sample identified by
        :attr:`~app.models.Sample.sha256`, running in :param: envid.

    ..  note::

        FireEye Sandbox REST API returns mixed responses.
        Most errors will return :http:statuscode:`200`.

    **Example request**:

    .. sourcecode:: http

        GET api/1.0/analysis/fireeye/54abd4674f61029d9ae3f8f805b9b7/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example success response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "response": {
            "analysis_start_time": "2016-04-28 17:03:52",
            "domains": [],
            "environmentDescription": "Windows 7 64 bit (KERNELMODE)",
            "environmentId": "6",
            "hosts": [
              "40.118.103.7"
            ],
            "isinteresting": false,
            "isurlanalysis": false,
            "md5": "864cc77a27d4618149ec0bba060bbca0",
            "multiscan_detectrate_pcnt": 0,
            "sha1": "31fced6d00e58147bff56902b986fd0cc6295aeb",
            "sha256": "54abd4674f61029d9ae3f8f8f5a484d396d10b87c9dc77765d87c2",
            "size": 336384,
            "submitname": "54abd4674f61029d9ae3f8f8f5a484d396d10b87c9dc777657",
            "targeturl": "",
            "threatlevel": 1,
            "threatscore": 41,
            "type": "PE32 executable (GUI) Intel 80386 Mono/.Net assembly"
          },
          "response_code": 0
        }

    **Example error response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "response": {
            "error": "Failed to save report to webservice",
            "state": "ERROR"
          },
          "response_code": 0
        }

    :param sha256: SHA256 of file
    :param sid: Sample identifier.

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer response_code: Response code.
      ``0`` for success, ``-1`` for errors
    :>json object response: Analysis summary or error details
    :>jsonobj string analysis_start_time: Analysis start time
    :>jsonobj array domains: Domains contacted during analysis
    :>jsonobj string environmentDescription: Environment details
    :>jsonobj string environmentId: Environment unique ID
    :>jsonobj array hosts: Hosts contacted during analysis
    :>jsonobj boolean isinteresting:
    :>jsonobj boolean isurlanalysis: Marker for URL analyzer
    :>jsonobj integer multiscan_detectrate_pcnt:
    :>jsonobj string md5: MD5 digest calculated upstream
    :>jsonobj string sha1: SHA1 digest calculated upstream
    :>jsonobj string sha256: SHA256 digest calculated upstream
    :>jsonobj integer size: Size of sample in bytes
    :>jsonobj string submitname: Submission file name
    :>jsonobj string targeturl:
    :>jsonobj integer threatlevel: Threatlevel
    :>jsonobj integer threatscore: Threat score
    :>jsonobj string type: Type of sample
    :>jsonobj string state: State of analysis
    :>jsonobj string error: Error message reported by upstream

    :status 200: Request successful. ``response_code`` check required to
      determine if action was successful.
    :status 404: Resource not found
    """
    return process_get_fireeye_analysis(sha256, sid, only_current_user=False)


def process_add_fireeye_analysis():
    token = _get_api_token_from_session()

    statuses = []

    request_data = request.json

    for f in request_data['files']:
        sample_id = f['id']
        sample_sha256 = f['sha256']

        sample = _get_sample_by_id_and_sha256(sample_id, sample_sha256, only_current_user=True)

        submit_samples = [sample]

        children = sample.children
        if children:
            submit_samples.extend(children)

        submitted_sha256s = set()
        for env in request_data['dyn_analysis']['fireeye']:
            for submit_sample in submit_samples:
                submission = _submit_to_fireeye(submit_sample, env, token)

                submit_sample.reports.append(_create_report(submission))

                submitted_sha256s.add(submit_sample.sha256)

                db.session.add(submit_sample)
            db.session.commit()

        for submitted_sha256 in submitted_sha256s:
            statuses.append({'sha256': submitted_sha256})

    return ApiResponse({
        'statuses': statuses,
        'message': 'Your files have been submitted for dynamic analysis'
    }, 202)


@api.route('/analysis/fireeye', methods=['POST', 'PUT'])
def add_fireeye_analysis():
    """Submit sample to the FireEye Sandbox. Also accepts :http:method:`put`.

    This endpoint should be called only after files have been uploaded via
    :http:post:`/api/1.0/samples`

    Files should be available under :attr:`config.Config.APP_UPLOADS_SAMPLES`.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/analysis/fireeye HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "files": [
            {
              "sha256": "9cf31818452fd16847171022d3d13713504db85733c265aa9398"
            }
          ],
          "dyn_analysis": {
            "fireeye": [5, 6]
          }
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 202 ACCEPTED
        Content-Type: application/json

        {
          "message": "Your files have been submitted for dynamic analysis",
          "statuses": [
            {
              "error": "Failed to submit file: analysis already exists for
              9cf31818452fd16847171022d3d13713504db85733c265aa93987ef23474fb95
              and allowOverwritingReports is disabled"
            },
            {
              "sha256": "33a53e3b28ee41c29afe79f49ecc53b34ac125e5e15f9e7cf10c0"
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json array files: List of files to scan. Files must be uploaded using
        :http:post:`/api/1.0/samples`
    :<jsonarr string sha256: SHA256 of file
    :<json object dyn_analysis: Sandbox configuration
    :<jsonarr array fireeye: List of FireEye environments to submit to.
        Get the list from :http:get:`/api/1.0/analysis/fireeye/environments`.
    :>json array statuses: List of statuses returned by upstream APIs.
    :>jsonarr string error: Error message from upstream API
    :>jsonarr string sha256: SHA256 calculated by upstream API
    :>json string message: Status message

    :status 202: Files have been accepted for dynamic analysis
    :status 400: Bad request
    """
    return process_add_fireeye_analysis()


def _create_url_sample(url):
    sha256 = hashlib.sha256(url.encode('utf-8')).hexdigest()
    return Sample(filename=url, sha256=sha256, user_id=g.user.id, md5='N/A', sha1='N/A', sha512='N/A', ctph='N/A')


def process_add_fireeye_url_analysis():
    token = _get_api_token_from_session()

    statuses = []

    request_data = request.json
    for url in request_data['urls']:
        if not url:
            raise ApiException("No URL to submit")

        if not url.startswith('http'):
            url = 'http://' + url

        sample = _create_url_sample(url)

        for env in request_data['dyn_analysis']['fireeye']:
            submission = _submit_url_to_fireeye(url, env, token)

            report = _create_report(submission)
            sample.reports.append(report)

        statuses.append({'sha256': sample.sha256})

        db.session.add(sample)
        db.session.commit()

    return ApiResponse({
        'statuses': statuses,
        'message': 'Your URLs have been submitted for dynamic analysis'
    }, 202)


@api.route('/analysis/fireeye-url', methods=['POST', 'PUT'])
@validate('analysis', 'add_fireeye_url_analysis')
def add_fireeye_url_analysis():
    """Submit URLs to the FireEye Sandbox. Also accepts :http:method:`put`.

    .. warning::

        Not Implemented

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/analysis/fireeye-url HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "urls": ["http://cert.europa.eu"],
          "dyn_analysis": {
            "fireeye": [5, 6]
          }
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Your URLs have been submitted for dynamic analysis",
          "statuses": [
            {
              "sha256": "33a53e3b28ee41c29afe79f49ecc53b34ac125e5e15f9e7c..."
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json array files: List of URLs to scan
    :<jsonarr string sha256: SHA256 of the shortcut file created
    :<json object dyn_analysis: Sandbox configuration
    :<jsonarr array fireeye: List of FireEye environments to submit to
        Get the list from :http:get:`/api/1.0/analysis/fireeye/environments`
    :>json array statuses: List of statuses returned by upstream APIs
    :>jsonarr string error: Error message from upstream API
    :>jsonarr string sha256: SHA256 calculated by upstream API
    :>json string message: Status message

    :status 202: The URLs have been accepted for scanning
    :status 400: Bad request
    """
    return process_add_fireeye_url_analysis()


def _get_sensor_profiles(config):
    entity = config["entity"]
    sensors = entity["sensors"]

    # At the moment there is only one sensor.
    sensor = sensors[0]

    profiles = sensor["profiles"]

    results = []
    for profile in profiles:
        results.append({"id": profile["id"], "name": profile["name"]})

    return results


def process_get_fireeye_environments():
    headers = _get_headers()

    try:
        config = fireeye.config(headers=headers)
        profiles = _get_sensor_profiles(config)
    except Exception as err:
        current_app.log.error(err)
        raise ApiException("Failed to get environments from FireEye AX")

    return ApiResponse({'environments': sorted(profiles, key=lambda i: i['id'])})


@api.route('/analysis/fireeye/environments')
def get_fireeye_environments():
    """Returns a list of available FireEye Sandbox environments

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/fireeye/environments HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "environments": [
            {
              "id": 4,
              "name": "Windows 8.1 64 bit"
            },
            {
              "id": 3,
              "name": "Windows 10 64 bit"
            },
            {
              "id": 2,
              "name": "Windows 7 32 bit"
            },
            {
              "id": 1,
              "name": "Windows 7 64 bit"
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array environments: Environments available
    :>jsonarr integer id: Environment unique ID
    :>jsonarr string name: Environment name (usually OS name)

    :status 200:
    """
    return process_get_fireeye_environments()


def _open_uploaded_sample(filename):
    cfg = current_app.config
    samples_dir = cfg['APP_UPLOADS_SAMPLES']
    return open(os.path.join(samples_dir, filename), 'rb')


def _create_url_submission_data(list_id, submission_id, env):
    return {
        "list_id": list_id,
        "submission_id": submission_id,
        "env": env
    }


def _create_submission_data(submission_id, env):
    return {
        "submission_id": submission_id,
        "env": env
    }


def _create_report(submission_data):
    serialized_report_content = json.dumps(submission_data)
    return Report(type_id=3, report=serialized_report_content)


def _get_submission_id_from_submissions(submissions):
    return submissions[0]['ID']


def _submit_to_fireeye(sample, env, token):
    """Submit ``sample`` to FireEye Sandbox for analysis.

    :param sample:
    :param env:
    :param token: FireEye Auth Token
    :return:
    """
    files = []
    try:
        filename = sample.filename
        file_obj = _open_uploaded_sample(sample.sha256)

        files.append(('filename', (filename, file_obj)))
    except IOError as io_err:
        current_app.log.error(io_err)
        return None
    except AttributeError as ae:
        current_app.log.error(ae)
        return None

    options = {
        "application": -1,
        "timeout": 500,
        "priority": 0,
        "profiles": [env],
        "analysistype": 2,
        "force": True,
        "prefetch": 1,
    }

    try:
        submissions = fireeye.submissions(options, files, headers=_get_token_header(token))
        submission_id = _get_submission_id_from_submissions(submissions)
        return _create_submission_data(submission_id, env)
    except Exception as err:
        current_app.log.error(err)
        raise ApiException("Failed to submit file to FireEye AX")
    finally:
        for (_, value) in files:
            _, file_obj = value
            file_obj.close()


def _get_list_id_from_url_submissions(url_submissions):
    entity = url_submissions['entity']
    response = entity['response']
    return response[0]['id']


def _get_submission_id_from_url_submissions_status(url_submissions_status):
    response = url_submissions_status['response']
    return response[0]['id']


def _submit_url_to_fireeye(url, env, token):
    """Submit ``sample`` to FireEye Sandbox for analysis.

    :param url:
    :param env:
    :param token: FireEye Auth Token
    :return:
    """
    urls = [url]

    options = {
        "timeout": 500,
        "priority": 0,
        "profiles": [env],
        "application": 0,
        "force": True,
        "analysistype": 2,
        "prefetch": 1,
        "urls": urls
    }

    try:
        submissions = fireeye.submissions_url(options, headers=_get_token_header(token))
    except Exception as err:
        current_app.log.error(err)
        raise ApiException("Failed to submit URL to FireEye AX")

    list_id = _get_list_id_from_url_submissions(submissions)

    submission_status = _get_submission_status(list_id)

    submission_id = _get_submission_id_from_url_submissions_status(submission_status)

    return _create_url_submission_data(list_id, submission_id, env)
