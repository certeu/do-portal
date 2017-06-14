import pytest
from flask import url_for
from .conftest import assert_msg


def test_create_fqdn(client):
    rv = client.post(
        url_for('api.add_fqdn'),
        json=dict(fqdn='cert.europa.eu', organization_id=1)
    )
    assert_msg(rv, value='Fqdn added', response_code=201)


def test_update_fqdn(client):
    rv = client.put(
        url_for('api.update_fqdn', fqdn_id=1),
        json=dict(fqdn='cert.europa.eu', organization_id=1)
    )
    assert rv.status_code == 200


def test_read_fqdn(client):
    rv = client.get(url_for('api.get_fqdns'))
    assert_msg(rv, key='fqdns')

    rv = client.get(url_for('api.get_fqdn', fqdn_id=1))
    assert_msg(rv, key='fqdn')


@pytest.mark.parametrize('fqdn_id, status_code', [(1, 200), (666, 404)])
def test_delete_fqdn(client, fqdn_id, status_code):
    rv = client.delete(url_for('api.delete_fqdn', fqdn_id=fqdn_id))
    assert rv.status_code == status_code
