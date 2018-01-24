from flask import url_for
from .conftest import assert_msg
from app.models import User, MembershipRole


def test_create_user(client):
    client.api_user = find_user_by_name('certmaster')
    org_id = client.api_user.get_organizations().first().id
    orgadmin_role_id = \
        MembershipRole.query.filter_by(name='OrgAdmin').first().id
    rv = client.post(
        url_for('cp.add_cp_user'),
        json=dict(
            user=dict(email='mylogin@mydomain.at',
                      name='Max Muster'),
            organization_membership=dict(
                membership_role_id=orgadmin_role_id,
                organization_id=org_id,
                email='orgmail@someorg.at')
        )
    )
    assert_msg(rv, value='User added', response_code=201)
    rv_user = rv.json['user']
    rv_membership = rv.json['organization_membership']
    assert rv_user['id'] == rv_membership['user_id']
    assert rv_user['email'] == 'mylogin@mydomain.at'
    assert rv_membership['email'] == 'orgmail@someorg.at'


def test_create_user_with_invalid_email(client):
    client.api_user = find_user_by_name('certmaster')
    org_id = client.api_user.get_organizations().first().id
    orgadmin_role_id = \
        MembershipRole.query.filter_by(name='OrgAdmin').first().id
    rv = client.post(
        url_for('cp.add_cp_user'),
        json=dict(
            user=dict(email='foobar',
                      name='Max Muster'),
            organization_membership=dict(
                membership_role_id=orgadmin_role_id,
                organization_id=org_id,
                email='orgmail@someorg.at')
        )
    )
    assert rv.status_code == 422


def test_return_certmaster_orgs(client):
    client.api_user = find_user_by_name('certmaster')
    rv = client.get(url_for('cp.get_cp_organizations'))
    assert_msg(rv, key='organizations')
    got = list(rv.json.values())
    got_abbreviations = [i['abbreviation'] for i in got[0]]
    expect_abbreviations = ['cert', 'eorg', 'eorg-gas', 'eorg-electricity',
                            'energyorg', 'energyorg-gas', 'energyorg-electricity',
                            'energyorg-electricity-transmission']
    assert set(got_abbreviations) == set(expect_abbreviations)


def test_return_energyorg_admin_orgs(client):
    client.api_user = find_user_by_name('EnergyOrg Admin')
    rv = client.get(url_for('cp.get_cp_organizations'))
    assert_msg(rv, key='organizations')
    got = list(rv.json.values())
    got_abbreviations = [i['abbreviation'] for i in got[0]]
    expect_abbreviations = ['energyorg', 'energyorg-gas', 'energyorg-electricity',
                            'energyorg-electricity-transmission']
    assert set(got_abbreviations) == set(expect_abbreviations)


def test_return_energyorg_ciso_orgs(client):
    client.api_user = find_user_by_name('EnergyOrg CISO')
    rv = client.get(url_for('cp.get_cp_organizations'))
    assert rv.status_code == 200
    assert len(rv.json['organizations']) == 0, 'no organizations'


def test_delete_self_fails(client):
    client.api_user = find_user_by_name('EnergyOrg CISO')
    rv = client.delete(
        url_for('cp.delete_cp_user', user_id=client.api_user.id))
    assert rv.status_code == 403


def test_delete_user_higher_up_fails(client):
    client.api_user = find_user_by_name('EnergyOrg CISO')
    certmaster_user = find_user_by_name('certmaster')
    rv = client.delete(
        url_for('cp.delete_cp_user', user_id=certmaster_user.id))
    assert rv.status_code == 403


def test_delete_managed_user_works(client):
    client.api_user = find_user_by_name('certmaster')
    energyorg_ciso_user = find_user_by_name('EnergyOrg CISO')

    rv = client.get(url_for('cp.get_cp_organization_memberships'))
    got = list(rv.json.values())
    membership_ids_before = [i['id'] for i in got[0]]

    rv = client.delete(
        url_for('cp.delete_cp_user', user_id=energyorg_ciso_user.id))
    assert rv.status_code == 200

    rv = client.get(url_for('cp.get_cp_organization_memberships'))
    got = list(rv.json.values())
    membership_ids_after = [i['id'] for i in got[0]]
    assert set(membership_ids_before) != set(membership_ids_after)


def find_user_by_name(name):
    return User.query.filter_by(name=name).first()
