from flask import url_for
from .conftest import assert_msg


def test_read_report(client):
    rv = client.get(url_for('api.get_reports'))
    assert_msg(rv, key='items')

    rv = client.get(url_for('api.get_report', report_id=1))
    assert rv.status_code == 404


def test_read_sample_report(client):
    rv = client.get(
        url_for('api.get_sample_report', sha256='NA1eeb2b09a4bf6c87b273305'))
    assert rv.status_code == 404
