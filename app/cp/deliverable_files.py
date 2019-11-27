import os

from flask import current_app, send_file
from flask_login import current_user

from app.api.deliverable_files import create_get_files_query
from app.core import ApiPagedResponse
from app.models import DeliverableFile, Permission
from . import cp


@cp.route('/files', methods=['GET'])
def get_files():
    """Return a paginated list of available files

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/files?page=1 HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        Link: <.../api/1.0/files?page=1&per_page=20>; rel="First",
              <.../api/1.0/files?page=2&per_page=20>; rel="Next"
              <.../api/1.0/files?page=2&per_page=20>; rel="Last"

        {
          "count": 58,
          "files": [
            {
              "deliverable": {
                "id": 3,
                "name": "CIMBL"
              },
              "id": 66,
              "name": "test.gz"
            },
            {
              "deliverable": {
                "id": 3,
                "name": "CIMBL"
              },
              "id": 65,
              "name": "test.gz"
            }
          ],
          "page": 1
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader Link: Describe relationship with other resources

    :>json array files: Files
    :>jsonarr integer id: File unique ID
    :>jsonarr string name: File name
    :>json object deliverable: Deliverable type
    :>jsonobj string id: Deliverable unique ID
    :>jsonobj string name: Deliverable name
    :>json integer page: Current page number
    :>json integer count: Total number of items

    :status 200: File found
    :status 404: Resource not found
    """
    deliverable_files = create_get_files_query()

    if not current_user.can(Permission.SLAACTIONS):
        deliverable_files = deliverable_files.filter(DeliverableFile.is_sla == 0)

    return ApiPagedResponse(deliverable_files)


@cp.route('/files/<int:file_id>', methods=['GET'])
@cp.route('/files/<string:file_id>', methods=['GET'])
def get_file(file_id):
    """Download file

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/files/67 HTTP/1.1
        Host: cp.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json
        Content-Disposition: attachment; filename=CIMBL-244-EU.zip
        Content-Length: 55277
        Content-Type: application/zip


    :param file_id: filename or unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :status 200: File found
    :status 404: Resource not found
    """
    if isinstance(file_id, str):
        cond = (DeliverableFile.name == file_id)
    else:
        cond = (DeliverableFile.id == file_id)

    if current_user.can(Permission.SLAACTIONS):
        deliverable_query = DeliverableFile.query.\
            filter(cond)
    else:
        deliverable_query = DeliverableFile.query.\
            filter(cond).filter_by(is_sla=0)
    dfile = deliverable_query.first_or_404()
    cfg = current_app.config
    return send_file(os.path.join(cfg['APP_UPLOADS'], dfile.name),
                     attachment_filename=dfile.name, as_attachment=True)
