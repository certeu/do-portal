from flask import url_for
from .conftest import assert_msg
from unittest.mock import MagicMock
from app.models import MailmanUser
import pytest


def test_create_email(client):
    rv = client.post(
        url_for('api.add_email'), json=dict(email='new@cert.europa.eu'))
    assert rv.status_code == 404


def test_update_email(client):
    rv = client.put(
        url_for('api.update_email', email_id=1),
        json=dict(email='updated@cert.europa.eu'))
    assert rv.status_code == 200


def test_read_emails(client, monkeypatch):
    users = MagicMock(addresses=[
        MagicMock(__str__=lambda x: 'some-mail@ec.europa.eu'),
        MagicMock(__str__=lambda x: 'blahblah@domain.tld')
    ])
    monkeypatch.setattr(MailmanUser.query, 'all', lambda: [users])
    rv = client.get(url_for('api.get_emails'))
    assert_msg(rv, key='emails')


@pytest.mark.parametrize('eml_id, status_code', [(1, 200), (666, 404)])
def test_delete_email(client, eml_id, status_code):
    rv = client.delete(url_for('api.delete_email', email_id=eml_id))
    assert rv.status_code == status_code
