import random
import pytest
from flask import url_for
import flask_gnupg
from .conftest import assert_msg
from unittest.mock import Mock, MagicMock
from app.models import MailmanQuery, MailmanList, MailmanDomain
from app import mail, gpg


testlist = 'test-' + str(random.choice(range(666)))
testlistid = '{}.{}'.format(testlist, 'lists.cert.europa.eu')


# serialize unitest.mock.Mock?
class MockMember(dict):

    email = 'member@list.domain.tld'


class MockSettings(dict):

    def save(self):
        pass


class MockList:

    list_id = testlistid
    display_name = testlist
    settings = MockSettings()
    fqdn_listname = testlistid
    subscribe = Mock()
    unsubscribe = Mock()

    @property
    def members(self):
        return [MockMember()]

    def add_owner(self, owner):
        pass

    def delete(self):
        pass


class MockDomain:

    def create_list(self, name):
        return MockList()


def test_create_list(client, monkeypatch):
    monkeypatch.setattr(MailmanDomain, 'get', lambda **kw: MockDomain())

    rv = client.post(
        url_for('api.add_list'),
        json=dict(name=testlist, description='Test list {}'.format(testlist))
    )
    assert_msg(rv, value='List added', response_code=201)


update_params = [
    (dict(name='updated', settings=dict(description='updated')), 200),
    (dict(settings=dict(description='updated')), 422)
]


@pytest.mark.parametrize('post_data, status_code', update_params)
def test_update_list(client, monkeypatch, post_data, status_code):
    monkeypatch.setattr(MailmanList, 'get', lambda **kw: MockList())
    rv = client.put(url_for('api.update_list', list_id=testlistid),
                    json=post_data)
    assert rv.status_code == status_code


def test_read_lists(client, monkeypatch):
    monkeypatch.setattr(MailmanQuery, 'all', lambda l: [MockList()])
    rv = client.get(url_for('api.get_lists'))
    assert_msg(rv, key='lists')


def test_read_list(client, monkeypatch):
    monkeypatch.setattr(MailmanList, 'get', lambda **kw: MockList())
    rv = client.get(url_for('api.get_list', list_id=testlistid))
    assert_msg(rv, key='name')


def test_delete_list(client, monkeypatch):
    monkeypatch.setattr(MailmanList, 'get_or_404', lambda **kw: MockList())
    rv = client.delete(url_for('api.delete_list', list_id=testlistid))
    assert_msg(rv, value='List deleted')


def test_subscribe_list(client, monkeypatch):
    monkeypatch.setattr(MailmanList, 'get', lambda **kw: MockList())
    monkeypatch.setattr(flask_gnupg, 'fetch_gpg_key', lambda eml, ks: True)
    rv = client.put(
        url_for('api.subscribe_list', list_id=testlistid),
        json=dict(emails=['test@test.com']))
    assert rv.status_code == 200


def test_unsubscribe_list(client, monkeypatch):
    monkeypatch.setattr(MailmanList, 'get', lambda **kw: MockList())
    rv = client.put(
        url_for('api.unsubscribe_list', list_id=testlistid),
        json=dict(emails=['test@test.com']))
    assert rv.status_code == 200


def post_params():
    combos = ((False, False, 200),
              (True, False, 400),
              (True, True, 200))
    for enc, ok, s in combos:
        yield (dict(list_id=testlistid, subject='zZz',
                    content='ž', encrypted=enc),
               MagicMock(ok=ok),
               s)


@pytest.mark.parametrize('post_data, cryptmock, status_code', post_params())
def test_post_message(client, monkeypatch, post_data, cryptmock, status_code):
    monkeypatch.setattr(MailmanList, 'get', lambda **kw: MockList())
    monkeypatch.setattr(mail, 'send', lambda msg: True)
    monkeypatch.setattr(gpg.gnupg, 'encrypt_file',
                        lambda fo, eml, **kw: cryptmock)
    rv = client.post(url_for('api.post_message'), json=post_data)
    assert rv.status_code == status_code


check_params = [
    (MagicMock(ok=True), 200),
    (MagicMock(ok=False, stderr='Error'), 400),
]


@pytest.mark.parametrize('cryptmock, status_code', check_params)
def test_check_gpg(client, monkeypatch, cryptmock, status_code):
    monkeypatch.setattr(MailmanList, 'get', lambda **kw: MockList())
    monkeypatch.setattr(mail, 'send', lambda msg: True)
    monkeypatch.setattr(gpg.gnupg, 'encrypt_file',
                        lambda fo, eml, **kw: cryptmock)
    rv = client.get(url_for('api.check_gpg', list_id=testlistid))
    assert rv.status_code == status_code
