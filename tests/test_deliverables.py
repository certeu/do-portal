import pytest
from flask import url_for
from .conftest import assert_msg


def test_create_deliverable(client):
    rv = client.post(
        url_for('api.add_deliverable'),
        json=dict(name='Sample deliverable')
    )
    assert_msg(rv, value='Deliverable added', response_code=201)


def test_update_deliverable(client):
    rv = client.put(
        url_for('api.update_deliverable', deliverable_id=1),
        json=dict(name='Sample deliverable updated')
    )
    assert rv.status_code == 200


def test_read_deliverable(client):
    rv = client.get(url_for('api.get_deliverables'))
    assert_msg(rv, key='deliverables')

    rv = client.get(url_for('api.get_deliverable', deliverable_id=1))
    assert_msg(rv, key='name')


def test_delete_deliverable(client):
    rv = client.delete(url_for('api.delete_deliverable', deliverable_id=1))
    assert_msg(rv, value='Deliverable deleted')

    rv = client.delete(url_for('api.delete_deliverable', deliverable_id=666))
    assert rv.status_code == 404


def test_create_file(client):
    rv = client.post(
        url_for('api.add_file'),
        json=dict(files=['file.ext', 'file2.ext'], deliverable_id=1)
    )
    assert_msg(rv, value='Files added', response_code=201)


def test_read_file(client):
    rv = client.get(url_for('api.get_files'))
    assert_msg(rv, key='items')

    rv = client.get(url_for('api.get_file', file_id=1))
    assert_msg(rv, key='name')


@pytest.mark.parametrize('file_id, status_code', [(1, 200), (666, 404)])
def test_delete_file(client, file_id, status_code):
    rv = client.delete(url_for('api.delete_file', file_id=file_id))
    assert rv.status_code == status_code
