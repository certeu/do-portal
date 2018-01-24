"""
    CP VxStream Dynamic analysis endpoint
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


"""
import gzip
from io import BytesIO
from flask import request, current_app, g, send_file
from flask_jsonschema import validate
from app.core import ApiResponse
from app import vxstream, db
from app.models import Permission, Sample
from app.api.decorators import permission_required
from app.api.analysis.vxstream import _state_to_name, SUCCESS
from app.api.analysis.vxstream import _submit_to_vxstream
from app.cp import cp


@cp.route('/analysis/vxstream', methods=['POST', 'PUT'])
@permission_required(Permission.SUBMITSAMPLE)
def add_cp_vxstream_analysis():
    """Submit samples to the VxStream Sandbox

    This endpoint should be called only after files have been uploaded via
    :http:post:`/cp/1.0/samples`. Also accepts :http:method:`put`.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/dynamic-analysis HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "files": [
            {
              "sha256": "9cf31818452fd16847171022d3d13713504db85733c265..."
            }
          ],
          "dyn_analysis": {
            "vxstream": [5, 6]
          }
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Your files have been submitted for dynamic analysis",
          "statuses": [
            {
              "error": "Failed to submit file: analysis already exists for ..."
            },
            {
              "sha256": "33a53e3b28ee41c29afe79f49ecc53b34ac125e5e15f9e7cf1..."
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json array files: List of files to scan. Files must be uploaded using
        :http:post:`/cp/1.0/samples`
    :<jsonarr string sha256: SHA256 of file
    :<json object dyn_analysis: Sandbox configuration
    :<jsonarr array vxstream: List of VxStream environments to submit to.
        Get the list from :http:get:`/cp/1.0/dynamic-analysis/environments`.
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


@cp.route('/analysis/vxstream/environments')
def get_cp_vxstream_environments():
    """Returns a list of available VxStream Sandbox environments

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/vxstream/environments HTTP/1.1
        Host: cp.cert.europa.eu
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

    :status 200: Files submitted for dynamic analysis
    :status 400: Bad request
    """
    st = vxstream.state()
    envs = []
    for id, env in st['response']['environmentList'].items():
        envs.append({'id': int(id), 'name': env})
    return ApiResponse({'environments': sorted(envs, key=lambda i: i['id'])})


@cp.route('/analysis/vxstream/<string:sha256>/<envid>', methods=['GET'])
def get_cp_vxstream_analysis(sha256, envid):
    """Return VxStream Sandbox dynamic analysis for sample identified by
        ``sha256``, running in ``envid``.

    ..  note::

        VxStream Sandbox REST API returns mixed responses.
        Most errors will return :http:statuscode:`200`.
        When possible CP will try to "transform" the :http:statuscode:`200`
        into :http:statuscode:`400` or :http:statuscode:`500`.

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/analysis/vxstream/54abd4674f61029d9ae3f8f8f5.../1 HTTP/1.1
        Host: cp.cert.europa.eu
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
            "sha256": "54abd4674f61029d9ae3f8f8f5a484d396d10b87c9dc77765d8...",
            "size": 336384,
            "submitname": "54abd4674f61029d9ae3f8f8f5a484d396d10b87c9dc777...",
            "targeturl": "",
            "threatlevel": 1,
            "threatscore": 41,
            "type": "PE32 executable (GUI) Intel 80386 Mono/.Net assembly..."
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
        :http:get:`/cp/1.0/analysis/vxstream/environments`.

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
    Sample.query.filter_by(sha256=sha256, user_id=g.user.id).first_or_404()
    state = vxstream.api.get(
        'state/{}'.format(sha256), params={
            'environmentId': envid
        })
    status = state['response_code'] == 0
    if status and state['response']['state'] == _state_to_name[SUCCESS]:
        params = {'type': 'json', 'environmentId': envid}
        vx = vxstream.api.get('summary/{}'.format(sha256), params=params)
        return ApiResponse(vx)
    else:
        state['response']['environmentId'] = envid
        return ApiResponse(state)


@cp.route('/analysis/vxstream/report', defaults={'type_': 'html'})
@cp.route(
    '/analysis/vxstream/report/<string:sha256>/<envid>/<type_>',
    methods=['GET'])
def get_cp_vxstream_report(sha256, envid, type_):
    # XML, HTML, BIN and PCAP are GZipped
    Sample.query.filter_by(sha256=sha256, user_id=g.user.id).first_or_404()
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


@cp.route('/analysis/vxstream/download', defaults={'ftype': 'bin', 'eid': 1})
@cp.route(
    '/analysis/vxstream/download/<string:sha256>/<eid>/<ftype>',
    methods=['GET'])
def get_cp_vxstream_download(sha256, eid, ftype):
    Sample.query.filter_by(sha256=sha256, user_id=g.user.id).first_or_404()
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


@cp.route('/analysis/vxstream-url', methods=['POST', 'PUT'])
@validate('analysis', 'add_vxstream_url_analysis')
def add_cp_vxstream_url_analysis():
    """Submit URLs for scanning to VxStream Sandbox.
    Also accepts :http:method:`put`.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/analysis/vxstream-url HTTP/1.1
        Host: cp.cert.europa.eu
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

    :<json array files: List of URLs to scan. Up to 5 URL per request.
    :<jsonarr string sha256: SHA256 of the shortcut file created.
    :<json object dyn_analysis: Sandbox configuration
    :<jsonarr array vxstream: List of VxStream environments to submit to.
        Get the list from :http:get:`/api/1.0/analysis/vxstream/environments`.
    :>json array statuses: List of statuses returned by upstream APIs.
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
