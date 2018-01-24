from flask import url_for
from .conftest import assert_msg


def test_create_group(client):
    rv = client.post(
        url_for('api.add_group'),
        json=dict(name='Test Group', color='#ffffff'))
    assert_msg(rv, value='Group added', response_code=201)


def test_update_group(client):
    rv = client.put(
        url_for('api.update_group', group_id=1),
        json=dict(name='Test Group updated', color='#ffff00'))
    assert rv.status_code == 200


def test_read_group(client):
    rv = client.get(url_for('api.get_groups'))
    assert_msg(rv, key='organization_groups')

    rv = client.get(url_for('api.get_group', group_id=1))
    assert_msg(rv, key='name')


def test_delete_group(client):
    rv = client.delete(url_for('api.delete_group', group_id=1))
    assert_msg(rv, value='Group deleted')

    rv = client.delete(url_for('api.delete_group', group_id=666))
    assert rv.status_code == 404
