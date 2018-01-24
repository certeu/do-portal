from flask import url_for
from .conftest import assert_msg
from app.models import User


def test_create_org(client):
    rv = client.post(
        url_for('cp.add_cp_organization'),
        json=dict(abbreviation="CERT-EU",
                  full_name="Computer Emergency Response Team for EU ",
                  parent_org_id=client.test_user.organization_id)
    )
    assert_msg(rv, value='Organization added', response_code=201)


def test_update_org(client):
    rv = client.put(
        url_for('cp.update_cp_organization',
                org_id=client.test_user.organization_id),
        json=dict(abbreviation="CERT-EU",
                  full_name="Computer Emergency Response Team for EU new",
                  parent_org_id=client.test_user.organization_id)
    )
    assert rv.status_code == 200


def test_return_orgs(client):
    client.api_user = find_user_by_name('EnergyOrg Admin')
    rv = client.get(url_for('cp.get_cp_organizations'))
    assert_msg(rv, key='organizations')
    got = list(rv.json.values())
    got_ids = [i['id'] for i in got[0]]

    for org_id in got_ids:
        rv = client.get(url_for('cp.get_cp_organization',
                        org_id=org_id))
        assert_msg(rv, key='abbreviation')


def test_delete_org(client):
    client.api_user = find_user_by_name('EnergyOrg Admin')
    rv = client.get(url_for('cp.get_cp_organizations'))
    assert_msg(rv, key='organizations')
    got = list(rv.json.values())
    got_ids = [i['id'] for i in got[0]]
    got_ids.sort()
    # exclude last org, which cannot be deleted
    for org_id in got_ids[:-1]:
        rv = client.delete(url_for('cp.delete_cp_organization',
                           org_id=org_id))
        assert_msg(rv, value='Organization deleted')


def test_delete_nonexistent_org(client):
    client.api_user = find_user_by_name('EnergyOrg Admin')
    rv = client.delete(url_for('cp.delete_cp_organization', org_id=666))
    assert rv.status_code == 404


def find_user_by_name(name):
    return User.query.filter_by(name=name).first()
