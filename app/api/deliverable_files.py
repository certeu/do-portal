import os
from flask import request, send_file, current_app
from app.core import ApiResponse, ApiPagedResponse
from . import api
from ..import db
from ..models import Deliverable, DeliverableFile, Permission
from .decorators import permission_required
from flask_jsonschema import validate
from sqlalchemy import or_


def create_get_files_query():
    query = request.args.get('query', None, type=str)

    if query is None:
        deliverable_files = DeliverableFile.query
    else:
        search = "%{}%".format(query)

        filters = [DeliverableFile.name.ilike(search), Deliverable.name.ilike(search)]

        deliverable_files = DeliverableFile.query.join(DeliverableFile.deliverable_)
        deliverable_files = deliverable_files.filter(or_(*filters))

    return deliverable_files


@api.route('/files', methods=['GET'])
def get_files():
    """Return a paginated list of available files

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/files?page=1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        DO-Page-Next: http://do.cert.europa.eu/api/1.0/files?page=1
        DO-Page-Prev: None
        DO-Page-Current: 1
        DO-Page-Item-Count: 8

        {
          "count": 8,
          "first": "http://do.cert.europa.eu/api/1.0/files?per_page=20&page=1",
          "items": [
            {
              "created": "2016-08-08T15:28:28",
              "id": 2,
              "name": "CIMBL-244-EU.zip",
              "type": "CIMBL"
            },
            {
              "created": "2016-08-08T10:36:31",
              "id": 1,
              "name": "CIMBL-244-EU.zip",
              "type": "CIMBL"
            }
          ],
          "last": "http://127.0.0.1:5001/api/1.0/files?per_page=20&page=1",
          "next": null,
          "page": 1,
          "per_page": 20,
          "prev": null
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader DO-Page-Next: Next page URL
    :resheader DO-Page-Prev: Previous page URL
    :resheader DO-Page-Curent: Current page number
    :resheader DO-Page-Item-Count: Total number of items

    :>json array items: Files
    :>jsonarr integer id: File unique ID
    :>jsonarr string name: File name
    :>jsonarr string type: Deliverable type
        For the list of available types see :http:get:`/api/1.0/deliverables`
    :>jsonarr string created: Creation date
    :>json integer page: Current page number
    :>json integer prev: Previous page number
    :>json integer next: Next page number
    :>json integer count: Total number of items

    :status 200: File found
    :status 404: Resource not found
    """
    deliverable_files = create_get_files_query()
    return ApiPagedResponse(deliverable_files)


@api.route('/files/<int:file_id>', methods=['GET'])
def get_file(file_id):
    """Get file from database

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/files/67 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "created": "2016-08-09T12:56:40",
          "id": 8,
          "name": "CIMBL-244-EU.zip",
          "type": "CIMBL"
        }

    :param file_id: file's unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: File unique ID
    :>json string name: File name
    :>json string type: Deliverable type
    :>json string date: Creation date

    :status 200: File found
    :status 404: Resource not found
    """
    g = DeliverableFile.query.get_or_404(file_id)
    return ApiResponse(g.serialize())


@api.route('/files/<int:file_id>/contents', methods=['GET'])
def download_file(file_id):
    """Download file

    **Example request**:

    .. sourcecode:: http

       GET /api/1.0/files/1 HTTP/1.1
       Host: do.cert.europa.eu
       Accept: application/json

    **Example response**:

    .. sourcecode:: http

       HTTP/1.0 200 OK
       Content-Type: application/json
       Content-Disposition: attachment; filename=CIMBL-244-EU.zip
       Content-Length: 55277
       Content-Type: application/zip


    :param file_id: file's unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :status 200: File found
    :status 404: Resource not found
    """
    dfile = DeliverableFile.query.filter_by(id=file_id).first_or_404()
    cfg = current_app.config
    return send_file(os.path.join(cfg['APP_UPLOADS'], dfile.name),
                     attachment_filename=dfile.name, as_attachment=True)


@api.route('/files', methods=['POST', 'PUT'])
@validate('deliverables', 'add_files')
def add_file():
    """Save file names to database.

    This endpoing should be called only after files have been uploaded via
    :http:post:`/api/1.0/upload`

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/files HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "deliverable_id": 2,
          "is_sla": 1,
          "files": [
            "test.gz"
          ]
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "files": [
            "test.gz"
          ],
          "message": "Files added"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string deliverable_id: ID of deliverable.
        For a full list of available IDs see :http:get:`/api/1.0/deliverables`
    :<json integer is_sla: When set file is for SLA constituents only
    :<json array files: List of files to save
    :>json array files: List of saved files
    :>json string message: Status message

    :status 201: GPG key successfully saved
    :status 400: Bad request
    """
    files = request.json.pop('files')
    for f in files:
        dfile = DeliverableFile.fromdict(request.json)
        dfile.name = f
        db.session.add(dfile)
    db.session.commit()
    return ApiResponse({'files': files, 'message': 'Files added'}, 201)


@api.route('/files/<int:file_id>', methods=['DELETE'])
@permission_required(Permission.ADMINISTER)
def delete_file(file_id):
    """Delete file from database
    Files are not currently removed from the filesystem.

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/files/67 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "File deleted"
        }

    :param file_id: file's unique ID.

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: File delete status

    :status 200: File was deleted
    :status 404: File was not found
    """
    g = DeliverableFile.query.filter(
        DeliverableFile.id == file_id
    ).first_or_404()

    g.deleted = 1
    db.session.add(g)
    db.session.commit()
    return ApiResponse({'message': 'File deleted'})
