from flask import url_for
from .conftest import assert_msg


def test_create_org(client):
    rv = client.post(
        url_for('api.add_organization'),
        json=dict(
            abbreviation="CERT-EU",
            full_name="Computer Emergency Response Team for EU "
            "Institutions Agencies and Bodies",
            ip_ranges=["212.8.189.16/28"],
            abuse_emails=["cert-eu@ec.europa.eu"],
            contact_emails=[{
                "email": "cert-eu@ec.europa.eu"
            }],
            asns=[5400],
            fqdns=["cert.europa.eu"]))
    assert_msg(rv, value='Organization added', response_code=201)


def test_update_org(client):
    rv = client.put(
        url_for('api.update_organization', org_id=1),
        json=dict(
            abbreviation="CERT-EU",
            full_name="Computer Emergency Response Team for EU "
            "Institutions Agencies and Bodies",
            ip_ranges=["212.8.189.16/28"],
            abuse_emails=["cert-eu@ec.europa.eu"],
            contact_emails=[{
                "email": "cert-eu-new@ec.europa.eu"
            }],
            asns=[5400],
            fqdns=["cert.europa.eu"]))
    assert rv.status_code == 200


def test_return_orgs(client):
    rv = client.get(url_for('api.get_organizations'))
    assert_msg(rv, key='organizations')

    rv = client.get(url_for('api.get_organization', org_id=1))
    assert_msg(rv, key='abbreviation')

    rv = client.get(
        url_for('api.get_organization_by_abbr', org_abbr='cert-eu'))
    assert_msg(rv, key='abbreviation')


def test_org_queries(client):
    rv = client.post(url_for('api.query'))
    assert rv.status_code == 501


def test_is_constituent(client):
    rv = client.put(
        url_for('api.check_constituents'), json=["212.8.189.18", "1.2.3.4"])
    assert rv.status_code == 200

    assert rv.json['response']['212.8.189.18'] == 'CERT-EU'


def test_del_org(client):
    rv = client.delete(url_for('api.delete_organization', org_id=1))
    assert_msg(rv, value='Organization deleted')

    rv = client.delete(url_for('api.delete_organization', org_id=666))
    assert rv.status_code == 404
