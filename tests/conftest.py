from io import BytesIO
import hashlib
import ssdeep
from collections import namedtuple
import onetimepass
import pytest
import json
from flask import Response
from flask.testing import FlaskClient
from app import create_app
from app import db as _db
from app.models import User, OrganizationGroup, ReportType, Role
from app.models import Organization, ContactEmail
from app.utils import bosh_client


class TestResponse(Response):

    @property
    def json(self):
        return json.loads(self.data.decode('utf-8'))


class TestClient(FlaskClient):
    def open(self, *args, **kwargs):
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        if 'json' in kwargs:
            kwargs['data'] = json.dumps(kwargs.pop('json'))

        kwargs['headers'].update({'API-Authorization': self.test_user.api_key,
                                  'Accept': 'application/json'})
        if 'content_type' not in kwargs:
            kwargs['content_type'] = 'application/json'

        return super().open(*args, **kwargs)


@pytest.fixture(scope='module')
def app(request):
    """Build an application"""
    app = create_app('testing')
    ctx = app.app_context()
    ctx.push()

    request.addfinalizer(ctx.pop)
    return app


@pytest.fixture(scope='module', autouse=True)
def db(request, app):
    """Create test database tables"""
    _db.drop_all()
    # Create the tables based on the current model
    _db.create_all()

    user = User.create_test_user()
    TestClient.test_user = user
    app.test_client_class = TestClient
    app.response_class = TestResponse

    _db.session.commit()


@pytest.fixture(autouse=True)
def session(request, monkeypatch):
    """Prevent the session from closing"""
    # Roll back at the end of every test
    request.addfinalizer(_db.session.remove)

    # Prevent the session from closing (make it a no-op) and
    # committing (redirect to flush() instead)
    # https://alextechrants.blogspot.com/2014/01/unit-testing-sqlalchemy-apps-part-2.html
    # monkeypatch.setattr(_db.session, 'commit', _db.session.flush)
    monkeypatch.setattr(_db.session, 'remove', lambda: None)


@pytest.fixture(autouse=True)
def addsampledata(client):
    """Add sample testing data"""
    OrganizationGroup._OrganizationGroup__insert_defaults()
    ReportType._ReportType__insert_defaults()
    Role._Role__insert_defaults()

    o = Organization(
        abbreviation="CERT-EU",
        full_name="Computer Emergency Response Team for EU "
                  "Institutions Agencies and Bodies",
        ip_ranges=['212.8.189.16/28'],
        abuse_emails=['cert-eu@ec.europa.eu'],
        contact_emails=[ContactEmail(email='cert-eu@ec.europa.eu')],
        asns=[5400],
        fqdns=['cert.europa.eu']
    )
    _db.session.add(o)
    _db.session.commit()
    client.test_user.organization_id = o.id


@pytest.fixture(scope='module')
def client(request, app):
    """Return a :class:`TestClient` instance for testing"""
    client = app.test_client()
    client.__enter__()
    request.addfinalizer(lambda: client.__exit__(None, None, None))
    return client


@pytest.fixture(autouse=True)
def valid_totp(monkeypatch):
    monkeypatch.setattr(onetimepass, 'valid_totp',
                        lambda token, otp, window: True)


@pytest.fixture(autouse=True)
def fake_bosh(monkeypatch):
    class FakeBOSHClient(object):

        def __init__(self, username, password, service):
            self.jid = 'test@abusehelperlab.cert.europa.eu/test-666'
            self.rid = 4387476
            self.sid = '205be616f1bc48cc9ca7e405fa08adb7098af809'

        def start_session_and_auth(self, hold=1, wait=2):
            return True

    monkeypatch.setattr(bosh_client, 'BOSHClient', FakeBOSHClient)


@pytest.fixture
def malware_sample():
    sampledata = BytesIO(b'clean')
    buf = sampledata.read()
    sampledata.seek(0)
    md5_hash = hashlib.md5(buf).hexdigest()
    sha1_hash = hashlib.sha1(buf).hexdigest()
    sha256_hash = hashlib.sha256(buf).hexdigest()
    sha512_hash = hashlib.sha512(buf).hexdigest()
    ctph = ssdeep.hash(buf)

    Sample = namedtuple(
        'Sample',
        ['data', 'filename', 'md5', 'sha1', 'sha256', 'sha512', 'ctph'])

    sample = Sample(
        data='sampledata', filename='blah.zip', md5=md5_hash, sha1=sha1_hash,
        sha256=sha256_hash, sha512=sha512_hash, ctph=ctph)
    return sample


def assert_msg(rv, key=None, value=None, response_code=None):
    if key is None:
        key = 'message'
    if response_code is None:
        response_code = 200
    assert rv.status_code == response_code
    assert rv.json[key] or hasattr(rv.json, key)

    if value is not None:
        assert rv.json[key] == value
