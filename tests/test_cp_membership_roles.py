from flask import url_for
from .conftest import assert_msg


def test_return_membership_roles(client):
    rv = client.get(url_for('cp.get_cp_membership_roles'))
    assert_msg(rv, key='membership_roles')
    got = list(rv.json.values())
    some_entry = got[0][0]

    rv = client.get(url_for('cp.get_cp_membership_role',
                    role_id=some_entry['id']))
    assert_msg(rv, key='display_name')
    got = list(rv.json.values())
    single_entry = rv.json
    assert some_entry['name'] == single_entry['name']
