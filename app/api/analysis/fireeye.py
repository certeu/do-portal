"""
    FireEye analysis endpoint
    ~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import os
import gzip
from io import BytesIO

from lxml import etree
from flask import request, current_app, g, send_file, session
from flask_jsonschema import validate
from app.core import ApiResponse, ApiException
from app import fireeye, db
from app.api import api
from app.models import Sample


@api.route('/analysis/fireeye', methods=['GET'])
def get_fireeye_analyses():
    """Return a paginated list of FireEye Sandbox JSON reports.

    .. warning::

        Not Implemented

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/fireeye?page=1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        DO-Page-Next: null
        DO-Page-Prev: null
        DO-Page-Current: 1
        DO-Page-Item-Count: 1

        {
          "count": 3,
          "items": [
            {
              "created": "2016-03-21T16:52:52",
              "id": 4,
              "report": "...",
              "type": "Dynamic analysis"
            },
            {
              "created": "2016-03-21T16:51:49",
              "id": 3,
              "report": "...",
              "type": "Dynamic analysis"
            },
            {
              "created": "2016-03-20T17:09:03",
              "id": 2,
              "report": "...",
              "type": "Dynamic analysis"
            }
          ],
          "next": null,
          "page": 1,
          "prev": null
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader DO-Page-Next: Next page URL
    :resheader DO-Page-Prev: Previous page URL
    :resheader DO-Page-Curent: Current page number
    :resheader DO-Page-Item-Count: Total number of items

    :>json array items: FireEye reports
    :>jsonarr integer id: AV scan unique ID
    :>jsonarr string name: File name
    :>jsonarr string sha256: SHA256 message-digest of file
    :>json integer page: Current page number
    :>json integer prev: Previous page number
    :>json integer next: Next page number
    :>json integer count: Total number of items

    :status 200: Reports found
    :status 404: Resource not found
    """
    raise ApiException({}, 501)
    # return Report.query.filter_by(type_id=5)


@api.route('/analysis/fireeye/report', defaults={'type': 'html'})
@api.route('/analysis/fireeye/report/<string:sha256>/<envid>/<type>',
           methods=['GET'])
def get_fireeye_report(sha256, envid, type):
    raise ApiException({}, 501)
    # XML, HTML, BIN and PCAP are GZipped
    Sample.query.filter_by(sha256=sha256).first_or_404()
    headers = {
        'Accept': 'text/html',
        'User-Agent': 'FireEye Sandbox API Client'}
    params = {'type': type, 'environmentId': envid}
    vx = fireeye.api.get('result/{}'.format(sha256),
                         params=params, headers=headers)
    if type in ['xml', 'html', 'bin', 'pcap']:
        return gzip.decompress(vx)
    return vx


@api.route('/analysis/fireeye/download', defaults={'ftype': 'bin', 'eid': 1})
@api.route('/analysis/fireeye/download/<string:sha256>/<eid>/<ftype>',
           methods=['GET'])
def get_fireeye_download(sha256, eid, ftype):
    raise ApiException({}, 501)
    Sample.query.filter_by(sha256=sha256).first_or_404()
    headers = {
        'Accept': 'text/html',
        'User-Agent': 'FireEye Sandbox API Client'}
    params = {'type': ftype, 'environmentId': eid}
    vx = fireeye.api.get('result/{}'.format(sha256),
                         params=params, headers=headers)
    if ftype in ['xml', 'html', 'bin', 'pcap']:
        ftype += '.gz'
    return send_file(BytesIO(vx),
                     attachment_filename='{}.{}'.format(sha256, ftype),
                     as_attachment=True)


@api.route('/analysis/fireeye/<string:sha256>/<envid>', methods=['GET'])
def get_fireeye_analysis(sha256, envid):
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
    :param envid: Environment ID. For the list of available environments see:
        :http:get:`/api/1.0/analysis/fireeye/environments`.

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
    raise ApiException({}, 501)
    sample = Sample.query.filter_by(sha256=sha256).first_or_404()
    state = fireeye.api.get(
        'state/{}'.format(sha256),
        params={'environmentId': envid})
    status = state['response_code'] == 0
    if status and state['response']['state'] == 0:
        #: FIXME: return the fireeye.api.get('result/sha256')
        #: and create a summary from that
        #: offer HTML & JSON downloads
        params = {'type': 'json', 'environmentId': envid}
        if sample.filename.startswith('http'):
            vx = {
                'response': {
                    'analysis_start_time': '1',
                    'environmentId': envid
                },
                'response_code': 0
            }
        else:
            vx = fireeye.api.get('summary/{}'.format(sha256), params=params)
        return ApiResponse(vx)
    else:
        state['response']['environmentId'] = envid
        return ApiResponse(state)


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
    fe_token = session.get('FE_API_TOKEN', None)
    statuses = []

    for env in request.json['dyn_analysis']['fireeye']:
        for f in request.json['files']:
            resp = _submit_to_fireeye(f['sha256'],
                                      env,
                                      fe_token,
                                      with_children=True)
            statuses.append(resp[0]['ID'])
    return ApiResponse({
        'statuses': statuses,
        'message': 'Your files have been submitted for dynamic analysis'
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
    raise ApiException({}, 501)
    statuses = []
    samples = {}
    for env in request.json['dyn_analysis']['fireeye']:
        for url in request.json['urls']:
            sdata = {
                'environmentId': env,
                'analyzeurl': url
            }
            headers = {
                'User-Agent': 'FireEye Sandbox API Client',
                'Accept': 'application/json'
            }
            resp = fireeye.submiturl(sdata, headers=headers)

            samples[resp['response']['sha256']] = url
            statuses.append(resp['response'])
            if resp['response_code'] != 0:
                current_app.log.debug(resp)

    for sha256, url in samples.items():
        surl = Sample(filename=url, sha256=sha256, user_id=g.user.id,
                      md5='N/A', sha1='N/A', sha512='N/A', ctph='N/A')
        db.session.add(surl)
    db.session.commit()
    return {
        'statuses': statuses,
        'message': 'Your URLs have been submitted for dynamic analysis'
    }, 202


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
    headers = {
        'X-FeApi-Token': session.get('FE_API_TOKEN', None)
    }
    req = fireeye.api.get('/config', headers=headers)
    e = etree.fromstring(req)
    envs = []
    for profile in e.xpath('//sensors/sensor/profiles/profile'):
        envs.append({'id': profile.get('id'), 'name': profile.get('name')})

    return ApiResponse({'environments': sorted(envs, key=lambda i: i['id'])})


def _submit_to_fireeye(sha256, env, token, with_children=False):
    """Submit ``sha256`` to FireEye Sandbox for analysis.

    :param sha256:
    :param env:
    :param token: FireEye Auth Token
    :param with_children:
    :return:
    """
    cfg = current_app.config
    fileobj = open(os.path.join(cfg['APP_UPLOADS_SAMPLES'], sha256), 'rb')
    files = {'file': fileobj}
    if with_children:
        s = Sample.query. \
            filter_by(sha256=sha256, user_id=g.user.id). \
            first_or_404()
        try:
            for child in s.children:
                cf = open(
                    os.path.join(cfg['APP_UPLOADS_SAMPLES'], child.sha256),
                    'rb')
                files[child.sha256] = cf
        except IOError as ioerr:
            current_app.log.error(ioerr)
        except AttributeError as ae:
            current_app.log.info(ae)

    data = {
        # ID fo the application to se used for analysis
        # get the list from '/config'
        "application": 0,
        "force": 0,  # 0 - don't analyze duplicates, 1 - force analysis
        "priority": 0,  # 0 - normal, 1 - urgent
        "analysistype": 1,  # 1 - Live, 2 - Sandbox
        "prefetch": 0,  # for analysistype == 2 prefetch must be 1
        "profiles": [env],  # VM to be used for analysis
        "timeout": "200"  # analysis timeout (seconds)
    }
    headers = {
        'Accept': 'application/json',
        'X-FeApi-Token': token
    }
    return fireeye.submit(
        data=data, files=files,
        verify=False,
        headers=headers)
