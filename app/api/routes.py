"""
    API routes
    ~~~~~~~~~~

    Routes from this file are included first.
    Routes that can't be grouped under an endpoint go here

"""
import os
from app import gpg
from app.core import ApiResponse, ApiException
from app.tasks import send_to_ks
from flask import current_app, request
from flask_jsonschema import validate
from werkzeug.utils import secure_filename
from . import api

HTTP_METHODS = [
    # RFC 2616
    'OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE', 'CONNECT',
    # RFC 2518
    'PROPFIND', 'PROPPATCH', 'MKCOL', 'COPY', 'MOVE', 'LOCK', 'UNLOCK',
    # RFC 3253
    'VERSION-CONTROL', 'REPORT', 'CHECKOUT', 'CHECKIN', 'UNCHECKOUT',
    'MKWORKSPACE', 'UPDATE', 'LABEL', 'MERGE', 'BASELINE-CONTROL',
    'MKACTIVITY'
    # RFC 3648
    'ORDERPATCH',
    # RFC 3744
    'ACL',
    # RFC 5789
    'PATCH'
]


@api.route('/')
def api_index():
    """List available endpoints
    """
    url_rules = [r.rule for r in current_app.url_map.iter_rules()]
    return ApiResponse({'endpoints': sorted(list(set(url_rules)))})


@api.route('/teapot')
def teapot():
    return ApiResponse({'message': "I'm a teapot"}, 418)


@api.route('/users', methods=HTTP_METHODS)
def api_honeytoken():
    # Honeytoken endpoint
    return ApiResponse({'message': "No such user"}, 200)


@api.route('/submit-key', methods=['POST', 'PUT'])
@validate('gnupg', 'submit_key')
def submit_gpg_key():
    """Submit GPG key to CERT-EU keyserver
    Keys are send to the first server from the GPG_KEYSERVERS configuration
    option

    **Example request**:

    .. sourcecode:: http

        POST /submit-key HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "ascii_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----nmQENBFHn
          ...-----END PGP PUBLIC KEY BLOCK-----"

        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "fingerprints": [
            "2D39D3A9ACCD18B1D7774A00A485C88DDA2AA2BF"
          ],
          "message": "Key saved"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string ascii_key: ASCII armored GPG public key
    :>json array fingerprints: List of fingerprints
    :>json string message: Status message

    :statuscode 201: GPG key successfully saved
    :statuscode 400: Bad request
    """
    result = gpg.gnupg.import_keys(request.json['ascii_key'])
    if result.fingerprints:
        send_to_ks.delay(
            current_app.config['GPG_KEYSERVERS'][0], result.fingerprints
        )
        return ApiResponse({
            'message': 'Key saved',
            'fingerprints': [f for f in result.fingerprints]},
            201)
    else:
        raise ApiException('The PGP Key could not be imported')


@api.route('/upload', methods=['POST'])
def upload():
    """Upload files. This endpoint is used to upload "trusted" files;
    E.i. files created by CERT-EU

    E.g. CITAR, CIMBL, IDS signatures, etc.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/upload HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryklDA9

        ------WebKitFormBoundaryklDA94BtcALil3R2
        Content-Disposition: form-data; name="files[0]"; filename="test.gz"
        Content-Type: application/x-gzip


        ------WebKitFormBoundaryklDA94BtcALil3R2--

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "files": [
            "test.gz"
          ],
          "message": "Files uploaded"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :reqheader Content-Type: multipart/form-data required
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array files: List of files saved to disk
    :>json string message: Status message

    :statuscode 201: Files successfully saved
    """
    uploaded_files = []
    for idx, file in request.files.items():
        filename = secure_filename(file.filename)
        file.save(os.path.join(current_app.config['APP_UPLOADS'], filename))
        uploaded_files.append(filename)
    return ApiResponse({
        'message': 'Files uploaded',
        'files': uploaded_files
    }, 201)


@api.route('/search-keys', methods=['POST'])
def search_public_ks(email=None):
    """Search GPG keys on public keyserver pool.
    The keysever pool is the second server from the GPG_KEYSERVERS
    configuration option.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/search-keys HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "email": "alex@cert.europa.eu"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "keys": [
            {
              "algo": "1",
              "date": "1379079830",
              "expires": "1479375689",
              "keyid": "8CC4185CF057F6F8690309DD28432835514AA0F6",
              "length": "4096",
              "type": "pub",
              "uids": [
                "Alexandru Ciobanu <alex@cert.europa.eu>"
              ]
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string email: E-mail address
    :>json array keys: List of found keys
    :>jsonarr string algo: `Key algorithm
      <https://tools.ietf.org/html/rfc4880#section-9.1>`_
    :>jsonarr string date: Creation date
    :>jsonarr string expires: Expiration date
    :>jsonarr string keyid: KeyID date
    :>jsonarr string length: Key size
    :>jsonarr string type: Key type. Only public keys are returned
    :>jsonarr array uids: Key type. Only public keys are returned


    :statuscode 200: GPG keys found
    :statuscode 404: No keys found for given email address

    :param email:
    """
    if email is None:
        email = request.json['email']
    keys = gpg.gnupg.search_keys(
        email, current_app.config['GPG_KEYSERVERS'][1])
    if not keys:
        raise ApiException('No keys found', 404)
    return ApiResponse({'keys': keys})


@api.route('/import-keys', methods=['POST'])
def import_keys():
    """Import GPG keys from public keyserver into local keychain

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/import-keys HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json;charset=UTF-8

        {
          "keys": [
            "8CC4185CF057F6F8690309DD28432835514AA0F6"
          ]
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "message": "Imported"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json array keys: Key IDs to import
    :>json string message: Status message

    :statuscode 201: GPG keys imported
    """
    for key in request.json['keys']:
        gpg.gnupg.recv_keys(current_app.config['GPG_KEYSERVERS'][1], key)
    return ApiResponse({'message': 'Imported'}, 201)
