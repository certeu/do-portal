from flask import request, redirect, url_for, g
from flask_jsonschema import validate
from app.core import ApiResponse
from app import db
from app.models import Tag
from . import api


@api.route('/tags', methods=['GET'])
def get_tags():
    """Return available tags

    For tag details see :http:get:`/api/1.0/tags/(int:tag_id)`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/tags HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "tags": [
            {
              "name": "Red",
              "id": 1
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array items: List of available tags
    :>jsonarr integer id: Tag unique ID
    :>jsonarr string name: Tag name

    :status 200: Tag list
    :status 204: No tags available
    :status 404: Not found
    """
    tags = Tag.query.distinct(Tag.name).all()
    if not tags:
        return ApiResponse({}, 204)
    return ApiResponse({'tags': tags})


@api.route('/tags/<int:tag_id>', methods=['GET'])
def get_tag(tag_id):
    """Return tag identified by `tag_id`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/tags/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "name": "Red",
          "id": 1
        }

    :param tag_id: tag unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: Tag unique ID
    :>json string name: Tag name

    :status 200: Returns tag details object
    :status 404: Resource not found
    """
    tag = Tag.query.get_or_404(tag_id)
    return ApiResponse(tag)


@api.route('/tags', methods=['POST', 'PUT'])
@validate('tags', 'add_tag')
def add_tag():
    """Add new tag

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/tags HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "name": "Green"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json
        Location: https://do.cert.europa.eu/api/1.0/tags/2

        {
          "message": "Tag added",
          "tag": {
            "name": "Green",
            "id": 2
          }
        }

    **Example validation error**:

    .. sourcecode:: http

        HTTP/1.0 422 UNPROCESSABLE ENTITY
        Content-Type: application/json

        {
          "message": "'name' is a required property",
          "validator": "required"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request
    :resheader Location: URL of newly created resource

    :<json string name: Tag name

    :>json object tag: New tag object
    :>json string message: Status message

    :status 200: Tag was successfully added
    :status 422: Request could not be processed
    """
    t = Tag.fromdict(request.json)
    t.user_id = g.user.id
    db.session.add(t)
    db.session.commit()
    return ApiResponse({
        'tag': t.serialize(),
        'message': 'Tag added'
    }, 201, {
        'Location': url_for('api.get_tag', tag_id=t.id)
    })


@api.route('/tags/<int:tag_id>', methods=['PUT'])
@validate('tags', 'update_tag')
def update_tag(tag_id):
    """Update tag details

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/tags/2 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "name": "Greener"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Tag saved"
        }

    **Example validation error**:

    .. sourcecode:: http

        HTTP/1.0 422 UNPROCESSABLE ENTITY
        Content-Type: application/json

        {
          "message": "'name' is a required property",
          "validator": "required"
        }

    :param tag_id: Tag unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string name: New tag name

    :>json string message: Status message

    :status 200: Tag was successfully saved
    :status 422: Request could not be processed
    """
    t = Tag.get(tag_id)
    if not t:
        return redirect(url_for('api.add_tag'))
    t.from_json(request.json)
    db.session.add(t)
    db.session.commit()
    return ApiResponse({'message': 'Tag saved'})


@api.route('/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """Delete tag

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/tags/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Tag deleted"
        }

    :param tag_id: Tag unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Status message

    :status 200: Tag was deleted
    :status 400: Bad request
    """
    t = Tag.query.get_or_404(tag_id)

    t.deleted = 1
    db.session.add(t)
    db.session.commit()
    return ApiResponse({'message': 'Tag deleted'})
