import pytest
from flask import url_for
from .conftest import assert_msg


def test_create_tag(client):
    rv = client.post(url_for('api.add_tag'), json=dict(name='Boobo'))
    assert_msg(rv, value='Tag added', response_code=201)


def test_update_tag(client):
    rv = client.put(
        url_for('api.update_tag', tag_id=1), json=dict(name='Yoggy'))
    assert rv.status_code == 200


def test_read_tag(client):
    rv = client.get(url_for('api.get_tags'))
    assert_msg(rv, key='tags')

    rv = client.get(url_for('api.get_tag', tag_id=1))
    assert_msg(rv, key='name')


@pytest.mark.parametrize('tag_id, status_code', [(1, 200), (666, 404)])
def test_delete_tag(client, tag_id, status_code):
    rv = client.delete(url_for('api.delete_tag', tag_id=tag_id))
    assert rv.status_code == status_code
