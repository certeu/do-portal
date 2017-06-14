import pytest
from flask import url_for
from .conftest import assert_msg


def test_create_asn(client):
    rv = client.post(
        url_for('api.add_asn'),
        json=dict(asn=12345, organization_id=1, as_name='Dummy')
    )
    assert_msg(rv, value='Asn added', response_code=201)


def test_update_asn(client):
    rv = client.put(
        url_for('api.update_asn', asn_id=1),
        json=dict(asn=54321, organization_id=1, as_name="Dummier")
    )
    assert rv.status_code == 200


def test_read_asn(client):
    rv = client.get(url_for('api.get_asns'))
    assert_msg(rv, key='asns')

    rv = client.get(url_for('api.get_asn', asn_id=1))
    assert_msg(rv, key='asn')


@pytest.mark.parametrize('asn_id, status_code', [(1, 200), (666, 404)])
def test_delete_asn(client, asn_id, status_code):
    rv = client.delete(url_for('api.delete_asn', asn_id=asn_id))
    assert rv.status_code == status_code
