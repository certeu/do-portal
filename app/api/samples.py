"""
    Samples endpoint module
    ~~~~~~~~~~~~~~~~~~~~~~~

"""
from sqlalchemy import or_
import os
from flask import request, current_app, g, send_file
from app.core import ApiResponse, ApiPagedResponse
from app import db
from app.models import Sample
from app.tasks import analysis
from app.utils import get_hashes
from . import api


@api.route('/samples', methods=['GET'])
def get_samples():
    """Return a paginated list of samples

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/samples?page=1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        DO-Page-Next: None
        DO-Page-Prev: None
        DO-Page-Current: 1
        DO-Page-Item-Count: 2

        {
          "count": 2,
          "files": [
            {
              "created": "2016-03-21T16:09:47",
              "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwkTY40GfAHw7qzLl6EKvwk...",
              "filename": "stux.zip",
              "id": 2,
              "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc4..."
            },
            {
              "created": "2016-03-20T16:58:09",
              "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwkTY40GfAHw7qzLl6EKvwk...",
              "filename": "stux.zip",
              "id": 1,
              "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc45..."
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

    :>json array items: Array of samples
    :>jsonarr integer id: Sample unique ID
    :>jsonarr string created: Time of upload
    :>jsonarr string sha256: SHA256 of file
    :>jsonarr string ctph: CTPH (a.k.a. fuzzy hash) of file
    :>jsonarr string filename: Filename (as provided by the client)
    :>json integer page: Current page number
    :>json integer prev: Previous page number
    :>json integer next: Next page number
    :>json integer count: Total number of items

    :status 200: Files found
    :status 404: Resource not found
    """
    return ApiPagedResponse(Sample.query)


@api.route('/samples/<string:digest>', methods=['GET'])
def get_sample(digest):
    """Return samples identified by its digest.
    The digest can be: `md5`, `sha1`, `sha256`.

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/samples/1eedab2b09a4bf6c87b273305c096fa2f597ff HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "created": "2016-03-21T16:09:47",
          "ctph": "49152:77qzLl6EKvwkdB7qzLl6EKvwkTY40GfAHw7qzLl6EKvwk...",
          "filename": "stux.zip",
          "id": 2,
          "sha256": "1eedab2b09a4bf6c87b273305c096fa2f597ff9e4bdd39bc4594d8..."
        }

    :param digest: MD5, SHA1 or SHA256 of file

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>jsonarr integer id: Sample unique ID
    :>jsonarr string created: Time of upload
    :>jsonarr string md5: MD5 of file
    :>jsonarr string sha1: SHA1 of file
    :>jsonarr string sha256: SHA256 of file
    :>jsonarr string ctph: CTPH (a.k.a. fuzzy hash) of file
    :>jsonarr string filename: Filename (as provided by the client)

    :status 200: Returns sample details object
    :status 404: Resource not found
    """
    _cond = or_(Sample.md5 == digest, Sample.sha1 == digest,
                Sample.sha256 == digest)
    i = Sample.query.filter(_cond).first_or_404()
    return ApiResponse(i.serialize())


@api.route('/samples/<string:digest>/contents', methods=['GET'])
def download_sample(digest):
    _cond = or_(Sample.md5 == digest, Sample.sha1 == digest,
                Sample.sha256 == digest)
    i = Sample.query.filter(_cond).first_or_404()
    cfg = current_app.config
    return send_file(
        os.path.join(cfg['APP_UPLOADS_SAMPLES'], i.sha256),
        attachment_filename=i.sha256,
        as_attachment=True)


@api.route('/samples', methods=['POST', 'PUT'])
def add_sample():
    """Upload untrusted files, E.i. malware samples, files for analysis.

    Uploaded files are save in :attr:`config.Config.APP_UPLOADS_SAMPLES` using
    the SHA-256 of the content as file name. Existing files are not
    overwritten. After upload MD5, SHA1, SHA256, SHA512 and CTPH hashes
    are calculated.

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/samples HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Length: 317825
        Content-Type: multipart/form-data; boundary=-----------3fa8efc8eb2a42e7
        Content-Disposition: form-data; name="files[0]"; filename="zepto.exe"

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "files": [
            {
              "created": "2016-08-02T14:26:15",
              "ctph": "6144:dOWrXkMZWMKsLXiyLgDf1tedfmqmqeGGAV//CNGa1FPi:d3rV",
              "filename": "zepto.exe",
              "id": 32,
              "md5": "a8188e964bc1f9cb1e905ce8f309e086",
              "sha1": "c3db12e0ffc4b4b090e32679c95aaa76e07150f7",
              "sha256": "7768d4e54b066a567bed1456077025ba7eb56a88aed1bc8cb207",
              "sha512": "1fa1ea4a72be8adc9257185a9d71d889fbea2360cee3f6102302e"
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
    for idx, file in request.files.items():
        buf = file.stream.read()
        digests = get_hashes(buf)

        hash_path = os.path.join(current_app.config['APP_UPLOADS_SAMPLES'],
                                 digests.sha256)
        if not os.path.isfile(hash_path):
            file.stream.seek(0)
            file.save(hash_path)

        s = Sample(
            user_id=g.user.id,
            filename=file.filename,
            md5=digests.md5,
            sha1=digests.sha1,
            sha256=digests.sha256,
            sha512=digests.sha512,
            ctph=digests.ctph)
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
