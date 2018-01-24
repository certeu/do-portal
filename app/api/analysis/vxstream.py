"""
    VxStream Dynamic analysis endpoint
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import os
from io import BytesIO
import gzip
from flask import request, current_app, g, send_file
from flask_jsonschema import validate
from app.core import ApiResponse, ApiPagedResponse, ApiException
from app import vxstream, db
from app.api import api
from app.models import Report, Sample

IN_QUEUE = 40
IN_PROGRESS = 30
SUCCESS = 20
ERROR = 10
UNKNOWN = 0

_state_to_name = {
    IN_QUEUE: 'IN_QUEUE',
    IN_PROGRESS: 'IN_PROGRESS',
    SUCCESS: 'SUCCESS',
    ERROR: 'ERROR',
    UNKNOWN: 'UNKNOWN',
}

_name_to_state = {
    'IN_QUEUE': IN_QUEUE,
    'IN_PROGRESS': IN_PROGRESS,
    'SUCCESS': SUCCESS,
    'ERROR': ERROR,
    'UNKNOWN': UNKNOWN
}


@api.route('/analysis/vxstream', methods=['GET'])
def get_vxstream_analyses():
    """Return a paginated list of VxStream Sandbox JSON reports.

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/vxstream?page=1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        Link: <.../api/1.0/analysis/vxstream?page=1&per_page=20>; rel="First",
              <.../api/1.0/analysis/vxstream?page=0&per_page=20>; rel="Last"

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
          "page": 1
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader Link: Describe relationship with other resources

    :>json array items: VxStream reports
    :>jsonarr integer id: AV scan unique ID
    :>jsonarr string name: File name
    :>jsonarr string sha256: SHA256 message-digest of file
    :>json integer page: Current page number
    :>json integer count: Total number of items

    :status 200: Reports found
    :status 404: Resource not found
    """
    return ApiPagedResponse(Report.query.filter_by(type_id=3))


@api.route('/analysis/vxstream/report', defaults={'type_': 'html'})
@api.route(
    '/analysis/vxstream/report/<string:sha256>/<envid>/<type_>',
    methods=['GET'])
def get_vxstream_report(sha256, envid, type_):
    # XML, HTML, BIN and PCAP are GZipped
    Sample.query.filter_by(sha256=sha256).first_or_404()
    headers = {
        'Accept': 'text/html',
        'User-Agent': 'VxStream Sandbox API Client'
    }
    params = {'type': type_, 'environmentId': envid}
    vx = vxstream.api.get(
        'result/{}'.format(sha256), params=params, headers=headers)
    if type_ in ['xml', 'html', 'bin', 'pcap']:
        return gzip.decompress(vx)
    return vx


@api.route('/analysis/vxstream/download', defaults={'ftype': 'bin', 'eid': 1})
@api.route(
    '/analysis/vxstream/download/<string:sha256>/<eid>/<ftype>',
    methods=['GET'])
def get_vxstream_download(sha256, eid, ftype):
    Sample.query.filter_by(sha256=sha256).first_or_404()
    headers = {
        'Accept': 'text/html',
        'User-Agent': 'VxStream Sandbox API Client'
    }
    params = {'type': ftype, 'environmentId': eid}
    vx = vxstream.api.get(
        'result/{}'.format(sha256), params=params, headers=headers)
    if ftype in ['xml', 'html', 'bin', 'pcap']:
        ftype += '.gz'
    return send_file(
        BytesIO(vx),
        attachment_filename='{}.{}'.format(sha256, ftype),
        as_attachment=True)


@api.route('/analysis/vxstream/<string:sha256>/<envid>', methods=['GET'])
def get_vxstream_analysis(sha256, envid):
    """Return VxStream Sandbox dynamic analysis for sample identified by
        :attr:`~app.models.Sample.sha256`, running in :param: envid.

    ..  note::

        VxStream Sandbox REST API returns mixed responses.
        Most errors will return :http:statuscode:`200`.

    **Example request**:

    .. sourcecode:: http

        GET api/1.0/analysis/vxstream/54abd4674f61029d9ae3f8f805b9b7/1 HTTP/1.1
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
        :http:get:`/api/1.0/analysis/vxstream/environments`.

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
    sample = Sample.query.filter_by(sha256=sha256).first_or_404()
    state = vxstream.api.get(
        'state/{}'.format(sha256), params={
            'environmentId': envid
        })
    status = state['response_code'] == 0
    if status and state['response']['state'] == _state_to_name[SUCCESS]:
        #: FIXME: return the vxstream.api.get('result/sha256')
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
            vx = vxstream.api.get('summary/{}'.format(sha256), params=params)
        return ApiResponse(vx)
    else:
        state['response']['environmentId'] = envid
        return ApiResponse(state)


@api.route('/analysis/vxstream', methods=['POST', 'PUT'])
def add_vxstream_analysis():
    """Submit sample to the VxStream Sandbox. Also accepts :http:method:`put`.

    This endpoint should be called only after files have been uploaded via
    :http:post:`/api/1.0/samples`

    Files should be available under :attr:`config.Config.APP_UPLOADS_SAMPLES`.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/analysis/vxstream HTTP/1.1
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
            "vxstream": [5, 6]
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
    :<jsonarr array vxstream: List of VxStream environments to submit to.
        Get the list from :http:get:`/api/1.0/analysis/vxstream/environments`.
    :>json array statuses: List of statuses returned by upstream APIs.
    :>jsonarr string error: Error message from upstream API
    :>jsonarr string sha256: SHA256 calculated by upstream API
    :>json string message: Status message

    :status 202: Files have been accepted for dynamic analysis
    :status 400: Bad request
    """
    statuses = []
    for env in request.json['dyn_analysis']['vxstream']:
        for f in request.json['files']:
            resp = _submit_to_vxstream(f['sha256'], env, with_children=True)
            statuses.append(resp['response'])
            if resp['response_code'] != 0:
                current_app.log.debug(resp)
    return ApiResponse(
        {
            'statuses': statuses,
            'message': 'Your files have been submitted for dynamic analysis'
        }, 202)


@api.route('/analysis/vxstream-url', methods=['POST', 'PUT'])
@validate('analysis', 'add_vxstream_url_analysis')
def add_vxstream_url_analysis():
    """Submit URLs to the VxStream Sandbox. Also accepts :http:method:`put`.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/analysis/vxstream-url HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "urls": ["http://cert.europa.eu"],
          "dyn_analysis": {
            "vxstream": [5, 6]
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
    :<jsonarr array vxstream: List of VxStream environments to submit to
        Get the list from :http:get:`/api/1.0/analysis/vxstream/environments`
    :>json array statuses: List of statuses returned by upstream APIs
    :>jsonarr string error: Error message from upstream API
    :>jsonarr string sha256: SHA256 calculated by upstream API
    :>json string message: Status message

    :status 202: The URLs have been accepted for scanning
    :status 400: Bad request
    """
    statuses = []
    samples = {}
    for env in request.json['dyn_analysis']['vxstream']:
        for url in request.json['urls']:
            if not url.startswith('http'):
                url = 'http://' + url
            sdata = {'environmentId': env, 'analyzeurl': url}
            headers = {
                'User-Agent': 'VxStream Sandbox API Client',
                'Accept': 'application/json'
            }
            resp = vxstream.submiturl(sdata, headers=headers)

            if resp['response_code'] == -1:
                raise ApiException(resp['response']['error'])

            samples[resp['response']['sha256']] = url
            statuses.append(resp['response'])
            if resp['response_code'] != 0:
                current_app.log.debug(resp)

    for sha256, url in samples.items():
        surl = Sample(
            filename=url,
            sha256=sha256,
            user_id=g.user.id,
            md5='N/A',
            sha1='N/A',
            sha512='N/A',
            ctph='N/A')
        db.session.add(surl)
    db.session.commit()
    return ApiResponse(
        {
            'statuses': statuses,
            'message': 'Your URLs have been submitted for dynamic analysis'
        }, 202)


@api.route('/analysis/vxstream/environments')
def get_vxstream_environments():
    """Returns a list of available VxStream Sandbox environments

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/vxstream/environments HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "environments": [
            {
              "id": 6,
              "name": "Windows 7 64 bit (KERNELMODE)"
            },
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
            },
            {
              "id": 5,
              "name": "Windows 7 32 bit (KERNELMODE)"
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
    st = vxstream.state()
    envs = []
    for eid, env in st['response']['environmentList'].items():
        envs.append({'id': int(eid), 'name': env})
    return ApiResponse({'environments': sorted(envs, key=lambda i: i['id'])})


def _submit_to_vxstream(sha256, env, with_children=False):
    """Submit ``sha256`` to VxStream Sandbo for analysis.

    :param sha256:
    :param env:
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
        'apikey': cfg['REST_CLIENT_VX_API_KEY'],
        'secret': cfg['REST_CLIENT_VX_API_SECRET'],
        'environmentId': env
    }
    # VxStream API returns 200 status code on errors :(
    # we have to parse their own version of error messages
    headers = {
        'User-Agent': 'VxStream Sandbox API Client',
        'Accept': 'application/json'
    }
    return vxstream.submit(
        data=data, files=files, use_params=False, headers=headers)
