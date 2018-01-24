import time
import pytest
from flask import url_for
from .conftest import assert_msg

from app.models import User


def test_login_logout(client):
    rv = client.post(
        url_for('auth.login'),
        json=dict(email=client.test_user.email, password='1e9c9525ef737'))
    assert rv.status_code == 200


def test_verify_totp(client, monkeypatch):
    monkeypatch.setattr(User, 'authenticate',
                        lambda u, a: (client.test_user, True))
    client.application.config['CP_WEB_ROOT'] = 'http://localhost'
    client.test_user.otp_enabled = True
    rv = client.post(url_for('auth.verify_totp'), json=dict(totp=123456))
    assert rv.status_code == 200


@pytest.mark.parametrize('toggle, expected_response',
                         [(True, 200), (False, 200), ('666', 422), (123, 422)])
def test_toggle_2fa(client, toggle, expected_response):
    rv = client.post(
        url_for('auth.toggle_2fa'), json=dict(totp=123456, otp_toggle=toggle))
    assert rv.status_code == expected_response


def test_auth_brute_force(client):
    codes = []
    for i in range(11):
        rv = client.get(url_for('auth.account'))
        codes.append(rv.status_code)
    assert all(code in codes for code in [200, 429])
    time.sleep(2)


def test_bosh(client):
    rv = client.get(url_for('auth.do_bosh_auth'))
    assert rv.status_code == 200

    cfg = client.application.config
    assert rv.json == {
        'service': cfg['BOSH_SERVICE'],
        'rooms': cfg['ROOMS'],
        'jid': 'test@abusehelperlab.cert.europa.eu/test-666',
        'rid': 4387476,
        'sid': '205be616f1bc48cc9ca7e405fa08adb7098af809',
    }


def test_my_account(client):
    rv = client.get(url_for('auth.account'))
    assert_msg(rv, 'email', client.test_user.email)
    assert_msg(rv, 'api_key', client.test_user.api_key)
    with pytest.raises(AttributeError):
        ro = client.test_user.password
        assert ro is False


def test_reset_api_key(client):
    rv = client.get(url_for('auth.reset_api_key'))
    assert_msg(rv, value='Your API key has been reset')


def test_set_password(client):
    token = client.test_user.generate_reset_token()
    rv = client.post(
        url_for('auth.set_password', token=token),
        follow_redirects=True,
        json=dict(password='e9c9525ef737', confirm_password='e9c9525ef737'))
    assert rv.status_code == 200


changepw_params = [
    ({
        'current_password': 'not-old-pass',
        'new_password': 'changedpass',
        'confirm_password': 'changedpass'
    }, 'Invalid current password', 400),
    ({
        'current_password': 'e9c9525ef737',
        'new_password': 'changedpass',
        'confirm_password': 'changedpassmiss'
    }, 'Confirmation password does not match', 400),
    ({
        'current_password': 'e9c9525ef737',
        'new_password': 'changedpass',
        'confirm_password': 'changedpass'
    }, 'Your password has been updated', 200),
]


@pytest.mark.parametrize('post_data, msg, status_code', changepw_params)
def test_change_password(client, post_data, msg, status_code):
    rv = client.post(url_for('auth.change_password'), json=post_data)
    assert_msg(rv, key='message', value=msg, response_code=status_code)


def test_reg_unreg_cp_account(client):
    rv = client.post(
        url_for('auth.register'),
        json=dict(
            organization_id=1,
            name='some',
            email='some@other7e405fa08adb709.com'))
    assert rv.status_code == 201

    rv = client.post(
        url_for('auth.unregister'),
        json=dict(
            organization_id=1,
            name='some',
            email='some@other7e405fa08adb709.com'))
    assert rv.status_code == 200
