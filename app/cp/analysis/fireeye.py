"""
    CP FireEye Dynamic analysis endpoint
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
from lxml import etree
from flask import session
from flask_jsonschema import validate
from app.core import ApiResponse, ApiException
from app import fireeye
from app.cp import cp


@cp.route('/analysis/fireeye', methods=['GET'])
def get_fireeye_analyses():
    raise ApiException({}, 501)


@cp.route('/analysis/fireeye/report', defaults={'type': 'html'})
@cp.route('/analysis/fireeye/report/<string:sha256>/<envid>/<type>',
          methods=['GET'])
def get_fireeye_report(sha256, envid, type):
    raise ApiException({}, 501)


@cp.route('/analysis/fireeye/download', defaults={'ftype': 'bin', 'eid': 1})
@cp.route('/analysis/fireeye/download/<string:sha256>/<eid>/<ftype>',
          methods=['GET'])
def get_fireeye_download(sha256, eid, ftype):
    raise ApiException({}, 501)


@cp.route('/analysis/fireeye/<string:sha256>/<envid>', methods=['GET'])
def get_fireeye_analysis(sha256, envid):
    raise ApiException({}, 501)


@cp.route('/analysis/fireeye', methods=['POST', 'PUT'])
def add_fireeye_analysis():
    raise ApiException({}, 501)


@cp.route('/analysis/fireeye-url', methods=['POST', 'PUT'])
@validate('analysis', 'add_fireeye_url_analysis')
def add_fireeye_url_analysis():
    raise ApiException({}, 501)


@cp.route('/analysis/fireeye/environments')
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
    headers = {
        'X-FeApi-Token': session.get('FE_API_TOKEN', None)
    }
    req = fireeye.api.get('/config', headers=headers)
    e = etree.fromstring(req)
    envs = []
    for profile in e.xpath('//sensors/sensor/profiles/profile'):
        envs.append({'id': profile.get('id'), 'name': profile.get('name')})

    return ApiResponse({'environments': sorted(envs, key=lambda i: i['id'])})
