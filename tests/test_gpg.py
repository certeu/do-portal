import pytest
from flask import url_for
from .conftest import assert_msg
from unittest.mock import MagicMock
from app import gpg

pk = """
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: SKS 1.1.5
Comment: Hostname: pgp.mit.edu

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
4lmcbEeeNr6kWDUzyeBlyfNq/VF9GilTfGtbQQ==
=+Z/R
-----END PGP PUBLIC KEY BLOCK-----
"""


def test_search_key(client, monkeypatch):
    k = {
        'algo':
        '1',
        'date':
        '1353431464',
        'expires':
        '',
        'keyid':
        '480183F5942E91953F377D6C64CDC60B16E645C6',
        'length':
        '2048',
        'type':
        'pub',
        'uids': [
            'Vicente Prueba <vicente.prueba@test.com>',
            'Vicente Revuelto <vrevuelto@cert.europa.eu>'
        ]
    }
    monkeypatch.setattr(gpg.gnupg, 'search_keys', lambda q, ks: [k])
    rv = client.post(
        url_for('api.search_public_ks'), json=dict(email='test@domain.tld'))
    assert_msg(rv, key='keys')


ir = MagicMock(
    fingerprints=['480183F5942E91953F377D6C64CDC60B16E645C6'],
    imported=1,
    imported_rsa=1,
)


def test_import_keys(client, monkeypatch):
    monkeypatch.setattr(gpg.gnupg, 'recv_keys', lambda ks, k: ir)
    rv = client.post(
        url_for('api.import_keys'),
        json=dict(keys=['480183F5942E91953F377D6C64CDC60B16E645C6']))
    assert rv.status_code == 201


responses = [(ir, 201), (MagicMock(fingerprints=None), 400)]


@pytest.mark.parametrize('mock, status_code', responses)
def test_send_keys(client, monkeypatch, mock, status_code):
    monkeypatch.setattr(gpg.gnupg, 'import_keys', lambda k: mock)
    rv = client.post(url_for('api.submit_gpg_key'), json=dict(ascii_key=pk))
    assert rv.status_code == status_code
