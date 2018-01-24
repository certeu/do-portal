from flask import url_for
from .conftest import assert_msg


def test_create_ip_range(client):
    rv = client.post(
        url_for('api.add_ip_range'),
        json=dict(ip_range='1.2.3.4/24', organization_id=1))
    assert_msg(rv, value='IP range added', response_code=201)


def test_update_ip_range(client):
    rv = client.put(
        url_for('api.update_ip_range', range_id=1),
        json=dict(ip_range='4.3.2.1/24', organization_id=1))
    assert rv.status_code == 200


def test_read_ip_range(client):
    rv = client.get(url_for('api.get_ip_ranges'))
    assert_msg(rv, key='ip_ranges')

    rv = client.get(url_for('api.get_ip_range', range_id=1))
    assert_msg(rv, key='ip_range')


def test_delete_ip_range(client):
    rv = client.delete(url_for('api.delete_ip_range', range_id=1))
    assert_msg(rv, value='IP range deleted')

    rv = client.delete(url_for('api.delete_ip_range', range_id=666))
    assert rv.status_code == 404
