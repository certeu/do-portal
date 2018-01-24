from flask import url_for
from .conftest import assert_msg


def test_return_countries(client):
    rv = client.get(url_for('cp.get_cp_countries'))
    assert_msg(rv, key='countries')
    got = list(rv.json.values())
    some_entry = got[0][0]

    rv = client.get(url_for('cp.get_cp_country',
                    country_id=some_entry['id']))
    assert_msg(rv, key='cc')
    got = list(rv.json.values())
    single_entry = rv.json
    assert some_entry['name'] == single_entry['name']
