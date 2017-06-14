from io import BytesIO
from flask import url_for
from .conftest import assert_msg


def test_api_routes_list(client):
    rv = client.get(url_for('api.api_index'))
    assert_msg(rv, key='endpoints')


def test_get_samples(client):
    rv = client.get(url_for('api.get_samples'))
    assert_msg(rv, key='items')


def test_get_sample(client):
    rv = client.get(url_for('api.get_sample', digest=1))
    assert rv.status_code == 404


def test_add_sample(client, malware_sample):
    rv = client.post(
        url_for('api.add_sample'),
        data=dict(file=(BytesIO(), malware_sample.filename)),
        content_type='multipart/form-data'
    )
    assert rv.status_code == 201


def test_404(client):
    rv = client.get('/api/1.0/non-existent-resource')
    assert rv.status_code == 404


def test_teapot(client):
    rv = client.get(url_for('api.teapot'))
    assert_msg(rv, value="I'm a teapot", response_code=418)


def test_honeytoken(client):
    rv = client.get(url_for('api.api_honeytoken'))
    assert_msg(rv, value='No such user')
