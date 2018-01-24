from flask import url_for
from flask_sqlalchemy import BaseQuery


def test_create_av_scan(client, monkeypatch, malware_sample):
    monkeypatch.setattr(BaseQuery, 'first_or_404', lambda x: True)
    rv = client.post(
        url_for('api.add_av_scan'), json={
            'files': [malware_sample._asdict()]
        })
    assert rv.status_code == 202
