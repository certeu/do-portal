from flask import url_for
from .conftest import assert_msg


def test_start_static_analysis(client):
    rv = client.post(
        url_for('api.add_analysis'),
        json=dict(files=[{
            'sha256': '1eedab2b09a4bf6c'
        }]))
    assert_msg(
        rv,
        value='Your files have been submitted for static analysis',
        response_code=202)


def test_get_static_analysis(client):
    rv = client.get(
        url_for('api.get_analysis', sha256='1eedab2b09a4bf6c87b273305c09'))
    assert rv.status_code == 404


def test_get_static_analyses(client):
    rv = client.get(url_for('api.get_analyses'))
    assert_msg(rv, key='items')
