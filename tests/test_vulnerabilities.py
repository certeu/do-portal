from flask import url_for
from .conftest import assert_msg


def test_create_vulnerability(client):
    rv = client.post(
        url_for('api.add_vulnerability'),
        json=dict(
            organization_id=1,
            url='http://hear-me-roar.tld/forest',
            check_string='--></script><script>alert("Honey")</script>',
            reporter_name='Yoggy',
            reporter_email='yoggy@hear-me-roar.frst',
            rtir_id=666,
            types=['XSS', 'berries']
        ),
    )
    assert_msg(rv, key='vulnerability', response_code=201)


def test_update_vulnerability(client):
    rv = client.put(
        url_for('api.update_vulnerability', vuln_id=1),
        json=dict()
    )
    assert rv.status_code == 422

    rv = client.put(
        url_for('api.update_vulnerability', vuln_id=1),
        json=dict(
            organization_id=1,
            url='http://hear-me-roar.tld/forest',
            check_string='--></script><script>alert("Moar moar")</script>',
            reporter_name='Yoggy',
            reporter_email='yoggy@hear-me-roar.frst',
            rtir_id=666,
            types=['XSS', 'cherries']
        ),
    )
    assert rv.status_code == 200


def test_read_vulnerability(client):
    rv = client.get(url_for('api.get_vulnerabilities'))
    assert_msg(rv, key='items')

    rv = client.get(url_for('api.get_vulnerability', vuln_id=1))
    assert_msg(rv, key='constituent')


def test_delete_vulnerability(client):
    rv = client.delete(url_for('api.delete_vulnerability', vuln_id=1))
    assert_msg(rv, value='Vulnerability deleted')

    rv = client.delete(url_for('api.delete_vulnerability', vuln_id=666))
    assert rv.status_code == 404


def test_cp_vulnerabilities(client):
    rv = client.get(url_for('cp.get_vulnerabilities'))
    assert rv.status_code == 200
