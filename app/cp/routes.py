import os
from flask import request, current_app, g
from app import db
from app.core import ApiResponse, ApiPagedResponse
from app.models import Sample, Permission
from app.api.decorators import permission_required
from app.tasks import analysis
from app.utils import get_hashes
from . import cp


@cp.route('/samples', methods=['GET'])
def get_samples():
    """Return a paginated list of samples

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/samples?page=1 HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        Link: <.../api/1.0/samples?page=1&per_page=20>; rel="First",
              <.../api/1.0/samples?page=0&per_page=20>; rel="Last"

        {
          "count": 2,
          "items": [
            {
              "created": "2016-03-21T16:09:47",
              "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwkTY40GfAHw7qzLl6EKv...",
              "filename": "stux.zip",
              "id": 2,
              "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc..."
            },
            {
              "created": "2016-03-20T16:58:09",
              "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwkTY40GfAHw7qzLl6EKv...",
              "filename": "stux.zip",
              "id": 1,
              "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc45..."
            }
          ],
          "page": 1
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader Link: Describe relationship with other resources

    :>json array items: Samples list
    :>jsonarr integer id: Sample unique ID
    :>jsonarr string created: Time of upload
    :>jsonarr string sha256: SHA256 of file
    :>jsonarr string ctph: CTPH (a.k.a. fuzzy hash) of file
    :>jsonarr string filename: Filename (as provided by the client)
    :>json integer page: Current page number
    :>json integer count: Total number of items

    :status 200: Files found
    :status 404: Resource not found
    """
    return ApiPagedResponse(Sample.query.filter_by(user_id=g.user.id))


@cp.route('/samples/<string:sha256>', methods=['GET'])
def get_sample(sha256):
    """Return samples identified by `sha256`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/samples/1eedab2b09a4bf6c87b273305c096fa2f597f... HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "created": "2016-03-21T16:09:47",
          "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwk:azp6EwdMzp6EwTVfKVzp6Ew...",
          "filename": "stux.zip",
          "id": 2,
          "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc4594d..."
        }

    :param sha256: SHA-256 of file

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>jsonarr integer id: Sample unique ID
    :>jsonarr string created: Time of upload
    :>jsonarr string sha256: SHA256 of file
    :>jsonarr string ctph: CTPH (a.k.a. fuzzy hash) of file
    :>jsonarr string filename: Filename (as provided by the client)

    :status 200: Returns sample details object
    :status 404: Resource not found
    """
    i = Sample.query.filter_by(sha256=sha256, user_id=g.user.id).first_or_404()
    return ApiResponse(i)


@cp.route('/samples', methods=['POST', 'PUT'])
@permission_required(Permission.SUBMITSAMPLE)
def add_cp_sample():
    """Upload untrusted files, E.i. malware samples, files for analysis.

    After upload MD5, SHA1, SHA256, SHA512 and CTPH hashes are calculated.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/samples HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json
        Content-Type: multipart/form-data; boundary=----FormBoundaryrflTTZA0oE

        ------FormBoundaryrflTTZA0oE
        Content-Disposition: form-data; name="files[0]"; filename="stux.zip"
        Content-Type: application/zip


        ------FormBoundaryrflTTZA0oE--

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "files": [
            {
              "created": "2016-03-21T16:09:47",
              "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwkTY40GfAHw7qzLl6EKvwk...",
              "filename": "stux.zip",
              "id": 2,
              "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc4..."
            }
          ],
          "message": "Files uploaded"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :reqheader Content-Type: multipart/form-data required
    :resheader Content-Type: this depends on `Accept` header or request

    :form files: Files to be uploaded
    :>json array files: List of files saved to disk
    :>jsonarr integer id: Sample unique ID
    :>jsonarr string created: Time of upload
    :>jsonarr string sha256: SHA256 of file
    :>jsonarr string ctph: CTPH (a.k.a. fuzzy hash) of file
    :>jsonarr string filename: Filename (as provided by the client)
    :>json string message: Status message

    :statuscode 201: Files successfully saved
    """
    uploaded_samples = []
    for idx, file_ in request.files.items():
        buf = file_.stream.read()
        hashes = get_hashes(buf)

        hash_path = os.path.join(current_app.config['APP_UPLOADS_SAMPLES'],
                                 hashes.sha256)

        if not os.path.isfile(hash_path):
            file_.stream.seek(0)
            file_.save(hash_path)

        s = Sample(
            user_id=g.user.id,
            filename=file_.filename,
            md5=hashes.md5,
            sha1=hashes.sha1,
            sha256=hashes.sha256,
            sha512=hashes.sha512,
            ctph=hashes.ctph)
        db.session.add(s)
        try:
            db.session.commit()
            analysis.preprocess(s)
        except Exception as e:
            db.session.rollback()
            db.session.flush()
            current_app.log.error(e.args[0])

        uploaded_samples.append(s.serialize())
    return ApiResponse({
        'message': 'Files uploaded',
        'files': uploaded_samples
    }, 201)
