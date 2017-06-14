from flask import request, redirect, url_for
from flask_jsonschema import validate
from app.core import ApiResponse
from app import db
from app.models import OrganizationGroup
from . import api


@api.route('/organization_groups', methods=['GET'])
@api.route('/organization-groups', methods=['GET'])
def get_groups():
    """Return a list of available groups
    Each organization belongs to one group; E.g. Constituents, National CERTs,
    Partners, etc. For group details see
    :http:get:`/api/1.0/organization_groups/(int:group_id)`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/organization_groups HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "organization_groups": [
            {
              "id": 3,
              "name": "Partners"
            },
            {
              "id": 2,
              "name": "CERTs"
            },
            {
              "id": 1,
              "name": "Constituents"
            }
          ]
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json array organization_groups: List of available organization groups
    :>jsonarr integer id: Group unique ID
    :>jsonarr string name: Group name

    :status 200: Group endpoint found, response may be empty
    :status 404: Not found
    """
    groups = OrganizationGroup.query.filter(
        OrganizationGroup.deleted == 0).all()
    return ApiResponse(
        {'organization_groups': [o.serialize() for o in groups]})


@api.route('/organization_groups/<int:group_id>', methods=['GET'])
@api.route('/organization-groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    """Return group identified by `group_id`

    **Example request**:

    .. sourcecode:: http

        GET /api/1.0/organization_groups/1 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "id": 1,
          "name": "Constituents"
        }

    :param group_id: group unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json integer id: Group unique ID
    :>json string name: Group name

    :status 200: Returns group details object
    :status 404: Resource not found
    """
    g = OrganizationGroup.query.get_or_404(group_id)
    return ApiResponse(g.serialize())


@api.route('/organization_groups', methods=['POST', 'PUT'])
@api.route('/organization-groups', methods=['POST', 'PUT'])
@validate('organization_groups', 'add_group')
def add_group():
    """Add new group

    **Example request**:

    .. sourcecode:: http

        POST /api/1.0/organization_groups HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "active": true,
          "name": "Test"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 201 CREATED
        Content-Type: application/json

        {
          "message": "Group added",
          "organization_group": {
            "id": 4,
            "name": "Test"
          }
        }

    **Example validation error**:

    .. sourcecode:: http

        HTTP/1.0 400 BAD REQUEST
        Content-Type: application/json

        {
          "message": "'name' is a required property",
          "validator": "required"
        }

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string name: Group name
    :<json boolean active: Active
    :>json object organization_group: New group object
    :>json string message: Status message

    :status 200: Group details were successfully added
    :status 400: Bad request
    """
    g = OrganizationGroup().from_json(request.json)
    db.session.add(g)
    db.session.commit()
    return ApiResponse(
        {'organization_group': g.serialize(), 'message': 'Group added'},
        201,
        {'Location': url_for('api.get_group', group_id=g.id)})


@api.route('/organization_groups/<int:group_id>', methods=['PUT'])
@api.route('/organization-groups/<int:group_id>', methods=['PUT'])
@validate('organization_groups', 'update_group')
def update_group(group_id):
    """Update group details

    **Example request**:

    .. sourcecode:: http

        PUT /api/1.0/organization_groups/6 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

        {
          "active": true,
          "name": "Test updated"
        }

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Group saved"
        }

    **Example validation error**:

    .. sourcecode:: http

        HTTP/1.0 400 BAD REQUEST
        Content-Type: application/json

        {
          "message": "'name' is a required property",
          "validator": "required"
        }

    :param group_id: Group unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :<json string name: Group name
    :<json boolean active: Active
    :>json string message: Status message

    :status 200: Group details were successfully updated
    :status 400: Bad request
    """
    g = OrganizationGroup.query.filter(
        OrganizationGroup.id == group_id,
        OrganizationGroup.deleted == 0
    ).first()
    if not g:
        return redirect(url_for('api.add_group'))
    g.from_json(request.json)
    db.session.add(g)
    db.session.commit()
    return ApiResponse({'message': 'Group saved'})


@api.route('/organization_groups/<int:group_id>', methods=['DELETE'])
@api.route('/organization-groups/<int:group_id>', methods=['DELETE'])
def delete_group(group_id):
    """Delete group

    **Example request**:

    .. sourcecode:: http

        DELETE /api/1.0/organization_groups/6 HTTP/1.1
        Host: do.cert.europa.eu
        Accept: application/json
        Content-Type: application/json

    **Example response**:

    .. sourcecode:: http

        HTTP/1.0 200 OK
        Content-Type: application/json

        {
          "message": "Group deleted"
        }

    :param group_id: Group unique ID

    :reqheader Accept: Content type(s) accepted by the client
    :resheader Content-Type: this depends on `Accept` header or request

    :>json string message: Status message

    :status 200: Group was deleted
    :status 400: Bad request
    """
    g = OrganizationGroup.query.filter(
        OrganizationGroup.id == group_id,
        OrganizationGroup.deleted == 0
    ).first_or_404()

    g.deleted = 1
    db.session.add(g)
    db.session.commit()
    return ApiResponse({'message': 'Group deleted'})
